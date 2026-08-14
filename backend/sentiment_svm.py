"""
sentiment_svm.py
Analisis sentimen: Lexicon (InSet Lexicon) + SVM.

Lexicon yang dipakai: InSet Lexicon (Koto & Rahmaningtyas, 2017) —
"InSet Lexicon: Evaluation of a Word List for Indonesian Sentiment Analysis
in Microblogs", IALP 2017. 3.609 kata positif + 6.609 kata negatif dengan
bobot -5 s/d +5. Sumber: https://github.com/fajri91/InSet
File lexicon-nya ada di folder lexicon/positive.tsv & lexicon/negative.tsv
(disertakan apa adanya dari repo aslinya, tanpa diedit).

Alurnya:
1. Setiap berita dikasih skor sentimen berbobot dari InSet Lexicon -> label
   (Positif/Negatif/Netral).
2. Label lexicon itu dipakai sebagai target buat melatih classifier SVM
   di atas fitur TF-IDF (unigram+bigram) dari teks yang sudah di-stem.
3. SVM dievaluasi pakai train/test split -> accuracy/precision/recall/F1
   + confusion matrix.
4. Prediksi SVM (bukan label lexicon mentah) dipakai sebagai sentimen
   akhir tiap berita, supaya konsisten dgn model yang divalidasi.

PENTING - batasan yang harus disadari:
1. Label training di sini berasal dari lexicon (walau sekarang InSet yang
   tervalidasi, bukan buatan sendiri), BUKAN dari anotasi manusia. Jadi
   metrik evaluasi (accuracy dkk) mengukur seberapa konsisten SVM meniru
   pola lexicon, BUKAN akurasi terhadap kebenaran/ground truth manusia.
   Untuk validasi yang sebenarnya, lihat evaluate_manual.py - itu
   membandingkan prediksi model terhadap label yang dianotasi manusia.
2. InSet punya ~240 entri positif & ~500 entri negatif berupa FRASA
   (lebih dari 1 kata), bukan kata tunggal. Frasa ini dicocokkan sebagai
   substring ke teks penuh (bukan token individual), jadi ada kemungkinan
   kecil kata-kata di dalam frasa itu ikut kehitung dua kali kalau
   kata-kata tunggalnya juga terdaftar sebagai entri lexicon terpisah.
   Untuk skala data berita (bukan tweet super pendek), efeknya kecil.
3. Kata yang di-lookup adalah bentuk kata dasar hasil stemming Sastrawi,
   BUKAN kata InSet mentah - supaya cocok dengan token yang sudah
   di-stem di pipeline (lihat preprocessing/stemming.py). Ini artinya kata
   InSet ikut di-stem sekali di awal (saat lexicon di-load), baru
   dicocokkan.
"""

import os

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
)

RANDOM_STATE = 42
LEXICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lexicon")

_stemmer = StemmerFactory().create_stemmer()


