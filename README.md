# ClogniChain Lite OSS + OmniHub OSS

Lightweight, dependency-free, pure-Python implementations:

- **ClogniChain Lite**: Audit logging & parsing engine (ja/en only)
- **OmniHub OSS**: Minimal RPC hub for local or embedded usage

## Features
- Pure Python 3.9+
- Zero external dependencies
- JSONL.GZ + SQLite audit logging
- Regex-based parsing (ja/en)
- Lightweight RPC hub

## Usage
```bash
python clognichain-lite.py parse --lang ja --text "今日は良い天気です"
python clognichain-lite.py ingest --source demo --payload '{"value":123}'
python omni-hub-oss.py serve --port 8080
