"""
evaluate_manual.py
Script berdiri sendiri (dijalankan dari terminal, bukan bagian dari API)
buat: (1) bikin evaluation set manual, (2) ngitung akurasi model
terhadap label manusia, dan (3) NABUNG label manusia itu ke
golden_dataset.csv supaya bisa dipakai train_model.py buat melatih model
final yang beneran divalidasi.

CARA PAKAI
==========

Langkah 1 - bikin sample buat dianotasi manual:

    python evaluate_manual.py sample laporan.xlsx --n 100

  `laporan.xlsx` = file hasil "Unduh Laporan" dari dashboard (yang ada
  sheet "Berita"-nya). Ini bakal bikin 2 file:

  - sample_anotasi_manual.xlsx
      Isinya: id, tanggal, judul, sumber, url, cuplikan isi berita, dan
      kolom kosong "label_manual" buat kamu isi sendiri (baca beritanya,
      tulis salah satu: Positif / Negatif / Netral).
      SENGAJA TIDAK ADA prediksi model-nya di file ini, biar kamu nilai
      murni dari isi beritanya sendiri (gak keinfluence sama hasil model).

  - _internal_JANGAN_DIBUKA.xlsx
      Prediksi model + teks yang sudah diproses, buat baris yang sama.
      JANGAN DIBUKA sebelum kamu selesai ngisi label_manual di file
      sample-nya - kalau kebuka & keliatan duluan, penilaian kamu bisa
      bias ikut-ikutan model.

Langkah 2 - isi kolom "label_manual" di sample_anotasi_manual.xlsx pakai
Excel biasa. Isi tiap baris dengan salah satu dari: Positif, Negatif,
Netral (boleh huruf besar/kecil bebas, nanti dinormalisasi otomatis).

Langkah 3 - setelah semua baris terisi, hitung akurasi beneran & nabung
ke golden dataset:

    python evaluate_manual.py evaluate sample_anotasi_manual.xlsx

  Ini akan:
  - Ngeprint + nyimpen hasil evaluasi ke hasil_evaluasi_manual.txt
    (accuracy, precision, recall, F1, confusion matrix) - ini akurasi
    yang valid buat laporan (dibanding label manusia, bukan lexicon).
  - Nambahin baris yang baru dilabel ke golden_dataset.csv (bikin file
    baru kalau belum ada, dedupe otomatis kalau ada teks yang sama).

Langkah 4 - kalau golden_dataset.csv sudah cukup banyak (minimal 30 baris,
disarankan 150+), latih model final-nya:

    python train_model.py

  Setelah itu restart backend biar dashboard pakai model yang baru
  dilatih & divalidasi ini (bukan lagi lexicon vs lexicon).
"""

import argparse
import os
import sys

import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
)

VALID_LABELS = {"positif": "Positif", "negatif": "Negatif", "netral": "Netral"}

# Path di-anchor ke folder backend/ (bukan ke folder tempat command dijalankan
# atau ke lokasi laporan.xlsx), supaya semua output selalu konsisten di satu
# tempat, dan train_model.py pasti nemu golden_dataset.csv yang sama.
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_FILENAME = os.path.join(BACKEND_ROOT, "sample_anotasi_manual.xlsx")
INTERNAL_FILENAME = os.path.join(BACKEND_ROOT, "_internal_JANGAN_DIBUKA.xlsx")
REPORT_FILENAME = os.path.join(BACKEND_ROOT, "hasil_evaluasi_manual.txt")
GOLDEN_PATH = os.path.join(BACKEND_ROOT, "golden_dataset.csv")


def cmd_sample(args):
    if not os.path.exists(args.laporan_xlsx):
        print(f"File tidak ditemukan: {args.laporan_xlsx}")
        sys.exit(1)

    df = pd.read_excel(args.laporan_xlsx, sheet_name="Berita")
    required_cols = {"sentiment", "text_final"}
    if not required_cols.issubset(df.columns):
        print("Sheet 'Berita' tidak punya kolom yang dibutuhkan (sentiment, text_final). "
              "Pastikan file ini hasil 'Unduh Laporan' dari dashboard versi terbaru.")
        sys.exit(1)

    df = df.reset_index(drop=True)
    df["id"] = df.index

    n = min(args.n, len(df))
    if n < args.n:
        print(f"Cuma ada {len(df)} berita di file ini, sample-nya {n} (bukan {args.n}).")

    sample = df.sample(n=n, random_state=args.seed).sort_values("id")

    # File buat dianotasi manual - TANPA prediksi model.
    to_annotate = sample[["id", "tanggal", "judul", "source", "url", "content"]].copy()
    to_annotate["content"] = to_annotate["content"].astype(str).str.slice(0, 1200)
    to_annotate["label_manual"] = ""
    to_annotate.to_excel(SAMPLE_FILENAME, index=False)

    # Data internal - prediksi model + teks final (buat dibandingin & nabung ke golden dataset).
    # Jangan dibuka dulu sebelum selesai labeling manual.
    internal = sample[["id", "sentiment", "sentiment_score", "text_final"]].copy()
    internal.to_excel(INTERNAL_FILENAME, index=False)

    print(f"Selesai. {n} berita dipilih acak (seed={args.seed}).")
    print(f"-> Isi kolom 'label_manual' di: {SAMPLE_FILENAME}")
    print(f"-> Jangan dibuka dulu: {INTERNAL_FILENAME}")
    print("Setelah selesai mengisi label, jalankan:")
    print(f"    python evaluate_manual.py evaluate {SAMPLE_FILENAME}")


def _normalize_label(raw):
    if pd.isna(raw):
        return None
    key = str(raw).strip().lower()
    return VALID_LABELS.get(key)


