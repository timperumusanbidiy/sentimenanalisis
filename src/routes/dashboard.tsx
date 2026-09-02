import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  Search,
  Calendar,
  Filter,
  Download,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Minus,
  Newspaper,
  Hash,
  LineChart as LineIcon,
  BarChart3,
  Target,
  CheckCircle2,
  RefreshCw,
  Layers,
  AlertTriangle,
  Globe,
  ScanText,
  BrainCircuit,
  GitMerge,
  ClipboardCheck,
  FileText,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Slider } from "@/components/ui/slider";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";

export const Route = createFileRoute("/dashboard")({
  component: DashboardPage,
});

// Ganti ini kalau backend jalan di alamat/port lain.
const API_BASE = "sentimenanalisis.up.railway.app";

const BRAND = {
  p50: "#EEF5FF",
  p200: "#B4D4FF",
  p400: "#86B6F6",
  p700: "#3674B5",
};

const MONTHS = [
  "Januari",
  "Februari",
  "Maret",
  "April",
  "Mei",
  "Juni",
  "Juli",
  "Agustus",
  "September",
  "Oktober",
  "November",
  "Desember",
];

const KEYWORD_PRESETS = [
  "Inflasi",
  "UMKM",
  "Ekonomi Digital",
  "Suku Bunga",
  "Pangan",
  "QRIS",
  "Nilai Tukar",
  "Kebijakan Moneter",
  "Harga Pasar",
  "Pertumbuhan Ekonomi",
  "Rupiah",
];
const ANALYSIS_STEPS = [
  {
    label: "Scraping Berita",
    desc: "Mengumpulkan berita dari berbagai sumber media online sesuai kata kunci dan periode yang dipilih.",
    icon: Globe,
    match: /mengambil dan memvalidasi berita|mendapatkan.*berita/i,
  },
  {
    label: "Normalisasi & Deduplikasi",
    desc: "Membersihkan format teks dan menghapus berita duplikat.",
    icon: ScanText,
    match: /membersihkan teks|menghapus duplikat|normalisasi & stemming/i,
  },
  {
    label: "Analisis Sentimen",
    desc: "Mengklasifikasikan sentimen berita menjadi positif, negatif, atau netral.",
    icon: BrainCircuit,
    match: /menganalisis sentimen/i,
  },
  {
    label: "Ekstraksi Topik (LDA)",
    desc: "Mengidentifikasi tema-tema utama yang dibahas dalam kumpulan berita.",
    icon: GitMerge,
    match: /mencari topik|lda/i,
  },
  {
    label: "Validasi Model",
    desc: "Menilai performa model dengan metrik akurasi, precision, recall, dan F1-score.",
    icon: ClipboardCheck,
    match: /memvalidasi performa model/i,
  },
  {
    label: "Generate Laporan",
    desc: "Menyusun ringkasan dan laporan yang siap diunduh.",
    icon: FileText,
    match: /menyusun tren harian|menyusun ringkasan|menyusun laporan/i,
  },
] as const;

// Cuma step scraping ("Mendapatkan X/Y berita") yang punya pecahan angka nyata,
// jadi persennya khusus di-hitung dari situ.
function parseStepProgress(note: string | null) {
  if (!note) return { stepIndex: 0, pct: 0 };

  let stepIndex = ANALYSIS_STEPS.findIndex((s) => s.match.test(note));
  if (stepIndex === -1) stepIndex = 0;

  const m = note.match(/(\d+)\s*\/\s*(\d+)/);
  const pct = m && stepIndex === 0 ? Math.round((Number(m[1]) / Number(m[2])) * 100) : 0;

  return { stepIndex, pct };
}
// Palet warna buat pie chart kategori (dipakai bergilir sesuai jumlah kategori nyata).
const CATEGORY_COLORS = ["#4e9fdf", "#89dd9f", "#f8ca90", "#b2e1e0", "#fa9484"];
function getMetricTone(val: number | null) {
  if (val === null) return { text: "text-muted-foreground", bar: "#9CA3AF" };
  const pct = val * 100;
  if (pct < 60) return { text: "text-red-600", bar: "#d64545" };
  if (pct < 80) return { text: "text-amber-600", bar: "#D97706" };
  return { text: "text-green-600", bar: "#16A34A" };
}
// --- Tipe data yang dibalikin backend (backend_api.py) ---
interface ArticleItem {
  tanggal: string;
  judul: string;
  source: string;
  url: string;
  content: string;
  clean_text: string;
  sentiment: string;
  sentiment_score: number;
  is_full_text: boolean;
  scrape_status_label: string;
}

interface TopKeywordItem {
  kata: string;
  frekuensi: number;
}

interface TrendPoint {
  day: string;
  berita: number;
  positif: number;
  negatif: number;
  netral: number;
}

interface CategoryItem {
  name: string;
  value: number;
}

interface LdaTopicItem {
  id: number;
  label: string;
  terms: string[];
  jumlah_berita: number;
  share: number;
}

interface ValidationResult {
  trained: boolean;
  trained_on?: string;
  note?: string;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  confusion_matrix: number[][] | null;
  labels: string[] | null;
  train_size?: number;
  test_size?: number;
}

