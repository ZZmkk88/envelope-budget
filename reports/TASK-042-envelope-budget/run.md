# TASK-042 envelope-budget 执行记录

开工时间：2026-10-21。工作目录 `E:\muse-bridge\in\TASK-042-envelope-budget`。先读仓库文件，再按 README 装环境、跑测试、起服务。

## 步骤 0 · 确认 Python

命令：

```powershell
python --version
python -c "import sys; print(sys.version); print(sys.executable)"
```

输出：

```text
Python 3.11.9
3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
E:\muse-bridge\env\TASK-042-envelope-budget\Scripts\python.exe
pip 24.0 from E:\muse-bridge\env\TASK-042-envelope-budget\Lib\site-packages\pip (python 3.11)
WARNING: Package(s) not found: fastapi, httpx, pytest, uvicorn
```

说明：`py -3 --version` 失败（`Unable to create process using 'E:\python.exe --version'`）。后续用上述 `python`（3.11.9，满足 README 要求的 3.10+）。这是任务预置的虚拟环境，不在仓库内；不在仓库里再建 `.venv`，以免把环境写进待审目录。数据库与探针脚本放到 `E:\muse-bridge\work\TASK-042-envelope-budget`。

## 步骤 1 · 安装依赖

命令（等价于 README 的 `pip install -r requirements.txt`，解释器已是虚拟环境）：

```powershell
python -m pip install -r E:\muse-bridge\in\TASK-042-envelope-budget\requirements.txt
```

输出片段（exit 0）：

```text
Collecting fastapi==0.156.7
Collecting uvicorn==0.54.0
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 click-8.5.0 fastapi-0.156.7 h11-0.16.0 idna-3.20 opentelemetry-api-1.45.1 pydantic-2.14.1 pydantic-core-2.50.1 starlette-1.9.0 typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.54.0
```

命令：

```powershell
python -m pip install -r E:\muse-bridge\in\TASK-042-envelope-budget\requirements-dev.txt
```

输出片段（exit 0）：

```text
Requirement already satisfied: fastapi==0.156.7
Requirement already satisfied: uvicorn==0.54.0
Collecting httpx==0.28.1
Collecting pytest==9.1.1
Successfully installed certifi-2026.10.19 colorama-0.4.6 httpcore-1.0.9 httpx-0.28.1 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
```

## 步骤 2 · 跑测试

工作目录即仓库根（pytest 能 import `app`）。加 `-p no:cacheprovider`，避免在仓库写 `.pytest_cache`。

命令：

```powershell
python -m pytest tests/ -q -p no:cacheprovider
```

输出（exit 0）：

```text
..................                                                       [100%]
============================== warnings summary ===============================
app.py:175
  DeprecationWarning: on_event is deprecated, use lifespan event handlers instead.
    @app.on_event("startup")
..\..\env\TASK-042-envelope-budget\Lib\site-packages\fastapi\applications.py:4723
  DeprecationWarning: on_event is deprecated, use lifespan event handlers instead.
fastapi\testclient.py:1
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
18 passed, 3 warnings in 3.21s
```

`tests/live_selftest.py` 不是 pytest 用例（`python -m pytest tests/live_selftest.py -q -p no:cacheprovider` → `no tests ran in 0.05s`，exit 1）。按 README 用脚本方式重跑：

```powershell
python tests/live_selftest.py
```

输出（exit 0）：

```text
PASS login (first-login change prompt flagged)
PASS create account, opening balance 2000.00
PASS salary in: 8888.88
PASS assigned 1000.00 to 餐饮, spent 234.56
PASS October envelope balance: 765.44, to_budget: 988888
PASS November carry-in rolls over: 765.44
PASS October report totals and ranking
ALL LIVE SELF-TESTS PASSED
```

自测进程监听 `127.0.0.1:8237`（见 `tests/live_selftest.py`），脚本在 `finally` 里 `proc.terminate()` 关掉。结束后 `netstat` 已无 8237 LISTENING。

