"""
FinTech News Monitor — Data Pipeline
Fetches RSS feeds, filters, tags, and renders dist/index.html
"""

import calendar
import html
import json
import logging
import os
import re
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path

import certifi
import feedparser
import yaml
from jinja2 import Environment

# Fix SSL certificates on macOS (Python doesn't use system certs by default)
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration loaders
# ---------------------------------------------------------------------------

def load_sources(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("sources", [])


def load_keywords(path: str) -> dict[str, list[str]]:
    """Load keywords.yml and expand any 'A / B / C' multi-value entries."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    tags_raw = data.get("tags", {})
    tags: dict[str, list[str]] = {}
    for tag_name, kw_list in tags_raw.items():
        expanded: list[str] = []
        for kw in (kw_list or []):
            if "/" in str(kw):
                parts = [p.strip() for p in str(kw).split("/")]
                expanded.extend(p for p in parts if p)
            else:
                stripped = str(kw).strip()
                if stripped:
                    expanded.append(stripped)
        tags[tag_name] = expanded
    return tags


def _flatten(value) -> list[str]:
    """Recursively flatten nested dicts/lists into a flat list of strings."""
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_flatten(item))
        return result
    if isinstance(value, dict):
        result = []
        for v in value.values():
            result.extend(_flatten(v))
        return result
    return []


def load_exclude(path: str) -> list[str]:
    """Load exclude.yml — handles both flat list and nested-dict structures."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    raw = data.get("exclude_keywords", [])
    words = _flatten(raw)
    return [w.lower() for w in words if w]


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_url(url: str) -> str:
    return url.lower().rstrip("/")


def normalize_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ---------------------------------------------------------------------------
# RSS fetching & parsing
# ---------------------------------------------------------------------------

BUILD_TIME: datetime = datetime.now(timezone.utc)


def parse_entry(entry, source_name: str) -> dict | None:
    title = clean_text(getattr(entry, "title", "") or "")
    link = (getattr(entry, "link", "") or "").strip()
    if not title or not link:
        return None

    # Summary: prefer summary, fall back to content, then description
    raw_summary = (
        getattr(entry, "summary", "")
        or getattr(entry, "description", "")
        or ""
    )
    # feedparser sometimes puts full HTML content in 'content'
    if not raw_summary and hasattr(entry, "content") and entry.content:
        raw_summary = entry.content[0].get("value", "")
    summary = clean_text(raw_summary)

    # Published date
    date_unknown = False
    published_date = BUILD_TIME
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed:
        try:
            ts = calendar.timegm(parsed)
            published_date = datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            date_unknown = True
    else:
        date_unknown = True

    return {
        "title": title,
        "link": link,
        "summary": summary,
        "published_date": published_date,
        "date_unknown": date_unknown,
        "source_name": source_name,
        "tags": [],
    }


def fetch_feed(source: dict, timeout: int = 15) -> list[dict]:
    name = source.get("name", source.get("url", "unknown"))
    url = source.get("url", "")
    articles: list[dict] = []
    try:
        feed = feedparser.parse(url, agent="FinTechNewsMonitor/1.0", request_headers={"Connection": "close"})
        if getattr(feed, "bozo", False) and feed.bozo_exception:
            log.warning("[%s] Feed parse warning: %s", name, feed.bozo_exception)
        for entry in feed.entries:
            article = parse_entry(entry, name)
            if article:
                articles.append(article)
        log.info("[%s] Fetched %d entries", name, len(articles))
    except Exception as exc:
        log.warning("[%s] Failed to fetch: %s", name, exc)
    return articles


def fetch_all_feeds(sources: list[dict]) -> list[dict]:
    all_articles: list[dict] = []
    for source in sources:
        all_articles.extend(fetch_feed(source))
    return all_articles


# ---------------------------------------------------------------------------
# Processing pipeline
# ---------------------------------------------------------------------------

def deduplicate(articles: list[dict]) -> list[dict]:
    # Sort ascending by date so we keep the earliest on conflict
    sorted_articles = sorted(articles, key=lambda a: a["published_date"])
    seen_urls: dict[str, bool] = {}
    seen_titles: dict[str, bool] = {}
    result: list[dict] = []
    for article in sorted_articles:
        url_key = normalize_url(article["link"])
        title_key = normalize_title(article["title"])
        if url_key in seen_urls or title_key in seen_titles:
            continue
        seen_urls[url_key] = True
        seen_titles[title_key] = True
        result.append(article)
    return result


def apply_blacklist(articles: list[dict], exclude_words: list[str]) -> list[dict]:
    kept: list[dict] = []
    for article in articles:
        haystack = (article["title"] + " " + article["summary"]).lower()
        if any(word in haystack for word in exclude_words):
            log.debug("Excluded (blacklist): %s", article["title"])
            continue
        kept.append(article)
    return kept


def apply_relevance_and_tags(articles: list[dict], tags: dict[str, list[str]]) -> list[dict]:
    kept: list[dict] = []
    for article in articles:
        haystack = (article["title"] + " " + article["summary"]).lower()
        matched_tags: list[str] = []
        for tag_name, keywords in tags.items():
            if any(kw.lower() in haystack for kw in keywords):
                matched_tags.append(tag_name)
        if not matched_tags:
            log.debug("Excluded (no tags): %s", article["title"])
            continue
        article["tags"] = matched_tags
        kept.append(article)
    return kept


def sort_articles(articles: list[dict]) -> list[dict]:
    return sorted(
        articles,
        key=lambda a: (a["date_unknown"], -a["published_date"].timestamp()),
    )


def prepare_for_render(articles: list[dict]) -> list[dict]:
    """Add display fields for the HTML template."""
    result: list[dict] = []
    for a in articles:
        summary_full = a["summary"]
        summary_short = (summary_full[:280] + "...") if len(summary_full) > 280 else summary_full
        result.append({
            **a,
            "date_display": a["published_date"].strftime("%-d %b %Y"),
            "date_iso": a["published_date"].strftime("%Y-%m-%d"),
            "date_ts": int(a["published_date"].timestamp()),
            "summary_short": summary_short,
            "summary_full": summary_full,
            "tags_display": [t.replace("_", " ") for t in a["tags"]],
        })
    return result


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FinTech News Monitor</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #F5F6F8;
    --surface: #FFFFFF;
    --border: #E5E7EB;
    --text-primary: #111827;
    --text-secondary: #6B7280;
    --text-muted: #9CA3AF;
    --accent: #059669;
    --accent-hover: #047857;
    --accent-light: #ECFDF5;
    --accent-dark: #065F46;
    --accent-mid: #34D399;
    --accent-pale: #A7F3D0;
    --tag-bg: #F0FDF4;
    --tag-text: #166534;
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-pill: 999px;
    --shadow-card: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-card-hover: 0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
    --font: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", Helvetica, Arial, sans-serif;
  }

  body {
    font-family: var(--font);
    background: var(--bg);
    color: var(--text-primary);
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }

  /* ── Header ── */
  header {
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(255,255,255,0.92);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
  }
  .header-inner {
    max-width: 1120px;
    margin: 0 auto;
    padding: 0 24px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  .site-name {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.2px;
    white-space: nowrap;
  }
  .site-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent);
    flex-shrink: 0;
  }
  .build-time {
    font-size: 12px;
    color: var(--text-muted);
    white-space: nowrap;
  }

  /* ── Layout ── */
  .page-wrapper {
    max-width: 1120px;
    margin: 0 auto;
    padding: 24px 24px 48px;
  }

  /* ── Filter bar ── */
  .filter-bar {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 16px;
    margin-bottom: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }
  .tag-btn {
    padding: 5px 12px;
    border-radius: var(--radius-pill);
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
    line-height: 1.4;
    font-family: var(--font);
  }
  .tag-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
    background: var(--accent-light);
  }
  .tag-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }
  .tag-btn.all-btn.active {
    background: var(--text-primary);
    border-color: var(--text-primary);
    color: #fff;
  }
  .search-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .search-wrap {
    flex: 1;
    position: relative;
  }
  .search-icon {
    position: absolute;
    left: 11px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-muted);
    font-size: 14px;
    pointer-events: none;
    line-height: 1;
  }
  .search-input {
    width: 100%;
    padding: 8px 12px 8px 34px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-size: 13px;
    color: var(--text-primary);
    background: var(--bg);
    font-family: var(--font);
    transition: border-color 0.15s;
    outline: none;
  }
  .search-input::placeholder { color: var(--text-muted); }
  .search-input:focus { border-color: var(--accent); }
  .clear-btn {
    padding: 8px 14px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    white-space: nowrap;
    font-family: var(--font);
    transition: all 0.15s;
    display: none;
  }
  .clear-btn:hover { border-color: #DC2626; color: #DC2626; background: #FEF2F2; }
  .clear-btn.visible { display: inline-flex; align-items: center; gap: 4px; }

  /* ── Stats bar ── */
  .stats-bar {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 16px;
    padding: 0 2px;
  }
  .stats-bar span { color: var(--text-secondary); font-weight: 500; }

  /* ── Article grid ── */
  .article-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 12px;
  }
  .article-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 18px 20px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    box-shadow: var(--shadow-card);
    transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
    cursor: pointer;
  }
  .article-card:hover {
    border-color: var(--accent);
    box-shadow: var(--shadow-card-hover);
    transform: translateY(-1px);
  }
  .article-title {
    font-size: 14px;
    font-weight: 600;
    line-height: 1.45;
    color: var(--text-primary);
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .article-title a {
    color: inherit;
    text-decoration: none;
  }
  .article-title a:hover { color: var(--accent); }
  .article-meta {
    font-size: 11.5px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .meta-source {
    font-weight: 500;
    color: var(--text-secondary);
  }
  .meta-sep { opacity: 0.5; }
  .article-summary {
    font-size: 12.5px;
    color: var(--text-secondary);
    line-height: 1.6;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    flex: 1;
  }
  .article-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 2px;
  }
  .tag-badge {
    padding: 2px 8px;
    border-radius: var(--radius-pill);
    background: var(--tag-bg);
    color: var(--tag-text);
    font-size: 10.5px;
    font-weight: 500;
    border: 1px solid #BBF7D0;
    white-space: nowrap;
  }

  /* ── Empty state ── */
  .empty-state {
    display: none;
    grid-column: 1 / -1;
    text-align: center;
    padding: 64px 24px;
    color: var(--text-muted);
  }
  .empty-state.visible { display: block; }
  .empty-icon { font-size: 36px; margin-bottom: 12px; }
  .empty-title { font-size: 15px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
  .empty-sub { font-size: 13px; margin-bottom: 20px; }
  .empty-clear {
    padding: 8px 20px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--surface);
    font-size: 13px;
    cursor: pointer;
    font-family: var(--font);
    color: var(--text-secondary);
    transition: all 0.15s;
  }
  .empty-clear:hover { border-color: var(--accent); color: var(--accent); }

  /* ── Footer ── */
  footer {
    margin-top: 48px;
    padding-top: 24px;
    border-top: 1px solid var(--border);
  }
  .footer-sources {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 8px;
  }
  .footer-sources strong { color: var(--text-secondary); }
  .footer-disclaimer { font-size: 11px; color: var(--text-muted); line-height: 1.6; }

  /* ── Hero ── */
  .hero {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    margin-bottom: 12px;
    overflow: hidden;
    display: flex;
    align-items: stretch;
    position: relative;
  }
  .hero-left-accent {
    width: 4px;
    background: linear-gradient(180deg, var(--accent) 0%, var(--accent-mid) 60%, var(--accent-pale) 100%);
    flex-shrink: 0;
  }
  .hero-body {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex: 1;
    gap: 32px;
    padding: 28px 28px 26px 24px;
  }
  .hero-content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .hero-title {
    font-size: clamp(22px, 2.8vw, 34px);
    font-weight: 800;
    line-height: 1.15;
    letter-spacing: -0.5px;
    color: var(--text-primary);
  }
  .hero-title-accent { color: var(--accent); }
  .hero-subtitle {
    font-size: 13.5px;
    color: var(--text-secondary);
    line-height: 1.7;
    max-width: 520px;
  }
  .hero-bullets {
    display: flex;
    flex-direction: column;
    gap: 7px;
    margin-top: 2px;
  }
  .bullet-item {
    display: flex;
    align-items: flex-start;
    gap: 9px;
  }
  .bullet-icon {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
    margin-top: 1px;
  }
  .bullet-text {
    font-size: 12.5px;
    color: var(--text-secondary);
    line-height: 1.55;
  }
  .bullet-text strong { color: var(--text-primary); font-weight: 600; }

  /* Hero visual — decorative right side */
  .hero-visual {
    flex-shrink: 0;
    width: 160px;
    height: 120px;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  @media (max-width: 680px) { .hero-visual { display: none; } }

  /* ── Time range row ── */
  .time-row {
    border-top: 1px solid var(--border);
    padding-top: 10px;
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    align-items: center;
  }
  .time-label {
    font-size: 11px;
    font-weight: 500;
    color: var(--text-muted);
    margin-right: 2px;
  }
  .time-btn {
    padding: 4px 10px;
    border-radius: var(--radius-pill);
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-secondary);
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
    line-height: 1.4;
    font-family: var(--font);
  }
  .time-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
    background: var(--accent-light);
  }
  .time-btn.active {
    background: var(--text-primary);
    border-color: var(--text-primary);
    color: #fff;
  }

  /* ── Responsive ── */
  @media (max-width: 640px) {
    .page-wrapper { padding: 16px 16px 40px; }
    .header-inner { padding: 0 16px; }
    .article-grid { grid-template-columns: 1fr; gap: 10px; }
    .filter-bar { padding: 12px; }
    .hero-body { padding: 20px 16px 18px 16px; gap: 0; }
    .tag-row { overflow-x: auto; flex-wrap: nowrap; padding-bottom: 2px; }
    .tag-row::-webkit-scrollbar { display: none; }
    .time-row { overflow-x: auto; flex-wrap: nowrap; padding-bottom: 2px; }
    .time-row::-webkit-scrollbar { display: none; }
  }

  @media (prefers-reduced-motion: reduce) {
    * { transition: none !important; transform: none !important; }
  }
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <div class="site-name">
      <span class="site-dot"></span>
      FinTech News Monitor
    </div>
    <div class="build-time">Updated {{ build_time }}</div>
  </div>
