"""外部源的 HTTP 抓取后端。

首选 curl_cffi（TLS 指纹伪装成 Chrome，能过一部分 CDN 的 bot 检测），
没装则退回 requests。代理按此优先级取：调用方 -> 环境变量 SOURCE_PROXY -> 环境变量 HTTPS_PROXY。
UA/编码统一在这里处理，源适配器不必关心。
"""
from __future__ import annotations

import os
import time

import config

try:  # 可选依赖
    from curl_cffi import requests as _curl
except Exception:  # noqa: BLE001
    _curl = None

import requests as _requests

_HEADERS = {
    "User-Agent": config.UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def backend() -> str:
    return "curl_cffi" if _curl else "requests"


def proxy() -> str:
    return (os.environ.get("SOURCE_PROXY")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("https_proxy")
            or "")


def get(url: str, referer: str = "", timeout: int = 20, proxy_url: str = "",
        retries: int = 2) -> tuple[int, str]:
    """返回 (status, text)；异常一律折成 (0, "")，让上层做源切换。

    盗版站常对连续请求限流（一秒内二次访问直接给空目录），所以失败会短暂间隔重试。
    """
    headers = dict(_HEADERS)
    if referer:
        headers["Referer"] = referer
    px = proxy_url or proxy()

    for attempt in range(max(1, retries)):
        try:
            kw = {"proxies": {"http": px, "https": px}} if px else {}
            if _curl:
                r = _curl.get(url, headers=headers, timeout=timeout,
                              impersonate="chrome", allow_redirects=True, **kw)
            else:
                r = _requests.get(url, headers=headers, timeout=timeout,
                                  allow_redirects=True, **kw)
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
            continue

        if r.status_code != 200:
            if r.status_code in (403, 429, 503) and attempt + 1 < retries:
                time.sleep(0.8)
                continue
            return r.status_code, ""
        try:
            return 200, r.content.decode("utf-8")
        except UnicodeDecodeError:
            return 200, r.content.decode("gb18030", "replace")
    return 0, ""
