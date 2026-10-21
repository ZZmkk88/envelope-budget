# 上游溯源（UPSTREAM）

本项目在设计上学习了开源信封预算法工具的设计思路。按接力规范记录上游信息如下：

- **source_url**: https://github.com/actualbudget/actual
- **source_commit**: d2dae07f5630dc191aa74aba6b88e243cce39193
- **license**: MIT
- **attribution**: Copyright James Long

## 说明

- `source_commit` 是 2026-10-21 通过 GitHub 接口实查的上游默认分支 HEAD 提交
  （提交时间 2026-10-21）；当日设计调研通读的上游材料正是这一提交，包括
  仓库 README、`LICENSE.txt`，以及 `packages/loot-core/src/shared/util.ts`
  中的金额换算实现。
- `attribution` 的版权行逐字复制自上游仓库 `LICENSE.txt` 原文第一行，未做
  任何改动（上游 LICENSE.txt 开头即为 "Copyright James Long"，无年份）。
- 本项目代码为独立重写，未复制上游源码；借鉴的是信封预算法的核心概念
  （按月给类别分配、类别余额跨月累计结转、待分配金额），具体取舍见
  NOTES.md 的调研笔记。
