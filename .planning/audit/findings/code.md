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

> 03-03 判定产物(worker 核心 14 模块普审 + 深挖):共 4 条发现——F-CODE-01/02(深挖 4 模块,poller 主证)、F-CODE-03(recovery 原子写孤儿 tmp)、F-CODE-04(paths .env 无界向上搜索);其中 F-CODE-02 在 10 模块普审中经 audio.py 转码失败路径增补证据并升级为 MEDIUM。pipeline/nls/cli 深挖点显式无发现(HYP-10/16/19 与 D14-1/D14-2 证据已记 COVERAGE 备注,回填见 HYPOTHESES.md)。DNF-01 对照命中(transcriber.py whisper 桩)按负面清单排除不立发现;oss_admin.py 契约观察移交 Phase 2 矩阵既有覆盖(F-CON-01/02/03 引用行),本维度不判断。判定过程未撞见安全类顺带发现。

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

### F-CODE-02: 持久性失败对象(sha256 失配/转码失败)每轮重下重处理,无失败计数、隔离或告警升级面

- **维度:** 组件代码 (CODE)
- **严重度:** MEDIUM — 影响:持久性失败对象使 Worker 每轮重新下载全量字节并重复失败,该片段永不完成转写且用户无升级告警(仅守护进程滚动日志每轮数行),长期空耗带宽与轮询时间;转码失败路径的 inbox/failed/ 留档给出"已隔离"的表象但并不阻止下一轮重下重试;可能性:sha256 持久失配需绕过 OSS 传输层完整性保障——极低;转码/探测失败仅需一次损坏或不支持格式的录音上传——低但现实,当前正常参数下不触发、异常上传即爆(潜伏类)
- **证据:** `apps/worker/src/soniscope_worker/poller.py:272-284 @ 5927f36`
  > `if draft.original_sha256 and actual_sha != draft.original_sha256:` → `part.unlink(missing_ok=True)  # 删本地 .part(非 OSS),下一轮重下` — 返回 `sha256_mismatch` 后无任何按 fragment 的重试上限或失败历史;消费端 `pipeline.py:412-422 @ 5927f36` 对该结果仅记日志并 continue,下一轮 `plan_downloads` 因无 `.done` 再次纳入下载,循环无界。
  >
  > 转码失败同构:`apps/worker/src/soniscope_worker/audio.py:134-142,221-235 @ 5927f36` — `_archive_failed` docstring 称"留档(不再重试)",但留档仅移走本地 `.part`;OSS 对象无 `.done` → 下一轮 `plan_downloads` 再次纳入 → 重下 → 再次探测/转码失败 → 再次留档(os.replace 同名覆盖),循环同样无界,且与 docstring "不再重试"语义相悖。
- **修复建议:** Worker 侧为 `sha256_mismatch`/`error`/`standardize failed` 结果增加按 fragment_id 的失败计数(落盘诊断文件或进程内计数),超阈值后进入跳过名单(如 inbox/failed/ 旁的 skiplist 文件)并输出显式告警日志;同步修正 `_archive_failed` docstring 的"不再重试"表述——与 F-CON-04 修复建议中的"保守告警方案"同一动作面,可合并实施。
- **工作量:** M(poller.py + pipeline.py + audio.py 同组件多文件 + 测试)
- **关联发现:** F-CON-04;关联线索: HYP-16
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-CODE-03: 原子写崩溃窗口残留的 `*.tmp` 孤儿文件无任何清理路径(fragment 目录内)

- **维度:** 组件代码 (CODE)
- **严重度:** LOW — 影响:`atomic_write_text` 的 mkstemp 临时文件写在目标同目录(fragment 目录),若进程在写入与 `os.replace` 之间被 kill -9,孤儿 `manifest.json.XXXX.tmp`/`transcript.txt.XXXX.tmp` 永久残留——启动恢复三段扫描只清 inbox/ 与 tmp/,`verify-no-stale` 运维检查同样只查 inbox/tmp,该类残留无任何清理或检出路径;文件极小,仅目录污染,不影响正确性(mkstemp 名唯一,不会被误认为产物);可能性:崩溃须恰好落在毫秒级写入窗口内,且需人工翻看 fragment 目录才会发现
- **证据:** `apps/worker/src/soniscope_worker/recovery.py:47-60 @ 5927f36`
  > `fd, tmp_name = tempfile.mkstemp(prefix=f"{dest.name}.", suffix=".tmp", dir=str(dest.parent))` — 异常路径 `except BaseException: tmp.unlink(...)` 覆盖 Python 异常但覆盖不了 kill -9/断电;恢复扫描三段(`recovery.py:196-209,236-250 @ 5927f36`)仅清理 inbox 的 `.part`/`.wav.tmp` 与 tmp 的 `.transcript.json.tmp`,fragment 目录内 `<name>.XXXX.tmp` 无人认领;`ops` 的 verify-no-stale 检查范围同为 inbox/tmp(`cli.py:488 @ 5927f36` docstring)。
- **修复建议:** 在恢复扫描第三段 `classify_fragment_dir`/`scan_fragments` 中顺带删除 fragment 目录内匹配 `*.tmp` 的孤儿文件(mkstemp 命名模式 `<产物名>.*.tmp`),或将 `verify-no-stale` 检查范围扩展到 fragments/ 并输出告警——单文件改动即可闭环。
- **工作量:** S(recovery.py 单文件 + 测试)
- **关联发现:** 无;关联线索: 无
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-CODE-04: `SONISCOPE_HOME` 的 `.env` 解析为不设边界的 CWD 向上搜索,与"仓库根目录 .env"的文档口径不符

- **维度:** 组件代码 (CODE)
- **严重度:** LOW — 影响:从仓库外目录运行 Worker 时,祖先目录中任意无关 `.env`(如 `$HOME/.env`)会静默劫持 `SONISCOPE_HOME` 解析,把运行时数据写到意外位置;错误提示与代码注释均声称"仓库根目录 .env",误导排障方向;可能性:Makefile 约定从仓库根运行,正常路径先命中仓库 `.env`——仅在脱离 Makefile、从任意 CWD 直跑 `soniscope-worker` 且祖先目录存在含 SONISCOPE_HOME 的 `.env` 时触发(潜伏类)
- **证据:** `apps/worker/src/soniscope_worker/paths.py:38-46 @ 5927f36`
  > `for directory in (current, *current.parents): candidate = directory / ".env"` — 从 `Path.cwd()` 向上直至文件系统根,无仓库边界判定;而同文件错误信息(`paths.py:61-64 @ 5927f36`)写"或在仓库根目录 .env 中写入",`config.py:6 @ 5927f36` 注释同为"② 仓库根目录 .env"。
- **修复建议:** 把 `_find_dotenv` 的向上搜索加终止条件(遇到 `.git`/`pyproject.toml` 等仓库标记即止),或改为仅检查仓库根一处 `.env` 并同步文档口径;二选一后错误信息与 config.py 注释保持一致。
- **工作量:** S(paths.py 单文件 + 测试)
- **关联发现:** 无;关联线索: 无
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft
