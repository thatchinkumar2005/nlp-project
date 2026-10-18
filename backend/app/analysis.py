from .config import settings
from .extraction import extract_requirements
from .matching import Matcher
from .scoring import WEIGHTS, compute_score

class NoRequirementsError(Exception):
    pass

DISCLAIMER = ("This score estimates how well your resume's wording covers the job description's requirements. "
              "It is not a probability of being hired or of passing any employer's screening.")

def suggest(res) -> str | None:
    r, t = res.req, res.req.text
    if res.status == "matched":
        return None
    if r.subtype == "years":
        return f"The role asks for {r.value}+ years. If your dates or durations are undercounted, make them explicit; don't inflate them."
    if r.subtype == "degree":
        return "State your education clearly. If you have equivalent practical experience instead of the degree, highlight it honestly."
    if res.status == "partial" and res.related:
        return (f"Your resume shows {res.related} but not {t}. If you have also used {t}, add a bullet with a concrete example; "
                f"otherwise explain how your {res.related} experience transfers.")
    if res.status == "partial":
        return f"Evidence for “{t[:80]}” is indirect. Make it explicit with what you did and the outcome, only if it's accurate."
    if r.kind == "skill":
        return (f"{t} is {r.importance}-priority and wasn't found. If you've genuinely used it (work, projects, coursework), "
                "add a specific bullet. If not, consider learning it, and keep it off your resume until it's true.")
    return f"Look for real experience resembling “{t[:90]}”. If you have it, add a bullet describing it in your own words."

def analyze(resume_text: str, jd_text: str, embedder, cfg=settings) -> dict:
    reqs = extract_requirements(jd_text)
    if not reqs:
        raise NoRequirementsError("No skills or requirements could be identified in the job description. Paste the full posting, including its requirements section.")
    results = Matcher(embedder, cfg).match(reqs, resume_text)
    results.sort(key=lambda r: (-WEIGHTS[r.req.importance], r.status))
    return {**compute_score(results, cfg), "disclaimer": DISCLAIMER, "model": cfg.model_name,
            "requirements": [{"id": r.req.id, "text": r.req.text, "kind": r.req.kind, "importance": r.req.importance,
                              "status": r.status, "evidence": r.evidence, "method": r.method,
                              "similarity": None if r.similarity is None else round(r.similarity, 3),
                              "explanation": r.explanation, "suggestion": suggest(r)} for r in results]}
