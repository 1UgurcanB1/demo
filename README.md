# BIST 100 Profit Demo

Next.js + FastAPI ile localhost üzerinde çalışan, 100.000 TL başlangıç bakiyeli paper trading MVP.
**DEMO DATA:** Fiyat, hacim, endeks ve geçmiş verileri tamamen sentetiktir. 100 örnek sembol güncel BIST 100 bileşen listesi iddiası taşımaz. Gerçek broker, gerçek emir veya API anahtarı yoktur. Kâr garantisi verilmez.

## 1. Mimari özeti

Tarayıcıdaki React/TypeScript arayüzü REST üzerinden FastAPI'ye bağlanır. WebSocket durum özeti aktarır; tablolar 7 saniyede yenilenir. Tek süreçte çalışan tarayıcı, strateji ve risk motoru aynı PaperBroker sınıfını kullanır. SQLAlchemy + SQLite, ayarları ve hesabı atomik işlemlerle saklar. Backtest ayrı hesap açar, canlı demo hesabını etkilemez. Backend kapanırsa otomasyon durur; yeniden başlatıldığında güvenli varsayılan olarak OFF olur.

## 2. Dosya ağacı

```text
bist100-profit-demo/
  backend/
    app/
      main.py                  REST, WebSocket, scanner, kayıt koordinasyonu
      config.py                Pydantic doğrulamalı ayarlar
      data/base.py             DataProvider sözleşmesi, mum doğrulama
      data/mock.py             Deterministik 100 sembollük sentetik veriler
      strategy/indicators.py   EMA, RSI, MACD, ROC, ATR, ADX, Bollinger, hacim
      strategy/scoring.py      Rejim, skorlar, çoklu işlem filtreleri
      risk/manager.py          Lot hesabı ve devre kesici
      trading/paper_broker.py  Muhasebe, kısmi çıkış, trailing, stop
      backtest/engine.py       Sıralı geçmiş simülasyonu
      backtest/metrics.py      Performans metrikleri
      backtest/optimizer.py    Train/validation/test grid araması
      database/store.py        SQLAlchemy modelleri ve SQLite işlemleri
    tests/test_engine.py
    tests/test_api.py
    requirements.txt
    Dockerfile
  frontend/
    app/page.tsx               Yedi işlevsel görünüm ve hisse detay penceresi
    app/types.ts              Paylaşılan API veri tipleri
    app/globals.css           Responsive koyu tema
    app/layout.tsx
    components/charts.tsx     Recharts + SVG mum grafiği
    package.json
    package-lock.json
    tsconfig.json
    Dockerfile
  docker-compose.yml
  .env.example
  BASLAT-WINDOWS.bat
  README.md
```

## 3. Backend kurulumu

Python 3.11+ gerekir. İki terminal kullanın.

```bash
cd backend
python -m venv .venv
```

Windows PowerShell: `.venv\Scripts\Activate.ps1`

macOS/Linux: `source .venv/bin/activate`

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Tek worker kullanın; bellek içi scheduler çoklu worker için tasarlanmamıştır. Otomatik tarama sunucu açık kaldıkça sürer.

## 4. Backend kodları

Tüm Python kaynakları `backend/app` içinde eksiksizdir. `main.py`, FastAPI lifespan üzerinden scheduler başlatır. Eşzamanlı hesap değişiklikleri `RLock` ile korunur; ağır backtest istekleri threadpool'a alınır. Otomatik tarama hataları loglanır. Hatalı girişler 422; işlem/risk çatışmaları 409; bulunamayan semboller 404 döndürür.

## 5. Frontend kurulumu

Node.js 22 LTS ve npm kullanın. Ayrı terminal:

```bash
cd frontend
npm ci
npm run dev
```

Tarayıcı: http://localhost:3000. API dokümanı: http://localhost:8000/docs.

## 6. Frontend kodları

Next.js App Router, React, strict TypeScript, Tailwind CSS ve özel tema. Ekranlar aynı rota içinde sekmeli uygulama olarak çalışır. Recharts performans/indikatör grafiklerinde, SVG mum grafiğinde kullanılır. Inter fontu kuruluysa kullanılır; ağdan font yükleme zorunluluğu olmaması için sistem fontuna düşebilir. API erişilemezse bağlantı mesajı gösterilir; WebSocket yeniden bağlanmayı dener.

## 7. Veritabanı modelleri

