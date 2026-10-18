"""Skill taxonomy: canonical name, aliases, and a 'family' of related-but-NOT-equivalent technologies.
Family members only ever earn *partial* credit for each other (e.g. Java vs Kotlin), and look-alike
names are kept apart by boundary-aware matching (Java != JavaScript, SQL != NoSQL, React != React Native)."""
import re
from functools import lru_cache

RAW = [
 ("python", ["python", "python3"], None), ("java", ["java"], "jvm"), ("kotlin", ["kotlin"], "jvm"),
 ("scala", ["scala"], "jvm"), ("spring boot", ["spring boot", "spring framework"], "jvm"),
 ("javascript", ["javascript", "es6", "ecmascript"], "js"), ("typescript", ["typescript"], "js"),
 ("node.js", ["node.js", "nodejs", "node js"], "js"), ("c++", ["c++", "cpp"], None),
 ("c#", ["c#", "csharp"], "dotnet"), (".net", [".net", "asp.net", "dotnet"], "dotnet"),
 ("go", ["golang"], None), ("rust", ["rust"], None), ("ruby", ["ruby"], "ruby"),
 ("ruby on rails", ["ruby on rails", "rails"], "ruby"), ("php", ["php"], None), ("swift", ["swift"], None),
 ("react", ["react", "reactjs", "react.js"], "jsfw"), ("react native", ["react native"], "jsfw"),
 ("angular", ["angular", "angularjs"], "jsfw"), ("vue", ["vue", "vue.js", "vuejs"], "jsfw"),
 ("svelte", ["svelte"], "jsfw"), ("next.js", ["next.js", "nextjs"], "jsfw"), ("redux", ["redux"], None),
 ("html", ["html", "html5"], None), ("css", ["css", "css3", "sass", "scss"], "css"), ("tailwind", ["tailwind", "tailwindcss"], "css"),
 ("django", ["django"], "pyweb"), ("flask", ["flask"], "pyweb"), ("fastapi", ["fastapi"], "pyweb"),
 ("express", ["express.js", "expressjs"], None), ("graphql", ["graphql"], None),
 ("rest apis", ["rest", "restful", "rest api", "rest apis"], None), ("microservices", ["microservices", "microservice"], None),
 ("sql", ["sql"], "rdbms"), ("postgresql", ["postgresql", "postgres"], "rdbms"), ("mysql", ["mysql"], "rdbms"),
 ("sqlite", ["sqlite"], "rdbms"), ("mongodb", ["mongodb", "mongo"], "nosql"), ("dynamodb", ["dynamodb"], "nosql"),
 ("cassandra", ["cassandra"], "nosql"), ("redis", ["redis"], "nosql"), ("elasticsearch", ["elasticsearch", "opensearch"], None),
 ("aws", ["aws", "amazon web services"], "cloud"), ("azure", ["azure"], "cloud"), ("gcp", ["gcp", "google cloud"], "cloud"),
 ("docker", ["docker"], "container"), ("kubernetes", ["kubernetes", "k8s"], "container"),
 ("terraform", ["terraform"], "iac"), ("ansible", ["ansible"], "iac"),
 ("ci/cd", ["ci/cd", "cicd", "continuous integration"], "cicd"), ("jenkins", ["jenkins"], "cicd"),
 ("github actions", ["github actions"], "cicd"), ("git", ["git", "github", "gitlab"], None), ("linux", ["linux"], None),
 ("machine learning", ["machine learning"], "ml"), ("deep learning", ["deep learning"], "ml"),
 ("nlp", ["nlp", "natural language processing"], "ml"), ("tensorflow", ["tensorflow"], "ml"),
 ("pytorch", ["pytorch"], "ml"), ("scikit-learn", ["scikit-learn", "sklearn"], "ml"),
 ("pandas", ["pandas"], None), ("numpy", ["numpy"], None), ("spark", ["spark", "pyspark"], "bigdata"),
 ("hadoop", ["hadoop"], "bigdata"), ("kafka", ["kafka"], "bigdata"), ("airflow", ["airflow"], "bigdata"),
 ("tableau", ["tableau"], "bi"), ("power bi", ["power bi", "powerbi"], "bi"), ("excel", ["excel"], "bi"),
 ("agile", ["agile", "scrum"], None), ("jira", ["jira"], None),
 ("automated testing", ["unit test", "unit tests", "unit testing", "pytest", "jest", "junit"], None),
]
SKILLS = {c: {"aliases": a, "family": f} for c, a, f in RAW}
EXCLUDE = {"react": ["react native"]}  # phrases removed before matching, to avoid look-alike hits

@lru_cache(maxsize=None)
def _pat(canon: str) -> re.Pattern:
    alts = "|".join(re.escape(a) for a in sorted(SKILLS[canon]["aliases"], key=len, reverse=True))
    return re.compile(rf"(?<![\w+#.])(?:{alts})(?![\w+#]|\.\w)", re.I)

def _clean(canon: str, text: str) -> str:
    for ex in EXCLUDE.get(canon, []):
        text = re.sub(re.escape(ex), " ", text, flags=re.I)
    return text

def mentions(canon: str, text: str) -> bool:
    return bool(_pat(canon).search(_clean(canon, text)))

def alias_hit(canon: str, text: str) -> str | None:
    m = _pat(canon).search(_clean(canon, text))
    return m.group(0).lower() if m else None

def find_skills(text: str) -> list[str]:
    return [c for c in SKILLS if mentions(c, text)]

def related(canon: str) -> list[str]:
    fam = SKILLS[canon]["family"]
    return [o for o, v in SKILLS.items() if fam and o != canon and v["family"] == fam]
