"""书源自检：逐个跑 search -> 目录 -> 首章，报告可用性与耗时。

用法：
    python scripts/check-sources.py                    # 用默认探针书
    python scripts/check-sources.py 荒野狩猎 从综艺开始起号
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

import config  # noqa: E402
import source_rule  # noqa: E402


def main() -> int:
    kwargs = sys.argv[1:]
    keyword = kwargs[0] if kwargs else "荒野狩猎，从综艺开始起号"

    rules = json.loads(config.SOURCES_FILE.read_text(encoding="utf-8")).get("sources") or []
    if not rules:
        print("data/sources.json 里没有源")
        return 1

    print("探针书名：%s\n" % keyword)
    for cfg in rules:
        name = cfg.get("name") or "unnamed"
        if not cfg.get("enabled"):
            print("%-14s 跳过（未启用）" % name)
            continue

        src = source_rule.RuleSource(cfg)
        t0 = time.time()
        try:
            books = src.search(keyword)
        except Exception as exc:  # noqa: BLE001
            print("%-14s 搜索异常：%s" % (name, str(exc)[:70]))
            continue
        if not books:
            print("%-14s 搜索无结果（%dms）" % (name, int((time.time() - t0) * 1000)))
            continue

        hit = next((b for b in books if keyword[:4] in b["name"]), books[0])
        chapters = src.chapters(hit["url"])
        if not chapters:
            print("%-14s 目录为空：%s" % (name, hit["url"][:60]))
            continue

        text = src.content(chapters[0]["url"])
        cost = int((time.time() - t0) * 1000)
        verdict = "✅ 可用" if len(text) >= 300 else "⚠️ 正文过短"
        print("%-14s %s  书名=%s  目录=%d章  首章=%d字  %dms"
              % (name, verdict, hit["name"][:18], len(chapters), len(text), cost))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
