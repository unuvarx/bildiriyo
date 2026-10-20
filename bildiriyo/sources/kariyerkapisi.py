"""Kariyer Kapısı.

api.kariyerkapisi.gov.tr sadece Türkiye'den erişilebiliyor; ana sitedeki
RSS beslemesi ise her yerden açılıyor ve tüm aktif ilanları içeriyor.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from ..models import Ilan, SourceError
from ..text import clean

LABEL = "Kariyer Kapısı"
RSS = "https://kariyerkapisi.gov.tr/RSS"
API = "https://api.kariyerkapisi.gov.tr/api"


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
            category=category,
            note=f"yayın: {published}" if published else "",
        ))
    return out


def enrich(s, ilan: Ilan) -> None:
    """İlan metni sadece Türkiye'den erişilebilen API'de; erişilemezse sessizce geç."""
    body = {"ilanGuid": ilan.id}
    try:
        parts = [requests.post(f"{API}/ilan/GetIlanPreviewPublic", json=body, timeout=(8, 60),
                               headers={"User-Agent": s.headers["User-Agent"]}).json().get("ilanMetni", "")]
        alt = requests.post(f"{API}/altilan/GetAltIlanInfoByIlanIdPublic", json=body, timeout=(8, 60),
                            headers={"User-Agent": s.headers["User-Agent"]}).json()
        parts += [f"{a.get('ilanBaslik', '')} {a.get('ilanMetni', '')}" for a in alt or []]
    except (requests.RequestException, ValueError):
        return
    text = clean(re.sub(r"\[/?[a-z0-9=#]+\]", " ", " ".join(parts)))
    if len(text) > 200:
        ilan.detail, ilan.has_text = text, True
