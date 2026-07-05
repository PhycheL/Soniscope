---
phase: 04-docs-config-test-audit
plan: 8
subsystem: audit
tags: [test-audit, D-11, D-12, gate-integrity, F-TEST, HYP-22, HYP-23, HYP-24, HYP-25]
requires:
  - "04-02(双语言覆盖率实测:scans/coverage-pytest.md 73% TOTAL / scans/coverage-node.md 92.73% all files)"
  - "04-07(41 行台账普审 8/8 + 9 缺口候选面 + 反向映射终态 22)"
  - "04-01(离线门禁实跑与反事实 SKIP 观测:scans/gate-run-worktree.md)"
provides:
  - ".planning/audit/TEST-AUDIT.md — D-11 三方对照 6 项 + 总机械对账 + 收口尾注(反向映射 21 缺口全反填)"
  - ".planning/audit/findings/test.md — F-TEST-01~10 十条发现 + 批次导语(显式无发现 2 处)"
affects:
  - "04-09(HYP-22/23/24/25 回填锚点:D-11 行 5、HYP-23 专项结论行、HYP-24 专项结论行+F-TEST-02、D-11 行 3+F-TEST-03)"
  - "Phase 5(F-TEST 台账汇总;F-TEST-00 示例剔除)"
tech-stack:
  added: []
  patterns:
    - "D-11 三方对照:声称 × 静态配置 × 实跑观测逐项取证,判定列落终态,缺口候选反填 F-TEST 编号"
    - "D-12 按面聚合:一个缺口面一条,反向映射 21 行按共同根因归入 5 条 F-TEST"
key-files:
  created: []
  modified:
    - .planning/audit/TEST-AUDIT.md
    - .planning/audit/findings/test.md
decisions:
  - "三方对照增设第 6 行『门禁结果的执行环境依赖』:gate-run 实跑 2 条 FAILED(RuntimeHomeError)系干净环境 make test 非绿的门禁信号失真,归入 F-TEST-04"
  - "F-TEST-04 合并三个门禁信号失真点(JS 桥静默 skip / typecheck 非绿 F-TOOL-06 / 环境依赖)为单一『门禁二值信号无守护』面,严重度参照 F-TOOL-06 MEDIUM"
  - "反向映射 21 缺口按共同根因归 5 条:F-TEST-05 契约镜像(7)/F-TEST-06 失败恢复路径(6)/F-TEST-07 低危同步义务(6)/F-TEST-03(1)/F-TEST-04(1)"
  - "候选面『pages 无自动化测试』经 HYP-24 证伪后按实态缩窄立 F-TEST-02(选择性驱动),不按原表述立条"
  - "AUDIT-04 不在本计划勾选:沿 04-01/04-02 决策,留待阶段收尾统一销号(worktree 模式亦不触碰共享 REQUIREMENTS.md)"
metrics:
  duration: "~15min"
  completed: "2026-07-05"
status: complete
---

# Phase 4 Plan 8: TEST 维度判断层(三方对照 + F-TEST 立条 + 收口)Summary

D-11 门禁完整性三方对照 6 项落表(一致 2 + 缺口候选 4,HANDOFF TEST 3 条逐条销号),TEST 维度全部缺口按面聚合为 F-TEST-01~10 十条发现写入 findings/test.md(覆盖率数字仅证据引用,负向检索词零命中),TEST-AUDIT.md 收口:反向映射 21 条缺口行与台账 9 行线索全部反填终态编号,总机械对账五等式闭合。

## 完成内容

### Task 1: D-11 门禁完整性三方对照表(commit 2ea5868)

- 6 对照项逐项三方取证:①pytest 套件范围(一致:testpaths × collected 567)②JS 测试进门禁路径(缺口候选:skipif `test_miniprogram_js.py:24` + 反事实剔除 node → skipped 1 / exit 0)③静态门禁范围(缺口候选:mypy/ruff 仅 apps/ 四路径 + test_asr.py 实害样本)④覆盖率门禁(一致:『无门禁』三方自洽事实行,不立条理由在档)⑤活体路径(缺口候选:缺 code 即 SKIP,静态+移交证据判定)⑥执行环境依赖(缺口候选:干净环境 make test 非绿,2 条 RuntimeHomeError)
- HANDOFF-PHASE4.md TEST 节 3 条移交逐条显式销号(第 1 条 → 行 5;第 2/3 条 → 行 3),销号 bullet 独立成行
- test_asr.py 证据只含位置(`scripts/test_asr.py:80 @ 5927f36`)+ 模式名,无任何 URL 参数值(T-04-17 mitigate)

### Task 2: F-TEST-01~10 按面聚合立条(commit 36d9b14)

| 编号 | 面 | 严重度(参照) | 关联 |
|------|-----|---------------|------|
| F-TEST-01 | 活体路径零自动化覆盖 | LOW | HYP-22 |
| F-TEST-02 | pages 选择性驱动(HYP-24 证伪后缩窄) | LOW | HYP-24 |
| F-TEST-03 | scripts/ 全静态门禁外 + 实害样本 | MEDIUM(参照 F-TOOL-05) | HYP-25、F-TOOL-05 |
| F-TEST-04 | 门禁二值信号无守护(JS 桥 skip/typecheck 非绿/环境依赖) | MEDIUM(参照 F-TOOL-06) | F-TOOL-06 |
| F-TEST-05 | 契约镜像常量/派生函数无对称锁定 | MEDIUM(参照 F-CON-02/03) | F-CON-01/02/03/06、F-CODE-07/08、F-TOOL-08 |
| F-TEST-06 | 失败/恢复路径无测试兜底 | MEDIUM(参照 F-CODE-02/06) | F-CODE-02/03/06、F-TOOL-01/02/03 |
| F-TEST-07 | 低危功能缺失面的测试同步义务 | LOW | F-CON-04、F-CODE-01/04/05、F-TOOL-04/07 |
| F-TEST-08 | fake 与真实实现无行为面对齐锁定 | LOW | 无(面②) |
| F-TEST-09 | oss_sign 无 raw secret 负断言 | LOW | 无(面⑤/秘密红线) |
| F-TEST-10 | 断言强度与测试卫生杂项(5 处聚合) | LOW | 无(面①/③/⑧) |

