# SPDX-License-Identifier: MIT
"""
omni-hub-oss.py — OmniHub OSS (Pure-Python, Lightweight)
Clean code: flake8 + black + isort compatible
"""

from __future__ import annotations

import argparse
import http.server
import json
import socketserver
import threading
from typing import Any, Callable, Dict


# ----------------------------- OmniHub -----------------------------


class OmniHub:
    def __init__(self) -> None:
        self._fns: Dict[str, Callable[..., Any]] = {}
        self._lock = threading.Lock()

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        with self._lock:
            self._fns[name] = fn

    def call(self, name: str, **kwargs) -> Any:
        with self._lock:
            if name not in self._fns:
                raise KeyError(f"Function '{name}' not registered")
            return self._fns[name](**kwargs)

    def list_functions(self) -> Dict[str, str]:
        with self._lock:
            return {k: str(v) for k, v in self._fns.items()}


# ----------------------------- HTTP Server -----------------------------


class HubHandler(http.server.BaseHTTPRequestHandler):
    hub: OmniHub = None  # 型ヒント用

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        try:
            req = json.loads(body)
            fn = req.get("fn")
            args = req.get("args", {})
            res = HubHandler.hub.call(fn, **args)
            resp = {"ok": True, "result": res}
        except Exception as e:
            resp = {"ok": False, "error": str(e)}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(resp, ensure_ascii=False).encode())


# ----------------------------- CLI -----------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="OmniHub OSS")
    sub = parser.add_subparsers(dest="cmd")

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--port", type=int, default=8080)

    p_call = sub.add_parser("call")
    p_call.add_argument("--fn", type=str, required=True)
    p_call.add_argument("--args", type=str, default="{}")

    args = parser.parse_args()
    hub = OmniHub()

    # デモ関数
    hub.register("echo", lambda msg: {"echo": msg})
    hub.register("add", lambda a, b: a + b)
    hub.register("ping", lambda: "pong")

    if args.cmd == "serve":
        HubHandler.hub = hub
        with socketserver.TCPServer(("", args.port), HubHandler) as httpd:
            print(f"Serving on port {args.port}")
            httpd.serve_forever()

    elif args.cmd == "call":
        req = {"fn": args.fn, "args": json.loads(args.args)}
        res = hub.call(req["fn"], **req["args"])
        print(json.dumps(res, ensure_ascii=False))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
