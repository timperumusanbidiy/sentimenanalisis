import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import {
  Info,
  ArrowRight,
  BarChart3,
  Brain,
  Database,
  Github,
  Mail,
  MapPin,
  Newspaper,
  Phone,
  Play,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  FileSpreadsheet,
  Filter,
  AlertTriangle,
} from "lucide-react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

import { Progress } from "@/components/ui/progress";
import diy from "@/assets/diy.png";
import bantul from "@/assets/bantul.jpeg";
import sleman from "@/assets/sleman.jpeg";
import kulonprogo from "@/assets/kulonprogo.jpeg";
import gunungkidul from "@/assets/gunungkidul.jpeg";
import jogjakota from "@/assets/jogjakota.jpeg";
import mockup from "@/assets/mockup.png";
import logo from "@/assets/logo.png";
import BI_Logo from "@/assets/BI_Logo.png";
import tutorialVideo from "@/assets/tutorial.mp4";
import cover from "@/assets/cover.jpeg"

export const Route = createFileRoute("/")({
  component: LandingPage,
  head: () => ({
    meta: [
      { title: "SentimenDIY — Analitik Sentimen Berita Ekonomi Yogyakarta" },
      {
        name: "description",
        content:
          "Platform analisis sentimen berita ekonomi & inflasi se-DIY: scraping, klasifikasi, topik LDA, dan ringkasan otomatis dalam satu dasbor.",
      },
      { property: "og:title", content: "SentimenDIY — Analitik Sentimen Berita Ekonomi" },
      {
        property: "og:description",
        content:
          "Pantau sentimen berita ekonomi Daerah Istimewa Yogyakarta secara real-time dengan model SVM dan topik LDA.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

const MOCK_BARS = [42, 58, 35, 72, 50, 88, 64, 79, 46, 92, 61, 74];

const FEATURES = [
  {
    icon: Newspaper,
    title: "Scraping Berita Otomatis",
    desc: "Mengambil hingga 1.000 artikel per periode sesuai kata kunci, lengkap dengan isi berita.",
  },
  {
    icon: Brain,
    title: "Klasifikasi Support Vector Machine (SVM)",
    desc: "Mengklasifikasikan sentimen berita menjadi positif, negatif, dan netral. Performa dievaluasi berdasarkan akurasi, presisi, recall, dan F1-score.",
  },
  {
    icon: BarChart3,
    title: "Topik LDA & Wordcloud",
    desc: "Temukan tema dominan seperti pangan, energi, dan daya beli beserta kata kunci pembentuknya.",
  },
  {
    icon: TrendingUp,
    title: "Tren Harian",
    desc: "Memantau pergerakan sentimen harian dan komoditas paling banyak diberitakan sepanjang bulan.",
  },
  {
    icon: Filter,
    title: "Deteksi Duplikat",
    desc: "Menghapus berita yang memiliki konten serupa dari berbagai sumber, sehingga hasil analisis lebih akurat.",
  },
  {
    icon: FileSpreadsheet,
    title: "Export Laporan",
    desc: "Mengekspor hasil analisis lengkap ke dalam format Excel sehingga memudahkan dokumentasi.",
  },
];

const VALIDATION = {
  note: "Evaluasi dilakukan pada data uji hasil anotasi manual terakhir.",
  accuracy: 0.78,
  precision: 0.76,
  recall: 0.77,
  f1: 0.765,
  trainSize: 800,
  testSize: 200,
  labels: ["Positif", "Negatif", "Netral"],
  confusionMatrix: [
    [62, 5, 8],
    [6, 58, 9],
    [7, 8, 65],
  ],
};
function getMetricTone(val: number) {
  const pct = val * 100;
  if (pct < 50) return { text: "text-red-600", bar: "#d64545" };
  if (pct < 70) return { text: "text-amber-600", bar: "#D97706" };
  return { text: "text-green-600", bar: "#16A34A" };
}

const VALIDATION_METRICS = [
  {
    label: "Accuracy",
    val: VALIDATION.accuracy,
    desc: (v: number) =>
      `Akurasi adalah persentase jumlah prediksi yang benar dari seluruh data yang diuji. Nilai akurasi ${(
        v * 100
      )
        .toFixed(1)
        .replace(".", ",")}% menunjukkan bahwa model berhasil mengklasifikasikan ${(v * 100)
        .toFixed(1)
        .replace(".", ",")}% berita dengan benar.`,
  },
  {
    label: "Precision",
    val: VALIDATION.precision,
    desc: (v: number) =>
      `Precision adalah persentase prediksi positif yang benar dibandingkan dengan seluruh data yang diprediksi positif oleh model. Nilai precision ${(
        v * 100
      )
        .toFixed(1)
        .replace(".", ",")}% berarti dari seluruh berita yang diprediksi positif, sekitar ${(
        v * 100
      )
        .toFixed(1)
        .replace(".", ",")}% di antaranya benar-benar positif.`,
  },
  {
    label: "Recall",
    val: VALIDATION.recall,
    desc: (v: number) =>
      `Recall adalah persentase data yang sebenarnya termasuk dalam suatu kelas dan berhasil dikenali dengan benar oleh model. Nilai recall ${(
        v * 100
      )
        .toFixed(1)
        .replace(".", ",")}% berarti model berhasil menemukan ${(v * 100)
        .toFixed(1)
        .replace(".", ",")}% dari seluruh berita yang sebenarnya termasuk dalam kelas tersebut.`,
  },
  {
    label: "F1-Score",
    val: VALIDATION.f1,
    desc: (v: number) =>
      `F1-Score menggambarkan keseimbangan antara Precision dan Recall dalam mengukur kinerja model. Nilai F1-Score ${(
        v * 100
      )
        .toFixed(1)
        .replace(
          ".",
          ",",
        )}% menunjukkan kemampuan model dalam menghasilkan prediksi yang tepat dan menemukan data yang relevan berada pada tingkat ${(
        v * 100
      )
        .toFixed(1)
        .replace(".", ",")}%.`,
  },
];

function ConfusionMatrixLegend() {
  const { labels, confusionMatrix: matrix } = VALIDATION;
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
      style={{
        background: "var(--brand-50)",
        border: "1px solid var(--brand-200)",
      }}
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
// --- CountUp ---
function CountUp({
  end,
  duration = 1200,
  decimals = 0,
  suffix = "",
}: {
  end: number;
  duration?: number;
  decimals?: number;
  suffix?: string;
}) {
  const [value, setValue] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const hasRun = useRef(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasRun.current) {
          hasRun.current = true;
          const start = performance.now();

          const tick = (now: number) => {
            const progress = Math.min((now - start) / duration, 1);
            // easeOutCubic biar animasinya melambat di akhir
            const eased = 1 - Math.pow(1 - progress, 3);
            setValue(end * eased);
            if (progress < 1) requestAnimationFrame(tick);
          };

          requestAnimationFrame(tick);
        }
      },
      { threshold: 0.3 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [end, duration]);

  return (
    <span ref={ref}>
      {value.toFixed(decimals).replace(".", ",")}
      {suffix}
    </span>
  );
}

// --- MetricCard ---
function MetricCard({
  label,
  val,
  desc,
}: {
  label: string;
  val: number; // persentase, misal 89.2
  desc: string;
}) {
  const tone = getMetricTone(val / 100); // getMetricTone mengharapkan pecahan 0-1

  return (
    <div className="rounded-2xl bg-card p-6 ring-1 ring-border">
      <p className="text-sm font-semibold text-muted-foreground">{label}</p>
      <p className={`mt-2 text-3xl font-extrabold ${tone.text}`}>
        <CountUp end={val} decimals={1} suffix="%" />
      </p>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full rounded-full transition-all duration-1000"
          style={{ width: `${val}%`, backgroundColor: tone.bar }}
        />
      </div>
      <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{desc}</p>
    </div>
  );
}
function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <style>{`
        @keyframes floaty { 0%,100% { transform: translateY(0) rotate(-2deg);} 50% { transform: translateY(-14px) rotate(2deg);} }
        .floaty { animation: floaty 6s ease-in-out infinite; }
      html { scroll-snap-type: y proximity; }
      `}</style>

      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-border/70 bg-background/80 backdrop-blur">
        <div className="mx-auto grid max-w-6xl grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-5 py-3 sm:flex sm:justify-between">
          <div className="flex min-w-0 items-center gap-2.5">
            <img
              src={BI_Logo}
              alt="Logo SentimenDIY"
              className="h-8 w-8 shrink-0 rounded-lg object-cover"
            />
            <img
              src={logo}
              alt="Logo SentimenDIY"
              className="h-9 w-auto shrink-0 object-contain sm:h-10.5"
            />
            <img
              src={diy}
              alt="Logo SentimenDIY"
              className="h-9 w-auto shrink-0 object-contain sm:h-10.5"
            />
          </div>
          <nav className="hidden items-center gap-7 text-sm text-muted-foreground md:flex">
            <a href="#fitur" className="transition-colors hover:text-primary">
              Fitur
            </a>
            <a href="#tutorial" className="transition-colors hover:text-primary">
              Tutorial
            </a>
            <a href="#validasi" className="transition-colors hover:text-primary">
              Validasi Model
            </a>
            <a href="#faq" className="transition-colors hover:text-primary">
              FAQ
            </a>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden px-5 pb-28 pt-16 sm:pt-24">
        {/* Pita transisi: gradasi biru muda cuma di seam bawah Hero, blend ke putih di section berikutnya */}
        <div
          className="pointer-events-none absolute inset-x-0 bottom-0 h-[420px]"
          style={{
            background:
              "linear-gradient(to bottom, transparent 0%, color-mix(in srgb, var(--brand-400) 16%, white) 55%, #ffffff 100%)",
          }}
        />
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.35]"
          style={{
            backgroundImage:
              "linear-gradient(to right, var(--border) 1px, transparent 1px), linear-gradient(to bottom, var(--border) 1px, transparent 1px)",
            backgroundSize: "96px 96px",
            maskImage: "radial-gradient(70% 60% at 50% 40%, black, transparent)",
          }}
        />

        <div className="relative mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-[1.05fr_1fr]">
          {/* Copy */}
          <div className="text-center lg:text-left">
            <h1 className="mt-6 text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-5xl xl:text-6xl">
              Monitoring Berita dan Analisis Opini.
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-sm text-muted-foreground sm:text-base lg:mx-0">
              Website ini dikembangkan oleh Bank Indonesia KPw DIY sebagai platform analisis
              sentimen berita berbasis machine learning. Hasil analisis yang disajikan bertujuan
              untuk menambah wawasan, mempermudah pemantauan isu, dan mendukung pengambilan
              keputusan berbasis data.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3 lg:justify-start">
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-2 rounded-full bg-foreground px-6 py-3 text-sm font-semibold text-background transition-transform hover:scale-[1.03]"
              >
                Mulai Analisis <ArrowRight className="h-4 w-4" />
              </Link>
              <a
                href="#tutorial"
                className="inline-flex items-center gap-2 rounded-full bg-card px-6 py-3 text-sm font-semibold text-foreground ring-1 ring-border transition-transform hover:scale-[1.03]"
              >
                Lihat Tutorial
              </a>
            </div>
          </div>

          {/* Mockup aplikasi */}
          <div className="relative mx-auto w-full max-w-lg">
            <div className="floaty">
              <img
                src={mockup}
                alt="Mockup Dashboard SentimenDIY"
                className="h-auto w-full object-cover"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="fitur" className="mx-auto max-w-6xl px-5 py-20">
        <div className="max-w-2xl">
          <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Fitur</h2>
        </div>
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="rounded-2xl bg-card p-6 ring-1 ring-border transition-shadow hover:shadow-[0_20px_45px_-25px_rgba(54,116,181,0.6)]"
            >
              <div className="grid h-11 w-11 place-items-center rounded-xl bg-secondary text-secondary-foreground">
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-base font-bold">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Tutorial */}
      <section id="tutorial" className="mx-auto max-w-6xl px-5 py-20">
        <div className="max-w-2xl">
          <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Cara Pakai</h2>
          <p className="mt-3 text-sm text-muted-foreground sm:text-base">
            Tonton panduan singkat atau ikuti langkah-langkah di bawah untuk mulai menganalisis
            sentimen berita ekonomi DIY.
          </p>
        </div>

        {/* Video player */}
        <div className="mt-10 overflow-hidden rounded-3xl bg-card p-3 ring-1 ring-border shadow-[0_40px_80px_-45px_rgba(54,116,181,0.7)] sm:p-5">
          <div className="relative aspect-video overflow-hidden rounded-2xl bg-background ring-1 ring-border">
            <video
              src={tutorialVideo}
              controls
              poster={cover}
              className="h-full w-full object-cover"
            >
              Browser kamu tidak mendukung tag video.
            </video>
          </div>
          <div className="px-2 pt-4 sm:px-4">
            <h3 className="text-sm font-bold">Panduan lengkap penggunaan dasbor SentimenDIY</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Dari menentukan kata kunci hingga mengekspor laporan analisis.
            </p>
          </div>
        </div>

        {/* Step cards */}
        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {[
            {
              n: "01",
              t: "Tentukan Periode & Kata Kunci",
              d: "Pilih bulan, tahun, jumlah berita, dan kata kunci seperti inflasi atau pangan.",
            },
            {
              n: "02",
              t: "Jalankan Analisis",
              d: "Sistem melakukan scraping, normalisasi, deduplikasi, klasifikasi sentimen, dan ekstraksi topik.",
            },
            {
              n: "03",
              t: "Baca & Ekspor",
              d: "Pantau hasil analisis melalui dashboard interaktif dan ekspor laporan ke format Excel dengan mudah.",
            },
          ].map((s) => (
            <div key={s.n} className="rounded-2xl bg-card p-6 ring-1 ring-border">
              <span className="text-sm font-extrabold text-accent">{s.n}</span>
              <h3 className="mt-2 text-base font-bold">{s.t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Validasi Model */}
      <section id="validasi" className="mx-auto max-w-6xl px-5 py-20">
        <div className="max-w-2xl">
          <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Validasi model</h2>
          <p className="mt-3 text-sm text-muted-foreground sm:text-base">
            Metrik dihitung dari held-out test set berisi 370 label manusia asli.{" "}
          </p>
        </div>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              label: "Accuracy",
              val: 71.9,
              desc: "Persentase prediksi yang benar secara keseluruhan. Akurasi 71,9% artinya sekitar 178 dari 200 berita diklasifikasikan dengan benar.",
            },
            {
              label: "Precision",
              val: 72.8,
              desc: "Seberapa yakin terhadap hasil positif yang diprediksi. Precision 72,8% berarti peluang benar saat model menyatakan positif mencapai 72,8%.",
            },
            {
              label: "Recall",
              val: 71.9,
              desc: "Kemampuan model menemukan seluruh berita yang seharusnya masuk suatu kelas. Recall 71,9% berarti 71,9% kasus relevan berhasil tertangkap.",
            },
            {
              label: "F1-Score",
              val: 72.2,
              desc: "Rata-rata harmonis Precision dan Recall. F1-Score 72,2% menunjukkan keseimbangan baik antara prediksi tepat dan menemukan kasus relevan.",
            },
          ].map((m) => (
            <MetricCard key={m.label} label={m.label} val={m.val} desc={m.desc} />
          ))}
        </div>

        <div className="mt-6 grid gap-5 lg:grid-cols-5">
          <div className="rounded-2xl bg-background p-6 ring-1 ring-border lg:col-span-3">
            <h3 className="text-base font-bold">Confusion Matrix</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Model: SVM · sampel: 1850 berita.
            </p>
            <div className="mt-5 overflow-hidden rounded-xl ring-1 ring-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-secondary/60">
                    <th className="p-3 text-left font-semibold"></th>
                    <th className="p-3 font-semibold">Pred: Positif</th>
                    <th className="p-3 font-semibold">Pred: Negatif</th>
                    <th className="p-3 font-semibold">Pred: Netral</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { label: "Aktual: Positif", vals: [135, 12, 30] },
                    { label: "Aktual: Negatif", vals: [8, 69, 18] },
                    { label: "Aktual: Netral", vals: [20, 16, 62] },
                  ].map((r, i) => (
                    <tr key={r.label} className="border-t border-border">
                      <td className="bg-secondary/30 p-3 font-semibold">{r.label}</td>
                      {r.vals.map((v, j) => (
                        <td key={j} className="p-3 text-center font-mono">
                          <span
                            className={`inline-block min-w-[3rem] rounded-md px-3 py-1 font-semibold ${
                              i === j
                                ? "bg-primary text-primary-foreground"
                                : "bg-secondary text-secondary-foreground"
                            }`}
                          >
                            <CountUp end={v} />
                          </span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-2xl bg-card/70 p-6 ring-1 ring-border lg:col-span-2">
            <h3 className="flex items-center gap-2 text-sm font-bold">
              <Info className="h-4 w-4 text-primary" /> Cara membaca confusion matrix
            </h3>
            <ul className="mt-3 list-disc space-y-2 pl-4 text-sm leading-relaxed text-muted-foreground">
              <li>
                <b className="text-foreground">Baris</b> = label aktual (sentimen sebenarnya),
                <b className="text-foreground"> kolom</b> = prediksi model.
              </li>
              <li>
                Angka berlatar biru (diagonal) adalah prediksi{" "}
                <b className="text-foreground">benar</b>. Contoh: 135 berita positif dikenali sebagai
                positif.
              </li>
              <li>
                Angka di luar diagonal adalah{" "}
                <b className="text-foreground">kesalahan klasifikasi</b>, misalnya 18 berita negatif
                diprediksi netral.
              </li>
              <li>
                Semakin banyak angka di diagonal dan sedikit di luar diagonal, semakin baik performa
                model.
              </li>
            </ul>
          </div>
        </div>
        <div
          className="mt-14 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-6 rounded-3xl p-8 text-primary-foreground sm:flex sm:justify-between sm:p-10"
          style={{ background: "linear-gradient(120deg, var(--brand-700), var(--brand-400))" }}
        >
          <div className="min-w-0">
            <h3 className="text-xl font-extrabold sm:text-2xl">Siap melihat sentimen bulan ini?</h3>
            <p className="mt-2 text-sm opacity-90">
              Temukan insight dari ribuan berita ekonomi dalam satu platform.
            </p>
          </div>
          <Link
            to="/dashboard"
            className="inline-flex shrink-0 items-center gap-2 rounded-full bg-card px-5 py-3 text-sm font-semibold text-primary"
          >
            Buka Dashboard <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="mx-auto max-w-3xl px-5 py-20">
        <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
          Pertanyaan yang sering diajukan
        </h2>
        <Accordion type="single" collapsible className="mt-8">
          {[
            {
              q: "Dari mana data berita diperoleh?",
              a: "Data berita diperoleh dari Google News yang memuat berbagai portal berita nasional. Pencarian dilakukan berdasarkan kata kunci dan rentang waktu yang dipilih, kemudian artikel yang terduplikasi akan disaring sebelum dianalisis.",
            },
            {
              q: "Seberapa akurat hasil klasifikasi sentimennya?",
              a: "Berdasarkan pengujian pada data uji, model mencapai akurasi sekitar 71.9% dengan performa yang relatif seimbang pada setiap kelas sentimen. Detail metrik evaluasi dan confusion matrix tersedia pada tab Validasi Model untuk membantu melihat performa model secara lebih menyeluruh.",
            },
            {
              q: "Apakah hasil analisis dapat diekspor?",
              a: "Bisa. Hasil analisis dapat diunduh sebagai CSV/Excel mencakup informasi berita seperti judul, tanggal, sumber, label sentimen, dan topik, serta dapat digunakan untuk dokumentasi maupun kebutuhan analisis dan pelaporan.",
            },
          ].map((f, i) => (
            <AccordionItem key={f.q} value={`faq-${i}`}>
              <AccordionTrigger className="text-left text-sm font-semibold">{f.q}</AccordionTrigger>
              <AccordionContent className="text-sm leading-relaxed text-muted-foreground">
                {f.a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </section>

      <footer className="text-center text-xs text-muted-foreground py-6">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-center gap-1 px-5 py-8 text-center text-xs text-muted-foreground">
          <span>
            © {new Date().getFullYear()} · Kantor Perwakilan Bank Indonesia Daerah Istimewa
            Yogyakarta
          </span>
          <span>Developed by Fiki Vania Arun Fadila &amp; Ananda Auliya Rahma</span>
        </div>
      </footer>
    </div>
  );
}
