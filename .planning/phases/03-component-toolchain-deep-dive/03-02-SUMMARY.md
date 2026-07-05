---
phase: 03-component-toolchain-deep-dive
plan: 02
subsystem: audit
tags: [audit, triage, static-analysis, secrets, gsd]
requires:
  - "03-01: 五份扫描档案(scans/)与空销号表骨架"
provides:
  - "五份 scans/ 档案的三态销号表(258 命中全部销号)"
  - "03-03/03-04/03-05/03-06 深挖线索清单(确认 15 项)"
  - "eslint.md HYP-15 量化小结(0 error / 29 warning 漏报面底数)"
  - "scans/ 秘密反扫零命中 + 零 diff 收尾记录"
affects: [03-03, 03-04, 03-05, 03-06, phase-5-report]
tech-stack:
  added: []
  patterns:
    - "三态销号(确认/误报/移交)+ 可复算对账等式(Phase 2 先例沿用)"
    - "秘密类证据仅 path:line + 模式名,零值本体(Pitfall 7)"
key-files:
  created: []
  modified:
    - .planning/audit/scans/gates-baseline.md
    - .planning/audit/scans/ruff-extended.md
    - .planning/audit/scans/vulture.md
    - .planning/audit/scans/eslint.md
    - .planning/audit/scans/secrets.md
key-decisions:
  - "apps/fc/tests/ 的 35 条 ruff 扩展命中逐条核实后全判误报(pytest/WSGI/Protocol 签名契合惯例或自述假值),不移交 Phase 4 TEST——五档移交项为零,HANDOFF-PHASE4.md 无需追加"
  - "mypy 门禁唯一命中(app.py:14 部署态导入)确认为 03-06 深挖线索(门禁在仓内结构性不可绿),交叉 03-04 HYP-12"
  - "eslint 29 条 warning 全误报(仓库惯例内写法),但检出面与 miniprogram_lint 规则面完全不重叠——HYP-15 量化参照落档供 03-05 引用"
  - "nls.py DTZ011 核实为本地成本分日键(单机自洽)判误报,不升级为跨组件日期契约问题"
metrics:
  duration: "~15 min"
  completed: 2026-07-05
status: complete
---

# Phase 3 Plan 02: 扫描命中三态销号 Summary

**One-liner:** 258 条工具命中经 git show 5927f36 逐条人工核实后三态销号完毕(确认 15 / 误报 243 / 移交 0),五档对账等式成立,15 条确认项形成 03-03~03-06 深挖线索输入,秘密红线反扫零命中。

## What Was Done

### Task 1: Python 侧线索销号(commit 0d3961a)

- **gates-baseline.md(90 命中 = mypy 1 + ruff 89 + miniprogram_lint 0):** 确认 7 + 误报 83 + 移交 0。
  - mypy 唯一命中(`apps/fc/shared/app.py:14` import-not-found)核实为部署态导入(handler.py 仅在部署 zip 内同目录)——strict 门禁在仓内直调必红,确认 → 03-06 Makefile/门禁口径深挖,交叉 03-04 HYP-12。
  - `scripts/test_asr.py` 6 条(UP009/E501×4/B904)均属门禁规则集(E,F,I,UP,B)内真实违例,确认 → 03-06(HYP-25 scripts 门禁覆盖缺口实证)。
  - vendored 80 条(分文件聚合 19 行,条数复算 80 ✓)与 scripts/ralph 3 条按 CHARTER 排除清单 #1/#2 判误报(存在级问题 D-09 另行承接)。
- **ruff-extended.md(69 命中):** 确认 5 + 误报 64 + 移交 0。探针信号(S110/S104/DTZ/S105/S106/ARG)逐条核实未批量定性。确认项:
  - `app.py:27` S104(0.0.0.0 绑定)→ 03-04(HYP-12)
  - `fc_deploy.py:419` ARG001(rollback_one 的 timestamp 形参被忽略,始终回滚最新备份)→ 03-05
  - `fc_deploy.py:688` ARG002(fetch_logs 的 hours 时间窗被静默忽略)→ 03-05
  - `miniprogram_lint.py:121` ARG001(scan_hardcoded_secrets 的 rel_path 落空)→ 03-05(HYP-15)
  - `poller.py:249` ARG001(process_plan 的 fragments_root 形参未使用,疑遗留 API 面)→ 03-03