def _load_inset_lexicon():
    """
    Load lexicon/positive.tsv & lexicon/negative.tsv (format InSet: kolom
    "word" & "weight", pemisah tab). Kata tunggal di-stem & dikumpulkan ke
    dict (rata-rata bobot kalau ada tabrakan hasil stem). Frasa (>1 kata)
    dipisah ke daftar sendiri, di-stem per kata lalu digabung lagi jadi
    frasa, buat dicocokkan via substring.
    """
    single = {}          # stemmed_word -> [list bobot] (dirata-ratakan di akhir)
    phrases = []         # [(stemmed_phrase, bobot), ...]

    for filename in ("positive.tsv", "negative.tsv"):
        path = os.path.join(LEXICON_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            next(f)  # skip header "word\tweight"
            for line in f:
                line = line.strip()
                if not line or "\t" not in line:
                    continue
                word, weight_str = line.rsplit("\t", 1)
                try:
                    weight = float(weight_str)
                except ValueError:
                    continue

                tokens = word.strip().lower().split()
                if not tokens:
                    continue
                stemmed_tokens = [_stemmer.stem(t) for t in tokens]

                if len(stemmed_tokens) == 1:
                    single.setdefault(stemmed_tokens[0], []).append(weight)
                else:
                    phrases.append((" ".join(stemmed_tokens), weight))

    single_avg = {word: sum(ws) / len(ws) for word, ws in single.items()}
    return single_avg, phrases


print("[sentiment_svm.py] Loading InSet Lexicon...")
_LEXICON_SINGLE, _LEXICON_PHRASES = _load_inset_lexicon()
print(
    f"[sentiment_svm.py] Lexicon siap: {len(_LEXICON_SINGLE)} kata tunggal, "
    f"{len(_LEXICON_PHRASES)} frasa."
)


NETRAL_THRESHOLD = 0.15  # rata-rata bobot per kata yang match; di bawah ini dianggap Netral


def _skor_lexicon(tokens, text_final):
    """
    Return (total_skor, jumlah_kata_match). Dipisah dari label supaya
    labelnya bisa dihitung dari RATA-RATA bobot per kata yang match, bukan
    cuma total mentah - total mentah gampang ke-skip dari nol persis
    (jarang banget dua angka pecahan kebetulan jumlahnya pas 0), sehingga
    kalau threshold Netral cuma "skor == 0" hasilnya nyaris nggak pernah
    Netral. Rata-rata per kata jauh lebih stabil buat nentuin ambang batas.
    """
    matched_weights = [_LEXICON_SINGLE[tok] for tok in tokens if tok in _LEXICON_SINGLE]

    for phrase, weight in _LEXICON_PHRASES:
        if phrase in text_final:
            matched_weights.append(weight)

    total_skor = sum(matched_weights)

    # Tambahan skor dari directional patterns
    directional_score = score_directional_patterns(tokens)
    total_skor += directional_score

    jumlah_match = len(matched_weights)
    return total_skor, jumlah_match


def _label_dari_skor(total_skor, jumlah_match):
    if jumlah_match == 0:
        return "Netral"

    rata2 = total_skor / jumlah_match

    if rata2 > NETRAL_THRESHOLD:
        return "Positif"
    elif rata2 < -NETRAL_THRESHOLD:
        return "Negatif"
    return "Netral"


def classify_dataframe(df, tokens_column="tokens_stemmed", text_column="text_final"):
    """
    df harus sudah punya kolom `tokens_column` (list token hasil stem) dan
    `text_column` (string gabungan token) - hasil dari
    preprocessing.stemming.stem_dataframe().

    Return: (df dengan kolom sentiment & sentiment_score, validation_dict)
    """
    df = df.copy()

    scored = df.apply(
        lambda row: _skor_lexicon(row[tokens_column], row[text_column]), axis=1
    )
    df["sentiment_score_lexicon"] = scored.apply(lambda x: x[0])
    df["_jumlah_match_lexicon"] = scored.apply(lambda x: x[1])
    df["sentiment_lexicon"] = [
        _label_dari_skor(s, n)
        for s, n in zip(df["sentiment_score_lexicon"], df["_jumlah_match_lexicon"])
    ]

    label_counts = df["sentiment_lexicon"].value_counts()

    # Data terlalu sedikit / label kurang variatif -> SVM nggak bisa/nggak
    # bermakna dilatih. Fallback: pakai label lexicon langsung, evaluasi
    # dikosongkan (bukan diisi angka palsu).
    if len(df) < 10 or len(label_counts) < 2:
        df["sentiment"] = df["sentiment_lexicon"]
        max_abs = df["sentiment_score_lexicon"].abs().max() or 1
        df["sentiment_score"] = (df["sentiment_score_lexicon"].abs() / max_abs).clip(upper=1.0)
        validation = {
            "trained": False,
            "note": (
                "Data terlalu sedikit atau label kurang bervariasi untuk melatih SVM "
                "(minimal 10 berita & minimal 2 kelas sentimen berbeda). Sentimen memakai "
                "label lexicon (InSet) langsung tanpa SVM."
            ),
            "accuracy": None, "precision": None, "recall": None, "f1": None,
            "confusion_matrix": None, "labels": None,
        }
        return df, validation

    tfidf = TfidfVectorizer(ngram_range=(1, 2), max_features=3000, min_df=2, max_df=0.9)
    X = tfidf.fit_transform(df[text_column])
    y = df["sentiment_lexicon"]

    stratify = y if y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=stratify
    )

    svm_model = SVC(
        kernel="linear", C=1.0, class_weight="balanced",
        probability=True, random_state=RANDOM_STATE,
    )
    svm_model.fit(X_train, y_train)
    y_pred_test = svm_model.predict(X_test)

    labels_order = sorted(y.unique())
    cm = confusion_matrix(y_test, y_pred_test, labels=labels_order).tolist()

    validation = {
        "trained": True,
        "accuracy": float(accuracy_score(y_test, y_pred_test)),
        "precision": float(precision_score(y_test, y_pred_test, average="weighted", zero_division=0)),
        "recall": float(recall_score(y_test, y_pred_test, average="weighted", zero_division=0)),
        "f1": float(f1_score(y_test, y_pred_test, average="weighted", zero_division=0)),
        "confusion_matrix": cm,
        "labels": labels_order,
        "train_size": int(X_train.shape[0]),
        "test_size": int(X_test.shape[0]),
    }

    # Prediksi SVM dipakai sebagai sentimen akhir (bukan lexicon mentah),
    # supaya sentimen yang tampil konsisten dengan model yang dievaluasi.
    y_pred_all = svm_model.predict(X)
    proba_all = svm_model.predict_proba(X)
    class_index = {c: i for i, c in enumerate(svm_model.classes_)}

    df["sentiment"] = y_pred_all
    df["sentiment_score"] = [
        float(proba_all[i, class_index[label]]) for i, label in enumerate(y_pred_all)
    ]

    return df, validation
