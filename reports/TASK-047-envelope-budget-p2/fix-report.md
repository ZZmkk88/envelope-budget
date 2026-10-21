# TASK-047 修复记录

范围：上一轮 `E:\muse-bridge\out\TASK-030-envelope-budget\review.md` 的 P2。每条改完跑一次全量 pytest。解释器：`E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe`。工作目录：仓库根。

## P2-1

- 文件：`app.py:16` 增加 `from contextlib import asynccontextmanager`。`app.py:37-43` 用 `_lifespan` 在启动时调用 `init_db()`，`FastAPI(..., lifespan=_lifespan)`。删掉原来的 `@app.on_event("startup")`（改前在 `app.py:174-176`）。
- 改法：弃用的 startup 钩子换成 lifespan。启动时仍然只做 `init_db()`。
- 验证：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:53:23+08:00` → `2026-10-21T19:53:26+08:00`。

```
18 passed, 1 warning in 2.21s
```

`on_event` 警告没有了。剩下的是 `fastapi\testclient.py:1` 的 httpx 弃用警告。

## P2-2

- 文件：`README.md:14`。`NOTES.md:42`。
- 改法：待分配改成「全部账户期初 + 收入（月份 ≤ M）− 已分配（月份 ≤ M）」，并写明晚于 M 的不算。删掉「待分配 + Σ 全部信封剩余 = Σ 全部账户余额」和「测试有覆盖」，改写成「期初 + 收入（≤ M）− 支出（≤ M）」，并写明之后还有收支时不等于全部账户余额、测试没有断言这条关系。计算代码没动。
- 验证：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:53:42+08:00` → `2026-10-21T19:53:45+08:00`。

```
18 passed, 1 warning in 2.18s
```

## P2-3

- 文件：`static/index.html:286`。
- 改法：分配额输入框前加可见文字「本月分配」。`title` 仍是「本月分配（元）」。
- 验证：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:54:03+08:00` → `2026-10-21T19:54:07+08:00`。

```
18 passed, 1 warning in 2.48s
```

## P2-4

- 文件：`static/index.html:118` 增加 `<div id="income-cats">`。`static/index.html:268-278` 新增 `renderIncomeCategories()`，用已有的 `esc()` 输出名称，删除按钮调用已有的 `delCategory`，接口仍是 `DELETE /api/categories/{id}`。`static/index.html:281` 在 `renderBudgets()` 开头调用它，所以登录、加减类别、删类别之后都会刷新。
- 改法：收入类别在页面上列出并可以删。支出信封上的删除按钮不动。
- 验证：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:54:32+08:00` → `2026-10-21T19:54:34+08:00`。

```
18 passed, 1 warning in 2.17s
```

## P2-5

- 文件：`README.md:48`。
- 改法：默认库从 `data/budget.db` 改成 `app.py` 所在目录下的 `data/budget.db`，与 `app.py:23-24` 的 `Path(__file__).resolve().parent / "data" / "budget.db"` 一致。代码没动。
- 验证：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:54:50+08:00` → `2026-10-21T19:54:53+08:00`。

```
18 passed, 1 warning in 2.20s
```

## P2-6

不改。`app.py:189-204` 的 `current_user` 不检查 `must_change_password`。改密接口 `app.py:246` 也依赖它。未改密就拒绝，会让 `tests/test_app.py:85-91` 在仍须改密时无法改密。README 只要求提示，页面 `static/index.html:234` 已有 `alert`。未改代码，没有单独再跑测试。

## P2-7

不改。`tests/test_app.py:155-162` 没有先记账再断言删账户会级联删流水。本任务不许改 `tests/`。级联本身在 `app.py:137` 的 `ON DELETE CASCADE`。未改代码，没有单独再跑测试。

## P2-8

- 文件：`static/index.html:192-198` 新增 `localYmd()`，用 `getFullYear` / `getMonth` / `getDate`。`static/index.html:198` 月份、`static/index.html:240` 记账日期改走它。`toISOString()` 已从该文件去掉。
- 改法：月份和日期按本地日历拼，不再用 UTC。
- 验证：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:55:15+08:00` → `2026-10-21T19:55:18+08:00`。

```
18 passed, 1 warning in 2.28s
```

## P2-9

- 文件：`app.py:176-179`。在 `init_db()` 的 `conn.commit()` 之前删除 `expires_at <= time.time()` 的会话。
- 改法：启动走 lifespan，登录函数开头会调用 `init_db()`，两条路径都会清掉过期行。比较符用 `<=`，和 `current_user` 里 `expires_at > now` 才算有效一致。新登录插入会话发生在 `init_db()` 返回之后，不会被这次删除清掉。
- 验证：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:55:40+08:00` → `2026-10-21T19:55:44+08:00`。

```
18 passed, 1 warning in 2.77s
```

## P2-10

- 文件：`app.py:43-49`。`FastAPI(...)` 增加 `docs_url=None`、`redoc_url=None`、`openapi_url=None`。
- 改法：默认不再挂 `/docs`、`/redoc`、`/openapi.json`。已安装的 FastAPI 在 `openapi_url` 为空时不会注册这些路由（`fastapi\applications.py:1135-1173`）。
- 验证：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:56:10+08:00` → `2026-10-21T19:56:14+08:00`。

```
18 passed, 1 warning in 2.65s
```

另外用 TestClient 对临时库 `E:\muse-bridge\work\TASK-047-envelope-budget-p2\docs-check.db` 看了四个路径（脚本 `E:\muse-bridge\work\TASK-047-envelope-budget-p2\check_p2.py`，起止 `2026-10-21T19:56:40+08:00` → `2026-10-21T19:56:42+08:00`）：

```
GET / 200
GET /docs 404
GET /redoc 404
GET /openapi.json 404
expired_before 1
login 200
expired_after 0
unexpired_sessions 1
```

过期会话那三行是顺手核对 P2-9：先插入一条已过期 token，登录（会进 `init_db()`）后该行没了，新登录会话还在。

## P2-11

不改。`app.py:96-101` 的 PBKDF2-HMAC-SHA256 仍是 200_000 次。库里的密码哈希没有迭代次数版本，改次数会让已有库的密码全部对不上。未改代码，没有单独再跑测试。