</header>

<div class="page-wrapper">

  <!-- Hero intro -->
  <section class="hero">
    <div class="hero-left-accent"></div>
    <div class="hero-body">
      <div class="hero-content">
        <h1 class="hero-title">
          Stay on top of <span class="hero-title-accent">FinTech</span><br>in minutes.
        </h1>
        <p class="hero-subtitle">
          A lightweight daily monitor that aggregates trusted RSS sources, filters noise,
          and tags articles by topic&nbsp;&mdash; so you can scan faster and click through only what matters.
        </p>
        <div class="hero-bullets">
          <!-- Tag icon -->
          <div class="bullet-item">
            <svg class="bullet-icon" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="9" cy="9" r="9" fill="#059669"/>
              <path d="M5 9.5l2.5 2.5 5.5-5.5" stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="bullet-text"><strong>Filter by topic tags</strong> &middot; search across titles &amp; summaries</span>
          </div>
          <!-- Clock icon -->
          <div class="bullet-item">
            <svg class="bullet-icon" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="9" cy="9" r="9" fill="#059669"/>
              <circle cx="9" cy="9" r="4.5" stroke="white" stroke-width="1.4"/>
              <path d="M9 7v2.2l1.3 1.3" stroke="white" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
            <span class="bullet-text"><strong>Choose a time window</strong> &mdash; Last 24h, 7&nbsp;days, or 30&nbsp;days</span>
          </div>
          <!-- Refresh icon -->
          <div class="bullet-item">
            <svg class="bullet-icon" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="9" cy="9" r="9" fill="#059669"/>
              <path d="M5.5 9a3.5 3.5 0 0 1 6.3-2.1" stroke="white" stroke-width="1.4" stroke-linecap="round"/>
              <path d="M12.5 9a3.5 3.5 0 0 1-6.3 2.1" stroke="white" stroke-width="1.4" stroke-linecap="round"/>
              <path d="M11.2 6.5l.6 1.4 1.4-.5" stroke="white" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M6.8 11.5l-.6-1.4-1.4.5" stroke="white" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="bullet-text"><strong>Updated automatically every day</strong> from 9 trusted sources</span>
          </div>
        </div>
      </div>

      <!-- Decorative right-side visual -->
      <div class="hero-visual" aria-hidden="true">
        <svg width="160" height="120" viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
          <!-- Card stack abstraction -->
          <rect x="30" y="62" width="100" height="48" rx="6" fill="#065F46" opacity="0.08"/>
          <rect x="22" y="50" width="100" height="48" rx="6" fill="#059669" opacity="0.10"/>
          <rect x="14" y="38" width="100" height="48" rx="6" fill="#34D399" opacity="0.13"/>
          <!-- Top card details -->
          <rect x="20" y="12" width="100" height="48" rx="6" fill="#ECFDF5" stroke="#A7F3D0" stroke-width="1"/>
          <rect x="30" y="22" width="60" height="6" rx="3" fill="#059669" opacity="0.35"/>
          <rect x="30" y="32" width="80" height="4" rx="2" fill="#6B7280" opacity="0.2"/>
          <rect x="30" y="40" width="65" height="4" rx="2" fill="#6B7280" opacity="0.15"/>
          <rect x="30" y="48" width="28" height="8" rx="4" fill="#D1FAE5" stroke="#A7F3D0" stroke-width="0.8"/>
          <rect x="62" y="48" width="22" height="8" rx="4" fill="#D1FAE5" stroke="#A7F3D0" stroke-width="0.8"/>
          <!-- Dot indicator -->
          <circle cx="130" cy="16" r="4" fill="#059669" opacity="0.7"/>
          <circle cx="130" cy="16" r="7" stroke="#059669" stroke-width="1" opacity="0.25"/>
        </svg>
      </div>
    </div>
  </section>

  <!-- Filter bar -->
  <div class="filter-bar">
    <div class="tag-row" id="tagRow">
      <button class="tag-btn all-btn active" data-tag="__all__" onclick="toggleTag('__all__', this)">All</button>
      {% for tag_key in all_tags %}
      <button class="tag-btn" data-tag="{{ tag_key }}" onclick="toggleTag('{{ tag_key }}', this)">{{ tag_key | replace('_', ' ') }}</button>
      {% endfor %}
    </div>
    <div class="search-row">
      <div class="search-wrap">
        <span class="search-icon">⌕</span>
        <input
          class="search-input"
          type="text"
          id="searchInput"
          placeholder="Search articles..."
          oninput="onSearch(this.value)"
          aria-label="Search articles"
        >
      </div>
      <button class="clear-btn" id="clearBtn" onclick="clearFilters()">✕ Clear</button>
    </div>
    <div class="time-row">
      <span class="time-label">Time:</span>
      <button class="time-btn active" data-window="0" onclick="setTimeWindow(0, this)">All time</button>
      <button class="time-btn" data-window="86400" onclick="setTimeWindow(86400, this)">Last 24h</button>
      <button class="time-btn" data-window="604800" onclick="setTimeWindow(604800, this)">Last 7 days</button>
      <button class="time-btn" data-window="2592000" onclick="setTimeWindow(2592000, this)">Last 30 days</button>
    </div>
  </div>

  <!-- Stats -->
  <div class="stats-bar" id="statsBar">
    Showing <span id="statsCount">{{ articles | length }}</span> article{{ 's' if articles | length != 1 else '' }}
  </div>

  <!-- Article grid -->
  <div class="article-grid" id="articleGrid">
    {% for a in articles %}
    <article
      class="article-card"
      data-tags="{{ a.tags | join(',') }}"
      data-title="{{ a.title | lower }}"
      data-summary="{{ a.summary_full | lower }}"
      data-ts="{{ a.date_ts }}"
      onclick="window.open('{{ a.link }}', '_blank', 'noopener,noreferrer')"
    >
      <div class="article-title">
        <a href="{{ a.link }}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">{{ a.title }}</a>
      </div>
      <div class="article-meta">
        <span class="meta-source">{{ a.source_name }}</span>
        <span class="meta-sep">·</span>
        <span>{{ a.date_display }}</span>
      </div>
      {% if a.summary_short %}
      <p class="article-summary">{{ a.summary_short }}</p>
      {% endif %}
      <div class="article-tags">
        {% for tag_display in a.tags_display %}
        <span class="tag-badge">{{ tag_display }}</span>
        {% endfor %}
      </div>
    </article>
    {% endfor %}

    <!-- Empty state -->
    <div class="empty-state" id="emptyState">
      <div class="empty-icon">◎</div>
      <div class="empty-title">No articles match your filters</div>
      <div class="empty-sub">Try removing a tag filter or clearing your search.</div>
      <button class="empty-clear" onclick="clearFilters()">Clear Filters</button>
    </div>
  </div>

  <!-- Footer -->
  <footer>
    <div class="footer-sources">
      <strong>Sources:</strong>
      {% for s in sources %}{{ s.name }}{% if not loop.last %} · {% endif %}{% endfor %}
    </div>
    <div class="footer-disclaimer">
      Content sourced from third-party RSS feeds. FinTech News Monitor does not own or endorse any linked content.
    </div>
  </footer>