## 步骤 3 · 逻辑探针（外键、跨年结转、第二用户、文档路由）

脚本：`E:\muse-bridge\work\TASK-042-envelope-budget\probe_logic.py`  
数据库在同一 work 目录。命令：

```powershell
python E:\muse-bridge\work\TASK-042-envelope-budget\probe_logic.py
```

与本仓库有关的输出（exit 0）：

```text
OK   pragma foreign_keys | foreign_keys=1
OK   delete account cascades tx | remaining_tx=0
OK   year boundary carry | carry_in_cents=3800 spent_cents=0 balance_cents=3800
OK   future income excluded from earlier to_budget | before=-5000 after_aug=-5000 dec=4999
OK   category delete drops budgets and restores to_budget | tb0=-5000 tb1=-7222 tb2=-5000 orphan_budgets=0
OK   bob cannot list admin accounts | []
OK   bob cannot delete admin account | status=404
OK   bob cannot post on admin account | {"detail":"账户不存在"}
OK   bob cannot budget admin category | {"detail":"类别不存在"}
OK   bob report empty | expense_cents=0
OK   password change keeps current token, drops other | change=200 other=401 current=200
OK   docs closed | docs=404 openapi=404 redoc=404
OK   no health route | health=404 api_health=404
OK   homepage 200 html | status=200 ctype=text/html; charset=utf-8 （正文含「信封账本」）
```

上述 HTTP 断言来自进程内 TestClient。同脚本后半段去连 `127.0.0.1:8000`，该端口当时已有 LISTENING pid 32492（本脚本拉起的解释器 pid 是 33020）。`GET /openapi.json` 的标题是 `freshfeeds`。那一段不能当作本仓库的启动结果。本仓库 `app.py` 把 `openapi_url` 设为 None，TestClient 对 `/docs`、`/openapi.json` 返回 404。

## 步骤 4 · 本仓库服务（空闲端口 8765）

8000 被占用，改用 `PORT=8765`、`EB_DB_PATH` 指向 work 目录、不设置 `ENVELOPE_HOST`。脚本：`E:\muse-bridge\work\TASK-042-envelope-budget\probe_server.py`。

```powershell
python E:\muse-bridge\work\TASK-042-envelope-budget\probe_server.py
```

输出片段（进程已退出；退出码 1 来自 Windows 上 `terminate()`，检查发生在退出之前）：

```text
GET / 200 text/html; charset=utf-8
BODY_HAS_TITLE True
BODY_SNIP <!DOCTYPE html> <html lang="zh-CN"> ...
GET /health 404 application/json {"detail":"Not Found"}
GET /api/health 404 application/json {"detail":"Not Found"}
GET /docs 404 application/json {"detail":"Not Found"}
GET /redoc 404 application/json {"detail":"Not Found"}
GET /openapi.json 404 application/json {"detail":"Not Found"}
GET /api/me 401 application/json {"detail":"未登录"}
NETSTAT
  TCP    127.0.0.1:8765         0.0.0.0:0              LISTENING       29352
INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
INFO:     127.0.0.1:58183 - "GET / HTTP/1.1" 200 OK
```

启动日志里有 `app.py:175` 的 `on_event` DeprecationWarning。结束后再查端口：8765 只剩 TIME_WAIT，没有 LISTENING。8000 仍是 pid 32492，未动那个进程。

耗时：pytest 输出自带 `3.21s`。pip、live_selftest、两次探针没有另计秒表，各自在单次命令内结束。

## 步骤 5 · 收尾重跑（未改源码）

```powershell
python -m pytest tests/ -q -p no:cacheprovider
```

```text
18 passed, 3 warnings in 2.35s
```

警告内容与步骤 2 相同（`on_event` 弃用，以及 TestClient/httpx 弃用）。

```powershell
python tests/live_selftest.py
```

```text
ALL LIVE SELF-TESTS PASSED
```

exit 0。

```powershell
git status --porcelain
```

exit 0，标准输出无行。仓库源码未改。

