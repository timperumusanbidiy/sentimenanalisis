"""
directional_lexicon.py
Kata arah/kata sifat yang polaritasnya TERGANTUNG entitas ekonomi yang
menyertainya (bukan makna kata itu sendiri):
  - "harga naik", "inflasi meningkat", "pengangguran tinggi"  -> NEGATIF
  - "pendapatan naik", "ekspor tinggi", "IHSG menguat"        -> POSITIF
  - "harga turun", "inflasi rendah"                           -> POSITIF
  - "pendapatan turun", "ekspor rendah"                       -> NEGATIF

PENTING: semua kata di bawah ini ditulis dalam BENTUK HASIL STEM Sastrawi,
BUKAN bentuk kamus biasa -- karena tokens yang masuk ke fungsi ini sudah
melewati stemming di pipeline. Contoh: "meningkat" di-stem Sastrawi jadi
"tingkat", BUKAN tetap "meningkat". Kalau nambah kata baru, selalu cek
dulu hasil stem-nya:

    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    print(StemmerFactory().create_stemmer().stem("kata_baru"))

lalu masukkan HASIL STEM-nya ke set di bawah, bukan kata aslinya.

Dipanggil SEBELUM/SESUDAH scoring lexicon kata-per-kata biasa, dan (mulai
sekarang) juga dipakai sebagai FITUR NUMERIK tambahan buat model SVM
(lihat tools/train_model.py & sentiment_model.py) -- bukan cuma buat
jalur lexicon lawas.

CARA PAKAI:

    from directional_lexicon import score_directional_patterns

    extra_score, matched_phrases = score_directional_patterns(tokens)
    total_score = lexicon_score_biasa + extra_score

Kalau mau nambah entitas baru, tinggal tambah ke NEGATIVE_IF_UP /
POSITIVE_IF_UP -- tidak perlu ubah logic-nya.
"""

# Kata KERJA arah (bentuk hasil stem Sastrawi, bukan kata kamus!)
#   naik      -> naik      (tidak berubah)
#   meningkat -> tingkat
#   melonjak  -> lonjak
#   menguat   -> kuat
#   melambung -> lambung
DIRECTIONAL_UP = {"naik", "tingkat", "lonjak", "kuat", "lambung"}

#   turun     -> turun      (tidak berubah)
#   menurun   -> turun      (sama, redundant tapi aman)
#   anjlok    -> anjlok     (tidak berubah)
#   merosot   -> merosot    (tidak berubah)
#   melemah   -> lemah
#   melambat  -> lambat
DIRECTIONAL_DOWN = {"turun", "anjlok", "merosot", "lemah", "lambat","susut","tajam","jatuh","landai","krisis","gagal"}

# Kata SIFAT statis (deskripsi kondisi, bukan pergerakan) -- semua sudah
# bentuk dasar jadi stem-nya sama persis.
STATIC_UP = {"tinggi", "besar", "mahal", "berat"}
STATIC_DOWN = {"rendah", "kecil", "murah", "ringan"}

ALL_UP = DIRECTIONAL_UP | STATIC_UP
ALL_DOWN = DIRECTIONAL_DOWN | STATIC_DOWN

# Entitas yang kalau NAIK/TINGGI -> berita buruk (dan TURUN/RENDAH -> baik)
NEGATIVE_IF_UP = {
    "harga", "inflasi", "angguran", "miskin", "utang", "defisit",
    "kriminal", "jahat", "celaka", "korupsi", "polusi",
    "macet", "bunga", "tarif", "beban", "biaya", "pajak", "ongkos",
    "krisis", "rugi", "phk", "curi", "tipu", "senjang", "tekan", "tunggak",
    "lonjak",
}

# Entitas yang kalau NAIK/TINGGI -> berita baik (dan TURUN/RENDAH -> buruk)
POSITIVE_IF_UP = {
    "dapat", "ekspor", "investasi", "produksi", "jual",
    "ihsg", "saham", "gaji", "upah", "tumbuh", "surplus",
    "cadang", "wisata", "kunjung", "pdb", "laba", "untung", "profit",
    "produktivitas", "kerja",
}

WEIGHT = 3  # kekuatan sinyal, disamakan skala dengan skor lexicon InSet (-5..5)
WINDOW = 4  # jarak maksimal (dalam token) antara entitas & kata arah/sifat


def score_directional_patterns(tokens):
    """
    tokens: list token HASIL STEM (dari tokens_stemmed / text_final.split()).

    Return: (extra_score: int, matched: list[str]) - matched isinya string
    deskriptif buat debugging/logging, misal "inflasi+tingkat(-3)".
    """
    extra_score = 0
    matched = []

    for i, tok in enumerate(tokens):
        if tok in ALL_UP:
            direction = "up"
        elif tok in ALL_DOWN:
            direction = "down"
        else:
            continue

        window_tokens = tokens[max(0, i - WINDOW): i] + tokens[i + 1: i + 1 + WINDOW]

        entity = None
        entity_polarity = None
        for w in window_tokens:
            if any(w.startswith(root) or root in w for root in NEGATIVE_IF_UP):
                entity, entity_polarity = w, "neg_if_up"
                break
            if any(w.startswith(root) or root in w for root in POSITIVE_IF_UP):
                entity, entity_polarity = w, "pos_if_up"
                break

        if entity is None:
            continue  # kata arah/sifat tanpa entitas dikenali -> tetap netral

        if entity_polarity == "neg_if_up":
            score = -WEIGHT if direction == "up" else WEIGHT
        else:
            score = WEIGHT if direction == "up" else -WEIGHT

        extra_score += score
        matched.append(f"{entity}+{tok}({score:+d})")

    return extra_score, matched
