---
phase: 04-docs-config-test-audit
plan: 2
subsystem: audit-evidence
tags: [audit, coverage, pytest-cov, node-test, d-03, d-04]
requires: ["04-01(worktree 基线专区 wt-5927f36)"]
provides:
  - ".planning/audit/scans/coverage-pytest.md — Python 覆盖率归档(命令+版本+35 条模块级数字+口径备注)"
  - ".planning/audit/scans/coverage-node.md — JS 覆盖率归档(experimental 标注+20 条文件级数字+pages/ HYP-24 注记)"
affects: ["04-08(反向映射兜底证据与 F-TEST 证据字段;HYP-24 消费)", "04-09(HYP-24 消费)"]
tech-stack:
  added: []
  patterns: ["pytest-cov ephemeral --with 注入(D-03,零仓库写入)", "node 内置 experimental 覆盖率直跑(D-04,绕过 pytest 桥)", "worktree 基线专区用完即拆(D-02)"]
key-files:
  created:
    - .planning/audit/scans/coverage-pytest.md
    - .planning/audit/scans/coverage-node.md
  modified: []
decisions:
  - "A1 口径取定:--cov=fc_shared 包名形式对 pythonpath 导入包正常出数,无需回退路径形式 --cov=apps/fc/shared"
  - "AUDIT-04 不在本计划勾选:沿 04-01 决策,该需求由 04-01/02/06/07/08 五计划共担,留待阶段收尾统一销号"
  - "Task 1 包合法性检查点经用户批准(approved — 批准注入)后放行 pytest-cov 首次注入,批准记录写入 coverage-pytest.md 文件头"
metrics:
  duration: "~8 min"
  completed: 2026-07-05
status: complete
---

# Phase 4 Plan 2: 双语言覆盖率实测归档 Summary

**One-liner:** 在 04-01 建立的 worktree 基线专区内以 pytest-cov 临时注入(TOTAL 5064/1375/73%)与 node 内置 experimental 覆盖率(all files 92.73% line,126 用例全过)完成双语言覆盖率实测并同格式归档,pages/ 覆盖数据登记 HYP-24 证据指针,专区拆除无残留、主仓零 diff 零配置写入。

## 关键观测(只存档不判断)

| 观测项 | 结果 |
|--------|------|
| Task 1 检查点(pytest-cov 包合法性) | 用户人工核验 PyPI 归属 pytest-dev 后批准("approved — 批准注入") |
| A1 冒烟(test_sts.py --cov=fc_shared) | exit=0,34 passed,fc_shared 全部 9 模块出数——包名口径成立,无需回退 |
| Python 全量(--cov=soniscope_worker --cov=fc_shared) | collected 567 / 565 passed / 2 failed(与 04-01 同两条 SONISCOPE_HOME 环境依赖现象,照记);TOTAL 5064 Stmts / 1375 Miss / 73% |
| JS 全量(node --experimental-test-coverage) | 126 tests / 126 pass;all files 92.73% line / 75.80% branch / 84.13% funcs |
| pages/ 出现(HYP-24 证据点) | uploads.js 89.66% / index.js 87.94% / dev.js 95.00% 三个页面文件入覆盖面,指针已登记 |
| 测试文件排除(Pitfall 4) | `--test-coverage-exclude='apps/miniprogram/test/**'` 生效,报告 0 条 *.test.js 行 |
| 零配置写入(D-03) | 主仓 `git status --porcelain -- pyproject.toml uv.lock apps/worker/pyproject.toml` 空;专区 status 空 |
| 专区拆除(D-02) | `worktree remove --force` exit=0 + prune 兜底;`git worktree list` 无 wt-5927f36 残留 |
| 零 diff 快查 | `git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空,PASS |

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | pytest-cov 包合法性确认(checkpoint:human-verify) | (无——人工确认门,无文件产出;批准记录随 Task 2 归档入 coverage-pytest.md 文件头) | — |
| 2 | Python 覆盖率实测与归档(D-03) | e6550c1 | .planning/audit/scans/coverage-pytest.md |
| 3 | JS 覆盖率实测归档与专区拆除(D-04) | 330f9a8 | .planning/audit/scans/coverage-node.md |

## Deviations from Plan

None - plan executed exactly as written。补充说明两点(非偏差):

1. Task 1 为 blocking-human 检查点,由上一执行代理暂停等待,本代理在用户回复 "approved — 批准注入" 后接续;批准事实按计划 done 条件记入 coverage-pytest.md 文件头一句。
2. Python 全量实跑含 2 条 FAILED(SONISCOPE_HOME 未设置的环境依赖现象,与 04-01 gate-run-worktree.md 同两条)——覆盖率采集不受影响,数字照抄归档,定级判断留 04-08;无需偏差处理。

## 白名单合规声明

全程仅执行:`uv run --frozen --with pytest-cov pytest ...`(获批后)、`node --test --experimental-test-coverage ...`、版本查询命令(`uv --version`/`pytest --version`/`node --version`)、`git worktree remove --force`/`worktree list`/`worktree prune`、`git status`/`git diff` 只读观测。未执行任何 `make test-*`、`make verify-*`、被审脚本;pytest 全 fake 零云 IO(T-04-04 mitigation 落实)。pytest-cov 仅经 ephemeral `--with` 注入,零仓库配置写入(T-04-SC mitigation 落实);两份归档仅含覆盖数字与文件路径,无凭证内容(T-04-05 mitigation 落实)。

## Requirements

- AUDIT-04:本计划完成其"双语言覆盖率实测证据"部分(Python 模块级 35 行 + JS 文件级 20 行,均为纯输入证据);需求整体由 04-06/07/08 续接,不在此勾选(沿 04-01 决策)。

## Known Stubs

无——本计划为纯审计取证,不产出代码。

## Self-Check: PASSED

- coverage-pytest.md 存在 ✓(提交 e6550c1 在 git 历史 ✓)
- coverage-node.md 存在 ✓(提交 330f9a8 在 git 历史 ✓)
- `git worktree list` 无 wt-5927f36 残留 ✓
- 零 diff / 零配置写入核查通过 ✓
