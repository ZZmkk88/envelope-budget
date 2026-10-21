# envelope-budget 修复记录

结论：`review.md` 分级清单里 P0 为零、P1 为零。按任务边界只修这两级，且最多 5 项。本次没有改仓库源码，也没有改测试、依赖版本、LICENSE、UPSTREAM。

P2 十条都未改。原因：不是阻断，也不是已经证实的越权或账目错误。其中第 6、8 条 `DECISIONS.md` 已写明暂缓；第 9 条会改动 `requirements-dev.txt` 里的版本号，当前测试是通过的。

下面是清单对应关系（无代码 diff）：

| 编号 | 文件:行号 | 改法 | 本次 |
|---|---|---|---|
| P0 | 无 | 无 | 不改 |
| P1 | 无 | 无 | 不改 |
| P2-1 | `README.md:7` | 收窄「均已测试覆盖」或补测试 | 不改（且不许改测试） |
| P2-2 | `static/index.html:115-116` | 收入类别加删除按钮 | 不改 |
| P2-3 | `static/index.html:291` | 给本月分配加可见标签 | 不改 |
| P2-4 | `README.md:14` | 补上待分配的月份上界 | 不改 |
| P2-5 | `README.md:68-69` | 写明 live_selftest 端口 8237 | 不改 |
| P2-6 | `app.py:175` | `on_event` 改为 lifespan | 不改 |
| P2-7 | `NOTES.md:42` | 恒等关系加上月份条件 | 不改 |
| P2-8 | `app.py:190-206` | 强制改密会改变已记录的产品决定 | 不改 |
| P2-9 | `requirements-dev.txt:2` | 更换 httpx 版本 | 不改 |
| P2-10 | 无对应路由 | 新增 `/health` | 不改 |

## 收尾全量测试

未改源码之后重跑。两条都是 exit 0。失败项：无。

```powershell
python -m pytest tests/ -q -p no:cacheprovider
```

```text
..................                                                       [100%]
app.py:175
  DeprecationWarning: on_event is deprecated, use lifespan event handlers instead.
    @app.on_event("startup")
fastapi\applications.py:4723
  DeprecationWarning: on_event is deprecated, use lifespan event handlers instead.
fastapi\testclient.py:1
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
18 passed, 3 warnings in 2.35s
```

```powershell
python tests/live_selftest.py
```

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

警告仍在，测试结果是通过。没有为消警告去改 `app.py` 或依赖版本。

## git status --porcelain

在仓库根目录执行。exit 0。标准输出没有任何行（工作区相对 HEAD 没有改动）。

```powershell
git status --porcelain
```

```text

```

输出为空是因为本次没有改仓库文件：P0/P1 清单为空，P2 按边界留下。验收正文在 `E:\muse-bridge\out\TASK-042-envelope-budget\`，不在这个 git 仓库里。
