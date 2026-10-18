from app.analysis import analyze
from app.extraction import extract_requirements
from app.matching import Matcher
from app.scoring import compute_score

def run(jd, resume, emb):
    reqs = extract_requirements(jd)
    return {r.req.id: r for r in Matcher(emb).match(reqs, resume)}

def test_extraction_importance():
    jd = "Requirements:\n- Python and SQL\n- 5+ years of experience\nNice to have:\n- Kubernetes\nPreferred: Docker"
    ids = {r.id: r.importance for r in extract_requirements(jd)}
    assert ids["skill:python"] == "high" and ids["skill:kubernetes"] == "low"
    assert ids["skill:docker"] == "medium" and ids["qual:years"] == "high"

def test_inline_cues():
    ids = {r.id: r.importance for r in extract_requirements("Python is required. Experience with Redis is a plus.")}
    assert ids["skill:python"] == "high" and ids["skill:redis"] == "low"

def test_exact_and_alias(emb):
    res = run("Requirements:\n- Python\n- Kubernetes", "Built services in Python.\nManaged k8s clusters.", emb)
    assert res["skill:python"].status == "matched" and res["skill:python"].method == "exact"
    assert res["skill:kubernetes"].status == "matched" and res["skill:kubernetes"].method == "alias"
    assert "k8s" in res["skill:kubernetes"].evidence

def test_semantic_related_partial(emb):
    res = run("Experience with Kubernetes is required.", "Deployed services using Docker containers", emb)
    r = res["skill:kubernetes"]
    assert r.status == "partial" and r.related == "docker"

def test_false_positives(emb):
    assert run("Java is required.", "Built front-end apps with JavaScript", emb)["skill:java"].status == "missing"
    assert run("Experience with NoSQL", "Wrote SQL reports in MySQL", emb).get("skill:sql") is None
    assert run("SQL required", "Used NoSQL stores", emb)["skill:sql"].status == "missing"
    assert run("React required", "Built apps in React Native", emb)["skill:react"].status == "partial"

def test_semantic_responsibility(emb):
    res = run("Responsibilities:\n- Design RESTful APIs for services", "Designed APIs and endpoints for services", emb)
    assert any(r.status in ("matched", "partial") for r in res.values() if r.req.kind == "responsibility")

def test_years_rule(emb):
    r = run("Requirements:\n- 5+ years of experience", "Engineer, 2015 - 2022", emb)["qual:years"]
    assert r.status == "matched"

def test_scoring_weights(emb):
    res = Matcher(emb).match(extract_requirements("Python is required. Docker preferred. Redis is a plus."), "Python dev. Kubernetes ops.")
    s = compute_score(res)
    assert s["counts"] == {"matched": 1, "partial": 1, "missing": 1}
    assert s["score"] == round(100 * (3 + 0.5 * 2) / 6)

def test_analyze_shape(emb):
    out = analyze("Python developer with APIs", "Python required", emb)
    assert 0 <= out["score"] <= 100 and out["requirements"][0]["evidence"]
