from __future__ import annotations

from ..models import Ilan, SourceError
from ..text import clean

LABEL = "Kariyer Kapısı"
API = "https://api.kariyerkapisi.gov.tr/api/ilan/SearchIlanPublic"


def fetch(s, seen) -> list[Ilan]:
    # Boş filtre tüm aktif ilanları tek seferde döndürür.
    r = s.post(API, json={"krM_ID": 0, "searchText": "", "il": "0", "ilanTuru": "0"}, timeout=120)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list) or not data:
        raise SourceError("API boş/beklenmeyen yanıt döndü")

    out = []
    for x in data:
        if x.get("ilanTipi") == 1 or not x.get("basvuruLinki"):
            url = f"https://kariyerkapisi.gov.tr/IlanDetay?i={x['guid']}"
        else:
            url = x["basvuruLinki"]
        out.append(Ilan(
            source=__name__.rsplit(".", 1)[1],
            id=x["guid"],
            title=clean(x.get("ilanBaslik")),
            url=url,
            org=clean(x.get("kurumAdi")),
            deadline=(x.get("bitTarih") or "")[:10],
            detail=x.get("ilanTuru") or "",
            note=x.get("ilanTuru") or "",
        ))
    return out
