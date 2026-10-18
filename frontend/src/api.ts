import type { AnalysisResult } from "./types";
const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function analyze(resume: File, jd: string): Promise<AnalysisResult> {
  const body = new FormData();
  body.append("resume", resume);
  body.append("job_description", jd);
  let res: Response;
  try {
    res = await fetch(`${BASE}/api/analyze`, { method: "POST", body });
  } catch {
    throw new Error("Can't reach the analysis server. Make sure the backend is running on port 8000.");
  }
  if (!res.ok) {
    const j = await res.json().catch(() => null);
    throw new Error(typeof j?.detail === "string" ? j.detail : "Analysis failed. Please try again.");
  }
  return res.json();
}
