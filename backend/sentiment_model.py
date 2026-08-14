"""
sentiment_model.py
Modul yang dipakai backend_api.py buat prediksi sentimen SEHARI-HARI
(dipanggil tiap ada analisis baru dari dashboard).

INI BEDA dari sentiment_svm.py: di sini model TIDAK dilatih ulang tiap
request. Model dilatih SEKALI lewat train_model.py dari data yang sudah
dilabel MANUSIA (golden_dataset.csv, dikumpulkan lewat evaluate_manual.py),
disimpan ke folder model/, lalu di-load di sini buat prediksi. Metrik
validasi yang ditampilkan di dashboard juga diambil dari sini — jadi
angkanya beneran dari perbandingan ke label manusia, bukan sirkular ke
lexicon lagi.

Kalau model belum pernah dilatih (folder model/ belum ada / belum cukup
data), fallback ke sentiment_svm.classify_dataframe() - yaitu SVM yang
dilatih ULANG tiap request dari label lexicon (bukan label manusia). Ini
tetap ngasih angka di tab Validasi Model (accuracy/precision/dst), tapi
catatannya SUDAH jelas bilang itu ngukur konsistensi ke lexicon, bukan ke
manusia - jadi nggak menyesatkan, cuma sekadar "ada isinya dulu" sambil
nunggu golden_dataset.csv cukup buat train_model.py.
"""

import json
import os

import joblib

import sentiment_svm  # dipakai sebagai fallback (SVM per-request vs lexicon)

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
MODEL_PATH = os.path.join(MODEL_DIR, "svm_model.joblib")
VECTORIZER_PATH = os.path.join(MODEL_DIR, "tfidf_vectorizer.joblib")
METRICS_PATH = os.path.join(MODEL_DIR, "validation_metrics.json")

_model = None
_vectorizer = None
_metrics = None

if os.path.exists(MODEL_PATH) and os.path.exists(VECTORIZER_PATH) and os.path.exists(METRICS_PATH):
    print("[sentiment_model.py] Loading model terlatih dari folder model/ ...")
    _model = joblib.load(MODEL_PATH)
    _vectorizer = joblib.load(VECTORIZER_PATH)
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        _metrics = json.load(f)
    acc = _metrics.get("accuracy")
    print(
        f"[sentiment_model.py] Model siap. Akurasi vs label manusia: "
        f"{f'{acc:.3f}' if acc is not None else '-'}"
    )
else:
    print(
        "[sentiment_model.py] Belum ada model terlatih di folder model/. "
        "Sentimen SEMENTARA memakai SVM per-request vs lexicon (lihat "
        "sentiment_svm.py) - tab Validasi Model bakal nunjukkin metrik, tapi "
        "dengan catatan itu masih dibandingkan ke lexicon, bukan label "
        "manusia. Jalankan evaluate_manual.py buat melabeli data, lalu "
        "train_model.py buat melatih & memvalidasi model yang beneran."
    )


def classify_dataframe(df, tokens_column="tokens_stemmed", text_column="text_final"):
    """
    Return: (df dengan kolom sentiment & sentiment_score, validation_dict)

    Kalau model human-validated ada: validation_dict SELALU sama untuk
    model yang sama (bukan dihitung ulang tiap request) - karena itu
    mengukur seberapa bagus model terhadap held-out test set manusia yang
    tetap, bukan terhadap data request ini.

    Kalau belum ada (fallback): validation_dict dihitung ulang tiap
    request dari sentiment_svm.py (SVM vs lexicon punya request ini).
    """
    df = df.copy()

    if _model is not None and _vectorizer is not None:
        from scipy.sparse import hstack, csr_matrix
        import numpy as np
        from directional_lexicon import score_directional_patterns

        X_tfidf = _vectorizer.transform(df[text_column])
        dir_scores = np.array(
            [score_directional_patterns(t.split())[0] for t in df[text_column]],
            dtype=float,
        ).reshape(-1, 1)
        X = hstack([X_tfidf, csr_matrix(dir_scores)]).tocsr()

        y_pred = _model.predict(X)
        proba = _model.predict_proba(X)
        class_index = {c: i for i, c in enumerate(_model.classes_)}

        df["sentiment"] = y_pred
        df["sentiment_score"] = [
            float(proba[i, class_index[label]]) for i, label in enumerate(y_pred)
        ]
        validation = _metrics
    else:
        df, validation = sentiment_svm.classify_dataframe(
            df, tokens_column=tokens_column, text_column=text_column
        )

    return df, validation