def _commit_to_golden_dataset(commit_df):
    """Tambahin baris (text_final, label_manual) ke golden_dataset.csv, dedupe on text_final."""
    if os.path.exists(GOLDEN_PATH):
        existing = pd.read_csv(GOLDEN_PATH)
        combined = pd.concat([existing, commit_df], ignore_index=True)
    else:
        combined = commit_df

    before = len(combined)
    combined = combined.drop_duplicates(subset=["text_final"], keep="last")
    combined.to_csv(GOLDEN_PATH, index=False)

    n_new = len(combined) - (before - len(commit_df) if os.path.exists(GOLDEN_PATH) else 0)
    print(f"\ngolden_dataset.csv sekarang berisi {len(combined)} baris berlabel manusia "
          f"(setelah dedupe).")
    if len(combined) < 30:
        print(f"Masih kurang dari 30 - label {30 - len(combined)} berita lagi sebelum "
              "train_model.py bisa dijalankan.")
    else:
        print("Sudah cukup buat dilatih. Jalankan: python train_model.py")


def cmd_evaluate(args):
    if not os.path.exists(args.sample_xlsx):
        print(f"File tidak ditemukan: {args.sample_xlsx}")
        sys.exit(1)

    internal_path = args.internal_file or INTERNAL_FILENAME
    if not os.path.exists(internal_path):
        print(f"File internal tidak ditemukan: {internal_path}")
        print("Pastikan file itu masih ada di folder yang sama (hasil dari 'sample' step).")
        sys.exit(1)

    labeled = pd.read_excel(args.sample_xlsx)
    internal = pd.read_excel(internal_path)

    if "label_manual" not in labeled.columns:
        print("Kolom 'label_manual' tidak ditemukan di file ini.")
        sys.exit(1)

    labeled["label_manual_norm"] = labeled["label_manual"].apply(_normalize_label)

    n_total = len(labeled)
    n_kosong = labeled["label_manual_norm"].isna().sum()
    if n_kosong > 0:
        print(f"Peringatan: {n_kosong} dari {n_total} baris belum diisi / isinya tidak "
              f"dikenali (harus persis 'Positif'/'Negatif'/'Netral'). Baris ini di-skip.")

    merged = labeled.merge(internal, on="id", how="inner", suffixes=("", "_model"))
    merged = merged.dropna(subset=["label_manual_norm"])

    if len(merged) < 5:
        print("Data yang sudah dilabeli & valid kurang dari 5 baris - belum cukup untuk "
              "dihitung akurasinya. Lengkapi dulu label_manual-nya.")
        sys.exit(1)

    y_true = merged["label_manual_norm"]
    y_pred = merged["sentiment"]

    labels_order = sorted(set(y_true) | set(y_pred))
    cm = confusion_matrix(y_true, y_pred, labels=labels_order)

    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, average="weighted", zero_division=0)
    recall = recall_score(y_true, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    report_text = classification_report(y_true, y_pred, labels=labels_order, zero_division=0)

    lines = []
    lines.append("=== HASIL EVALUASI TERHADAP LABEL MANUSIA ===")
    lines.append(f"Jumlah sample yang dievaluasi: {len(merged)} dari {n_total} berita")
    lines.append("")
    lines.append(f"Accuracy  : {accuracy:.4f}")
    lines.append(f"Precision : {precision:.4f} (weighted)")
    lines.append(f"Recall    : {recall:.4f} (weighted)")
    lines.append(f"F1-score  : {f1:.4f} (weighted)")
    lines.append("")
    lines.append("Confusion Matrix (baris = label manual/manusia, kolom = prediksi model):")
    header = "        " + "  ".join(f"{l:>10}" for l in labels_order)
    lines.append(header)
    for lbl, row in zip(labels_order, cm):
        lines.append(f"{lbl:>8}" + "  ".join(f"{v:>10}" for v in row))
    lines.append("")
    lines.append("Classification report per kelas:")
    lines.append(report_text)
    lines.append("")
    lines.append(
        "Catatan: ini akurasi model dibandingkan LABEL MANUSIA "
        f"({os.path.basename(args.sample_xlsx)}), bukan terhadap lexicon."
    )

    output_text = "\n".join(lines)
    print(output_text)

    with open(REPORT_FILENAME, "w", encoding="utf-8") as f:
        f.write(output_text)
    print(f"\nHasil juga disimpan ke: {REPORT_FILENAME}")

    # Nabung ke golden dataset supaya bisa dipakai train_model.py.
    commit_df = merged[["text_final", "label_manual_norm"]].rename(
        columns={"label_manual_norm": "label_manual"}
    )
    _commit_to_golden_dataset(commit_df)


def main():
    parser = argparse.ArgumentParser(
        description="Bikin sample anotasi manual, evaluasi akurasi model terhadap label manusia, "
                     "dan nabung hasilnya ke golden_dataset.csv."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_sample = subparsers.add_parser("sample", help="Bikin sample buat dianotasi manual dari file laporan.xlsx")
    p_sample.add_argument("laporan_xlsx", help="Path ke file hasil 'Unduh Laporan' dari dashboard")
    p_sample.add_argument("--n", type=int, default=100, help="Jumlah berita yang di-sample (default 100)")
    p_sample.add_argument("--seed", type=int, default=42, help="Random seed (default 42)")
    p_sample.set_defaults(func=cmd_sample)

    p_eval = subparsers.add_parser(
        "evaluate", help="Hitung akurasi model terhadap label manual & nabung ke golden_dataset.csv"
    )
    p_eval.add_argument("sample_xlsx", help="Path ke sample_anotasi_manual.xlsx yang sudah diisi label_manual-nya")
    p_eval.add_argument("--internal-file", default=None, help="Path ke file internal (default: cari otomatis di folder yang sama)")
    p_eval.set_defaults(func=cmd_evaluate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
