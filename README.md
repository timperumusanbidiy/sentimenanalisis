# Sentimen Analisis Berita Ekonomi Indonesia
 
**Dashboard scraping & analisis sentimen berita ekonomi Indonesia** (fokus wilayah D.I. Yogyakarta) dari Google News, lengkap dengan topic modeling, wordcloud, tren harian, dan laporan Excel otomatis.

### Alur kerja detail
 
1. User mengisi form pada dashboard, meliputi tahun, bulan, keyword, dan jumlah berita yang ingin dianalisis. Setelah form dikirim, frontend melakukan `POST /api/analyze`.
2. Backend langsung mengembalikan `job_id` dan menjalankan proses analisis sebagai background task. Dengan cara ini, request tidak perlu menunggu seluruh proses selesai karena beberapa tahapan, seperti pengambilan berita dan pemodelan LDA, membutuhkan waktu cukup lama.
3. Frontend melakukan polling ke `GET /api/analyze/{job_id}` secara berkala untuk memantau status proses. Selama analisis berlangsung, pengguna dapat melihat informasi progres melalui `progress_note`, misalnya "Menghapus duplikat..." atau "Mencari topik (LDA)...".
4. Setelah proses selesai, hasil analisis ditampilkan dalam bentuk dashboard interaktif menggunakan Recharts. Informasi yang ditampilkan meliputi distribusi sentimen, tren sentimen harian, keyword teratas, hasil pemodelan topik LDA, serta tabel berita yang dianalisis.
5. User dapat mengunduh hasil analisis melalui `GET /api/analyze/{job_id}/export`. Laporan yang dihasilkan berupa file Excel dengan lima sheet, yaitu ringkasan, berita, kata kunci, topik LDA, dan validasi model.
>  **Model sentimen:** Sistem menyediakan dua mode pemodelan sentimen. Jika folder model/ sudah berisi model hasil training dari `train_model.py`, model tersebut akan digunakan. Model ini dilatih menggunakan `golden_dataset.csv` yang berisi data dengan label sentimen hasil anotasi manusia. Jika model tersebut belum tersedia, sistem akan menggunakan `sentiment_svm.py` sebagai fallback. Pada mode ini, model dilatih ulang pada setiap proses analisis menggunakan label yang berasal dari lexicon InSet. Dengan demikian, dashboard tetap dapat digunakan meskipun belum tersedia model hasil anotasi manusia.

---

## Tech Stack
 
| Layer | Teknologi |
|---|---|
| **Backend** | Python, FastAPI, pandas, scikit-learn, gensim (LDA), Sastrawi (stemmer & stopword ID), trafilatura, feedparser, `google-generativeai` (Gemini), openpyxl |
| **Frontend** | React 19, TanStack Start & Router, Vite, Tailwind CSS, shadcn/ui, recharts |
| **Model** | Lexicon **InSet** (Koto & Rahmaningtyas, 2017) + SVM (TF-IDF unigram+bigram) |
| **Deploy** | Railway (backend, `railpack.json`), Lovable/Vite (frontend) |

---

## Struktur File
 
