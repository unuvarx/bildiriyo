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
PAGE_SIZE = 15  # e-Şube sonuç sayfası boyutu
DUYURU_RE = re.compile(r"personel|istihdam|sinav|isci alim|eleman alim|uzman yardimcisi")


def _search(s, ilan_tarihi):
    r = s.get(SEARCH, timeout=90)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    form = {i["name"]: i.get("value", "") for i in soup.find_all("input", type="hidden") if i.get("name")}
    for sel in soup.find_all("select"):
        o = sel.find("option", selected=True) or sel.find("option")
        if sel.get("name"):
            form[sel["name"]] = o.get("value", "") if o else ""
    form.update({
        "__EVENTTARGET": "ctl04$ctlAcikIsPageCommand$CommandItem_Search",
        "__EVENTARGUMENT": "",
        "ctl04$IsyeriTuruRadios": "kamuRadio",
        "ctl04$ctlIlanTarihi": ilan_tarihi,  # 1=Tümü, 2=Son 24 saat
    })
    r = s.post(SEARCH, data=form, timeout=120)
    r.raise_for_status()
    if "ctlGridAcikIslerListeDetail" not in r.text and "bulunamad" not in r.text:
        raise SourceError("e-Şube arama sonucu beklenen biçimde değil")
    return BeautifulSoup(r.text, "html.parser").select("a.share-toggle[data-ilanno]")


def fetch(s, seen) -> list[Ilan]:
    out, ids, warn = [], set(), ""
    for tarih in ("2", "1"):
        rows = _search(s, tarih)
        if len(rows) >= PAGE_SIZE:
            warn = "e-Şube'de 15'ten fazla kamu ilanı var; tamamını görmek için siteye bakın"
        for a in rows:
            no = a["data-ilanno"]
            if no in ids:
                continue
            ids.add(no)
            out.append(Ilan(
                source="iskur", id=no,
                title=clean(a.get("data-meslekler")),
                url=f"https://esube.iskur.gov.tr/Istihdam/AcikIsIlanDetay.aspx?uiID={no}",
                org=clean(a.find_parent("tr").find("span", id=re.compile("ctlIsverenDL")).get_text())
                if a.find_parent("tr") else "",
                deadline=a.get("data-sontarih", ""),
                note=" · ".join(filter(None, [clean(a.get("data-il")), f"{a.get('data-acikissayi')} kişi", warn])),
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
