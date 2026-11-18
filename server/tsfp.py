"""w_tsfp 令牌管理：纯 Python（V8 跑 probev3.js）铸造 + TTL 缓存。"""
from __future__ import annotations

import threading
import time

import config
import store


class Minter:
    """线程安全的令牌缓存；到期或强制时重新铸造。"""

    def __init__(self, ttl: int | None = None) -> None:
        self.ttl = ttl or config.TOKEN_TTL
        self._token = ""
        self._born = 0.0
        self._lock = threading.Lock()
        self.calls = 0
        self.last_ms = 0

    # ---------------- 内部 ----------------
    def _mint(self) -> str:
        import mint  # 延迟导入：V8 初始化较重

        t0 = time.time()
        token = mint.mint_token(store.seed())
        self.calls += 1
        self.last_ms = int((time.time() - t0) * 1000)
        if not token:
            raise RuntimeError("token 铸造失败（probev3 未产出）")
        return token

    # ---------------- 对外 ----------------
    def get(self, force: bool = False) -> str:
        with self._lock:
            fresh = self._token and (time.time() - self._born) < self.ttl
            if fresh and not force:
                return self._token
            self._token = self._mint()
            self._born = time.time()
            return self._token

    def invalidate(self) -> None:
        with self._lock:
            self._token = ""
            self._born = 0.0

    def state(self) -> dict:
        ok = bool(self._token)
        return {
            "ok": ok,
            "len": len(self._token),
            "age": int(time.time() - self._born) if ok else None,
            "ttl": self.ttl,
            "calls": self.calls,
            "ms": self.last_ms,
        }


MINTER = Minter()


def state() -> dict:
    return {
        "hasCookie": bool(store.read()),
        "engine": "v8-py",
        **MINTER.state(),
    }
