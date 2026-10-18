from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..models import Ilan, SourceError
from ..text import clean

LABEL = "Yerel Yönetimler (ÇŞİDB)"
URL = "https://yerelyonetimler.csb.gov.tr/duyurular"


def fetch(s, seen) -> list[Ilan]:
    r = s.get(URL, timeout=90)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    out, ids = [], set()
    for a in soup.find_all("a", href=True):
        m = re.search(r"-duyuru-(\d+)$", a["href"])
        if not m or m.group(1) in ids:
            continue
        ids.add(m.group(1))
        # Kart düzenine göre <p> etiketlerinden biri gün adı ("Cuma"), en uzunu başlık.
        title = max((clean(p.get_text(" ", strip=True)) for p in a.find_all("p")), key=len, default="")
        title = title or clean(a.get_text(" ", strip=True))
        date = a.find("span")
        out.append(Ilan(
            source=__name__.rsplit(".", 1)[1],
            id=m.group(1),
            title=title.rstrip(". "),
            url=a["href"],
            note=clean(date.get_text()) if date else "",
        ))
    if not out:
        raise SourceError("Duyuru listesi bulunamadı (site yapısı değişmiş olabilir)")
    return out
