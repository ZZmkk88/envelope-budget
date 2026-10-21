# envelope-budget 修复记录

只改 `review.md` 里的 P1-1、P1-2、P1-3。P0 无。P2 未动。

## P1-1 流水备注打穿 HTML

- 问题编号：P1-1
- 文件：`static/index.html:302`
- 改法：编辑按钮不再把 `JSON.stringify(t)` 拼进单引号 `onclick`。整段 JSON 先经已有的 `esc()` 放进 `data-tx`，点击时 `editTx(JSON.parse(this.dataset.tx))`。

验证 1，`verify_p1_1.py`（用含撇号和 `<img onerror>` 的备注做属性往返）：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe E:\muse-bridge\work\TASK-030-envelope-budget\verify_p1_1.py
```

```
old_pattern_present False
data_tx_present True
frag_has_raw_apostrophe_attr_break False
frag_has_raw_img_tag False
parsed_note mom's <img src=x onerror=alert(1)>
roundtrip_ok True
onclick editTx(JSON.parse(this.dataset.tx))
```

验证 2，全量 pytest：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe E:\muse-bridge\work\TASK-030-envelope-budget\run_pytest.py
```

```
18 passed, 3 warnings in 1.81s
```

页面没有自动化点击测试。这里用 HTML 解析确认属性不会被撇号截断，浏览器里没有点过「改」。

## P1-2 默认监听所有网卡

- 问题编号：P1-2
- 文件：`app.py:746`（改前是 `app.py:739`）
- 改法：`uvicorn.run` 的 `host` 从 `0.0.0.0` 改为 `127.0.0.1`。

验证 1，pytest：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe E:\muse-bridge\work\TASK-030-envelope-budget\run_pytest.py
```

```
18 passed, 3 warnings in 1.90s
```

验证 2，重新起服务（`serve_once.py`，`PORT=8000`，库在 work 目录）。日志：

```
pid 28140
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

`netstat -ano -p tcp | findstr :8000`：

```
TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING       28140
```

`probe_bind.py`：

```
http http://127.0.0.1:8000/ 200 <!DOCTYPE html> ...
http http://localhost:8000/ 200 <!DOCTYPE html> ...
tcp 100.69.58.124 TimeoutError
tcp 192.168.31.86 TimeoutError
```

本机 `localhost` 与 `127.0.0.1` 首页都是 200。netstat 只剩 `127.0.0.1:8000`。探测完已停掉 pid 28140。

## P1-3 改密废止其他会话

- 问题编号：P1-3
- 文件：`app.py:246` 增加 `request`；`app.py:252` 取出当前 token；`app.py:261-264` 删除该用户其余会话。
- 改法：密码更新成功后执行 `DELETE FROM sessions WHERE user_id = ? AND token != ?`。发出改密请求的那个 token 继续有效，其它 token 失效。

验证 1，`repro_after.py`（新库，登录两次再改密）：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe E:\muse-bridge\work\TASK-030-envelope-budget\repro_after.py
```

```
change 200
tokenA_after 200
tokenB_after 401
relogin 200 False
```

修复前同一检查是 `tokenB_after 200`（见 `run.md`）。现在另一个会话是 401，当前会话仍是 200，用新密码可以再登录，且 `must_change_password` 为 false。

验证 2，pytest：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe E:\muse-bridge\work\TASK-030-envelope-budget\run_pytest.py
```

```
18 passed, 3 warnings in 1.83s
```

## 全量重跑

三条都改完之后重跑 README 里的两步。pytest 仍有原来的 3 条弃用警告，没有失败。

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
PASS login (first-login change prompt flagged)
PASS create account, opening balance 2000.00
PASS salary in: 8888.88
PASS assigned 1000.00 to 餐饮, spent 234.56
PASS October envelope balance: 765.44, to_budget: 988888
PASS November carry-in rolls over: 765.44
PASS October report totals and ranking
ALL LIVE SELF-TESTS PASSED
```

没有失败项。P2 未改。测试文件、依赖版本、`LICENSE`、`UPSTREAM.md` 未改。

## git status

```
git -C E:\muse-bridge\in\TASK-030-envelope-budget status --porcelain
```

```
 M app.py
 M static/index.html
```
