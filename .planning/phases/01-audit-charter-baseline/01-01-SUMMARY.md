---
phase: 01-audit-charter-baseline
plan: 01
subsystem: audit-docs
tags: [audit-charter, findings-ledger, baseline, severity, schema]
requires: []
provides:
  - ".planning/audit/CHARTER.md — CHARTER-01~05 全部规则:基线声明、范围与方法、排除清单、秘密扫描规则、严重度体系、工作量分档、发现 schema"
  - ".planning/audit/findings/{contract,code,toolchain,docs-config,test}.md — 五维度台账骨架(表头 + 00 号 schema 示例)"
affects:
  - "01-02(HYPOTHESES.md / DO-NOT-FIX.md 引用本章程 ID 规则与证据格式)"
  - "Phase 2-5(全部审计执行以 CHARTER.md 为唯一标尺)"
tech-stack:
  added: []
  patterns:
    - "证据一律出自 git show 5927f36:<path>,免疫 HEAD 推进"
    - "台账按维度分五文件,Phase 2/3 并行写入防冲突"
key-files:
  created:
    - .planning/audit/CHARTER.md
    - .planning/audit/findings/contract.md
    - .planning/audit/findings/code.md
    - .planning/audit/findings/toolchain.md
    - .planning/audit/findings/docs-config.md
    - .planning/audit/findings/test.md
  modified: []
key-decisions:
  - "完整基线 SHA 全文只在 CHARTER.md 头部声明一次,正文统一短 SHA 5927f36(D-02)"
  - "严重度边界以锚点示例封死:无法对号入座的发现取影响最接近的锚点级别并在理由中写明对应关系——不留裁量措辞"
  - "顺带安全发现不设自动升级,同用影响×可能性定级,仅加 out-of-dimension 标注"
  - "九字段 schema 在 CHARTER-05 七字段之上追加「上线判定」「状态」两槽,避免 Phase 5 改 schema 返工"
duration: ~10min
completed: 2026-07-04
status: complete
---

# Phase 1 Plan 01: 审计章程与 findings 台账骨架 Summary

审计章程 CHARTER.md 定稿(基线 5927f36、五级严重度 SoniScope 锚点、S/M/L/XL 四档、九字段发现 schema、九条排除清单、五类秘密扫描穿透模式)+ findings/ 五维度台账骨架,Phase 2–5 任何审计者可直接套用。

## What Was Built

### CHARTER.md(Task 1 + Task 2)

- **审计基线(CHARTER-01,D-01~D-04):** 完整 SHA 头部声明恰一次;证据格式 `path:line @ 5927f36`;取证标准做法 `git show 5927f36:<path>`(禁止工作树取证);零 diff 命令 `git diff --stat 5927f36 -- apps/ scripts/ docs/` 逐字写定,附覆盖面说明(根文件靠"证据一律出自 5927f36"兜底);D-04 无例外协议保留绝对措辞(云端操作绝不由审计者动手,一律只进台账标 BLOCKER);dirty-tree 处置成文为记录事实(旧文档迁移已随提交入库)。
- **范围与方法(CHARTER-04):** 五维度表(CON→P2、CODE/TOOL→P3、DOC/TEST→P4)、五条明确排除项(FC 直转目标态、渗透深度、vendored 逐行、数值评分、精确工时)、双语言适配声明、三条已实测取证命令。
- **扫描排除清单(D-05/D-06/D-09):** 九条路径表格(start-fc-main、scripts/ralph、.claude/、.cursor/、.codex/、.agents/、openspec/、build/、tests/audio);scripts/ 审计缩窄为三个文件;存在级问题照常进台账(LOW/INFO 预期)。
- **秘密扫描穿透规则(D-07):** 五类模式命令(LTAI、OSSAccessKeyId=、Signature=、appsecret、SecurityToken)对基线 commit 全量扫描穿透所有排除目录;`test_asr.py` 过期预签名 URL 先例作为穿透理由;命中 ≠ 发现(人工核实后进台账);秘密类证据红线:只引 `path:line @ 5927f36` + 模式名,绝不复制值本体。
- **严重度体系(CHARTER-02):** 五级 SoniScope 场景锚点(CRITICAL=数据丢失/有效凭证泄露/认证绕过,HIGH=静默转写失败/STS 越界/恢复损坏,MEDIUM=潜伏失配/误导文档/过期凭证入库,LOW=技术债/死链/覆盖缺口,INFO=存在级观察);评级理由固定一行"影响:…;可能性:…",禁止数值评分;全文零裁量措辞。
- **工作量分档(CHARTER-03):** S/M/L/XL 判定标准照需求原文 + 每档一个 SoniScope 示例;禁止小时级精确估计,全文无"数字+小时"表达。
- **发现 schema 与台账布局(CHARTER-05):** 九字段固定顺序(ID/维度/严重度/证据/修复建议/工作量/关联发现/上线判定/状态);ID 规则 F-CON/F-CODE/F-TOOL/F-DOC/F-TEST-NN + HYP-NN + DNF-NN;五文件分维度布局及并行防冲突理由;台账严禁写入零 diff 保护区。

### findings/ 骨架(Task 3)

五个文件结构相同:头部(维度名 + 写入阶段 + ID 前缀 + schema 权威指向 CHARTER.md)、00 号 schema 示例条目(九字段与章程逐字段一致,标注"Phase 5 汇总时剔除")、空`## 发现`节供 append。

## Task Commits

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | CHARTER.md 前半部(基线/范围/排除/秘密扫描) | ada9c16 |
| 2 | CHARTER.md 追加严重度/工作量/schema | 1bea3fb |
| 3 | findings/ 五维度台账骨架 | f2057fa |

## Verification

- Task 1/2/3 automated verify 全部通过(完整 SHA 恰 1 次、五级术语齐、九排除路径齐、无"数字+小时"、无"视情况/可酌情"、schema 字段齐)
- 零 diff 不变量每 task 收尾均验证:`git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空
- 本 plan 全程未对 apps/、scripts/、docs/ 做任何 Edit/Write(威胁 T-01-02 缓解落实)
- 秘密扫描章节未复制任何秘密值本体,先例引用仅提文件与模式名(威胁 T-01-01 缓解落实)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

findings/ 五文件的 00 号条目为计划明确要求的 schema 示例占位(非真实发现),已标注"Phase 5 汇总时剔除"——这是刻意设计,不阻碍本 plan 目标。

## Threat Flags

None — 纯文档产出,无新增安全面;T-01-01/02/03 三项 mitigate 处置均已在章程条款与执行过程中落实。

## Self-Check: PASSED
