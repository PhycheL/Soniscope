---
phase: 03-component-toolchain-deep-dive
plan: 03
subsystem: audit
tags: [audit, worker, code-dimension, static-analysis, hypotheses]
requires:
  - 03-01 (scans archives, baseline export, COVERAGE skeleton)
  - 03-02 (scan dispositions, confirmed leads routing)
provides:
  - findings/code.md worker 侧 F-CODE-01~04 四条发现
  - COVERAGE.md CODE 维度 worker 14 行落格(9/9)
  - HYPOTHESES.md HYP-10/16/19 回填(证实/细化/证实)
  - HANDOFF-PHASE4.md HYP-16 文档一致性半句移交
affects:
  - 03-04 (HYP-08 证据已备,FC 侧合并后回填)
  - 03-07 (D14-1/D14-2 证据就位待裁定;COVERAGE 完成判定)
  - Phase 4 (HYP-16 DOC 半句移交)
  - Phase 5 (F-CODE 条目入报告汇总)
tech-stack:
  added: []
  patterns:
    - git show 5927f36 取证(禁读工作树)
    - 九字段发现 schema(CHARTER)
    - D-12 深挖点显式"无发现"落格
key-files:
  created: []
  modified:
    - .planning/audit/findings/code.md
    - .planning/audit/COVERAGE.md
    - .planning/audit/HYPOTHESES.md
    - .planning/audit/HANDOFF-PHASE4.md
    - .planning/audit/scans/ruff-extended.md
decisions:
  - "F-CODE-02 定级 MEDIUM:转码失败路径使无界重下循环具备现实触发条件(一次损坏上传),按潜伏失配锚点定级"
  - "HYP-16 回填为'细化'而非'证实':代码半句证实,文档一致性半句移交 Phase 4 DOC"
  - "HYP-10/16 可接受自评经 D-10 上线语境裁定成立,记 RPT-06 优点候选兼 DNF 候选,不占发现 ID"
  - "oss_admin 契约观察以 COVERAGE 备注注明 Phase 2 矩阵覆盖(F-CON-01/02/03),不入 HANDOFF DOC/TEST 节"
metrics:
  duration: ~35 min
  completed: 2026-07-05
  tasks: 3
  files-modified: 5
status: complete
---

# Phase 3 Plan 03: apps/worker 核心 14 模块普审与深挖 Summary

**One-liner:** worker 核心 14 模块(4,871 行)逐模块 9 面普审 + 深挖完成,产出 F-CODE-01~04 四条发现(1 MEDIUM + 3 LOW),HYP-10/16/19 闭环回填,基线零污染。

## 完成内容

### Task 1: 四大模块深挖(pipeline / nls / cli / poller,2,747 行)— commit 415f43f

- **pipeline.py(875)深挖 HYP-10:** 证实串行单线程(`:407-441` 逐条 for 循环 + `:485-506` 单线程主循环);`.done` 最后写(`:274`/`:367`)、任一阶段失败不建 `.done`、原子写协议全路径核查通过。无发现。
- **nls.py(740)深挖 HYP-19 + D14-2:** 2018-08-17 filetrans API 依赖证实(`verify_prep.py:87` 常量,`nls.py:454-455` 消费,legacy aliyunsdkcore);D14-2 证据只记不裁(D-15):`RETRY_DELAYS_SECONDS = (5.0, 15.0, 45.0)` 与 `MAX_RETRIES = 3` 均为独立字面量(`nls.py:45-46`),非 `len()` 派生,当前 3 == len 自洽。RESIGN_THRESHOLD 续签逻辑无静默失败;秘密仅入 SDK 参数不入日志。无发现。
- **cli.py(601)普审:** 全部子命令统一 `(lines, exit_code)` → `typer.Exit` 边界转换完整;`oss-delete-obj` 双闸门测试专用。COVERAGE 保持"TOOL 子命令入口"口径。无发现(docstring 滞后属 face7 轻微,备注记录)。
- **poller.py(531)深挖 HYP-10/16 + D14-1 + 销号确认项:**
  - **F-CODE-01(LOW):** `process_plan` 声明 `fragments_root` 形参未使用(`:248-250`)——ruff #55 确认项人工核实立发现。
  - **F-CODE-02:** sha256 失配对象每轮全量重下无失败计数/隔离/告警(`:272-284` + `pipeline.py:412-422`)。
  - D14-1 证据只记不裁:Worker 侧 sha256 比对 `:261,272-284`(stdlib hashlib 经 fixtures.sha256_of)。
  - `fragment_id_from_key` 往返校验(`:47-61`)契约观察 → Phase 2 矩阵已覆盖,不判断(成功判据 4)。

