from __future__ import annotations

import hashlib
import re

from bs4 import BeautifulSoup

from ..models import Ilan, SourceError
from ..text import clean, fold

LABEL = "Kamu İlanları (SBB)"
BASE = "https://kamuilan.sbb.gov.tr/"


def fetch(s, seen) -> list[Ilan]:
    r = s.get(BASE, timeout=90)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    out, ids = [], set()
    for a in soup.find_all("a", href=True):
        if "ilanDetay.aspx" not in a["href"]:
            continue
        title = clean(a.get_text(" ", strip=True))
        if not title:
            continue
        # "kod" parametresi her istekte değiştiği için kimlik başlıktan üretilir.
        # Aynı ilan sayfada iki kez (parantezli/parantezsiz) geçebiliyor.
        key = fold(re.sub(r"[()]", " ", title))
        iid = hashlib.sha1(key.encode()).hexdigest()[:16]
        if iid in ids:
            continue
        ids.add(iid)
        m = re.search(r"\(?\s*(\d{1,2} \w+ - \d{1,2} \w+)\s*\)?\s*$", title)
        out.append(Ilan(
            source=__name__.rsplit(".", 1)[1],
            id=iid,
            title=title[: m.start()].strip() if m else title,
            url=BASE + a["href"],
            deadline=m.group(1) if m else "",
        ))
    if not out:
        raise SourceError("Sayfada ilan linki bulunamadı (site yapısı değişmiş olabilir)")
    return out
