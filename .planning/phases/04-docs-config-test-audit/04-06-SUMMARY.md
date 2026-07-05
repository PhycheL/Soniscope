---
phase: 04-docs-config-test-audit
plan: 6
subsystem: audit
tags: [test-audit, coverage-ledger, reverse-mapping, D-09, D-10, D-16]
requires: []
provides:
  - ".planning/audit/TEST-AUDIT.md — 8 面清单 + 41 行台账 + 22 行反向映射清单"
affects:
  - "04-07(逐模块普审按 8 面分母填账、销号 2 条占位态行)"
  - "04-08(F-TEST 缺口定级引用节首定级规则)"
tech-stack:
  added: []
  patterns:
    - "证据/判断分层:台账只登记对象/深度/已过面/线索,发现正文入 findings/test.md"
    - "取证一律 git show/git grep @ 5927f36,worktree 副本仅供实跑"
key-files:
  created:
    - .planning/audit/TEST-AUDIT.md
  modified: []
decisions:
  - "D-10 定稿:质量检查面为 8 面(断言强度/fake 漂移/隔离泄漏/契约常量锁定/秘密泄漏断言/静默 skip/错误路径/测试生产耦合),全阶段分母『已过面 N/8』"
  - "台账对象实测 41(worker 24 + fc 7 + node 10),与 ls-tree 枚举一致,无需头部注记偏差"
  - "矩阵 12 个非 agree 格全部已由 F-CON-01~06 承载(CONTRACT-MATRIX §机械对账第 3 条),反向映射矩阵追加行数 = 0"
  - "兜底初判收敛:终态 20 行(参照原严重度 19 + 无缺口 1),占位态 2 行(F-CODE-02、F-CODE-08)"
metrics:
  duration: "~12min"
  completed: "2026-07-05"
status: complete
---

# Phase 4 Plan 6: TEST-AUDIT.md 骨架与反向映射清单 Summary

TEST-AUDIT.md 按 D-16 独立新建:D-10 的 8 面质量检查清单定稿、41 个测试模块逐对象台账骨架就绪,D-09 反向映射清单 22 行成表且兜底初判完成 20/22,余 2 行显式占位待 04-07 补证。

## 完成内容

### Task 1: TEST-AUDIT.md 骨架(commit 6505059)

- 文件头:标题、Created 2026-07-05、基线 5927f36、证据/判断分层声明(发现正文入 findings/test.md)、取证纪律、worktree 执行区备注(实跑证据指向 scans/gate-run-worktree.md 与 scans/coverage-*.md,重建命令 `git worktree add <scratchpad>/wt-5927f36 5927f36` + `uv sync --frozen`)
- 8 面清单表(# | 关注面 | 锚点/关联 | 仪器辅助信号),契约常量锁定/静默 skip 等全部 8 面在列,面⑥预置已知线索 test_miniprogram_js.py:24
- 逐对象台账 41 行(路径 | 行数 | 侧 | 深度 | 已过面 | 产出 | 备注):行数为 `git show 5927f36:<path> | wc -l` 实测;已过面初始 0/8、产出初始 `-`;备注列预置 F-CON/F-CODE/F-TOOL 既有发现的已知测试线索作为 04-07 过账起点

### Task 2: D-09 反向映射清单(commit 5742dfc)

- 22 条 F-* 逐条在列;矩阵非 agree 格 12 个经去重核对全部由 F-CON-01~06 承载,追加行数 = 0(去重依据写入节内)
- 兜底列全部非空:有关联测试的写 `文件:行号 @ 5927f36`(如 F-CODE-07 反查引用 uploader.test.js:55-56 / verify.test.js:54-55 / test_nls.py:401,449-450),无兜底的写『无』附 grep 裁决
- 节首预置定级规则两句(脆弱区缺口参照原严重度 / 一般缺口 CHARTER LOW 锚点),供 04-08 引用
- 节尾机械对账:22 = 22 F-* + 0 追加;终态 20 + 占位态 2 = 22 ✓

## 占位态行数(供 04-07 销号核对)

**占位态共 2 行**,『补证中』字样仅出现在这 2 个表行的缺口判定列单元格:

| 条目 | 占位原因 | 04-07 销号方向 |
|------|----------|----------------|
| F-CODE-02 | 单轮失败行为有锁定(test_poller/test_pipeline/test_audio),多轮重复与计数缺失面静读不可定判 | 面⑦逐面普审 test_poller/test_pipeline/test_e2e_scenarios 后定终态 |
| F-CODE-08 | uploads 页参照实现与 queue_runtime 编排各有测试,两份请求组装是否存在同步性断言静读不可定判 | 面④/面⑧普审 uploader.test.js 与 redesign_view.test.js 后定终态 |

措辞自洽 gate 已验证:`grep -c '补证中'` = `grep -c '^|.*补证中'` = 2(说明性文字零出现,04-07 Task 3 负向 grep 收口可用)。

## 验证结果

- 台账行数:`grep -c '^| \`apps/' TEST-AUDIT.md` = 41(与 ls-tree 枚举一致,worker 24 + fc 7 + node 10)
- F 行数:`grep -c '^| F-CON-\|^| F-CODE-\|^| F-TOOL-'` = 22
- 封版产物零改动:`git diff --stat 5927f36 -- apps/ scripts/ docs/` 为空;findings 三本与 CONTRACT-MATRIX 仅只读引用(T-04-14 mitigate)
- F-TOOL-05 行只写 `scripts/test_asr.py:79-81 @ 5927f36` + 模式名,无值本体(T-04-13 mitigate)

## Deviations from Plan

### 上下文缺失(不影响产出)

**1. [上下文] 04-PATTERNS.md 未进入工作树**
- **Found during:** 执行启动加载上下文
- **Issue:** `.planning/phases/04-docs-config-test-audit/04-PATTERNS.md` 在主仓库为未跟踪文件,未随基线提交进入本 worktree,plan `<context>` 引用不可达
- **处理:** 以 COVERAGE.md(仿写范式)、TESTING.md(测试地图)、CHARTER.md(严重度锚点)三份齐备上下文执行,产出不受影响
- **Files modified:** 无
- **Commit:** 无

其余按计划逐字执行,无功能性偏差。

## Known Stubs

台账的深度/已过面/产出三列为设计上的占位骨架(初始 `-`/`0/8`/`-`),由 04-07 逐模块回填——系计划明示的填账格,非缺陷性 stub。

## Threat Flags

无新增安全面(本计划仅新建审计文档,threat_model 内 T-04-13/T-04-14 两项 mitigation 均已落实,见验证结果)。

## Self-Check: PASSED

- FOUND: .planning/audit/TEST-AUDIT.md
- FOUND: commit 6505059(Task 1)
- FOUND: commit 5742dfc(Task 2)