### Task 2: 其余 10 模块普审(2,124 行)— commit 84d12ec

- **recovery.py:** **F-CODE-03(LOW)** — `atomic_write_text` mkstemp 崩溃窗口的孤儿 `*.tmp` 残留在 fragment 目录,三段恢复扫描与 verify-no-stale 均不覆盖。三段清理误删面核查通过(仅中间态后缀,`.done` 无删除路径)。
- **audio.py:** **F-CODE-02 增补证据并升级 MEDIUM** — 转码/探测失败留档 inbox/failed/ 不阻止下轮重下(`_archive_failed` docstring "不再重试"与实态相悖),无界重试循环获得现实触发条件(一次损坏上传)。
- **paths.py:** **F-CODE-04(LOW)** — `.env` 自 CWD 无界向上搜索直至根目录(`:38-46`),与错误信息/config.py 注释"仓库根目录 .env"口径不符。
- **manifest.py / oss_admin.py / transcriber.py / config.py / locks.py / __main__.py / __init__.py:** 无发现。transcriber DNF-01 对照命中按负面清单排除;oss_admin 契约观察注明 Phase 2 矩阵行覆盖;config HYP-08 证据落 COVERAGE 备注(MaskedSecret `:31-35`、chmod 判定 `:148-150` CLI 侧仅警告、`mask_secret` 9-16 字符短秘密暴露占比边界细节),回填留 03-04 合并 FC 侧。

### Task 3: HYP 回填与销号反填 — commit 51fbe5c

- **HYP-10:** 证实 — 串行单进程属实;可接受自评成立 → RPT-06 优点候选兼 DNF 候选。
- **HYP-16:** 细化 — 代码半句证实;文档一致性半句移交 Phase 4 DOC(HANDOFF-PHASE4.md);F-CODE-02 交叉引用。
- **HYP-19:** 证实 — 2018 API 依赖属实;Transcriber/NlsBackend 双层 Protocol 隔离充分,替换引擎不动流水线;direct 模式为短期退路。
- **销号反填:** ruff-extended.md #55 去向改为 F-CODE-01;scans/ 三档无其余"03-03"占位残留(vulture 唯一确认项去向 03-05,不属本计划)。
- **零 diff 验证:** `git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空 ✓。

## 发现汇总

| ID | 严重度 | 标题 | 工作量 |
|----|--------|------|--------|
| F-CODE-01 | LOW | process_plan 未使用 fragments_root 形参(遗留 API 面) | S |
| F-CODE-02 | MEDIUM | 持久性失败对象(sha256 失配/转码失败)无界重下重试,无计数/隔离/告警 | M |
| F-CODE-03 | LOW | 原子写崩溃窗口孤儿 *.tmp 无清理路径(fragment 目录内) | S |
| F-CODE-04 | LOW | .env 无界向上搜索与"仓库根目录"文档口径不符 | S |

## Deviations from Plan

None - plan executed exactly as written.(F-CODE-02 的跨任务证据增补与升级属计划内普审产出的正常合并,发现状态均为 draft,Phase 5 校准。)

## 移交与未尽事项

- **HYP-08 未回填(计划内约定):** config.py 侧证据已采,回填在 03-04 合并 FC env.py/audit.py 侧证据后执行。
- **D14-1/D14-2 未裁定(计划内约定,D-15):** 定义形态与行号证据已记 COVERAGE 备注,03-07 裁定。
- **REQUIREMENTS(AUDIT-01)未标记完成:** AUDIT-01 覆盖 worker + fc + miniprogram 三层,本计划仅完成 worker 份额;03-04/03-05 完成后由收口计划/orchestrator 统一处理。
- **上下文余量:** 14 模块全部完整读毕,无未审余量。

## Commits

| Task | Commit | 内容 |
|------|--------|------|
| 1 | 415f43f | 四大模块深挖,F-CODE-01/02,COVERAGE 4 行 |
| 2 | 84d12ec | 10 模块普审,F-CODE-03/04,F-CODE-02 升级,COVERAGE 10 行,HANDOFF 1 条 |
| 3 | 51fbe5c | HYP-10/16/19 回填,销号 #55 反填,零 diff 验证 |

## Self-Check: PASSED

- SUMMARY.md 存在 ✓;任务提交 415f43f/84d12ec/51fbe5c 均在 git log ✓
- 工作树无未提交改动、无未跟踪文件 ✓;`git diff --stat 5927f36 -- apps/ scripts/ docs/` 为空 ✓
