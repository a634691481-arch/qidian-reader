"""规则型外部书源：用选择器配置去适配任意小说站。

一个源就是一段 JSON（见 sources.json）：

    {
      "name": "站点名",
      "enabled": true,
      "searchUrl": "https://host/search.php?q={kw}",
      "itemSelector": ".result-list .item a",     # 搜索结果里指向书页的链接
      "itemTitleAttr": "title",                  # 书名取哪个属性，留空取文本
      "chapterSelector": "#list dd a",           # 目录页章节链接
      "contentSelector": "#content",             # 正文容器
      "removeSelectors": ["script", ".ads"],     # 正文里要剔掉的节点
      "referer": ""                              # 抓正文时的 Referer，可留空
    }

适配器只负责"配置 → 请求 → 文本"，不关心业务；匹配哪一章由 registry 决定。
"""
from __future__ import annotations

from urllib.parse import quote, urljoin

import time

from bs4 import BeautifulSoup

import parse
import source_fetch

import re

# 盗版站塞在正文里的推广行，按行剔除
AD_LINE = re.compile(
    r"天才一秒记住|本站地址|最新网址|最快更新|请记住本站|手机阅读|加入书签"
    r"|上一章|下一章|章节错误|求收藏|求月票|返回目录|全文阅读"
    r"|浏览器转码失败|报送后维护人员|请退出.{0,4}阅读模式"
    r"|首发域名|手机版阅读网址|一秒记住|记住本站|本书首发"
    r"|^https?://|^www\.|^\S+\.(com|net|la|cc|info|xyz)\b"
)

# 整页坏数据信号。注意：壁落这类站把"章节错误,点此报送"写在**每个**章节页的页脚，
# 属于全站模板而非坏章标志，因此这里只认真正指向内容缺失的措辞。
CORRUPT_MARK = re.compile(r"内容正在手打|请耐心等待校正|本章内容缺失|数据加载失败")


def _soup(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:  # noqa: BLE001
        return BeautifulSoup(html, "html.parser")


class RuleSource:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg or {}
        self.name = self.cfg.get("name") or "unnamed"
        self.proxy = self.cfg.get("proxy") or ""

    # ---------------- 对外 ----------------
    @property
    def enabled(self) -> bool:
        return bool(self.cfg.get("enabled"))

    def search(self, keyword: str) -> list[dict]:
        tpls = [x.strip() for x in (self.cfg.get("searchUrl") or "").split("|") if x.strip()]
        if not tpls or not keyword:
            return []
        quoted = quote(keyword)
        for tpl in tpls:  # 多域名互为备份，前一个挂了自动试下一个
            url = tpl.replace("{kw}", quoted).replace("{kw_gbk}",
                                                      quote(keyword, encoding="gb18030"))
            for attempt in range(2):
                status, html = source_fetch.get(url, proxy_url=self.proxy)
                if status == 200 and html:
                    found = self._parse_search(html, url)
                    if found:
                        return found
                if attempt == 0:
                    time.sleep(0.7)   # 部分站对连续请求返回 200 空结果
        return []

    def _parse_search(self, html: str, url: str) -> list[dict]:
        soup = _soup(html)
        sel = self.cfg.get("itemSelector") or "a"
        attr = self.cfg.get("itemTitleAttr") or ""
        out, seen = [], set()
        for a in soup.select(sel):
            href = a.get("href") or ""
            if not href:
                continue
            full = urljoin(url, href)
            if full in seen:
                continue
            seen.add(full)
            title = (a.get(attr) if attr else a.get_text(strip=True)) or ""
            out.append({"name": parse.clean(title), "url": full})
        return out

    def chapters(self, book_url: str) -> list[dict]:
        status, html = source_fetch.get(book_url, proxy_url=self.proxy)
        if status != 200 or not html:
            return []
        soup = _soup(html)
        sel = self.cfg.get("chapterSelector") or "a"
        out, seen = [], set()
        for a in soup.select(sel):
            href = a.get("href") or ""
            if not href:
                continue
            full = urljoin(book_url, href)
            if full in seen:
                continue
            name = parse.clean(a.get_text(strip=True))
            if not name:
                continue
            seen.add(full)
            out.append({"ord": len(out) + 1, "name": name, "url": full})
        return out

    def content(self, chapter_url: str) -> str:
        status, html = source_fetch.get(chapter_url,
                                        referer=self.cfg.get("referer") or "",
                                        proxy_url=self.proxy)
        if status != 200 or not html:
            return ""
        # 站方自己标了"章节错误/待校正"的页，正文是拿别的书拼凑的垃圾，直接判失败
        if CORRUPT_MARK.search(html):
            return ""
        soup = _soup(html)
        for sel in self.cfg.get("removeSelectors") or []:
            for node in soup.select(sel):
                node.decompose()

        node = None
        for sel in (self.cfg.get("contentSelector") or "").split("|"):
            sel = sel.strip()
            if not sel:
                continue
            node = soup.select_one(sel)
            if node is not None:
                break
        if node is None:
            return ""

        # 两种排版都要吃下：<p> 分段（多数站），以及纯文本 + <br> 分段（部分站）。
        # 后者不能用 p，否则只会捞到广告段。
        paras = [parse.clean(p.get_text()) for p in node.select("p")]
        paras = [p for p in paras if p]
        text = "\n".join(paras) if sum(len(p) for p in paras) >= 300 else parse.clean(str(node))

        lines = [ln.strip() for ln in text.split("\n")]
        lines = [ln for ln in lines if ln and not AD_LINE.search(ln)]
        return "\n".join(lines)
