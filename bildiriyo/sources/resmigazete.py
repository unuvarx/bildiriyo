"""Resmî Gazete "Çeşitli İlânlar" bölümü.

Her ilan ayrı bir PDF; sayfada yalnızca kurum adı var. Personel ilanı olup
olmadığını anlamak için PDF metni okunur. Bot bir gün çalışamazsa ilan
kaçmasın diye son LOOKBACK_DAYS günün sayıları taranır.
"""
from __future__ import annotations

import io
import logging
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..models import Ilan, SourceError
from ..text import clean, fold

LABEL = "Resmî Gazete"
FIHRIST = "https://www.resmigazete.gov.tr/fihrist"
LOOKBACK_DAYS = 7  # günde bir tarama + olası kesintiler için geniş pay
TR = timezone(timedelta(hours=3))

# PDF metninde bunlardan biri geçerse personel ilanı sayılır.
PERSONEL = re.compile(
    r"personel|alim ilan|alimi ilan|istihdam|ogretim (uyesi|elemani|gorevlisi)|arastirma gorevlisi"
    r"|uzman yardimcisi|denetci yardimcisi|mufettis yardimcisi|memur|isci alim|giris sinavi|sozlesmeli"
)
NOT_PERSONEL = re.compile(r"ihale|yasaklama|tescil|ruhsat|imar plani|kamulastirma")
log = logging.getLogger(__name__)


def _ocr(pdf: bytes, pages: int = 2) -> str:
    """Taranmış (resim) PDF'in ilk sayfalarını OCR ile okur. Araçlar yoksa boş döner."""
    if not (shutil.which("pdftoppm") and shutil.which("tesseract")):
        return ""
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "in.pdf")
        with open(src, "wb") as f:
            f.write(pdf)
        subprocess.run(["pdftoppm", "-r", "200", "-l", str(pages), "-png", src, os.path.join(d, "p")],
                       check=True, timeout=120)
        langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout.split()
        lang = "tur" if "tur" in langs else "eng"
        out = []
        for img in sorted(f for f in os.listdir(d) if f.endswith(".png")):
            out.append(subprocess.run(["tesseract", os.path.join(d, img), "-", "-l", lang],
                                      capture_output=True, text=True, timeout=180).stdout)
        return " ".join(out)


def _pdf_text(s, url) -> str:
    r = s.get(url, timeout=120)
    r.raise_for_status()
    reader = PdfReader(io.BytesIO(r.content))
    text = " ".join((p.extract_text() or "") for p in reader.pages)
    if len(clean(text)) < 300:
        try:
            text += " " + _ocr(r.content)
        except Exception as e:
            log.warning("OCR başarısız %s: %s", url, e)
    return text


def _issue_pages(s, day) -> list[str]:
    """O günün (mükerrerler dahil) Çeşitli İlânlar sayfalarının URL'leri."""
    urls = []
    for params in ({"tarih": day}, {"tarih": day, "mukerrer": 1}):
        r = s.get(FIHRIST, params=params, timeout=90)
        if r.status_code == 404:
            continue
        r.raise_for_status()
        if "yayimlanmamaktadir" in fold(r.text):
            break  # bayram vb.: o gün Resmî Gazete çıkmıyor
        if "fihrist-item" not in r.text:
            # Engelleme/hata sayfası: "ilan yok" sanıp sessizce geçmek yerine hata ver.
            raise SourceError(f"Fihrist sayfası beklenen biçimde değil ({day}, {len(r.text)} bayt)")
        for a in BeautifulSoup(r.text, "html.parser").find_all("a", href=True):
            if "/ilanlar/" in a["href"] and "cesitli" in fold(a.get_text()):
                u = urljoin(r.url, a["href"])
                if u not in urls:
                    urls.append(u)
    return urls


def _ads_on_page(s, page_url):
    """(kurum başlığı, pdf url) çiftleri. Başlıklar ve PDF'ler aynı sırada."""
    r = s.get(page_url, timeout=90)
    r.raise_for_status()
    html = r.content.decode("windows-1254", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    pdfs = [urljoin(page_url, a["href"]) for a in soup.find_all("a", href=True)
            if a["href"].lower().endswith(".pdf")]
    heads = [clean(t) for t in re.findall(r"([^\n:]{5,200}?(?:dan|den|tan|ten)\s*:)",
                                          clean(soup.get_text("\n")).replace(":", ":\n"))]
    if len(heads) != len(pdfs):
        heads = [""] * len(pdfs)
    return list(zip(heads, pdfs))


def _title(text, head):
    """PDF metninden (kurum, başlık). Baştaki dizgi notlarını atar."""
    text = re.sub(r"^.{0,120}?ÇEŞİTLİ İLANLAR\W*\d*\s*", "", text)
    m = re.match(r"(.{3,150}?(?:dan|den|tan|ten))\s*:\s*", text)
    org = m.group(1) if m else head.rstrip(":").strip()
    rest = text[m.end():] if m else text
    caps = re.match(r"[A-ZÇĞİÖŞÜÂÎÛ0-9][A-ZÇĞİÖŞÜÂÎÛ0-9 ()\-–/.,’'“”]{8,}(?= [A-ZÇĞİÖŞÜ][a-zçğıöşü]|$)", rest)
    title = caps.group(0).strip() if caps else rest[:120] + "…"
    title = re.split(r"\s\d{4,5}/\d", title)[0]  # sayfa altı ilan numarası
    return clean(org), clean(title) or "Çeşitli İlan"


def fetch(s, seen) -> list[Ilan]:
    today = datetime.now(TR).date()
    out, ids, failed = [], set(), []
    for d in range(LOOKBACK_DAYS):
        day = (today - timedelta(days=d)).isoformat()
        for page in _issue_pages(s, day):
            for head, pdf in _ads_on_page(s, page):
                iid = pdf.rsplit("/", 1)[1]
                if iid in seen or iid in ids:
                    continue  # PDF'i tekrar indirmeye gerek yok
                ids.add(iid)
                try:
                    text = clean(_pdf_text(s, pdf))
                except Exception as e:
                    # "Görüldü" sayılmasın: sonraki taramada tekrar denenir (son 3 gün taranıyor).
                    log.warning("PDF indirilemedi %s: %s", pdf, e)
                    failed.append(pdf)
                    continue
                ftext = fold(text)
                org, title = _title(text, head)
                note = day
                if NOT_PERSONEL.search(fold(title)):
                    out.append(Ilan(source="resmigazete", id=iid, title=title, url=pdf, silent=True))
                    continue
                if PERSONEL.search(ftext):
                    pass
                elif len(text) >= 300:
                    out.append(Ilan(source="resmigazete", id=iid, title=title, url=pdf, silent=True))
                    continue
                else:
                    # Metni (OCR dahil) okunamayan PDF: kaçırmamak için "kontrol edin" diye bildir.
                    note += " · PDF okunamadı"
                out.append(Ilan(
                    source="resmigazete", id=iid, title=title, url=pdf,
                    org=org, detail=text[:30000], has_text=len(text) >= 300, note=note,
                ))
    if failed and not out:
        raise SourceError(f"{len(failed)} ilan PDF'i indirilemedi")
    return out
