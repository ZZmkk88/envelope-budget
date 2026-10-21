"""envelope-budget: a lightweight single-user envelope budgeting app.

Clean-room implementation of the classic envelope method: every month you
assign money into spending categories ("envelopes"); each expense draws its
envelope down; whatever is left rolls over to the next month. Design notes
live in NOTES.md. Single-file FastAPI backend + SQLite + one static page.

All money is stored and computed as integer cents. Floats never touch money.
"""
import hashlib
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("EB_DB_PATH", str(BASE_DIR / "data" / "budget.db"))
TOKEN_TTL_SECONDS = 24 * 60 * 60
INITIAL_USERNAME = os.environ.get("EB_INITIAL_USERNAME", "admin")
INITIAL_PASSWORD = os.environ.get("EB_INITIAL_PASSWORD", "admin123")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_NAME_LENGTH = 64
MAX_NOTE_LENGTH = 500

DEFAULT_EXPENSE_CATEGORIES = ["餐饮", "交通", "购物", "居住", "娱乐", "医疗", "其他"]
DEFAULT_INCOME_CATEGORIES = ["工资", "其他收入"]

app = FastAPI(title="envelope-budget")


# ---------------------------------------------------------------------------
# small utilities
# ---------------------------------------------------------------------------

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def check_month(month: str) -> str:
    if not MONTH_RE.match(month or ""):
        raise HTTPException(status_code=400, detail="月份格式应为 YYYY-MM")
    return month


def check_date(date: str) -> str:
    if not DATE_RE.match(date or ""):
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期不存在")
    return date


def clean_name(name: str, what: str = "名称") -> str:
    name = (name or "").strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        raise HTTPException(status_code=400, detail=f"{what}为空或过长")
    return name


# ---------------------------------------------------------------------------
# database
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 200_000
    ).hex()


def init_db() -> None:
    conn = get_db()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                expires_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name TEXT NOT NULL,
                opening_balance_cents INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name TEXT NOT NULL,
                name_lower TEXT NOT NULL,
                kind TEXT NOT NULL CHECK (kind IN ('income', 'expense')),
                created_at TEXT NOT NULL,
                UNIQUE(user_id, kind, name_lower)
            );
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                month TEXT NOT NULL,
                amount_cents INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, category_id, month)
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                date TEXT NOT NULL,
                kind TEXT NOT NULL CHECK (kind IN ('income', 'expense')),
                amount_cents INTEGER NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )
        row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        if row["c"] == 0:
            salt = secrets.token_hex(16)
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, salt, must_change_password, created_at)"
                " VALUES (?, ?, ?, 1, ?)",
                (INITIAL_USERNAME, hash_password(INITIAL_PASSWORD, salt), salt, iso(utcnow())),
            )
            user_id = cur.lastrowid
            now = iso(utcnow())
            for name in DEFAULT_EXPENSE_CATEGORIES:
                conn.execute(
                    "INSERT INTO categories (user_id, name, name_lower, kind, created_at)"
                    " VALUES (?, ?, ?, 'expense', ?)",
                    (user_id, name, name.lower(), now),
                )
            for name in DEFAULT_INCOME_CATEGORIES:
                conn.execute(
                    "INSERT INTO categories (user_id, name, name_lower, kind, created_at)"
                    " VALUES (?, ?, ?, 'income', ?)",
                    (user_id, name, name.lower(), now),
                )
        conn.commit()
    finally:
        conn.close()


@app.on_event("startup")
def _startup() -> None:
    init_db()


# ---------------------------------------------------------------------------
# auth (single user; same scheme as the team's other apps)
# ---------------------------------------------------------------------------

class LoginIn(BaseModel):
    username: str
    password: str
class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str
def current_user(request: Request) -> sqlite3.Row:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = auth[len("Bearer "):].strip()
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token = ? AND s.expires_at > ?",
            (token, time.time()),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
        return row
    finally:
        conn.close()


