import re
import html
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

stopword_factory = StopWordRemoverFactory()
STOPWORDS = set(stopword_factory.get_stop_words())

EXTRA_STOPWORDS = {
    "kompas", "detik", "antara", "cnbc", "cnn", "tempo", "liputan", "liputan6",
    "com", "co", "id", "news", "portal", "resmi", "pemprov", "kementerian",
    "wib", "jakarta","nol","satu","dua","tiga","empat","lima","enam","tujuh",
    "delapan","sembilan","sepuluh","belas","puluh","ratus","ribu","juta","miliar",
    "triliun","2023","2024","2025","2026","1","2","3","4","5","6","7","8","9","0","00","000","0000","00000","000000","0000000","00000000","000000000","0000000000",
    "persen","per","rp","rupiah","usd","dolar","miliar","triliun","kali","unit",
    "hari","tanggal","pekan","minggu","bulan","tahun","januari","februari","maret",
    "april","mei","juni","juli","agustus","september","oktober","november","desember",
    "kemarin","besok","hariini","lalu","kini","saat","jakarta","indonesia","nasional","global",
    "daerah","wilayah","provinsi","kabupaten","kota","kata","ujar","ungkap","jelas","sebut",
    "tutur","terang","menurut","ucap","imbuh","papar","tegas","lanjut","yakni","yaitu","adapun",
    "sementara","detikcom","detik","kompas","tempo","cnn","antara","kontan","bisnis","kumparan",
    "tribun","cnbc","republika","okezone","liputan6","jpnn","mediaindonesia","com","co","id","news",
    "foto","gambar","ilustrasi","dok","dokumentasi","grafik","jadi","masih","sudah","telah","akan",
    "sedang","lebih","hingga","mulai","turut","atas","bawah","tersebut","terhadap","dalam","kepada","oleh",
    "guna","agar","karena","sehingga","namun","bahkan","selain","sementara","masing","yakni","angka",
    "jumlah","nilai","data","hasil","informasi","program","kegiatan","upaya","langkah","kondisi",
    "proses","sektor","bidang","masyarakat","warga","pihak","orang","pelaku","perusahaan","pemerintah",
    "kementerian","menteri","presiden","bank","indonesia","badan","pusat","statistik","bps","serta", "beri", 
    "perlu", "bagi", "baca", "terus", "pilih", "kulon", "progo", "tetap", "salah", "ada", "bukan", "ikut", 
    "berita", "terima", "sama", "lalu", "bagai", "siap", "lanjut", "rupa", "alami", "akibat", "bangun", "butuh", 
    "hektare", "picu", "salur", "kalau", "tak", "dasar", "dapat", "hadap", "tengah", "tangan", "jawa", "kait", 
    "daerah", "liter", "penuh", "camat", "copyright", "awal", "selesai", "dinas", "pasti", "kalsel", "gunungkidul", 
    "gunung", "kidul", "kota", "selatan", "utara", "barat", "timur", "wetan", "lor"
}
STOPWORDS |= EXTRA_STOPWORDS


def strip_source_suffix(judul):
    """Google News nulis judul sbg 'Isi Berita - Nama Media'. Buang bagian sumbernya."""
    if not isinstance(judul, str):
        return ""
    return judul.split(" - ")[0].strip()


def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def remove_stopwords(text, dynamic_stopwords=None):
    if dynamic_stopwords is None:
        dynamic_stopwords = set()
    words = text.split()
    words = [w for w in words if w not in STOPWORDS and w not in dynamic_stopwords and len(w) > 2]
    return " ".join(words)


def preprocess_dataframe(df, search_keyword="", custom_stopwords_input=""):
    df = df.copy()

    # Generate dynamic stopwords from search keyword and custom input
    dynamic_stopwords = set()
    if search_keyword:
        dynamic_stopwords.update(search_keyword.lower().split())
    if custom_stopwords_input:
        custom_words = [w.strip().lower() for w in custom_stopwords_input.split(",")]
        dynamic_stopwords.update(custom_words)

    judul_inti = df["judul"].fillna("").apply(strip_source_suffix)
    content = df["content"].fillna("")

    same_as_judul = content.str.strip() == df["judul"].fillna("").str.strip()
    content_dedup = content.where(~same_as_judul, "")

    df["text"] = (judul_inti + " " + content_dedup).str.strip()

    df["clean_text"] = df["text"].apply(clean_text)
    df["clean_text"] = df["clean_text"].apply(lambda x: remove_stopwords(x, dynamic_stopwords))

    return df
