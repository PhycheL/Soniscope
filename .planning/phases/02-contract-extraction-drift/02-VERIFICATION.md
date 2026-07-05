---
phase: 02-contract-extraction-drift
verified: 2026-07-04T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 2: 契约抽取与漂移分析 Verification Report

**Phase Goal:** 系统的核心契约(fragment_id / object key / `x-oss-meta-*` 等)在小程序、FC、Worker 三处实现的现状一致性有逐字段的证据矩阵与分歧判定
**Verified:** 2026-07-04
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 漂移矩阵完成:每要素 × FC/Worker/小程序三列,每格 agree/diverge/absent + 行号证据 | ✓ VERIFIED | `CONTRACT-MATRIX.md` 51 行(组① 15 + 组② 28 + 组③ 5 + 普查 3),236 处 `@ 5927f36` 证据引用;8/8 抽查行号经 `git show 5927f36:<path>` 逐一命中(sts.py:30-33、oss_admin.py:24-27、audio.js:95-96、poller.py:47-61、upload_queue.js:38-44、errors.py:13-19、env.py:41、uploader.js:32-50);n/a 格均带结构性理由,agree 格同样带行号(D-11) |
| 2 | 往返校验结论在案:FC 签发 key 能否被 Worker `fragment_id_from_key` 解析有明确记录 | ✓ VERIFIED | 矩阵『往返校验结论』章节 + 18 样本表(预期/实测/销号三元组全闭合)。**行为级复核**:验证者在独立基线导出树(`git archive 5927f36` → scratchpad)上重跑关键样本——S-01 往返等式 True 且 FC/Worker key 逐字符相等;S-02/S-04 FC 抛 `400 INVALID_REQUEST: invalid fragment_id date`;S-14/S-18 Worker 返回 None;JS 侧 S-02 正则放行 true、S-14/S-18 第四处照单全收、S-07 产出目录≠前缀 key——全部与矩阵记录逐项一致,零矛盾 |
| 3 | 每条分歧归入良性/潜伏/活跃失配/覆盖洞四类之一 + Postel 宽严分析 | ✓ VERIFIED | 矩阵判定列全回填(`待判定` 表格行残留 = 0);12 个 diverge/absent 格 → F-CON-01~06(覆盖洞 3 / 潜伏 2 / 良性 1 / 活跃失配 0);6 条 F-CON 各含 Postel 三要素(谁严谁宽/失配方向/触发条件);严重度映射符合 D-10(良性→INFO,潜伏→MEDIUM,覆盖洞 LOW~低档);对账等式 12 格 = 5×1 + 1×7(F-CON-05 覆盖行 35-41 同根因)复算成立 |
| 4 | 三处之外契约相关跨语言重复实现普查完成,含"已检查,无新发现"记录 | ✓ VERIFIED | 矩阵『重复逻辑普查』:9 项候选三态结论(新行 1 / 指针 4 / 已检查无新发现 4 = 9 ✓);5 条 `git grep ... 5927f36` 扫描命令原文 + 命中计数存档(966 实现 + 581 测试 = 1547 复算平);D14-1~6 债务移交 Phase 3、CLAUDE.md 错误码声明失实移交 Phase 4 |
| 5 | 存在真实分歧则黄金样本契约测试设计配方成文(D-16 五要素) | ✓ VERIFIED | 非良性分歧 5 条 → 触发线成立,`CONTRACT-TEST-RECIPE.md` 存在(199 行):黄金样本 JSON schema 与建议路径、覆盖要素表(引矩阵行 + F-CON ID)、pytest 骨架(node 缺席 skip + 显式文件清单两个先例要点齐)、node:test 骨架、make 接入点与 4 条验收标准;样本逐一复用 S-01~S-18(D-07→D-16 复用链) |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Plan-level Must-Haves (merged, spot-verified)

