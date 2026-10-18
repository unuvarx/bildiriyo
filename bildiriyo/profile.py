"""Kişisel filtre ayarları. İlanlar ASLA tamamen atılmaz; sadece önceliklendirilir.

Anahtar kelimeler Türkçe karakterlerden arındırılmış küçük harfle yazılır
(ç→c, ğ→g, ı→i, ö→o, ş→s, ü→u). Eşleştirme text.fold() ile yapılır.
"""

# 🟢 Doğrudan size uygun: bunlardan biri geçerse ilan "UYGUN" olarak işaretlenir.
STRONG = [
    "yazilim",
    "bilgisayar muhendis",
    "bilisim",
    "bilgi islem",
    "bilgi teknolojileri",
    "programci",
    "siber guvenlik",
    "veri analist",
    "veri bilim",
    "yapay zeka",
    "sistem yonetici",
    "ag yonetici",
    "375 sayili",  # sözleşmeli bilişim personeli KHK'si
    "herhangi bir lisans",
    "tum lisans",
    "lisans mezunu olmak",
    "kpss p3",
    "kpssp3",
]

# ⚪ Muhtemelen uygun değil (doktora, sağlık, askeri, kurum içi vb.).
# Yine de bildirilir, ama tek tek değil toplu özet mesajında.
UNLIKELY = [
    "ogretim uyesi",
    "doktor ogretim",
    "docent",
    "profesor",
    "tabip",
    "hemsire",
    "ebe ",
    "eczaci",
    "veteriner",
    "dis hekim",
    "fizyoterapist",
    "diyetisyen",
    "subay",
    "astsubay",
    "uzman erbas",
    "sozlesmeli er",
    "hakim",
    "savci",
    "gorevde yukselme",
    "unvan degisikligi",
    "engelli isci",
    "eski hukumlu",
    "pdf taranmis",  # Resmî Gazete'de içeriği okunamayan PDF
]

# Yeni başvuru almayan duyurular: her zaman ⚪ (RESCUE uygulanmaz).
NOTICE = [
    "sonuc ilan",
    "sonuclari",
    "iptal ilan",
    "ilan iptali",
    "iptali ilan",
    "duzeltme ilan",
]

# Başlık kararsızsa ilan METNİNE bakılır. Metinde bunlar varsa akademik
# kadro ilanıdır (doktora gerekir) → ⚪; ancak BODY_RESCUE varsa 🟡.
BODY_UNLIKELY = [
    "ogretim uyeligi",
    "ogretim uyesi",
    "doktor ogretim",
]
BODY_RESCUE = [
    "arastirma gorevlisi",
    "ogretim gorevlisi",
]

# UNLIKELY eşleşse bile bunlardan biri varsa 🟡'ye yükseltilir
# (örn. "mühendis sınıfı muvazzaf subay" yazılım mühendisine açık olabilir).
RESCUE = [
    "muhendis",
]
