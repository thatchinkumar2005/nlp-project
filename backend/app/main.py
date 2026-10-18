import logging
from functools import lru_cache

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .analysis import NoRequirementsError, analyze
from .config import settings
from .matching import SentenceTransformerEmbedder
from .parsing import ParseError, extract_text

log = logging.getLogger("rjm")
app = FastAPI(title="Resume–JD Matcher")
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"], allow_headers=["*"])

@lru_cache(maxsize=1)
def get_embedder():
    return SentenceTransformerEmbedder(settings.model_name)

@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/analyze")
def analyze_endpoint(resume: UploadFile | None = File(None), job_description: str = Form(""), embedder=Depends(get_embedder)):
    jd = job_description.strip()
    if resume is None or not resume.filename:
        raise HTTPException(400, "Please upload a resume (PDF or DOCX).")
    if not jd:
        raise HTTPException(400, "Please paste a job description.")
    if len(jd) < settings.min_jd_chars:
        raise HTTPException(400, "The job description is too short to analyze. Paste the full posting.")
    if len(jd) > settings.max_jd_chars:
        raise HTTPException(400, f"The job description is too long (max {settings.max_jd_chars} characters).")
    ext = resume.filename.lower().rsplit(".", 1)[-1] if "." in resume.filename else ""
    if ext not in ("pdf", "docx"):
        raise HTTPException(415, "Unsupported file type. Upload a PDF or DOCX resume.")
    data = resume.file.read(settings.max_upload_bytes + 1)   # in memory only; never written to disk
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, f"File too large (max {settings.max_upload_bytes // 1024 // 1024} MB).")
    if (ext == "pdf" and not data.startswith(b"%PDF")) or (ext == "docx" and not data.startswith(b"PK")):
        raise HTTPException(415, f"This file isn't a valid {ext.upper()}.")
    try:
        text = extract_text(resume.filename, data)
        return analyze(text, jd, embedder)
    except ParseError as e:
        raise HTTPException(422, str(e))
    except NoRequirementsError as e:
        raise HTTPException(422, str(e))
    except Exception:
        log.exception("analysis failed")
        raise HTTPException(500, "Something went wrong while analyzing. Please try again.")
