import feedparser
import pandas as pd
import urllib.parse
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from article_parser import get_full_text, strip_html
from googlenewsdecoder import gnewsdecoder

MONTH_MAP = {
    "Januari": 1, "Februari": 2, "Maret": 3, "April": 4,
    "Mei": 5, "Juni": 6, "Juli": 7, "Agustus": 8,
    "September": 9, "Oktober": 10, "November": 11, "Desember": 12
}

def get_news(year, month, keyword, limit=100):

    month_num = MONTH_MAP[month]

    start_date = date(year, month_num, 1)

    if month_num == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month_num + 1, 1)

    query = (
        f"{keyword} "
        f"after:{start_date.isoformat()} "
        f"before:{end_date.isoformat()}"
    )

    encoded_query = urllib.parse.quote(query)

    url = (
        f"https://news.google.com/rss/search?"
        f"q={encoded_query}&hl=id&gl=ID&ceid=ID:id"
    )

    feed = feedparser.parse(url)

    news = []

    for item in feed.entries:

        source = ""
        if hasattr(item, "source"):
            source = item.source.get("title", "")

        tanggal = ""
        if hasattr(item, "published"):
            tanggal = item.published

        if hasattr(item, "published_parsed") and item.published_parsed:
            item_date = date(
                item.published_parsed.tm_year,
                item.published_parsed.tm_mon,
                item.published_parsed.tm_mday
            )

            if not (start_date <= item_date < end_date):
                continue

        news.append({
            "tanggal": tanggal,
            "judul": item.get("title", ""),
            "content": item.get("description", ""),
            "url": item.get("link", ""),
            "source": source
        })

        if len(news) >= limit:
            break

    df = pd.DataFrame(news)

    return df

def resolve_real_url(google_url):
    try:
        result = gnewsdecoder(google_url)
        if result.get("status"):
            return result["decoded_url"]
    except Exception:
        pass
    return google_url

def enrich_with_full_content(df, max_workers=10, progress_callback=None, target_full_text=None):
    """
    Coba ambil full text tiap baris di df secara paralel.

    Kalau `target_full_text` diisi: proses BERHENTI LEBIH AWAL begitu jumlah
    yang berhasil dapat full text sudah mencapai target itu. Kandidat sisa
    yang belum sempat mulai diproses (masih ngantre di ThreadPoolExecutor,
    belum dapat giliran worker) langsung dibatalkan - jadi nggak buang waktu
    scraping ratusan kandidat yang sebenarnya sudah nggak dibutuhkan lagi.
    Kandidat yang KEBURU JALAN pas keputusan berhenti diambil tetap
    diselesaikan dulu (nggak bisa dihentikan di tengah request HTTP).
    """

    def fetch(idx, url, desc_fallback, judul_fallback):

        real_url = resolve_real_url(url)
        full_text = get_full_text(real_url)

        if full_text:
            return idx, full_text, True, "Teks Lengkap"

        cleaned_desc = strip_html(desc_fallback)

        if cleaned_desc:
            return idx, cleaned_desc, False, "Ringkasan RSS"

        return idx, judul_fallback, False, "Judul Saja"

    total = len(df)
    done = 0
    full_text_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        futures = {
            executor.submit(
                fetch, idx, row["url"], row["content"], row["judul"]
            ): idx
            for idx, row in df.iterrows()
        }

        for future in as_completed(futures):

            idx, content, is_full, status_label = future.result()

            df.at[idx, "content"] = content
            df.at[idx, "is_full_text"] = is_full
            df.at[idx, "scrape_status_label"] = status_label

            done += 1
            if is_full:
                full_text_count += 1

            if progress_callback:
                if target_full_text is not None:
                    progress_callback(full_text_count, target_full_text)
                else:
                    progress_callback(done, total)

            if target_full_text is not None and full_text_count >= target_full_text:
                # Kuota full-text udah kepenuhan - batalin kandidat yang
                # belum sempat mulai (yang udah jalan tetap boleh selesai,
                # tapi kita nggak nunggu itu; loop as_completed berhenti di sini).
                for f in futures:
                    f.cancel()
                break

    return df

