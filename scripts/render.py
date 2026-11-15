"""HTML rendering for the research index.

Every page is static, readable without JavaScript, and carries schema.org
JSON-LD so that search engines and language models can parse it.
"""
from __future__ import annotations

import html
import json
from datetime import date

E = html.escape


def esc(s: str) -> str:
    return E(s or "", quote=True)


CSS = """
:root{
  --bg:#fbfaf7; --fg:#1a1a1a; --muted:#5c5c5c; --line:#e2ded6; --card:#ffffff;
  --accent:#8a3b12; --accent-soft:#f4ece5; --chip:#f0ece4;
}
@media (prefers-color-scheme: dark){
  :root{--bg:#14120f; --fg:#eeeae4; --muted:#a8a29a; --line:#2e2a25; --card:#1c1916;
        --accent:#e0a06a; --accent-soft:#2a211a; --chip:#241f1a;}
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);
  font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif;}
.wrap{max-width:820px;margin:0 auto;padding:0 22px}
header.site{border-bottom:1px solid var(--line);padding:18px 0;margin-bottom:38px}
header.site .wrap{display:flex;align-items:baseline;gap:18px;flex-wrap:wrap}
header.site a.brand{font-weight:650;color:var(--fg);text-decoration:none;letter-spacing:-.01em}
header.site nav{display:flex;gap:16px;flex-wrap:wrap;font-size:14.5px}
header.site nav a{color:var(--muted);text-decoration:none}
header.site nav a:hover{color:var(--accent)}
h1,h2,h3{font-family:Georgia,"Times New Roman","Songti SC","Noto Serif",serif;
  line-height:1.25;letter-spacing:-.015em;margin:1.9em 0 .6em}
h1{font-size:2.05rem;margin-top:.2em}
h2{font-size:1.35rem}
h3{font-size:1.08rem}
a{color:var(--accent)}
a:hover{text-decoration:none}
p{margin:.7em 0}
.lede{font-size:1.12rem;color:var(--muted)}
hr{border:0;border-top:1px solid var(--line);margin:2.4em 0}
.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:11.5px;color:var(--accent);
  font-weight:700;margin-bottom:.5em}
.meta{color:var(--muted);font-size:14.5px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px 22px;margin:1.2em 0}
.claim{border-left:3px solid var(--accent);background:var(--card);border-radius:0 10px 10px 0;
  padding:14px 18px;margin:12px 0;border:1px solid var(--line);border-left-width:3px}
.claim p{margin:0;font-size:15.6px}
.claim .tag{display:inline-block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;
  color:var(--muted);margin-bottom:6px}
.attr{font-variant:small-caps;letter-spacing:.02em;font-weight:650}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:.8em 0;padding:0;list-style:none}
.chips li a{display:inline-block;background:var(--chip);color:var(--fg);text-decoration:none;
  font-size:13px;padding:5px 11px;border-radius:999px;border:1px solid var(--line)}
.chips li a:hover{background:var(--accent-soft);color:var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(238px,1fr));gap:14px;padding:0;list-style:none;margin:1.4em 0}
.grid li{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.grid li a{text-decoration:none;color:var(--fg);font-weight:600;display:block;margin-bottom:5px}
.grid li a:hover{color:var(--accent)}
.grid li .meta{font-size:13px}
ol.papers{list-style:none;padding:0;margin:1.2em 0}
ol.papers>li{padding:14px 0;border-bottom:1px solid var(--line)}
ol.papers>li:last-child{border-bottom:0}
ol.papers a.title{font-weight:600;text-decoration:none;color:var(--fg)}
ol.papers a.title:hover{color:var(--accent)}
.abstract{font-size:15px;color:var(--fg);background:var(--accent-soft);border-radius:10px;padding:16px 20px}
.abstract h2{margin-top:0;font-size:1rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
pre{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;
  overflow-x:auto;font-size:13px;line-height:1.5;white-space:pre-wrap;word-break:break-word}
code{font-size:.92em;word-break:break-word}
.notice{border:1px solid #b42318;background:#fdf3f2;color:#7a1c14;border-radius:10px;padding:14px 18px;margin:1.2em 0}
@media (prefers-color-scheme: dark){.notice{background:#2a1512;color:#f0b8b0;border-color:#7a3b33}}
footer.site{border-top:1px solid var(--line);margin-top:56px;padding:26px 0 60px;color:var(--muted);font-size:14px}
.small{font-size:13.5px;color:var(--muted)}
table{border-collapse:collapse;width:100%;font-size:14.5px}
td,th{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left;vertical-align:top}
"""


def page(cfg: dict, title: str, body: str, *, desc: str = "", canonical: str = "",
         jsonld: dict | list | None = None, nav_extra: str = "") -> str:
    site_title = cfg["site_title"]
    t = f"{title} · {site_title}" if title != site_title else site_title
    ld = ""
    if jsonld:
        blob = json.dumps(jsonld, ensure_ascii=False, indent=2)
        ld = f'<script type="application/ld+json">\n{blob}\n</script>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(t)}</title>