```text
sentimenanalisis-main/
├── AGENTS.md                     # Catatan buat AI agent (Lovable) soal git history project
├── package.json                  # Dependency & script frontend
├── vite.config.ts                # Konfigurasi build Vite + TanStack Start + Tailwind
├── tsconfig.json                 # Konfigurasi TypeScript
├── components.json               # Konfigurasi shadcn/ui
│
├── backend/                      # Semua logic Python: scraping, NLP, ML, API
│   ├── backend_api.py            # Entry point FastAPI — semua endpoint REST
│   ├── news_scraper.py           # Scraping daftar berita dari RSS Google News
│   ├── article_parser.py         # Ambil isi teks lengkap tiap artikel (trafilatura)
│   ├── deduplication.py          # Hapus berita duplikat/mirip (cosine similarity TF-IDF)
│   ├── sentiment_model.py        # Loader model sentimen terlatih (+ fallback)
│   ├── sentiment_svm.py          # Sentimen: lexicon InSet + SVM (retrain per-request)
│   ├── topic_modeling.py         # Topic modeling LDA + penamaan topik via Gemini
│   ├── keyword_analysis.py       # Top keyword, n-gram, wordcloud
│   ├── requirements.txt          # Dependency Python backend
│   ├── railpack.json             # Konfigurasi deploy Railway
│   ├── .env.example              # Contoh isi .env (GEMINI_API_KEY)
│   │
│   ├── preprocessing/
│   │   ├── cleaning.py           # Lowercase, buang HTML/URL/simbol, stopword awal
│   │   └── stemming.py           # Normalisasi slang, stemming Sastrawi, stopword lanjutan
│   │
│   ├── tools/                    # Script CLI (dijalankan manual, bukan lewat API)
│   │   ├── evaluate_manual.py    # Bikin sample label manual + hitung akurasi vs model
│   │   └── train_model.py        # Latih & simpan model SVM final dari golden_dataset.csv
│   │
│   ├── lexicon/
│   │   ├── positive.tsv          # Kamus sentimen positif InSet Lexicon
│   │   └── negative.tsv          # Kamus sentimen negatif InSet Lexicon
│   │
│   ├── model/                    # Model hasil training (auto-generated)
│   │   ├── svm_model.joblib
│   │   ├── tfidf_vectorizer.joblib
│   │   └── validation_metrics.json
│   │
│   └── golden_dataset.csv        # Data berita berlabel manusia (training & validasi)
│
└── src/                           # Frontend React (TanStack Start)
    ├── router.tsx                 # Setup TanStack Router
    ├── server.ts / start.ts       # Entry point SSR
    ├── styles.css                 # Style global (Tailwind)
    │
    ├── routes/
    │   ├── __root.tsx              # Root layout
    │   ├── index.tsx               # Landing page
    │   └── dashboard.tsx           # Halaman utama: form, chart, tabel, ekspor Excel
    │
    ├── components/ui/             # Komponen shadcn/ui (button, card, chart, dst)
    ├── hooks/use-mobile.tsx       # Hook deteksi layar mobile
    ├── lib/                        # Helper umum & error handling
    └── assets/                    # Gambar, logo, video landing page
```
 
---

## Penjelasan File Backend
 
### `backend_api.py`
Entry point FastAPI. Endpoint yang tersedia:
 
| Method | Endpoint | Fungsi |
|---|---|---|
| `POST` | `/api/analyze` | Mulai job analisis baru (`year`, `month`, `keyword`, `limit`), balikin `job_id` |
| `GET` | `/api/analyze/{job_id}` | Cek status job (`pending`/`processing`/`done`/`error`) + progress & hasil |
| `GET` | `/api/analyze/{job_id}/export` | Unduh laporan Excel 5 sheet |
| `GET` | `/api/health` | Health check |
 
`run_analysis_job()` adalah orkestrator utama yang menjalankan seluruh pipeline secara berurutan sambil update `progress_note` di tiap tahap.
 
### `news_scraper.py`
Cari berita dari **RSS Google News** berdasarkan keyword + rentang tanggal. Decode URL asli artikel (pakai `googlenewsdecoder`), lalu ambil isi teks lengkap secara **paralel** (`ThreadPoolExecutor`).
 
### `article_parser.py`
Ekstrak isi teks lengkap dari URL artikel pakai `trafilatura`, dengan retry. Ada filter `looks_like_google_ui()` buat deteksi hasil scraping yang cuma "nyangkut" di tampilan UI Google News, bukan isi berita asli.
 
### `deduplication.py`
`semantic_deduplicate()` — hapus berita yang **mirip** (bukan cuma identik) pakai TF-IDF + cosine similarity (threshold default `0.85`).
 
### `preprocessing/cleaning.py`
Tahap pembersihan awal: unescape HTML → buang tag/URL → lowercase → buang karakter non-alfanumerik → stopword removal pertama.
 
