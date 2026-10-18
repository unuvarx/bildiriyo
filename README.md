# Bildiriyo

Kamu ilanlarını tarayıp yenilerini Telegram grubuna gönderen ücretsiz bot.
GitHub Actions üzerinde her 20 dakikada bir çalışır, sunucu gerekmez.

## Taranan kaynaklar

| Kaynak | Ne alınıyor |
|---|---|
| kariyerkapisi.gov.tr | Tüm aktif ilanlar (API) |
| ilan.gov.tr | "Personel Alımı" türündeki tüm ilanlar (API) |
| resmigazete.gov.tr | Çeşitli İlânlar bölümündeki personel ilanları (PDF içeriği okunur, son 3 gün) |
| kamuilan.sbb.gov.tr | Tüm aktif ilanlar |
| iskur.gov.tr | e-Şube'deki kamu işyeri ilanları + İŞKUR'un kendi personel alım duyuruları |
| yerelyonetimler.csb.gov.tr | Belediye alım ilanı duyuruları |

## Mesaj türleri

- 🟢 **Size uygun olabilir**: bilişim, yazılım, bilgisayar mühendisliği, "tüm lisans bölümleri", KPSS P3 vb.
- 🟡 **Yeni kamu ilanı**: uygunluğu başlıktan anlaşılamayan ilanlar (her biri ayrı mesaj).
- ⚪ **Muhtemelen uygun değil**: öğretim üyesi, sağlık, askeri, iptal/sonuç duyuruları vb.
  Bunlar atılmaz, her çalışmada tek bir özet mesajda toplanır.
- ⚠️ Bir site 3 kez üst üste (~1 saat) taranamazsa uyarı gelir.
- 🤖 Her sabah 09:00'dan sonra günlük durum mesajı gelir. **Bu mesaj gelmezse bot durmuş demektir.**

Bir ilan yalnızca Telegram'a başarıyla gönderildikten sonra "görüldü" sayılır;
gönderim başarısız olursa sonraki çalışmada tekrar denenir.

Filtreleri değiştirmek için: `bildiriyo/profile.py`

## Kurulum

1. **Telegram botu:** Telegram'da @BotFather → `/newbot` → token'ı kopyalayın.
2. **Grup:** Bir grup açın, botu ekleyin, gruba herhangi bir mesaj yazın.
   Sonra tarayıcıda `https://api.telegram.org/bot<TOKEN>/getUpdates` adresini açın,
   `"chat":{"id":-100...}` değerini kopyalayın (eksi işaretiyle birlikte).
3. **GitHub:** Bu klasörü **public** bir repoya gönderin (public repoda Actions sınırsız ücretsiz).
4. Repo → Settings → Secrets and variables → Actions → New repository secret:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Repo → Actions → "İlan kontrolü" → **Run workflow** ile ilk çalıştırmayı yapın.
   İlk çalıştırmada her kaynak için şu an açık ilanların özeti gelir; sonrasında sadece yeniler.

## Yerelde test

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m bildiriyo              # token yoksa mesajları ekrana yazar
.venv/bin/python -m bildiriyo kamuilan     # sadece bir kaynak
```

Yerel test `state/state.json` dosyası oluşturur; repoya göndermeden önce silin.