- 批次导语含显式无发现 2 处(覆盖率门禁行三方自洽、F-CON-05 无缺口)与 HANDOFF 3 条销号去向
- 机械验收:`grep -ci '评分\|score'` = 0;`grep -c 'scans/coverage'` = 2(数字仅证据引用,指向归档行并连带 experimental 标注)

### Task 3: TEST-AUDIT.md 收口与总机械对账(commit 0c784b2)

- 台账产出列 9 行线索反填(test_audio/test_e2e/test_manifest/test_skeleton/test_custom_runtime_app → F-TEST-10;test_miniprogram_js → F-TEST-04;test_nls → F-TEST-05;test_poller → F-TEST-08;oss_sign → F-TEST-09)
- 反向映射 21 条缺口行全部反填;归属等式 21 = 1(F-TEST-03)+ 1(F-TEST-04)+ 7(F-TEST-05)+ 6(F-TEST-06)+ 6(F-TEST-07)✓
- HYP-24 节 stale 指针补引完毕(coverage-node.md pages 三文件数据行入档)
- 尾注四计数:41 模块 × 8 面;反向映射 22 行终态;三方对照 6 项;F-TEST 10 条;HYP-22/23/24/25 锚点齐备

## 4 条 TEST HYP 回填锚点(04-09 消费)

| HYP | 锚点位置 |
|-----|----------|
| HYP-22 | TEST-AUDIT.md D-11 对照行 5 + findings/test.md F-TEST-01 |
| HYP-23 | TEST-AUDIT.md『HYP-23 专项』结论行(9/9 错误码 handler 级覆盖,04-07 在档) |
| HYP-24 | TEST-AUDIT.md『HYP-24 专项』结论行(3/3 页加载、补引完毕)+ F-TEST-02 |
| HYP-25 | TEST-AUDIT.md D-11 对照行 3 + F-TEST-03 |

## 验证结果

- `grep -c '销号引 HANDOFF-PHASE4.md TEST' TEST-AUDIT.md` = 5(≥3,3 条移交逐条独立成行)
- `grep -c '^### F-TEST-' findings/test.md` = 11(示例 00 + 实条 10,≥4)
- `grep -ci '评分\|score' findings/test.md` = 0(成功判据 3 机械验收通过)
- 反向映射未反填残留 = 0;`→ 04-08 候选面` 残留 = 0;反填行计数 = 21
- `git diff --stat 5927f36 -- apps/ scripts/ docs/` 为空(T-04-19 mitigate:纯静读,files_modified 仅两个 .planning 写入点)

## Deviations from Plan

**1. [Rule 2 - 补充对照项] 三方对照增设第 6 行『门禁结果的执行环境依赖』**
- **Found during:** Task 1
- **Issue:** 计划列 5 个对照项,但 gate-run-worktree.md 实跑观测含 make test exit=2 / 2 条 FAILED(RuntimeHomeError,SONISCOPE_HOME 未设置)——该现象是门禁完整性(非绿 ≠ 代码错)的直接证据,5 项框架无处安放
- **Fix:** 增设行 6(计划明示『至少覆盖以下对照项』允许扩行),静态侧补 `test_skeleton.py:33-35`/`test_retranscribe.py:268-280 @ 5927f36` 依赖面证据,缺口归入 F-TEST-04
- **Commit:** 2ea5868

**2. [证据修正] 候选面 2『pages 胶水层无自动化测试』按 HYP-24 证伪结果缩窄立条**
- **Found during:** Task 2
- **Issue:** 计划候选面 2 原表述与 04-07 HYP-24 专项事实(3/3 注册页均被 node 测试真实加载)不符
- **Fix:** 按计划『据实取舍』条款缩窄为『选择性驱动,未驱动路径无自动化』立 F-TEST-02,批次导语显式记录原表述证伪
- **Commit:** 36d9b14

其余按计划逐字执行。

## Known Stubs

无。三方对照、F-TEST 条目、收口对账三件套均为终态且指针互相闭环;F-TEST 条目状态 draft、上线判定留空系 CHARTER schema 约定(Phase 5 填),非 stub。

## Threat Flags

无新增安全面。T-04-17(test_asr.py 仅位置+模式名)、T-04-18(覆盖率数字仅证据字段且指向 scans/ 归档行,负向 grep 通过)、T-04-19(仅两个 .planning 写入点,封版产物零改动)三项 mitigation 均落实,见验证结果。

## Self-Check: PASSED

- FOUND: .planning/audit/TEST-AUDIT.md(D-11 节 + 总机械对账 + 尾注)
- FOUND: .planning/audit/findings/test.md(F-TEST-01~10 + 批次导语)
- FOUND: commit 2ea5868(Task 1)
- FOUND: commit 36d9b14(Task 2)
- FOUND: commit 0c784b2(Task 3)
