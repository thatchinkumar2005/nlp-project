"""JD -> list of requirements with importance, using section headers and inline cue words."""
import re
from dataclasses import dataclass

from .nlp import split_sentences
from .skills import find_skills

RANK = {"low": 0, "medium": 1, "high": 2}
VERBS = set("build design develop maintain lead manage collaborate write implement deploy own create work partner "
            "mentor analyze optimize drive ensure support architect test monitor improve contribute define "
            "participate review deliver integrate troubleshoot communicate".split())
LOW = re.compile(r"nice[- ]to[- ]have|bonus|good to have|a plus|desirable|optional|not required|extra credit", re.I)
HIGH = re.compile(r"\b(required|requires?|must|essential|mandatory|minimum|proven|strong)\b", re.I)
MED = re.compile(r"\b(preferred|desired|ideally|familiarity|exposure)\b", re.I)
HEADERS = [
    (r"(nice[- ]to[- ]haves?|bonus|good to have|extra credit)", "req", "low"),
    (r"(preferred|desired|ideal|additional)", "req", "medium"),
    (r"((minimum |basic |key |required |technical |core )*(qualifications|requirements?|skills|must[- ]haves?)"
     r"|what you.?ll need|what we.?re looking for|who you are|you have|you bring)", "req", "high"),
    (r"((key |main |core )?responsibilit(y|ies)|what you.?ll do|duties|your role|the role|day[- ]to[- ]day|your impact)", "resp", None),
    (r"(about( us| the company)?|benefits|perks|we offer|compensation|salary|why .*|our .*|equal .*|how to apply|company)", "ignore", None),
]
DEG = re.compile(r"\b(bachelor'?s?|b\.?tech|master'?s?|m\.?tech|mba|ph\.?d|doctorate|degree|b\.?sc|m\.?sc)\b", re.I)
YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)", re.I)

@dataclass
class Requirement:
    id: str
    text: str
    kind: str            # skill | qualification | responsibility
    importance: str
    source: str          # the JD sentence it came from (context for semantic matching)
    canonical: str | None = None
    subtype: str | None = None   # degree | years
    value: int | None = None

def degree_level(text: str, pick=max) -> int:
    lv = []
    for m in DEG.finditer(text):
        w = m.group(0).lower()
        lv.append(3 if re.match(r"ph|doctor", w) else 2 if re.match(r"master|m\.?(tech|sc)|mba", w) else 1)
    return pick(lv) if lv else 0

def _header(line: str):
    colon = line.rstrip().endswith(":")
    body = line.rstrip(": ").lower()
    if len(body.split()) > 6:
        return None
    tail = r"(\s+\w+){0,3}" if colon else r"(\s+(qualifications|requirements|skills|experience|responsibilities))?"
    for pat, sec, imp in HEADERS:
        if re.fullmatch(pat + tail, body):
            return sec, imp
    return None

def _importance(sent: str, section_imp: str | None) -> str:
    if LOW.search(sent): return "low"
    if HIGH.search(sent): return "high"
    if MED.search(sent): return "medium"
    return section_imp or "medium"

def extract_requirements(jd: str, max_other: int = 12) -> list[Requirement]:
    reqs: dict[str, Requirement] = {}
    section, sec_imp, others = None, None, 0

    def upsert(r: Requirement):
        old = reqs.get(r.id)
        if old is None:
            reqs[r.id] = r
        elif RANK[r.importance] > RANK[old.importance]:
            old.importance = r.importance

    for raw in jd.splitlines():
        line = raw.strip()
        if not line:
            continue
        bullet = bool(re.match(r"^\s*[-•*·▪●◦–]", line))
        h = None if bullet else _header(line)
        if h:
            section, sec_imp = h
            continue
        m = None if bullet else re.match(r"^([A-Za-z' /-]{3,40}):\s+(\S.*)$", line)
        if m and _header(m.group(1) + ":"):
            section, sec_imp = _header(m.group(1) + ":")
            line = m.group(2)
        if section == "ignore":
            continue
        for sent in split_sentences(line):
            imp = _importance(sent, sec_imp)
            skills = find_skills(sent)
            for c in skills:
                upsert(Requirement(f"skill:{c}", c, "skill", imp, sent, canonical=c))
            if DEG.search(sent):
                lvl = degree_level(sent, min)
                upsert(Requirement("qual:degree", "Degree: " + sent[:90], "qualification", imp, sent, subtype="degree", value=lvl))
                continue
            ym = YEARS.search(sent)
            if ym and not skills and re.search(r"experience", sent, re.I):
                n = int(ym.group(1))
                upsert(Requirement("qual:years", f"{n}+ years of relevant experience", "qualification", imp, sent, subtype="years", value=n))
                continue
            words = len(sent.split())
            first = re.sub(r"\W", "", sent.split()[0].lower()) if words else ""
            if others < max_other and 4 <= words <= 40 and len(skills) < 2:
                if section == "resp" or (section is None and first in VERBS):
                    upsert(Requirement("resp:" + re.sub(r"\W+", " ", sent.lower())[:60], sent.rstrip("."), "responsibility", imp, sent))
                    others += 1
                elif section == "req" and not skills:
                    upsert(Requirement("req:" + re.sub(r"\W+", " ", sent.lower())[:60], sent.rstrip("."), "qualification", imp, sent))
                    others += 1
    return list(reqs.values())
