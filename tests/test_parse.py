"""解析层快照测试：用 data/ 下抓好的真实页面做固件，不联网。

运行：python -m unittest discover -s tests -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

import parse  # noqa: E402


def fixture(name: str) -> str:
    return (ROOT / "data" / name).read_text(encoding="utf-8", errors="ignore")


class TestClean(unittest.TestCase):
    def test_strip_tags_and_unescape(self):
        self.assertEqual(parse.clean("<p>a&nbsp;b</p>"), "a b")

    def test_br_to_newline(self):
        self.assertIn("\n", parse.clean("x<br/>y"))

    def test_script_removed(self):
        self.assertEqual(parse.clean("<script>var a=1</script>正文"), "正文")


class TestSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = parse.parse_search(fixture("search-sample.html"))

    def test_not_empty(self):
        self.assertGreaterEqual(len(self.items), 5)

    def test_unique_ids(self):
        ids = [i["bookId"] for i in self.items]
        self.assertEqual(len(ids), len(set(ids)))

    def test_core_fields(self):
        first = self.items[0]
        for key in ("bookId", "name", "author", "cover", "url"):
            self.assertIn(key, first)
        self.assertTrue(first["bookId"].isdigit())
        self.assertTrue(first["cover"].startswith("https://"))

    def test_no_reading_suffix(self):
        for it in self.items:
            self.assertFalse(it["name"].endswith("在线阅读"), it["name"])


class TestBookHead(unittest.TestCase):
    def test_parse_vip_chapter_page_head(self):
        head = parse.parse_book_head(fixture("vip-chapter.html"))
        # 章节页也可能带 og 信息；只断言结构稳定
        self.assertIsInstance(head["title"], str)


class TestChapterJson(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = parse.parse_chapter_json(fixture("vip-chapter.html"))

    def test_parsed(self):
        self.assertIsNotNone(self.data)

    def test_vip_teaser(self):
        d = self.data
        self.assertTrue(d["is_vip"])
        self.assertFalse(d["is_buy"])
        self.assertTrue(d["teaser"], "VIP 未订阅章节应被标记为试读")
        self.assertLess(d["chars"], d["words"])


class TestChapterDomFallback(unittest.TestCase):
    def test_dom_parse_returns_string_body(self):
        html = "<main id='c-1'><p>第一段</p><p>第二段</p></main>"
        out = parse.parse_chapter(html)
        self.assertEqual(out["body"], "第一段\n第二段")
        self.assertEqual(out["chars"], len("第一段\n第二段"))


if __name__ == "__main__":
    unittest.main()
