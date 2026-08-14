"""
topic_modeling.py
Topic modeling pakai LDA (gensim):
1. Cari jumlah topik "optimal" berdasarkan coherence score (c_v) — dicoba
   beberapa kandidat jumlah topik, dipilih yang skornya paling tinggi.
2. Tiap topik dikasih NAMA TEMA oleh Gemini (LLM), berdasarkan kata-kata
   paling khas di topik itu + beberapa contoh judul berita yang masuk ke
   topik itu. Ini menghasilkan nama yang lebih natural (misal "Kebijakan
   Pengendalian Inflasi Pangan Daerah") dibanding sekadar menggabungkan
   kata-kata teratasnya ("Harga & Daerah & Cabai").

SETUP YANG DIBUTUHKAN
======================
1. pip install google-generativeai python-dotenv
2. Bikin file `.env` di folder backend/ (SEJAJAR sama backend_api.py),
   isinya:
       GEMINI_API_KEY=api_key_kamu_di_sini
   (dapetin API key gratis di https://aistudio.google.com/apikey)
   File .env ini SUDAH masuk .gitignore, jangan sampai ke-commit ke git
   ya - itu kredensial pribadi.
3. backend_api.py sudah manggil load_dotenv() di baris paling atas, jadi
   API key ini otomatis kebaca tiap kali server dijalankan.

FALLBACK
========
Kalau GEMINI_API_KEY belum di-set, atau pemanggilan Gemini gagal (rate
limit, tidak ada internet, dll), otomatis fallback ke label statistik
(gabungan kata-kata teratas topik) - jadi dashboard TETAP jalan normal,
cuma nama topiknya kurang natural. Nggak pernah bikin analisis gagal
total gara-gara Gemini bermasalah.

Catatan performa: dibanding notebook aslinya (topic_range 2-10, passes=10),
di sini range & passes-nya sengaja dikecilkan (topic_range 3-7, passes=5)
supaya nggak terlalu lama waktu dipanggil lewat API (LDA dilatih ulang untuk
tiap kandidat jumlah topik). Panggilan ke Gemini sendiri cuma sebanyak
jumlah topik (3-7 kali per analisis, BUKAN per berita), jadi tetap ringan.
"""

import os

from gensim import corpora
from gensim.models import LdaModel, CoherenceModel

RANDOM_STATE = 42
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

_genai_module = None
_gemini_configured = False


def _label_from_words(words, top_n=3):
    """
    Fallback: bikin label dari kata-kata teratas topik itu sendiri, misal
    ["inflasi", "harga", "pangan", ...] -> "Inflasi & Harga & Pangan".
    Dipakai kalau Gemini tidak tersedia / gagal dipanggil.
    """
    top_words = [w.capitalize() for w in words[:top_n] if w]
    return " & ".join(top_words) if top_words else "Lainnya"


def _get_gemini_model():
    """Load & configure google-generativeai secara lazy (sekali saja)."""
    global _genai_module, _gemini_configured

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        if _genai_module is None:
            import google.generativeai as genai
            _genai_module = genai

        if not _gemini_configured:
            _genai_module.configure(api_key=api_key)
            _gemini_configured = True

        return _genai_module.GenerativeModel(GEMINI_MODEL_NAME)
    except Exception as e:
        print(f"[topic_modeling.py] Gemini tidak bisa di-load: {e}")
        return None


