"""
preprocessing/stemming.py
Tahap lanjutan setelah cleaning + stopword removal (preprocessing/cleaning.py):
1. Tokenize
2. Normalisasi kata tidak baku/slang
3. Stemming pakai Sastrawi (di-cache per kata unik biar cepat untuk data
   ratusan berita — stemming per kata yang sama nggak dihitung ulang)
4. Filter stopword TAMBAHAN setelah stemming

Kenapa perlu filter stopword lagi SETELAH stemming (bukan cuma sebelum)?
Karena banyak kata kerja "pelapor" umum di berita (menjadi, terjadi,
kejadian, mengatakan, menyebutkan, mengungkapkan, dst) BUKAN stopword di
bentuk aslinya, tapi begitu di-stem semuanya collapse jadi kata generik
yang nggak informatif (jadi, kata, sebut, ungkap, dst) - dan filter
stopword sebelumnya nggak nangkep ini karena dia jalan sebelum stemming.

Menghasilkan dua kolom baru:
- tokens_stemmed : list token hasil stem (dipakai buat LDA topic modeling)
- text_final     : string gabungan token (dipakai buat TF-IDF sentimen SVM)
"""

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

_stemmer = StemmerFactory().create_stemmer()

# Kamus normalisasi kata tidak baku/singkatan umum di media & medsos Indonesia.
# Bisa ditambah sesuai temuan di data.
KAMUS_NORMALISASI = {
    "gak": "tidak", "ga": "tidak", "nggak": "tidak", "enggak": "tidak",
    "yg": "yang", "dg": "dengan", "dgn": "dengan", "utk": "untuk",
    "krn": "karena", "karna": "karena", "sdh": "sudah", "udah": "sudah",
    "blm": "belum", "tdk": "tidak", "jgn": "jangan",
    "bgt": "banget", "skrg": "sekarang", "pemda": "pemerintah daerah",
    "pemprov": "pemerintah provinsi", "bi": "bank indonesia",
}

# Kata generik hasil "collapse" stemming dari kata kerja pelapor berita
# (menjadi/terjadi/kejadian -> jadi, mengatakan/dikatakan -> kata, dst).
# Bukan stopword di bentuk aslinya, tapi begitu di-stem jadi nggak
# informatif buat wordcloud/topic modeling. Tambahin di sini kalau nemu
# kata generik lain yang lolos.
STOPWORDS_PASCA_STEM = {
    "jadi", "kata", "sebut", "ungkap", "tutur", "guna", "tunjuk", "lapor",
}


def _normalize_tokens(tokens):
    return [KAMUS_NORMALISASI.get(tok, tok) for tok in tokens]


def stem_dataframe(df, source_column="clean_text"):
    """
    df[source_column] diasumsikan sudah lolos cleaning + stopword removal
    (hasil dari preprocessing.cleaning.preprocess_dataframe).
    """
    df = df.copy()

    tokens_raw = df[source_column].fillna("").apply(lambda t: t.split())
    tokens_norm = tokens_raw.apply(_normalize_tokens)

    # Cache stemming per kata unik supaya nggak stem ulang kata yang sama
    # berkali-kali (bisa ratusan/ribuan kali lebih cepat untuk data besar).
    vocab = set()
    for toks in tokens_norm:
        vocab.update(toks)

    stem_cache = {word: _stemmer.stem(word) for word in vocab}

    def _stem_and_filter(tokens):
        stemmed = [stem_cache[t] for t in tokens]
        return [t for t in stemmed if len(t) > 2 and t not in STOPWORDS_PASCA_STEM]

    df["tokens_stemmed"] = tokens_norm.apply(_stem_and_filter)
    df["text_final"] = df["tokens_stemmed"].apply(lambda toks: " ".join(toks))

    return df