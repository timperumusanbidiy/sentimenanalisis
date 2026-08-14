from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


def semantic_deduplicate(df, text_column="clean_text", threshold=0.85):

    df = df.reset_index(drop=True)

    texts = df[text_column].fillna("").tolist()

    if len(texts) < 2:
        return df

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(texts)

    similarity_matrix = cosine_similarity(tfidf_matrix)

    keep = np.ones(len(texts), dtype=bool)

    for i in range(len(texts)):

        if not keep[i]:
            continue

        for j in range(i + 1, len(texts)):

            if keep[j] and similarity_matrix[i, j] >= threshold:
                keep[j] = False

    return df[keep].reset_index(drop=True)