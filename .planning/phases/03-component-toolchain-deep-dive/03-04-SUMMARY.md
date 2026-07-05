---
phase: 03-component-toolchain-deep-dive
plan: 04
subsystem: audit
tags: [audit, fc, miniprogram, coverage, hypotheses, static-analysis]

# Dependency graph
requires:
  - phase: 03-component-toolchain-deep-dive
    plan: 03
    provides: worker 14 行 COVERAGE 落格、F-CODE-01~04、HYP-10/16/19 回填、HANDOFF DOC 节骨架
provides:
  - COVERAGE.md CODE 维度 47 行全部落格(worker 14 + fc 12 + miniprogram 21,9/9 面)
  - findings/code.md F-CODE-05(FC 无频控/配额面)与 F-CODE-06(uploading 死态)
  - HYPOTHESES.md HYP-01/08/09/12/17/20 六条回填(累计 9/25,CODE 维度仅余 HYP-03)
  - HANDOFF-PHASE4.md HYP-14 两条 DOC 移交(config.js ENV、dev.js 门控)
  - scans/ruff-extended.md #1 S104 人工核实下落回填
  - D14-1/2/4/5/6 证据行号登记(COVERAGE 备注,未下裁定,供 03-07)
affects:
  - 03-07(D14 裁定 + HYP-03 微基准 + COVERAGE 完成判定收口)
  - Phase 4(HYP-14 DOC 移交、HYP-16 文档一致性半句)
  - Phase 5(F-CODE-05/06 上线判定、RPT-06 优点候选、DNF 候选裁定)

# Tech tracking
tech-stack:
  added: []
  patterns: [静态审计零改码, git show 基线取证, 九字段发现 schema, 三态销号]

key-files:
  created: []
  modified:
    - .planning/audit/COVERAGE.md
    - .planning/audit/findings/code.md
    - .planning/audit/HYPOTHESES.md
    - .planning/audit/HANDOFF-PHASE4.md
    - .planning/audit/scans/ruff-extended.md

key-decisions:
  - "app.py S104 bind-all 销号:FC 容器内 0.0.0.0 为自定义运行时必需形态,平台网关为唯一公网入口,降级不立发现"
  - "HYP-17 无自评可接受条目,深挖证实后立 F-CODE-05(LOW):频控缺失属成本/可用性面,爆炸半径受单 key policy 约束"
  - "uploading 死态定级 MEDIUM(潜伏类):与 F-CODE-02 无界重试同口径,正常完成流程不触发、进程中断即爆"
  - "FC 侧 plain-str dataclass 无类型级掩码作为 HYP-08 细化边界记录,不立发现(现有调用点全部只传安全标量)"
  - "深挖点登记表的下落列留给 03-07 收口统一回填,避免与并行 TOOL 计划(03-05)产生同表写冲突"

# Metrics
duration: ~50min
completed: 2026-07-05
status: complete
---

# Phase 3 Plan 04: apps/fc 与 apps/miniprogram 全模块普审 + 线索深挖 Summary

**FC 12 文件与小程序 21 文件逐文件 9 面过审落格,立 F-CODE-05(FC 无频控)与 F-CODE-06(uploading 死态)两条发现,回填 HYP-01/08/09/12/17/20 六条,CODE 维度三层主体代码盘点完成。**

## Accomplishments

- **Task 1(apps/fc 12 文件,1,120 行):** 逐文件 `git show 5927f36` 完整读 + 9 面过审。深挖下落:HYP-09/17(sts.py 单 key policy 精确单 key/仅 PutObject/恒 900s,策略实现无缺陷;handler 全链路无频控 → F-CODE-05)、HYP-12(wsgiref 生产运行时证实,MVP 自评经 D-10 裁定成立)、HYP-08(env.py 缺失只报变量名、audit.py 双层洗涤核实,FC 侧无类型级掩码作细化边界)。DNF-03(两 handler mypy 豁免)与 DNF-04(原始 STS 下发)对照零误立;errors.py 错误码真值源证据记 COVERAGE 备注供 03-07 D14-3;S104 销号确认项人工核实下落回填 scans/ruff-extended.md #1(降级理由,不立发现)。提交 `cca1ddc`。
- **Task 2(apps/miniprogram 21 文件,3,406 行):** 逐文件完整读 + 9 面过审,判断基准为仓库既有惯例。队列状态机普审发现漏态:`uploading` 残留项不被自动驱动拾取(仅 queued/pending_verify)、不在任何可操作按钮集合、不计积压提示 → F-CODE-06(MEDIUM,五文件共证)。D14-1(sha256 调用端 index.js:30,640 + 主线程同步全量哈希)、D14-2(uploader.js:28/verify.js:16 重试常量,JS 侧 length 派生)、D14-4(uploads.js:330-370 与 queue_runtime.js:94-128 同构两份)、D14-5(config.js:10-15 硬编码真实云值)、D14-6(fragmentIdFromObjectKey :38-44 无校验切割)证据全部只记不裁。HYP-14 两处顺带证据(config.js:29 ENV='development' 现值、dev.js 三重门控)移交 HANDOFF DOC 节,HYP-14 状态未动;DNF-02 拼写域名对照零误立;eslint.md 销号表零"确认"项,无待回填去向。提交 `a9008d6`。
- **Task 3(HYP 六条回填):** HYP-01/20 证实(git ls-tree 无 transcribe_audio/,现役转写全在 Worker 侧,D-12 存在级不占发现 ID);HYP-08 细化(存放形态证实,"Strong" 评价成立 + 两处细化边界:600 权限仅警告不拒载、FC plain-str dataclass);HYP-09 证实(D-10 裁定自评成立,RPT-06/DNF 候选);HYP-12 证实(D-10 成立,DNF 候选);HYP-17 证实(备注引 F-CODE-05)。尾部统计行更新为累计 9 条(03-03 的 3 + 本计划 6),CODE 维度仅余 HYP-03 待 03-07 微基准。提交 `3710c2f`。

## Task Commits

| Task | Name | Commit |
|------|------|--------|
| 1 | apps/fc 12 文件普审+深挖 | `cca1ddc` |
| 2 | apps/miniprogram 21 文件普审+深挖 | `a9008d6` |
| 3 | HYP-01/08/09/12/17/20 回填 | `3710c2f` |

## Verification Evidence

- `awk -F'|' '$2 ~ /apps\/fc/ && $0 ~ /待审/' COVERAGE.md` → 0;miniprogram 同查 → 0;CODE 维度文件行合计 47、无一 `待审` ✓
- 六条 HYP 状态行均为 证实/细化,每条 `-A9` 窗口内含 `@ 5927f36` 证据 ✓;HYP-08 证据同时含 worker(config.py/cli.py)与 FC(env.py/audit.py)两侧 ✓
- `grep 'HYP-14' HANDOFF-PHASE4.md` → 3 处(两条移交 + 引用) ✓;HYPOTHESES.md 中 HYP-14 状态本计划未改动 ✓
- 零 diff 验证:`git diff --stat 5927f36 -- apps/ scripts/ docs/` → 空(全部三个任务收尾各跑一次) ✓
- 秘密反扫:`.planning/audit/` 内 `OSSAccessKeyId=`/`Signature=` 命中均为既有模式名引用(CHARTER 命令存档/假设描述),无任何值本体,本计划零新增 ✓

## Deviations from Plan

None - plan executed exactly as written. 两点执行内裁量(非偏差):① 深挖点登记表(COVERAGE §深挖点登记)的"下落"列未回填——03-03 同样未动该表,且并行 wave 的 03-05(TOOL)会写同一张表,留给 03-07 收口统一回填以避免写冲突;② eslint.md 无"确认"项(29 条全误报),验收项"确认项去向回填"空集成立,已在 findings/code.md 判定说明段显式记录。

## Known Stubs

None——本计划为纯审计文档写入,不涉产品源码。

## For 03-07 (收口计划)

- D14-1/2/4/5/6 证据行号已全部记入 COVERAGE 对应行备注,均未下裁定
- HYP-03 静态采证就位(sha256.js 纯 JS 实现形态、主线程调用链、约 2× 内存峰值),微基准 + 回填待 03-07
- 深挖点登记表 20 行"下落"列待收口回填(本计划与 03-03/03-05 的下落素材均在各 COVERAGE 行备注)
- errors.py 错误码真值源(`errors.py:13-24 @ 5927f36`)供 D14-3 裁定

## Self-Check: PASSED

- 03-04-SUMMARY.md 存在 ✓;四个提交 cca1ddc/a9008d6/3710c2f/b03a063 均在 git log ✓
- 无意外删除(`git diff --diff-filter=D` 相对 wave 基线为空)、无未跟踪残留文件 ✓
