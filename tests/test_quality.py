"""质量回归：ID 消毒、参数钳制、原子写、dispatch 收口。全部离线不联网。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

import config  # noqa: E402
import core  # noqa: E402
import qidian  # noqa: E402
import store  # noqa: E402


class TestGid(unittest.TestCase):
    """ID 消毒：只放行纯数字，防 URL/命令注入。"""

    def test_valid_ids(self):
        self.assertEqual(qidian.gid("1048541850"), "1048541850")
        self.assertEqual(qidian.gid(" 894700866 "), "894700866")

    def test_rejects_injection(self):
        for bad in ("", None, "1/../../etc", "894700866'", "1;drop", "0x123", "-1", "1 2"):
            self.assertEqual(qidian.gid(bad), "", repr(bad))

    def test_chapter_rejects_bad_ids(self):
        out = qidian.chapter("1/..", "x")
        self.assertFalse(out["ok"])
        self.assertIn("invalid", out["note"])


class TestClamp(unittest.TestCase):
    """core._int 参数钳制。"""

    def test_normal(self):
        self.assertEqual(core._int({}, "page", 1, 1, 100), 1)
        self.assertEqual(core._int({"page": "3"}, "page", 1, 1, 100), 3)

    def test_fallback_on_garbage(self):
        self.assertEqual(core._int({"page": "abc"}, "page", 1, 1, 100), 1)
        self.assertEqual(core._int({"page": None}, "page", 1, 1, 100), 1)
        self.assertEqual(core._int({"page": []}, "page", 1, 1, 100), 1)

    def test_clamped(self):
        self.assertEqual(core._int({"max": 99999}, "max", 0, 0, 500), 500)
        self.assertEqual(core._int({"page": -5}, "page", 1, 1, 100), 1)


class TestDispatch(unittest.TestCase):
    """dispatch 收口：未知命令与坏参数都返回 ok=False 而非抛异常。"""

    def test_unknown_cmd(self):
        self.assertFalse(core.dispatch({"cmd": "nope"})["ok"])

    def test_search_rejects_empty_kw(self):
        out = core.dispatch({"cmd": "search", "params": {"kw": ""}})
        self.assertFalse(out["ok"])

    def test_export_chunk_filters_bad_items(self):
        # 打桩：不联网，只验证坏 items 在入口就被剔除
        import unittest.mock as mock

        seen = []

        def fake_chunk(book_id, items):
            seen.extend(items)
            return {"ok": True, "text": "", "okChapters": 0}

        with mock.patch.object(core.exporter, "chunk", fake_chunk):
            out = core.dispatch({
                "cmd": "export_chunk",
                "params": {
                    "bookId": "1",
                    "items": [
                        {"chapterId": "999", "name": "ok"},
                        "not-a-dict",
                        {"chapterId": "1/.."},   # 注入 ID 被剔
                        {"no-chapter": 1},
                    ],
                },
            })
        self.assertTrue(out["ok"])
        # 只有合法 item 传到业务层
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["chapterId"], "999")


class TestAtomicWrite(unittest.TestCase):
    """store.write 原子性：不留 .tmp，读回一致。"""

    def test_roundtrip(self):
        old = store.read()
        try:
            store.write("a=1; b=2")
            self.assertEqual(store.read(), "a=1; b=2")
            self.assertFalse(config.COOKIE_FILE.with_suffix(".tmp").exists())
        finally:
            store.write(old)


if __name__ == "__main__":
    unittest.main()
