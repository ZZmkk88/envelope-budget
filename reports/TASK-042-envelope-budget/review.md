# envelope-budget 验收

结论：依赖按锁定版本能装上，自动化测试 18 项通过，真实进程自测通过，服务默认只听 `127.0.0.1`。首页返回 200 且含「信封账本」。没有 `/health`。未发现跑不起来的问题，也未发现可利用的越权或账目算错。本次不改源码。

未在浏览器里点界面（本环境没有浏览器工具）。界面结论来自读 `static/index.html`，账户/记账/信封流程来自 API 与 `tests/live_selftest.py`。

## 本地跑通记录

解释器：Python 3.11.9，`E:\muse-bridge\env\TASK-042-envelope-budget\Scripts\python.exe`（任务预置虚拟环境，不在仓库里）。`py -3` 不可用。README 要求 3.10+，这一条满足。

```text
python -m pip install -r requirements.txt
Successfully installed ... fastapi-0.156.7 ... starlette-1.9.0 ... uvicorn-0.54.0
python -m pip install -r requirements-dev.txt
Successfully installed ... httpx-0.28.1 ... pytest-9.1.1
```

```text
python -m pytest tests/ -q -p no:cacheprovider
18 passed, 3 warnings in 3.21s
```

三条警告：`app.py:175` `on_event` 已弃用；Starlette 提示 TestClient 所用 `httpx` 已弃用、要换 `httpx2`。都没有让测试失败。

`tests/live_selftest.py` 不是 pytest 用例。按 README 执行 `python tests/live_selftest.py`，exit 0：

```text
PASS login (first-login change prompt flagged)
PASS October envelope balance: 765.44, to_budget: 988888
PASS November carry-in rolls over: 765.44
ALL LIVE SELF-TESTS PASSED
```

`to_budget: 988888` = 期初 200000 + 收入 888888 − 分配 100000，与 `app.py:662` 一致。

8000 端口当时已被 pid 32492 占用，OpenAPI 标题是 `freshfeeds`。那次连 8000 的响应不算本仓库。本仓库用 `PORT=8765` 另起一次（`EB_DB_PATH` 在 `E:\muse-bridge\work\TASK-042-envelope-budget`，未设置 `ENVELOPE_HOST`）：

```text
INFO:     Uvicorn running on http://127.0.0.1:8765
GET /            200  text/html  正文含「信封账本」
GET /health      404
GET /api/health  404
GET /docs        404
GET /openapi.json 404
GET /api/me      401  {"detail":"未登录"}
NETSTAT  TCP  127.0.0.1:8765  LISTENING
```

查完已关掉。8765 不再 LISTENING。8000 上的进程没有动。

额外探针（`probe_logic.py`，TestClient，数据库在 work 目录）结果：`PRAGMA foreign_keys=1`；删除账户后对应流水剩余 0 行；2025-12 分配 5000、支出 1200，2026-01 结转 3800；2026-12 的收入 9999 不改变 2026-08 的待分配（-5000 保持不变，12 月变为 4999）；删除只有预算、没有流水的类别后，预算行消失，待分配回到删除前。直接往库里插入的第二个用户 bob：账户列表为 `[]`，删别人的账户 404，用别人的账户记账 400「账户不存在」，给别人的类别分配 404。改密后当前 token 仍有效，另一枚 token 401。

## README 与实际不符处

1. `README.md:7` 写「功能清单……均已测试覆盖」。24 小时过期在 `app.py:25` 与 `app.py:222`，`tests/test_app.py` 全文没有对 `expires_at` / TTL 的断言。删账户连同流水删除写在 `README.md:10`，实现是 `app.py:138` 的 `ON DELETE CASCADE`（探针确认剩余流水为 0），但 `tests/test_app.py:155-162` 只断言账户 id 消失，没有断言流水被删。
2. `README.md:12` 写支出类别与收入类别都可增删。删除接口 `app.py:411` 对两种类别都开放，页面只在支出信封上放了删除按钮（`static/index.html:285`）。收入类别只有新增输入框（`static/index.html:115-116`），没有删除入口。
3. `README.md:13` 写每只信封显示「上月结转 / 本月分配 / 本月已花 / 剩余」。页面有剩余、上月结转、本月已花（`static/index.html:286-288`）。「本月分配」只出现在输入框的 `title`（`static/index.html:291`），没有与另外三项并列的可见文字。
4. `README.md:14` 写待分配 = 全部期初 + 累计收入 − 累计已分配，没有月份上界。代码是期初全额 + 收入月份 `<=` 所选月 − 分配月份 `<=` 所选月（`app.py:643-662`）。探针：2026-12 的收入不进入 2026-08 的待分配。`NOTES.md:40` 写了这个上界，与 README 这句话不一致。
5. `README.md:68-69` 让人直接跑 `tests/live_selftest.py`，没有写它固定占用 `8237`（`tests/live_selftest.py:17-18`）。端口被占时该命令会失败。

