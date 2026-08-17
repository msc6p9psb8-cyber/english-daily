#!/usr/bin/env python3
"""Fetch live news from BBC/Guardian RSS -> /tmp/live_news.json.

Designed to run inside GitHub Actions (network is unrestricted there).
Uses only the Python standard library.

Behavior:
  1. Fetch BBC RSS, then Guardian RSS as fallback.
  2. For each of the top 5 items, fetch the article detail page and extract
     the FULL article body text (not just the RSS summary).
  3. Write /tmp/live_news.json where each item carries a "body" field with the
     full article text. update_news.py --inject then extracts vocab/grammar/
     slang from the full body instead of only the headline+summary.

Exit codes: 0 = OK (>=5 items written), 1 = all feeds failed.
"""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

FEEDS = [
    ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Guardian", "https://www.theguardian.com/world/rss"),
]

# A <body> of this many chars is considered a real full-text extraction.
MIN_BODY = 400

OUT_PATH = "/tmp/live_news.json"


def _clean(text):
    """Strip HTML tags/entities and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _fetch(url, timeout=30):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; english-daily-bot; +https://github.com/msc6p9psb8-cyber/english-daily)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _extract_body(html, source):
    """Extract full article body text from a detail page.

    BBC: paragraphs live in <div data-component="text-block"><p>...</p></div>.
    Guardian: paragraphs are plain <p> inside <div data-guardian="..."> main content.
    Fallback: join all <p> tags, excluding nav/footer/aside.
    """
    if not html:
        return ""
    text = html.decode("utf-8", "ignore")

    # BBC style
    paras = re.findall(
        r'data-component="text-block"[^>]*>\s*<p[^>]*>(.*?)</p>', text, re.DOTALL | re.IGNORECASE
    )
    # Guardian style (data-guardian block)
    if len(paras) < 3:
        g = re.search(
            r'<div[^>]*data-guardian="[^"]*"[^>]*>(.*?)</div>', text, re.DOTALL | re.IGNORECASE
        )
        if g:
            paras = re.findall(r"<p[^>]*>(.*?)</p>", g.group(1), re.DOTALL | re.IGNORECASE)

    # Generic fallback: gather <p> but skip known noise sections
    if len(paras) < 3:
        noise = re.compile(r"<nav|class=\"[^\"]*(nav|footer|aside|share|related)[^\"]*\"", re.IGNORECASE)
        # remove noise blocks first
        text_no = re.sub(r"<nav[\s\S]*?</nav>", " ", text, flags=re.IGNORECASE)
        paras = re.findall(r"<p[^>]*>(.*?)</p>", text_no, re.DOTALL | re.IGNORECASE)

    body_paras = []
    for p in paras:
        t = _clean(p)
        if len(t) >= 40:  # skip short captions / labels
            body_paras.append(t)

    body = "\n\n".join(body_paras)
    return body.strip()


def _parse(xml_bytes, source):
    """RSS 2.0 with <item><title/><link/><description/>."""
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.iter("item"):
        title = _clean(item.findtext("title"))
        link = _clean(item.findtext("link"))
        summary = _clean(item.findtext("description"))[:300]
        if title and link:
            items.append({"title": title, "link": link, "source": source, "summary": summary})
    return items


def _enrich_with_body(item):
    """Fetch the article detail page and attach a full 'body' field."""
    try:
        html = _fetch(item["link"], timeout=25)
        body = _extract_body(html, item["source"])
        if len(body) >= MIN_BODY:
            item["body"] = body
            print(f"  BODY ok: {len(body)} chars from {item['source']}")
        else:
            print(f"  BODY short ({len(body)} chars), keeping summary only")
    except Exception as e:
        print(f"  BODY fetch failed for {item['link']}: {e}", file=sys.stderr)
    return item


def main():
    for source, url in FEEDS:
        try:
            items = _parse(_fetch(url), source)
            if len(items) >= 5:
                picked = items[:5]
                print(f"FETCH OK: {len(picked)} items from {source}")
                # Enrich each item with full article body text
                for it in picked:
                    print(f"  - [{it['source']}] {it['title'][:80]}")
                    it = _enrich_with_body(it)
                with open(OUT_PATH, "w", encoding="utf-8") as f:
                    json.dump(picked, f, ensure_ascii=False, indent=1)
                return 0
            print(f"WARN: {source} returned only {len(items)} items", file=sys.stderr)
        except Exception as e:
            print(f"WARN: {source} failed: {e}", file=sys.stderr)
    print("FETCH FAILED: all feeds failed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
