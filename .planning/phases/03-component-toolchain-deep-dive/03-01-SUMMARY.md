---
phase: 03-component-toolchain-deep-dive
plan: 01
subsystem: audit
tags: [static-audit, coverage-ledger, scan-archive, ruff, vulture, eslint, secrets-scan]
requires: []
provides:
  - COVERAGE.md 覆盖台账骨架(63 对象 + 9 面关注面清单定稿 + 20 深挖点登记)
  - HANDOFF-PHASE4.md 跨维度移交清单骨架
  - scans/ 五份扫描档案(线索池,含空三态销号表)
affects: [03-02, 03-03, 03-04, 03-05, 03-06, 03-07]
tech-stack:
  added: []
  patterns:
    - 扫描档案 = 命令原文 + 工具版本行 + 完整输出 + 空三态销号表(D-07,沿用 Phase 2 CONTRACT-MATRIX 先例)
    - 秘密类输出脱敏管道(cut 剥离内容列,只留 rev:path:line)
key-files:
  created:
    - .planning/audit/COVERAGE.md
    - .planning/audit/HANDOFF-PHASE4.md
    - .planning/audit/scans/gates-baseline.md
    - .planning/audit/scans/ruff-extended.md
    - .planning/audit/scans/vulture.md
    - .planning/audit/scans/eslint.md
    - .planning/audit/scans/secrets.md
  modified: []
decisions:
  - "秘密扫描脱敏管道由 RESEARCH 的 cut -d: -f1,2 修正为 -f1-3:git grep 带 rev 前缀时字段为 rev:path:line:content,-f1,2 会剥掉行号;修正保留行号且内容列仍被剥离,五类 grep 模式与 CHARTER 原文逐字一致"
  - "门禁直调 venv 经 UV_PROJECT_ENVIRONMENT 指向 scratchpad 且 uv run --frozen,保证零仓库写入(含防 uv.lock 更新)"
metrics:
  duration: ~35min(不含检查点等待)
  completed: 2026-07-05
status: complete
---

# Phase 3 Plan 01: 覆盖台账骨架与扫描档案 Summary

覆盖台账 63 对象骨架 + 9 面关注面清单定稿,全部审计仪器(mypy/ruff 门禁、ruff 扩展集 69 命中、vulture 1 命中、ESLint 29 warning、五类秘密扫描 69 命中)运行完毕并按 D-05/D-06/D-07 存档于 scans/,秘密输出全程脱敏,零 diff 全程保持。

## 完成任务

| # | 任务 | 提交 |
|---|------|------|
| 1 | 零 diff 前置验证、基线导出与台账骨架创建 | fa9571d |
| 2 | 临时仪器包合法性确认(vulture/eslint)— checkpoint:human-verify | 用户回复 "approved"(2026-07-05) |
| 3 | 全部审计仪器运行与扫描档案存档 | 47d9f23 |

## 产出明细

**COVERAGE.md(fa9571d):**
- 63 对象逐行登记(47 CODE:worker 核心 14 + fc 12 + miniprogram 21;16 TOOL:worker 验证/运维 12 + scripts 3 + Makefile),行数照抄 03-RESEARCH.md 实测值
- 9 面普审关注面清单定稿(D-04,含 CHARTER 锚点列与仪器辅助信号列)= 全阶段"已过面 N/9"分母
- 20 处深挖点登记(14 HYP:CODE 10 + TOOL 4;6 D14),下落列初始"待审"
- cli.py 备注"TOOL 子命令入口,整体归 CODE 审一次";pages/dev/dev.js 在列(Pitfall 8);基线导出 scratchpad 路径记入头部备注
- 完成判定节占位(03-07 填)

**HANDOFF-PHASE4.md(fa9571d):** DOC/TEST 两节移交骨架 + D-11 逐条格式声明。

**scans/ 五档(47d9f23),每档含命令原文 + 工具版本行 + 完整输出 + 空三态销号表(销号列 03-02 填):**

