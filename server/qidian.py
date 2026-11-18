"""业务层：搜索 / 目录 / 详情 / 正文 / 导出。只依赖 net + parse + config。"""
from __future__ import annotations

import json
import re
from urllib.parse import quote

import cache
import config
import net
import parse
import paywall
import source_registry

# www 被腾讯防水墙拦下时的特征（挑战页里必有 seqid，正常页有 pageContext）
_WAF_MARK = "seqid"
_PAGE_MARK = '{"pageContext"'
_DIGITS = re.compile(r"\d+")


def gid(value) -> str:
    """ID 钳制：只放行纯数字。ID 最终来自外部 HTML 解析，拼 URL 前必须消毒。"""
    s = str(value or "").strip()
    return s if _DIGITS.fullmatch(s) else ""


def _waf_blocked(status: int, html: str) -> bool:
    if status == 202 or len(html) < 4000:
        return True
    if _WAF_MARK in html and _PAGE_MARK not in html:
        return True
    return _PAGE_MARK not in html and len(html) < 20000


def _page(www_url: str, mobile_url: str, extra: dict | None = None):
    """先打 www；被 WAF 挑战就换移动端入口。

    返回 (status, html, via)。via 是 www|m，写进响应方便排查。
    实测 2026-10：www 频繁请求后整站弹滑块，移动端同时刻仍是干净的。
    """
    status, html = net.get(www_url, extra=extra)
    if not _waf_blocked(status, html):
        return status, html, "www"
    m_status, m_html = net.get(mobile_url, extra=extra, ua=config.MOBILE_UA)
    if m_status == 200 and not _waf_blocked(m_status, m_html):
        return m_status, m_html, "m"
    return status, html, "www"


# ---------------- 搜索 ----------------
def search(kw: str, page: int = 1) -> dict:
    kw = (kw or "").strip()
    if not kw:
        return {"ok": False, "error": "关键词为空", "items": []}

    www_url = config.SEARCH_URL.format(kw=quote(kw))
    if page > 1:
        www_url += "?page=%d" % page
    mobile_url = config.MOBILE_BASE + "/soushu/%s.html" % quote(kw)
    if page > 1:
        mobile_url += "?page=%d" % page

    status, html, via = _page(www_url, mobile_url)
    if status != 200:
        return {"ok": False, "status": status, "note": "WAF 拦截或 cookie 失效", "items": [], "via": via}

    items = parse.parse_mobile_search(html) if via == "m" else parse.parse_search(html)
    if not items:                      # 通道判错时两条解析都试一遍
        items = parse.parse_search(html) or parse.parse_mobile_search(html)
    return {
        "ok": True,
        "status": status,
        "via": via,
        "kw": kw,
        "page": page,
        "count": len(items),
        "hasMore": len(items) >= 10,
        "items": items,
    }


# ---------------- 目录（官方 JSON 接口，失败则走移动端目录页） ----------------
def catalog(book_id: str, primed_html: str = "") -> dict:
    """primed_html：调用方已抓到的书页 HTML，兜底解析先试它，命中就省一次请求。"""
    status, text = net.get(
        "%s?bookId=%s&_csrfToken=%s" % (config.CATALOG_URL, book_id, config.CSRF_PLACEHOLDER),
        extra={
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": config.BOOK_URL.format(book_id=book_id),
        },
        csrf=True,
    )
    data = None
    try:
        payload = json.loads(text)
        data = payload.get("data") if isinstance(payload, dict) else None
    except Exception:  # noqa: BLE001
        payload = {}

    via = "ajax"
    if not data:
        # www 的 ajax 被 WAF 挡：移动端目录页的 pageData 与它同构（vs[].cs[]）。
        # 先试调用方传入的页面（零成本），不行再真发请求。
        page = parse.parse_mobile_catalog(primed_html) if primed_html else None
        if page:
            data, via = page, "primed"
        else:
            m_status, m_html, m_via = _page(
                config.BOOK_URL.format(book_id=book_id),
                config.MOBILE_BASE + "/book/%s/catalog/" % book_id,
            )
            page = parse.parse_mobile_catalog(m_html) if m_status == 200 else None
            if page:
                data = page
                via = "m-catalog"

    if not data:
        return {"ok": False, "status": status, "note": (payload or {}).get("msg", "目录获取失败")}

    volumes, flat, order = [], [], 0
    for vol in data.get("vs") or []:
        chapters = []
        for ch in vol.get("cs") or []:
            order += 1
            item = {
                "chapterId": str(ch.get("id") or ""),
                "name": ch.get("cN") or "",
                "ord": order,
                "words": ch.get("cnt") or 0,
                "updated": ch.get("uT") or "",
                "free": str(ch.get("sS")) == "1",
            }
            chapters.append(item)
            flat.append(item)
        volumes.append({"name": vol.get("vN") or "", "count": len(chapters), "chapters": chapters})

    return {
        "ok": True,
        "status": status,
        "via": via,
        "bookStatus": data.get("actionStatus") or data.get("bookStatus") or "",
        "chapterCount": len(flat),
        "volumes": volumes,
        "chapters": flat,
    }


