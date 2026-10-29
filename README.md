# Bildiriyo

Kamu ilanlarını tarayıp yenilerini Telegram grubuna gönderen ücretsiz bot.
GitHub Actions üzerinde günde bir çalışır, sunucu gerekmez.

## Taranan kaynaklar

| Kaynak | Ne alınıyor |
|---|---|
| kariyerkapisi.gov.tr | Tüm aktif ilanlar (resmi RSS beslemesi) |
| ilan.gov.tr | "Personel Alımı" türündeki tüm ilanlar (API) |
| resmigazete.gov.tr | Çeşitli İlânlar bölümündeki personel ilanları (PDF içeriği okunur, taranmış PDF için OCR, son 7 gün) |
| iskur.gov.tr | e-Şube'deki kamu işyeri ilanlarının tüm sayfaları + İŞKUR'un kendi personel alım duyuruları |

kamuilan.sbb.gov.tr ve yerelyonetimler.csb.gov.tr yurt dışı IP'lerini engellediği için
(GitHub sunucuları ABD'de) kapsam dışında.

## Nasıl çalışır

- Her gün **~18:30**'da (yedekler: 19:40, 20:50, 22:10; GitHub birkaç saat geciktirebilir) 4 kaynak taranır. Daha önce görülmemiş her ilanın
  **metni okunur** ve profilinize göre karar verilir (`bildiriyo/profile.py`):
  - 🟢 **Başvurabilirsiniz**: metinde Yazılım/Bilgisayar Mühendisliği veya "herhangi bir lisans" geçiyor.
  - 🟡 **Şartları kontrol edin**: bölümler ilan ekinde/kılavuzda, deneyim isteyen kadro var
    ya da ilan metni okunamadı (Kariyer Kapısı metni yurt dışından okunamıyor).
  - Gönderilmeyenler: akademik kadrolar (ALES/doktora), sözleşmeli bilişim personeli
    (en az 3 yıl deneyim), farklı bölüm/meslek, iptal/düzeltme/sonuç duyuruları, kurum içi sınavlar.
- Aynı ilan birden fazla kaynakta çıkarsa tek kez gönderilir.
- Her taramadan sonra 🤖 durum mesajı gelir (gönderilen / elenen sayısı). **Gelmezse bot durmuştur.**
- Bir site taranamazsa ⚠️ uyarısı gelir.
- Tarama işi herhangi bir sebeple çökerse ❌ mesajı ve hata kaydının linki gelir.
- Şu an açık tüm uygun ilanların özeti: Actions → "İlan kontrolü" → Run workflow → "özet" kutusunu işaretleyin.

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
.venv/bin/python -m bildiriyo iskur        # sadece bir kaynak
```

Yerel test `state/state.json` dosyası oluşturur; repoya göndermeden önce silin.
