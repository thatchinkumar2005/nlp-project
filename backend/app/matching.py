"""Hybrid matcher: keyword/alias evidence + sentence-embedding similarity + contextual validation."""
import re
from dataclasses import dataclass

import numpy as np

from .config import settings
from .extraction import DEG, YEARS, Requirement, degree_level
from .nlp import content_tokens, split_sentences
from .skills import alias_hit, mentions, related

class SentenceTransformerEmbedder:
    def __init__(self, name: str = settings.model_name):
        self.name, self._m = name, None

    def encode(self, texts: list[str]) -> np.ndarray:
        if self._m is None:
            from sentence_transformers import SentenceTransformer
            self._m = SentenceTransformer(self.name)
        return np.asarray(self._m.encode(texts, normalize_embeddings=True, convert_to_numpy=True))

@dataclass
class Result:
    req: Requirement
    status: str                 # matched | partial | missing
    evidence: str | None = None
    method: str = "none"        # exact | alias | related | semantic | rule | none
    similarity: float | None = None
    explanation: str = ""
    related: str | None = None

def _norm(a: np.ndarray) -> np.ndarray:
    a = np.atleast_2d(np.asarray(a, dtype=float))
    n = np.linalg.norm(a, axis=1, keepdims=True)
    return a / np.where(n == 0, 1, n)

def _cut(s: str, n: int = 300) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"

def resume_years(text: str) -> tuple[float, str | None]:
    best, ev = 0.0, None
    for line in split_sentences(text):
        for m in YEARS.finditer(line):
            if int(m.group(1)) > best:
                best, ev = float(m.group(1)), line
    spans = re.findall(r"\b((?:19|20)\d\d)\s*(?:-|–|—|to)\s*((?:19|20)\d\d|present|current|now)\b", text, re.I)
    if spans:
        from datetime import date
        a = [int(s) for s, _ in spans]
        b = [date.today().year if e.lower() in ("present", "current", "now") else int(e) for _, e in spans]
        span = max(b) - min(a)
        if span > best:
            best = float(span)
            ev = next((l for l in split_sentences(text) if re.search(spans[0][0], l) and re.search(r"-|–|—|to", l)), None)
    return best, ev

class Matcher:
    def __init__(self, embedder, cfg=settings):
        self.emb, self.cfg = embedder, cfg

    def _enc(self, texts):
        return _norm(self.emb.encode(texts))

    def match(self, reqs: list[Requirement], resume_text: str) -> list[Result]:
        sents = split_sentences(resume_text)
        if not sents:
            return [Result(r, "missing", explanation="Resume text was empty.") for r in reqs]
        self.sents, self.S, self.text = sents, self._enc(sents), resume_text
        out = []
        for r in reqs:
            if r.kind == "skill":
                out.append(self._skill(r))
            elif r.subtype == "years":
                out.append(self._years(r))
            elif r.subtype == "degree":
                out.append(self._degree(r))
            else:
                out.append(self._semantic(r))
        return out

    def _skill(self, r: Requirement) -> Result:
        c, S, sents = r.canonical, self.S, self.sents
        hits = [i for i, s in enumerate(sents) if mentions(c, s)]
        if hits:
            qv = self._enc([r.source])[0]
            i = max(hits, key=lambda j: float(S[j] @ qv))   # embeddings pick the strongest evidence
            a = alias_hit(c, sents[i])
            method = "exact" if a == c else "alias"
            return Result(r, "matched", _cut(sents[i]), method, float(S[i] @ qv),
                          f"Found “{a}” in the resume" + ("" if method == "exact" else f" (an alias of {c})") + ".")
        q = self._enc([f"experience with {c}"])[0]
        rel = [(i, n) for n in related(c) for i, s in enumerate(sents) if mentions(n, s)]
        if rel:
            i, n = max(rel, key=lambda t: float(S[t[0]] @ q))
            sim = float(S[i] @ q)
            if sim >= self.cfg.related_min_sim:
                return Result(r, "partial", _cut(sents[i]), "related", sim,
                              f"Related but not equivalent technology found: {n}. {c} itself is not mentioned.", n)
        j = int(np.argmax(S @ q)); sim = float(S[j] @ q)
        if sim >= self.cfg.skill_semantic_only:
            return Result(r, "partial", _cut(sents[j]), "semantic", sim,
                          f"No explicit mention of {c}, but this sentence is semantically very similar.")
        return Result(r, "missing", None, "none", sim, f"No evidence of {c} found in the resume.")

    def _semantic(self, r: Requirement) -> Result:
        q = self._enc([r.text])[0]
        sims = self.S @ q
        i = int(np.argmax(sims)); sim = float(sims[i]); ev = self.sents[i]
        shared = content_tokens(r.text) & content_tokens(ev)
        c = self.cfg
        if sim >= c.semantic_match and shared:
            return Result(r, "matched", _cut(ev), "semantic", sim, f"Closely matches this resume line (shared terms: {', '.join(sorted(shared)[:4])}).")
        if sim >= c.semantic_partial:
            why = "similar in meaning but shares no key terms" if not shared else "partly related"
            return Result(r, "partial", _cut(ev), "semantic", sim, f"This resume line is {why}; evidence is indirect.")
        return Result(r, "missing", None, "none", sim, "No resume line is close enough to this requirement.")

    def _years(self, r: Requirement) -> Result:
        have, ev = resume_years(self.text)
        need = r.value or 0
        if have >= need:
            return Result(r, "matched", _cut(ev) if ev else None, "rule", None, f"Resume indicates about {have:g} years (needs {need}).")
        if have >= 0.6 * need and have > 0:
            return Result(r, "partial", _cut(ev) if ev else None, "rule", None, f"Resume indicates about {have:g} years; {need} requested.")
        return Result(r, "missing", None, "rule", None, f"Resume indicates about {have:g} years; {need} requested.")

    def _degree(self, r: Requirement) -> Result:
        need = r.value or 1
        best, ev = 0, None
        for s in self.sents:
            lv = degree_level(s)
            if lv > best:
                best, ev = lv, s
        if best >= need:
            return Result(r, "matched", _cut(ev), "rule", None, "Education level in the resume meets the stated degree requirement.")
        edu = next((s for s in self.sents if re.search(r"university|college|institute|diploma|coursework", s, re.I)), None)
        if edu:
            return Result(r, "partial", _cut(edu), "rule", None, "Education is listed, but the required degree level isn't explicit.")
        return Result(r, "missing", None, "rule", None, "No degree found in the resume.")
