"""导出 TXT：先取目录，再分片抓正文（前端按片显示进度）。"""
from __future__ import annotations

import time

import config
import qidian

def plan(book_id: str, max_chapters: int | None = None) -> dict:
    """只取目录，供前端分批拉正文"""
    limit = max_chapters or config.MAX_EXPORT_CHAPTERS
    info = qidian.book_info(book_id)
    if not info.get("ok"):
        return {"ok": False, "error": info.get("note") or "取书失败"}

    chapters = [
        {"chapterId": c["chapterId"], "name": c["name"]} for c in info["chapters"][:limit]
    ]
    return {
        "ok": True,
        "bookId": book_id,
        "title": info["title"],
        "author": info["author"],
        "total": len(chapters),
        "chapters": chapters,
    }


def chunk(book_id: str, items: list[dict]) -> dict:
    """抓一小批章节正文，返回拼接文本"""
    parts, ok_count = [], 0
    for item in items:
        ch = qidian.chapter(book_id, str(item.get("chapterId")))
        parts.append("\n\n%s\n\n%s" % (item.get("name") or "", ch.get("body") or "[空/付费]"))
        if ch.get("body"):
            ok_count += 1
        time.sleep(config.REQUEST_DELAY)
    return {"ok": True, "text": "".join(parts), "okChapters": ok_count}
