from .config import settings

WEIGHTS = {"high": 3, "medium": 2, "low": 1}

def compute_score(results, cfg=settings) -> dict:
    """Importance-weighted requirement coverage: matched=1, partial=partial_credit, missing=0."""
    credit = {"matched": 1.0, "partial": cfg.partial_credit, "missing": 0.0}
    total = sum(WEIGHTS[r.req.importance] for r in results)
    earned = sum(WEIGHTS[r.req.importance] * credit[r.status] for r in results)
    weights = {s: sum(WEIGHTS[r.req.importance] for r in results if r.status == s) for s in credit}
    counts = {s: sum(1 for r in results if r.status == s) for s in credit}
    return {"score": round(100 * earned / total) if total else 0, "counts": counts,
            "weights": weights, "total_weight": total}