</div>

<script>
  const CARDS = document.querySelectorAll('.article-card');
  let selectedTags = new Set();
  let searchQuery = '';
  let timeWindow = 0; // seconds; 0 = all time

  function filterArticles() {
    const now = Math.floor(Date.now() / 1000);
    let visible = 0;

    CARDS.forEach(card => {
      const tags    = card.dataset.tags ? card.dataset.tags.split(',') : [];
      const title   = card.dataset.title   || '';
      const summary = card.dataset.summary || '';
      const ts      = parseInt(card.dataset.ts || '0', 10);

      const tagMatch  = selectedTags.size === 0 ||
                        [...selectedTags].some(t => tags.includes(t));
      const searchMatch = searchQuery === '' ||
                          title.includes(searchQuery) ||
                          summary.includes(searchQuery);
      const timeMatch = timeWindow === 0 || (now - ts) <= timeWindow;

      const show = tagMatch && searchMatch && timeMatch;
      card.style.display = show ? '' : 'none';
      if (show) visible++;
    });

    // Stats bar
    const bar = document.getElementById('statsBar');
    if (bar) bar.innerHTML = `Showing <span>${visible}</span> article${visible !== 1 ? 's' : ''}`;

    // Empty state
    const empty = document.getElementById('emptyState');
    if (empty) empty.classList.toggle('visible', visible === 0);

    // Clear button — show if any filter is active
    const clearBtn = document.getElementById('clearBtn');
    const hasFilter = selectedTags.size > 0 || searchQuery !== '' || timeWindow !== 0;
    if (clearBtn) clearBtn.classList.toggle('visible', hasFilter);
  }

  function toggleTag(tagKey, btn) {
    const allBtn = document.querySelector('.all-btn');
    if (tagKey === '__all__') {
      selectedTags.clear();
      document.querySelectorAll('.tag-btn:not(.all-btn)').forEach(b => b.classList.remove('active'));
      allBtn.classList.add('active');
    } else {
      allBtn.classList.remove('active');
      if (selectedTags.has(tagKey)) {
        selectedTags.delete(tagKey);
        btn.classList.remove('active');
      } else {
        selectedTags.add(tagKey);
        btn.classList.add('active');
      }
      if (selectedTags.size === 0) allBtn.classList.add('active');
    }
    filterArticles();
  }

  function onSearch(value) {
    searchQuery = value.trim().toLowerCase();
    filterArticles();
  }

  function setTimeWindow(seconds, btn) {
    timeWindow = seconds;
    document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    filterArticles();
  }

  function clearFilters() {
    selectedTags.clear();
    searchQuery = '';
    timeWindow  = 0;
    document.getElementById('searchInput').value = '';
    document.querySelectorAll('.tag-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.all-btn').classList.add('active');
    document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.time-btn[data-window="0"]').classList.add('active');
    filterArticles();
  }
