"""HTTP 适配层：仅供浏览器里调试 UI 使用（生产走 core.py 的 stdio）。

命令实现不再重复写：统一委托 core.COMMANDS（与 IPC 生产通道同一套），
本文件只做「HTTP 路由 -> cmd/params」翻译 + 图片代理。
启动：python server/app.py  ->  http://127.0.0.1:8788（仅绑回环地址）
"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import config
import core
import net


def _json(handler: BaseHTTPRequestHandler, code: int, obj) -> None:
    body = json.dumps(obj, ensure_ascii=False).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _image(handler: BaseHTTPRequestHandler, url: str) -> None:
    if not re.match(r"^https?://", url or ""):
        return _json(handler, 400, {"ok": False, "error": "bad url"})
    try:
        data, ctype = net.fetch_bytes(url)
    except Exception as exc:  # noqa: BLE001
        return _json(handler, 502, {"ok": False, "error": str(exc)[:120]})
    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Cache-Control", "public, max-age=86400")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _run(cmd: str, params: dict):
    """HTTP -> 内核命令表。异常在这里收口，不让 traceback 冒给浏览器。"""
    try:
        return core.dispatch({"cmd": cmd, "params": params})
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # ---------------- 基础 ----------------
    def log_message(self, *args) -> None:  # 静音访问日志
        pass

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ---------------- GET ----------------
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        try:
            if parsed.path == "/api/img":
                return _image(self, q.get("u", ""))
            cmd = GET_ROUTES.get(parsed.path)
            if cmd:
                return _json(self, 200, _run(cmd, q))
            _json(self, 404, {"ok": False, "error": "not found"})
        except Exception as exc:  # noqa: BLE001
            _json(self, 500, {"ok": False, "error": str(exc)[:200]})

    # ---------------- POST ----------------
    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            body = {}
        try:
            cmd = POST_ROUTES.get(parsed.path)
            if cmd:
                return _json(self, 200, _run(cmd, body if isinstance(body, dict) else {}))
            _json(self, 404, {"ok": False, "error": "not found"})
        except Exception as exc:  # noqa: BLE001
            _json(self, 500, {"ok": False, "error": str(exc)[:200]})


# ---------------- 路由 -> 命令映射（实现统一在 core.COMMANDS） ----------------
GET_ROUTES = {
    "/api/health": "health",
    "/api/token": "token",
    "/api/search": "search",
    "/api/book": "book",
    "/api/chapter": "chapter",
    "/api/slider": "slider",
    "/api/login/poll": "login_poll",
    "/api/login/state": "login_state",
    "/api/export/plan": "export_plan",
    "/api/sources": "sources",
}

POST_ROUTES = {
    "/api/login/qr": "login_qr",
    "/api/logout": "logout",
    "/api/export/chunk": "export_chunk",
}


def serve(port: int | None = None) -> None:
    port = port or config.API_PORT
    print(f"[api] http://127.0.0.1:{port}  （仅调试用；桌面端走 IPC）")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
