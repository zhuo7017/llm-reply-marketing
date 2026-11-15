"""Data model for the research index.

Turns data/papers.enriched.json into fully-resolved paper records: clean titles,
stable slugs, topics, verbatim claim sentences, and citation strings.

Design rule: nothing in this module paraphrases a paper's findings. Every claim
sentence is a substring of the source abstract, only trimmed and label-stripped.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# ---------------------------------------------------------------- topics ----

# (slug, title, blurb, keywords, questions)
TOPICS = [
    {
        "slug": "musculoskeletal-ai",
        "title": "AI for musculoskeletal radiographs",
        "blurb": "Deep-learning measurement of anatomical angles on hip, pelvis and lower-limb X-rays.",
        "keywords": ["hip", "knee", "ankle", "pelvi", "sharp's angle", "ce angle",
                      "dysplasia", "x-ray", "radiograph", "lower limb", "orthop"],
        "questions": [
            "How accurately can deep learning measure the hip–knee–ankle angle on X-rays?",
            "Can an automated tool replace manual measurement of Sharp's angle for hip dysplasia?",
            "Which deep-learning model architecture works best for pelvic radiograph measurements?",
            "Is AI-assisted angle measurement reliable enough for orthopaedic clinical use?",
            "How much time does automated radiographic measurement save clinicians?",
        ],
    },
    {
        "slug": "cancer-imaging-ai",
        "title": "AI for cancer imaging and pathology",
        "blurb": "Radiomics, convolutional networks and multimodal models for tumour diagnosis and prognosis.",
        "keywords": ["mammograph", "her2", "breast cancer", "radiomic", "convolutional",
                      "molecular subtype", "multimodal model", "imaging"],
        "questions": [
            "Can mammography plus deep learning predict HER2, ER and PR status in breast cancer?",
            "How well do radiomics models predict glioblastoma molecular subtype?",
            "Do multimodal imaging models improve survival prediction over clinical variables alone?",
            "What is the reported AUC or accuracy of CNN-based tumour subtyping?",
        ],
    },
    {
        "slug": "glioma-biology",
        "title": "Glioma and glioblastoma biology",
        "blurb": "Epigenetic control of glioma cell fate, prognostic signatures and target discovery.",
        "keywords": ["glioma cell", "h3k9", "h3k14", "acetylat", "neuron-fate",
                      "prognostic signature", "mcl-1", "pdk1", "zeylenol", "egfr inhibitor"],
        "questions": [
            "What drives neuron-fate induction in glioma cells?",
            "Can histone acetylation state determine glioblastoma cell fate?",
            "Which prognostic signatures predict glioma survival?",
            "What targets are being explored for glioblastoma therapy?",
        ],
    },
    {
        "slug": "computational-drug-discovery",
        "title": "Computational drug discovery and natural inhibitors",
        "blurb": "Structure-based virtual screening and molecular dynamics for natural-compound inhibitors.",
        "keywords": ["docking", "inhibitor", "natural compound", "virtual screening",
                      "molecular dynamics", "bcl2", "akt1", "c-met", "kras", "pdgfra",
                      "parp", "mtorc1", "dopamine receptor", "pha-793887", "computational study"],
        "questions": [
            "Which natural compounds inhibit AKT1 according to molecular docking studies?",
            "How are natural-product inhibitors of BCL2 identified by virtual screening?",
            "What computational pipeline is used to prioritise candidate inhibitors before wet-lab testing?",
            "Are docking-predicted natural inhibitors stable in molecular dynamics simulations?",
            "Which natural compounds target KRAS G12C, c-MET or PDGFRA?",
        ],
    },
    {
        "slug": "mendelian-randomization",
        "title": "Mendelian randomization and causal inference",
        "blurb": "Two-sample and bidirectional MR designs testing causal risk factors for brain tumours and neurological disease.",
        "keywords": ["mendelian randomization", "mendelian-randomization", "causal",
                      "instrumental variable", "gwas", "exposure"],
        "questions": [
            "Is there a causal link between viral infections and glioma risk?",
            "Do psychiatric disorders causally increase glioma risk?",
            "Does COVID-19 hospitalisation increase glioblastoma risk?",
            "Are dietary factors causally associated with glioma?",
            "Can Mendelian randomization separate correlation from causation in neuro-oncology?",
            "How should a bidirectional two-sample MR study be designed and reported?",
        ],
    },
    {
        "slug": "brain-imaging-genetics",
        "title": "Brain imaging phenotypes and genetic risk",
        "blurb": "Imaging-derived phenotypes, exposome-wide and genetic analyses of neurological and psychiatric risk.",
        "keywords": ["imaging-derived", "imaging data", "bipolar", "epilep", "parkinson",
                      "exposome", "biobank", "brain disorder risk", "plasma metabolite"],
        "questions": [
            "Do brain imaging phenotypes causally influence bipolar disorder risk?",
            "Can routine imaging data predict future brain disorder risk in adults?",
            "Which plasma metabolites link lifestyle to epilepsy risk?",
            "How large a cohort is needed to predict brain disorder risk from imaging?",
        ],
    },
    {
        "slug": "immuno-oncology",
        "title": "Tumour immunology and immunotherapy",
        "blurb": "Oncolytic virotherapy, T-cell immunity, nanoplatforms and peripheral immune markers.",
        "keywords": ["oncolytic", "cd8", "t-cell", "immunity", "nanoplatform",
                      "immune marker", "immunological profile", "antigen"],
        "questions": [
            "How does oncolytic virus M1 trigger anti-glioma immunity?",
            "Can peripheral blood immune markers predict glioma prognosis?",
            "What is the immunological profile of glioblastoma in East Asian patients?",
            "Which nanoplatform strategies target glioblastoma stemness?",
        ],
    },
    {
        "slug": "neuro-epidemiology",
        "title": "Neuro-epidemiology and global burden",
        "blurb": "Population-level burden estimates, druggable-genome screens and risk-factor epidemiology.",
        "keywords": ["global burden", "gbd", "burden of", "aneurysm", "druggable genome",
                      "epidemiolog", "obesity", "facial aging"],
        "questions": [
            "What is the global burden of brain and central nervous system cancer?",
            "Which druggable genes are causal targets for intracranial aneurysm?",
            "How has CNS cancer incidence changed between 1990 and 2021?",
        ],
    },
    {
        "slug": "clinical-case-reports",
        "title": "Clinical case reports and diagnostics",
        "blurb": "Rare presentations, diagnostic pitfalls and single-patient evidence.",
        "keywords": ["case report", "a case of", "leptomeningeal", "methylmalonic"],
        "questions": [
            "What causes bilateral cerebellar lesions in adult methylmalonic acidemia?",
            "How high can cerebrospinal fluid protein rise in leptomeningeal metastasis?",
        ],
    },
    {
        "slug": "other",
        "title": "Other publications",
        "blurb": "Work that does not fit the main research themes.",
        "keywords": ["__never_matches__"],
        "questions": [],
    },
]

TOPIC_BY_SLUG = {t["slug"]: t for t in TOPICS}

# ----------------------------------------------------------------- utils ----


def clean_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\u2212", "-").replace("\u2011", "-").replace("\u2010", "-")
    s = s.replace("\u00ad", "").replace("\u200b", "")
    s = re.sub(r"(?<=[A-Za-z])-\s+(?=[0-9])", "-", s)   # "COVID- 19" -> "COVID-19"
    s = re.sub(r"(?<=[a-z])-\s+(?=[a-z])", "-", s)      # "high- grade" -> "high-grade"
    s = re.sub(r"\s+", " ", s).strip()
    return s


def slugify(s: str, maxlen: int = 72) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    if len(s) > maxlen:
        s = s[:maxlen].rsplit("-", 1)[0]
    return s or "paper"


ABBREV = ["e.g.", "i.e.", "et al.", "vs.", "Fig.", "No.", "approx.", "cf.", "resp.", "Dr.", "etc."]


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    protected = text
    for i, a in enumerate(ABBREV):
        protected = protected.replace(a, f"__AB{i}__")
    parts = re.split(r"(?<=[.!?])\s+", protected)
    out = []
    for p in parts:
        for i, a in enumerate(ABBREV):
            p = p.replace(f"__AB{i}__", a)
        p = p.strip()
        if p:
            out.append(p)
    return out


SECTION_LABELS = re.compile(
    r"^(?:\*{0,2})(background|objective|objectives|aim|aims|purpose|methods|method|"
    r"materials and methods|results|result|findings|conclusions?|conclusion/(s|s)?|"
    r"significance|importance|design|setting|patients|interventions?|main outcomes)\s*[:：]\s*",
    re.I,
)


def strip_label(s: str) -> str:
    prev = None
    while prev != s:
        prev = s
        s = SECTION_LABELS.sub("", s).strip()
    return s


def sentence_section(text: str) -> list[tuple[str, str]]:
    """Return (section_label, sentence) pairs, tracking structured labels."""
    rows = []
    current = ""
    for raw in split_sentences(text):
        m = re.match(
            r"^\*{0,2}(?P<lab>background|objective|objectives|aim|aims|purpose|methods|"
            r"method|materials and methods|results|result|findings|conclusions?|conclusion/(s|s)?|"
            r"significance|importance)\s*[:：]",
            raw,
            re.I,
        )
        if m:
            current = m.group("lab").lower()
        rows.append((current, strip_label(raw)))
    return rows


CUE_RESULT = re.compile(
    r"\b(significant|significantly|achiev\w*|reach\w*|improv\w*|increas\w*|decreas\w*|"
    r"reduc\w*|higher|lower|outperform\w*|accurate|accuracy|auc|correlat\w*|predict\w*|"
    r"associated with|risk of|sensitivity|specificity|hazard ratio|odds ratio|compared with)\b",
    re.I,
)
# Language that only appears when a paper states what it found.
CUE_FINDING = re.compile(
    r"\b(we (found|observed|identified|detected|demonstrated)|our (results|findings|analysis)|"
    r"(was|were) (found|observed|identified|detected|associated|correlated|significantly)|"
    r"(results?|findings?|analysis) (showed|revealed|indicated|suggested|demonstrated)|"
    r"(showed|revealed|demonstrated) that|(suggest|indicat|demonstrat|conclud)\w* that)\b",
    re.I,
)
# Study-design prose: describes what the authors did, not what they found.
DESIGN_PROSE = re.compile(
    r"\b(were|was)\s+(selected|collected|recruited|enrolled|included|obtained|extracted|"
    r"downloaded|divided|randomly|cropped|labelled|labeled|used|utilized|utilised|applied|"
    r"performed|conducted|trained|validated|tested|converted|identified|screened|assessed|"
    r"evaluated|measured|calculated|estimated|analy[sz]ed|compared|matched|constructed|"
    r"developed|implemented|generated|categorized|classified|integrated|downloaded)\b"
    r"|\bwe (used|performed|conducted|collected|recruited|downloaded|obtained|extracted|"
    r"applied|analy[sz]ed|constructed|developed|implemented|integrated|categorized)\b"
    r"|\bthis study (retrospectively|prospectively)|patients were|data were|"
    r"\b(inclusion|exclusion) criteria\b",
    re.I,
)
BOILERPLATE = re.compile(
    r"^(the (aim|purpose|objective)s? of (this|the) study|this study (aimed|sought|investigated)|"
    r"we (aimed|sought|set out)|here,? we|in this (study|paper|work|review),? we)|"
    r"^(to (determine|investigate|assess|evaluate|explore))",
    re.I,
)
# Connectives and stray punctuation left over from a broken sentence start.
LEAD_JUNK = re.compile(r"^[\s,;:.\-\u2013\u2014]+")
LEAD_CONNECTIVE = re.compile(
    r"^(also|however|moreover|furthermore|additionally|in addition|thus|therefore|"
    r"besides|meanwhile|then|consequently|accordingly|thereby|as a result|"
    r"nevertheless|nonetheless|in contrast|still|yet|finally|overall)\s*,?\s+",
    re.I,
)
# Statements of what is still unknown are not findings.
KNOWLEDGE_GAP = re.compile(
    r"\b(remains? to be (explored|determined|elucidated|clarified|investigated)|"
    r"remain(s)? (unclear|unknown|poorly understood)|(is|are) (still )?(needed|required)|"
    r"warrant(s)? further|future (studies|research|work)|should be (further )?(investigated|explored)|"
    r"further (studies|research) (are|is) (needed|required))\b",
    re.I,
)
# A claim must state an outcome. If a sentence has none of these, it is a frame,
# a design description or a definition — never a finding worth quoting.
FINDING_VERB = re.compile(
    r"\b(found|finds|showed|shows|shown|revealed|reveals|demonstrated|demonstrates|"
    r"indicated|indicates|suggested|suggests|detected|detects|observed|observes|"
    r"identified|identifies|yielded|yields|achieved|achieves|proved|proves|"
    r"increased|increases|decreased|decreases|reduced|reduces|improved|improves|"
    r"remained|remains|predicted|predicts|correlated|correlates|caused|causes|"
    r"(led|leads) to|result(ed|s) in|outperformed|outperforms|provid(es|ed)|"
    r"similar to|comparable to|consistent with|did not differ|no (significant )?difference|"
    r"was associated|"
    r"were associated|is associated|are associated|was correlated|were correlated|"
    r"no (evidence|association|significant|difference|effect)|higher|lower)\b",
    re.I,
)
# A numeric outcome that makes a design sentence worth keeping anyway.
NUMERIC_OUTCOME = re.compile(
    r"±|%|\bp\s*[<=>]|\bICC\b|\bAUC\b|\b(OR|HR|RR)\s*=|95%\s*CI|accuracy of|"
    r"sensitivity of|specificity of|correlation coefficient",
    re.I,
)
BACKGROUND_OPENERS = re.compile(
    r"^(at present|currently|in recent years|nowadays|with the (development|progress|rapid)|"
    r"in light of|in the context of|given that|although|despite|however|glioma is|"
    r"cancer is|it is (well )?known|studies have shown|previous (studies|research)|"
    r"observational studies|recent (studies|advances)|owing to|due to the)",
    re.I,
)
FRAGMENT_START = re.compile(r"^(of|in|at|by|from|to|for|with|and|or|which|while|as|than)\b", re.I)
# A sentence that opens with a back-reference cannot stand alone as a quote.
DANGLING_START = re.compile(
    r"^(they|them|it|its|these|those|such|their|the latter|both|all of them|"
    r"this (compound|group|effect|association|finding|approach|method|model|study|"
    r"analysis|result)s?|the above|above)\b",
    re.I,
)
# Connectives that only make sense in the flow of the abstract they came from.
# Stance adverbs ("importantly", "intriguingly") are deliberately allowed: they
# open a sentence fine once the original capitalisation is kept.
DEPENDENT_START = re.compile(
    r"^(however|moreover|furthermore|therefore|thus|hence|then|also|additionally|"
    r"in addition|in contrast|by contrast|consequently|"
    r"finally|first|second|third|fourth|based on|given that|as a result|taken together|"
    r"together|similarly|accordingly|meanwhile|specifically|overall|in summary|"
    r"in conclusion|to this end|in this (study|work|paper)|here)\b",
    re.I,
)
CAUSAL = re.compile(r"\b(causal\w*|evidence (of|for|against|supporting)|no (evidence|association|significant)|"
                    r"genetically predicted|genetic liability)\b", re.I)


def tidy_body(s: str) -> str:
    """Trim a sentence so it reads correctly after 'reported that'."""
    prev = None
    while prev != s:
        prev = s
        s = LEAD_JUNK.sub("", s)
        s = LEAD_CONNECTIVE.sub("", s)
    return s.strip()


def first_surname(authors_short: str, full: list[str]) -> str:
    if full:
        nm = full[0].strip()
        return nm.split()[-1] if nm.split() else nm
    if authors_short:
        first = authors_short.split(",")[0].strip()
        toks = first.split()
        return toks[-1] if toks else first
    return "The authors"


def is_sole_author(authors_short: str, full: list[str]) -> bool:
    if full:
        return len(full) == 1
    return authors_short.count(",") == 0 and "..." not in authors_short


def lower_first(s: str) -> str:
    if not s:
        return s
    w = s.split(" ", 1)[0]
    if len(w) > 1 and w[1:].isupper() and w[0].isupper():
        return s            # acronym or all-caps word: leave alone
    if w[:1].isupper():
        return s[0].lower() + s[1:]
    return s


# ----------------------------------------------------------------- model ----


@dataclass
class Claim:
    sentence: str
    attributed: str
    attributed_full: str
    section: str
    has_number: bool
    anchor: str


@dataclass
class Paper:
    index: int
    title: str
    title_raw: str
    slug: str
    year: str
    venue: str
    doi: str
    pmid: str
    authors_short: str
    authors_full: list[str]
    citations: int
    abstract: str
    abstract_source: str
    topics: list[str] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    headline: str = ""
    first_author_surname: str = ""
    is_first_author: bool = False
    url_scholar: str = ""
    openalex_id: str = ""
    publisher_year: str = ""
    retracted: bool = False

    @property
    def doi_url(self) -> str:
        return f"https://doi.org/{self.doi}" if self.doi else ""

    @property
    def path(self) -> str:
        return f"papers/{self.slug}.html"

    @property
    def authors_display(self) -> str:
        if self.authors_full:
            if len(self.authors_full) <= 8:
                return ", ".join(self.authors_full)
            return ", ".join(self.authors_full[:8]) + ", et al."
        a = self.authors_short
        return a + ("" if a.endswith("...") else "")

    @property
    def has_abstract(self) -> bool:
        return bool(self.abstract.strip())


RE_MR = re.compile(r"mendelian[\s-]?randomi[sz]ation|\btwo[- ]sample\b|\bbidirectional\b", re.I)
RE_MUSCULO = re.compile(
    r"\b(hip|knee|ankle|pelvi\w*|pelvis|femur|femoral|radiograph\w*|x[- ]ray\w*|"
    r"dysplasia|orthop\w*|sharp'?s angle|ce angle|lower limb)\b",
    re.I,
)


def _kw_regex(keywords: list[str]) -> re.Pattern:
    parts = []
    for k in keywords:
        k = re.escape(k)
        k = k.replace(r"\ ", r"[- ]?")
        k = k.replace(r"\-", r"[-\s]?")
        parts.append(k)
    return re.compile(r"\b(?:" + "|".join(parts) + r")", re.I)


for _t in TOPICS:
    _t["_re"] = _kw_regex(_t["keywords"])


def classify(title: str, abstract: str) -> list[str]:
    """Assign up to two topics, weighted towards the title."""
    t = title.lower()
    a = abstract[:1200].lower()

    if RE_MR.search(t):
        return ["mendelian-randomization"]

    scored: list[tuple[float, str]] = []
    for topic in TOPICS:
        rx = topic["_re"]
        n_title = len(rx.findall(t))
        n_abs = len(rx.findall(a))
        if not (n_title or n_abs):
            continue
        scored.append((n_title * 3 + min(n_abs, 4), topic["slug"]))
    scored.sort(key=lambda x: (-x[0], x[1]))

    # Mendelian-randomization prose in the abstract still beats a stray keyword.
    if RE_MR.search(a) and (not scored or scored[0][1] != "mendelian-randomization"):
        scored.insert(0, (99.0, "mendelian-randomization"))

    primary = [s for _, s in scored[:1]]
    if primary and primary[0] in ("musculoskeletal-ai",) and not RE_MUSCULO.search(t + " " + a[:400]):
        primary = [s for _, s in scored[1:2]] or ["other"]
    if primary and primary[0] == "mendelian-randomization":
        return ["mendelian-randomization"]

    secondary = []
    for _, slug in scored[1:]:
        if slug in primary or slug == "musculoskeletal-ai":
            continue
        secondary.append(slug)
        break
    out = primary + secondary
    return out or ["other"]


def build_claims(p: Paper, cfg: dict) -> list[Claim]:
    if not p.has_abstract:
        return []
    rows = sentence_section(p.abstract)
    lo = cfg.get("min_sentence_chars", 60)
    hi = cfg.get("max_sentence_chars", 320)
    n = cfg.get("max_claims_per_paper", 4)
    n_rows = max(len(rows) - 1, 1)

    def score_sentence(order: int, section: str, sent: str) -> float | None:
        """Return a relevance score, or None if the sentence cannot be a claim."""
        if not (lo <= len(sent) <= hi):
            return None
        if BOILERPLATE.search(sent):
            return None
        if sent.count("(") != sent.count(")"):
            return None
        has_digit = bool(re.search(r"\d", sent))
        finding = bool(CUE_FINDING.search(sent))
        result = bool(CUE_RESULT.search(sent))
        verb = bool(FINDING_VERB.search(sent))
        numeric = bool(NUMERIC_OUTCOME.search(sent))

        strict_ok = verb and not (DESIGN_PROSE.search(sent) and not numeric and not finding)
        relaxed_ok = numeric and (verb or finding or result)
        if not (strict_ok or relaxed_ok):
            return None
        if BACKGROUND_OPENERS.match(sent):
            return None
        if KNOWLEDGE_GAP.search(sent):
            return None
        if FRAGMENT_START.match(tidy_body(sent)):
            return None
        body_probe = tidy_body(sent)
        if DANGLING_START.match(body_probe) or DEPENDENT_START.match(body_probe):
            return None
        # A quote must open as a sentence: capital letter, digit or acronym.
        if not re.match(r"[A-Z0-9\u4e00-\u9fff]", body_probe):
            return None
        if re.search(r"\b(we|they|we next|next,? we|then we|we then)\b\s+(then|next)\b", sent, re.I):
            return None
        if re.search(r"\b(methods?|results?|conclusions?)\b\s+[A-Z]", sent):
            return None
        if re.search(r"\b(studies|research|evidence) (have|has|had) (shown|demonstrated|reported|found|suggested)\b", sent, re.I) and not has_digit:
            return None
        if order < 2 and not finding and not CAUSAL.search(sent):
            return None

        score = 0.0
        if strict_ok:
            score += 4.0
        if finding:
            score += 3.0
        if has_digit:
            score += 2.0
        if numeric:
            score += 2.0
        if result:
            score += 1.0
        if CAUSAL.search(sent):
            score += 2.0
        # Abstracts run background -> aim -> methods -> results -> conclusion:
        # later sentences are far likelier to be the actual finding.
        score += 4.0 * (order / n_rows)
        if DESIGN_PROSE.search(sent):
            score -= 3.0
        if section.startswith("result"):
            score += 2.5
        elif section.startswith("conclusion"):
            score += 2.0
        elif section.startswith("method"):
            score -= 3.0
        elif section.startswith("background"):
            score -= 2.0
        if order <= 1 and not has_digit:
            score -= 2.0          # opening sentences are usually framing
        if re.search(r"\b(is|are|was|were) (common|rare|one of the|a major|an important)\b", sent, re.I):
            score -= 2.0
        if len(sent) > 260:
            score -= 1.0
        if sent.rstrip().endswith("?"):
            score -= 3.0
        return score

    scored = []
    for order, (section, sent) in enumerate(rows):
        s = score_sentence(order, section, sent)
        scored.append(None if s is None else (s, order, section or "abstract", sent))
    scored = [s for s in scored if s is not None]

    scored.sort(key=lambda x: (-x[0], x[1]))
    picked = sorted(scored[: max(n * 2, n)], key=lambda x: x[1])[:n]

    surname = p.first_author_surname
    etal = "" if is_sole_author(p.authors_short, p.authors_full) else " et al."
    year = p.year or "n.d."
    short_attr = f"{surname}{etal} ({year})"
    full_attr = f"{surname}{etal} ({year}, *{p.venue}*)" if p.venue else short_attr

    claims = []
    for i, (score, order, section, sent) in enumerate(picked, 1):
        # Keep the author's own capitalisation: a quote is not re-typeset.
        body = tidy_body(sent).rstrip()
        claims.append(
            Claim(
                sentence=sent,
                attributed=f"{short_attr}. {body}",
                attributed_full=f"{full_attr}. {body}",
                section=section,
                has_number=bool(re.search(r"\d", sent)),
                anchor=f"c{i}",
            )
        )
    return claims


def build(cfg_path: Path | None = None) -> dict:
    cfg = json.loads((DATA / "site.json").read_text(encoding="utf-8"))
    raw = json.loads((DATA / "papers.enriched.json").read_text(encoding="utf-8"))
    prof = raw["profile"]

    papers: list[Paper] = []
    used_slugs: dict[str, int] = {}
    for i, r in enumerate(raw["papers"], 1):
        title = clean_text(r.get("title_oa") or r["title"])
        retracted = bool(re.match(r"^\s*retracted\s+article\s*[:\-\u2013]\s*", title, re.I))
        if retracted:
            title = re.sub(r"^\s*retracted\s+article\s*[:\-\u2013]\s*", "", title, count=1, flags=re.I)
        scholar_year = str(r.get("year") or "").strip()
        pub_year = str(r.get("publisher_year") or "").strip()
        year = scholar_year or pub_year
        slug_base = f"{year}-{slugify(title)}" if year else slugify(title)
        n = used_slugs.get(slug_base, 0)
        used_slugs[slug_base] = n + 1
        slug = slug_base if n == 0 else f"{slug_base}-{n + 1}"

        p = Paper(
            index=i,
            title=title,
            title_raw=r["title"],
            slug=slug,
            year=year,
            venue=clean_text(r.get("journal") or ""),
            doi=(r.get("doi") or "").lower(),
            pmid=r.get("pmid") or "",
            authors_short=r.get("authors") or "",
            authors_full=r.get("authors_full") or [],
            citations=int(r.get("cited_by") or 0),
            abstract=clean_text(r.get("abstract") or ""),
            abstract_source=r.get("abstract_source") or "",
            is_first_author=False,
            openalex_id=r.get("openalex_id") or "",
            publisher_year=pub_year,
            retracted=retracted,
        )
        full = p.authors_full
        p.is_first_author = bool(full) and "yang" in full[0].lower()
        if not full and p.authors_short:
            p.is_first_author = p.authors_short.lower().startswith("w yang")
        p.first_author_surname = first_surname(p.authors_short, full)
        p.topics = classify(title, p.abstract)
        p.claims = [] if p.retracted else build_claims(p, cfg)
        p.headline = p.claims[0].sentence if p.claims else ""
        papers.append(p)

    for t in TOPICS:
        t["papers"] = [p for p in papers if t["slug"] in p.topics]
    return {"cfg": cfg, "profile": prof, "papers": papers, "topics": TOPICS}


if __name__ == "__main__":
    d = build()
    print(f"papers={len(d['papers'])}")
    for p in d["papers"]:
        print(f"[{p.year}] {p.slug}")
        print(f"    topics={p.topics} claims={len(p.claims)} first_author={p.is_first_author}")
        for c in p.claims[:2]:
            print(f"    - {c.attributed[:150]}")
