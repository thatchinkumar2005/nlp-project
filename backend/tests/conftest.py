import sys, zlib
from pathlib import Path
import numpy as np, pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CONCEPTS = {"kubernetes": "container", "docker": "container", "containers": "container",
            "api": "api", "apis": "api", "restful": "api", "endpoints": "api"}
STOP = {"experience", "with", "in", "of", "and", "the", "a", "to", "for", "using", "is", "required"}

class FakeEmbedder:
    """Deterministic bag-of-concepts embedder so tests need no model download."""
    def encode(self, texts):
        out = np.zeros((len(texts), 256))
        for i, t in enumerate(texts):
            for w in "".join(c if c.isalnum() else " " for c in t.lower()).split():
                if w not in STOP:
                    out[i, zlib.crc32(CONCEPTS.get(w, w).encode()) % 256] += 1
        return out

@pytest.fixture
def emb():
    return FakeEmbedder()
