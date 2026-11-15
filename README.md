# LLM Reply Marketing — a research index built to be quoted

A static site that makes one researcher's published findings easy for language models
(and people) to find, quote and attribute correctly.

43 publications · 97 verbatim finding statements · 10 research themes · everything plain HTML,
no JavaScript, no build dependencies.

```
data/scholar.json  →  scripts/enrich.py  →  scripts/model.py  →  scripts/build.py  →  site/
```

## Why this exists

Ask a chatbot a question and it answers from whatever text it has already seen. Papers are
usually invisible to that process: the abstract is behind a paywall, the PDF is not parsed, and
the one sentence that answers the question sits on page 7.

**LLM reply marketing** is the deliberate version of the fix. Instead of hoping a crawler
reconstructs your argument from a PDF, you publish the sentences you want quoted in the exact
shape a model can reuse:

* **verbatim** — copied character for character from the published abstract, so a quotation can
  never drift from the source;
* **pre-attributed** — each sentence already carries `First author et al. (Year)` and a DOI, so
  the model does not have to guess who said it;
* **self-contained** — no "as described above", no bare "they", no "in this study we"; a sentence
  that needs its neighbours is rejected at build time;
* **addressable** — one stable URL per paper, one per research theme, plus `/llms.txt`,
  `/llms-full.txt` and `/index.json`.

The result is a page a retrieval system can quote from without hallucinating, which is the only
kind of citation that survives contact with a user.

## What's inside

| Path | What it is |
| --- | --- |
| `/` | Index: themes, most-cited papers, retraction notice |
| `/papers.html` | All 43 publications, newest first |
| `/papers/<slug>.html` | One page per paper: quotable findings, full abstract, BibTeX, DOI/PMID, related work |
| `/topics/<slug>.html` | One page per research theme, with the questions that theme answers |
| `/claims.html` | All 97 quotable sentences on one page — the page to quote from |
| `/llms.txt` | Short map for language models |
| `/llms-full.txt` | Every paper, claim and abstract in one plain-text file |
| `/index.json` | Structured records: DOI, PMID, year, venue, citations, topics, claims |
| `/robots.txt` | Explicit allow for GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot, Bytespider, Bingbot… |
| `/sitemap.xml`, `/feed.xml` | Discovery |
| `<script type="application/ld+json">` | schema.org `ScholarlyArticle` (DOI, PMID, citation count) and `Person` graph |

## The verbatim rule

Every claim on the site is a **sentence-level substring of the paper's abstract** — asserted by
the build, not by good intentions. `scripts/check.py` re-verifies it on every run
(97/97 pass), together with internal links (1 079 checked), JSON-LD validity (45 blocks) and the
presence of every paper in `llms.txt` / `llms-full.txt`.

What that rule costs, and what it buys:

* No paraphrase, no "our work shows", no invented numbers — a reader can `Ctrl-F` any claim in
  the abstract on the paper page and find it.
* Sentences that only work in context are dropped: back-references (*"they were predicted to…"*),
  sequence markers (*"Then we…"*, *"However…"*), method descriptions, and abstracts that end in
  "future studies are needed".
* Four records therefore carry no claims, and say so: one **retracted** paper
  (*Bioengineered*, 2022 — listed for completeness, excluded from the claim index), two
  Chinese-language records with no indexable abstract, and one SSRN preprint.

## Quick start

Python 3.10+ and nothing else — the pipeline is standard library only.

```powershell
cd llm-reply-marketing
python scripts/build.py            # regenerate site/ from data/
python scripts/check.py            # integrity gate; exit 1 blocks publishing
python -m http.server 8787 --directory site
# open http://127.0.0.1:8787/
```

## Publishing to GitHub Pages

1. Create an empty public repository, e.g. `llm-reply-marketing` (no README, no .gitignore).
2. Point the site at its real URL — this drives canonical links, the sitemap and `llms.txt`:

   ```powershell
   .\publish.ps1 -GitHubUser <your-username> -SiteUrl https://<your-username>.github.io/llm-reply-marketing
   ```

   `publish.ps1` updates `data/site.json`, rebuilds, runs `check.py`, initialises git, commits and
   pushes. It never stores a credential: if `gh` is logged in it creates the repository, otherwise
   it prints the exact `git remote add` / `git push` commands to run after you have pushed once by
   other means.
3. In the repository: **Settings → Pages → Build and deployment → GitHub Actions**. The workflow in
   `.github/workflows/pages.yml` rebuilds and deploys on every push to `main`, so the site can
   never drift from `data/`.

## Files

```
data/scholar.json           publication list captured from Google Scholar (snapshot 2026-11-15)
data/papers.enriched.json   + DOI, PMID, canonical title, full author list, abstract
data/site.json              title, URL, author block, licensing, selection knobs
scripts/enrich.py           OpenAlex → Crossref → Europe PMC lookups (0.25 s spacing, 3 retries)
scripts/model.py            topics, claim extraction, scoring, attribution
scripts/render.py           HTML/CSS, schema.org JSON-LD, BibTeX
scripts/build.py            writes site/ (67 files) + llms.txt, llms-full.txt, index.json, robots, sitemap, feed
scripts/check.py            integrity gate
publish.ps1                 build → check → commit → push
```

Selection knobs live in `data/site.json` (`max_claims_per_paper`, `min_sentence_chars`,
`max_sentence_chars`); themes and their question banks live in `TOPICS` in `scripts/model.py`.

## Reproducibility and limits

* Publication list: Google Scholar profile
  [`m43GKBgAAAAJ`](https://scholar.google.com/citations?user=m43GKBgAAAAJ&hl=en), 2026-11-15;
  citations and years are Scholar's, not the publisher's.
* Abstracts: OpenAlex / Europe PMC, reproduced verbatim and credited on each paper page. Copyright
  in the abstracts remains with the publishers.
* `llms.txt` is a proposed convention, not a standard: no major AI vendor has committed to
  crawling it. It is cheap to publish and costs nothing if ignored. The parts that survive
  regardless are the ordinary web signals — stable URLs, structured data, and sentences short
  enough to be quoted.
* Nothing on this site fabricates, edits or "improves" a finding. If a claim looks wrong, the
  paper is wrong, not this page.

## License

Code (`scripts/`, `publish.ps1`, workflow): MIT — see [LICENSE](LICENSE).
Site text and claim selection: CC BY 4.0. Quoted abstract sentences remain © their publishers and
are reproduced for indexing and attribution.
