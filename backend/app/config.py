"""Tunable thresholds. Override with environment variables (e.g. RJM_SEMANTIC_MATCH=0.65)."""
import os
from dataclasses import dataclass, field

def _f(name: str, default: float) -> float:
    return float(os.getenv(f"RJM_{name.upper()}", default))

@dataclass
class Settings:
    model_name: str = os.getenv("RJM_MODEL", "all-MiniLM-L6-v2")
    max_upload_bytes: int = 5 * 1024 * 1024
    max_jd_chars: int = 20000
    min_jd_chars: int = 40
    # Non-skill requirements (responsibilities, qualifications): cosine thresholds.
    semantic_match: float = field(default_factory=lambda: _f("semantic_match", 0.62))
    semantic_partial: float = field(default_factory=lambda: _f("semantic_partial", 0.45))
    # Skills: a *related* technology (same family) must be at least this similar to count as partial.
    related_min_sim: float = field(default_factory=lambda: _f("related_min_sim", 0.30))
    # Skills with no keyword/related evidence: only a very strong semantic hit earns partial credit.
    skill_semantic_only: float = field(default_factory=lambda: _f("skill_semantic_only", 0.72))
    partial_credit: float = field(default_factory=lambda: _f("partial_credit", 0.5))
    cors_origins: tuple = ("http://localhost:5173", "http://127.0.0.1:5173")

settings = Settings()