SQLAlchemy şu tabloları oluşturur: `portfolio`, `positions`, `orders`, `trades`, `signals`, `market_snapshots`, `performance`, `settings`, `backtests`. MVP'de her model integer kimlik ve JSON payload kullanır. Normalize muhasebe şeması değildir. Hesap/pozisyon/emir/geçmiş/ayar snapshot'ları tek transaction ile yazılır. Varsayılan dosya backend çalışma dizinindeki `paper.db` dosyasıdır. Hesap sıfırlama, portföy/pozisyon/emir/işlem/equity kayıtlarını yeniler; geçmiş backtest arşivi korunur.

## 8. Strateji motoru

EMA 9/20/50/200, ayarlanabilir hızlı/yavaş EMA, Wilder tarzı RSI/ATR/ADX, MACD, ROC, Bollinger, önceki 20 seans destek/direnç ve göreli hacim hesaplanır. BULLISH/NEUTRAL/BEARISH rejimi sentetik XU100 üzerinden belirlenir. BEARISH rejiminde yeni otomatik long açılmaz. Trend, momentum, hacim, direnç, aşırı uzama, fırsat/beklenti skoru ve maliyet sonrası R/R birlikte filtrelenir.

Fırsat skoru: trend %25, momentum %20, hacim %15, fiyat hareketi %15, risk/getiri %15, piyasa %10. Ağırlıklar ayarlardan değişir; toplam 100 olmak zorundadır.

Expected Profit Score **heuristik araştırma skorudur**, tahmin edilmiş gerçek getiri değildir. Benzer RSI/trend koşullarındaki tamamlanmış 10 seanslık net pozitif sonuç oranını kullanır. En az 20 örnek yoksa %50 nötr varsayım kullanılır. Bu oran hedefe ulaşma olasılığı veya kalibre edilmiş sinyal güveni değildir. Kullanıcıya örnek sayısı ve açıklama gösterilir. Tamamlanmamış gelecekteki 10 seans sonuçları kullanılmaz.

## 9. Risk motoru

Lot = risk bütçesi / (stop mesafesi + tahmini komisyon ve kayma). Ardından nakit, %10 pozisyon ağırlığı ve tam lota yuvarlama uygulanır. Varsayılanlar: işlem riski %1, en çok 5 pozisyon, seans kayıp limiti %2, portföy drawdown limiti %10. Aynı sembole tekrar alım, kaldıraç ve martingale yoktur. Gap durumunda gerçekleşen zarar planlanan %1'den fazla olabilir.

Limit aşılırsa yeni alımlar durur; koruyucu çıkışlar devam eder. Bu MVP'de limit duraklatması hesap sıfırlanana kadar kilitlidir. Manuel alımlar teknik filtreleri atlar ancak risk, nakit ve pozisyon limitlerini atlamaz.

## 10. Paper trading motoru

Giriş ve çıkışta ayrı komisyon ve kayma uygulanır. Stop gap'inde stop fiyatı yerine daha kötü açılış kullanılır. Aynı OHLC mumunda stop ve hedef görüldüyse stop önceliklidir. Hedef 1'de ilk lotun %30'u, hedef 2'de ilk lotun %30'u kapanır; lotlar aşağı yuvarlanır. Kalan lotlar takip edilir. Hedef sonrası stop maliyetleri içeren başabaşa taşınır; trailing ATR stop güncellenir. Yeni trailing stop takip eden mumdan itibaren aktiftir. EMA50 altında trend çıkışı uygulanır.

Küçük lotlarda kısmi satış 0 lota yuvarlanabilir; aşama ilerler ve kalan lot trailing ile korunur. Manuel satış tüm kalan lotu kapatır. Açık K/Z alış komisyonunu içerir, henüz gerçekleşmemiş satış komisyonunu içermez.

## 11. Scanner

Varsayılan 60 saniyede bir 100 sembol taranır. Her tarama **bir sanal günlük seans** ilerletir; bu canlı BIST verisi değildir. “Bir seans ilerlet” elle aynı işlemi tetikler. Son/sonraki tarama saatleri gerçek duvar saatini, simülasyon tarihi sentetik veri tarihini gösterir. AUTO OFF yeni otomatik alımı durdurur; açık pozisyonların koruyucu çıkışları çalışır. AUTO ON koşullara uygun en yüksek beklenti skorlarını seçer. Şartlar oluşmazsa nakitte kalabilir.

## 12. Backtest

Tarih, sermaye, risk, minimum skor ve R/R seçilir. 210 seans ön veri gerekir. Sinyal önceki kapanışta, gerçekleşme sonraki seans açılışındadır. %3 üzeri açılış gap'i veya giriş öncesi stop ihlali alımı iptal eder; yeni açılışta R/R tekrar kontrol edilir. Son seans sonunda kalan pozisyonlar `BACKTEST END` ile tasfiye edilir. Sonuçlar veritabanında son 20 çalıştırma olarak tutulur.

