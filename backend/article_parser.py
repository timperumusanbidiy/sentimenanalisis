import re
import time
import requests
import trafilatura
import pandas as pd
from tqdm.auto import tqdm

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# potongan teks UI Google News yang sering nyelip kalau halaman
# belum ke-resolve sempurna ke artikel aslinya
GOOGLE_UI_ARTIFACTS = [
    "preferredsource",
    "add preferred source",
    "opening in another tab",
]


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def looks_like_google_ui(text, min_words=40):

    word_count = len(text.split())

    if word_count < min_words:
        return True

    text_lower = text.lower()

    for artifact in GOOGLE_UI_ARTIFACTS:
        if artifact in text_lower:
            return True

    return False


def get_full_text(url, timeout=10, retries=2):
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)

            if resp.status_code != 200:
                continue  # coba lagi kalau masih ada percobaan tersisa

            text = trafilatura.extract(
                resp.text,
                include_comments=False,
                include_tables=False
            )

            if not text:
                return None

            text = text.strip()

            if looks_like_google_ui(text):
                return None  # dianggap gagal, biar fallback/kandidat lain dipakai

            return text

        except requests.exceptions.RequestException:
            if attempt < retries:
                time.sleep(1)  # jeda sebelum retry
                continue
            return None

    return None