</script>
</body>
</html>
"""


def render_html(
    articles: list[dict],
    tags: dict[str, list[str]],
    sources: list[dict],
    build_time: datetime,
    output_path: str,
) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    display_articles = prepare_for_render(articles)
    all_tags = sorted(tags.keys())
    build_time_str = build_time.strftime("%-d %b %Y, %H:%M UTC")

    env = Environment(autoescape=True)
    tmpl = env.from_string(HTML_TEMPLATE)
    rendered = tmpl.render(
        articles=display_articles,
        all_tags=all_tags,
        sources=sources,
        build_time=build_time_str,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
    )
    global BUILD_TIME
    BUILD_TIME = datetime.now(timezone.utc)

    base = Path(__file__).parent

    log.info("Loading configuration...")
    sources = load_sources(base / "sources.yml")
    tags = load_keywords(base / "keywords.yml")
    excludes = load_exclude(base / "exclude.yml")
    log.info("  %d sources, %d tag groups, %d exclude terms", len(sources), len(tags), len(excludes))

    log.info("Fetching RSS feeds...")
    articles = fetch_all_feeds(sources)
    log.info("Fetched %d raw articles", len(articles))

    articles = deduplicate(articles)
    log.info("After dedup: %d articles", len(articles))

    articles = apply_blacklist(articles, excludes)
    log.info("After blacklist filter: %d articles", len(articles))

    articles = apply_relevance_and_tags(articles, tags)
    log.info("After relevance filter + tagging: %d articles", len(articles))

    articles = sort_articles(articles)

    output = str(base / "dist" / "index.html")
    render_html(articles, tags, sources, BUILD_TIME, output)
    log.info("Generated: %s", output)


if __name__ == "__main__":
    main()
