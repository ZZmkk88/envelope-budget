# envelope-budget 验收

结论：仓库能在本机跑通。pytest `18 passed`，`tests/live_selftest.py` 全过，`GET /` 返回 200。没有 P0。P1 有 3 条：流水备注可打穿页面、进程监听 `0.0.0.0`、改密不废止其他登录。许可证文本与仓库内署名互相一致；上游 commit 和上游 LICENSE 原文这次没有联网核对。

工作目录 `E:\muse-bridge\in\TASK-030-envelope-budget`。Python 3.11.9。虚拟环境在 `E:\muse-bridge\work\TASK-030-envelope-budget\venv`（不放进仓库）。

## 本地跑通记录

安装（`requirements-dev.txt` 已包含 `-r requirements.txt`）：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

exit 0。末尾：`Successfully installed ... fastapi-0.156.7 ... httpx-0.28.1 ... pytest-9.1.1 ... uvicorn-0.54.0`。

自动化测试（仓库根目录）：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

```
18 passed, 3 warnings in 2.06s
```

警告原文要点：`app.py:174 DeprecationWarning: on_event is deprecated, use lifespan event handlers instead.`；`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 测试是通过的。

真实流程自测：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe tests\live_selftest.py
```

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

起服务：`serve_once.py` 把数据库放到 work 目录，`PORT=8000`。日志：

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

`netstat -ano -p tcp`：

```
TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       30516
```

urllib 探测：

```
GET / 200 text/html; charset=utf-8
<title>envelope-budget · 信封账本</title>
GET /health HTTP 404 {"detail":"Not Found"}
GET /api/health HTTP 404 {"detail":"Not Found"}
GET /api/me HTTP 401 {"detail":"未登录"}
POST /api/login 200 {"username":"admin","must_change_password":true}
```

首页正常。README 没有健康检查路径，`/health` 与 `/api/health` 均为 404，记在这里，不单列成缺陷。探测结束后已停掉 pid 30516。复查：`PORT8000 closed TimeoutError`。

改密取证（修复前，`repro_before.py`）：同一数据库登录两次，用 token A 改密成功（200）后，token A 与 token B 访问 `/api/me` 都是 200。

## README 与实际不符处

1. `README.md:41` 写打开 `http://localhost:8000`。`app.py:739` 是 `uvicorn.run(app, host="0.0.0.0", port=...)`。启动日志和 netstat 都是 `0.0.0.0:8000`，局域网网卡也能连上。同条见 P1-2。

2. `README.md:14` 写待分配 = 全部期初 + 累计收入 − 累计已分配，没有月份上界。`app.py:637-645` 的收入是 `substr(date, 1, 7) <= 所选月`，分配是 `month <= 所选月`。看历史月份时，之后的收入不进待分配。`repro_before.py`：2026-10 的待分配 12000、信封剩余合计 2000，相加 14000；账户余额合计 22000（多出的 8000 是 2026-12 的收入）。

3. `README.md:13` 写每只信封显示「上月结转 / 本月分配 / 本月已花 / 剩余」。`static/index.html:281-284` 的可见文字是剩余、上月结转、本月已花。本月分配额在 `static/index.html:286` 的输入框里，标签只有 `title="本月分配（元）"`。

4. `README.md:12` 写支出类别与收入类别可增删。后端 `app.py:401` 的 `DELETE /api/categories/{id}` 两种都收。页面上的删除按钮只在支出信封卡上，`static/index.html:280`。收入类别能加（`static/index.html:115-116`），界面上删不掉。

5. `README.md:48` 默认数据库写 `data/budget.db`。`app.py:24` 默认是 `Path(__file__).parent / "data" / "budget.db"`，钉在 `app.py` 所在目录。按 README 先 `cd` 到项目目录再启动时，两个路径重合；从别的目录直接跑 `app.py` 时，库不在当前目录的 `data\` 下。

6. `README.md:7` 写功能「均已测试覆盖」。`README.md:10` 的「删账户会连同记账记录一并删除」在 `tests/test_app.py:155-162` 里只断言账户消失，没有先记账再断言流水被删。实现本身在 `app.py:137`（`accounts` 上 `ON DELETE CASCADE`）。

附 `NOTES.md`（不是 README 正文）：`NOTES.md:42` 写「待分配 + Σ 全部信封剩余 = Σ 全部账户余额」，并写测试有覆盖。`tests/test_app.py` 里没有这条断言。上面第 2 条的数字说明，只要所选月之后还有收支，这个等式不成立。`NOTES.md:37-40` 的分月公式和 `app.py:578-652` 一致。

## 许可证与署名核查

仓库内几份声明对得上，没有改 `LICENSE` 或 `UPSTREAM.md`。

- `LICENSE:1-5`：MIT，版权行 `Copyright (c) 2026 envelope-budget contributors`。
- `UPSTREAM.md:5-8`：上游 `https://github.com/actualbudget/actual`，commit `d2dae07f5630dc191aa74aba6b88e243cce39193`，许可证 MIT，署名 `Copyright James Long`。
- `UPSTREAM.md:18-20` 与 `README.md:5`、`app.py:3` 都写本仓库是独立实现，没有复制上游源码。本仓库是单个 Python 文件加一个静态页，结构上不是上游的 TypeScript `loot-core`。
- `NOTES.md:3` 的短 commit `d2dae07f` 与 `UPSTREAM.md:6` 的全长哈希前缀相同。
- 本仓库 `LICENSE` 署的是 2026 年本项目贡献者，上游署名放在 `UPSTREAM.md`。在「没有复制源码」这个前提下，两份文件不互相打架：MIT 要求保留的是被复制的那份版权声明。

