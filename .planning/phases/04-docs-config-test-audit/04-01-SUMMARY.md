---
phase: 04-docs-config-test-audit
plan: 1
subsystem: audit-evidence
tags: [audit, gate, worktree, pytest, d-11]
requires: []
provides:
  - ".planning/audit/scans/gate-run-worktree.md — 离线门禁基线实跑归档(D-11 实跑观测方)"
  - "仓库外 worktree 基线专区 wt-5927f36(存续,供 04-02 覆盖率实测复用)"
affects: ["04-02(专区复用)", "04-08(D-11 三方对照)"]
tech-stack:
  added: []
  patterns: ["worktree 基线专区实跑(D-02)", "uv --frozen 钉版执行(Pitfall 2)", "受控反事实观测(Pitfall 5)"]
key-files:
  created:
    - .planning/audit/scans/gate-run-worktree.md
  modified: []
decisions:
  - "AUDIT-04 不在本计划勾选:该需求由 04-01/02/06/07/08 五计划共担,留待阶段收尾统一销号"
  - "make test 非绿(2 failed)按 CONTEXT 裁量条款照记不阻塞,环境依赖现象(SONISCOPE_HOME unset)如实注记,判断留 04-08"
metrics:
  duration: "~5 min"
  completed: 2026-07-05
status: complete
---

# Phase 4 Plan 1: 离线门禁 worktree 基线实跑 Summary

**One-liner:** 在仓库外 worktree 基线专区(5927f36)实跑 `make test` 离线门禁,采得 D-11 三方对照实跑观测(collected 567 / passed 565 / skipped 0,2 failed 照记)与 node 缺失反事实 SKIP 证据(exit 0),归档 gate-run-worktree.md,主仓零触碰。

## 关键观测(只存档不判断)

| 观测项 | 结果 |
|--------|------|
| `uv sync --frozen`(= make install 钉版) | exit=0 |
| `make test`(Makefile:170-171,实体 `uv run pytest`) | exit=2,collected 567 / passed 565 / skipped 0 / failed 2 |
| FAILED 用例 | test_retranscribe.py::test_run_retranscribe_config_missing、test_skeleton.py::test_cli_run_command_is_placeholder(均含 RuntimeHomeError:SONISCOPE_HOME 未设置) |
| JS 桥(node v22.18.0 存在) | test_miniprogram_js.py 实际执行且 passed |
| 反事实(PATH 剔除 node) | SKIPPED [1] @ test_miniprogram_js.py:24,exit 0——『全绿≠全跑』证据成立 |
| lock 漂移 | 专区 `git status --porcelain` 空,uv.lock 未被 make test 改动 |
| 主仓零 diff 快查 | `git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空,PASS |

## worktree 专区(供 04-02 接续)

- **绝对路径:** `/private/tmp/claude-501/-Volumes-Data-ProjectCode-my-soniscope/298eef3f-7232-4386-a700-f7db47f5da56/scratchpad/wt-5927f36`(detached HEAD @ 5927f36)
- **状态:** 存续未拆(本计划不拆区);依赖已 `uv sync --frozen` 装好(.venv 就绪)
- **路径失效时重建:** `git worktree add <新路径> 5927f36`(内容由基线 SHA 唯一决定);04-02 用毕后 `git worktree remove --force` 拆除
- **原始输出留存(scratchpad,不入仓):** gate-run-make-test.txt / gate-run-rs.txt / gate-run-collect.txt / gate-run-counterfactual.txt

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | worktree 基线专区建立与离线门禁实跑观测 | (无——产物全部在仓库外 scratchpad,按计划"均不入仓",证据随 Task 2 归档提交) | 仓库外 wt-5927f36/、gate-run-*.txt |
| 2 | node 缺失反事实 SKIP 观测与 scans 归档 | bebec6c | .planning/audit/scans/gate-run-worktree.md |

## Deviations from Plan

None - plan executed exactly as written。补充说明两点(非偏差):

1. Task 1 无单独提交:其全部产物按计划显式声明"不入仓",无可提交的仓内文件,实跑证据经 Task 2 归档入仓。
2. `make test` 非绿(2 failed):计划已预置裁量条款("若非绿照记不阻塞"),照记执行,无需偏差处理;两条失败均与执行环境 SONISCOPE_HOME 未设置相关,已在归档注记中如实记录环境观测,定级判断留 04-08。

## 白名单合规声明

全程仅执行:`git worktree add`、`uv sync --frozen`、`make test`、`uv run --frozen pytest ...`、`git status`/`git diff`/`git worktree list` 只读观测。未执行任何 `make test-*`、`make verify-*`、`scripts/test_asr.py`、`scripts/fetch_test_fixtures.py`。归档内容仅含计数、skip 原因行与错误消息,无凭证模式(T-04-01/02/03 mitigations 全部落实)。

## Requirements

- AUDIT-04:本计划完成其"实跑观测"证据链部分(make test exit + 三计数 + JS 桥实跑 + 反事实 SKIP + lock 漂移);需求整体由 04-02/06/07/08 续接,不在此勾选。

## Known Stubs

无——本计划为纯审计取证,不产出代码。

## Self-Check: PASSED

- gate-run-worktree.md 存在 ✓
- 04-01-SUMMARY.md 存在 ✓
- 归档提交 bebec6c 在 git 历史 ✓
- worktree 专区 wt-5927f36 存续(list 恰 1 条)✓
