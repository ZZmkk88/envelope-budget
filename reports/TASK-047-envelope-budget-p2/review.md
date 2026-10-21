# envelope-budget 第二轮（P2）

结论：本树基线 pytest `18 passed, 3 warnings in 2.37s`（Python 3.11.9，复用 `E:\muse-bridge\work\TASK-030-envelope-budget\venv`）。没有新的 P0。上一轮报告里的 11 条 P2 都还在。本轮按该报告的顺序处理，实际改 8 条：P2-1、P2-2、P2-3、P2-4、P2-5、P2-8、P2-9、P2-10。P2-6、P2-7、P2-11 不改，理由写在清单里。

本树仍能看到上一轮的 3 条 P1（备注打穿 HTML、监听 `0.0.0.0`、改密不废止其他会话）。任务书写明 P0/P1 上一轮已修、本轮只处理 P2，所以这 3 条不重复改。对照 `E:\muse-bridge\in\TASK-030-envelope-budget`：那边的 `app.py` 已是 `host="127.0.0.1"`，改密处有 `DELETE FROM sessions WHERE user_id = ? AND token != ?`，`static/index.html` 编辑按钮已改用 `data-tx`。本任务工作区是改之前的快照。

## 基线证据

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

```
18 passed, 3 warnings in 2.37s
```

`app.py:174` 的警告原文是 `DeprecationWarning: on_event is deprecated, use lifespan event handlers instead.` 另有 Starlette 提示 `httpx` 与 `TestClient` 的弃用，与业务无关。

## 上一轮 P1 在本树的位置（本轮不改）

1. `static/index.html:302` 仍是 `onclick='editTx(${JSON.stringify(t)})'`。备注列 `static/index.html:300` 用了 `esc()`，编辑按钮没有。
2. `app.py:739` 仍是 `uvicorn.run(app, host="0.0.0.0", port=...)`。
3. `app.py:254-258` 改密只更新 `password_hash` / `salt` / `must_change_password`。删会话只出现在登出 `app.py:238`。

## 分级修复清单

### P0

无。全量 pytest 18 项通过。

### P1

无本轮新增项。上面 3 条按任务书不重复修。

### P2

1. **P2-1 修** `app.py:174-176` `@app.on_event("startup")` 只调用 `init_db()`。修法：改成 lifespan，启动时仍只做 `init_db()`。
2. **P2-2 修** `README.md:14` 把待分配写成「全部期初 + 累计收入 − 累计已分配」，没有月份上界。实现是 `app.py:637-645`：收入 `substr(date, 1, 7) <= 所选月`，分配 `month <= 所选月`。`NOTES.md:42` 写「待分配 + Σ 全部信封剩余 = Σ 全部账户余额」且「测试有覆盖」。按公式，该和等于「期初 + 收入(≤M) − 支出(≤M)」，所选月之后还有收支时不等于全部账户余额；`tests/test_app.py` 里没有这条断言。修法：改这两处文档，计算不动。
3. **P2-3 修** `README.md:13` 要求信封显示「上月结转 / 本月分配 / 本月已花 / 剩余」。`static/index.html:281-284` 可见的是剩余、上月结转、本月已花。本月分配只在 `static/index.html:286` 输入框的 `title` 上。修法：给该输入一个可见的「本月分配」标签。
4. **P2-4 修** `README.md:12` 写收入类别可删。后端 `app.py:401` `DELETE /api/categories/{id}` 不区分收支。页面删除按钮只在支出信封上，`static/index.html:280`。收入类别只有新增框 `static/index.html:115-116`。修法：列出收入类别并给删除按钮，仍走现有接口。
5. **P2-5 修** `README.md:48` 默认库写 `data/budget.db`。`app.py:23-24` 是 `Path(__file__).resolve().parent / "data" / "budget.db"`，钉在 `app.py` 所在目录。修法：文档改成相对 `app.py` 所在目录。
6. **P2-6 不修** `app.py:189-204` `current_user` 不看 `must_change_password`。`README.md:9` 只要求首次登录提示改密，`static/index.html:234` 会 `alert`。改密接口自己也走 `current_user`（`app.py:246`）。未改密就 403 会让 `tests/test_app.py:85-91` 的改密请求失败，模块级 `auth` 夹具也无法再往下用。不改。
7. **P2-7 不修** `tests/test_app.py:155-162` 删账户前没有先记账，也就没有断言流水被级联删除。实现侧级联在 `app.py:137`。本任务不许改 `tests/`。不改。
8. **P2-8 修** `static/index.html:191` 与 `static/index.html:233` 用 `toISOString()` 取月份和日期，得到的是 UTC。东八区月初凌晨会落到上一月或上一天。修法：用本地年月日拼字符串。
9. **P2-9 修** 过期会话只在查询时比较。`app.py:197-199` 条件是 `expires_at > now`，没有删除。`app.py:105-108` 是表结构。修法：在 `init_db()` 提交前删掉 `expires_at <= now` 的行。启动（lifespan）和登录（`app.py:210` 会调用 `init_db()`）都会走到。
10. **P2-10 修** `app.py:36` `FastAPI(title="envelope-budget")` 使用库默认的文档地址。已安装的 `fastapi\applications.py:1135-1152`：`openapi_url` 非空时注册 `/openapi.json`，并在 `docs_url` 非空时注册 `/docs`。本轮没有再起服务探测。修法：`openapi_url=None`（文档字符串写明这会同时关掉 docs 与 redoc）。
11. **P2-11 不修** `app.py:86-89` PBKDF2-HMAC-SHA256 迭代 200_000 次。库里已有哈希没有版本字段，改次数会让旧密码全部验不过。不改。

本轮不动 `tests/`、`LICENSE`、`UPSTREAM.md`、`requirements.txt`、`requirements-dev.txt`。