@app.post("/api/login")
def login(body: LoginIn):
    init_db()
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (body.username.strip(),)
        ).fetchone()
        if not user or hash_password(body.password, user["salt"]) != user["password_hash"]:
            raise HTTPException(status_code=401, detail="用户名或密码不正确")
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user["id"], time.time() + TOKEN_TTL_SECONDS),
        )
        conn.commit()
        return {
            "token": token,
            "username": user["username"],
            "must_change_password": bool(user["must_change_password"]),
        }
    finally:
        conn.close()


@app.post("/api/logout")
def logout(request: Request, user: sqlite3.Row = Depends(current_user)):
    token = request.headers.get("Authorization", "")[len("Bearer "):].strip()
    conn = get_db()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.post("/api/change-password")
def change_password(body: ChangePasswordIn, request: Request, user: sqlite3.Row = Depends(current_user)):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    if hash_password(body.old_password, user["salt"]) != user["password_hash"]:
        raise HTTPException(status_code=400, detail="旧密码不正确")
    salt = secrets.token_hex(16)
    token = request.headers.get("Authorization", "")[len("Bearer "):].strip()
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ?, must_change_password = 0 WHERE id = ?",
            (hash_password(body.new_password, salt), salt, user["id"]),
        )
        # The token that just changed the password stays valid. Every other
        # session for this user was issued under the old password.
        conn.execute(
            "DELETE FROM sessions WHERE user_id = ? AND token != ?",
            (user["id"], token),
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/me")
def me(user: sqlite3.Row = Depends(current_user)):
    return {
        "username": user["username"],
        "must_change_password": bool(user["must_change_password"]),
    }


# ---------------------------------------------------------------------------
# accounts: balance = opening + income - expense (integer cents throughout)
# ---------------------------------------------------------------------------

class AccountIn(BaseModel):
    name: str
    opening_balance_cents: int = Field(default=0, ge=0)


def account_with_balance(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    sums = conn.execute(
        "SELECT kind, COALESCE(SUM(amount_cents), 0) AS total FROM transactions"
        " WHERE account_id = ? GROUP BY kind",
        (row["id"],),
    ).fetchall()
    income = sum(s["total"] for s in sums if s["kind"] == "income")
    expense = sum(s["total"] for s in sums if s["kind"] == "expense")
    return {
        "id": row["id"],
        "name": row["name"],
        "opening_balance_cents": row["opening_balance_cents"],
        "income_cents": income,
        "expense_cents": expense,
        "balance_cents": row["opening_balance_cents"] + income - expense,
        "created_at": row["created_at"],
    }


@app.get("/api/accounts")
def list_accounts(user: sqlite3.Row = Depends(current_user)):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM accounts WHERE user_id = ? ORDER BY id", (user["id"],)
        ).fetchall()
        return [account_with_balance(conn, r) for r in rows]
    finally:
        conn.close()


@app.post("/api/accounts")
def create_account(body: AccountIn, user: sqlite3.Row = Depends(current_user)):
    name = clean_name(body.name, "账户名称")
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO accounts (user_id, name, opening_balance_cents, created_at)"
            " VALUES (?, ?, ?, ?)",
            (user["id"], name, body.opening_balance_cents, iso(utcnow())),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (cur.lastrowid,)).fetchone()
        return account_with_balance(conn, row)
    finally:
        conn.close()


@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: int, user: sqlite3.Row = Depends(current_user)):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM accounts WHERE id = ? AND user_id = ?", (account_id, user["id"])
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="账户不存在")
        # transactions of this account are removed with it (ON DELETE CASCADE)
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# categories
# ---------------------------------------------------------------------------

class CategoryIn(BaseModel):
    name: str
    kind: str


@app.get("/api/categories")
def list_categories(user: sqlite3.Row = Depends(current_user), kind: str = ""):
    conn = get_db()
    try:
        if kind in ("income", "expense"):
            rows = conn.execute(
                "SELECT * FROM categories WHERE user_id = ? AND kind = ? ORDER BY id",
                (user["id"], kind),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM categories WHERE user_id = ? ORDER BY kind, id", (user["id"],)
            ).fetchall()
        return [
            {"id": r["id"], "name": r["name"], "kind": r["kind"], "created_at": r["created_at"]}
            for r in rows
        ]
    finally:
        conn.close()


