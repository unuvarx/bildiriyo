"""İŞKUR: e-Şube'deki kamu işyeri ilanları + İŞKUR'un kendi personel alım duyuruları."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Ilan, SourceError
from ..text import clean, fold

LABEL = "İŞKUR"
SEARCH = "https://esube.iskur.gov.tr/Istihdam/AcikIsIlanAra.aspx"
DUYURU = "https://www.iskur.gov.tr/duyurular/"
DUYURU_RE = re.compile(r"personel|istihdam|sinav|isci alim|eleman alim|uzman yardimcisi")


MAX_PAGES = 100


def _form(soup):
    form = {i["name"]: i.get("value", "") for i in soup.find_all("input", type="hidden") if i.get("name")}
    for sel in soup.find_all("select"):
        o = sel.find("option", selected=True) or sel.find("option")
        if sel.get("name"):
            form[sel["name"]] = o.get("value", "") if o else ""
    form["ctl04$IsyeriTuruRadios"] = "kamuRadio"
    form["__EVENTARGUMENT"] = ""
    return form


def _kamu_ilanlari(s):
    """Kamu işyeri ilanlarının TÜM sayfaları. Toplam kayıt sayısına ulaşılamazsa hata verir."""
    r = s.get(SEARCH, timeout=90)
    r.raise_for_status()
    form = _form(BeautifulSoup(r.text, "html.parser"))
    form["__EVENTTARGET"] = "ctl04$ctlAcikIsPageCommand$CommandItem_Search"
    form["ctl04$ctlIlanTarihi"] = "1"  # Tümü

    rows, total = {}, None
    for _ in range(MAX_PAGES):
        r = s.post(SEARCH, data=form, timeout=120)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        if "ctlGridAcikIslerListeDetail" not in r.text:
            if "bulunamad" in r.text:
                return []
            raise SourceError("e-Şube arama sonucu beklenen biçimde değil")
        m = re.search(r"Toplam Kayıt:\s*([\d.]+)", soup.get_text(" "))
        total = int(m.group(1).replace(".", "")) if m else None
        for a in soup.select("a.share-toggle[data-ilanno]"):
            rows.setdefault(a["data-ilanno"], a)
        nxt = soup.find("a", id="ctl04_ctlDataPagerDetay_btnNext")
        if total is None or len(rows) >= total or not nxt or "disabled" in (nxt.get("class") or []):
            break
        form = _form(soup)
        form["__EVENTTARGET"] = "ctl04$ctlDataPagerDetay$btnNext"
    if total is not None and len(rows) < total:
        raise SourceError(f"e-Şube'de {total} kamu ilanı var ama {len(rows)} tanesi okunabildi")
    return list(rows.values())


def fetch(s, seen) -> list[Ilan]:
    out = []
    for a in _kamu_ilanlari(s):
        no = a["data-ilanno"]
        tr = a.find_parent("tr")
        org = tr.find("span", id=re.compile("ctlIsverenDL")) if tr else None
        out.append(Ilan(
            source="iskur", id=no,
            title=clean(a.get("data-meslekler")),
            url=f"https://esube.iskur.gov.tr/Istihdam/AcikIsIlanDetay.aspx?uiID={no}",
            org=clean(org.get_text()) if org else "",
            deadline=a.get("data-sontarih", ""),
            note=" · ".join(filter(None, [clean(a.get("data-il")), f"{a.get('data-acikissayi')} kişi"])),
        ))

    r = s.get(DUYURU, timeout=90)
    r.raise_for_status()
    links = BeautifulSoup(r.text, "html.parser").select('a[href^="/duyurular/"]')
    if not links:
        raise SourceError("Duyurular sayfası boş geldi")
    for a in links:
        t = clean(a.get_text(" ", strip=True))
        if len(t) > 15 and DUYURU_RE.search(fold(t)) and "ihale" not in fold(t):
            out.append(Ilan(
                source="iskur", id="duyuru:" + a["href"].strip("/").split("/")[-1],
                title=t, url=urljoin(DUYURU, a["href"]), org="Türkiye İş Kurumu",
            ))
    return out