interface AnalysisResult {
  total_berita: number;
  jumlah_didapat?: number;
  total_pool_dicoba?: number;
  jumlah_sebelum_dedup?: number;
  jumlah_setelah_exact_dedup?: number;
  jumlah_setelah_semantic_dedup?: number;
  sentiment_counts?: { positif: number; negatif: number; netral: number };
  top_keywords?: TopKeywordItem[];
  top_bigrams?: TopKeywordItem[];
  top_trigrams?: TopKeywordItem[];
  trend?: TrendPoint[];
  categories?: CategoryItem[];
  lda_topics?: LdaTopicItem[];
  validation?: ValidationResult;
  articles?: ArticleItem[];
  message?: string;
}

interface JobStatusResponse {
  job_id: string;
  status: "pending" | "processing" | "done" | "error";
  progress_note: string | null;
  result: AnalysisResult | null;
  error: string | null;
}

function DashboardPage() {
  const currentYear = new Date().getFullYear();
  const currentMonthIndex = new Date().getMonth();
  const [month, setMonth] = useState(MONTHS[currentMonthIndex]);
  const [year, setYear] = useState(String(currentYear));
  const [keyword, setKeyword] = useState("Inflasi");
  const [count, setCount] = useState<number[]>([100]);

  const [running, setRunning] = useState(false);
  const [progressNote, setProgressNote] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [lastJobId, setLastJobId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 10;

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // Bersihin interval polling kalau komponen di-unmount saat masih jalan.
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const dateRange = useMemo(() => {
    const monthIdx = MONTHS.indexOf(month);
    const now = new Date();
    const isCurrent = Number(year) === now.getFullYear() && monthIdx === now.getMonth();
    const end = isCurrent
      ? now.toLocaleDateString("id-ID", {
          day: "2-digit",
          month: "long",
          year: "numeric",
        })
      : `${new Date(Number(year), monthIdx + 1, 0).getDate()} ${month} ${year}`;
    return `1 ${month} ${year} — ${end}`;
  }, [month, year]);

  const runAnalysis = async () => {
    setErrorMsg(null);
    setRunning(true);
    setProgressNote("Memulai analisis...");
    setSelectedSources([]);
    setCurrentPage(1);

    try {
      const startRes = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          year: Number(year),
          month,
          keyword,
          limit: count[0],
        }),
      });

      if (!startRes.ok) {
        throw new Error(`Gagal memulai analisis (HTTP ${startRes.status})`);
      }

      const startData: JobStatusResponse = await startRes.json();
      const jobId = startData.job_id;
      setLastJobId(jobId);

      pollRef.current = setInterval(async () => {
        try {
          const pollRes = await fetch(`${API_BASE}/api/analyze/${jobId}`);
          const pollData: JobStatusResponse = await pollRes.json();

          setProgressNote(pollData.progress_note);

          if (pollData.status === "done") {
            if (pollRef.current) clearInterval(pollRef.current);
            setResult(pollData.result);
            setRunning(false);
            setProgressNote(null);
          } else if (pollData.status === "error") {
            if (pollRef.current) clearInterval(pollRef.current);
            setErrorMsg(pollData.error ?? "Terjadi kesalahan saat analisis.");
            setRunning(false);
            setProgressNote(null);
          }
        } catch (err) {
          if (pollRef.current) clearInterval(pollRef.current);
          setErrorMsg(
            "Gagal terhubung ke backend saat polling status. Pastikan backend_api.py sedang berjalan di " +
              API_BASE,
          );
          setRunning(false);
          setProgressNote(null);
        }
      }, 1500);
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? `${err.message}. Pastikan backend_api.py sedang berjalan (uvicorn backend_api:app --reload --port 8000).`
          : "Gagal terhubung ke backend.",
      );
      setRunning(false);
      setProgressNote(null);
    }
  };

  const exportExcel = async () => {
    if (!lastJobId) return;
    setExporting(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`${API_BASE}/api/analyze/${lastJobId}/export`);
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error ?? `Gagal mengunduh laporan (HTTP ${res.status})`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sentimen_${keyword.replace(/\s+/g, "_")}_${month}_${year}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Gagal mengunduh laporan Excel.");
    } finally {
      setExporting(false);
    }
  };

  // --- Data turunan dari hasil analisis asli (null kalau belum pernah jalan) ---
  const hasResult = !!result && (result.total_berita ?? 0) > 0;

  const stats = useMemo(() => {
    if (!hasResult || !result?.sentiment_counts) return null;
    return {
      total: result.jumlah_sebelum_dedup ?? result.total_berita,
      unique: result.total_berita,
      positif: result.sentiment_counts.positif,
      negatif: result.sentiment_counts.negatif,
      netral: result.sentiment_counts.netral,
      sumberUnik: undefined as number | undefined,
    };
  }, [result, hasResult]);

  const topWords = useMemo(() => {
    if (!hasResult || !result?.top_keywords) return [];
    return result.top_keywords.slice(0, 10).map((k) => ({ word: k.kata, count: k.frekuensi }));
  }, [result, hasResult]);

  const topBigrams = useMemo(() => {
    if (!hasResult || !result?.top_bigrams) return [];
    return result.top_bigrams.slice(0, 15).map((k) => ({ word: k.kata, count: k.frekuensi }));
  }, [result, hasResult]);

  const topTrigrams = useMemo(() => {
    if (!hasResult || !result?.top_trigrams) return [];
    return result.top_trigrams.slice(0, 15).map((k) => ({ word: k.kata, count: k.frekuensi }));
  }, [result, hasResult]);

  const wordcloudWords = useMemo(() => {
    if (!hasResult || !result?.top_keywords) return [];
    return result.top_keywords.map((k) => ({ text: k.kata, weight: k.frekuensi }));
  }, [result, hasResult]);

  const trend = useMemo(() => {
    if (!hasResult || !result?.trend) return [];
    return result.trend;
  }, [result, hasResult]);

  const availableSources = useMemo(() => {
    if (!hasResult || !result?.articles) return [];
    const set = new Set(result.articles.map((a) => a.source || "Tidak diketahui"));
    return Array.from(set).sort();
  }, [result, hasResult]);

  const filteredArticles = useMemo(() => {
    if (!hasResult || !result?.articles) return [];
    if (selectedSources.length === 0) return result.articles;
    return result.articles.filter((a) => selectedSources.includes(a.source || "Tidak diketahui"));
  }, [result, hasResult, selectedSources]);

  const totalPages = Math.max(1, Math.ceil(filteredArticles.length / PAGE_SIZE));

  const newsList = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredArticles.slice(start, start + PAGE_SIZE).map((a) => ({
      title: a.judul,
      source: a.source,
      date: a.tanggal,
      sentiment: a.sentiment.toLowerCase(),
      url: a.url,
      content: a.content,
    }));
  }, [filteredArticles, currentPage]);

  const toggleSource = (source: string) => {
    setSelectedSources((prev) =>
      prev.includes(source) ? prev.filter((s) => s !== source) : [...prev, source],
    );
    setCurrentPage(1);
  };

  const categories = useMemo(() => {
    if (!hasResult || !result?.categories) return [];
    return result.categories;
  }, [result, hasResult]);

  const ldaTopics = useMemo(() => {
    if (!hasResult || !result?.lda_topics) return [];
    return result.lda_topics;
  }, [result, hasResult]);

  const validation = result?.validation ?? null;

  const sentimentMethodText = validation?.trained_on
    ? "model SVM yang sudah divalidasi terhadap label manusia"
    : "Lexicon (InSet) + SVM";

  const positifPct = stats ? Math.round((stats.positif / stats.unique) * 100) : 0;
  const negatifPct = stats ? Math.round((stats.negatif / stats.unique) * 100) : 0;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-border/60 bg-white/70 backdrop-blur sticky top-0 z-30">
        <div className="mx-auto max-w-[1400px] px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/">
              <Button variant="outline" size="icon" className="h-9 w-9 shrink-0">
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-[color:var(--brand-700)]">
                Monitoring Berita dan Analisis Opini
              </h1>
              <p className="text-xs text-muted-foreground">Analisis Berita &amp; Opini Ekonomi</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              className="gap-2 bg-[color:var(--brand-700)] hover:bg-[color:var(--brand-700)]/90"
              disabled={!hasResult || exporting}
              onClick={exportExcel}
            >
              {exporting ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Unduh Laporan
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] px-6 py-8 space-y-8">
        {/* Search / Input Panel */}
        <Card className="border-border/60 shadow-sm overflow-hidden">
          <div
            className="h-1.5 w-full"
            style={{
              background: `linear-gradient(90deg, ${BRAND.p700})`,
            }}
          />
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5 text-[color:var(--brand-700)]" />
              Input Pencarian
            </CardTitle>
            <CardDescription>
              Atur periode, kata kunci, dan jumlah berita untuk analisis.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Bulan
                </Label>
                <Select value={month} onValueChange={setMonth}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MONTHS.map((m) => (
                      <SelectItem key={m} value={m}>
                        {m}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Tahun
                </Label>
                <div className="flex items-center gap-1">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="h-9 w-9 shrink-0"
                    onClick={() => setYear((y) => String(Number(y) - 1))}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <div className="flex-1 h-9 rounded-md border border-input flex items-center justify-center text-sm font-semibold">
                    {year}
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="h-9 w-9 shrink-0"
                    disabled={Number(year) >= currentYear}
                    onClick={() => setYear((y) => String(Number(y) + 1))}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Kata Kunci / Topik
                </Label>
                <Input
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  placeholder="Contoh: Inflasi, UMKM, Ekonomi Digital"
                />
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Label className="w-full text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Quick Topic
              </Label>
              {KEYWORD_PRESETS.map((k) => (
                <button
                  key={k}
                  onClick={() => setKeyword(k)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium border transition ${
                    keyword === k
                      ? "bg-[color:var(--brand-700)] text-white border-transparent"
                      : "bg-[color:var(--brand-50)] text-[color:var(--brand-700)] border-[color:var(--brand-200)] hover:bg-[color:var(--brand-200)]"
                  }`}
                >
                  {k}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
              <div className="md:col-span-2 space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Jumlah Berita (max 1000)
                  </Label>
                  <span className="text-sm font-bold text-[color:var(--brand-700)]">
                    {count[0]} berita
                  </span>
                </div>
                <Slider value={count} onValueChange={setCount} min={10} max={1000} step={10} />
                <div className="flex justify-between text-[10px] text-muted-foreground">
                  <span>10</span>
                  <span>250</span>
                  <span>500</span>
                  <span>750</span>
                  <span>1000</span>
                </div>
              </div>
              <div
                className="rounded-xl p-4 space-y-1"
                style={{
                  background: BRAND.p50,
                  border: `1px solid ${BRAND.p200}`,
                }}
              >
                <div className="flex items-center gap-2 text-xs font-semibold text-[color:var(--brand-700)] uppercase tracking-wide">
                  <Calendar className="h-4 w-4" /> Rentang Otomatis
                </div>
                <p className="text-sm font-semibold text-foreground">{dateRange}</p>
                <p className="text-xs text-muted-foreground">Bulan berjalan → sampai hari ini.</p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3 pt-2 items-center">
              <Button
                onClick={runAnalysis}
                disabled={running}
                className="gap-2 bg-[color:var(--brand-700)] hover:bg-[color:var(--brand-700)]/90"
              >
                {running ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                {running ? "Menganalisis..." : "Jalankan Analisis"}
              </Button>
            </div>

            {running && <AnalysisStepsFlow progressNote={progressNote} />}

            {errorMsg && (
              <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                {errorMsg}
              </div>
            )}

            {!running && !errorMsg && result && !hasResult && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/40 border border-border rounded-lg px-3 py-2">
                Tidak ada berita ditemukan untuk kata kunci/periode ini. Coba kata kunci atau bulan
                lain.
              </div>
            )}
          </CardContent>
        </Card>

        {!hasResult ? (
          <Card className="shadow-sm">
            <CardContent className="py-16 text-center text-muted-foreground">
              <Newspaper className="h-8 w-8 mx-auto mb-3 text-[color:var(--brand-400)]" />
              Belum ada data. Atur pencarian di atas lalu klik <b>Jalankan Analisis</b> untuk mulai
              scraping &amp; analisis sentimen berita asli.
            </CardContent>
          </Card>
        ) : (
          <>
            {/* KPI cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <KpiCard
                icon={<Newspaper className="h-4 w-4" />}
                label="Total Berita"
                value={stats!.total.toLocaleString("id-ID")}
                sub="sebelum deduplikasi"
              />
              <KpiCard
                icon={<Layers className="h-4 w-4" />}
                label="Setelah Dedup"
                value={stats!.unique.toLocaleString("id-ID")}
                sub={`${Math.round((stats!.unique / stats!.total) * 100)}% unik`}
              />
              <KpiCard
                icon={<TrendingUp className="h-4 w-4 text-[color:var(--positive)]" />}
                label="Positif"
                value={stats!.positif.toString()}
                sub={`${positifPct}%`}
                tone="positive"
              />
              <KpiCard
                icon={<TrendingDown className="h-4 w-4 text-[color:var(--negative)]" />}
                label="Negatif"
                value={stats!.negatif.toString()}
                sub={`${negatifPct}%`}
                tone="negative"
              />
              <KpiCard
                icon={<Minus className="h-4 w-4" />}
                label="Netral"
                value={stats!.netral.toString()}
                sub={`${Math.round((stats!.netral / stats!.unique) * 100)}%`}
                tone="neutral"
              />
            </div>

            {/* Visualizations tabs */}
            <Tabs defaultValue="viz" className="space-y-6">
              <TabsList className="bg-white border border-border">
                <TabsTrigger value="viz">Visualisasi</TabsTrigger>
                <TabsTrigger value="topics">Topik (LDA)</TabsTrigger>
                <TabsTrigger value="news">Berita &amp; Ringkasan</TabsTrigger>
              </TabsList>

              {/* VIZ */}
              <TabsContent value="viz" className="space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <Card className="lg:col-span-2 shadow-sm">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-base">
                        <Hash className="h-4 w-4 text-[color:var(--brand-700)]" /> Wordcloud
                      </CardTitle>
                      <CardDescription>
                        Istilah paling sering muncul dalam berita hasil scraping.
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <Wordcloud words={wordcloudWords} />
                    </CardContent>
                  </Card>

                  <Card className="shadow-sm">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-base">
                        <Target className="h-4 w-4 text-[color:var(--brand-700)]" /> Distribusi
                        Kategori
                      </CardTitle>
                      <CardDescription>
                        Kategori topik hasil LDA, di-label otomatis.
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {categories.length === 0 ? (
                        <div className="h-[300px] grid place-items-center text-sm text-muted-foreground text-center px-4">
                          Data terlalu sedikit untuk topic modeling yang bermakna (minimal ±10
                          berita dengan variasi kata yang cukup).
                        </div>
                      ) : (
                        <>
                          <div className="h-[230px]">
                            <ResponsiveContainer width="100%" height="100%">
                              <PieChart>
                                <Pie
                                  data={categories}
                                  dataKey="value"
                                  nameKey="name"
                                  innerRadius={55}
                                  outerRadius={95}
                                  paddingAngle={3}
                                >
                                  {categories.map((_, i) => (
                                    <Cell
                                      key={i}
                                      fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]}
                                    />
                                  ))}
                                </Pie>
                                <Tooltip />
                              </PieChart>
                            </ResponsiveContainer>
                          </div>
                          <div className="mt-4 space-y-2">
                            {categories.map((cat, i) => {
                              const total = categories.reduce((sum, c) => sum + c.value, 0);
                              const pct = total > 0 ? Math.round((cat.value / total) * 100) : 0;
                              return (
                                <div key={cat.name} className="flex items-center gap-2 text-xs">
                                  <span
                                    className="h-2.5 w-2.5 rounded-full shrink-0"
                                    style={{
                                      background: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
                                    }}
                                  />
                                  <span className="flex-1 truncate font-medium">{cat.name}</span>
                                  <span className="text-muted-foreground shrink-0">
                                    {cat.value} berita ({pct}%)
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        </>
                      )}
                    </CardContent>
                  </Card>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Card className="shadow-sm">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-base">
                        <BarChart3 className="h-4 w-4 text-[color:var(--brand-700)]" /> Kata Paling
                        Sering Muncul
                      </CardTitle>
                      <CardDescription>Top 10 kata berdasarkan frekuensi.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[340px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={topWords} layout="vertical" margin={{ left: 20 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5eefc" />
                          <XAxis type="number" tick={{ fontSize: 11 }} />
                          <YAxis
                            type="category"
                            dataKey="word"
                            tick={{ fontSize: 12 }}
                            width={80}
                          />
                          <Tooltip cursor={{ fill: BRAND.p50 }} />
                          <Bar dataKey="count" fill="#78A4CB" radius={[0, 6, 6, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>

                  <Card className="shadow-sm">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-base">
                        <LineIcon className="h-4 w-4 text-[color:var(--brand-700)]" /> Tren Berita
                        per Hari
                      </CardTitle>
                      <CardDescription>Distribusi sentimen sepanjang periode.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[340px]">
                      {trend.length === 0 ? (
                        <div className="h-full grid place-items-center text-sm text-muted-foreground">
                          Tanggal berita tidak bisa diparse, tren tidak tersedia.
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={trend}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5eefc" />
                            <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                            <YAxis tick={{ fontSize: 11 }} />
                            <Tooltip />
                            <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                            <Line
                              type="monotone"
                              dataKey="berita"
                              stroke={BRAND.p700}
                              strokeWidth={2.5}
                              dot={{ r: 3 }}
                              name="Total"
                            />
                            <Line
                              type="monotone"
                              dataKey="positif"
                              stroke="#2f9e6a"
                              strokeWidth={2}
                              dot={false}
                            />
                            <Line
                              type="monotone"
                              dataKey="negatif"
                              stroke="#d64545"
                              strokeWidth={2}
                              dot={false}
                            />
                            <Line
                              type="monotone"
                              dataKey="netral"
                              stroke="#EAB308"
                              strokeWidth={2}
                              dot={false}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      )}
                    </CardContent>
                  </Card>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Card className="shadow-sm">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-base">
                        <BarChart3 className="h-4 w-4 text-[color:var(--brand-700)]" /> Frasa 2 Kata
                        Paling Sering Muncul
                      </CardTitle>
                      <CardDescription>
                        Top 15 pasangan kata (bigram) berdasarkan frekuensi.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="h-[420px]">
                      {topBigrams.length === 0 ? (
                        <div className="h-full grid place-items-center text-sm text-muted-foreground">
                          Belum ada data.
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={topBigrams} layout="vertical" margin={{ left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5eefc" />
                            <XAxis type="number" tick={{ fontSize: 11 }} />
                            <YAxis
                              type="category"
                              dataKey="word"
                              tick={{ fontSize: 11 }}
                              width={110}
                            />
                            <Tooltip cursor={{ fill: BRAND.p50 }} />
                            <Bar dataKey="count" fill="#99D0CF" radius={[0, 6, 6, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="shadow-sm">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-base">
                        <BarChart3 className="h-4 w-4 text-[color:var(--brand-700)]" /> Frasa 3 Kata
                        Paling Sering Muncul
                      </CardTitle>
                      <CardDescription>
                        Top 15 rangkaian kata (trigram) berdasarkan frekuensi.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="h-[420px]">
                      {topTrigrams.length === 0 ? (
                        <div className="h-full grid place-items-center text-sm text-muted-foreground">
                          Belum ada data.
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={topTrigrams} layout="vertical" margin={{ left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5eefc" />
                            <XAxis type="number" tick={{ fontSize: 11 }} />
                            <YAxis
                              type="category"
                              dataKey="word"
                              tick={{ fontSize: 11 }}
                              width={130}
                            />
                            <Tooltip cursor={{ fill: BRAND.p50 }} />
                            <Bar dataKey="count" fill="#BFDDF0" radius={[0, 6, 6, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              {/* LDA */}
              <TabsContent value="topics" className="space-y-6">
                <Card className="shadow-sm">
                  <CardHeader>
                    <CardTitle className="text-base">Topik Utama (LDA)</CardTitle>
                    <CardDescription>
                      Jumlah topik dicari otomatis berdasarkan coherence score; nama tema tiap topik
                      dibuat otomatis (AI atau dari kata kuncinya sendiri kalau AI tidak tersedia).
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {ldaTopics.length === 0 ? (
                      <div className="py-10 text-center text-sm text-muted-foreground">
                        Data terlalu sedikit untuk topic modeling yang bermakna (minimal ±10 berita
                        dengan variasi kata yang cukup setelah cleaning).
                      </div>
                    ) : (
                      ldaTopics.map((t) => (
                        <div key={t.id} className="rounded-xl border border-border p-4 bg-white">
                          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                            <div className="flex items-center gap-3">
                              <div
                                className="h-9 w-9 rounded-lg grid place-items-center font-bold text-white"
                                style={{ background: BRAND.p700 }}
                              >
                                T{t.id}
                              </div>
                              <div>
                                <div className="font-semibold">{t.label}</div>
                                <div className="text-xs text-muted-foreground">
                                  {t.jumlah_berita} berita
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-3 min-w-[240px]">
                              <Progress value={t.share} className="h-2 flex-1" />
                              <span className="text-sm font-bold text-[color:var(--brand-700)] w-12 text-right">
                                {t.share}%
                              </span>
                            </div>
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            {t.terms.map((term, i) => (
                              <span key={term} className="inline-flex items-center gap-2">
                                <span
                                  className="px-2.5 py-1 rounded-md text-xs font-medium"
                                  style={{
                                    background: BRAND.p50,
                                    color: BRAND.p700,
                                    border: `1px solid ${BRAND.p200}`,
                                  }}
                                >
                                  {term}
                                </span>
                                {i < t.terms.length - 1 && (
                                  <span className="text-muted-foreground text-xs">,</span>
                                )}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* News */}
              <TabsContent value="news" className="space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <Card className="lg:col-span-2 shadow-sm">
                    <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
                      <div>
                        <CardTitle className="text-base">Contoh Berita Hasil Scraping</CardTitle>
                        <CardDescription>
                          {selectedSources.length > 0
                            ? `Menampilkan ${filteredArticles.length} dari ${result?.articles?.length ?? 0} berita (difilter).`
                            : "Setelah cleaning, validasi & deduplikasi."}
                        </CardDescription>
                      </div>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-2 shrink-0"
                            disabled={availableSources.length === 0}
                          >
                            <Filter className="h-3.5 w-3.5" />
                            Sumber
                            {selectedSources.length > 0 && (
                              <Badge
                                variant="outline"
                                className="ml-0.5 px-1.5 py-0 text-[10px] border-[color:var(--brand-200)]"
                              >
                                {selectedSources.length}
                              </Badge>
                            )}
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="max-h-72 overflow-y-auto">
                          <DropdownMenuLabel className="flex items-center justify-between gap-2">
                            <span>Tampilkan sumber</span>
                            {selectedSources.length > 0 && (
                              <button
                                onClick={() => {
                                  setSelectedSources([]);
                                  setCurrentPage(1);
                                }}
                                className="text-xs font-normal text-[color:var(--brand-700)] hover:underline"
                              >
                                Reset
                              </button>
                            )}
                          </DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          {availableSources.map((src) => (
                            <DropdownMenuCheckboxItem
                              key={src}
                              checked={selectedSources.includes(src)}
                              onCheckedChange={() => toggleSource(src)}
                              onSelect={(e) => e.preventDefault()}
                            >
                              {src}
                            </DropdownMenuCheckboxItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </CardHeader>
                    <CardContent>
                      {newsList.length === 0 ? (
                        <div className="py-8 text-center text-sm text-muted-foreground">
                          Tidak ada berita yang cocok dengan filter sumber ini.
                        </div>
                      ) : (
                        <Accordion type="single" collapsible className="w-full">
                          {newsList.map((n, i) => (
                            <AccordionItem key={i} value={`item-${i}`}>
                              <AccordionTrigger className="hover:no-underline">
                                <div className="flex items-start gap-3 text-left pr-2">
                                  <div className="mt-1.5">
                                    <SentimentDot s={n.sentiment} />
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <div className="font-semibold text-sm leading-snug">
                                      {n.title}
                                    </div>
                                    <div className="text-xs text-muted-foreground mt-1">
                                      {n.source} · {n.date}
                                    </div>
                                  </div>
                                  <Badge
                                    variant="outline"
                                    className="capitalize border-[color:var(--brand-200)] shrink-0"
                                  >
                                    {n.sentiment}
                                  </Badge>
                                </div>
                              </AccordionTrigger>
                              <AccordionContent>
                                <p className="text-sm leading-relaxed whitespace-pre-line text-muted-foreground pl-6">
                                  {n.content || "Isi berita tidak tersedia."}
                                </p>
                                {n.url && (
                                  <a
                                    href={n.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="pl-6 mt-2 inline-block text-xs font-medium text-[color:var(--brand-700)] hover:underline"
                                  >
                                    Buka artikel asli ↗
                                  </a>
                                )}
                              </AccordionContent>
                            </AccordionItem>
                          ))}
                        </Accordion>
                      )}

                      {filteredArticles.length > PAGE_SIZE && (
                        <Pagination className="mt-4">
                          <PaginationContent>
                            <PaginationItem>
                              <PaginationPrevious
                                href="#"
                                onClick={(e) => {
                                  e.preventDefault();
                                  setCurrentPage((p) => Math.max(1, p - 1));
                                }}
                                className={
                                  currentPage === 1 ? "pointer-events-none opacity-40" : ""
                                }
                              />
                            </PaginationItem>
                            {Array.from({ length: totalPages }, (_, i) => i + 1)
                              .filter(
                                (p) =>
                                  p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1,
                              )
                              .map((p, idx, arr) => (
                                <PaginationItem key={p}>
                                  {idx > 0 && arr[idx - 1] !== p - 1 ? (
                                    <span className="px-2 text-muted-foreground">…</span>
                                  ) : null}
                                  <PaginationLink
                                    href="#"
                                    isActive={p === currentPage}
                                    onClick={(e) => {
                                      e.preventDefault();
                                      setCurrentPage(p);
                                    }}
                                  >
                                    {p}
                                  </PaginationLink>
                                </PaginationItem>
                              ))}
                            <PaginationItem>
                              <PaginationNext
                                href="#"
                                onClick={(e) => {
                                  e.preventDefault();
                                  setCurrentPage((p) => Math.min(totalPages, p + 1));
                                }}
                                className={
                                  currentPage === totalPages ? "pointer-events-none opacity-40" : ""
                                }
                              />
                            </PaginationItem>
                          </PaginationContent>
                        </Pagination>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="shadow-sm">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-base">
                        <Sparkles className="h-4 w-4 text-[color:var(--brand-700)]" /> Ringkasan
                      </CardTitle>
                      <CardDescription>
                        Isu utama periode {month} {year}.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm leading-relaxed">
                      <p>
                        Selama <b>{dateRange}</b>, ditemukan{" "}
                        <b>{stats!.unique.toLocaleString("id-ID")} berita unik</b> yang membahas{" "}
                        <b>{keyword.toLowerCase()}</b>.
                      </p>
                      <p>
                        Sentimen{" "}
                        <b className="text-[color:var(--negative)]">negatif ({negatifPct}%)</b> dan{" "}
                        <b className="text-[color:var(--positive)]">positif ({positifPct}%)</b>{" "}
                        berdasarkan klasifikasi {sentimentMethodText} terhadap teks lengkap artikel.
                      </p>
                      <Separator />
                      <div className="text-xs text-muted-foreground">
                        Total kandidat dicoba: {result?.total_pool_dicoba ?? "-"} · Berhasil
                        di-scrape: {result?.jumlah_didapat ?? "-"}
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        className="w-full gap-2 mt-2"
                        disabled={exporting}
                        onClick={exportExcel}
                      >
                        {exporting ? (
                          <RefreshCw className="h-4 w-4 animate-spin" />
                        ) : (
                          <Download className="h-4 w-4" />
                        )}
                        Export Ringkasan (Excel)
                      </Button>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
            </Tabs>
          </>
        )}

        <footer className="text-center text-xs text-muted-foreground py-6">
          <div className="mx-auto flex max-w-6xl flex-col items-center justify-center gap-1 px-5 py-8 text-center text-xs text-muted-foreground">
            <span>© {new Date().getFullYear()} · Daerah Istimewa Yogyakarta</span>
            <span>Developed by Fiki Vania Arun Fadila &amp; Ananda Auliya Rahma</span>
          </div>
        </footer>
      </main>
    </div>
  );
}

/* --- Helpers --- */
function AnalysisStepsFlow({ progressNote }: { progressNote: string | null }) {
  const { stepIndex, pct } = parseStepProgress(progressNote);
  const activeStep = ANALYSIS_STEPS[stepIndex];

  return (
    <Card className="border-border/60 shadow-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <RefreshCw className="h-4 w-4 text-[color:var(--brand-700)] animate-spin" />
          Alur Pengolahan Analisis
        </CardTitle>
        <CardDescription>
          Tahapan yang dijalankan sistem setelah kamu menekan <b>Jalankan Analisis</b>. Setiap
          langkah ditampilkan secara transparan agar prosesnya dapat dipantau.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-8">
        <div
          className="rounded-2xl p-4 flex items-center justify-between gap-4"
          style={{ background: BRAND.p50, border: `1px solid ${BRAND.p200}` }}
        >
          <div className="flex items-center gap-3">
            <div
              className="h-10 w-10 rounded-full grid place-items-center text-white shrink-0 font-bold text-sm"
              style={{ background: BRAND.p700 }}
            >
              {stepIndex + 1}
            </div>
            <div>
              <div className="font-semibold text-sm">{activeStep.label}</div>
              <div className="text-xs text-muted-foreground">
                {progressNote ?? "Menyiapkan tahap berikutnya..."}
              </div>
            </div>
          </div>
          {pct > 0 && (
            <Badge className="bg-[color:var(--brand-700)] text-white shrink-0">{pct}%</Badge>
          )}
        </div>
        {pct > 0 && <Progress value={pct} className="h-1.5 -mt-4" />}

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-y-6 gap-x-2">
          {ANALYSIS_STEPS.map((step, i) => {
            const done = i < stepIndex;
            const current = i === stepIndex;
            return (
              <div
                key={step.label}
                className="relative flex flex-col items-center text-center px-2"
              >
                {i < ANALYSIS_STEPS.length - 1 && (
                  <div
                    className="hidden lg:block absolute top-5 left-1/2 w-full h-[2px] -z-0"
                    style={{ background: done ? BRAND.p700 : BRAND.p200 }}
                  />
                )}
                <div
                  className="relative z-10 h-10 w-10 rounded-full grid place-items-center border-2 mb-2 bg-white font-bold text-sm"
                  style={{
                    background: done ? BRAND.p700 : "white",
                    borderColor: done || current ? BRAND.p700 : BRAND.p200,
                    color: done ? "white" : current ? BRAND.p700 : "#9ca3af",
                  }}
                >
                  {done ? <CheckCircle2 className="h-5 w-5" /> : i + 1}
                </div>
                <div className="text-xs font-semibold leading-snug">{step.label}</div>
                <div className="text-[11px] text-muted-foreground leading-snug mt-0.5">
                  {step.desc}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
function ConfusionMatrixLegend({ matrix, labels }: { matrix: number[][]; labels: string[] }) {
  const diagExample = { label: labels[0], val: matrix[0]?.[0] ?? 0 };

  const offDiagExamples: { actual: string; pred: string; val: number }[] = [];
  matrix.forEach((row, i) => {
    row.forEach((v, j) => {
      if (i !== j && v > 0) {
        offDiagExamples.push({ actual: labels[i], pred: labels[j], val: v });
      }
    });
  });
  offDiagExamples.sort((a, b) => b.val - a.val);
  const topOffDiag = offDiagExamples.slice(0, 2);

  return (
    <div
      className="rounded-2xl p-4 mt-4 space-y-2 text-sm"
      style={{ background: BRAND.p50, border: `1px solid ${BRAND.p200}` }}
    >
      <div className="flex items-center gap-2 font-semibold text-[color:var(--brand-700)]">
        <AlertTriangle className="h-4 w-4" />
        Cara Membaca Confusion Matrix
      </div>
      <ul className="space-y-1.5 text-muted-foreground list-disc pl-5">
        <li>
          <b className="text-foreground">Baris</b> menunjukkan{" "}
          <b className="text-foreground">label aktual</b> (sentimen sebenarnya dari data uji),
          sedangkan <b className="text-foreground">kolom</b> menunjukkan{" "}
          <b className="text-foreground">prediksi model</b>.
        </li>
        <li>
          Angka yang <b className="text-foreground">berwarna biru tua (diagonal)</b> adalah prediksi
          yang <b className="text-foreground">benar</b>. Misalnya, {diagExample.val} berita{" "}
          {diagExample.label.toLowerCase()} berhasil dikenali sebagai{" "}
          {diagExample.label.toLowerCase()}.
        </li>
        {topOffDiag.length > 0 && (
          <li>
            Angka di luar diagonal adalah <b className="text-foreground">kesalahan klasifikasi</b>.
            Contoh:{" "}
            {topOffDiag
              .map(
                (ex) =>
                  `${ex.val} berita yang sebenarnya ${ex.actual.toLowerCase()} malah diprediksi ${ex.pred.toLowerCase()}`,
              )
              .join(", atau ")}
            .
          </li>
        )}
        <li>
          Semakin banyak angka di diagonal dan semakin sedikit di luar diagonal, semakin baik
          performa model.
        </li>
      </ul>
    </div>
  );
}
function KpiCard({
  icon,
  label,
  value,
  sub,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  tone?: "positive" | "negative" | "neutral";
}) {
  const accent =
    tone === "positive"
      ? "var(--positive)"
      : tone === "negative"
        ? "var(--negative)"
        : "var(--brand-700)";
  return (
    <Card className="shadow-sm">
      <CardContent className="p-4">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-semibold uppercase tracking-wide">{label}</span>
          {icon}
        </div>
        <div
          className="mt-2 text-2xl font-bold"
          style={{ color: `color-mix(in oklab, ${accent}, black 5%)` }}
        >
          {value}
        </div>
        {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
      </CardContent>
    </Card>
  );
}

function SentimentDot({ s }: { s: string }) {
  const color =
    s === "positif" ? "var(--positive)" : s === "negatif" ? "var(--negative)" : "var(--brand-400)";
  return (
    <span className="inline-block h-2.5 w-2.5 rounded-full mt-1" style={{ background: color }} />
  );
}

function Wordcloud({ words }: { words: { text: string; weight: number }[] }) {
  if (words.length === 0) {
    return (
      <div className="min-h-[280px] grid place-items-center text-sm text-muted-foreground">
        Belum ada data kata kunci.
      </div>
    );
  }

  const max = Math.max(...words.map((w) => w.weight));
  const min = Math.min(...words.map((w) => w.weight));
  const palette = [BRAND.p700, "#1e4d80", BRAND.p400, "#5a97d8", BRAND.p200];
  return (
    <div
      className="min-h-[280px] rounded-xl p-6 flex flex-wrap items-center justify-center gap-x-4 gap-y-2"
      style={{
        background: `radial-gradient(circle at 30% 30%, ${BRAND.p50}, white 70%)`,
        border: `1px solid ${BRAND.p200}`,
      }}
    >
      {words.map((w, i) => {
        const t = max === min ? 0.5 : (w.weight - min) / (max - min);
        const size = 14 + t * 34;
        const weight = 400 + Math.round(t * 4) * 100;
        const color = palette[i % palette.length];
        const rot = i % 5 === 0 ? "-4deg" : i % 7 === 0 ? "3deg" : "0deg";
        const opacity = 0.55 + t * 0.45;
        return (
          <span
            key={w.text}
            className="whitespace-nowrap leading-none select-none"
            style={{
              fontSize: `${size}px`,
              fontWeight: weight,
              color,
              opacity,
              transform: `rotate(${rot})`,
              letterSpacing: "-0.01em",
            }}
          >
            {w.text}
          </span>
        );
      })}
    </div>
  );
}
