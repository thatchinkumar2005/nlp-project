# Resume–JD Matcher

React + TypeScript + Tailwind frontend, FastAPI backend. No database, auth, or paid/LLM APIs.

## Run the backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm                # optional; falls back to a rule-based sentence splitter
uvicorn app.main:app --reload --port 8000
```
The first request downloads `all-MiniLM-L6-v2` (~90 MB) and is slower.

## Run the frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (set VITE_API_URL if the backend isn't on :8000)
```

## Tests
```bash
cd backend && pytest -q    # uses a deterministic fake embedder; no model download needed
```

## How it works
1. **Extract**: PyMuPDF / python-docx parse the resume; spaCy splits sentences. The JD is parsed into skills (taxonomy + aliases), degree/years rules, and responsibilities. Importance comes from section headers ("Requirements", "Nice to have") and cues ("required", "preferred", "a plus").
2. **Match**: exact/alias keyword hits (boundary-aware, so Java ≠ JavaScript, SQL ≠ NoSQL, React ≠ React Native); sentence embeddings pick the strongest evidence line, find related-technology partials, and decide matches for responsibilities. Related-but-different technologies (Docker vs Kubernetes) never count as full matches.
3. **Score**: weights high=3, medium=2, low=1; matched=1, partial=0.5 (`RJM_PARTIAL_CREDIT`), missing=0. Thresholds are in `app/config.py` and overridable via `RJM_*` env vars.

The score estimates requirement coverage. It is **not** a probability of getting hired.

## Limits
Skill detection is taxonomy-based (~90 skills in `app/skills.py`; extend as needed). Unlisted skills are not detected as skills, though responsibility lines are still matched semantically. Scanned/image-only PDFs aren't supported (no OCR).