本次按任务要求没有访问 GitHub。`UPSTREAM.md:12-17` 里的三件事都没有当场复核：commit 是否为 2026-10-21 的默认分支 HEAD、上游 `LICENSE.txt` 第一行是否逐字就是 `Copyright James Long`、`packages/loot-core/src/shared/util.ts` 里是否有 `amountToInteger`。这三句保持原样，不改。

## 分级修复清单

### P0

无。pytest 18 项通过，live_selftest 通过，首页 200，服务能起能停。`on_event` 只是弃用警告，当前 pin 的 FastAPI 0.156.7 仍会执行启动逻辑。

### P1

1. **P1-1** 流水备注会打穿本月流水的 HTML。`static/index.html:302` 把 `JSON.stringify(t)` 拼进单引号 `onclick='editTx(...)'`。备注里的 `'` 会截断属性，后续字符按 HTML 解析，可以插事件。备注正文那一列用了 `esc()`（`static/index.html:300`），编辑按钮没有。修法：JSON 放进经 `esc()` 的 `data-tx`，点击时 `JSON.parse(this.dataset.tx)`。

2. **P1-2** 记账服务默认绑在所有网卡上，同时默认口令是 README 公开的 `admin / admin123`（`README.md:41`，`app.py:26-27`）。`app.py:739`。证据：日志 `Uvicorn running on http://0.0.0.0:8000`，netstat `0.0.0.0:8000 LISTENING`，登录返回 `must_change_password: true`。修法：`host` 改为 `127.0.0.1`。

3. **P1-3** 改密后，其他已发出的 token 仍然有效。`app.py:245-259` 只更新 `password_hash` / `salt` / `must_change_password`，不删 `sessions`。证据：`repro_before.py` 里 `tokenB_after 200`。修法：改密成功时删掉该用户除当前 token 以外的会话。当前这次请求的 token 保留，`tests/test_app.py:33-36` 的模块级 `auth` 在 `test_change_password` 之后还要用它。

### P2

1. `app.py:174` 使用已弃用的 `@app.on_event("startup")`。当前能跑。修法：改成 lifespan，行为保持「启动时 `init_db()`」。
2. `README.md:14` 的待分配公式没写月份上界，与 `app.py:637-645` 不一致。`NOTES.md:42` 的恒等不成立，也没有测试。修法：改文档，公式与 `NOTES.md:40` 对齐，并删掉或改写那句恒等。不改计算，现有测试按分月公式写的。
3. `README.md:13` 与 `static/index.html:281-286`：补一个可见的「本月分配」标签。
4. `README.md:12` 与 `static/index.html:280`：收入类别在界面上不能删。修法：给收入类别加删除按钮，继续走现有 `DELETE /api/categories/{id}`。
5. `README.md:48` 与 `app.py:24`：把默认库路径的说明写成「相对 `app.py` 所在目录」。
6. `app.py:189-204` 的 `current_user` 不看 `must_change_password`。README 只要求提示，`static/index.html:234` 会 `alert`。服务端若改成未改密就 403，单独跑 `test_account_balance` 这类用例会失败（它们只登录、不改密）。这次不改。
7. `tests/test_app.py:155-162` 没有覆盖「删账户连同流水」。修法：补测试。本次不许改测试文件，所以不动。
8. `static/index.html:191` 和 `static/index.html:233` 用 `toISOString()` 取月份和日期，是 UTC。东八区月初凌晨会落到上一月或上一天。修法：用本地年月日拼字符串。
9. 过期会话没有清理（`app.py:105-108` 只在查询时比较 `expires_at`）。修法：登录或启动时删掉过期行。
10. `/docs` 与 `/openapi.json` 不需要登录（探测均为 200）。修法：生产默认关掉 `docs_url`，或加上鉴权。
11. `app.py:86-89` 的 PBKDF2-HMAC-SHA256 是 200_000 次。这次不改迭代次数，避免和已经生成的库不兼容，也避免顺手改参数。

本次只改 P1-1、P1-2、P1-3。共 3 项，涉及 `static/index.html` 与 `app.py`。