Komisyon ve kayma dahildir. Sonuçlar sentetik veri üzerindedir; gerçek tarihi BIST backtest'i değildir. Bölünme, temettü, taban/tavan fiyat, likidite, emir kuyruğu ve borsa tatilleri modellenmez. “Başarı” gerçek piyasaya genellenemez.

## 13. Strategy optimizer

Varsayılan grid minimum skor [65,75] ve ATR stop çarpanı [1.5,2.5] için dört kombinasyonu karşılaştırır. Arayüzden EMA dönemleri, RSI eşikleri, minimum fırsat/beklenti skorları, R/R, ATR stop, trailing, kısmi satış oranları ve hedef R çarpanlarına virgülle ayrılmış değerler girilebilir. Boş alanlar mevcut ayarı kullanır. Toplam en fazla 12 kombinasyon kabul edilir; geçersiz kombinasyonlar hata döndürür. Tarih aralığı train %50, validation %25, test %25 bölünür. Train raporlanır, seçim yalnızca validation skoruyla yapılır, seçilen ayar test döneminde bir kez çalıştırılır.

Skor = getiri yüzdesi + 5×sınırlandırılmış profit factor + 3×Sharpe − 2×drawdown + sınırlandırılmış expectancy bileşeni. Minimum 60 seans gerekir. Test dönemleri bağımsız hesapla başlar; önceki dönem mumları indikatör ısınması için kullanılabilir. Seçim otomatik olarak canlı ayarlara uygulanmaz. Walk-forward bu MVP'de yoktur. Grid araması kullanım süresini sınırlamak için en fazla 12 kombinasyondur.

## 14. REST API

| Yöntem | Yol | İşlev |
|---|---|---|
| GET | /api/dashboard | Hesap, risk, tarama özeti |
| GET | /api/stocks | 100 sembolün skorları |
| GET | /api/stocks/{symbol} | Mumlar, indikatörler, sinyal |
| GET | /api/opportunities | Sıralı fırsat listesi |
| GET | /api/positions | Açık pozisyonlar |
| GET | /api/trades | Gerçekleşen sanal kapanışlar |
| GET | /api/performance | Metrikler ve equity eğrisi |
| POST | /api/paper/buy | `{"symbol":"ASELS"}` ile risk bazlı alım |
| POST | /api/paper/sell | `{"symbol":"ASELS"}` ile tüm pozisyonu sat |
| POST | /api/automation/start | Otomatik alımları aç |
| POST | /api/automation/stop | Otomatik alımları kapat |
| POST | /api/scan | Bir sentetik seans ilerlet |
| POST | /api/reset | `{"initial_balance":100000}` ile hesabı sıfırla |
| POST | /api/backtest | Geçmiş simülasyonu |
| POST | /api/optimization | Ayarlanabilir grid araştırması |
| GET / PUT | /api/settings | Ayarları oku/kaydet |

Örnek backtest gövdesi:

```json
{"start":"2025-01-01","end":"2025-06-27","initial_balance":100000,"risk_per_trade":0.01,"min_score":70,"min_rr":2}
```

## 15. WebSocket

`ws://localhost:8000/ws/market` iki saniyede bir dashboard JSON gönderir. Tarayıcı bağlantı kesilince 3 saniye sonra tekrar dener. REST tabloları 7 saniyede bir yenilenir. Dış origin WebSocket istekleri engellenir.

## 16. Dashboard

Portföy, nakit, günlük/toplam K/Z, getiri, pozisyon sayısı, kazanma oranı, profit factor, Sharpe, maksimum düşüş, rejim, tarama zamanları ve sıralanabilir/aranabilir fırsat tablosu. İlk açılışta portföy 100.000 TL ve işlem geçmişi boştur; sahte kazanç gösterilmez.

## 17. Hisse detay ekranı

Sembole basıldığında mum, EMA20/50/200, RSI, MACD, hacim, giriş/stop/hedefler açılır. Destek/direnç seviyeleri API mumlarında ve grafikte bulunur. Açıklama paneli deterministik filtre sonuçlarını gösterir; LLM kullandığı iddia edilmez. Manuel demo alım bu paneldedir.

## 18. Trade history

Alım/satım tarih ve fiyatları, lot, brüt K/Z, iki taraf komisyonu, net K/Z, getiri ve çıkış nedeni. Kısmi çıkışlar ayrı kapanış satırıdır.

## 19. Performance sayfası

