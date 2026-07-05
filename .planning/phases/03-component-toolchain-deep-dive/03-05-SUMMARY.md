---
phase: 03-component-toolchain-deep-dive
plan: 05
subsystem: audit-toolchain
tags: [audit, tool-dimension, fc-deploy, verify-tooling, miniprogram-lint, d14-3]
requires:
  - "03-01 COVERAGE.md 骨架与基线导出"
  - "03-02 scans/ 三态销号档案(ruff-extended/vulture/eslint 量化小结)"
  - "03-04 HANDOFF-PHASE4.md 与 HYPOTHESES 回填先例(累计 9 条)"
provides:
  - "COVERAGE.md TOOL 维度 worker 模块 12/12 行落格(全部 9/9 面)"
  - "findings/toolchain.md F-TOOL-01~04(全 LOW,九字段齐备)"
  - "HYPOTHESES.md HYP-04 证实 / HYP-15 细化(累计回填 11 条)"
  - "D14-1/D14-3 工具侧证据齐备(只采证未裁定,供 03-07)"
  - "HANDOFF-PHASE4.md TEST 节首条(HYP-22 工具侧证据)"
affects:
  - "03-06(scripts/Makefile 审计,HYP-07/18 留给它)"
  - "03-07(D14-3/D14-1 裁定 + 完成判定收口)"
tech-stack:
  added: []
  patterns:
    - "逐模块读完立即落格(增量写 COVERAGE/findings,不攒批)"
    - "销号确认项降级用'03-0N 人工核实下落'追记体例(沿 03-04 先例)"
key-files:
  created: []
  modified:
    - .planning/audit/findings/toolchain.md
    - .planning/audit/COVERAGE.md
    - .planning/audit/HYPOTHESES.md
    - .planning/audit/HANDOFF-PHASE4.md
    - .planning/audit/scans/ruff-extended.md
    - .planning/audit/scans/vulture.md
decisions:
  - "HYP-04 经 D-10 上线语境裁定成立(RPT-06/DNF 候选,不占发现 ID);同模块备份失败分支独立立 F-TOOL-02"
  - "HYP-15 细化:覆盖面狭窄证实但基线漏报实害为零;缺口按 CHARTER LOW 锚点立 F-TOOL-04,修复给双选项(增补语义检查或零依赖 eslint 配置)"
  - "ruff #41/#45/#49 与 vulture #1 四条销号确认项全部降级(CLI 面一致/自述故意桩/死参数无操作者影响),不立发现"
  - "D14-3 全部证据只采不裁(D-15),含 sts_escape 顺带两点(key 模板手拼 :127-129、key→id 切割 :256-258)"
metrics:
  duration: "~17 min"
  completed: "2026-07-05"
status: complete
---

# Phase 3 Plan 05: Worker 验证/运维工具链普审+深挖 Summary

**One-liner:** Worker 包内 12 个验证/运维模块(4,982 行)9 面全过审,立 4 条 LOW 级 F-TOOL 发现(STS 反例误导诊断/部署无备份不阻断/测试对象残留污染主链前缀/小程序语义 lint 缺位),HYP-04 证实、HYP-15 细化回填,D14-3 六处镜像证据齐备待 03-07 裁定。

## What Was Done

### Task 1: 四大工具模块深挖普审(2,777 行)— commit 7f9163a

- **verify_prep.py(924)**:前置检查清单(REQUIRED_TOOLS/MIN_DISK_BYTES/config 权限)完整,报告路径异常处理逐块收敛无静默;**F-TOOL-01(LOW)**——STS 越权反例把非拒绝类异常(网络超时等)与"操作成功"同报为"疑似越权放行"且汇总丢弃 error_code,误导操作者排查方向(`verify_prep.py:747-753,275-293 @ 5927f36`)。
- **fc_deploy.py(707,深挖 HYP-04)**:能力面证实仅"备份/打包/代码更新/回滚/日志诊断",FcApi Protocol 无 create/触发器/env 面(`:106-119`),update_code 显式只传 code(`:667-672`);**F-TOOL-02(LOW)**——备份失败(任意类别,非仅首次部署)不阻断部署,预部署快照缺失仅 detail 注记(`:380-386`);凭证脱敏管道(`_redact_error_text` + 备份只记 env 名)记 RPT-06 优点候选;rollback timestamp 死参数与 fetch_logs 故意桩均降级(CLI 面一致)。
- **retranscribe.py(590,D-03 点名)**:`.done` 绕行边界核查通过——单条经 object_key_for 合法性校验、批量同一决策函数、`.done` 零删除路径、失败不覆盖产物、与主轮询 fragment_lock 互斥;误触面受控,无发现(锁外决策竞态/跨文件非事务窗口/--all-from 日期无校验三点记备注)。
- **fc_live.py(556,D14-3)**:四处证据逐处核实并记行号——3 错误码 `:42-44`(含"与 fc_shared 保持一致"锚点 `:41`)、7 字段 `:47-55`(锚点 tech-spec §4.1)、50MB 隐式假设 `:57-59`(无 env.py 常量引用)、合成 fragment_id `:254-258`;反例目标全为合成 key,无真实录音波及;未下裁定。

### Task 2: 其余 8 模块普审(2,205 行)— commit d43536e

