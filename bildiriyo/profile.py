"""Kişisel profil ve uygunluk kuralları.

Anahtar kelimeler Türkçe karakterlerden arındırılmış küçük harfle yazılır
(ç→c, ğ→g, ı→i, ö→o, ş→s, ü→u). Eşleştirme text.fold() ile yapılır.
"""

# --- Profil -----------------------------------------------------------------
BOLUM = "Yazılım Mühendisliği (lisans)"
DENEYIM_YIL = 0  # belgelenebilir bilişim deneyimi; 3+ olunca bilişim personeli ilanları açılır
ALES_VAR = False  # akademik kadrolar (arş. gör., öğr. gör.) ALES ister
# YDS: yok ama sınava girecek → YDS isteyen ilanlar elenmez.

# --- Başvurulamayan ilanlar (başlık/kategori) ---------------------------------
# (anahtar kelime, sebep). Başlıkta kelime başında geçerse ilan gönderilmez.
SKIP_TITLE = [
    # yeni başvuru almayan duyurular
    ("sonuc ilan", "sonuç duyurusu"), ("sonuclari", "sonuç duyurusu"), ("sonuc duyuru", "sonuç duyurusu"),
    ("iptal", "iptal duyurusu"), ("duzeltme", "düzeltme duyurusu"), ("duzelme", "düzeltme duyurusu"),
    ("erteleme", "erteleme duyurusu"), ("yedek aday", "yedek aday duyurusu"),
    ("sozlu sinav", "sınav duyurusu"), ("mulakat", "sınav duyurusu"),
    # kurum içi
    ("gorevde yukselme", "kurum içi sınav"), ("unvan degisikligi", "kurum içi sınav"),
    ("yeterlik sinavi", "kurum içi sınav"), ("belge basvurusu", "başvuru ilanı değil"),
    # akademik (ALES / doktora gerekir)
    ("ogretim uyesi", "akademik kadro (doktora gerekir)"), ("doktor ogretim", "akademik kadro (doktora gerekir)"),
    ("docent", "akademik kadro"), ("profesor", "akademik kadro"),
    ("ogretim elemani", "akademik kadro (ALES gerekir)"), ("ogretim gorevlisi", "akademik kadro (ALES gerekir)"),
    ("arastirma gorevlisi", "akademik kadro (ALES gerekir)"), ("akademik personel", "akademik kadro"),
    ("ic denetci", "kamu iç denetçi sertifikası ve deneyim gerekir"),
    ("personeli icin", "sadece kurumun kendi personeline yönelik"),
]

# Başka meslek/bölüm gerektiren unvanlar. İlan metni okunabiliyorsa karar metne
# göre verilir (çok kadrolu ilanlarda başka uygun kadro olabilir); okunamıyorsa elenir.
SKIP_TITLE_NO_TEXT = [
    ("hakim", "hukuk mezunu gerekir"), ("savci", "hukuk mezunu gerekir"), ("avukat", "hukuk mezunu gerekir"),
    ("noter", "hukuk mezunu gerekir"), ("icra mudur", "hukuk/iktisat mezunu gerekir"),
    ("tabip", "sağlık mesleği"), ("dis hekim", "sağlık mesleği"), ("hemsire", "sağlık mesleği"),
    ("ebe ", "sağlık mesleği"), ("eczaci", "sağlık mesleği"), ("veteriner", "sağlık mesleği"),
    ("fizyoterapist", "sağlık mesleği"), ("diyetisyen", "sağlık mesleği"), ("psikolog", "farklı bölüm"),
    ("saglik personeli", "sağlık mesleği"), ("saglik teknikeri", "sağlık mesleği"),
    ("ogretmen alim", "öğretmenlik (formasyon gerekir)"), ("imam", "din görevlisi"), ("muezzin", "din görevlisi"),
    ("vaiz", "din görevlisi"),
    ("muhasebe", "farklı meslek"), ("sofor", "farklı meslek"), ("kuafor", "farklı meslek"),
    ("asci", "farklı meslek"), ("garson", "farklı meslek"), ("temizlik", "farklı meslek"),
    ("guvenlik gorevlisi", "farklı meslek (sertifika gerekir)"), ("koruma ve guvenlik", "farklı meslek"),
    ("bekci", "farklı meslek"), ("itfaiye", "farklı meslek"), ("elektrikci", "farklı meslek"),
    ("tesisatci", "farklı meslek"), ("kaynakci", "farklı meslek"), ("bahcivan", "farklı meslek"),
]

# Bunlar her durumda elenir (metin olsa da).
SKIP_TITLE += [
    ("astsubay", "önlisans/askeri"), ("uzman erbas", "askeri"), ("sozlesmeli er", "askeri"),
    ("engelli", "engelli kontenjanı"), ("eski hukumlu", "eski hükümlü kontenjanı"),
    ("terorle mucadele", "özel kontenjan"),
]

# Kariyer Kapısı ilan türleri: başvurulamayanlar
SKIP_CATEGORY = [
    "gorevde yukselme", "hakim ve savci", "ogretim uyesi", "ogretim gorevlisi", "arastirma gorevlisi",
    "engelli isci", "eski hukumlu", "yeterlik sinavi", "belge basvurusu",
]

