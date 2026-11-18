"""HTML 解析层：只做「文本 → 结构」，不发请求、不写文件。"""
from __future__ import annotations

import html as html_lib
import json
import re

TAG = re.compile(r"<[^>]+>")
CARD_RE = re.compile(r'<li class="res-book-item[\s\S]*?</li>')
NOISE = re.compile(r"^(限免|免费试读|最新章节|已更新至|立即阅读)")


# ---------------- 通用 ----------------
def clean(text: str) -> str:
    """去标签 + 反转义 + 归一空白"""
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = TAG.sub("", text)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t\u3000\u00a0]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _pick(pattern: str, source: str, default: str = "") -> str:
    m = re.search(pattern, source, re.S)
    return clean(m.group(1)) if m else default


def _https(url: str) -> str:
    url = (url or "").strip()
    return "https:" + url if url.startswith("//") else url


# ---------------- 搜索 ----------------
def parse_search(html: str) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    for block in CARD_RE.findall(html):
        card = _parse_card(block)
        if card and card["bookId"] not in seen:
            seen.add(card["bookId"])
            items.append(card)
    if items:
        return items

    # 兜底：老页面结构
    for m in re.finditer(
        r'<a[^>]+href="(?:https?:)?//www\.qidian\.com/book/(\d+)/?"[^>]*>([\s\S]{0,80}?)</a>', html
    ):
        bid, name = m.group(1), clean(m.group(2)).splitlines()[0].strip()
        if name and bid not in seen:
            seen.add(bid)
            items.append({"bookId": bid, "name": name})
    return items


def _parse_card(block: str) -> dict | None:
    bid = re.search(r'data-bid="(\d+)"', block)
    if not bid:
        return None
    book_id = bid.group(1)

    cover = _https(re.search(r'data-original="([^"]+)"', block).group(1)) if 'data-original="' in block else ""

    latest, latest_url = "", ""
    m = re.search(r'<p class="update"><a[^>]*href="([^"]*)"[^>]*>([\s\S]*?)</a>', block, re.S)
    if m:
        latest_url = _https(m.group(1))
        latest = clean(m.group(2)).replace("最新更新", "").strip()

    title = _pick(r'<h3 class="book-info-title"><a[^>]*title="([^"]*)"', block) or _pick(
        r'<h3 class="book-info-title"><a[^>]*>([\s\S]*?)</a>', block
    )
    title = re.sub(r"在线阅读$", "", title).strip()

    return {
        "bookId": book_id,
        "name": title,
        "author": _pick(r'class="name"[^>]*title="([^"]*)"', block)
        or _pick(r'class="name"[^>]*>([\s\S]*?)</a>', block),
        "authorId": _pick(r"/author/(\d+)/", block),
        "cat": _pick(r'</em><a[^>]*href="[^"]*qidian\.com/[a-z]+/"[^>]*>([^<]*)</a>', block),
        "status": _pick(r"</em><span>([^<]*)</span>", block),
        "intro": _pick(r'<p class="intro[^"]*">([\s\S]*?)</p>', block)[:220],
        "latest": latest,
        "latestUrl": latest_url,
        "date": _pick(r"<span>(\d{4}-\d{2}-\d{2})</span>", block),
        "words": _pick(r"<span>\s*([\d.]+万?)\s*</span>总字数", block),
        "recommend": _pick(r"<span>\s*([\d.]+万?)\s*</span>总推荐", block),
        "cover": cover,
        "url": "https://www.qidian.com/book/%s/" % book_id,
    }


# ---------------- 作品页 ----------------
def parse_book_head(html: str) -> dict:
    title = _pick(r"<h1[^>]*>([\s\S]*?)</h1>", html)
    if not title:
        title = _pick(r"<title>([\s\S]*?)</title>", html).split("(")[0].split("_")[0]
    return {
        "title": title,
        "author": _pick(r'<a[^>]+class="[^"]*writer[^"]*"[^>]*>([\s\S]*?)</a>', html),
        "intro": _pick(r'<p[^>]+class="[^"]*intro[^"]*"[^>]*>([\s\S]*?)</p>', html)[:400],
        "cover": _https(_pick(r'og:image"\s*content="([^"]+)"', html)),
        "cat": _pick(r'og:novel:category"\s*content="([^"]*)"', html),
        "words": _pick(r'og:novel:word_count"\s*content="([^"]*)"', html),
    }


