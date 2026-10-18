"""Kariyer Kapısı.

api.kariyerkapisi.gov.tr sadece Türkiye'den erişilebiliyor; ana sitedeki
RSS beslemesi ise her yerden açılıyor ve tüm aktif ilanları içeriyor.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from ..models import Ilan, SourceError
from ..text import clean

LABEL = "Kariyer Kapısı"
RSS = "https://kariyerkapisi.gov.tr/RSS"


def fetch(s, seen) -> list[Ilan]:
    r = s.get(RSS, timeout=180)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    items = root.findall("./channel/item")
    if not items:
        raise SourceError("RSS beslemesi boş geldi")

    out = []
    for it in items:
        link = (it.findtext("link") or it.findtext("guid") or "").strip()
        m = re.search(r"[?&]i=([0-9a-fA-F-]{36})", link)
        title = clean(it.findtext("title"))
        category = clean(it.findtext("category"))
        try:
            published = parsedate_to_datetime(it.findtext("pubDate")).date().isoformat()
        except (TypeError, ValueError):
            published = ""
        out.append(Ilan(
            source="kariyerkapisi",
            id=m.group(1) if m else link,
            title=title,
            url=link,
            org=title.split(" - ", 1)[0] if " - " in title else "",
            detail=category,
            note=" · ".join(filter(None, [category, f"yayın: {published}" if published else ""])),
        ))
    return out
