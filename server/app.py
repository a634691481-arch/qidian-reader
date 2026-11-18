"""HTTP 入口（浏览器调试用）。

生产环境不启动本文件：Tauri 直接 spawn server/core.py，通过 stdin/stdout 通信。
用法：python server/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_http import serve  # noqa: E402

if __name__ == "__main__":
    serve()
