# 🎬 Media Tracker

Kişisel film, dizi ve anime takip galerisi — Letterboxd tarzı poster duvarı ve analitik paneli.

**Sıfır bağımlılık.** Python standart kütüphanesi + SQLite. Pip install gerektirmez.

---

## ✨ Özellikler

- **Poster Galerisi** — Letterboxd tarzı grid poster duvarı
- **TMDB & IMDb Entegrasyonu** — Çift kaynaklı film/dizi arama, otomatik poster indirme, metadata çekme
- **Rastgele Keşif Ruleti** — Yerel arşivden, TMDB trendlerinden veya IMDb klasiklerinden rastgele öneri
- **Detay & Fragman Modali** — Poster, özet, türler, oyuncular, yönetmen, sezon takibi, dahili fragman oynatıcı
- **Filtre, Sıralama & Arama** — Tür (film/dizi/anime), durum, puan, yıl, süre, etiket ve favoriler
- **İstatistik & Analitik Dashboard** — Toplam izleme süresi (saat/gün), 30 günlük aktivite, tür oranları, puan dağılımı
- **Dışa Aktarma (Export)** — JSON, CSV ve Letterboxd uyumlu CSV aktarımı
- **REST API** — Tam CRUD (GET/POST/PUT/DELETE)
- **Docker Desteği** — Tek komutla ayağa kalkar
- **Sıfır Bağımlılık** — Sadece Python 3.12+ ve SQLite

---

## 🚀 Hızlı Başlangıç

### Python ile (doğrudan)

```bash
# 1. Klonla & dizine git
git clone https://github.com/caymazyusuf72/filmarchive.git
cd filmarchive

# 2. Web sunucusunu başlat (şemayı otomatik oluşturur)
python3 app.py

# 3. Tarayıcıda aç
# http://127.0.0.1:8766
```

### Docker ile

```bash
# 1. .env dosyasını oluştur
cp .env.example .env
# .env içine TMDB_API_KEY değerini yaz

# 2. Build & çalıştır
docker compose up -d --build

# 3. Tarayıcıda aç
# http://localhost:8766
```

---

## 🔑 TMDB API Key (isteğe bağlı)

TMDB entegrasyonu (film arama, poster indirme) için ücretsiz API anahtarı gerekir:

1. https://www.themoviedb.org/signup → hesap oluştur
2. Settings → API → Request an API Key
3. `.env` dosyasına ekle:

```
TMDB_API_KEY=buraya_api_anahtarını_yaz
```

> TMDB anahtarı olmadan da uygulama çalışır, IMDb ve Cinemeta üzerinden aramalar ve manuel kayıtlar sorunsuz kullanılır.

---

## 🛠️ CLI Kullanımı

```bash
# Web sunucusunu başlat
python3 app.py
python3 app.py serve --host 0.0.0.0 --port 8766

# Veritabanını hazırla & migrasyon
python3 app.py init
python3 app.py migrate

# Kayıtları listele
python3 app.py list
python3 app.py list --kind anime

# Manuel kayıt ekle
python3 app.py add "Inception" --type movie --year 2010 --rating 9 --status completed

# Toplu poster indir
python3 app.py fetch-posters --match-missing
python3 app.py fetch-posters --force

# Dışa aktar
python3 app.py export --format letterboxd > letterboxd.csv
python3 app.py export --format json > backup.json
```

---

## 📡 API Endpoints

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/` | Ana Galeri & Analitik Web Arayüzü |
| GET | `/api/records` | Kayıtları listele (filtre/sıralama/sayfalama) |
| GET | `/api/records/{id}` | Tek kayıt detayı |
| GET | `/api/records/{id}/trailer` | Fragman embed URL'i |
| GET | `/api/records/{id}/similar` | Benzer yapım önerileri |
| GET | `/api/summary` | İstatistik ve analitik özeti |
| GET | `/api/random` | Rastgele film/dizi seçici |
| GET | `/api/person/movies` | Oyuncu/yönetmen filmografisi |
| GET | `/api/export` | JSON / CSV / Letterboxd aktarımı |
| GET | `/health` | Sağlık kontrolü |
| POST | `/api/records` | Yeni kayıt ekle |
| POST | `/api/system/optimize` | SQLite VACUUM & optimize |
| POST | `/api/tmdb/search` | TMDB'de ara |
| POST | `/api/tmdb/import/{id}` | TMDB'den import et |
| POST | `/api/imdb/search` | IMDb'de ara |
| POST | `/api/imdb/import/{id}` | IMDb'den import et |
| PUT | `/api/records/{id}` | Kayıt güncelle |
| DELETE | `/api/records/{id}` | Kayıt sil |

---

## 📁 Proje Yapısı

```
filmarchive/
├── app.py              # Tüm Backend, REST API, CLI, TMDB & IMDb (Birleşik Tek Dosya)
├── schema.sql          # SQLite temel şeması
├── templates/
│   └── gallery.html    # Modern Galeri ve Analitik Arayüzü
├── static/
│   ├── gallery.js      # Frontend JavaScript
│   ├── main-logo.svg   # Logo
│   ├── tailwind.min.css # CSS
│   └── posters/        # İndirilen poster görselleri
├── data/               # SQLite veritabanı (media.sqlite)
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

---

## 📜 Lisans

MIT — Detaylar için [LICENSE](LICENSE) dosyasına bakın.
