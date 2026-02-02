import os, json, re
import feedparser
from datetime import datetime, timezone
from pathlib import Path

# ローカル実行時は .env から読み込む
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- 設定 ---
MAX_ITEMS_PER_FEED = 5       # 各フィードから処理する上限
MAX_SEEN = 2000              # state.json肥大化防止
OUT_DIR = Path("public")
STATE_PATH = Path("state.json")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing")

from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"seen": []}

def save_state(state):
    state["seen"] = state["seen"][-MAX_SEEN:]
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def is_japanese(text: str) -> bool:
    return any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in text)

def summarize_to_japanese(title: str, content: str) -> str:
    prompt = f"""
あなたは最先端のトレンドを追う知的好奇心旺盛な読者向けの編集者です。
次の英語記事を日本語で要約し、RSSリーダーで読みやすいHTML形式で出力してください。

## 出力フォーマット（HTML）
<p><strong>一言で言うと:</strong> （1文で核心を突く）</p>
<p><strong>ポイント:</strong></p>
<ul>
<li>（重要な発見・主張を3〜4点）</li>
</ul>
<p><strong>So What?:</strong> （この情報が読者にとってなぜ重要か、どう活かせるか）</p>

## ルール
- 必ず上記のHTML形式で出力すること
- 専門用語は残しつつ、初見でも分かる短い補足を括弧内に
- 「〜と思われる」「〜の可能性」など、推測と事実を区別
- 堅すぎず、知的な友人に話すようなトーンで
- 200〜300字程度

## 記事情報
TITLE: {title}

CONTENT:
{content}
""".strip()

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()

def read_feeds_by_category():
    """feeds.txt をカテゴリごとに分けて読み込む"""
    lines = Path("feeds.txt").read_text(encoding="utf-8").splitlines()
    categories = {}
    current_category = "other"

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("# ====="):
            # カテゴリ名を抽出: "# ===== カテゴリ名 =====" → "カテゴリ名"
            match = re.search(r"# =+ (.+?) =+", line)
            if match:
                current_category = match.group(1).strip()
                # ファイル名用にスラッグ化
                slug = current_category.lower()
                slug = re.sub(r'[（(].+?[）)]', '', slug)  # 括弧内を除去
                slug = re.sub(r'[^a-z0-9]+', '_', slug).strip('_')
                current_category = slug if slug else "other"
                if current_category not in categories:
                    categories[current_category] = {"name": match.group(1).strip(), "feeds": []}
        elif line.startswith("#"):
            continue
        else:
            if current_category not in categories:
                categories[current_category] = {"name": current_category, "feeds": []}
            categories[current_category]["feeds"].append(line)

    return categories

def rss_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&apos;"))

def build_rss(items, category_name):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
    channel_title = f"日本語要約RSS - {category_name}"
    channel_link = "https://github.com/"
    channel_desc = f"{category_name}の英語記事を日本語要約して配信します。"

    out = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append('<rss version="2.0">')
    out.append('<channel>')
    out.append(f"<title>{rss_escape(channel_title)}</title>")
    out.append(f"<link>{rss_escape(channel_link)}</link>")
    out.append(f"<description>{rss_escape(channel_desc)}</description>")
    out.append(f"<lastBuildDate>{now}</lastBuildDate>")

    for it in items:
        out.append("<item>")
        out.append(f"<title>{rss_escape(it['title'])}</title>")
        out.append(f"<link>{rss_escape(it['link'])}</link>")
        out.append(f"<guid isPermaLink='false'>{rss_escape(it['guid'])}</guid>")
        out.append(f"<pubDate>{rss_escape(it['pubDate'])}</pubDate>")
        out.append(f"<description><![CDATA[{it['description']}]]></description>")
        out.append("</item>")

    out.append("</channel></rss>")
    return "\n".join(out)

def main():
    state = load_state()
    seen = set(state.get("seen", []))

    categories = read_feeds_by_category()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    total_items = 0

    for cat_slug, cat_data in categories.items():
        cat_name = cat_data["name"]
        feed_urls = cat_data["feeds"]
        collected = []

        print(f"Processing category: {cat_name} ({len(feed_urls)} feeds)")

        for fu in feed_urls:
            try:
                f = feedparser.parse(fu)
                for e in f.entries[:MAX_ITEMS_PER_FEED]:
                    link = getattr(e, "link", "")
                    guid = getattr(e, "id", link) or link
                    if not guid or guid in seen:
                        continue

                    title = getattr(e, "title", "(no title)")
                    summary = getattr(e, "summary", "") or getattr(e, "description", "")

                    # 日本語記事はそのまま、英語は要約
                    if is_japanese(title + " " + summary):
                        jp = summary
                    else:
                        print(f"  Summarizing: {title[:50]}...")
                        jp = summarize_to_japanese(title, summary)

                    pub = getattr(e, "published", "") or datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")

                    collected.append({
                        "title": f"[要約] {title}",
                        "link": link,
                        "guid": guid,
                        "pubDate": pub,
                        "description": f"<p><a href='{link}'>元記事を読む</a></p>{jp}"
                    })

                    seen.add(guid)
            except Exception as ex:
                print(f"  Error processing {fu}: {ex}")
                continue

        # カテゴリごとにRSSを出力
        collected = collected[::-1]
        out_path = OUT_DIR / f"feed_{cat_slug}.xml"
        out_path.write_text(build_rss(collected, cat_name), encoding="utf-8")
        print(f"  Generated: {out_path} ({len(collected)} items)")
        total_items += len(collected)

    # 全カテゴリ統合版も出力
    # (既存のfeed.xmlとの互換性のため)

    state["seen"] = list(seen)
    save_state(state)
    print(f"\nTotal: {total_items} items processed")

if __name__ == "__main__":
    main()
