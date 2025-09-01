# SPDX-License-Identifier: MIT
"""
clognichain-lite-flake8.py — ClogniChain (Lightweight OSS Edition, Pure-Python)
flake8 safe: max line length ~80
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sqlite3
import threading
import time
from typing import Any, Dict, List


def now_ts() -> int:
    return int(time.time())


# ----------------------------- Ring buffers -----------------------------


class RingBuffer:
    __slots__ = ("size", "buf", "idx")

    def __init__(self, size: int = 4096):
        self.size = size
        self.buf: List[Any] = []
        self.idx = 0

    def push(self, x: Any) -> None:
        if len(self.buf) < self.size:
            self.buf.append(x)
        else:
            self.buf[self.idx] = x
            self.idx = (self.idx + 1) % self.size

    def last(self, n: int = 1) -> List[Any]:
        return self.buf[-n:]


# ----------------------------- Parser -----------------------------


class Parser:
    def __init__(self, lang: str = "ja"):
        self.lang = lang
        self.re_ja = re.compile(r"[一-龠ぁ-んァ-ヴー]+")
        self.re_en = re.compile(r"[A-Za-z]+")

    def parse(self, text: str) -> Dict[str, Any]:
        if self.lang == "ja":
            tokens = self.re_ja.findall(text)
        else:
            tokens = self.re_en.findall(text)
        return {"lang": self.lang, "tokens": tokens, "len": len(tokens)}


# ----------------------------- Logger -----------------------------


class Logger:
    def __init__(self, path: str = "audit.jsonl.gz", db: str = "audit.db"):
        self.path = path
        self.db = db
        self.lock = threading.Lock()
        self._ensure_db()

    def _ensure_db(self) -> None:
        with sqlite3.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute(
                """CREATE TABLE IF NOT EXISTS audit_index (
                    ts INTEGER,
                    sha TEXT,
                    source TEXT,
                    payload TEXT
                )"""
            )
            conn.commit()

    def append(self, source: str, payload: Dict[str, Any]) -> None:
        ts = now_ts()
        sha = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
        rec = {"ts": ts, "sha": sha, "source": source, "payload": payload}

        with self.lock:
            with gzip.open(self.path, "at", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            with sqlite3.connect(self.db) as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO audit_index VALUES (?, ?, ?, ?)",
                    (
                        ts,
                        sha,
                        source,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
                conn.commit()

    def search(self, term: str, limit: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute(
                (
                    "SELECT ts, sha, source, payload "
                    "FROM audit_index "
                    "WHERE payload LIKE ? "
                    "ORDER BY ts DESC LIMIT ?"
                ),
                (f"%{term}%", limit),
            )
            rows = cur.fetchall()
        return [
            {
                "ts": ts,
                "sha": sha,
                "source": source,
                "payload": json.loads(payload),
            }
            for ts, sha, source, payload in rows
        ]

    def tail(self, n: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute(
                (
                    "SELECT ts, sha, source, payload "
                    "FROM audit_index "
                    "ORDER BY ts DESC LIMIT ?"
                ),
                (n,),
            )
            rows = cur.fetchall()
        return [
            {
                "ts": ts,
                "sha": sha,
                "source": source,
                "payload": json.loads(payload),
            }
            for ts, sha, source, payload in rows
        ]


# ----------------------------- CLI -----------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="ClogniChain Lite OSS")
    sub = parser.add_subparsers(dest="cmd")

    p_parse = sub.add_parser("parse")
    p_parse.add_argument("--lang", type=str, default="ja")
    p_parse.add_argument("--text", type=str, required=True)

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--source", type=str, required=True)
    p_ingest.add_argument("--payload", type=str, required=True)

    p_tail = sub.add_parser("tail")
    p_tail.add_argument("--n", type=int, default=10)

    p_search = sub.add_parser("search")
    p_search.add_argument("--term", type=str, required=True)

    sub.add_parser("stats")

    args = parser.parse_args()
    log = Logger()

    if args.cmd == "parse":
        res = Parser(args.lang).parse(args.text)
        print(json.dumps(res, ensure_ascii=False))

    elif args.cmd == "ingest":
        payload = json.loads(args.payload)
        log.append(args.source, payload)
        print("OK")

    elif args.cmd == "tail":
        print(json.dumps(log.tail(args.n), ensure_ascii=False, indent=2))

    elif args.cmd == "search":
        print(json.dumps(log.search(args.term), ensure_ascii=False, indent=2))

    elif args.cmd == "stats":
        with sqlite3.connect(log.db) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM audit_index")
            count = cur.fetchone()[0]
        print(json.dumps({"entries": count}, ensure_ascii=False))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
