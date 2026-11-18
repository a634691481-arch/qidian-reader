"""Cookie 存储：读 / 写 / 派生 seed。"""
from __future__ import annotations

import os
import re

from config import COOKIE_FILE


def read() -> str:
    try:
        return COOKIE_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def write(value: str) -> None:
    """原子写：先写临时文件再 os.replace，写一半崩溃不会丢登录态。"""
    tmp = COOKIE_FILE.with_suffix(".tmp")
    tmp.write_text(value.strip(), encoding="utf-8")
    os.replace(tmp, COOKIE_FILE)


def seed() -> str:
    """去掉 w_tsfp 的底座 cookie（铸造与请求都用它）"""
    return re.sub(r"\s*w_tsfp=[^;]*;?", "", read()).strip().strip(";").strip()


def get(name: str) -> str:
    m = re.search(r"(?:^|;\s*)%s=([^;]*)" % re.escape(name), read())
    return m.group(1) if m else ""


def login_state() -> dict:
    openid = get("ywopenid")
    return {
        "loggedIn": bool(openid),
        "ywopenid": (openid[:6] + "…") if openid else None,
        "hasAlk": bool(get("alk")),
    }