| 档案 | 仪器/版本 | 命中 | 关键信号 |
|------|-----------|------|----------|
| gates-baseline.md | mypy 2.1.0 / ruff 0.15.20 / miniprogram_lint(基线 218 行) | mypy 1 error;ruff 89 errors;mplint 通过 | mypy 报 `app.py:14 import handler` 部署态导入;ruff 裸跑命中全落 vendored docs/example(80)+ scripts(9),apps/ 零命中——门禁调用口径为 TOOL 观察点 |
| ruff-extended.md | ruff 0.15.20(--isolated 扩展集) | 69(= RESEARCH 实测) | ARG ×37、S105/S106 ×13、TRY ×7、DTZ ×3、S110/S104 各 ×1;fc tests 35 条(配方原样含 tests/) |
| vulture.md | vulture 2.16(uvx) | 1 | miniprogram_lint.py:121 unused variable 'rel_path'(100% 置信) |
| eslint.md | eslint 9.39.4(npx)/ node v22.18.0 | 29 warning / 0 error | test/ 已排除(Pitfall 3);no-unused-vars 为主 = HYP-15 漏报面量化底数 |
| secrets.md | git 2.23.0(git grep) | 10/4/1/3/51 = 69(= RESEARCH 参考值) | 只含 rev:path:line,无任何匹配内容列;scripts/test_asr.py:80 命中模式 2/3(HYP-07 对象) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 修正秘密扫描脱敏管道字段选择(-f1,2 → -f1-3)**
- **Found during:** Task 3 步骤 5(五类秘密扫描)
- **Issue:** RESEARCH #7 配方 `cut -d: -f1,2` 在 `git grep <rev>` 输出(`rev:path:line:content` 四段)上会把行号剥掉,只剩 `rev:path`,三态销号表将无 path:line 可引
- **Fix:** 改用 `cut -d: -f1-3`(保留 `rev:path:line`,内容列仍被完整剥离);五类 grep 模式本体与 CHARTER 原文逐字一致未动;修正已在 secrets.md 档案内注明
- **Files modified:** .planning/audit/scans/secrets.md
- **Commit:** 47d9f23

**2. [Rule 3 - Blocking] 门禁直调 venv 落位 scratchpad**
- **Found during:** Task 3 步骤 1(仓内直调门禁)
- **Issue:** worktree 内无项目 venv,`uv run` 默认会在仓库根创建 `.venv` 并可能更新 uv.lock,与"零仓库写入"约束冲突
- **Fix:** `UV_PROJECT_ENVIRONMENT` 指向 scratchpad 目录 + `uv run --frozen`;直调前后零 diff 快查均为空,`git status --porcelain` 仅 `.planning/` 条目
- **Files modified:** 无(纯执行环境处置,记录于 gates-baseline.md 头部)
- **Commit:** 47d9f23

## Authentication/Approval Gates

- **Task 2(checkpoint:human-verify,gate=blocking-human):** vulture(PyPI)/eslint(npm)包合法性人工确认。呈现 03-RESEARCH.md §Package Legitimacy Audit 证据后用户回复 "approved",Task 3 照常执行(未启用兜底方案)。

## 验证结果

- `git diff --stat 5927f36 -- apps/ scripts/ docs/` 为空(前置、门禁前后、收尾共 4 次全 PASS)
- COVERAGE.md 对象行数 = 63(`grep -cE '^\| \`'`);关注面 9 行;深挖点 20 行;cli.py/dev.js/Makefile 备注就位
- scans/ 五档齐备,每档含"版本"行与命令原文;秘密反扫 `grep -rE 'OSSAccessKeyId=[0-9A-Za-z]{8,}|Signature=[0-9A-Za-z%+/=]{16,}|LTAI[0-9A-Za-z]{10,}' .planning/audit/scans/` 零命中
- secrets.md 五类命中计数 10/4/1/3/51(与 RESEARCH 实测参考值逐一相符)
- `git status --porcelain` 新增条目仅落 `.planning/` 路径

## Known Stubs

无——本计划产物为审计台账骨架,"待审"/"销号列留空"/"完成判定占位"均为计划内设计(由 03-02~03-07 按序回填),非未接线桩。

## Threat Flags

无新增威胁面。计划 threat_model 三项 mitigate 全部落实:T-03-01(脱敏管道 + 反扫零命中)、T-03-02(仪器只对导出运行,直调门禁只读 + 前后零 diff)、T-03-SC(blocking-human 检查点已获批准,eslint 固定 @9)。

## Next Phase Readiness

- 03-02 可直接开工:五档销号表骨架就位,线索池共 69(ruff-ext)+ 1(vulture)+ 29(eslint)+ 69(secrets)+ 门禁 2 条观察(mypy 1 error、ruff 门禁口径)
- 基线导出路径已记入 COVERAGE.md 头部(会话更替时按记录命令重导出即可)

## Self-Check: PASSED

7 个产物文件 + SUMMARY 全部存在;3 个提交(fa9571d / 47d9f23 / SUMMARY 提交)均在 git log;零 diff 为空;`git status --porcelain` 零条目。