- **verify_upload_live.py(464,D14-3)**:REASON 第三份字面定义 `:34-35`、合成 ID `:199-203` 采证;**F-TOOL-03(LOW)**——测试对象写入生产 recordings/ 前缀且 key 通过 Worker 往返校验,`_try_delete` 静默吞清理失败,残留即落入 F-CODE-02 无界重试面(`:257-262,276-277`)。
- **ops.py(380)**:删除类操作入口核实结论——**无**(三命令全只读);本模块反而是 R-07 红线自动核查器(源码+日志删除扫描,豁免名单四模块)。
- **e2e.py(295)/e2e_scenarios.py(268)/sts_escape.py(268)/fixtures.py(232)/latency.py(80)**:全部无发现。e2e_scenarios **确为 D14-3 导入消费端**(`:31-40` from fc_live import,非第四份副本);sts_escape 凭证面通过且 detail 带 error_code(F-TOOL-01 修复可参照),顺带采两点契约镜像(key 模板手拼/key→id 切割);fixtures 落 D14-1 stdlib hashlib 流式实现证据(`:21,116-122`)。
- **miniprogram_lint.py(218,深挖 HYP-15)**:规则清单五族逐条采证(appid/四件套/域名+拼写守卫/JSON 可解析/密钥启发式,`:42-46,65-128,182-191`),零 JS 语义规则;对照 scans/eslint.md 量化底数(0 error/29 warning 全误报)→ **F-TOOL-04(LOW,CHARTER "lint 覆盖缺口"锚点)**。
- HANDOFF-PHASE4.md TEST 节新增 HYP-22 工具侧证据(live 场景依赖一次性 code,CI 零活体覆盖)。

### Task 3: 回填与销号反填 — commit 2f74ed9

- **HYP-04 → 证实**:四处行号证据;D-10 裁定自评成立(两函数在线、工具覆盖高频操作),记 RPT-06/DNF 候选不占发现 ID;runbook 保真度口径移 Phase 4 DOC。
- **HYP-15 → 细化**:"只捕获被教会的规则"半句证实(规则面零重叠)、"漏报实害"半句基线证伪(增量 0 真实缺陷);缺口立 F-TOOL-04。
- 销号去向反填:ruff #41/#45/#49、vulture #1 四行均追记"03-05 人工核实下落"降级理由(沿 03-04 #1 先例体例)。
- 尾部统计:累计回填 11 条,余 14 条(TOOL 余 HYP-07/18 → 03-06)。

## Verification Results

- Task 1 awk(四模块无待审)→ PASS;Task 2 awk(TOOL×soniscope_worker 全 12 行无待审)→ PASS;12 行全部 9/9。
- Task 3:HYP-04/15 状态均非"未验证"且含 `@ 5927f36` 证据 → PASS。
- 零 diff:`git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空 ✓;`git status --porcelain` 仅 `.planning/` 条目 ✓。
- scans/ 秘密反扫:6 处命中均为 secrets.md 既有模式名叙述(命令原文/销号表描述),无值本体,红线成立。
- D-08 全程成立:被审工具零执行,取证仅 `git show 5927f36:<path>`。

## Deviations from Plan

None - plan executed exactly as written.(注:验收项"去向列不再含 03-05 占位"按 03-04 既有先例以追记"03-05 人工核实下落"方式满足——原始线索文字保留、下落已闭合,与 ruff #1 的 03-04 处置体例一致。)

## Findings Ledger Delta

| ID | 严重度 | 一行标题 |
|----|--------|----------|
| F-TOOL-01 | LOW | verify-prep STS 反例误导诊断且报告丢错误码 |
| F-TOOL-02 | LOW | deploy-fc 备份失败不阻断部署 |
| F-TOOL-03 | LOW | test-verify-upload 测试对象残留生产前缀且清理失败不可见 |
| F-TOOL-04 | LOW | 小程序 JS 语义类缺陷零静态门禁 |

## For 03-06 / 03-07

- 03-06:TOOL 维度仅余 scripts 3 文件 + Makefile;HYP-07(test_asr DEFAULT_FILE_LINK)/HYP-18(legacy AcsClient)在彼处回填。
- 03-07 裁定输入(D14-3):fc_live 四点 + verify_upload_live 两点 + e2e_scenarios 导入定性 + sts_escape 顺带两点,全部行号在 COVERAGE 行备注与深挖点登记表;D14-1 双侧证据(sha256.js CODE 侧 + fixtures.py `:21,116-122`)亦齐。

## Self-Check: PASSED

- [x] `.planning/phases/03-component-toolchain-deep-dive/03-05-SUMMARY.md` exists
- [x] Commits 7f9163a / d43536e / 2f74ed9 exist on worktree branch
- [x] COVERAGE.md TOOL soniscope_worker 12 行无待审(awk → 0)
- [x] `grep -c '^### F-TOOL-'` → 5(含 F-TOOL-00 示例,真实 4 条)
- [x] HYPOTHESES.md 尾部统计 11/25,未验证 14

---
*03-05 Summary: 2026-07-05(TOOL worker 12/12 落格,F-TOOL-01~04 入账,HYP-04/15 回填,零 diff 为空)*
