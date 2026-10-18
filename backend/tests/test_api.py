import io
import fitz, pytest
from docx import Document
from fastapi.testclient import TestClient
from app.main import app, get_embedder

JD = "Requirements:\n- Python\n- Docker\n- Experience building APIs"

@pytest.fixture
def client(emb):
    app.dependency_overrides[get_embedder] = lambda: emb
    yield TestClient(app)
    app.dependency_overrides.clear()

def docx_bytes(text):
    d = Document(); [d.add_paragraph(l) for l in text.split("\n")]
    b = io.BytesIO(); d.save(b); return b.getvalue()

def post(client, name, data, jd=JD):
    return client.post("/api/analyze", data={"job_description": jd}, files={"resume": (name, data)} if data is not None else None)

def test_docx_ok(client):
    r = post(client, "cv.docx", docx_bytes("Jane Doe\nBuilt Python services and APIs.\nDocker in production."))
    assert r.status_code == 200 and r.json()["counts"]["matched"] >= 2

def test_pdf_ok(client):
    doc = fitz.open(); doc.new_page().insert_text((72, 72), "Python engineer. Used Docker daily to ship APIs.")
    r = post(client, "cv.pdf", doc.tobytes())
    assert r.status_code == 200

@pytest.mark.parametrize("name,data,jd,code", [
    ("cv.txt", b"hello", JD, 415), ("cv.pdf", b"not a pdf", JD, 415), ("cv.docx", b"", JD, 400),
    ("cv.docx", docx_bytes("Python"), "", 400), ("cv.docx", docx_bytes("Python"), "short", 400),
    ("cv.docx", docx_bytes("x"), JD, 422), (None, None, JD, 400),
])
def test_errors(client, name, data, jd, code):
    assert post(client, name, data, jd).status_code == code

def test_too_large(client):
    assert post(client, "cv.pdf", b"%PDF" + b"0" * (5 * 1024 * 1024 + 1)).status_code == 413

def test_jd_without_requirements(client):
    r = post(client, "cv.docx", docx_bytes("Python developer with experience."), "We are a friendly company with a nice office and great culture.")
    assert r.status_code == 422