@app.post("/api/categories")
def create_category(body: CategoryIn, user: sqlite3.Row = Depends(current_user)):
    if body.kind not in ("income", "expense"):
        raise HTTPException(status_code=400, detail="类别类型只能是 income 或 expense")
    name = clean_name(body.name, "类别名称")
    conn = get_db()
    try:
        dup = conn.execute(
            "SELECT id FROM categories WHERE user_id = ? AND kind = ? AND name_lower = ?",
            (user["id"], body.kind, name.lower()),
        ).fetchone()
        if dup:
            raise HTTPException(status_code=400, detail="同类类别里已有这个名字")
        cur = conn.execute(
            "INSERT INTO categories (user_id, name, name_lower, kind, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (user["id"], name, name.lower(), body.kind, iso(utcnow())),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM categories WHERE id = ?", (cur.lastrowid,)).fetchone()
        return {"id": row["id"], "name": row["name"], "kind": row["kind"], "created_at": row["created_at"]}
    finally:
        conn.close()


@app.delete("/api/categories/{category_id}")
def delete_category(category_id: int, user: sqlite3.Row = Depends(current_user)):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM categories WHERE id = ? AND user_id = ?", (category_id, user["id"])
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="类别不存在")
        used = conn.execute(
            "SELECT COUNT(*) AS c FROM transactions WHERE category_id = ?", (category_id,)
        ).fetchone()["c"]
        if used:
            raise HTTPException(status_code=400, detail="类别已被记账记录使用，不能删除")
        # its budget rows go with it (ON DELETE CASCADE)
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# transactions
# ---------------------------------------------------------------------------

class TransactionIn(BaseModel):
    date: str
    account_id: int
    category_id: int
    kind: str
    amount_cents: int = Field(gt=0)
    note: str = ""


def validate_transaction(conn: sqlite3.Connection, user_id: int, body: TransactionIn) -> None:
    check_date(body.date)
    if body.kind not in ("income", "expense"):
        raise HTTPException(status_code=400, detail="类型只能是 income 或 expense")
    if len(body.note or "") > MAX_NOTE_LENGTH:
        raise HTTPException(status_code=400, detail="备注过长")
    acc = conn.execute(
        "SELECT id FROM accounts WHERE id = ? AND user_id = ?", (body.account_id, user_id)
    ).fetchone()
    if not acc:
        raise HTTPException(status_code=400, detail="账户不存在")
    cat = conn.execute(
        "SELECT * FROM categories WHERE id = ? AND user_id = ?", (body.category_id, user_id)
    ).fetchone()
    if not cat:
        raise HTTPException(status_code=400, detail="类别不存在")
    if cat["kind"] != body.kind:
        raise HTTPException(status_code=400, detail="类别与收支类型不匹配")


def tx_to_dict(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "date": r["date"],
        "account_id": r["account_id"],
        "category_id": r["category_id"],
        "kind": r["kind"],
        "amount_cents": r["amount_cents"],
        "note": r["note"],
        "created_at": r["created_at"],
    }


@app.get("/api/transactions")
def list_transactions(
    user: sqlite3.Row = Depends(current_user),
    month: str = "",
    account_id: int = 0,
    category_id: int = 0,
    kind: str = "",
):
    clauses = ["t.user_id = ?"]
    params: list = [user["id"]]
    if month:
        check_month(month)
        clauses.append("substr(t.date, 1, 7) = ?")
        params.append(month)
    if account_id:
        clauses.append("t.account_id = ?")
        params.append(account_id)
    if category_id:
        clauses.append("t.category_id = ?")
        params.append(category_id)
    if kind in ("income", "expense"):
        clauses.append("t.kind = ?")
        params.append(kind)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT t.* FROM transactions t WHERE " + " AND ".join(clauses)
            + " ORDER BY t.date DESC, t.id DESC",
            params,
        ).fetchall()
        return [tx_to_dict(r) for r in rows]
    finally:
        conn.close()


