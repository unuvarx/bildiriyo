import re

_FOLD = str.maketrans("çğıöşüâîûÇĞIİÖŞÜÂÎÛ", "cgiosuaiucgiiosuaiu")


def fold(s: str) -> str:
    """Türkçe-duyarsız karşılaştırma için küçük harf + ASCII'ye indirger."""
    return re.sub(r"\s+", " ", (s or "").translate(_FOLD).lower()).strip()


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()
