"""Bu ilana başvurabilir miyim? Kurallar profile.py'de."""
from __future__ import annotations

import re

from . import profile
from .models import Ilan
from .text import fold

OK, CHECK, SKIP = "ok", "check", "skip"

_B = r"(?<![a-z])"  # kelime başı: "lisans" "onlisans" içinde eşleşmesin
_BOLUM_OK = [re.compile(_B + p) for p in profile.BOLUM_OK]
_MAYBE = [(re.compile(_B + p), why) for p, why in profile.BOLUM_MAYBE]
# "Bölümler ekte/tabloda/kılavuzda" türü sebepler
_REFER = {why for _, why in profile.BOLUM_MAYBE if "tablo" in why or "ekinde" in why or "kılavuz" in why}
_CAUTION = [(re.compile(_B + p), why) for p, why in profile.CAUTION]
_BILISIM = [re.compile(_B + p) for p in profile.BILISIM_PERSONELI]


def _snippet(text: str, m: re.Match) -> str:
    return text[max(0, m.start() - 40): m.end() + 40].strip()


def decide(i: Ilan) -> tuple[str, str]:
    """(OK | CHECK | SKIP, sebep)."""
    head = fold(f"{i.title} {i.category}")
    for kw, why in profile.SKIP_TITLE:
        if re.search(_B + re.escape(kw), head):
            return SKIP, why
    cat = fold(i.category)
    if any(c in cat for c in profile.SKIP_CATEGORY):
        return SKIP, f"ilan türü: {i.category}"

    if i.source == "iskur" and i.id.isdigit() and not re.search(profile.ISKUR_MESLEK_OK, head):
        return SKIP, "meslek alanınızla ilgili değil"

    text = fold(i.detail)
    if (re.search(r"2547 ?s ?ayili", text[:1500]) or "akademik birim" in text[:1500]) \
            and any(a in text[:3000] for a in profile.ACADEMIC_BODY + ["akademik birim"]):
        return SKIP, "akademik kadro (2547 sayılı Kanun)"
    if profile.DENEYIM_YIL < 3 and any(p.search(f"{head} {text}") for p in _BILISIM):
        return SKIP, "sözleşmeli bilişim personeli: tüm kadrolar en az 3 yıl deneyim istiyor"

    if i.has_text and re.search(r"p9[34]\b", text) and not re.search(
            r"p3\b|kpssp3|(?<![a-z])(?<!on )lisans (?:mezun|duzeyinde|egitimi)|(?<![a-z])(?<!on )lisans programlarin", text):
        return SKIP, "sadece lise/ön lisans kadroları (KPSS P93/P94)"

    if i.has_text:
        m = next((m for p in _BOLUM_OK if (m := p.search(text))), None)
        if not m:
            maybe = next((why for p, why in _MAYBE if p.search(text)), None)
            if maybe in _REFER and re.search(profile.NAMED_LIST, text):
                maybe = None  # bölüm listesi metinde var ve Yazılım Müh. içinde değil
            if maybe:
                return CHECK, f"{maybe}; bölüm şartını kontrol edin"
            return SKIP, f"bölüm şartı {profile.BOLUM} içermiyor"
        why = f"bölüm şartı uygun: “…{_snippet(text, m)}…”"
        cautions = [w for p, w in _CAUTION if p.search(text)]
        if cautions:
            return CHECK, f"{why}; ama {', '.join(cautions)}"
        return OK, why

    other = re.search(r"([a-z]+) muhendisligi", head)
    if other and other.group(1) not in ("bilgisayar", "yazilim"):
        return SKIP, f"başlıkta farklı bölüm: {other.group(0)}"
    for kw, why in profile.SKIP_TITLE_NO_TEXT:
        if re.search(_B + re.escape(kw), head):
            return SKIP, why
    if any(k in head for k in profile.TITLE_OK):
        return OK, "başlık uygun"
    return CHECK, "ilan metni okunamadı, şartları kontrol edin"
