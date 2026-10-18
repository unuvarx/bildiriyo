from __future__ import annotations

from ..models import Ilan, SourceError
from ..text import clean

LABEL = "ilan.gov.tr"
API = "https://www.ilan.gov.tr/api/api/services/app/Ad/AdsByFilter"
HEADERS = {
    "X-Request-Origin": "IGT-UI",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "text/plain",
    "Content-Type": "application/json-patch+json",
}
PERSONEL_ALIMI = 5  # ilan türü kimliği ("ats" filtresi)
PAGE = 20  # sunucu daha büyük değerleri 20'ye düşürüyor


def fetch(s, seen) -> list[Ilan]:
    out, skip, total = [], 0, None
    while total is None or skip < min(total, 1000):
        r = s.post(API, headers=HEADERS, timeout=90, json={
            "keys": {"ats": [PERSONEL_ALIMI]}, "skipCount": skip, "maxResultCount": PAGE,
        })
        r.raise_for_status()
        res = r.json()["result"]
        total = res["numFound"]
        ads = res["ads"]
        if not ads:
            break
        for a in ads:
            out.append(Ilan(
                source=__name__.rsplit(".", 1)[1],
                id=str(a["id"]),
                title=clean(a.get("title")),
                url="https://www.ilan.gov.tr" + a["urlStr"],
                org=clean(a.get("advertiserName")),
                note=clean(a.get("addressCityName")),
            ))
        skip += len(ads)
    if not out:
        raise SourceError("Personel alımı ilanı listesi boş geldi")
    return out
