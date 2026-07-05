---
phase: 03-component-toolchain-deep-dive
verified: 2026-07-05T00:00:00Z
status: passed
score: 13/13 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 3: 组件与工具链深潜 Verification Report

**Phase Goal:** 三层主体代码与部署工具链的技术债、脆弱区域全部经人工核实进入发现台账,为后续测试审计与报告提供代码实态基准
**Verified:** 2026-07-05
**Status:** passed
**Re-verification:** No — initial verification

本阶段为静态审计里程碑的文档产出阶段:交付物是审计台账文档而非代码。验证方式为文档级 must_haves 核验(覆盖行完整性、发现 schema 字段、对账等式独立复算)+ **对发现证据逐条抽查回溯 `git show 5927f36` 基线代码**(反捏造核验)。SUMMARY 声明未被采信为证据——全部关键数字均独立重算。

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | SC1: 三层(worker/fc/miniprogram)债务与脆弱区域发现按统一 schema 进台账,每条经人工在引用行核实 | ✓ VERIFIED | findings/code.md 含 F-CODE-01~08(8 条真实发现 + 1 条声明的 schema 示例),九字段(维度/严重度/证据/修复建议/工作量/关联发现/上线判定/状态)齐备。证据抽查 6 条全部与 `git show 5927f36` 实际代码一致(见下"证据抽查") |
| 2 | SC2: scripts/、Makefile、fc_deploy 等工具链发现进台账,含 test_asr.py 预签名 URL 线索核实结论 | ✓ VERIFIED | findings/toolchain.md 含 F-TOOL-01~08。F-TOOL-05 即 HYP-07 核实结论:独立核验 `git show 5927f36:scripts/test_asr.py:79-81` 确为预签名 URL 字面量,`Expires=1780035733`(2026-05-28/29,早于审计日)已过期,AccessKeyId 为 TMP. 前缀 STS 形态——与发现陈述完全一致 |
| 3 | SC3: 无原始 linter 输出直接充当发现——每条发现附人工确认的 file:line@SHA 证据片段 | ✓ VERIFIED | scans/(线索池)与 findings/(判断)物理分离;258 条工具命中全部经三态销号后仅 15 条确认项流转,每条发现的证据字段含 `@ 5927f36` 引用片段与人工核实叙述(如 F-CODE-01 明记"ruff ARG001 命中与人工核实互证") |
| 4 | SC4: 跨组件契约类观察已移交 Phase 2 漂移矩阵,未在组件维度单独下判断 | ✓ VERIFIED | findings/code.md 与 toolchain.md 均零 F-CON 条目(grep 复核 = 0);COVERAGE 中 oss_admin.py/audio.js/errors.py 行均标注"契约观察移交…本维度不判断";D14-6 裁定显式让位既有 F-CON-03 不重复立 |
| 5 | COVERAGE.md 63 对象(47 CODE + 16 TOOL)逐行登记,9 面清单在文件头定稿 | ✓ VERIFIED | 独立重算 `grep -cE '^\| \`'` = 63;9 面清单表在 §普审关注面清单;行数抽查 5 处(pipeline.py 875 / nls.py 740 / index.js 796 / verify_prep.py 924 / Makefile 171)与基线 `wc -l` 实测全部一致 |
| 6 | 全部审计仪器输出存档 scans/,每档含命令原文 + 工具版本 | ✓ VERIFIED | 五档(gates-baseline/ruff-extended/vulture/eslint/secrets)头部均含命令原文与实测工具版本行(uv 0.8.14 / mypy 2.1.0 / ruff 0.15.20 / vulture 2.16 / eslint 9.39.4 / git 2.23.0) |
| 7 | 秘密类扫描存档只含 path:line,不含匹配内容列(脱敏管道生效) | ✓ VERIFIED | scans/secrets.md 销号表仅 path:line + 模式名列;全 .planning/audit/ 目录秘密模式反扫独立复跑零命中(exit 1) |
| 8 | scans/ 五档 258 命中全部三态销号,每档尾部对账等式可复算 | ✓ VERIFIED | 逐档等式独立复核:gates 7+83=90、ruff 5+64=69、vulture 1+0=1、eslint 0+29=29、secrets 2+67=69;跨档交叉和 确认 15 + 误报 243 + 移交 0 = 258 ✓;15 条确认项去向列逐条有下落(F-TOOL-05/06、F-CODE-01、HYP-12/25、降级理由) |
| 9 | 零 diff 红线:apps/ scripts/ docs/ 相对基线 5927f36 零改动 | ✓ VERIFIED | 验证时独立执行 `git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空;`git status --porcelain` 三目录无任何残留 |
| 10 | 14 条指定 HYP(CODE 10 + TOOL 4)全部回填并附 file:line@5927f36 证据 | ✓ VERIFIED | 逐条提取 14 个 ID 状态:HYP-01/04/07/09/10/12/17/19/20 证实、HYP-03/08/15/16/18 细化,全部 ≠ 未验证且携证据字段;余 11 条未验证均属 Phase 4 维度(独立计数 = 11) |
| 11 | HANDOFF-PHASE4.md 移交清单定稿封版 | ✓ VERIFIED | 6 条移交(DOC 3 + TEST 3)独立计数吻合,每条含去向 + 观察 + `@ 5927f36` 行号,尾部封版行注明被移交 HYP 状态未动(D-11) |
| 12 | D14-1~6 六条移交线索逐条经三要素裁定,各有独立下落并反向串联 | ✓ VERIFIED | COVERAGE 深挖点登记节:D14-2→F-CODE-07、D14-3→F-TOOL-08、D14-4→F-CODE-08 立发现(三要素裁定段写入证据字段),D14-1/5/6 "不构成债务"结论附三要素理由;CONTRACT-MATRIX ③ 6 条移交记录每条有明确下落(RPT-08),F-CODE-07/08、F-TOOL-08 关联字段反向引用矩阵行 |
| 13 | COVERAGE.md 完成判定节成立,对账等式可复算;微基准档案含命令+环境+结果+复跑说明 | ✓ VERIFIED | 完成判定 10 条逐项独立复算全部成立(见下 Info 项 1 的唯一措辞瑕疵);scans/microbench-sha256.md 含导出命令、Node v22.18.0/darwin-arm64 环境表、"Mac 非真机量级参考"限定与复跑说明 |

**Score:** 13/13 truths verified(0 present, behavior-unverified — 文档型阶段,无运行时行为面)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `.planning/audit/COVERAGE.md` | 63 对象覆盖台账 + 深挖点登记 + 完成判定 | ✓ VERIFIED | 158 行,63 对象行全 9/9,20 深挖点全下落,完成判定 10 条可复算 |
| `.planning/audit/findings/code.md` | worker/fc/miniprogram F-CODE 条目 | ✓ VERIFIED | F-CODE-01~08(MEDIUM 2 / LOW 6),九字段 schema 合规,证据抽查通过 |
| `.planning/audit/findings/toolchain.md` | F-TOOL 条目(工具级定级) | ✓ VERIFIED | F-TOOL-01~08(MEDIUM 2 / LOW 6),含 HYP-07 结论条目 F-TOOL-05 |
| `.planning/audit/HYPOTHESES.md` | 14 条 HYP 回填 | ✓ VERIFIED | 14/14 状态回填,11 条余量均 Phase 4 维度,尾部进度封版行与实态一致 |
| `.planning/audit/HANDOFF-PHASE4.md` | 移交清单封版 | ✓ VERIFIED | 6 条(DOC 3 + TEST 3),封版行完整 |
| `.planning/audit/scans/gates-baseline.md` | 门禁直调存档 + 销号表 | ✓ VERIFIED | 1125 行,90 命中销号,等式 7+83+0=90 ✓ |
| `.planning/audit/scans/ruff-extended.md` | 扩展规则集存档 + 销号表 | ✓ VERIFIED | 848 行,69 命中销号,等式 5+64+0=69 ✓ |
| `.planning/audit/scans/vulture.md` | 死代码扫描存档 + 销号表 | ✓ VERIFIED | 1 命中确认销号(ruff #49 同点互证) |
| `.planning/audit/scans/eslint.md` | JS 侧临时扫描存档 + HYP-15 量化小结 | ✓ VERIFIED | 29 命中全误报销号,0 error/29 warning 量化底数在档 |
| `.planning/audit/scans/secrets.md` | 五类秘密扫描存档(脱敏) | ✓ VERIFIED | 69 命中销号,仅 path:line + 模式名,#14/#15 → F-TOOL-05 去向闭环 |
| `.planning/audit/scans/microbench-sha256.md` | D-16 微基准档案 | ✓ VERIFIED | 命令 + 环境 + 结果 + 复跑说明齐备,非销号类不入 258 等式 |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| COVERAGE.md 对象清单 | 03-RESEARCH.md 全量清单 | 行数含逐行一致 | ✓ WIRED | 行数抽查 5 处与 `git show 5927f36 \| wc -l` 全部一致 |
| scans/ 确认项 | findings F-ID / HYP 移交 | 去向列回填 | ✓ WIRED | 15 条确认项去向零空置(gates #1→F-TOOL-06、#2-7→HYP-25、ruff #55→F-CODE-01、secrets #14/#15→F-TOOL-05 等) |
| F-CODE/F-TOOL 证据字段 | git show 5927f36 可复现引用 | path:line@SHA | ✓ WIRED | 6 条发现证据逐一回溯基线代码核实,全部准确(见证据抽查) |
| D14 裁定条目 | CONTRACT-MATRIX ③ 移交记录 | 逐条销号 + 反向引用 | ✓ WIRED | 6 条 D14 各有明确下落;矩阵为 Phase 2 封版文档,销号落 Phase 3 侧(COVERAGE 登记节 + findings 关联字段),可追溯闭环成立 |
| HYP 回填 | HANDOFF-PHASE4.md / findings | 状态 + 证据双写 | ✓ WIRED | HYP-07→F-TOOL-05、HYP-15→F-TOOL-04、HYP-17→F-CODE-05;被移交 HYP(14/16 半句/22/25)状态未动 |

### 证据抽查(反捏造核验,全部经 `git show 5927f36`)

| 发现 | 声明 | 基线实态 | 结论 |
| ---- | ---- | -------- | ---- |
| F-CODE-01 | poller.py:248-250 `process_plan` 声明 fragments_root 未使用 | 签名吻合,函数体 :251-292 零 fragments_root 引用 | ✓ 属实 |
| F-CODE-06 | uploader.js:72 uploading 先落盘;queue_runtime.js:198,221 仅拾取两态;uploads_view.js:25-39 无 uploading | 三处逐行吻合 | ✓ 属实 |
| F-CODE-07 | nls.py:45-46 独立字面量,MAX 非 len 派生 | `RETRY_DELAYS_SECONDS = (5.0, 15.0, 45.0)` / `MAX_RETRIES = 3` | ✓ 属实 |
| F-TOOL-05 | test_asr.py:79-81 已过期预签名 URL(Expires→2026-05 末) | DEFAULT_FILE_LINK 确为签名 URL,Expires=1780035733 已过期,TMP. 前缀 STS 形态 | ✓ 属实 |
| F-TOOL-06 | app.py:14 部署态导入 + mypy files 含 apps/fc/shared → 门禁恒红 | `from handler import handler as application`;pyproject:32 吻合 | ✓ 属实 |
| F-TOOL-07 | Makefile:19 .PHONY 含 lint-miniprogram 而无规则 | .PHONY 列表含该条目,`^lint-miniprogram:` 规则 0 命中 | ✓ 属实 |

### Behavioral Spot-Checks

Step 7b: SKIPPED(文档型审计阶段,无本阶段产出的可运行代码;等价核验为上表对账等式独立复算与证据基线回溯)。已知前置条件:`make test` 的 2 个环境依赖失败(test_run_retranscribe_config_missing / test_cli_run_command_is_placeholder)系里程碑前既有 SONISCOPE_HOME 环境问题,本阶段仅改动 .planning/,非阶段缺口。

### Probe Execution

无 PLAN/SUMMARY 声明的 probe 脚本;`scripts/*/tests/probe-*.sh` 约定路径不存在。SKIPPED。

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| AUDIT-01 | 03-01/02/03/04/07 | 三层主体代码债务盘点,工具输出仅作线索,逐条人工核实 | ✓ SATISFIED | 47 CODE 对象全覆盖 9/9,F-CODE-01~08,scans/findings 分离,证据抽查通过 |
| AUDIT-02 | 03-01/02/05/06/07 | scripts/、Makefile、fc_deploy 等工具链审计 | ✓ SATISFIED | 16 TOOL 对象全覆盖 9/9,F-TOOL-01~08 含 fc_deploy(F-TOOL-02)、Makefile(F-TOOL-06/07)、test_asr.py(F-TOOL-05) |

孤儿需求检查:REQUIREMENTS.md 映射 Phase 3 的需求仅 AUDIT-01/AUDIT-02,均被计划声明。无孤儿需求。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| .planning/audit/COVERAGE.md | 136 | 完成判定 #3 的字面命令 `grep -c '\| 9/9 \|'` 实际返回 64(判定行自匹配),声明值 63 | ℹ️ Info | 实质声明为真:63 个对象行全部 9/9(经行号分析,第 64 个匹配即判定行本身);判定 #2 已用字符类写法避免自匹配而 #3 未用,纯措辞瑕疵,不影响任何结论 |
| findings/*.md | 7-19 | F-*-00 schema 示例含占位文本 | ℹ️ Info | 显式声明"Phase 5 汇总时剔除"的示例条目,非 stub |

零 diff 红线、秘密反扫、debt-marker 扫描均通过:交付物内无未引用后续工作的 TBD/FIXME/XXX;`.planning/audit/` 全目录秘密模式反扫零命中。

### Human Verification Required

无。唯一的人工检查点(03-01 Task 2 临时仪器包合法性,blocking-human)已在执行中解决——scans/vulture.md 与 scans/eslint.md 均记录"包合法性已经 03-01 Task 2 人工批准",两仪器实际运行且版本在档。

### Gaps Summary

无缺口。阶段目标经目标反推验证成立:63 个审计对象全部落格且行数与基线实测一致;16 条发现(F-CODE 8 + F-TOOL 8)九字段 schema 合规且证据抽查 6/6 与 `git show 5927f36` 基线代码吻合(无捏造、无原始工具输出冒充发现);258 条工具命中全部三态销号且五档对账等式独立复算成立;14 条指定 HYP 全部回填;6 条 D14 移交线索逐条裁定有下落;契约类观察零越界判断;零 diff 红线与秘密脱敏红线全程保持。

---

_Verified: 2026-07-05_
_Verifier: Claude (gsd-verifier)_
