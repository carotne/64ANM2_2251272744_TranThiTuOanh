#!/usr/bin/env python3
"""Probe SQLi payloads through CloudFront/WAF without being confused by 422s.

This is an edge/WAF test, not an application-layer test. Send requests to the
public CloudFront URL (or frontend custom domain), not directly to API Gateway.

Examples:
    python backend/scripts/sec_test_waf_sqli.py --base https://app.example.com
    python backend/scripts/sec_test_waf_sqli.py --base https://d123.cloudfront.net --limit 50
    python backend/scripts/sec_test_waf_sqli.py --base https://app.example.com --mode query,login-body

Exit code:
    0 = WAF blocks were observed and backend validation did not dominate
    1 = no WAF blocks or backend validation dominated the result
    2 = target/request setup error
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
WORKSPACE_ROOT = SCRIPT.parents[3]
DEFAULT_PAYLOAD_FILE = WORKSPACE_ROOT / "PayloadSQLi" / "sqli_all.txt"

WAF_STATUSES = {403, 405, 406, 429}


def load_payloads(path: Path, limit: int | None) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Payload file not found: {path}")

    seen: set[str] = set()
    payloads: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        payload = raw.strip()
        if not payload or payload.startswith("#") or payload in seen:
            continue
        seen.add(payload)
        payloads.append(payload)
        if limit is not None and len(payloads) >= limit:
            break
    return payloads


def http(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    timeout: int = 20,
) -> tuple[int, str, dict[str, str]]:
    data = None
    if body is not None:
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", "datn-waf-sqli-probe/1.0")
    req.add_header("Accept", "application/json,text/plain,*/*")
    if body is not None:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read(512).decode("utf-8", errors="replace")
            return resp.status, text, dict(resp.headers.items())
    except urllib.error.HTTPError as e:
        text = e.read(512).decode("utf-8", errors="replace")
        return e.code, text, dict(e.headers.items())
    except urllib.error.URLError as e:
        raise RuntimeError(f"Cannot reach target: {e}") from e


def classify(status: int, text: str, headers: dict[str, str]) -> str:
    server = (headers.get("Server") or headers.get("server") or "").lower()
    via = (headers.get("Via") or headers.get("via") or "").lower()
    lower_text = text.lower()
    looks_like_fastapi_json = lower_text.startswith('{"detail"') or lower_text.startswith('{"message"')

    if status in WAF_STATUSES and not looks_like_fastapi_json and (
        "cloudfront" in server
        or "cloudfront" in via
        or "request blocked" in lower_text
        or "forbidden" in lower_text
    ):
        return "waf_block"
    if status == 422:
        return "backend_422"
    if 400 <= status < 500:
        return "backend_4xx"
    if status >= 500:
        return "server_error"
    return "allowed"


def build_query_probe(base_api: str, payload: str) -> tuple[str, str, dict[str, Any] | None]:
    q = urllib.parse.urlencode({"tag": payload, "limit": "20", "offset": "0"})
    return "GET", f"{base_api}/articles?{q}", None


def build_author_probe(base_api: str, payload: str) -> tuple[str, str, dict[str, Any] | None]:
    q = urllib.parse.urlencode({"author": payload, "limit": "20", "offset": "0"})
    return "GET", f"{base_api}/articles?{q}", None


def build_path_probe(base_api: str, payload: str) -> tuple[str, str, dict[str, Any] | None]:
    encoded = urllib.parse.quote(payload, safe="")
    return "GET", f"{base_api}/profiles/{encoded}", None


def build_login_body_probe(base_api: str, payload: str) -> tuple[str, str, dict[str, Any]]:
    # Keep the shape valid for FastAPI/Pydantic. Put the SQLi string in password
    # because email must remain syntactically valid or the app returns 422.
    return (
        "POST",
        f"{base_api}/users/login",
        {"user": {"email": "waf-probe@example.com", "password": f"Password123! {payload}"}},
    )


BUILDERS = {
    "query": build_query_probe,
    "author-query": build_author_probe,
    "path": build_path_probe,
    "login-body": build_login_body_probe,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send SQLi payloads through CloudFront/WAF and separate WAF blocks from backend 422s."
    )
    parser.add_argument(
        "--base",
        required=True,
        help="CloudFront/frontend base URL, for example https://d123.cloudfront.net or https://app.example.com",
    )
    parser.add_argument(
        "--payload-file",
        default=str(DEFAULT_PAYLOAD_FILE),
        help=f"Payload file path. Default: {DEFAULT_PAYLOAD_FILE}",
    )
    parser.add_argument(
        "--mode",
        default="query",
        help=f"Comma-separated probe modes: {', '.join(BUILDERS)}. Default: query",
    )
    parser.add_argument("--limit", type=int, default=100, help="Max unique payload lines to test. Default: 100")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds. Default: 20")
    parser.add_argument("--show", type=int, default=10, help="Number of sample results to print per class. Default: 10")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base = args.base.rstrip("/")
    base_api = f"{base}/api"
    payload_file = Path(args.payload_file).expanduser().resolve()

    modes = [m.strip() for m in args.mode.split(",") if m.strip()]
    unknown = [m for m in modes if m not in BUILDERS]
    if unknown:
        print(f"Unknown mode(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    try:
        payloads = load_payloads(payload_file, args.limit)
    except OSError as e:
        print(str(e), file=sys.stderr)
        return 2
    if not payloads:
        print(f"No payloads found in {payload_file}", file=sys.stderr)
        return 2

    print(f"Target: {base_api}")
    print(f"Payloads: {len(payloads)} from {payload_file}")
    print(f"Modes: {', '.join(modes)}")
    print()

    counts: Counter[str] = Counter()
    samples: dict[str, list[str]] = {
        "waf_block": [],
        "backend_422": [],
        "backend_4xx": [],
        "allowed": [],
        "server_error": [],
    }

    total = 0
    for payload in payloads:
        for mode in modes:
            method, url, body = BUILDERS[mode](base_api, payload)
            total += 1
            try:
                status, text, headers = http(method, url, body=body, timeout=args.timeout)
            except RuntimeError as e:
                print(str(e), file=sys.stderr)
                return 2

            kind = classify(status, text, headers)
            counts[kind] += 1
            if len(samples[kind]) < args.show:
                samples[kind].append(f"{mode} {status}: {payload}")

            marker = "BLOCK" if kind == "waf_block" else "PASS "
            print(f"[{marker}] {mode:<13} {status:<3} {payload[:100]}")

    print()
    print("=" * 72)
    print("SUMMARY")
    print("=" * 72)
    print(f"Total probes      : {total}")
    print(f"WAF blocked       : {counts['waf_block']}")
    print(f"Reached backend   : {counts['allowed'] + counts['backend_4xx'] + counts['backend_422']}")
    print(f"Backend 422       : {counts['backend_422']}")
    print(f"Backend other 4xx : {counts['backend_4xx']}")
    print(f"2xx/allowed       : {counts['allowed']}")
    print(f"5xx/server error  : {counts['server_error']}")

    for kind, rows in samples.items():
        if rows:
            print()
            print(f"{kind} samples:")
            for row in rows:
                print(f"  - {row}")

    if counts["backend_422"]:
        print()
        print("NOTE: 422 means the request reached FastAPI/Pydantic. For WAF testing, keep")
        print("the request JSON/schema valid and put the SQLi string inside a valid field.")

    if counts["waf_block"] == 0:
        print()
        print("FAIL: no WAF blocks were observed. Confirm --base is the CloudFront/frontend")
        print("URL, enable_waf=true, and the Web ACL is attached to the distribution.")
        return 1

    if counts["backend_422"] > counts["waf_block"]:
        print()
        print("FAIL: backend validation is dominating the result. Use --mode query or")
        print("login-body so payloads are carried in schema-valid requests.")
        return 1

    print()
    print("PASS: WAF blocks were observed before the request reached the backend.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
