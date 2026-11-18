"""客户端内核 · stdin/stdout JSON 行协议（生产通道，无端口）。

请求：{"id":1,"cmd":"search","params":{"kw":"荒野狩猎","page":1}}
响应：{"id":1,"ok":true,...}

由 Tauri 侧 spawn 一次常驻进程，前端 invoke('qidian', {...}) 经 Rust 转发到这里。
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as config_mod  # noqa: E402
import login  # noqa: E402
import net  # noqa: E402
import export as exporter  # noqa: E402
import qidian  # noqa: E402
import slider  # noqa: E402
import store  # noqa: E402
import tsfp as token_mod  # noqa: E402


# ---------------- 命令实现 ----------------
def _int(params: dict, key: str, default: int, lo: int, hi: int) -> int:
    """参数钳制：非数字回落默认值，超界截断，杜绝畸形参数打进业务层。"""
    try:
        v = int(params.get(key) or default)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def _token(params: dict) -> dict:
    value = token_mod.MINTER.get(force=bool(params.get("force")))
    return {"ok": True, "token": value[:24] + "…", **token_mod.state()}


def _search(params: dict) -> dict:
    return qidian.search(str(params.get("kw") or ""), _int(params, "page", 1, 1, 100))


def _book(params: dict) -> dict:
    return qidian.book_info(str(params.get("bookId") or ""))


def _chapter(params: dict) -> dict:
    return qidian.chapter(str(params.get("bookId") or ""), str(params.get("chapterId") or ""))


def _export_plan(params: dict) -> dict:
    return exporter.plan(str(params.get("bookId") or ""), _int(params, "max", 0, 0, 500) or None)


def _export_chunk(params: dict) -> dict:
    # items 必须是 [{chapterId: 数字串, name: str}]，坏的直接剔除
    items = [
        it for it in (params.get("items") or [])
        if isinstance(it, dict) and qidian.gid(it.get("chapterId"))
    ]
    return exporter.chunk(str(params.get("bookId") or ""), items)


def _sources(_: dict) -> dict:
    import source_fetch
    import source_registry

    return {
        "ok": True,
        "backend": source_fetch.backend(),
        "enabled": source_registry.enabled_names(),
        "rulesFile": str(config_mod.SOURCES_FILE),
        "cacheDir": str(config_mod.CACHE),
    }


def _slider(params: dict) -> dict:
    return slider.solve_urls(str(params.get("bg") or ""), str(params.get("slice") or ""))


def _login_qr(_: dict) -> dict:
    return login.start()


def _login_poll(params: dict) -> dict:
    return login.poll(str(params.get("sid") or ""))


def _login_state(_: dict) -> dict:
    return {"ok": True, **store.login_state(), "token": token_mod.MINTER.state()}


def _logout(_: dict) -> dict:
    store.write("")
    token_mod.MINTER.invalidate()
    return {"ok": True, **token_mod.state()}


def _health(_: dict) -> dict:
    return {
        "ok": True,
        "token": token_mod.state(),
        "login": store.login_state(),
        "last": net.last_request(),
    }


COMMANDS = {
    "ping": lambda _: {"ok": True, "pong": True},
    "health": _health,
    "token": _token,
    "search": _search,
    "book": _book,
    "chapter": _chapter,
    "export_plan": _export_plan,
    "export_chunk": _export_chunk,
    "sources": _sources,
    "slider": _slider,
    "login_qr": _login_qr,
    "login_poll": _login_poll,
    "login_state": _login_state,
    "logout": _logout,
}


def dispatch(req: dict) -> dict:
    cmd = str(req.get("cmd") or "").strip()
    handler = COMMANDS.get(cmd)
    if not handler:
        return {"ok": False, "error": "unknown cmd: %s" % cmd}
    result = handler(req.get("params") or {})
    result.setdefault("ok", True)
    return result


def main() -> None:
    # Windows 管道默认 GBK，强制 UTF-8，否则 Rust 侧按 UTF-8 读会报错
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", newline="\n")
    except Exception:  # noqa: BLE001
        pass

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            res = dispatch(req)
        except Exception as exc:  # noqa: BLE001
            res = {"ok": False, "error": str(exc)[:300], "trace": traceback.format_exc()[-600:]}
        res["id"] = rid
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
