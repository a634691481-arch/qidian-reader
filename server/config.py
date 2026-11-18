"""全局配置与常量。所有可调项集中在此，避免散落在业务代码里。"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------- 路径 ----------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)
COOKIE_FILE = DATA / "cookie.txt"
PROBE_FILE = Path(__file__).resolve().parent / "probev3.js"
SOURCES_FILE = DATA / "sources.json"      # 外部书源规则（付费墙回落）
CACHE = DATA / "cache"                    # 命中正文的本地缓存

# ---------------- 网络 ----------------
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
)
BASE = "https://www.qidian.com"
SEARCH_URL = BASE + "/soushu/{kw}.html"
CATALOG_URL = BASE + "/ajax/book/category"
BOOK_URL = BASE + "/book/{book_id}/"
CHAPTER_URL = BASE + "/chapter/{book_id}/{chapter_id}/"

# 移动端入口：www 被 WAF 弹滑块时它仍然是干净的（实测 2026-10）
MOBILE_BASE = "https://m.qidian.com"
MOBILE_BOOK_URL = MOBILE_BASE + "/book/{book_id}/"
MOBILE_CHAPTER_URL = MOBILE_BASE + "/chapter/{book_id}/{chapter_id}/"
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
LOGIN_REDIRECT = "https://passport.qidian.com/login/redirect"
LOGIN_RETURN = "https://www.qidian.com/loginSuccess?surl=https%3A%2F%2Fwww.qidian.com%2F"

TIMEOUT = int(os.environ.get("QD_TIMEOUT", 20))
REQUEST_DELAY = float(os.environ.get("QD_DELAY", 0.35))   # 抓多章时的节流
MAX_EXPORT_CHAPTERS = int(os.environ.get("QD_MAX_EXPORT", 80))

# ---------------- 令牌 ----------------
TOKEN_TTL = int(os.environ.get("TOKEN_TTL", 480))         # 秒
CSRF_PLACEHOLDER = "x"

# ---------------- 服务 ----------------
API_PORT = int(os.environ.get("PORT", 8788))