- **vulture.md(1 命中):** 确认 1(与 ruff ARG001 同点互证,非 RESEARCH A1 预记的动态引用误报类)→ 03-05。

### Task 2: JS 侧与秘密扫描销号 + 收尾(commit 4751d38)

- **eslint.md(29 命中):** 确认 0 + 误报 29 + 移交 0。全部为仓库惯例内写法:catch(e) 形参未用 ×21、`== null` 故意宽松判空 ×7、logger.js 遗留 eslint-disable 注释 ×1(HYP-15 旁证)。尾部落档 HYP-15 量化小结:增量检出零真实缺陷,但 ESLint 语义类规则面与 miniprogram_lint 现有规则面(域名/密钥/四文件)完全不重叠,供 03-05 判断是否立发现。
- **secrets.md(69 命中):** 确认 2 + 误报 67 + 移交 0。`scripts/test_asr.py:80` 双模式命中(签名 URL + 签名参数)确认 → 03-06(HYP-07),表中零值本体(Pitfall 7 全程遵守);LTAI 10 条均为测试自述假值,security_token 51 条均为标识符/注释红线声明/测试假值/文档占位(sts.py 三条引 DNF-04),app_secret 3 条均为字段名或 runbook 占位符。
- **收尾核验(记录于 secrets.md 尾部):** scans/ 三模式反扫零命中;`git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空。

## 对账等式(五档全部成立)

| 档案 | 确认 | 误报 | 移交 | 总数 |
|------|------|------|------|------|
| gates-baseline.md | 7 | 83 | 0 | 90 ✓ |
| ruff-extended.md | 5 | 64 | 0 | 69 ✓ |
| vulture.md | 1 | 0 | 0 | 1 ✓ |
| eslint.md | 0 | 29 | 0 | 29 ✓ |
| secrets.md | 2 | 67 | 0 | 69 ✓ |
| **合计** | **15** | **243** | **0** | **258 ✓** |

## 深挖线索输出(供后续计划机械提取)

- **03-03(worker 核心):** poller.py:249(fragments_root 遗留形参)
- **03-04(FC/小程序):** app.py:27 S104 + app.py:14 部署态导入交叉(均 HYP-12)
- **03-05(worker 运维工具链):** fc_deploy.py:419、fc_deploy.py:688、miniprogram_lint.py:121(×2 工具互证,HYP-15);eslint.md HYP-15 量化小结引用点
- **03-06(scripts/Makefile):** mypy 门禁不可绿(app.py:14)、test_asr.py 门禁违例 ×6(HYP-25)、test_asr.py:80 签名 URL ×2(HYP-07)

## Deviations from Plan

None - plan executed exactly as written。唯一裁量点:五档核实后移交项为零,HANDOFF-PHASE4.md 按计划验收条款("无移交项则档案记'本档无移交项'")未作追加,五档各已记录移交说明。

## Known Stubs

无(本计划为纯审计文档写入,不涉及产品代码)。

## Threat Flags

无新增威胁面。威胁登记表 T-03-01(销号表截入秘密值)经 Task 2 反扫门禁验证缓解到位(零命中);T-03-02(基线篡改)经零 diff 验证缓解到位(输出为空);T-03-SC 如计划所述未安装任何包,全程仅 git show 取证。

## Commits

| Task | Commit | 内容 |
|------|--------|------|
| 1 | 0d3961a | gates-baseline / ruff-extended / vulture 销号表 |
| 2 | 4751d38 | eslint / secrets 销号表 + 收尾反扫记录 |

## Self-Check: PASSED

- [x] 5 份 scans/ 档案对账等式含 ✓ 且三数之和等于命中总数
- [x] 销号列无空值(gates 29 行 / ruff-ext 69 行 / vulture 1 行 / eslint 29 行 / secrets 69 行)
- [x] scans/ 反扫 `OSSAccessKeyId=[0-9A-Za-z]{8,}|Signature=…|LTAI…` 零命中
- [x] `git diff --stat 5927f36 -- apps/ scripts/ docs/` 为空
- [x] commit 0d3961a、4751d38 存在于 git log
