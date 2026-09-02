"""
backend_api.py
FastAPI wrapper (job-based / polling) di atas pipeline:
scraping -> cleaning -> dedup -> stemming -> sentimen (lexicon+SVM)
-> topic modeling (LDA) -> keyword/wordcloud -> tren harian.

Jalankan dengan: uvicorn backend_api:app --reload --port 8000
"""

from dotenv import load_dotenv
load_dotenv()  # baca .env di folder ini, isinya GEMINI_API_KEY (buat pelabelan topik pakai AI)

import uuid
import traceback
from io import BytesIO

import pandas as pd
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from news_scraper import get_news_with_full_text
from preprocessing.cleaning import preprocess_dataframe
from preprocessing.stemming import stem_dataframe
from sentiment_model import classify_dataframe
from topic_modeling import run_topic_modeling
from deduplication import semantic_deduplicate
from keyword_analysis import get_top_keywords, get_top_ngrams

app = FastAPI(title="Sentimen Analisis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "https://dashboardsentimen.up.railway.app/",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs = {}


class AnalysisRequest(BaseModel):
    year: int
    month: str
    keyword: str
    limit: int = 100


class AnalysisStatus(BaseModel):
    job_id: str
    status: str
    progress_note: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


def _compute_daily_trend(df: pd.DataFrame) -> list:
    try:
        tanggal_parsed = pd.to_datetime(df["tanggal"], errors="coerce", dayfirst=True)
        trend_df = df.assign(
            _tanggal=tanggal_parsed.dt.date,
            _sentiment=df["sentiment"].str.lower(),
        )
        trend_df = trend_df.dropna(subset=["_tanggal"])
        if len(trend_df) == 0:
            return []

        pivot = trend_df.pivot_table(
            index="_tanggal", columns="_sentiment", values="judul",
            aggfunc="count", fill_value=0,
        ).sort_index()

        trend = []
        for date_idx, row in pivot.iterrows():
            trend.append({
                "day": date_idx.strftime("%d"),
                "berita": int(row.sum()),
                "positif": int(row.get("positif", 0)),
                "negatif": int(row.get("negatif", 0)),
                "netral": int(row.get("netral", 0)),
            })
        return trend
    except Exception:
        return []


def run_analysis_job(job_id: str, year: int, month: str, keyword: str, limit: int):

    try:
        print(f"[JOB {job_id[:8]}] MULAI: keyword={keyword}, year={year}, month={month}, limit={limit}")
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress_note"] = "Mengambil dan memvalidasi berita..."

        def progress_callback(done, total):
            jobs[job_id]["progress_note"] = f"Mendapatkan {done}/{total} berita (teks lengkap)..."

        df, jumlah_didapat, total_pool = get_news_with_full_text(
            year, month, keyword,
            target_limit=limit, max_workers=10, progress_callback=progress_callback,
        )
        print(f"[JOB {job_id[:8]}] Scraping selesai: {len(df)} baris")

        if len(df) == 0:
            jobs[job_id]["status"] = "done"
            jobs[job_id]["result"] = {"total_berita": 0, "message": "Tidak ada berita ditemukan."}
            return

        jobs[job_id]["progress_note"] = "Membersihkan teks..."
        df = preprocess_dataframe(df, search_keyword=keyword, custom_stopwords_input="")

        jumlah_sebelum = len(df)

        jobs[job_id]["progress_note"] = "Menghapus duplikat..."
        df["judul_norm"] = df["judul"].str.strip().str.lower()
        df = df.drop_duplicates(subset=["judul_norm", "source"], keep="first")
        df = df.drop(columns=["judul_norm"])
        jumlah_setelah_exact = len(df)

        df = semantic_deduplicate(df, text_column="clean_text", threshold=0.85)
        jumlah_sesudah = len(df)
        print(f"[JOB {job_id[:8]}] Setelah dedup: {jumlah_sesudah} baris")

        jobs[job_id]["progress_note"] = "Normalisasi & stemming kata..."
        df = stem_dataframe(df, source_column="clean_text")

        jobs[job_id]["progress_note"] = "Menganalisis sentimen (lexicon + SVM)..."
        df, validation = classify_dataframe(df, tokens_column="tokens_stemmed", text_column="text_final")
        jobs[job_id]["progress_note"] = "Memvalidasi performa model (accuracy, precision, recall, F1)..."
        counts = df["sentiment"].str.lower().value_counts()
        n_pos = int(counts.get("positif", 0))
        n_neg = int(counts.get("negatif", 0))
        n_net = int(counts.get("netral", 0))
        n_total = len(df)
        print(f"[JOB {job_id[:8]}] Sentimen: pos={n_pos}, neg={n_neg}, net={n_net}")

        jobs[job_id]["progress_note"] = "Mencari topik (LDA) & memberi nama tema pakai AI..."
        df, lda_topics, categories = run_topic_modeling(df, tokens_column="tokens_stemmed")

        all_texts = df["text_final"].dropna().astype(str).tolist()
        # Unigram di-ambil lebih banyak (bukan cuma 15) khusus buat wordcloud -
        # wordcloud "mainnya" di ukuran teks (makin sering muncul, makin
        # besar), jadi butuh lebih banyak variasi kata biar kelihatan bedanya.
        top_keywords = get_top_keywords(all_texts, top_k=100)
        top_bigrams = get_top_ngrams(all_texts, ngram_range=(2, 2), top_k=15)
        top_trigrams = get_top_ngrams(all_texts, ngram_range=(3, 3), top_k=15)

        scrape_status_counts = (
            df["scrape_status_label"].value_counts().to_dict()
            if "scrape_status_label" in df.columns else {}
        )

        jobs[job_id]["progress_note"] = "Menyusun tren harian..."
        trend = _compute_daily_trend(df)

        jobs[job_id]["progress_note"] = "Menyusun ringkasan & laporan hasil analisis..."  # BARU

        articles = []
        for _, row in df.iterrows():
            articles.append({
                "tanggal": str(row.get("tanggal", "")),
                "judul": str(row.get("judul", "")),
                "source": str(row.get("source", "")),
                "url": str(row.get("url", "")),
                "content": str(row.get("content", "")),
                "clean_text": str(row.get("clean_text", "")),
                "text_final": str(row.get("text_final", "")),
                "sentiment": str(row.get("sentiment", "")),
                "sentiment_score": float(row.get("sentiment_score", 0)),
                "label_topik": str(row.get("label_topik", "")),
                "is_full_text": bool(row.get("is_full_text", False)),
                "scrape_status_label": str(row.get("scrape_status_label", "")),
            })

        print(f"[JOB {job_id[:8]}] SELESAI! {n_total} artikel...")
        jobs[job_id]["status"] = "done"
        jobs[job_id]["result"] = {
            "total_berita": n_total,
            "jumlah_didapat": jumlah_didapat,
            "total_pool_dicoba": total_pool,
            "jumlah_sebelum_dedup": jumlah_sebelum,
            "jumlah_setelah_exact_dedup": jumlah_setelah_exact,
            "jumlah_setelah_semantic_dedup": jumlah_sesudah,
            "sentiment_counts": {"positif": n_pos, "negatif": n_neg, "netral": n_net},
            "top_keywords": [{"kata": w, "frekuensi": f} for w, f in top_keywords],
            "top_bigrams": [{"kata": w, "frekuensi": f} for w, f in top_bigrams],
            "top_trigrams": [{"kata": w, "frekuensi": f} for w, f in top_trigrams],
            "scrape_status_counts": scrape_status_counts,
            "trend": trend,
            "validation": validation,
            "categories": categories,
            "lda_topics": lda_topics,
            "articles": articles,
        }

    except Exception as e:
        err_detail = traceback.format_exc()
        print(f"[JOB {job_id[:8]}] ERROR: {e}")
        print(err_detail)
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


@app.post("/api/analyze", response_model=AnalysisStatus)
def start_analysis(req: AnalysisRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending", "progress_note": None, "result": None, "error": None}
    background_tasks.add_task(run_analysis_job, job_id, req.year, req.month, req.keyword, req.limit)
    return AnalysisStatus(job_id=job_id, status="pending")


@app.get("/api/analyze/{job_id}", response_model=AnalysisStatus)
def get_analysis_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return AnalysisStatus(job_id=job_id, status="error", error="Job tidak ditemukan.")
    return AnalysisStatus(
        job_id=job_id, status=job["status"],
        progress_note=job.get("progress_note"), result=job.get("result"), error=job.get("error"),
    )


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/analyze/{job_id}/export")
def export_analysis_excel(job_id: str):
    """Ekspor hasil analisis (job yang sudah 'done') jadi file Excel multi-sheet."""
    job = jobs.get(job_id)
    if not job or job["status"] != "done" or not job.get("result"):
        return JSONResponse(
            status_code=404,
            content={"error": "Hasil analisis tidak ditemukan atau belum selesai."},
        )

    result = job["result"]
    if not result.get("total_berita"):
        return JSONResponse(
            status_code=400,
            content={"error": "Tidak ada data untuk diekspor."},
        )

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # --- Sheet 1: Ringkasan ---
        sc = result.get("sentiment_counts", {}) or {}
        ringkasan_rows = [
            ("Total berita (sebelum dedup)", result.get("jumlah_sebelum_dedup")),
            ("Total kandidat dicoba", result.get("total_pool_dicoba")),
            ("Berhasil di-scrape", result.get("jumlah_didapat")),
            ("Setelah dedup exact", result.get("jumlah_setelah_exact_dedup")),
            ("Setelah dedup semantic", result.get("jumlah_setelah_semantic_dedup")),
            ("Total berita final", result.get("total_berita")),
            ("Sentimen Positif", sc.get("positif")),
            ("Sentimen Negatif", sc.get("negatif")),
            ("Sentimen Netral", sc.get("netral")),
        ]
        pd.DataFrame(ringkasan_rows, columns=["Metrik", "Nilai"]).to_excel(
            writer, sheet_name="Ringkasan", index=False
        )

        # --- Sheet 2: Berita ---
        articles_df = pd.DataFrame(result.get("articles", []))
        if not articles_df.empty:
            cols = [
                "tanggal", "judul", "source", "sentiment", "sentiment_score",
                "label_topik", "url", "content", "text_final",
            ]
            cols = [c for c in cols if c in articles_df.columns]
            articles_df[cols].to_excel(writer, sheet_name="Berita", index=False)

        # --- Sheet 3: Kata Kunci ---
        kw_df = pd.DataFrame(result.get("top_keywords", []))
        if not kw_df.empty:
            kw_df.to_excel(writer, sheet_name="Kata Kunci", index=False)

        # --- Sheet 4: Topik LDA ---
        lda_df = pd.DataFrame(result.get("lda_topics", []))
        if not lda_df.empty:
            lda_df = lda_df.copy()
            lda_df["terms"] = lda_df["terms"].apply(lambda t: ", ".join(t))
            lda_df.to_excel(writer, sheet_name="Topik LDA", index=False)

        # --- Sheet 5: Validasi Model ---
        validation = result.get("validation") or {}
        val_rows = [
            ("Model dilatih?", validation.get("trained")),
            ("Accuracy", validation.get("accuracy")),
            ("Precision", validation.get("precision")),
            ("Recall", validation.get("recall")),
            ("F1-score", validation.get("f1")),
            ("Jumlah data latih", validation.get("train_size")),
            ("Jumlah data uji", validation.get("test_size")),
            ("Catatan", validation.get("note")),
        ]
        pd.DataFrame(val_rows, columns=["Metrik", "Nilai"]).to_excel(
            writer, sheet_name="Validasi Model", index=False
        )

    buffer.seek(0)
    filename = f"sentimen_analisis_{job_id[:8]}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