抽查过且与 README 一致的部分：Token 24 小时（`app.py:25`）、默认账号 admin / admin123 且仅空库生效（`app.py:26-27`、`app.py:148-155`）、余额 = 期初 + 收入 − 支出（`app.py:305`）、整数分（`app.py:442` 与界面 `yuanToCents`）、默认监听 `127.0.0.1` 与 `PORT`（`app.py:750-751`）、信封剩余 = 结转 + 本月分配 − 本月已花（`app.py:625-634`，负结转有测试 `tests/test_app.py:244-255`）。

## 许可证与署名核查

仓库内部是自洽的，上游两行事实本次未核实。

- `LICENSE:1-3`：MIT，版权人 “Copyright (c) 2026 envelope-budget contributors”。
- `UPSTREAM.md:5-8`：上游标为 `https://github.com/actualbudget/actual`，commit `d2dae07f5630dc191aa74aba6b88e243cce39193`，许可证 MIT，署名 “Copyright James Long”。
- `UPSTREAM.md:16-20` 与 `README.md:5`、`app.py:3` 都声明代码是独立重写，未复制上游源码。阅读 `app.py` 与 `static/index.html`，实现是 FastAPI + SQLite + 单页，没有成段的上游源码。本项目版权行与上游署名指向不同作品，这样写不冲突。
- 任务禁止抓取外部页面，没有打开 GitHub 核对上述 commit 是否为 2026-10-21 的默认分支 HEAD，也没有核对上游 `LICENSE.txt` 首行是否真是无年份的 “Copyright James Long”。这两句保持原样，不改 `LICENSE` 与 `UPSTREAM.md`。

## 分级修复清单

### P0

无。pytest 18 passed；`live_selftest` 通过；`127.0.0.1:8765` 能启动并返回首页 200。8000 被别的进程占用，记为环境限制，不记本仓库缺陷。

### P1

无。第二用户读不到、删不掉、记不进别人的账户和类别；外键打开且删账户会删流水；删空类别会把预算一并删掉并退回待分配；交互式文档关闭；默认绑定地址是 `127.0.0.1`。

### P2

1. `README.md:7` 测试覆盖说满了。修法：改掉「均已测试覆盖」，或在允许改测试的轮次补上 TTL 与删账户级联断言。本次不改测试。
2. `README.md:12`、`static/index.html:115-116`。收入类别在页面上不能删。修法：给收入类别加删除按钮，走已有的 `DELETE /api/categories/{id}`。`DECISIONS.md:24` 已把这类按钮问题标成暂缓。
3. `README.md:13`、`static/index.html:291`。本月分配没有可见标签。修法：信封卡片加一行「本月分配」，或给输入框加可见 label。
4. `README.md:14`、`app.py:650-662`。待分配的月份上界只写在 `NOTES.md:40`。修法：README 补上「截至所选月份（含当月）」。计算与 NOTES 一致，不改代码。
5. `README.md:68-69`、`tests/live_selftest.py:17`。自测固定端口未写入 README。修法：README 加一句「live_selftest 占用 8237」。
6. `app.py:175`。`on_event("startup")` 在当前 FastAPI 下打弃用警告，测试仍通过。修法：改成 lifespan，启动时仍调用 `init_db()`。`DECISIONS.md:21` 写明暂缓。
7. `NOTES.md:42`。它写待分配 + 全部信封剩余 = 全部账户余额，且「测试有覆盖」。按 `app.py:643-662` 与 `app.py:291-305`，账户余额含全部月份，待分配和信封只算到所选月；存在更晚的流水时等式不成立。`tests/test_app.py` 没有这条断言。修法：NOTES 改成「没有晚于所选月的流水时才成立」，并删掉「测试有覆盖」。
8. `app.py:190-206` 不看 `must_change_password`，首次登录只在 `static/index.html:239` `alert`。`DECISIONS.md:11-13` 明确保持这样。修法若要收紧：除改密、`/api/me`、登出外拒绝业务接口。本次按已记录的决定不改。
9. `requirements-dev.txt:2` 的 `httpx==0.28.1` 触发 Starlette 弃用警告。修法：等 TestClient 与 httpx2 的组合可用再动版本。本次不改版本号。
10. 没有健康检查路由（`/health`、`/api/health` 均为 404）。README 未承诺该路径。修法：若运维需要，加一个不带账本数据的 `GET /health`。本次不加。