### `preprocessing/stemming.py`
Tokenisasi → normalisasi slang (`gak`→`tidak`, `yg`→`yang`, dst) → stemming **Sastrawi** (di-cache per kata unik) → stopword removal tahap dua (khusus kata generik hasil stemming, misal "mengatakan" → "kata").
 
### `sentiment_svm.py`
Skor tiap berita pakai **InSet Lexicon** (3.609 kata positif + 6.609 kata negatif) → label lexicon dipakai buat melatih **SVM** (TF-IDF unigram+bigram) → SVM dievaluasi via train/test split. Metrik di sini ngukur konsistensi ke lexicon, **bukan** akurasi ke label manusia.
 
### `sentiment_model.py`
Dipanggil `backend_api.py` untuk prediksi sehari-hari. Prioritas: **model terlatih** dari `model/` (kalau ada) → fallback ke `sentiment_svm.py`.
 
### `topic_modeling.py`
LDA (gensim): coba beberapa kandidat jumlah topik (range 3–7, 5 passes), pilih berdasarkan *coherence score* (c_v) terbaik. Nama topik dibuat pakai **Gemini** (fallback ke label statistik dari kata-kata teratas kalau Gemini tidak tersedia).
 
### `keyword_analysis.py`
`get_top_keywords()`, `get_top_ngrams()` (bigram/trigram), dan `generate_wordcloud_figure()` (warna beda per sentimen: 🟢 positif, 🔴 negatif, 🟡 netral).
 
### `tools/evaluate_manual.py`
CLI buat bikin dataset evaluasi manusia:
```bash
python evaluate_manual.py sample laporan.xlsx --n 100     # bikin sample buat dilabel
python evaluate_manual.py evaluate sample_anotasi_manual.xlsx  # hitung akurasi + simpan ke golden_dataset.csv
```
 
### `tools/train_model.py`
Melatih model SVM final dari `golden_dataset.csv` (label manusia asli), simpan ke `model/*.joblib` + `validation_metrics.json`. **Perlu restart backend** setelah dijalankan.
 
### `lexicon/`
Kamus **InSet Lexicon** (Koto & Rahmaningtyas, 2017), dipakai apa adanya dari [repo aslinya](https://github.com/fajri91/InSet).
 
---

## Penjelasan File Frontend
 
| File | Fungsi |
|---|---|
| `src/routes/index.tsx` | Landing page — penjelasan project, fitur, cara pakai |
| `src/routes/dashboard.tsx` | Halaman utama: form input, polling status job, chart (recharts), tabel artikel, tombol ekspor Excel |
| `src/components/ui/` | Komponen reusable dari [shadcn/ui](https://ui.shadcn.com/) |
| `src/router.tsx`, `server.ts`, `start.ts` | Setup TanStack Router & TanStack Start (SSR) |
 
> **Catatan:** `API_BASE` di `dashboard.tsx` saat ini **hardcoded** ke URL backend produksi (Railway). Buat testing ke backend lokal, ubah dulu ke `http://localhost:8000`.
 
---

## Cara Menjalankan
 
### Backend
 
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # isi GEMINI_API_KEY (opsional, buat penamaan topik otomatis)
uvicorn backend_api:app --reload --port 8000
```
 
### Frontend
 
```bash
npm install      # atau: bun install
npm run dev       # jalan di http://localhost:8080
```
 
---
 
## Melatih Model Sentimen dari Label Manusia
 
```bash
cd backend
python tools/evaluate_manual.py sample laporan.xlsx --n 100
# isi kolom label_manual di sample_anotasi_manual.xlsx pakai Excel
python tools/evaluate_manual.py evaluate sample_anotasi_manual.xlsx
python tools/train_model.py
# restart backend biar model baru ke-load
```
 
> Minimal butuh **30 baris** data berlabel sebelum training dianggap stabil (idealnya **150+**).
 
---

## Referensi
 
- Koto, F. & Rahmaningtyas, G.S. (2017). *InSet Lexicon: Evaluation of a Word List for Indonesian Sentiment Analysis in Microblogs*. IALP 2017 — [github.com/fajri91/InSet](https://github.com/fajri91/InSet)
---