def get_news_expanded(year, month, keyword, raw_pool_target=600):
    """
    Ambil berita dengan pool lebih besar dari kebutuhan, dengan memecah
    periode per minggu biar dapat lebih banyak kandidat dibanding
    satu query langsung untuk satu bulan penuh.
    """

    month_num = MONTH_MAP[month]

    start_date = date(year, month_num, 1)

    if month_num == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month_num + 1, 1)

    all_news = []
    seen_urls = set()
    seen_titles = set()

    current = start_date

    while current < end_date:

        week_end = min(current + timedelta(days=7), end_date)

        query = (
            f"{keyword} "
            f"after:{current.isoformat()} "
            f"before:{week_end.isoformat()}"
        )

        encoded_query = urllib.parse.quote(query)

        url = (
            f"https://news.google.com/rss/search?"
            f"q={encoded_query}&hl=id&gl=ID&ceid=ID:id"
        )

        feed = feedparser.parse(url)

        for item in feed.entries:

            link = item.get("link", "")
            title_norm = item.get("title", "").strip().lower()

            if link in seen_urls or title_norm in seen_titles:
                continue

            if hasattr(item, "published_parsed") and item.published_parsed:
                item_date = date(
                    item.published_parsed.tm_year,
                    item.published_parsed.tm_mon,
                    item.published_parsed.tm_mday
                )

                if not (current <= item_date < week_end):
                    continue

            source = ""
            if hasattr(item, "source"):
                source = item.source.get("title", "")

            tanggal = ""
            if hasattr(item, "published"):
                tanggal = item.published

            seen_urls.add(link)
            seen_titles.add(title_norm)

            all_news.append({
                "tanggal": tanggal,
                "judul": item.get("title", ""),
                "content": item.get("description", ""),
                "url": link,
                "source": source
            })

        current = week_end

        if len(all_news) >= raw_pool_target:
            break

    return pd.DataFrame(all_news)


def get_news_with_full_text(
    year, month, keyword, target_limit,
    max_workers=10, progress_callback=None,
    max_pool_multiplier=4
):
    """
    Ambil berita, coba full text-nya, BERHENTI begitu jumlah yang berhasil
    full text sudah = target_limit (nggak nyoba seluruh pool kalau nggak
    perlu). Kalau ternyata seluruh pool udah dicoba dan tetap belum cukup
    (situs-situs banyak yang gagal di-scrape), sisanya baru ditambal dari
    fallback (deskripsi RSS / judul) supaya nggak kosong total.
    """

    max_pool = min(target_limit * max_pool_multiplier, 1500)

    pool_df = get_news_expanded(
        year, month, keyword,
        raw_pool_target=max_pool
    )

    if len(pool_df) == 0:
        pool_df["is_full_text"] = pd.Series(dtype=bool)
        return pool_df, 0, 0

    pool_df["is_full_text"] = False
    pool_df["scrape_status_label"] = ""

    pool_df = enrich_with_full_content(
        pool_df,
        max_workers=max_workers,
        progress_callback=progress_callback,
        target_full_text=target_limit,
    )

    # Buang kandidat yang belum sempat diproses (dibatalkan karena kuota
    # full-text sudah kepenuhan lebih dulu) - biar nggak ikut kehitung.
    processed_df = pool_df[pool_df["scrape_status_label"] != ""].reset_index(drop=True)
    total_pool = len(processed_df)

    # prioritaskan yang full text asli
    df_full_text = processed_df[processed_df["is_full_text"]].reset_index(drop=True)

    if len(df_full_text) >= target_limit:
        return df_full_text.head(target_limit), target_limit, total_pool

    # Kalau full-text yang didapat masih kurang dari target_limit walaupun
    # SELURUH pool sudah dicoba (jarang, tapi bisa kejadian kalau topiknya
    # emang sepi berita atau kebanyakan situs blokir scraping), baru
    # ditambal dari fallback (yang is_full_text == False tapi content-nya
    # tetap terisi, bukan kosong).
    df_fallback = processed_df[
        (~processed_df["is_full_text"]) & (processed_df["content"].str.strip() != "")
    ].reset_index(drop=True)

    kekurangan = target_limit - len(df_full_text)

    df_combined = pd.concat(
        [df_full_text, df_fallback.head(kekurangan)],
        ignore_index=True
    )

    jumlah_didapat = len(df_combined)

    return df_combined, jumlah_didapat, total_pool