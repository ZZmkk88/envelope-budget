# envelope-budget · 信封账本

一句话定位：一个轻量、可自己部署的信封预算法记账工具——每月先把钱分进各个支出信封，花一笔扣一笔，没花完的自动结转下月。

本项目的设计学习了开源社区信封预算法工具的通行思路——如按月分配、余额结转、待分配金额这类核心概念；代码为独立实现。上游溯源与署名见 [UPSTREAM.md](UPSTREAM.md)，设计取舍见 [NOTES.md](NOTES.md)。

## 功能清单（与代码实现一一对应，均已测试覆盖）

- **登录**：单用户账号，Token 登录（24 小时有效），首次登录提示改密；内置默认支出/收入类别，开箱即用
- **账户**：新增 / 删除账户（带期初余额）；余额 = 期初 + 收入 − 支出，自动计算（删账户会连同其记账记录一并删除）
- **记账**：新增 / 编辑 / 删除一笔（日期、账户、类别、金额、备注；收入与支出分开，类别必须与收支类型匹配）
- **类别**：支出类别与收入类别可增删；已被记账记录使用的类别不能删除（防数据悬空）
- **月度信封预算**：按月给每个支出类别分配额度；每只信封显示「上月结转 / 本月分配 / 本月已花 / 剩余」，剩余为负（超支）也会如实结转下月
- **待分配**：看月份 M 时，还没分进信封的钱 = 全部账户期初 + 收入（月份 ≤ M）− 已分配（月份 ≤ M）。晚于 M 的收入和分配不算进去
- **月度报表**：某月总收入、总支出、结余，以及各支出类别的花费排行

金额一律用**整数分**存储与计算（界面上输入输出的是元），杜绝浮点误差。

## 安装与启动

需要 Python 3.10 或更高版本。

**Linux / macOS（bash）:**

```bash
cd envelope-budget
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py            # 默认监听 8000 端口
```

**Windows（PowerShell）:**

```powershell
cd envelope-budget
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py        # 默认监听 8000 端口
```

启动后打开 http://localhost:8000 ，默认账号 **admin / admin123**，首次登录会提示改密码。

可选环境变量：

| 变量 | 说明 | 默认 |
|---|---|---|
| `PORT` | 监听端口（Windows PowerShell 里用 `$env:PORT=8123` 设置） | 8000 |
| `EB_DB_PATH` | SQLite 数据库文件位置 | `app.py` 所在目录下的 `data/budget.db` |
| `EB_INITIAL_USERNAME` / `EB_INITIAL_PASSWORD` | 首次启动时创建的管理员账号（仅在数据库为空时生效） | admin / admin123 |

## 测试

先装开发依赖，再跑自动化测试与真实流程自测：

**Linux / macOS（bash）:**

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests/ -q
.venv/bin/python tests/live_selftest.py
```

**Windows（PowerShell）:**

```powershell
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest tests/ -q
.venv\Scripts\python tests/live_selftest.py
```

## 信封规则（一句话版）

某信封本月剩余 = 上月结转 + 本月分配 − 本月已花；其中上月结转就是上个月的剩余，正负都带过来。公式与实现细节见 [NOTES.md](NOTES.md)。
