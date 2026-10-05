#!/usr/bin/env python3
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

OUTPUT = Path("news.json")
MAX_ITEMS = 120
JST = timezone(timedelta(hours=9))

MEMBERS = {
    "RM": ["RM", "NAMJOON", "NAM JUN", "ナムジュン"],
    "JIN": ["JIN", "SEOKJIN", "SEOK JIN", "ジン"],
    "SUGA": ["SUGA", "YOONGI", "ユンギ"],
    "J-HOPE": ["J-HOPE", "JHOPE", "HOSEOK", "ホソク", "ジェイホープ"],
    "JIMIN": ["JIMIN", "ジミン"],
    "V": ["TAEHYUNG", "テテ", "テヒョン"],
    "JUNG KOOK": ["JUNG KOOK", "JUNGKOOK", "JEON JUNGKOOK", "ジョングク", "グク"],
}

SEARCHES = [
    ("ALL", "BTS"),
    ("RM", 'BTS RM OR ナムジュン'),
    ("JIN", 'BTS JIN OR ジン'),
    ("SUGA", 'BTS SUGA OR ユンギ'),
    ("J-HOPE", 'BTS "J-HOPE" OR ホソク'),
    ("JIMIN", 'BTS JIMIN OR ジミン'),
    ("V", 'BTS V OR テヒョン OR テテ'),
    ("JUNG KOOK", 'BTS "JUNG KOOK" OR JUNGKOOK OR ジョングク'),
]

def strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def normalize_title(title):
    return re.sub(r"\s+", " ", strip_html(title)).strip()

def contains_v(text):
    return re.search(r"(^|[\s（(【「『])V(?=$|[\s、。：:）)】」』])", text, re.I) is not None

def detect_member(text):
    upper = text.upper()
    hits = []
    for member, aliases in MEMBERS.items():
        if member == "V":
            if contains_v(text):
                hits.append(member)
            continue
        if any(alias.upper() in upper for alias in aliases):
            hits.append(member)
    return hits[0] if len(hits) == 1 else "ALL"

def rss_url(query):
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "ja",
        "gl": "JP",
        "ceid": "JP:ja",
    })
    return f"https://news.google.com/rss/search?{params}"

def fetch_feed(label, query):
    req = urllib.request.Request(
        rss_url(query),
        headers={"User-Agent": "Mozilla/5.0 BTS-News-Hub/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()

    root = ET.fromstring(data)
    items = []

    for item in root.findall("./channel/item"):
        title = normalize_title(item.findtext("title", ""))
        link = (item.findtext("link", "") or "").strip()
        desc = strip_html(item.findtext("description", ""))
        pub = item.findtext("pubDate", "")
        source_el = item.find("source")
        source = strip_html(source_el.text if source_el is not None else "")

        if not title or not link:
            continue

        try:
            dt = parsedate_to_datetime(pub)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            date_str = dt.astimezone(JST).date().isoformat()
            timestamp = dt.timestamp()
        except Exception:
            date_str = datetime.now(JST).date().isoformat()
            timestamp = 0

        member = label if label != "ALL" else detect_member(f"{title} {desc}")

        # Google News titles often end in " - Publisher". The source field already contains it.
        if source and title.endswith(f" - {source}"):
            title = title[:-(len(source) + 3)].rstrip()

        items.append({
            "m": member,
            "d": date_str,
            "s": source or "Google News",
            "t": title,
            "x": desc[:280] if desc else "最新記事です。",
            "u": link,
            "_ts": timestamp,
        })
    return items

def dedupe(items):
    chosen = {}
    for item in items:
        key = re.sub(r"\W+", "", item["t"].lower())
        if not key:
            key = item["u"]
        old = chosen.get(key)
        if old is None:
            chosen[key] = item
        else:
            # Prefer a member-specific classification over ALL.
            if old["m"] == "ALL" and item["m"] != "ALL":
                chosen[key] = item
            elif item["_ts"] > old["_ts"]:
                chosen[key] = item
    return list(chosen.values())

def main():
    all_items = []
    failures = []

    for label, query in SEARCHES:
        try:
            all_items.extend(fetch_feed(label, query))
        except Exception as e:
            failures.append(f"{label}: {e}")
        time.sleep(0.6)

    items = dedupe(all_items)
    items.sort(key=lambda x: (x["_ts"], x["d"]), reverse=True)
    items = items[:MAX_ITEMS]

    for item in items:
        item.pop("_ts", None)

    OUTPUT.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Wrote {len(items)} articles to {OUTPUT}")
    if failures:
        print("Some feeds failed:")
        for failure in failures:
            print(" -", failure)

if __name__ == "__main__":
    main()
