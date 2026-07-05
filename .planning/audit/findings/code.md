# 发现台账: 组件代码 (CODE)

**Created:** 2026-07-04

本文件由 Phase 3 写入,ID 前缀 `F-CODE-NN`;schema 以 `.planning/audit/CHARTER.md` 为准。

### F-CODE-00: (schema 示例,非真实发现)

> 本条为 schema 示例,Phase 5 汇总时剔除。

- **维度:** 组件代码 (CODE)
- **严重度:** (五级之一) — 影响:(一句场景语言);可能性:(一句触发条件)
- **证据:** `path:line @ 5927f36`(占位;从 `git show 5927f36:<path>` 提取)
  > (引用片段占位)
- **修复建议:** (一段占位)
- **工作量:** (S/M/L/XL 之一)
- **关联发现:** (F-XXX-NN 或 HYP-NN,无则写"无")
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

## 发现

> 03-03 判定产物(worker 核心 14 模块普审 + 深挖):4 大模块深挖(pipeline/nls/cli/poller)产出 F-CODE-01/02 两条(均 poller 侧);pipeline/nls/cli 深挖点显式无发现(HYP-10/16/19 与 D14-1/D14-2 证据已记 COVERAGE 备注,回填见 HYPOTHESES.md)。DNF-01 对照命中(transcriber.py whisper 桩)按负面清单排除不立发现。判定过程未撞见安全类顺带发现。

### F-CODE-01: `process_plan` 声明 `fragments_root` 形参但函数体未使用,遗留 API 面误导调用方

- **维度:** 组件代码 (CODE)
- **严重度:** LOW — 影响:误导性 API 面——签名暗示 process_plan 参与 fragments/.done 判定,实际 `.done` 跳过完全由调用方 done_check 闭包承担,未来新增调用点可能误信该函数自带幂等判定;可能性:仅在新增调用点或重构时触发误用,现有两个调用方(poller.py:342-344、pipeline.py:411)行为正确
- **证据:** `apps/worker/src/soniscope_worker/poller.py:248-250 @ 5927f36`
  > `def process_plan(plan: PollPlan, source: OssSource, *, inbox_root: Path, fragments_root: Path) -> ObjectOutcome:` — 函数体(:257-292)无任何 `fragments_root` 引用;`.done` 判定由调用方以 done_check 闭包另行携带(`poller.py:333 @ 5927f36`、`pipeline.py:399 @ 5927f36`)。ruff ARG001 命中与人工核实互证(scans/ruff-extended.md 销号表 #55 确认项)。
- **修复建议:** 移除 `fragments_root` 形参并同步两个调用点(poller.py:342-344、pipeline.py:411);若保留则在 docstring 明示"幂等判定由调用方 done_check 承担,本函数不读 fragments_root"。以移除为佳,消除误导面。
- **工作量:** S(poller.py 单文件 + 两调用点同步 + 既有测试)
- **关联发现:** 无;关联线索: scans/ruff-extended.md #55(ARG001 确认项反填)
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-CODE-02: 持久性 sha256 失配对象每轮全量重下,无失败计数、隔离或告警升级面

- **维度:** 组件代码 (CODE)
- **严重度:** LOW — 影响:单个持久损坏对象(内容与 `x-oss-meta-sha256` 恒不符)使 Worker 每轮删 `.part` 重下、该片段永不完成转写,仅守护进程滚动日志每轮一行可见,无失败计数/隔离/告警升级,长期空耗带宽与轮询时间;可能性:需绕过 OSS 传输层完整性保障(HTTPS + 服务端 CRC)产生持久内容失配,现实概率极低(与 F-CON-04 同一概率判断)
- **证据:** `apps/worker/src/soniscope_worker/poller.py:272-284 @ 5927f36`
  > `if draft.original_sha256 and actual_sha != draft.original_sha256:` → `part.unlink(missing_ok=True)  # 删本地 .part(非 OSS),下一轮重下` — 返回 `sha256_mismatch` 后无任何按 fragment 的重试上限或失败历史;消费端 `pipeline.py:412-422 @ 5927f36` 对该结果仅记日志并 continue,下一轮 `plan_downloads` 因无 `.done` 再次纳入下载,循环无界。
- **修复建议:** Worker 侧为 `sha256_mismatch`/`error` 结果增加按 fragment_id 的失败计数(落盘诊断文件或进程内计数),超阈值后隔离(记入 inbox/failed/ 名单或跳过名单)并输出显式告警日志——与 F-CON-04 修复建议中的"保守告警方案"同一动作面,可合并实施。
- **工作量:** M(poller.py + pipeline.py 同组件两文件 + 测试)
- **关联发现:** F-CON-04;关联线索: HYP-16
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft
