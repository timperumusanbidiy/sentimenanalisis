from wordcloud import WordCloud
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import CountVectorizer


SENTIMENT_COLORMAP = {
    "positif": "Greens",
    "negatif": "Reds",
    "netral": "Greys",
}


def generate_wordcloud_figure(text, sentiment_label="netral"):

    if not text or not text.strip():
        return None

    colormap = SENTIMENT_COLORMAP.get(sentiment_label.lower(), "Greys")

    wc = WordCloud(
        width=800,
        height=400,
        background_color="#f7f5f0",
        colormap=colormap,
        max_words=80,
        prefer_horizontal=0.95
    ).generate(text)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.patch.set_alpha(0)

    return fig


def get_top_ngrams(texts, ngram_range=(2, 2), top_k=15):

    texts = [t for t in texts if isinstance(t, str) and t.strip()]

    if len(texts) == 0:
        return []

    vectorizer = CountVectorizer(
        ngram_range=ngram_range,
        token_pattern=r"(?u)\b\w+\b"
    )

    try:
        matrix = vectorizer.fit_transform(texts)
    except ValueError:
        # kejadian kalau semua teks kosong / cuma 1 kata / dsb
        return []

    sums = matrix.sum(axis=0)

    words_freq = [
        (word, int(sums[0, idx]))
        for word, idx in vectorizer.vocabulary_.items()
    ]

    words_freq = sorted(words_freq, key=lambda x: x[1], reverse=True)

    return words_freq[:top_k]

def get_top_keywords(texts, top_k=15):
    return get_top_ngrams(texts, ngram_range=(1, 1), top_k=top_k)