@app.post("/api/transactions")
def create_transaction(body: TransactionIn, user: sqlite3.Row = Depends(current_user)):
    conn = get_db()
    try:
        validate_transaction(conn, user["id"], body)
        cur = conn.execute(
            "INSERT INTO transactions (user_id, account_id, category_id, date, kind,"
            " amount_cents, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], body.account_id, body.category_id, body.date, body.kind,
             body.amount_cents, (body.note or "").strip(), iso(utcnow())),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (cur.lastrowid,)).fetchone()
        return tx_to_dict(row)
    finally:
        conn.close()


@app.put("/api/transactions/{tx_id}")
def update_transaction(tx_id: int, body: TransactionIn, user: sqlite3.Row = Depends(current_user)):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user["id"])
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="记录不存在")
        validate_transaction(conn, user["id"], body)
        conn.execute(
            "UPDATE transactions SET account_id = ?, category_id = ?, date = ?, kind = ?,"
            " amount_cents = ?, note = ? WHERE id = ?",
            (body.account_id, body.category_id, body.date, body.kind,
             body.amount_cents, (body.note or "").strip(), tx_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        return tx_to_dict(row)
    finally:
        conn.close()


@app.delete("/api/transactions/{tx_id}")
def delete_transaction(tx_id: int, user: sqlite3.Row = Depends(current_user)):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user["id"])
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="记录不存在")
        conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# envelope budgets
#
# Rollover rule (cumulative, same idea as classic envelope budgeting):
#   carry_in(cat, M)  = sum(budgets of cat for months < M)
#                       - sum(expenses of cat for months < M)
#   balance(cat, M)   = carry_in + budgeted(M) - spent(M)
# Unspent money therefore rolls into the next month automatically, and an
# overspent envelope carries its negative balance forward too.
# "To budget" for month M = all opening balances + all income up to M
#                           - all budget assignments up to M.
# ---------------------------------------------------------------------------

def month_of(date_str: str) -> str:
    return date_str[:7]


def spent_by_category(conn: sqlite3.Connection, user_id: int, month: str, before: bool) -> dict:
    op = "<" if before else "="
    rows = conn.execute(
        "SELECT category_id, COALESCE(SUM(amount_cents), 0) AS total FROM transactions"
        f" WHERE user_id = ? AND kind = 'expense' AND substr(date, 1, 7) {op} ?"
        " GROUP BY category_id",
        (user_id, month),
    ).fetchall()
    return {r["category_id"]: r["total"] for r in rows}


def budgeted_by_category(conn: sqlite3.Connection, user_id: int, month: str, before: bool) -> dict:
    op = "<" if before else "="
    rows = conn.execute(
        f"SELECT category_id, COALESCE(SUM(amount_cents), 0) AS total FROM budgets"
        f" WHERE user_id = ? AND month {op} ? GROUP BY category_id",
        (user_id, month),
    ).fetchall()
    return {r["category_id"]: r["total"] for r in rows}