| Plan | Truth | Status |
|------|-------|--------|
| 02-01 | 矩阵 8 章节骨架 + 组① 15 行逐字段(key 族 6 + meta 9) | ✓ (`x-oss-meta-` 12 处命中,7 字段行齐) |
| 02-02 | 组② 全字段 + 9 错误码/reason 字符串 + 组③ 5 常量行 + 普查双保险 | ✓ (9/9 码 grep 命中;52428800/CHUNK_MAX_DURATION_SECONDS/RETRY_DELAYS/STS_MAX_DURATION_SECONDS 均命中) |
| 02-03 | 样本 ≥11 类、TZ 双跑记录、`__file__` 来源断言、执行只作佐证 | ✓ (18 样本 18 销号;TZ=Asia/Shanghai / TZ=America/New_York 均在案;复跑说明可重放——本验证实际按其重放成功) |
| 02-04 | 判定列回填 + F-CON 九字段 + 条件配方 + 收尾机械对账 | ✓ (7 条对账等式全部独立复算成立;文档尾斜体摘要在位) |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.planning/audit/CONTRACT-MATRIX.md` | 漂移矩阵 + 往返结论 + 样本附录 + 普查 + 收尾 | ✓ VERIFIED | 395 行,51 矩阵行,全部章节在位,非 stub |
| `.planning/audit/findings/contract.md` | F-CON 发现台账(九字段 schema) | ✓ VERIFIED | F-CON-01~06 六条真实发现,九字段齐全,F-CON-00 示例保留未删改,严重度理由为 `影响:…;可能性:…` 格式,无数值评分 |
| `.planning/audit/CONTRACT-TEST-RECIPE.md` | 条件产出(D-15 触发) | ✓ VERIFIED | 触发线成立且成文,D-16 五要素各自成节,纯设计未落测试文件 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| 矩阵格行号 | 基线代码 | `git show 5927f36:<path>` | ✓ WIRED | 8/8 抽查命中(含组①②③各组) |
| 矩阵 diverge/absent 格 | F-CON 条目 | `→ F-CON-NN` 链接 | ✓ WIRED | 矩阵 12 链接 ↔ 台账 6 条(F-CON-05 一对七映射显式给出);每条 F-CON 反向引用矩阵行 |
| 样本清单 S-01~S-18 | CONTRACT-TEST-RECIPE.md | D-07→D-16 复用链 | ✓ WIRED | 配方 §6 逐样本注明来源 ID |
| F-CON 关联字段 | HYPOTHESES.md | HYP-13 / HYP-03 挂钩 | ✓ WIRED | 6/6 条挂 HYP-13;F-CON-04 另挂 HYP-03 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| FC↔Worker 往返(S-01) | baseline-export python: `object_key_for` → `fragment_id_from_key` | fc==wk True, roundtrip True | ✓ PASS |
| 非法日期拒绝(S-02/S-04) | same | `FcHttpError 400 INVALID_REQUEST: invalid fragment_id date` | ✓ PASS |
| 非 .wav / 日期错位 key(S-14/S-18) | same | Worker 均返回 `None` | ✓ PASS |
| JS 正则放行非法日期(S-02) | `TZ=Asia/Shanghai node spot.js` | `true` | ✓ PASS |
| 第四处反推照单全收(S-14/S-18) | same | 返回前缀 id | ✓ PASS |
| preview 错位 key(S-07) | same | `recordings/2026-07-05/20260704T…` dir≠prefix true | ✓ PASS |

### Probe Execution

无项目 probe 脚本声明(`scripts/*/tests/probe-*.sh` 不存在,PLAN/SUMMARY 未声明 probe)— 不适用。零 diff 约束由验证者直接执行:`git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空 ✓;工作树仅 `.planning/` 变更(02-PATTERNS.md untracked)✓。

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CONTRACT-01 | 02-01, 02-02 | 三处逐字段漂移矩阵 | ✓ SATISFIED | 矩阵 51 行,SC1 证据 |
| CONTRACT-02 | 02-03, 02-04 | 往返校验 + 四类分类 + Postel | ✓ SATISFIED | SC2/SC3 证据,行为级复核通过 |
| CONTRACT-03 | 02-02 | 重复逻辑普查 | ✓ SATISFIED | SC4 证据 |
| CONTRACT-04 | 02-04 | 黄金样本测试设计配方 | ✓ SATISFIED | SC5 证据 |

无 ORPHANED 需求(REQUIREMENTS.md Phase 2 映射恰为此四项)。

**书记不一致(warning,非阻断):** REQUIREMENTS.md 中 CONTRACT-01 与 CONTRACT-03 的复选框仍为 `[ ]`、追踪表状态为 `Pending`,而 CONTRACT-02/04 已被 02-04 更新为 Complete。四项需求的实质证据均已在案(见上表),该不一致为状态簿记遗漏(02-01/02-02 未回写 REQUIREMENTS.md),建议在里程碑对账或下次 `.planning` 提交时将 CONTRACT-01/03 一并勾选,保持台账一致。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `findings/contract.md` | 17 | `F-XXX-NN`(grep 命中 XXX) | ℹ️ Info | schema 示例中的发现 ID 占位模式,非债务标记,无影响 |

无 TBD/FIXME 债务标记;无占位/stub 内容;审计文档为审计里程碑的最终产物形态,无"存在但未接线"问题。

### Human Verification Required

无。全部真值可程序化验证:行号证据经 git show 复核,执行佐证经独立基线导出复跑,机械对账等式经独立复算。

### Gaps Summary

无缺口。五条成功判据全部由代码库/产物实证:矩阵 51 行三列证据齐备且抽查行号 100% 命中;往返校验结论不仅在案且被本次验证独立复跑证实(python 5 样本 + JS 4 断言,零矛盾);12 个分歧格四类归类完整且对账等式平;普查 9 候选三态收口含显式"已检查,无新发现";配方触发线成立且五要素成文。零 diff 硬约束成立(apps/、scripts/、docs/ 相对 5927f36 空 diff)。唯一瑕疵为 REQUIREMENTS.md 中 CONTRACT-01/03 复选框未勾(簿记遗漏,warning 级,不影响目标达成)。

---

_Verified: 2026-07-04_
_Verifier: Claude (gsd-verifier)_