# --- Bölüm uygunluğu (ilan metninde aranır) -----------------------------------
# Biri geçerse "Yazılım Mühendisliği mezunu başvurabilir" sayılır.
BOLUM_OK = [
    r"yazilim muhendis",
    r"bilgisayar muhendis",
    r"bilgisayar bilimleri muhendis",
    r"bilisim sistemleri muhendis",
    # "mühendislik ve fen-edebiyat fakültelerinin bilgisayar, yazılım, ... bölümlerinden"
    r"muhendislik(?: ve [a-z-]+)? fakultelerinin[^.]{0,250}?(?<![a-z])(?:bilgisayar|yazilim)(?:,| ve| bolum| muhendis)",
    r"muhendislik fakultelerinin (?:herhangi|tum|butun)",
    r"muhendislik fakultesi(?:nin|nden)? (?:herhangi|tum)",
    r"(?:herhangi bir|her hangi bir|tum|butun) (?:\w+ ){0,4}(?<!on )(?:lisans|fakulte)",
    r"(?<!on )(?:lisans|fakulte)(?: \w+){0,6} (?:herhangi bir|her hangi bir) (?:bolum|program|dal)",
    # "en az dört yıllık lisans eğitimi veren yükseköğretim kurumlarından mezun olmak":
    # ardından bölüm listesi gelmiyorsa her bölüm kabul edilir.
    r"(?:dort|4)(?: \(dort\))? yillik (?:lisans )?(?:egitim(?:i)? veren )?(?:yuksekogretim kurumlarin(?:dan|in)"
    r"|fakulte(?:lerden| veya yuksekokullardan)|okullardan|universitelerden) (?:veya [^.]{0,80})?mezun",
    r"lisans mezunu olmak \(?(?:herhangi|tum)",
]

# Bölüm uygunluğu metinden kesin anlaşılamıyor ama muhtemel: "kontrol edin" olarak gönderilir.
BOLUM_MAYBE = [
    (r"(?:,|ve) muhendislik(?: ve [a-z-]+)?(?:,| ve| veya| fakulte)", "mühendislik fakültesi mezunları kabul ediliyor görünüyor"),
    (r"(?:fakulte|bolum)[^.]{0,250}?(?<![a-z])(?:yazilim|bilgisayar)(?! (?:programciligi|teknolojisi|teknolojileri|isletmen|kullan|operat|ve ogretim))",
     "kabul edilen bölümler arasında bilgisayar/yazılım geçiyor"),
    (r"tablo(?:da|lar|-?\s?\d)?\W[^.]{0,40}belirtilen", "kabul edilen bölümler ilan ekindeki tabloda"),
    (r"kilavuz(?:un)?da belirtilen (?:[a-z/]+ ){0,5}(?:bolum|program)", "kabul edilen bölümler başvuru kılavuzunda"),
    (r"ek(?:te|-?\d)(?:'?de)? (?:yer alan|belirtilen) (?:[a-z/]+ ){0,4}(?:bolum|program)", "kabul edilen bölümler ilan ekinde"),
]

# Metinde açıkça bölüm/fakülte adı sayılıyorsa "tabloda/kılavuzda belirtilen" ifadesine
# bakılmaz: liste metnin içindedir ve Yazılım Müh. orada yoksa ilan uygun değildir.
NAMED_LIST = (r"[a-z]+ (?:muhendisligi|ogretmenligi)"
              r"|(?:hukuk|iktisat|isletme|siyasal bilgiler|maliye|kamu yonetimi|ekonomi)(?:,| ve| veya)[^.]{0,80}(?:fakulte|bolum|program)")

# İŞKUR işçi ilanları: sadece bu meslek alanları gönderilir (beden işçisi, bulaşıkçı vb. gönderilmez).
ISKUR_MESLEK_OK = r"bilgisayar|yazilim|bilisim|programci|muhendis|veri |sistem|teknik destek|buro memuru|idari"

# İlan metninde bunlar geçiyorsa (ve bölüm uygunsa) yine de "kontrol edin" denir.
CAUTION = [
    (r"en az (?:\d+|bir|iki|uc|dort|bes|alti|yedi) \(?\w*\)? ?yil(?:lik)? (?:\w+ ){0,6}(?:deneyim|tecrube|fiilen)",
     "bazı kadrolar iş deneyimi istiyor"),
    (r"\bales\b", "ALES istenebilir"),
]

# 375 sayılı KHK Ek-6 sözleşmeli bilişim personeli: tüm kadrolar en az 3 yıl deneyim ister.
BILISIM_PERSONELI = [r"bilisim personeli", r"375 sayili (?:kanun hukmunde kararname|khk)(?:\w|\s|')*ek[ -]?6"]

# Metinde 2547 sayılı Kanun + bunlardan biri: akademik kadro ilanı (başlıksız PDF'ler için)
ACADEMIC_BODY = ["ogretim uyesi", "ogretim elemani", "ogretim gorevlisi", "arastirma gorevlisi", "docent", "profesor"]

# Metin yoksa (Kariyer Kapısı) başlıktan uygun sayılanlar
TITLE_OK = [
    "yazilim muhendis", "bilgisayar muhendis", "kpss tercih", "merkezi yerlestirme", "tercih kilavuzu",
]
