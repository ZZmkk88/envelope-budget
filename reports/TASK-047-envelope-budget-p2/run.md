# TASK-047 envelope-budget P2 执行记录

开工：2026-10-21。工作目录 `E:\muse-bridge\in\TASK-047-envelope-budget-p2`。先只读上一轮报告 `E:\muse-bridge\out\TASK-030-envelope-budget\review.md`，再核对源码与测试。

## 环境

未新建虚拟环境，也未执行 pip。解释器用已有 `E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe`。

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe --version
```

```
Python 3.11.9
```

## 基线全量 pytest

工作目录：仓库根。起止 `2026-10-21T19:51:35+08:00` → `2026-10-21T19:51:38+08:00`。

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

```
18 passed, 3 warnings in 2.37s
```

警告三处：`app.py:174` `on_event` 弃用；`fastapi\applications.py:4723` 同一弃用；`fastapi\testclient.py:1` 建议改用 httpx2。测试通过。

## P2-1 之后

改 `app.py` 的 startup 为 lifespan 后：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:53:23+08:00` → `2026-10-21T19:53:26+08:00`。

```
18 passed, 1 warning in 2.21s
```

只剩 `fastapi\testclient.py:1` 的 httpx 弃用警告。

## P2-2 之后

改 `README.md:14` 与 `NOTES.md:42` 后：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:53:42+08:00` → `2026-10-21T19:53:45+08:00`。

```
18 passed, 1 warning in 2.18s
```

## P2-3 之后

`static/index.html` 补上「本月分配」可见标签后：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:54:03+08:00` → `2026-10-21T19:54:07+08:00`。

```
18 passed, 1 warning in 2.48s
```

## P2-4 之后

收入类别删除按钮加入 `static/index.html` 后：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:54:32+08:00` → `2026-10-21T19:54:34+08:00`。

```
18 passed, 1 warning in 2.17s
```

## P2-5 之后

`README.md:48` 改默认库路径说明后：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:54:50+08:00` → `2026-10-21T19:54:53+08:00`。

```
18 passed, 1 warning in 2.20s
```

## P2-6、P2-7

这两条按审查结论不改代码，没有单独再跑测试。

## P2-8 之后

`static/index.html` 改用本地年月日后：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:55:15+08:00` → `2026-10-21T19:55:18+08:00`。

```
18 passed, 1 warning in 2.28s
```

## P2-9 之后

`init_db()` 增加过期会话删除后：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:55:40+08:00` → `2026-10-21T19:55:44+08:00`。

```
18 passed, 1 warning in 2.77s
```

## P2-10 之后

`app.py` 关掉文档路由后：

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe -m pytest tests/ -q
```

起止 `2026-10-21T19:56:10+08:00` → `2026-10-21T19:56:14+08:00`。

```
18 passed, 1 warning in 2.65s
```

## 文档路由与过期会话抽查

```
E:\muse-bridge\work\TASK-030-envelope-budget\venv\Scripts\python.exe E:\muse-bridge\work\TASK-047-envelope-budget-p2\check_p2.py
```

起止 `2026-10-21T19:56:40+08:00` → `2026-10-21T19:56:42+08:00`。数据库在 work 目录，没有写进仓库。

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

## P2-11

不改 PBKDF2 迭代次数。未改代码，没有单独再跑测试。
