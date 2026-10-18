from __future__ import annotations

from . import profile
from .models import Ilan
from .text import fold

GREEN, YELLOW, GREY = "green", "yellow", "grey"


def _first(words, text):
    return next((w for w in words if w in text), "")


def classify(ilan: Ilan) -> tuple[str, str]:
    """(seviye, eşleşen kelime). Hiçbir ilan atılmaz, sadece önceliklendirilir.

    Önce başlığa bakılır; ilan metni (detail) yalnızca başlık kararsızsa
    kullanılır. Böylece "Bilgisayar Mühendisliği bölümüne öğretim üyesi"
    gibi doktora isteyen ilanlar metindeki bölüm adı yüzünden 🟢 olmaz.
    """
    head = fold(" ".join([ilan.title, ilan.org, ilan.note]))
    body = fold(ilan.detail)

    kw = _first(profile.NOTICE, head)
    if kw:
        return GREY, kw
    kw = _first(profile.STRONG, head)
    if kw:
        return GREEN, kw
    kw = _first(profile.UNLIKELY, head)
    if kw:
        return (YELLOW if _first(profile.RESCUE, head) else GREY), kw

    kw = _first(profile.BODY_UNLIKELY, body)
    if kw and not _first(profile.BODY_RESCUE, body):
        return GREY, kw
    kw = _first(profile.STRONG, body)
    if kw:
        return GREEN, kw
    return YELLOW, ""
