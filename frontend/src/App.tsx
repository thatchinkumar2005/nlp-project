import { useState } from "react";
import { analyze } from "./api";
import type { AnalysisResult, Importance, Requirement, Status } from "./types";

const MAX_BYTES = 5 * 1024 * 1024;
const ST: Record<Status, { label: string; bar: string; text: string; border: string; blurb: string }> = {
  matched: { label: "Matched", bar: "bg-emerald-700", text: "text-emerald-800", border: "border-emerald-700", blurb: "Explicit evidence in your resume." },
  partial: { label: "Partially matched", bar: "bg-amber-500", text: "text-amber-800", border: "border-amber-500", blurb: "Related or indirect evidence only." },
  missing: { label: "Missing", bar: "bg-rose-700", text: "text-rose-800", border: "border-rose-700", blurb: "No convincing evidence found." },
};
const IMP: Record<Importance, string> = { high: "High priority", medium: "Medium priority", low: "Low priority" };

function ReqCard({ r }: { r: Requirement }) {
  return (
    <li className={`bg-white border border-line border-l-4 ${ST[r.status].border} rounded-md p-4`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="font-semibold">{r.text}</h4>
        <span className="text-xs text-slate-600">{IMP[r.importance]}</span>
      </div>
      {r.evidence ? (
        <blockquote className="mt-2 border-l-2 border-line pl-3 text-sm text-slate-700">“{r.evidence}”</blockquote>
      ) : (
        <p className="mt-2 text-sm text-slate-600">No supporting resume text found.</p>
      )}
      <p className="mt-2 text-sm text-slate-700">{r.explanation}</p>
      {r.similarity !== null && <p className="mt-1 text-xs text-slate-500">Semantic similarity {r.similarity.toFixed(2)} · method: {r.method}</p>}
    </li>
  );
}

function Results({ data }: { data: AnalysisResult }) {
  const by = (s: Status) => data.requirements.filter((r) => r.status === s);
  const gaps = data.requirements.filter((r) => r.suggestion);
  return (
    <section aria-labelledby="results" className="mt-10 space-y-8">
      <div className="bg-white border border-line rounded-lg p-6">
        <h2 id="results" className="sr-only">Results</h2>
        <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
          <p className="text-6xl font-bold tabular-nums">{data.score}<span className="text-2xl text-slate-500">/100</span></p>
          <p className="max-w-md text-sm text-slate-700">Importance-weighted requirement coverage. Segments below are sized by how much each group of requirements counts.</p>
        </div>
        <div className="mt-5 flex h-4 overflow-hidden rounded-full bg-line" role="img"
          aria-label={`${data.counts.matched} matched, ${data.counts.partial} partial, ${data.counts.missing} missing`}>
          {(Object.keys(ST) as Status[]).map((s) => (
            <div key={s} className={ST[s].bar} style={{ width: `${(100 * data.weights[s]) / (data.total_weight || 1)}%` }} />
          ))}
        </div>
        <dl className="mt-4 grid grid-cols-3 gap-3 text-sm">
          {(Object.keys(ST) as Status[]).map((s) => (
            <div key={s}><dt className={`font-medium ${ST[s].text}`}>{ST[s].label}</dt><dd className="text-2xl font-semibold">{data.counts[s]}</dd></div>
          ))}
        </dl>
        <p className="mt-4 text-xs text-slate-600">{data.disclaimer}</p>
      </div>

      {(Object.keys(ST) as Status[]).map((s) => (
        <div key={s}>
          <h3 className={`text-lg font-semibold ${ST[s].text}`}>{ST[s].label} ({by(s).length})</h3>
          <p className="text-sm text-slate-600">{ST[s].blurb}</p>
          {by(s).length ? <ul className="mt-3 space-y-3">{by(s).map((r) => <ReqCard key={r.id} r={r} />)}</ul>
            : <p className="mt-3 text-sm text-slate-500">Nothing in this group.</p>}
        </div>
      ))}

      <div>
        <h3 className="text-lg font-semibold">Suggestions</h3>
        <p className="text-sm text-slate-600">Only add what's true. These point to gaps; they don't rewrite your resume.</p>
        {gaps.length ? (
          <ul className="mt-3 space-y-3">
            {gaps.map((r) => (
              <li key={r.id} className="bg-white border border-line rounded-md p-4 text-sm">
                <span className="font-semibold">{r.text}</span> <span className="text-slate-500">({IMP[r.importance]})</span>
                <p className="mt-1 text-slate-700">{r.suggestion}</p>
              </li>
            ))}
          </ul>
        ) : <p className="mt-3 text-sm text-slate-500">No gaps found. Every requirement has evidence.</p>}
      </div>
    </section>
  );
}

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalysisResult | null>(null);

  function pick(f: File | undefined) {
    if (!f) return;
    if (!/\.(pdf|docx)$/i.test(f.name)) return setError("Unsupported file type. Upload a PDF or DOCX resume.");
    if (f.size > MAX_BYTES) return setError("File too large. The limit is 5 MB.");
    setError(null); setFile(f);
  }

  async function run() {
    if (!file) return setError("Upload your resume first.");
    if (!jd.trim()) return setError("Paste a job description first.");
    setError(null); setLoading(true); setData(null);
    try { setData(await analyze(file, jd)); }
    catch (e) { setError(e instanceof Error ? e.message : "Something went wrong."); }
    finally { setLoading(false); }
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-bold tracking-tight">Resume–Job Description Matcher</h1>
      <p className="mt-2 max-w-2xl text-slate-700">
        Upload your resume and paste a job posting. You'll see which requirements your resume covers, with the exact lines that support each one.
        Files are processed in memory and not stored.
      </p>

      <div className="mt-8 grid gap-6 md:grid-cols-5">
        <div className="md:col-span-2">
          <label htmlFor="resume" className="mb-1 block text-sm font-semibold">Resume</label>
          <div onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer.files[0]); }}
            className="flex h-48 flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-400 bg-white p-4 text-center">
            <input id="resume" type="file" accept=".pdf,.docx" className="sr-only" onChange={(e) => pick(e.target.files?.[0])} />
            <label htmlFor="resume" className="cursor-pointer rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white focus-within:outline">
              {file ? "Choose a different file" : "Choose a file"}
            </label>
            <p className="mt-3 text-sm text-slate-700">{file ? file.name : "or drop a PDF or DOCX here (max 5 MB)"}</p>
          </div>
        </div>
        <div className="md:col-span-3">
          <label htmlFor="jd" className="mb-1 block text-sm font-semibold">Job description</label>
          <textarea id="jd" value={jd} onChange={(e) => setJd(e.target.value)} rows={9}
            placeholder={"Paste the full posting. Section headings like “Requirements” and “Nice to have” help rank importance."}
            className="h-48 w-full resize-y rounded-lg border border-line bg-white p-3 text-sm md:h-48" />
        </div>
      </div>

      {error && <p role="alert" className="mt-4 rounded-md border border-rose-700 bg-rose-50 p-3 text-sm text-rose-900">{error}</p>}

      <button onClick={run} disabled={loading}
        className="mt-6 w-full rounded-lg bg-accent px-6 py-3 text-base font-semibold text-white hover:bg-indigo-900 disabled:opacity-60 sm:w-auto">
        {loading ? "Analyzing… (the first run loads the language model)" : "Analyze Resume"}
      </button>

      {data ? <Results data={data} /> : !loading && (
        <p className="mt-10 rounded-lg border border-line bg-white p-5 text-sm text-slate-600">
          Results appear here: an overall coverage score, then every requirement sorted into matched, partial, or missing with resume evidence.
        </p>
      )}
    </main>
  );
}
