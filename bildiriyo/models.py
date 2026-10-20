from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Ilan:
    source: str  # kaynak anahtarı, örn. "kariyerkapisi"
    id: str  # kaynak içinde benzersiz, kalıcı kimlik
    title: str
    url: str
    org: str = ""
    deadline: str = ""
    category: str = ""  # ilan türü (Kariyer Kapısı)
    detail: str = ""  # ilan metni (uygunluk kararı için)
    has_text: bool = False  # detail gerçekten ilan metnini içeriyor mu
    note: str = ""  # mesajda gösterilecek ek bilgi
    silent: bool = False  # personel ilanı değil: bildirme, sadece "görüldü" say


class SourceError(Exception):
    """Kaynağın yapısı değişti veya erişilemiyor."""