<meta name="description" content="{esc(desc)}">
{('<link rel="canonical" href="' + esc(canonical) + '">') if canonical else ''}
<meta name="author" content="{esc(cfg['author']['name'])}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(t)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:site_name" content="{esc(site_title)}">
{('<meta property="og:url" content="' + esc(canonical) + '">') if canonical else ''}
<meta name="twitter:card" content="summary">
<link rel="alternate" type="text/plain" href="/llms.txt" title="llms.txt">
<style>{CSS}</style>
{ld}
</head>
<body>
<header class="site"><div class="wrap">
<a class="brand" href="/">{esc(site_title)}</a>
<nav>
<a href="/papers.html">Papers</a>
<a href="/topics/">Topics</a>
<a href="/claims.html">Claim index</a>
<a href="/about.html">About</a>
<a href="/llms.txt">llms.txt</a>{nav_extra}
</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="site"><div class="wrap">
<p>{esc(cfg['author']['name'])} · {esc(cfg['author']['affiliation'])}</p>
<p class="small">Snapshot {esc(cfg['snapshot_date'])}. Text is quoted verbatim from the published
abstracts; nothing here paraphrases a scientific finding. Abstract text is reproduced for
discovery and citation, and remains © the original publishers. Site code and metadata are
licensed {esc(cfg['license'])}.</p>
<p class="small"><a href="/llms.txt">llms.txt</a> · <a href="/llms-full.txt">llms-full.txt</a> ·
<a href="/index.json">index.json</a> · <a href="{esc(cfg['author']['scholar_url'])}">Google Scholar</a></p>
</div></footer>
</body>
</html>
"""


# ------------------------------------------------------------- fragments ----


def person_jsonld(cfg: dict) -> dict:
    a = cfg["author"]
    return {
        "@type": "Person",
        "@id": cfg["site_url"] + "/#person",
        "name": a["name"],
        "alternateName": a.get("name_variants", []),
        "affiliation": {"@type": "Organization", "name": a["affiliation"]},
        "url": cfg["site_url"] + "/",
        "sameAs": [u for u in [a.get("scholar_url"), a.get("orcid_url"), a.get("github_url")] if u],
        "identifier": [{"@type": "PropertyValue", "propertyID": "GoogleScholar",
                        "value": a.get("scholar_id", "")}],
    }


def author_names(p) -> list[str]:
    if p.authors_full:
        return p.authors_full
    return [a.strip() for a in (p.authors_short or "").split(",") if a.strip()]


def paper_jsonld(cfg: dict, p) -> dict:
    d = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": p.title,
        "name": p.title,
        "url": f"{cfg['site_url']}/{p.path}",
        "author": [{"@type": "Person", "name": n} for n in author_names(p)],
        "datePublished": p.year,
        "isPartOf": {"@type": "Periodical", "name": p.venue} if p.venue else None,
        "abstract": p.abstract or None,
        "inLanguage": "zh" if any("\u4e00" <= c <= "\u9fff" for c in p.title) else "en",
        "identifier": [],
        "sameAs": [],
        "isAccessibleForFree": True,
    }
    if p.doi:
        d["identifier"].append({"@type": "PropertyValue", "propertyID": "DOI", "value": p.doi})
        d["sameAs"].append(p.doi_url)
    if p.pmid:
        d["identifier"].append({"@type": "PropertyValue", "propertyID": "PMID", "value": p.pmid})
        d["sameAs"].append(f"https://pubmed.ncbi.nlm.nih.gov/{p.pmid}/")
    if p.citations:
        d["interactionStatistic"] = {
            "@type": "InteractionCounter",
            "interactionType": "https://schema.org/CiteAction",
            "userInteractionCount": p.citations,
        }
    return {k: v for k, v in d.items() if v not in (None, [], "")}


def claim_html(c: dict) -> str:
    return (
        f'<div class="claim" id="{esc(c["anchor"])}">'
        f'<span class="tag">Finding {esc(c["anchor"][1:])}</span>'
        f'<p>{esc(c["attributed"])}</p></div>'
    )


def bibtex(p) -> str:
    first = (p.authors_full[0].split()[-1].lower() if p.authors_full else "unknown")
    key = f"{first}{p.year}{p.slug.split('-')[0]}"
    authors = " and ".join(author_names(p)) or p.authors_short
    lines = [
        f"@article{{{key},",
        f"  author  = {{{authors}}},",
        f"  title   = {{{p.title}}},",
        f"  journal = {{{p.venue}}}," if p.venue else "",
        f"  year    = {{{p.year}}},",
        f"  doi     = {{{p.doi}}}," if p.doi else "",
        f"  pmid    = {{{p.pmid}}}," if p.pmid else "",
        "}",
    ]
    return "\n".join(l for l in lines if l)


def paper_card(cfg: dict, p, *, show_claim: bool = True) -> str:
    bits = []
    if p.venue:
        bits.append(esc(p.venue))
    if p.citations:
        bits.append(f"{p.citations} cited")
    meta = " · ".join(bits)
    claim = ""
    if show_claim and p.claims:
        claim = f'<p class="small" style="margin:.45em 0 0">{esc(p.claims[0].attributed)}</p>'
    warn = ' <span class="small" style="color:#b42318">· retracted</span>' if p.retracted else ""
    return (
        f'<li><a class="title" href="/{esc(p.path)}">{esc(p.title)}</a>'
        f'<div class="meta">{esc(", ".join(author_names(p)[:4]))}'
        f'{" et al." if len(author_names(p)) > 4 else ""} · {esc(p.year)}'
        f"{' · ' + meta if meta else ''}{warn}</div>{claim}</li>"
    )