# ---------------- 详情 ----------------
def book_info(book_id: str) -> dict:
    book_id = gid(book_id)
    if not book_id:
        return {"ok": False, "note": "bookId invalid"}

    status, html, _via = _page(
        config.BOOK_URL.format(book_id=book_id),
        config.MOBILE_BOOK_URL.format(book_id=book_id),
    )
    if status != 200:
        return {"ok": False, "status": status, "note": "被拦截或书籍不存在"}

    head = parse.parse_book_head(html)
    cat = catalog(book_id, primed_html=html)
    if cat.get("ok"):
        out = {
            "ok": True,
            "status": status,
            "bookId": book_id,
            "title": head["title"] or "book-%s" % book_id,
            "author": head["author"],
            "intro": head["intro"],
            "cover": head["cover"],
            "cat": head["cat"],
            "words": head["words"],
            "source": "ajax/book/category",
            "bookStatus": cat.get("bookStatus"),
            "chapterCount": cat["chapterCount"],
            "volumes": cat["volumes"],
            "chapters": cat["chapters"],
        }
        cache.save_book(out)
        return out

    # 兜底：页面链接
    chapters, seen = [], set()
    for m in re.finditer(
        r'<a[^>]+href="(?:https?:)?//(?:www|m)\.qidian\.com/chapter/\d+/(\d+)/?"[^>]*>([\s\S]*?)</a>', html
    ):
        cid, name = m.group(1), parse.clean(m.group(2)).splitlines()[0].strip()[:60]
        if not name or parse.NOISE.match(name) or cid in seen:
            continue
        seen.add(cid)
        chapters.append({"chapterId": cid, "name": name, "ord": len(chapters) + 1})

    out = {
        "ok": True,
        "status": status,
        "bookId": book_id,
        "title": head["title"] or "book-%s" % book_id,
        "author": head["author"],
        "intro": head["intro"],
        "cover": head["cover"],
        "cat": head["cat"],
        "words": head["words"],
        "source": "html",
        "chapterCount": len(chapters),
        "chapters": chapters,
    }
    cache.save_book(out)
    return out


# ---------------- 正文 ----------------
def _fetch_detail(book_id: str, chapter_id: str) -> tuple[int, str, dict | None]:
    """抓章节页并解析 SSR JSON；解析失败回退 DOM。返回 (status, via, detail)。"""
    status, html, via = _page(
        config.CHAPTER_URL.format(book_id=book_id, chapter_id=chapter_id),
        config.MOBILE_CHAPTER_URL.format(book_id=book_id, chapter_id=chapter_id),
    )
    if status != 200:
        return status, via, None

    detail = parse.parse_chapter_json(html)
    if detail is None:
        legacy = parse.parse_chapter(html)
        detail = {
            "title": legacy["title"],
            "body": legacy["body"],
            "chars": legacy["chars"],
            "words": legacy["chars"],
            "is_vip": False,
            "is_buy": False,
            "price": 0,
            "limit_free": False,
            "teaser": False,
            "book_name": "",
            "ord": 0,
        }
    return status, via, detail


def _enrich_fallback(book_id: str, info: dict, detail: dict) -> None:
    """付费墙 / 正文残缺 -> 去外部源把整章补回来（原地更新 info）。"""
    check = paywall.verdict(detail)
    info["paid"] = check["paid"]
    info["ratio"] = check["ratio"]
    if not (check["paid"] or check["incomplete"]):
        return

    book_title = detail.get("book_name") or ""
    chapter_name = detail["title"]
    ord_ = detail.get("ord") or 0
    # 起点被 WAF 挡死时拿不到书名，用上次成功抓到的目录缓存兜底
    if not book_title or not chapter_name:
        cached = cache.get_book(book_id, chapter_id)
        book_title = book_title or cached.get("title") or ""
        chapter_name = chapter_name or cached.get("chapterName") or ""
        ord_ = ord_ or cached.get("ord") or 0

    got = source_registry.resolve(
        book_id=book_id,
        key=chapter_id,
        book_title=book_title,
        chapter_name=chapter_name,
        ord_=ord_,
        expect_words=detail["words"],
    )
    info["tried"] = got.get("tried") or []
    if got["ok"]:
        words = detail.get("words") or 0
        real_ratio = round(min(got["chars"] / float(words), 1.0), 3) if words else 1.0
        info.update({
            "ok": True,
            "body": got["text"],
            "chars": got["chars"],
            "source": got["source"],
            "fallback": True,
            "teaser": False,
            "ratio": real_ratio,
            # 外部源也可能只采到半章，别把残缺当完整
            "truncated": real_ratio < 0.9,
        })
    else:
        info["fallback"] = False
        if check["paid"]:
            info["note"] = "VIP 章未购买，起点只给试读，外部源也没命中"


def chapter(book_id: str, chapter_id: str) -> dict:
    book_id, chapter_id = gid(book_id), gid(chapter_id)
    if not book_id or not chapter_id:
        return {"ok": False, "chars": 0, "note": "ids invalid"}

    status, via, detail = _fetch_detail(book_id, chapter_id)
    if detail is None:
        return {"ok": False, "status": status, "chars": 0, "note": "被拦截/需订阅", "via": via}

    info = {
        "ok": bool(detail["body"]),
        "status": status,
        "title": detail["title"],
        "chars": detail["chars"],
        "body": detail["body"],
        "words": detail["words"],
        "isVip": detail["is_vip"],
        "isBuy": detail["is_buy"],
        "price": detail["price"],
        "limitFree": detail["limit_free"],
        "teaser": detail["teaser"],
        "source": "qidian",
        "via": via,
    }
    _enrich_fallback(book_id, info, detail)
    return info