Equity, günlük K/Z, drawdown, aylık getiriler; en iyi/kötü işlem, ortalama kazanç/kayıp, expectancy ve diğer metrikler. Kazanma oranı kapanış parçaları bazındadır. Profit factor zarar yoksa tanımsız gösterilir; Sharpe yeterli değişkenlik yoksa tanımsızdır. Risksiz oran 0, yıllık seans sayısı 252 varsayılır. Sharpe/annualized değerler az gözlemde anlamlı olmayabilir.

## 20. Backtest sayfası

Parametreleri girip “Backtest çalıştır” seçin. İlk çalıştırma 100 sembol için donanıma bağlı zaman alır. İşlem boyunca buton devre dışıdır; bitince sonuç kartları, equity ve işlem tablosu görünür.

## 21. Strategy Lab

En az 60 seans seçip optimizasyonu çalıştırın. Train/validation tarihleri, sonuç tablosu ve seçilmiş parametrenin bağımsız test sonuçları gösterilir. Geçmiş sonuçlara aşırı uyum hâlâ mümkündür; sentetik veri değerlendirme amacıyla kullanılır.

## 22. Settings sayfası

Bakiye, risk, pozisyon limitleri, eşikler, ATR, trailing, kısmi satış oranları, tarama aralığı, komisyon/kayma, EMA/RSI ve skor ağırlıkları değişir. Kaydetme SQLite'a yazılır. Hedefler varsayılan 2R ve 3,5R'dir; ayarlardan değişir. Yeni başlangıç bakiyesi hesabı sıfırladığınızda uygulanır. Sıfırlama onay ister. Açık pozisyonların mevcut stop/hedefleri yeni ayarlarla yeniden hesaplanmaz; sonraki yönetim adımları güncel trailing/kısmi çıkış oranlarını kullanır.

## 23. requirements.txt

Python bağımlılıkları `backend/requirements.txt` içindedir. Teknik indikatörler pandas/numpy ile açıkça uygulanmıştır; pandas-ta zorunlu değildir. Test bağımlılıkları aynı dosyadadır.

## 24. package.json

`frontend/package.json` dev/build/start/typecheck komutlarını tanımlar. `package-lock.json` tekrarlanabilir npm kurulumunu sağlar. Kaynak kod TypeScript strict denetiminden geçer.

## 25. .env.example

Kök dosyadaki DATABASE_URL değerini değiştirecekseniz backend/.env içine alın. NEXT_PUBLIC_API_URL değerini frontend/.env.local içine koyun ve frontend'i yeniden derleyin. Bu URL gizli değildir. Secret değerleri NEXT_PUBLIC_ ön ekiyle göndermeyin. Mock provider için anahtar gerekmez.

## 26. README / gerçek veri sağlayıcısı / güvenlik

Yeni provider, `data/base.py` sözleşmesindeki beş metodu uygulamalıdır. `main.py` içindeki provider oluşturmasını ve backtest snapshot oluşturma fabrikasını yeni provider'a bağlayın; strateji/skor/muhasebe kodları değişmez. Gerçek provider önce seans takvimine göre mumları normalize etmeli, timestamp'leri saat dilimiyle doğrulamalı ve güncelliği veri kaynağının beklenen son tamamlanmış seansıyla kontrol etmelidir. Temel doğrulayıcı NaN, mükerrer/sırasız zaman, OHLC tutarsızlığı, yetersiz geçmiş ve timestamp ve endeks seans dizisi uyumsuzluğunu reddeder; 4 günden uzun boşluğu uyarır. Gerçek borsa tatil/eksik seans doğrulaması için sağlayıcıya özgü takvim gerekir. Gerçek veri adaptörü bu teslimata dahil değildir.

Uygulama tek kullanıcılı localhost MVP'dir; kimlik doğrulama/çok kullanıcılı izolasyon yoktur. İnternete açık backend olarak yayınlamayın. Docker portları yalnızca 127.0.0.1'e bağlıdır. Veritabanını düzenli yedekleyin. Gerçek broker kodu mevcut değildir.

## 27. Çalıştırma komutları

En kolay: Docker Desktop açıkken proje klasöründe:

```bash
docker compose up --build -d
```

Windows'ta `BASLAT-WINDOWS.bat` aynı işlemi yapar. Sonra http://localhost:3000 açın. İlk derleme sırasında internet gerekir. Durdurma:

```bash
docker compose down
```

Kalıcı SQLite volume korunur. `down -v` veriyi siler.

Docker olmadan 3. ve 5. bölümlerdeki iki terminali kullanın. Üretim frontend derleme:

```bash
cd frontend
npm run build
npm start
```

Testler:

```bash
cd backend
python -m pytest -q
```

Resmî başvuru dokümanları: https://fastapi.tiangolo.com/advanced/events/ ve https://nextjs.org/docs/app/getting-started/installation.
