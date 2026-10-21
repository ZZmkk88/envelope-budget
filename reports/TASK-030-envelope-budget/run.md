# TASK-030 envelope-budget 执行记录

开工：2026-10-21。执行方 Grok Build。工作目录 `E:\muse-bridge\in\TASK-030-envelope-budget`。先读仓库再装环境、跑测试。

## 环境

命令：`python --version`

```
Python 3.11.9
```

满足 README「Python 3.10 或更高版本」。仓库是 git 工作区，开工时 `git status --porcelain` 为空。`.gitignore` 忽略 `.venv/`、`__pycache__/`、`*.db`、`data/`。

虚拟环境不放进仓库，改放到 `E:\muse-bridge\work\TASK-030-envelope-budget\venv`（任务要求临时文件进 work 目录）。数据库与测试临时目录也放这里，避免在仓库里生成 `data/budget.db`。

## 安装依赖

命令（在仓库目录，使用 work 下的 venv；README 写的是仓库内 `.venv`，路径不同，原因见上）：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` 含 `-r requirements.txt`，一次装齐运行与测试依赖。

结果：exit 0。装上 fastapi==0.156.7、uvicorn==0.54.0、httpx==0.28.1、pytest==9.1.1 及传递依赖（starlette 1.9.0、pydantic 2.14.1 等）。末行：`Successfully installed ... fastapi-0.156.7 ... pytest-9.1.1 ... uvicorn-0.54.0`。

## 自动化测试

命令（工作目录为仓库；`TEMP`/`TMP` 指到 work 目录，让测试里的 `tempfile.mkdtemp` 不落系统 TEMP）：

```
Set-Location E:\muse-bridge\in\TASK-030-envelope-budget
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

结果：exit 0。`18 passed, 3 warnings in 2.06s`。

警告原文要点：

- `app.py:174` `DeprecationWarning: on_event is deprecated, use lifespan event handlers instead.`
- `fastapi/testclient.py:1` `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`

测试本身全绿。`on_event` 仍能跑，只是弃用警告。

## 真实流程自测 live_selftest

命令：

```
Set-Location E:\muse-bridge\in\TASK-030-envelope-budget
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe tests\live_selftest.py
```

结果：exit 0。输出：

```
PASS login (first-login change prompt flagged)
PASS create account, opening balance 2000.00
PASS salary in: 8888.88
PASS assigned 1000.00 to 餐饮, spent 234.56
PASS October envelope balance: 765.44, to_budget: 988888
PASS November carry-in rolls over: 765.44
PASS October report totals and ranking
ALL LIVE SELF-TESTS PASSED
```

脚本自带耗时未打印。它会另起一个进程，监听 8237，数据库在 `tempfile.mkdtemp`（系统 TEMP）。

## 起服务并探测

数据库放到 work 目录，避免在仓库里生成 `data/budget.db`。启动脚本：`E:\muse-bridge\work\TASK-030-envelope-budget\serve_once.py`（设置 `EB_DB_PATH` 与 `PORT=8000` 后执行 `app.py`）。

命令：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe E:\muse-bridge\work\TASK-030-envelope-budget\serve_once.py
```

启动日志片段：

```
pid 30516
app.py:174: DeprecationWarning: on_event is deprecated, use lifespan event handlers instead.
INFO:     Started server process [30516]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

`netstat -ano -p tcp` 中与本进程相关的一行：

```
TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       30516
```

探测脚本 `probe_once.py`（urllib，未用 curl）输出：

```
GET / 200 text/html; charset=utf-8
<!DOCTYPE html> ... <title>envelope-budget · 信封账本</title> ...
GET /health HTTP 404 application/json
{"detail":"Not Found"}
GET /api/health HTTP 404 application/json
{"detail":"Not Found"}
GET /docs 200 text/html; charset=utf-8
GET /openapi.json 200 application/json
{"openapi":"3.1.0","info":{"title":"envelope-budget","version":"0.1.0"},...
GET /api/me HTTP 401 application/json
{"detail":"未登录"}
POST /api/login 200 application/json
{"token":"(已截断)","username":"admin","must_change_password":true}
```

首页 200，未登录接口 401，默认账号可以登录。README 没有 `/health`，`/health` 与 `/api/health` 都是 404。

关掉服务：停止上面的后台进程（pid 30516）。随后 `repro_before.py` 对 8000 端口做了连接，结果 `PORT8000 closed TimeoutError`。

## 改密会话与待分配恒等（修复前取证）

命令：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe E:\muse-bridge\work\TASK-030-envelope-budget\repro_before.py
```

输出：

```
PORT8000 closed TimeoutError
change 200
tokenA_after 200
tokenB_after 200
to_budget 12000
envelope_sum 2000
to_budget_plus_envelopes 14000
account_sum 22000
identity_holds False
```

两个 token 都登录成功。用 token A 把密码从 `admin123` 改成 `newpass456` 之后，token B 访问 `/api/me` 仍是 200。另：10 月待分配 12000、信封剩余合计 2000，两者相加 14000；账户余额合计 22000（多出来的 8000 是 12 月的收入）。NOTES.md 写的恒等在这个数据上不成立。

## 修复后的验证

P1-1 之后：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe E:\muse-bridge\work\TASK-030-envelope-budget\verify_p1_1.py
```

```
old_pattern_present False
data_tx_present True
roundtrip_ok True
```

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe E:\muse-bridge\work\TASK-030-envelope-budget\run_pytest.py
```

```
18 passed, 3 warnings in 1.81s
```

P1-2 之后，pytest：`18 passed, 3 warnings in 1.90s`。再起服务，日志 `Uvicorn running on http://127.0.0.1:8000`。`netstat -ano -p tcp | findstr :8000` 得到 `TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING       28140`。`probe_bind.py` 对 `http://127.0.0.1:8000/` 与 `http://localhost:8000/` 都是 200。随后停掉 pid 28140。

P1-3 之后：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe E:\muse-bridge\work\TASK-030-envelope-budget\repro_after.py
```

```
change 200
tokenA_after 200
tokenB_after 401
relogin 200 False
```

pytest：`18 passed, 3 warnings in 1.83s`。

全量收尾：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe E:\muse-bridge\work\TASK-030-envelope-budget\run_pytest.py
```

```
18 passed, 3 warnings in 1.84s
```

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe E:\muse-bridge\work\TASK-030-envelope-budget\run_live.py
```

```
ALL LIVE SELF-TESTS PASSED
```

`git status --porcelain`：

```
 M app.py
 M static/index.html
```
