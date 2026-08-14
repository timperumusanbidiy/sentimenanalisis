"""
train_model.py
Latih & simpan model sentimen FINAL dari golden_dataset.csv — kumpulan
berita yang sudah dilabel MANUSIA lewat evaluate_manual.py.

Beda dari sentiment_svm.py (yang lama): model di sini dilatih dari label
manusia asli, bukan dari lexicon. Sekali dilatih, disimpan ke folder
model/, lalu dipakai berkali-kali oleh sentiment_model.py buat semua
analisis di dashboard — sampai kamu nambah data label baru & jalankan
ulang script ini.

CARA PAKAI
==========
1. Kumpulin label manusia dulu (bisa berkali-kali, dari beberapa kali
   analisis berbeda) lewat:
       python evaluate_manual.py sample laporan.xlsx --n 100
       (isi label_manual di Excel-nya)
       python evaluate_manual.py evaluate sample_anotasi_manual.xlsx
   Tiap kali langkah terakhir ini dijalankan, data yang sudah dilabel
   otomatis ditambahkan ke golden_dataset.csv (dedupe otomatis).

2. Setelah golden_dataset.csv punya cukup banyak baris (minimal 30, tapi
   makin banyak makin stabil hasilnya — idealnya 150+), jalankan:
       python train_model.py

3. Restart backend (`uvicorn backend_api:app --reload`) biar model baru
   ke-load.
"""

import json
import os

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
)

# Path di-anchor ke folder backend/ (bukan ke folder tempat command dijalankan),
# supaya script ini selalu nemu/nulis file yang benar walau dijalankan dari
# folder mana pun: python tools/train_model.py
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN_PATH = os.path.join(BACKEND_ROOT, "golden_dataset.csv")
MODEL_DIR = os.path.join(BACKEND_ROOT, "model")
MIN_SAMPLES = 30  # di bawah ini, train/test split gak bisa dipercaya hasilnya


def main():
    if not os.path.exists(GOLDEN_PATH):
        print(f"Belum ada {GOLDEN_PATH}. Label dulu data pakai evaluate_manual.py "
              "(lihat docstring di atas file ini).")
        return

    df = pd.read_csv(GOLDEN_PATH)
    df = df.dropna(subset=["text_final", "label_manual"])
    df = df.drop_duplicates(subset=["text_final"])

    if len(df) < MIN_SAMPLES:
        print(f"Baru ada {len(df)} data berlabel manusia, minimal {MIN_SAMPLES} "
              f"buat dilatih. Label lebih banyak dulu pakai evaluate_manual.py.")
        return

    label_counts = df["label_manual"].value_counts()
    print("Distribusi label saat ini:")
    print(label_counts.to_string())
    print()

    if len(label_counts) < 2:
        print("Cuma ada 1 jenis label di data kamu, classifier gak bisa dilatih. "
              "Butuh variasi label (minimal 2 kelas berbeda).")
        return

    X_text = df["text_final"]
    y = df["label_manual"]

    stratify = y if label_counts.min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X_text, y, test_size=0.2, random_state=42, stratify=stratify
    )

    tfidf = TfidfVectorizer(ngram_range=(1, 2), max_features=5000, min_df=1, max_df=0.9)
    X_train_vec = tfidf.fit_transform(X_train)
    X_test_vec = tfidf.transform(X_test)

    model = SVC(
        kernel="linear", C=1.0, class_weight="balanced",
        probability=True, random_state=42,
    )
    model.fit(X_train_vec, y_train)

    y_pred = model.predict(X_test_vec)
    labels_order = sorted(y.unique())
    cm = confusion_matrix(y_test, y_pred, labels=labels_order).tolist()

    metrics = {
        "trained": True,
        "trained_on": "golden_dataset.csv (label manusia asli, lewat evaluate_manual.py)",
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, average="weighted", zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, average="weighted", zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
        "confusion_matrix": cm,
        "labels": labels_order,
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "note": (
            f"Metrik ini dihitung dari held-out test set berisi {len(X_test)} label "
            "manusia asli (bukan lexicon). Model dilatih ulang tiap kali "
            "golden_dataset.csv bertambah — jalankan ulang train_model.py setelah "
            "menambah label baru, lalu restart backend."
        ),
    }

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, os.path.join(MODEL_DIR, "svm_model.joblib"))
    joblib.dump(tfidf, os.path.join(MODEL_DIR, "tfidf_vectorizer.joblib"))
    with open(os.path.join(MODEL_DIR, "validation_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"Model & vectorizer disimpan ke folder {MODEL_DIR}/")
    print(f"Accuracy (vs {len(X_test)} label manusia held-out): {metrics['accuracy']:.3f}")
    print(f"Precision: {metrics['precision']:.3f} | Recall: {metrics['recall']:.3f} | F1: {metrics['f1']:.3f}")
    print("\nRestart backend (uvicorn backend_api:app --reload) biar model baru ke-load.")


if __name__ == "__main__":
    main()
