"""Live end-to-end self-test against a real running server.

Starts app.py on a scratch port with a throwaway database, then walks the
full user flow over HTTP: login -> create account -> salary in -> assign an
envelope -> spend -> check the envelope balance -> check next month's
carry-over -> monthly report. Run: .venv/bin/python tests/live_selftest.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8237
BASE = f"http://127.0.0.1:{PORT}"


def call(method, path, body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, data=data, timeout=10) as res:
        return json.loads(res.read().decode("utf-8"))


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="eb-live-")
    env = dict(os.environ)
    env["EB_DB_PATH"] = os.path.join(tmp, "live.db")
    env["PORT"] = str(PORT)
    log_path = os.path.join(tmp, "server.log")
    log_file = open(log_path, "w")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "app.py")],
        env=env, stdout=log_file, stderr=log_file,
    )
    try:
        up = False
        for _ in range(300):
            if proc.poll() is not None:
                break
            try:
                # probe only: status code matters, body is HTML (not JSON)
                with urllib.request.urlopen(BASE + "/", timeout=5) as res:
                    up = res.status == 200
                if up:
                    break
            except Exception:
                time.sleep(0.3)
        if not up:
            log_file.flush()
            print("FAIL: server did not come up; server log tail:")
            with open(log_path) as f:
                print("".join(f.readlines()[-15:]))
            return 1

        login = call("POST", "/api/login", {"username": "admin", "password": "admin123"})
        token = login["token"]
        assert login["must_change_password"] is True
        print("PASS login (first-login change prompt flagged)")

        acc = call("POST", "/api/accounts",
                   {"name": "工资卡", "opening_balance_cents": 200000}, token)
        assert acc["balance_cents"] == 200000
        print("PASS create account, opening balance 2000.00")

        cats = {c["name"]: c for c in call("GET", "/api/categories", token=token)}
        salary = call("POST", "/api/transactions", {
            "date": "2026-10-05", "account_id": acc["id"],
            "category_id": cats["工资"]["id"], "kind": "income",
            "amount_cents": 888888, "note": "十月工资"}, token)
        assert salary["amount_cents"] == 888888
        print("PASS salary in: 8888.88")

        call("PUT", "/api/budgets/2026-10/" + str(cats["餐饮"]["id"]),
             {"amount_cents": 100000}, token)
        call("POST", "/api/transactions", {
            "date": "2026-10-12", "account_id": acc["id"],
            "category_id": cats["餐饮"]["id"], "kind": "expense",
            "amount_cents": 23456, "note": "聚餐"}, token)
        print("PASS assigned 1000.00 to 餐饮, spent 234.56")

        oct_view = call("GET", "/api/budgets/2026-10", token=token)
        env_oct = [e for e in oct_view["categories"] if e["name"] == "餐饮"][0]
        assert env_oct["balance_cents"] == 100000 - 23456, env_oct
        assert oct_view["summary"]["income_cents"] == 888888
        print("PASS October envelope balance: 765.44, to_budget:",
              oct_view["summary"]["to_budget_cents"])

        nov_view = call("GET", "/api/budgets/2026-11", token=token)
        env_nov = [e for e in nov_view["categories"] if e["name"] == "餐饮"][0]
        assert env_nov["carry_in_cents"] == 76544, env_nov
        print("PASS November carry-in rolls over: 765.44")

        report = call("GET", "/api/reports/2026-10", token=token)
        assert report["income_cents"] == 888888 and report["expense_cents"] == 23456
        assert report["by_category"][0]["name"] == "餐饮"
        print("PASS October report totals and ranking")

        print("ALL LIVE SELF-TESTS PASSED")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
