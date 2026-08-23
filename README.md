# 🎬 Media Tracker

Kişisel film, dizi ve anime takip galerisi — Letterboxd tarzı poster duvarı.

**Sıfır bağımlılık.** Python standart kütüphanesi + SQLite. Pip install gerekmez.

---

## ✨ Özellikler

- **Poster Galerisi** — Letterboxd tarzı grid poster duvarı
- **TMDB Entegrasyonu** — Film/dizi arama, otomatik poster indirme, metadata çekme
- **Manuel Ekleme** — TMDB olmadan da kayıt ekleyebilirsin
- **Detay Modali** — Poster, overview, genres, sezon takibi, TMDB puanı
- **Filtre & Sıralama** — Tür (film/dizi/anime), durum, puan, yıl
- **İstatistik Dashboard** — Toplam kayıt, ortalama puan, puan dağılımı
- **REST API** — Tam CRUD (GET/POST/PUT/DELETE)
- **Docker Desteği** — Tek komutla ayağa kalk
- **Sıfır Bağımlılık** — Sadece Python 3.12+ ve SQLite

---

## 🚀 Hızlı Başlangıç

### Python ile (doğrudan)

```bash
# 1. Klonla
git clone https://github.com/KULLANICI/filmarchive.git
cd filmarchive

# 2. Veritabanını oluştur ve örnek verilerle doldur
python cli.py seed

# 3. Galeri sunucusunu başlat
python gallery.py

# 4. Tarayıcıda aç
# http://127.0.0.1:8766
```

### Docker ile

```bash
# 1. .env dosyasını oluştur
cp .env.example .env
# .env içine TMDB_API_KEY değerini yaz

# 2. Build & çalıştır
docker compose up -d

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

> TMDB anahtarı olmadan da uygulama çalışır, sadece TMDB arama ve otomatik poster indirme devre dışı kalır.

---

## 🛠️ CLI Kullanımı

```bash
# Veritabanı oluştur
python cli.py init

# Örnek verilerle doldur
python cli.py seed

# Kayıtları listele
python cli.py list
python cli.py list --kind anime

# Manuel kayıt ekle
python cli.py add "Inception" --type movie --year 2010 --rating 9 --status completed

# Şema migrasyonu
python cli.py migrate

# Toplu poster indir (TMDB key gerekir)
python fetch_posters.py --match-missing
python fetch_posters.py --force
```

---

## 📡 API Endpoints

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/records` | Kayıtları listele (filtre/sıralama/sayfalama) |
| GET | `/api/records/{id}` | Tek kayıt detayı |
| GET | `/api/summary` | İstatistik özeti |
| GET | `/health` | Sağlık kontrolü |
| POST | `/api/records` | Yeni kayıt ekle |
| PUT | `/api/records/{id}` | Kayıt güncelle |
| DELETE | `/api/records/{id}` | Kayıt sil |
| POST | `/api/tmdb/search` | TMDB'de ara |
| POST | `/api/tmdb/import/{tmdb_id}` | TMDB'den import et |

---

## 📁 Proje Yapısı

```
filmarchive/
├── gallery.py          # HTTP sunucu + REST API
├── cli.py              # Veritabanı katmanı + CLI
├── tmdb.py             # TMDB API istemcisi
├── fetch_posters.py    # Toplu poster indirici
├── schema.sql          # SQLite şeması (v2 base)
├── templates/
│   └── gallery.html    # Ana galeri şablonu
├── static/
│   ├── gallery.js      # Frontend JavaScript
│   ├── main-logo.svg   # Logo
│   └── posters/        # İndirilen poster görselleri
├── data/               # SQLite veritabanı (gitignore)
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
