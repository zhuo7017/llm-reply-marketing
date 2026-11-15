"""Enrich the Google Scholar publication list with DOI / abstract / venue.

Sources, in order of trust for each field:
  OpenAlex   -> DOI, canonical title, abstract (inverted index), venue, authors, concepts
  Crossref   -> DOI fallback, publisher metadata
  EuropePMC  -> abstract fallback (biomedical full text is richest here)

Nothing here rewrites a paper's science: every stored sentence is copied verbatim
from the source abstract. The build step never invents findings.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MAILTO = "llm-reply-marketing@example.org"
UA = f"llm-reply-marketing/1.0 (mailto:{MAILTO})"


def get_json(url: str, tries: int = 3) -> dict | None:
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                print(f"    ! {type(e).__name__}: {e}")
                return None
            time.sleep(1.5 * (i + 1))
    return None


def norm_title(s: str) -> str:
    s = s.lower()
    s = s.replace("\u2010", "-").replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    s = s.replace("\u2212", "-").replace("\u2019", "'")
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


def similar(a: str, b: str) -> float:
    a, b = norm_title(a), norm_title(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ratio = SequenceMatcher(None, a, b).ratio()
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    if short in long and len(short) / len(long) > 0.75:
        ratio = max(ratio, 0.95)
    return ratio


def abstract_from_inverted(idx: dict) -> str:
    if not isinstance(idx, dict) or not idx:
        return ""
    pos: dict[int, str] = {}
    for word, places in idx.items():
        for p in places:
            pos[p] = word
    if not pos:
        return ""
    return " ".join(pos[i] for i in sorted(pos))


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = (
        s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    )
    return re.sub(r"\s+", " ", s).strip()


def openalex_lookup(title: str) -> dict | None:
    q = urllib.parse.quote(title)
    url = (
        "https://api.openalex.org/works?per-page=5&mailto=" + MAILTO
        + "&filter=title.search:" + q
        + "&select=id,doi,title,display_name,publication_year,abstract_inverted_index,"
          "primary_location,authorships,cited_by_count,type,concepts,biblio,ids"
    )
    data = get_json(url)
    if not data:
        return None
    best, best_score = None, 0.0
    for w in data.get("results", []):
        t = w.get("display_name") or w.get("title") or ""
        score = similar(title, t)
        if score > best_score:
            best, best_score = w, score
    if best and best_score >= 0.86:
        best["_match"] = round(best_score, 3)
        return best
    return None


def crossref_lookup(title: str) -> str:
    q = urllib.parse.quote(title)
    url = f"https://api.crossref.org/works?rows=5&select=DOI,title,is-referenced-by-count&query.bibliographic={q}&mailto={MAILTO}"
    data = get_json(url)
    if not data:
        return ""
    best, best_score = "", 0.0
    for it in data.get("message", {}).get("items", []):
        t = (it.get("title") or [""])[0]
        s = similar(title, t)
        if s > best_score:
            best, best_score = it.get("DOI", ""), s
    return best if best_score >= 0.90 else ""


def europepmc_abstract(title: str) -> tuple[str, str, str]:
    q = urllib.parse.quote(f'TITLE:"{title}"')
    url = (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json&resultType=core"
        f"&pageSize=5&query={q}"
    )
    data = get_json(url)
    if not data:
        return "", "", ""
    best, best_score = None, 0.0
    for it in data.get("resultList", {}).get("result", []):
        s = similar(title, it.get("title", ""))
        if s > best_score:
            best, best_score = it, s
    if best and best_score >= 0.86:
        return strip_tags(best.get("abstractText", "")), best.get("pmid", ""), best.get("doi", "")
    return "", "", ""


def main() -> None:
    src = json.loads((DATA / "scholar.json").read_text(encoding="utf-8"))
    pubs = src["pubs"]
    out = []

    for i, p in enumerate(pubs, 1):
        title = p["title"]
        print(f"[{i:2d}/{len(pubs)}] {title[:70]}")
        rec = dict(p)
        rec.update({"doi": "", "pmid": "", "abstract": "", "abstract_source": "",
                    "journal": p["venue"], "openalex_id": "", "concepts": [],
                    "authors_full": [], "match_score": 0, "publisher_year": ""})

        oa = openalex_lookup(title)
        if oa:
            rec["match_score"] = oa.pop("_match", 0)
            rec["doi"] = (oa.get("doi") or "").replace("https://doi.org/", "")
            rec["openalex_id"] = oa.get("id", "")
            rec["title_oa"] = oa.get("display_name") or title
            rec["publisher_year"] = oa.get("publication_year") or ""
            loc = oa.get("primary_location") or {}
            src_name = ((loc.get("source") or {}) or {}).get("display_name") or ""
            if src_name:
                rec["journal"] = src_name
            rec["authors_full"] = [
                a["author"]["display_name"]
                for a in (oa.get("authorships") or [])
                if (a.get("author") or {}).get("display_name")
            ]
            rec["concepts"] = [
                c["display_name"] for c in (oa.get("concepts") or [])[:8] if c.get("score", 0) > 0.3
            ]
            abs_txt = abstract_from_inverted(oa.get("abstract_inverted_index"))
            if abs_txt:
                rec["abstract"] = strip_tags(abs_txt)
                rec["abstract_source"] = "openalex"

        if not rec["doi"]:
            doi = crossref_lookup(title)
            if doi:
                rec["doi"] = doi
                rec["abstract_source"] = rec["abstract_source"] or ""

        if not rec["abstract"]:
            abs_txt, pmid, doi2 = europepmc_abstract(title)
            if abs_txt:
                rec["abstract"] = abs_txt
                rec["abstract_source"] = "europepmc"
            rec["pmid"] = pmid or rec["pmid"]
            if not rec["doi"] and doi2:
                rec["doi"] = doi2

        print(
            f"     doi={rec['doi'] or '-'} pmc={rec['pmid'] or '-'} "
            f"abs={len(rec['abstract'])} src={rec['abstract_source'] or '-'} "
            f"score={rec['match_score']}"
        )
        out.append(rec)
        time.sleep(0.25)

    payload = {
        "profile": src.get("profile", {}),
        "generated_by": "scripts/enrich.py",
        "papers": out,
    }
    (DATA / "papers.enriched.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    have_abs = sum(1 for r in out if r["abstract"])
    have_doi = sum(1 for r in out if r["doi"])
    print(f"\nDONE  abstracts={have_abs}/{len(out)}  dois={have_doi}/{len(out)}")


if __name__ == "__main__":
    main()
