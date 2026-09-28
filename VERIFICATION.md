# Doğrulama — 28 Eylül 2026

- Python 3.12 ortamında 8 pytest testi geçti.
- Risk bazlı lot ve maksimum ağırlık/nakit sınırları kontrol edildi.
- Alım/satım sonrası nakit = başlangıç + gerçekleşen net K/Z eşitliği doğrulandı.
- Gap-stop gerçekleşmesi ve aynı mumda stop önceliği kontrol edildi.
- Kısmi kâr alımlarında toplam lotun korunması kontrol edildi.
- Gelecekteki mumları değiştirmek geçmiş sinyali değiştirmedi.
- Yanlış ayarlar ve mevcut verinin dışındaki tarih istekleri reddedildi.
- API üzerinden 100 sembol, demo alım, mükerrer alım reddi, demo satış, geçmiş, sıfırlama ve WebSocket mesajı kontrol edildi.
- 100 sembollük 1 aylık backtest çalıştırıldı; muhasebe sonucu alındı.
- Varsayılan 4 kombinasyonlu train/validation/test optimizasyonu çalıştırıldı; 4 aday ve bağımsız test sonucu üretildi.
- `npm run build` başarılı: Next.js 15.5.26, TypeScript kontrolü ve üretim sayfası derlemesi geçti.

## Doğrulanamayanlar

Bu ortamda Chromium indirmesi başarısız olduğu için ekran görüntüsü, tarayıcı etkileşimleri ve mobil görsel kalite doğrulanamadı. Docker Compose başlatma işlemi burada çalıştırılmadı. Dockerfile ve komutlar teslimata dahildir; Docker Desktop üzerinde ilk kurulum testini kullanıcı yapmalıdır.

Bu kontroller gerçek piyasa verisinde kârlılık veya strateji geçerliliğini doğrulamaz. Gerçek veri sağlayıcısı, walk-forward, çok kullanıcılı kullanım ve broker bağlantısı teslimata dahil değildir.