@app.get("/api/budgets/{month}")
def get_budgets(month: str, user: sqlite3.Row = Depends(current_user)):
    check_month(month)
    conn = get_db()
    try:
        cats = conn.execute(
            "SELECT * FROM categories WHERE user_id = ? AND kind = 'expense' ORDER BY id",
            (user["id"],),
        ).fetchall()
        spent_before = spent_by_category(conn, user["id"], month, before=True)
        budgeted_before = budgeted_by_category(conn, user["id"], month, before=True)
        spent_now = spent_by_category(conn, user["id"], month, before=False)
        budgeted_now = budgeted_by_category(conn, user["id"], month, before=False)

        envelopes = []
        for c in cats:
            carry_in = budgeted_before.get(c["id"], 0) - spent_before.get(c["id"], 0)
            budgeted = budgeted_now.get(c["id"], 0)
            spent = spent_now.get(c["id"], 0)
            envelopes.append({
                "category_id": c["id"],
                "name": c["name"],
                "carry_in_cents": carry_in,
                "budgeted_cents": budgeted,
                "spent_cents": spent,
                "balance_cents": carry_in + budgeted - spent,
            })

        income_month = conn.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) AS t FROM transactions"
            " WHERE user_id = ? AND kind = 'income' AND substr(date, 1, 7) = ?",
            (user["id"], month),
        ).fetchone()["t"]
        expense_month = sum(spent_now.values())
        opening_total = conn.execute(
            "SELECT COALESCE(SUM(opening_balance_cents), 0) AS t FROM accounts WHERE user_id = ?",
            (user["id"],),
        ).fetchone()["t"]
        income_cum = conn.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) AS t FROM transactions"
            " WHERE user_id = ? AND kind = 'income' AND substr(date, 1, 7) <= ?",
            (user["id"], month),
        ).fetchone()["t"]
        budgeted_cum = conn.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) AS t FROM budgets"
            " WHERE user_id = ? AND month <= ?",
            (user["id"], month),
        ).fetchone()["t"]
        return {
            "month": month,
            "summary": {
                "income_cents": income_month,
                "expense_cents": expense_month,
                "to_budget_cents": opening_total + income_cum - budgeted_cum,
            },
            "categories": envelopes,
        }
    finally:
        conn.close()


class BudgetIn(BaseModel):
    amount_cents: int = Field(ge=0)


@app.put("/api/budgets/{month}/{category_id}")
def set_budget(month: str, category_id: int, body: BudgetIn,
               user: sqlite3.Row = Depends(current_user)):
    check_month(month)
    conn = get_db()
    try:
        cat = conn.execute(
            "SELECT * FROM categories WHERE id = ? AND user_id = ?", (category_id, user["id"])
        ).fetchone()
        if not cat:
            raise HTTPException(status_code=404, detail="类别不存在")
        if cat["kind"] != "expense":
            raise HTTPException(status_code=400, detail="只有支出类别可以分配信封额度")
        conn.execute(
            "INSERT INTO budgets (user_id, category_id, month, amount_cents) VALUES (?, ?, ?, ?)"
            " ON CONFLICT(user_id, category_id, month) DO UPDATE SET amount_cents = excluded.amount_cents",
            (user["id"], category_id, month, body.amount_cents),
        )
        conn.commit()
        return {"ok": True, "month": month, "category_id": category_id,
                "amount_cents": body.amount_cents}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# monthly report
# ---------------------------------------------------------------------------

@app.get("/api/reports/{month}")
def get_report(month: str, user: sqlite3.Row = Depends(current_user)):
    check_month(month)
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT kind, COALESCE(SUM(amount_cents), 0) AS t FROM transactions"
            " WHERE user_id = ? AND substr(date, 1, 7) = ? GROUP BY kind",
            (user["id"], month),
        ).fetchall()
        income = sum(r["t"] for r in totals if r["kind"] == "income")
        expense = sum(r["t"] for r in totals if r["kind"] == "expense")
        rows = conn.execute(
            "SELECT t.category_id AS cid, c.name AS name,"
            " COALESCE(SUM(t.amount_cents), 0) AS total"
            " FROM transactions t JOIN categories c ON c.id = t.category_id"
            " WHERE t.user_id = ? AND t.kind = 'expense' AND substr(t.date, 1, 7) = ?"
            " GROUP BY t.category_id ORDER BY total DESC, c.id",
            (user["id"], month),
        ).fetchall()
        return {
            "month": month,
            "income_cents": income,
            "expense_cents": expense,
            "net_cents": income - expense,
            "by_category": [
                {"category_id": r["cid"], "name": r["name"], "amount_cents": r["total"]}
                for r in rows
            ],
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# frontend
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
