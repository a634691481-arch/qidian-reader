"""HTTP 访问层：统一注入 w_tsfp / cookie / UA，自动重试与解码。

性能：模块级 Session 复用 TCP+TLS 连接（导出 80 章不再每次重新握手）。
健壮性：仅风控类响应（202/403/429/网络错误）才重铸令牌重试，避免白铸。
"""
from __future__ import annotations

import time

import requests

import config
import store
import tsfp as token_mod

# 复用连接池：与服务端的 keep-alive 握手只做一次
SESSION = requests.Session()
# 值得重铸令牌再试的状态码：WAF 挑战 / 明确拒绝 / 限频
_REMINT_STATUS = {202, 403, 429}

_LAST: dict = {}


def last_request() -> dict:
    return dict(_LAST)


def _headers(extra: dict | None, tok: str, csrf: bool, ua: str = "") -> dict:
    headers = {
        "User-Agent": ua or config.UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": config.BASE + "/",
    }
    if extra:
        headers.update(extra)
    parts = [x for x in (store.seed(), "w_tsfp=" + tok) if x and not x.endswith("=")]
    if csrf:
        parts.append("_csrfToken=" + config.CSRF_PLACEHOLDER)
    headers["Cookie"] = "; ".join(parts)
    return headers


def _decode(resp: requests.Response) -> str:
    try:
        return resp.content.decode("utf-8")
    except UnicodeDecodeError:
        return resp.content.decode("gbk", "replace")


def _should_remint(status: int) -> bool:
    """只有风控/拒绝类响应才值得花 8s 重铸令牌；4xx 其他码重铸也没用。"""
    return status == 0 or status in _REMINT_STATUS


def get(
    url: str,
    *,
    extra: dict | None = None,
    csrf: bool = False,
    retry: bool = True,
    ua: str = "",
) -> tuple[int, str]:
    """返回 (status, text)。风控类失败且 retry=True 时重铸令牌再试一次。"""
    status, text = 0, ""
    for attempt in (0, 1):
        force = attempt > 0 and _should_remint(status)
        try:
            tok = token_mod.MINTER.get(force=force)
        except Exception as exc:  # noqa: BLE001
            _LAST.update({"url": url, "status": 0, "err": "mint: " + str(exc)[:100]})
            return 0, ""

        try:
            resp = SESSION.get(
                url,
                headers=_headers(extra, tok, csrf, ua),
                timeout=config.TIMEOUT,
                allow_redirects=True,
            )
            status, text = resp.status_code, _decode(resp)
            _LAST.update(
                {
                    "url": url,
                    "status": status,
                    "len": len(text),
                    "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "try": attempt + 1,
                }
            )
        except Exception as exc:  # noqa: BLE001
            _LAST.update({"url": url, "status": 0, "err": str(exc)[:120]})
            status, text = 0, ""

        if status == 200 or not retry:
            break
        time.sleep(0.6)
    return status, text


def fetch_bytes(url: str) -> tuple[bytes, str]:
    """下载二进制（封面 / 滑块图），同样走连接池"""
    resp = SESSION.get(
        url,
        headers={"User-Agent": config.UA, "Referer": config.BASE + "/"},
        timeout=config.TIMEOUT,
    )
    return resp.content, resp.headers.get("Content-Type", "image/jpeg")
