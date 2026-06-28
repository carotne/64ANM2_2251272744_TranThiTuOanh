#!/usr/bin/env python3
"""Kiem thu phong thu DA LOP o tang ung dung (chay LOCAL, KHONG qua WAF).

Muc tieu: chung minh rang ngay ca khi attacker da VUOT QUA lop edge (CloudFront+WAF),
cac lop ben trong (xac thuc, phan quyen, validate, tham so hoa truy van) van chan duoc.
Day la phep thu "assume breach" cho phan ung dung — bo sung cho phan ha tang o runbook.

Khong phu thuoc thu vien ngoai (chi dung stdlib urllib) -> chay duoc bang python he thong.

Cach dung:
    # 1) Chay backend local truoc (xem memory datn-conduit-local-run):
    #    uvicorn app.main:app --port 8000   (voi DynamoDB Local o port 8001)
    # 2) Chay test:
    python backend/scripts/sec_test_local.py
    #    Tuy chon: doi target / bat kiem tra origin-verify:
    SEC_TEST_BASE=http://localhost:8000 ORIGIN_VERIFY_SECRET=mysecret \
        python backend/scripts/sec_test_local.py

Thoat code 0 = tat ca PASS, 1 = co FAIL.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("SEC_TEST_BASE", "http://localhost:8000").rstrip("/")
API = f"{BASE}/api"
ORIGIN_SECRET = os.environ.get("ORIGIN_VERIFY_SECRET", "")
RUN = str(int(time.time()))  # nhan dinh danh cho moi lan chay -> email/username duy nhat

results: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = "") -> None:
    results.append((name, passed, detail))
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] {name}" + (f"  -> {detail}" if detail else ""))


def http(method: str, path: str, *, token: str | None = None,
         body: dict | None = None, headers: dict | None = None) -> tuple[int, object]:
    """Goi HTTP, tra ve (status_code, parsed_json_or_text). Khong nem loi tren 4xx/5xx."""
    url = path if path.startswith("http") else f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Token {token}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    # Neu origin-verify dang BAT (chay AWS hoac local co set secret), gan header de cac
    # test khac di qua duoc; rieng test A se tu kiem tra thieu/sai header.
    if ORIGIN_SECRET and not (headers and "X-Origin-Verify" in headers):
        req.add_header("X-Origin-Verify", ORIGIN_SECRET)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        status = e.code
    except urllib.error.URLError as e:
        print(f"\n!! Khong ket noi duoc {url}: {e}. Backend da chay chua?")
        raise SystemExit(2)
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def register_and_login(tag: str) -> str:
    """Dang ky + dang nhap 1 user, tra ve JWT token."""
    email = f"sec_{tag}_{RUN}@example.com"
    username = f"sec_{tag}_{RUN}"
    pw = "Passw0rd!123"
    http("POST", "/users", body={"user": {"email": email, "username": username, "password": pw}})
    st, data = http("POST", "/users/login", body={"user": {"email": email, "password": pw}})
    assert st == 200, f"login that bai ({st}): {data}"
    return data["user"]["token"]


# ---------------------------------------------------------------------------
# TEST A — Lop 3: chong bypass origin (X-Origin-Verify)
# ---------------------------------------------------------------------------
def test_a_origin_verify() -> None:
    print("\n[A] Lop 3 — Chong bypass origin (X-Origin-Verify)")
    # Probe: goi 1 endpoint public KHONG kem header origin-verify.
    st, _ = http("GET", "/tags", headers={"X-Origin-Verify": "__none__"})
    if not ORIGIN_SECRET:
        # Local mac dinh secret rong -> middleware bo qua. Khong the test that o local.
        record("A1 origin-verify dang TAT (local) — kiem tra o AWS (xem runbook)",
               st == 200, f"GET /tags = {st} (khong co secret de ep 403)")
        return
    # Secret dang BAT: thieu/sai header phai bi 403; dung header phai 200.
    record("A1 thieu/sai X-Origin-Verify -> 403", st == 403, f"got {st}")
    st_ok, _ = http("GET", "/tags", headers={"X-Origin-Verify": ORIGIN_SECRET})
    record("A2 dung X-Origin-Verify -> 200", st_ok == 200, f"got {st_ok}")


# ---------------------------------------------------------------------------
# TEST C — Lop 4 & 5: xac thuc (JWT) + phan quyen (chong IDOR)
# ---------------------------------------------------------------------------
def test_c_authz(token_a: str, token_b: str, slug: str) -> None:
    print("\n[C] Lop 4-5 — Xac thuc & Phan quyen (IDOR)")
    # C1: khong co token -> 401
    st, _ = http("PUT", f"/articles/{slug}", body={"article": {"title": "hacked by anon"}})
    record("C1 sua bai khong co token -> 401", st == 401, f"got {st}")

    # C2: token gia mao (lat ky tu cuoi cua chu ky) -> 401
    bad = token_a[:-1] + ("a" if token_a[-1] != "a" else "b")
    st, _ = http("PUT", f"/articles/{slug}", token=bad,
                 body={"article": {"title": "hacked tampered"}})
    record("C2 token gia mao (sai chu ky) -> 401", st == 401, f"got {st}")

    # C3: token HOP LE cua user B sua bai cua user A -> 403 (khong phai chu so huu)
    st, _ = http("PUT", f"/articles/{slug}", token=token_b,
                 body={"article": {"title": "hacked by user B"}})
    record("C3 user B sua bai cua user A -> 403 (IDOR bi chan)", st == 403, f"got {st}")

    # C4: user B xoa bai cua user A -> 403
    st, _ = http("DELETE", f"/articles/{slug}", token=token_b)
    record("C4 user B xoa bai cua user A -> 403", st == 403, f"got {st}")

    # C5 (doi chung): chu so huu (user A) sua duoc -> 200, chung to logic dung, khong "chan bay"
    st, _ = http("PUT", f"/articles/{slug}", token=token_a,
                 body={"article": {"description": "owner edit ok"}})
    record("C5 chu so huu sua duoc -> 200 (doi chung)", st == 200, f"got {st}")


# ---------------------------------------------------------------------------
# TEST B — Lop 7: tham so hoa truy van DynamoDB (an toan by-design, KHONG nho WAF)
# ---------------------------------------------------------------------------
INJECTION_PAYLOADS = [
    # NoSQL/SQL-style — DynamoDB coi tat ca la chuoi literal, khong dien giai
    '{"$ne": null}',
    '{"$gt": ""}',
    "' OR '1'='1",
    '" OR "1"="1',
    "'; DROP TABLE conduit; --",
    "admin'--",
    "PK = ARTICLE OR 1=1",
    "*",
    "../../etc/passwd",
    "${jndi:ldap://x}",
]


def test_b_injection(token_a: str) -> None:
    print("\n[B] Lop 7 — Tham so hoa truy van (chay THANG vao app, khong co WAF)")
    # Baseline: dem so bai voi mot tag chac chan khong ton tai (hop le)
    st0, base = http("GET", "/articles?tag=__definitely_not_a_tag__", token=token_a)
    base_count = base.get("articlesCount") if isinstance(base, dict) else None
    record("B0 truy van tag binh thuong tra ve 200", st0 == 200, f"count={base_count}")

    all_safe = True
    for p in INJECTION_PAYLOADS:
        q = urllib.parse.quote(p, safe="")
        st_t, dt = http("GET", f"/articles?tag={q}", token=token_a)
        st_a, da = http("GET", f"/articles?author={q}", token=token_a)
        # An toan = khong 500, va khong tra ra du lieu khac baseline (khong bypass filter)
        ct = dt.get("articlesCount") if isinstance(dt, dict) else "ERR"
        ca = da.get("articlesCount") if isinstance(da, dict) else "ERR"
        ok = st_t < 500 and st_a < 500 and ct == base_count and ca == base_count
        all_safe = all_safe and ok
        if not ok:
            record(f"B! payload lam thay doi hanh vi: {p!r}", False,
                   f"tag:{st_t}/{ct} author:{st_a}/{ca} (baseline {base_count})")
    record("B1 toan bo payload injection KHONG gay loi & KHONG bypass filter",
           all_safe, f"{len(INJECTION_PAYLOADS)} payload, tat ca khop baseline={base_count}")

    # B2: noi dung doc hai duoc luu/tra ve NGUYEN VAN (literal) -> chung to la DATA, khong phai query.
    #     Luu y: an toan render (chong stored XSS) la trach nhiem cua FE/lop khac.
    payload_body = "<script>alert(1)</script> ' OR 1=1 -- {\"$ne\":null}"
    st_c, created = http("POST", "/articles", token=token_a, body={"article": {
        "title": "Injection probe article",
        "description": "desc",
        "body": payload_body,
        "tagList": ["sectest"],
    }})
    if st_c == 200 and isinstance(created, dict):
        returned = created["article"]["body"]
        record("B2 payload luu/tra ve nguyen van (la data, khong phai lenh)",
               returned == payload_body, f"match={returned == payload_body}")
    else:
        record("B2 tao bai de kiem tra luu tru", False, f"got {st_c}")


def summary() -> int:
    print("\n" + "=" * 64)
    print("KET QUA KIEM THU PHONG THU DA LOP (tang ung dung, local)")
    print("=" * 64)
    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print("-" * 64)
    print(f"  Tong: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    print(f"Target: {API}  (origin-verify: {'ON' if ORIGIN_SECRET else 'OFF/local'})")
    token_a = register_and_login("alice")
    token_b = register_and_login("bob")
    st, art = http("POST", "/articles", token=token_a, body={"article": {
        "title": "Alice bai viet goc",
        "description": "cua alice",
        "body": "noi dung",
        "tagList": ["sectest"],
    }})
    assert st == 200, f"tao bai that bai ({st}): {art}"
    slug = art["article"]["slug"]

    test_a_origin_verify()
    test_c_authz(token_a, token_b, slug)
    test_b_injection(token_a)
    raise SystemExit(summary())
