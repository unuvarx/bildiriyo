"""Aynı ilan farklı kaynaklarda (Kariyer Kapısı, Resmî Gazete, ilan.gov.tr) çıkabilir.

Kurum adı + ilan türü parmak izi ile eşleştirilir. Kariyer Kapısı ilan metni
yurt dışından okunamadığı için, aynı ilanın başka kaynaktaki metnine göre
verilen karar da buradan kullanılır.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from .models import Ilan
from .text import fold

KEEP_DAYS = 60
KINDS = [
    "bilisim", "uzman yardimci", "denetci yardimci", "mufettis yardimci", "kontrolor yardimci",
    "aktuer", "subay", "polis", "sozlesmeli personel", "surekli isci", "isci", "memur",
    "tercih", "yerlestirme", "personel",
]
_STOP = {"ve", "il", "ili", "tc", "t.c", "dan", "den", "ilan", "ilani", "alim", "alimi"}
# Başlıktaki genel kelimeler (kurum adı dışındakiler)
_GENERIC = {"perso", "alaca", "sinav", "giris", "duyur", "sozle", "uzman", "yardi", "kisil", "kisi",
            "adet", "kadro", "memur", "isci", "daimi", "statu", "temin", "genel", "baska", "mudur",
            "rekto", "yili", "sinif", "muvaz", "hakki", "sozlu", "yazil"}


def _stems(org: str) -> set[str]:
    words = re.findall(r"[a-z]+", fold(org))
    words = [re.sub(r"(?:n?dan|n?den|n?tan|n?ten)$", "", w) for w in words]
    return {w[:5] for w in words if len(w) >= 3 and w not in _STOP}


def fingerprint(i: Ilan) -> dict:
    # Kurum adı önce başlıktan alınır: ilan.gov.tr'de "yayımlayan" alanı birçok kurum için
    # aynı olabiliyor (örn. tüm kalkınma ajansları), başlık ise kurumu ayırt eder.
    # Resmî Gazete'de başlık kurum adı içermez; kurum ayrı alanda gelir.
    title_org = {w for w in _stems(i.title.split(" - ", 1)[0]) if w not in _GENERIC and not w.isdigit()}
    if len(title_org) >= 2 and i.source != "resmigazete":
        return {"o": sorted(title_org), "k": next((k for k in KINDS if k in fold(i.title)), "")}
    org = i.org or i.title.split(" - ", 1)[0]
    head = fold(i.title)
    kind = next((k for k in KINDS if k in head), "")
    return {"o": sorted(w for w in _stems(org) if w not in _GENERIC), "k": kind}


def _same(a: dict, b: dict) -> bool:
    oa, ob = set(a["o"]), set(b["o"])
    generic = {"", "personel"}
    if not oa or not ob or (a["k"] != b["k"] and a["k"] not in generic and b["k"] not in generic):
        return False
    common = len(oa & ob)
    # Belirgin ilan türü aynıysa ve kısa kurum adı uzun olanın içindeyse aynı ilandır:
    # "VAKIFLAR GENEL MÜDÜRLÜĞÜ" ↔ "Kültür ve Turizm Bakanlığı Vakıflar Genel Müdürlüğü"
    if a["k"] == b["k"] and a["k"] not in generic and (oa <= ob or ob <= oa):
        return True
    # Biri diğerinin kısaltılmış/uzatılmış hali olabilir: "X AJANSI (MARKA)" ↔ "X AJANSI GENEL SEKRETERLİĞİ"
    return common / len(oa | ob) >= 0.6 or (common >= 3 and common / min(len(oa), len(ob)) >= 0.8)


def find(st: dict, fp: dict):
    return next((x for x in st.setdefault("decided", []) if _same(x, fp)), None)


def remember(st: dict, fp: dict, decision: str, why: str, title: str, sent: bool) -> None:
    st.setdefault("decided", []).append({
        **fp, "dec": decision, "why": why, "t": title[:120], "sent": sent,
        "d": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })


def prune(st: dict) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).isoformat()
    st["decided"] = [x for x in st.get("decided", []) if x["d"] >= cutoff]
