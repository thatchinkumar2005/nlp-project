import re
from functools import lru_cache

import spacy

BULLET = re.compile(r"^\s*[-•*·▪●◦–]+\s*")

@lru_cache(maxsize=1)
def get_nlp():
    """en_core_web_sm if installed (better sentence/lemma handling), else a rule-based fallback."""
    try:
        return spacy.load("en_core_web_sm", disable=["ner"])
    except OSError:
        nlp = spacy.blank("en")
        nlp.add_pipe("sentencizer")
        return nlp

def split_sentences(text: str, max_len: int = 160) -> list[str]:
    """Line-first splitting (bullets are natural units); spaCy splits long/multi-sentence lines."""
    out: list[str] = []
    for line in text.splitlines():
        line = BULLET.sub("", line).strip()
        if len(line) < 3:
            continue
        if len(line) > max_len or re.search(r"[.!?]\s+[A-Z]", line):
            out += [s.text.strip() for s in get_nlp()(line).sents if len(s.text.strip()) >= 3]
        else:
            out.append(line)
    return out

def content_tokens(text: str) -> set[str]:
    return {(t.lemma_ or t.text).lower() for t in get_nlp()(text)
            if t.is_alpha and not t.is_stop and len(t.text) > 3}
