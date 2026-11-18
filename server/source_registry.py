"""外部书源注册表：按 书名 + 章节 到各源里找可读正文。

调用时机由 qidian.chapter() 决定：起点被判付费墙或正文残缺时才会走到这里。
命中结果落盘缓存，同一章不会重复抓。
"""
from __future__ import annotations

import json
import re

import config
from source_rule import RuleSource

_NOISE = re.compile(
    r"第[0-9零一二三四五六七八九十百千]+[章节回卷]"
    r"|[\s]*[(\（\[【][^()\（\）\[\]【】]*[)\）\]】]"
)


def _norm(name: str) -> str:
    s = _NOISE.sub("", name or "").strip()
    return re.sub(r"[\s\W_]+", "", s)


def _similar(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    return len(short) >= 4 and short in long


def _book_match(wanted: str, got: str) -> bool:
    a, b = re.sub(r"[\s\W_]+", "", wanted or ""), re.sub(r"[\s\W_]+", "", got or "")
    if not a or not b:
        return False
    return a == b or (len(a) >= 4 and (a in b or b in a))


def load() -> list[RuleSource]:
    path = config.SOURCES_FILE
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    return [RuleSource(c) for c in (raw.get("sources") or []) if isinstance(c, dict)]


def enabled_names() -> list[str]:
    return [s.name for s in load() if s.enabled]


# ---------------- 缓存 ----------------
def _cache_path(book_id: str, key: str):
    d = config.CACHE / str(book_id or "_")
    d.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^0-9A-Za-z_-]", "_", str(key or "0"))[:60]
    return d / (safe + ".json")


def cache_read(book_id: str, key: str) -> str:
    p = _cache_path(book_id, key)
    if not p.exists():
        return ""
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("text") or ""
    except Exception:  # noqa: BLE001
        return ""


def cache_write(book_id: str, key: str, text: str, source: str, url: str) -> None:
    try:
        _cache_path(book_id, key).write_text(
            json.dumps({"source": source, "url": url, "chars": len(text), "text": text},
                       ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:  # noqa: BLE001
        pass


# ---------------- 主流程 ----------------
def resolve(book_id: str, key: str, book_title: str, chapter_name: str,
            ord_: int = 0, expect_words: int = 0, floor: float = 0.3) -> dict:
    """到所有启用源里找这一章的完整正文。

    返回 {"ok", "text", "chars", "source", "url", "cached", "tried"}。
    质量闸：正文至少 300 字，且不低于全章字数的 floor 比例（有 wordsCount 时）。
    floor 取 0.3 而不是 0.5：盗版站普遍只采到三到五成，宁可给出半章并让上层标
    truncated，也好过整章没有。
    """
    cached = cache_read(book_id, key)
    if cached:
        return {"ok": True, "text": cached, "chars": len(cached), "source": "cache",
                "url": "", "cached": True, "tried": []}

    need = max(300, int((expect_words or 0) * floor))
    tried = []

    for src in load():
        if not src.enabled:
            continue
        try:
            books = src.search(book_title)
        except Exception as exc:  # noqa: BLE001
            tried.append({"source": src.name, "stage": "search", "err": str(exc)[:80]})
            continue

        hit = next((b for b in books if _book_match(book_title, b["name"])), None)
        if not hit:
            tried.append({"source": src.name, "stage": "search", "err": "未命中书籍"})
            continue

        chapters = src.chapters(hit["url"])
        if not chapters:
            tried.append({"source": src.name, "stage": "catalog", "err": "目录为空"})
            continue

        target = next((c for c in chapters if _similar(chapter_name, c["name"])), None)
        if target is None and 0 < ord_ <= len(chapters):
            guess = chapters[ord_ - 1]
            if _similar(chapter_name, guess["name"]):
                target = guess
        if target is None:
            tried.append({"source": src.name, "stage": "catalog", "err": "未命中章节"})
            continue

        text = src.content(target["url"])
        if len(text) < need:
            tried.append({"source": src.name, "stage": "content",
                          "err": "正文过短 %d<%d" % (len(text), need)})
            continue

        # 只缓存接近全章的正文：残缺章节下次可能被别的源补全，不能锁死坏数据
        ratio = (len(text) / float(expect_words)) if expect_words else 1.0
        if ratio >= 0.9:
            cache_write(book_id, key, text, src.name, target["url"])
        return {"ok": True, "text": text, "chars": len(text), "source": src.name,
                "url": target["url"], "cached": False, "tried": tried,
                "complete": ratio >= 0.9}

    return {"ok": False, "text": "", "chars": 0, "source": "", "url": "",
            "cached": False, "tried": tried}
