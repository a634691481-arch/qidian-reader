"""目录缓存：起点被 WAF 挡住时，仍能靠缓存去外部书源找正文。"""
from __future__ import annotations

import json

import config

_BOOK_CACHE = config.CACHE / "books"

_BOOK_CACHE = config.CACHE / "books"


def save_book(info: dict) -> None:
    """把书名与目录存下来：起点被 WAF 挡死时，仍能靠它去外部源找正文。"""
    if not info.get("ok") or not info.get("chapters"):
        return
    try:
        _BOOK_CACHE.mkdir(parents=True, exist_ok=True)
        (_BOOK_CACHE / ("%s.json" % info["bookId"])).write_text(
            json.dumps(
                {
                    "title": info.get("title") or "",
                    "chapters": [
                        {"chapterId": c.get("chapterId"), "name": c.get("name"), "ord": c.get("ord")}
                        for c in info["chapters"]
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception:  # noqa: BLE001
        pass


def get_book(book_id: str, chapter_id: str = "") -> dict:
    p = _BOOK_CACHE / ("%s.json" % book_id)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    out = {"title": data.get("title") or ""}
    if chapter_id:
        for c in data.get("chapters") or []:
            if str(c.get("chapterId")) == str(chapter_id):
                out["chapterName"] = c.get("name") or ""
                out["ord"] = c.get("ord") or 0
                break
    return out
