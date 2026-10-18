export type Status = "matched" | "partial" | "missing";
export type Importance = "high" | "medium" | "low";
export interface Requirement {
  id: string; text: string; kind: string; importance: Importance; status: Status;
  evidence: string | null; method: string; similarity: number | null; explanation: string; suggestion: string | null;
}
export interface AnalysisResult {
  score: number; counts: Record<Status, number>; weights: Record<Status, number>; total_weight: number;
  requirements: Requirement[]; disclaimer: string; model: string;
}