# ---------------- 移动端 SSR JSON（www 被 WAF 挡时的通道） ----------------
def _page_data(html: str) -> dict | None:
    marker = '{"pageContext"'
    start = html.find(marker)
    if start < 0:
        return None
    end = html.find("</script>", start)
    try:
        return json.loads(html[start:end])["pageContext"]["pageProps"]["pageData"]
    except Exception:  # noqa: BLE001
        return None


def parse_mobile_search(html: str) -> list[dict]:
    """m.qidian.com/soushu/{kw}.html：书名/作者等在 bookInfo.records。"""
    page = _page_data(html)
    if not page:
        return []
    records = (page.get("bookInfo") or {}).get("records") or []
    items = []
    for r in records:
        bid = str(r.get("bid") or r.get("cid") or "")
        if not bid:
            continue
        items.append({
            "bookId": bid,
            "name": r.get("bName") or "",
            "author": r.get("bAuth") or "",
            "authorId": str(r.get("authorId") or ""),
            "cat": r.get("cat") or "",
            "status": r.get("state") or "",
            "intro": (r.get("desc") or "")[:220],
            "latest": r.get("lastChapterName") or "",
            "latestUrl": "",
            "date": r.get("updateTime") or "",
            "words": r.get("cnt") or "",
            "recommend": str(r.get("recomendCnt") or ""),
            "cover": _https(r.get("imgUrl") or ""),
            "url": "https://www.qidian.com/book/%s/" % bid,
        })
    return items


def parse_mobile_catalog(html: str) -> dict | None:
    """m.qidian.com/book/{id}/catalog/：vs[].cs[] 与官方 ajax 同构。"""
    page = _page_data(html)
    if not page or "vs" not in page:
        return None
    return page


# ---------------- 正文（SSR JSON，含订阅状态） ----------------
def parse_chapter_json(html: str) -> dict | None:
    """起点新版阅读页把章节数据放在 vite-plugin-ssr 的 JSON 里，字段比 DOM 全。"""
    marker = '{"pageContext"'
    start = html.find(marker)
    if start < 0:
        return None
    end = html.find("</script>", start)
    try:
        data = json.loads(html[start:end])
        page = data["pageContext"]["pageProps"]["pageData"]
        info = page["chapterInfo"]
    except Exception:  # noqa: BLE001
        return None

    raw = info.get("content") or ""
    paras = [clean(p) for p in re.findall(r"<p[^>]*>([\s\S]*?)</p>", raw)]
    body = "\n".join([p for p in paras if p]) or clean(raw)
    book = (page.get("bookInfo") or {})
    return {
        "title": info.get("chapterName") or "",
        "body": body,
        "chars": len(body),
        "words": info.get("wordsCount") or 0,
        "is_vip": str(info.get("vipStatus")) == "1",
        "is_buy": str(info.get("isBuy")) == "1",
        "price": info.get("price") or 0,
        "limit_free": str(info.get("limitFree")) == "1",
        "teaser": bool(body) and (info.get("wordsCount") or 0) > len(body) * 1.5,
        "book_name": book.get("bookName") or "",
        "ord": int(info.get("seq") or 0),
    }


# ---------------- 正文（DOM 兜底） ----------------
def parse_chapter(html: str) -> dict:
    body_html = ""
    m = re.search(r'<main[^>]*id=["\']c-\d+["\'][^>]*>([\s\S]*?)</main>', html) or re.search(
        r'<div[^>]+id="chapterContent"[^>]*>([\s\S]*?)</div>', html
    )
    if m:
        body_html = m.group(1)

    paras = [clean(p) for p in re.findall(r"<p[^>]*>([\s\S]*?)</p>", body_html)]
    paras = [p for p in paras if p]
    body = "\n".join(paras) if len(paras) >= 2 else clean(body_html)
    title = _pick(r"<h1[^>]*>([\s\S]*?)</h1>", html)
    return {"title": title, "body": body, "chars": len(body)}
