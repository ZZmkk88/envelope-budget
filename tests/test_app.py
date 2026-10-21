"""Automated tests for envelope-budget. Run: .venv/bin/python -m pytest tests/ -q

All money amounts are integer cents. The scenario uses distinct months per
test group (2026-10/11 shared basics, 2027-01..06 isolated flows) so tests
stay deterministic even though budgets work on cumulative sums.
"""
import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="eb-test-")
os.environ["EB_DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["EB_INITIAL_USERNAME"] = "admin"
os.environ["EB_INITIAL_PASSWORD"] = "admin123"

import app as appmod  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(appmod.app) as c:
        yield c


def do_login(client, password="admin123"):
    res = client.post("/api/login", json={"username": "admin", "password": password})
    assert res.status_code == 200, res.text
    return res.json()


@pytest.fixture(scope="module")
def auth(client):
    data = do_login(client)
    return {"Authorization": f"Bearer {data['token']}"}


def get_categories(client, auth):
    res = client.get("/api/categories", headers=auth)
    assert res.status_code == 200
    return {c["name"]: c for c in res.json()}


def first_account_id(client, auth):
    res = client.get("/api/accounts", headers=auth)
    assert res.status_code == 200 and res.json(), "need at least one account"
    return res.json()[0]["id"]


def add_tx(client, auth, **kw):
    res = client.post("/api/transactions", json=kw, headers=auth)
    assert res.status_code == 200, res.text
    return res.json()


def envelope_of(client, auth, month, category_id):
    res = client.get(f"/api/budgets/{month}", headers=auth)
    assert res.status_code == 200, res.text
    for e in res.json()["categories"]:
        if e["category_id"] == category_id:
            return e
    raise AssertionError(f"category {category_id} not in budget view {month}")


# ------------------------------------------------------------------ auth ----

def test_login_wrong_password(client):
    res = client.post("/api/login", json={"username": "admin", "password": "nope"})
    assert res.status_code == 401


def test_login_ok_and_must_change(client):
    data = do_login(client)
    assert data["token"]
    assert data["must_change_password"] is True


def test_unauthenticated_rejected(client):
    assert client.get("/api/accounts").status_code == 401
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/budgets/2026-10").status_code == 401


def test_change_password(client, auth):
    res = client.post(
        "/api/change-password",
        json={"old_password": "admin123", "new_password": "newpass456"},
        headers=auth,
    )
    assert res.status_code == 200, res.text
    bad = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert bad.status_code == 401
    ok = do_login(client, password="newpass456")
    assert ok["must_change_password"] is False


# -------------------------------------------------------------- categories --

def test_default_categories_seeded(client, auth):
    cats = get_categories(client, auth)
    assert cats["餐饮"]["kind"] == "expense"
    assert cats["交通"]["kind"] == "expense"
    assert cats["工资"]["kind"] == "income"


def test_category_duplicate_rejected(client, auth):
    res = client.post("/api/categories", json={"name": "餐饮", "kind": "expense"}, headers=auth)
    assert res.status_code == 400


def test_category_delete_rules(client, auth):
    client.post("/api/accounts",
                json={"name": "类别测试账户", "opening_balance_cents": 0}, headers=auth)
    # unused category (even with a budget row) can be deleted
    res = client.post("/api/categories", json={"name": "宠物", "kind": "expense"}, headers=auth)
    assert res.status_code == 200
    pet = res.json()
    put = client.put(f"/api/budgets/2026-10/{pet['id']}",
                     json={"amount_cents": 5000}, headers=auth)
    assert put.status_code == 200
    assert client.delete(f"/api/categories/{pet['id']}", headers=auth).status_code == 200
    assert "宠物" not in get_categories(client, auth)

    # category referenced by a transaction cannot be deleted
    res = client.post("/api/categories", json={"name": "宠物用品", "kind": "expense"}, headers=auth)
    used = res.json()
    add_tx(client, auth, date="2026-10-08", account_id=first_account_id(client, auth),
           category_id=used["id"], kind="expense", amount_cents=100, note="猫粮")
    assert client.delete(f"/api/categories/{used['id']}", headers=auth).status_code == 400


# ---------------------------------------------------------------- accounts --

def test_account_balance_math(client, auth):
    cats = get_categories(client, auth)
    res = client.post("/api/accounts",
                      json={"name": "现金", "opening_balance_cents": 100000}, headers=auth)
    assert res.status_code == 200, res.text
    acc = res.json()
    assert acc["balance_cents"] == 100000

    add_tx(client, auth, date="2026-10-05", account_id=acc["id"],
           category_id=cats["工资"]["id"], kind="income", amount_cents=250050, note="十月工资")
    add_tx(client, auth, date="2026-10-06", account_id=acc["id"],
           category_id=cats["餐饮"]["id"], kind="expense", amount_cents=99, note="一杯豆浆 0.99 元")

    res = client.get("/api/accounts", headers=auth)
    mine = [a for a in res.json() if a["id"] == acc["id"]][0]
    assert mine["income_cents"] == 250050
    assert mine["expense_cents"] == 99
    assert mine["balance_cents"] == 100000 + 250050 - 99


def test_account_delete(client, auth):
    res = client.post("/api/accounts",
                      json={"name": "临时账户", "opening_balance_cents": 1}, headers=auth)
    acc_id = res.json()["id"]
    assert client.delete(f"/api/accounts/{acc_id}", headers=auth).status_code == 200
    ids = [a["id"] for a in client.get("/api/accounts", headers=auth).json()]
    assert acc_id not in ids
    assert client.delete(f"/api/accounts/{acc_id}", headers=auth).status_code == 404


# ------------------------------------------------------------- transactions --

def test_transaction_validation(client, auth):
    cats = get_categories(client, auth)
    acc_id = first_account_id(client, auth)
    base = {"date": "2026-10-07", "account_id": acc_id,
            "category_id": cats["餐饮"]["id"], "kind": "expense", "note": ""}
    assert client.post("/api/transactions", json={**base, "amount_cents": 0},
                       headers=auth).status_code == 422
    assert client.post("/api/transactions", json={**base, "amount_cents": -50},
                       headers=auth).status_code == 422
    assert client.post("/api/transactions", json={**base, "amount_cents": 10.5},
                       headers=auth).status_code == 422
    # kind does not match the category's kind
    assert client.post("/api/transactions",
                       json={**base, "category_id": cats["工资"]["id"], "amount_cents": 100},
                       headers=auth).status_code == 400
    # impossible date
    assert client.post("/api/transactions",
                       json={**base, "date": "2026-02-30", "amount_cents": 100},
                       headers=auth).status_code == 400
    # unknown account
    assert client.post("/api/transactions",
                       json={**base, "account_id": 999999, "amount_cents": 100},
                       headers=auth).status_code == 400


def test_transaction_edit_and_delete(client, auth):
    cats = get_categories(client, auth)
    acc_id = first_account_id(client, auth)
    tx = add_tx(client, auth, date="2026-10-09", account_id=acc_id,
                category_id=cats["交通"]["id"], kind="expense", amount_cents=5000, note="打车")
    res = client.put(f"/api/transactions/{tx['id']}",
                     json={"date": "2026-10-09", "account_id": acc_id,
                           "category_id": cats["交通"]["id"], "kind": "expense",
                           "amount_cents": 6000, "note": "打车（改）"},
                     headers=auth)
    assert res.status_code == 200 and res.json()["amount_cents"] == 6000

    lst = client.get("/api/transactions?month=2026-10&category_id=" + str(cats["交通"]["id"]),
                     headers=auth).json()
    assert [t["id"] for t in lst] == [tx["id"]]

    assert client.delete(f"/api/transactions/{tx['id']}", headers=auth).status_code == 200
    assert client.get("/api/transactions?month=2026-10&category_id=" + str(cats["交通"]["id"]),
                      headers=auth).json() == []
    assert client.delete(f"/api/transactions/{tx['id']}", headers=auth).status_code == 404


# ----------------------------------------------------------------- budgets --

def test_budget_month_view_and_carryover(client, auth):
    res = client.post("/api/categories", json={"name": "信封甲", "kind": "expense"}, headers=auth)
    cat = res.json()
    acc_id = first_account_id(client, auth)

    assert client.put(f"/api/budgets/2026-10/{cat['id']}",
                      json={"amount_cents": 80000}, headers=auth).status_code == 200
    add_tx(client, auth, date="2026-10-10", account_id=acc_id,
           category_id=cat["id"], kind="expense", amount_cents=12345, note="")

    oct_env = envelope_of(client, auth, "2026-10", cat["id"])
    assert oct_env["carry_in_cents"] == 0
    assert oct_env["budgeted_cents"] == 80000
    assert oct_env["spent_cents"] == 12345
    assert oct_env["balance_cents"] == 80000 - 12345

    # next month: unspent 67655 rolls in automatically
    nov_env = envelope_of(client, auth, "2026-11", cat["id"])
    assert nov_env["carry_in_cents"] == 67655

    assert client.put(f"/api/budgets/2026-11/{cat['id']}",
                      json={"amount_cents": 20000}, headers=auth).status_code == 200
    add_tx(client, auth, date="2026-11-03", account_id=acc_id,
           category_id=cat["id"], kind="expense", amount_cents=7655, note="")
    nov_env = envelope_of(client, auth, "2026-11", cat["id"])
    assert nov_env["spent_cents"] == 7655
    assert nov_env["balance_cents"] == 67655 + 20000 - 7655


def test_overspend_negative_carryover(client, auth):
    res = client.post("/api/categories", json={"name": "信封乙", "kind": "expense"}, headers=auth)
    cat = res.json()
    acc_id = first_account_id(client, auth)
    client.put(f"/api/budgets/2026-10/{cat['id']}", json={"amount_cents": 1000}, headers=auth)
    add_tx(client, auth, date="2026-10-11", account_id=acc_id,
           category_id=cat["id"], kind="expense", amount_cents=1500, note="超支")
    oct_env = envelope_of(client, auth, "2026-10", cat["id"])
    assert oct_env["balance_cents"] == -500
    nov_env = envelope_of(client, auth, "2026-11", cat["id"])
    assert nov_env["carry_in_cents"] == -500


def test_budget_rejects_income_category(client, auth):
    cats = get_categories(client, auth)
    res = client.put(f"/api/budgets/2026-10/{cats['工资']['id']}",
                     json={"amount_cents": 100}, headers=auth)
    assert res.status_code == 400


def test_month_format_validation(client, auth):
    assert client.get("/api/budgets/2026-13", headers=auth).status_code == 400
    assert client.get("/api/reports/202610", headers=auth).status_code == 400


def test_to_budget_moves_with_opening_income_and_assignment(client, auth):
    cats = get_categories(client, auth)
    before = client.get("/api/budgets/2027-03", headers=auth).json()["summary"]["to_budget_cents"]

    acc = client.post("/api/accounts",
                      json={"name": "结转测试账户", "opening_balance_cents": 5000},
                      headers=auth).json()
    add_tx(client, auth, date="2027-03-15", account_id=acc["id"],
           category_id=cats["工资"]["id"], kind="income", amount_cents=7000, note="")
    res = client.post("/api/categories", json={"name": "信封丙", "kind": "expense"}, headers=auth)
    cat = res.json()
    client.put(f"/api/budgets/2027-03/{cat['id']}", json={"amount_cents": 3000}, headers=auth)

    after = client.get("/api/budgets/2027-03", headers=auth).json()["summary"]["to_budget_cents"]
    assert after - before == 5000 + 7000 - 3000


# ----------------------------------------------------------------- reports --

def test_report_totals_and_ranking(client, auth):
    cats = get_categories(client, auth)
    acc_id = first_account_id(client, auth)
    add_tx(client, auth, date="2027-05-01", account_id=acc_id,
           category_id=cats["工资"]["id"], kind="income", amount_cents=100000, note="五月工资")
    add_tx(client, auth, date="2027-05-02", account_id=acc_id,
           category_id=cats["餐饮"]["id"], kind="expense", amount_cents=3000, note="")
    add_tx(client, auth, date="2027-05-03", account_id=acc_id,
           category_id=cats["交通"]["id"], kind="expense", amount_cents=9000, note="")
    add_tx(client, auth, date="2027-05-04", account_id=acc_id,
           category_id=cats["餐饮"]["id"], kind="expense", amount_cents=2000, note="")

    r = client.get("/api/reports/2027-05", headers=auth).json()
    assert r["income_cents"] == 100000
    assert r["expense_cents"] == 14000
    assert r["net_cents"] == 86000
    assert [(c["name"], c["amount_cents"]) for c in r["by_category"]] == [
        ("交通", 9000), ("餐饮", 5000),
    ]


def test_cents_precision_no_float_drift(client, auth):
    res = client.post("/api/categories", json={"name": "零头", "kind": "expense"}, headers=auth)
    cat = res.json()
    acc_id = first_account_id(client, auth)
    for i in range(33):
        add_tx(client, auth, date="2027-06-10", account_id=acc_id,
               category_id=cat["id"], kind="expense", amount_cents=333, note=f"零头{i}")
    add_tx(client, auth, date="2027-06-10", account_id=acc_id,
           category_id=cat["id"], kind="expense", amount_cents=1, note="最后一分")
    r = client.get("/api/reports/2027-06", headers=auth).json()
    assert r["expense_cents"] == 33 * 333 + 1  # 10990, exact integer arithmetic
    env = envelope_of(client, auth, "2027-06", cat["id"])
    assert env["spent_cents"] == 10990