def _label_from_llm(words, sample_titles, fallback_label):
    """
    Minta Gemini kasih nama tema yang natural dari kata-kata topik +
    beberapa contoh judul. Kalau gagal dengan alasan apapun, balik ke
    fallback_label (label statistik) - tidak pernah melempar error ke atas.
    """
    model = _get_gemini_model()
    if model is None:
        return fallback_label

    titles_text = "\n".join(f"- {t}" for t in sample_titles[:5]) or "(tidak ada contoh judul)"
    prompt = f"""Kamu membantu memberi nama tema untuk satu topik hasil topic modeling (LDA) dari berita berbahasa Indonesia.

Kata-kata kunci paling khas di topik ini (urut dari paling khas):
{", ".join(words[:10])}

Contoh judul berita yang termasuk topik ini:
{titles_text}

Beri nama tema topik ini dalam Bahasa Indonesia, singkat (3-6 kata), berupa \
frasa yang menggambarkan ISI/TEMA topik ini secara keseluruhan - bukan \
sekadar menyebutkan ulang kata kuncinya satu-satu. Jawab HANYA dengan nama \
temanya saja, tanpa tanda kutip, tanpa penjelasan tambahan, tanpa awalan \
seperti "Tema:" atau "Topik:"."""

    try:
        response = model.generate_content(prompt)
        label = (response.text or "").strip().strip('"').strip("'").strip()
        # Buang awalan umum kalau model tetap nulisnya, jaga-jaga.
        for prefix in ("Tema:", "Topik:", "Nama tema:"):
            if label.lower().startswith(prefix.lower()):
                label = label[len(prefix):].strip()
        return label if label else fallback_label
    except Exception as e:
        print(f"[topic_modeling.py] Gagal minta label ke Gemini, pakai fallback statistik: {e}")
        return fallback_label


def run_topic_modeling(
    df, tokens_column="tokens_stemmed", topic_range=range(3, 8), passes=5,
    use_llm_labels=True, title_column="judul",
):
    """
    Return: (df dengan kolom topik_dominan & label_topik, topics_info list, categories list)
    Kalau data terlalu sedikit buat topic modeling yang bermakna, semua
    berita ditandai "Lainnya" dan topics_info/categories dikembalikan kosong
    (bukan diisi data palsu).
    """
    df = df.copy()
    texts = [[tok for tok in toks if len(tok) > 2] for toks in df[tokens_column]]

    dictionary = corpora.Dictionary(texts)
    dictionary.filter_extremes(no_below=2, no_above=0.6)
    corpus = [dictionary.doc2bow(t) for t in texts]

    if len(dictionary) < 5 or len(df) < 10:
        df["topik_dominan"] = -1
        df["label_topik"] = "Lainnya"
        return df, [], []

    candidate_ks = [k for k in topic_range if k < len(df)]
    if not candidate_ks:
        candidate_ks = [2]

    coherence_scores = []
    models = {}
    for k in candidate_ks:
        lda_temp = LdaModel(
            corpus=corpus, id2word=dictionary, num_topics=k,
            random_state=RANDOM_STATE, passes=passes, alpha="auto", eta="auto",
        )
        models[k] = lda_temp
        try:
            coherence_model = CoherenceModel(
                model=lda_temp, texts=texts, dictionary=dictionary, coherence="c_v"
            )
            coherence_scores.append(coherence_model.get_coherence())
        except Exception:
            coherence_scores.append(-1.0)

    best_idx = max(range(len(coherence_scores)), key=lambda i: coherence_scores[i])
    best_k = candidate_ks[best_idx]
    lda_model = models[best_k]

    def _dominant_topic(bow):
        probs = lda_model.get_document_topics(bow)
        if not probs:
            return -1
        return max(probs, key=lambda x: x[1])[0]

    df["topik_dominan"] = [_dominant_topic(bow) for bow in corpus]

    doc_counts = df["topik_dominan"].value_counts()
    total = len(df)
    has_titles = title_column in df.columns

    topic_labels = {}
    topics_info = []
    for idx in range(lda_model.num_topics):
        words = [w for w, _ in lda_model.show_topic(idx, topn=10)]
        fallback_label = _label_from_words(words)

        if use_llm_labels:
            sample_titles = (
                df.loc[df["topik_dominan"] == idx, title_column].head(5).tolist()
                if has_titles else []
            )
            label = _label_from_llm(words, sample_titles, fallback_label)
        else:
            label = fallback_label

        topic_labels[idx] = label
        jumlah = int(doc_counts.get(idx, 0))
        topics_info.append({
            "id": idx,
            "label": label,
            "terms": words[:8],
            "jumlah_berita": jumlah,
            "share": round(jumlah / total * 100, 1) if total else 0,
        })
    topics_info.sort(key=lambda t: t["jumlah_berita"], reverse=True)

    df["label_topik"] = df["topik_dominan"].map(topic_labels).fillna("Lainnya")

    cat_counts = df["label_topik"].value_counts()
    categories = [{"name": k, "value": int(v)} for k, v in cat_counts.items()]

    return df, topics_info, categories