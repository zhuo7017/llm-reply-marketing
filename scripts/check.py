#!/usr/bin/env python3
"""Integrity checks for the built site.

Verifies the three promises the site makes to readers and to language models:

1. Every claim sentence really is a verbatim substring of the paper's abstract.
2. Every internal link and asset resolves to a file that exists.
3. Every JSON-LD block parses, and the machine-readable indexes are in sync
   with the rendered pages.

Run after `python scripts/build.py`. Exit code 1 means the build cannot be
published as-is.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = ROOT / "data"

errors: list[str] = []
warnings: list[str] = []


def norm(s: str) -> str:
    """Normalise for comparison: NFKC, collapse whitespace, unify dashes/quotes."""
    s = unicodedata.normalize("NFKC", s)
    for a, b in (("\u2013", "-"), ("\u2014", "-"), ("\u2212", "-"), ("\u2019", "'"),
                 ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u00a0", " ")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip().lower()


def slug_of(p: dict) -> str:
    """'https://host/papers/2021-....html' -> '2021-....'"""
    return Path(p["url"].split("?")[0]).stem


def check_claims(index: dict) -> None:
    total = 0
    for p in index["papers"]:
        abstract = p.get("abstract") or ""
        na = norm(abstract)
        slug = slug_of(p)
        surname = (p.get("first_author") or "").split()[-1] if p.get("first_author") else ""
        for c in p["claims"]:
            total += 1
            body = c["text"]
            if norm(body) not in na:
                errors.append(f"claim not verbatim in abstract: {slug} :: {body[:90]}")
            if surname and not c["attributed"].startswith(surname):
                errors.append(f"claim attribution does not start with first author ({surname}): {slug}")
            if body.rstrip()[-1:] not in ".!?°%)":
                warnings.append(f"claim does not end like a sentence: {slug} :: {body[-60:]}")
            if len(body) < 40:
                warnings.append(f"very short claim: {slug} :: {body}")
        if p["retracted"] and p["claims"]:
            errors.append(f"retracted paper still exposes claims: {slug}")
        if not p["claims"] and not p["retracted"] and p.get("abstract"):
            warnings.append(f"paper has an abstract but no claims: {slug}")
    print(f"claims checked: {total}")


def check_links() -> None:
    href_re = re.compile(r'(?:href|src)="(/[^"#?]*)')
    seen = 0
    for f in SITE.rglob("*.html"):
        html = f.read_text(encoding="utf-8")
        for href in href_re.findall(html):
            seen += 1
            target = SITE / href.lstrip("/")
            if href.endswith("/"):
                target = target / "index.html"
            if not target.exists():
                errors.append(f"broken link in {f.relative_to(SITE)}: {href}")
    print(f"internal links checked: {seen}")


def check_jsonld() -> None:
    blocks = 0
    for f in SITE.rglob("*.html"):
        html = f.read_text(encoding="utf-8")
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            blocks += 1
            try:
                obj = json.loads(m.group(1))
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON-LD in {f.relative_to(SITE)}: {exc}")
                continue
            if "@context" not in obj:
                errors.append(f"JSON-LD without @context in {f.relative_to(SITE)}")
            elif "@type" not in obj and "@graph" not in obj:
                errors.append(f"JSON-LD without @type/@graph in {f.relative_to(SITE)}")
            elif "@graph" in obj and not all("@type" in n for n in obj["@graph"]):
                errors.append(f"JSON-LD @graph node without @type in {f.relative_to(SITE)}")
    print(f"JSON-LD blocks checked: {blocks}")


def check_artifacts(index: dict) -> None:
    for name in ("llms.txt", "llms-full.txt", "index.json", "sitemap.xml",
                 "robots.txt", "feed.xml", ".nojekyll", "404.html"):
        if not (SITE / name).exists():
            errors.append(f"missing artifact: {name}")

    llms = (SITE / "llms.txt").read_text(encoding="utf-8")
    full = (SITE / "llms-full.txt").read_text(encoding="utf-8")
    for p in index["papers"]:
        slug = slug_of(p)
        if slug not in llms:
            errors.append(f"paper missing from llms.txt: {slug}")
        if slug not in full:
            errors.append(f"paper missing from llms-full.txt: {slug}")

    count = index["counts"]["claims"]
    if llms.count("claim") < 1:
        errors.append("llms.txt does not mention the claim index")

    robots = (SITE / "robots.txt").read_text(encoding="utf-8")
    for bot in ("GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "CCBot"):
        if bot not in robots:
            errors.append(f"robots.txt does not name {bot}")

    site_cfg = json.loads((DATA / "site.json").read_text(encoding="utf-8"))
    url = site_cfg.get("site_url", "")
    if "USERNAME" in url:
        warnings.append("site_url still contains the USERNAME placeholder — "
                        "canonical URLs and the sitemap will be wrong for the real domain")
    if not url.startswith("https://"):
        warnings.append(f"site_url is not https: {url}")
    print(f"artifacts checked, declared claim count: {count}")


def main() -> int:
    index_path = SITE / "index.json"
    if not index_path.exists():
        print("site/index.json missing — run scripts/build.py first", file=sys.stderr)
        return 1
    index = json.loads(index_path.read_text(encoding="utf-8"))

    check_claims(index)
    check_links()
    check_jsonld()
    check_artifacts(index)

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
