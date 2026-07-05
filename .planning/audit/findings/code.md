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

> 03-04 判定产物(fc 12 文件 + miniprogram 21 文件普审 + 深挖):共 2 条发现——F-CODE-05(FC 侧,issue-credential 无频控/配额面,深挖 HYP-17 主证)、F-CODE-06(小程序侧,uploading 死态,队列状态机普审产出,uploader/queue_runtime/uploads/uploads_view/upload_queue 五文件共证)。FC 侧 sts.py/env.py/audit.py/auth.py/app.py 五个深挖点显式无发现(HYP-08/09/12 证据已记 COVERAGE 备注,回填见 HYPOTHESES.md);小程序侧 sha256.js 深挖为 HYP-03 静态采证(微基准与回填留 03-07),D14-1/2/4/5/6 证据只记不裁(D-15,记 COVERAGE 备注供 03-07)。DNF-02 对照命中(config.js 拼写域名)、DNF-03 对照命中(两 handler mypy 豁免)、DNF-04 对照命中(sts.py 原始 STS 下发)均按负面清单排除不立发现;errors.py 错误码真值源与 audio.js 契约观察只记/只移交不判断;HYP-14 两处顺带证据(config.js ENV、dev.js 门控)已移交 HANDOFF-PHASE4.md DOC 节,HYP-14 状态未动。app.py S104 销号确认项人工核实为 FC 容器必需形态,不立发现(去向已回填 scans/ruff-extended.md #1);eslint.md 销号表零"确认"项,无待回填去向。判定过程未撞见安全类顺带发现。

### F-CODE-05: `issue-credential` 在 allowlist 之外无任何频控/配额面,STS 签发与上游 jscode2session 调用均无上限

- **维度:** 组件代码 (CODE)
- **严重度:** LOW — 影响:两个成本/可用性面——①被攻陷的白名单客户端可无限刷 STS 签发与 ≤50 MB 对象上传(OSS 存储与 FC 调用成本滥用,单凭证爆炸半径仍受单 key/PutObject/900 s 约束);②匿名攻击者对公网触发器的每个 POST 都会在鉴权拒绝前消耗一次 jscode2session 上游调用(pre-auth 成本面,极端情况下刷占微信 appid 接口配额可波及合法用户登录);无数据丢失或认证绕过面,取最接近锚点 LOW(非关键路径债务);可能性:需攻击者主动针对个人应用端点或白名单客户端被攻陷,现实概率低
- **证据:** `apps/fc/issue_credential/handler.py:71-81 @ 5927f36`
  > `issuer = fc_shared.sts.get_issuer()` → `cred = issuer.assume_role(...)` — 鉴权通过后每请求一次 AssumeRole,函数内与 `fc_shared` 全链路无任何计数、窗口或配额判定;鉴权路径 `apps/fc/shared/fc_shared/auth.py:50 @ 5927f36`(`openid = wechat.code_to_openid(...)`)在 allowlist 判定之前执行,任意匿名 POST 均先触发一次微信上游调用。FC 触发器为匿名 HTTP(业务鉴权仅 allowlist 成员判定,`auth.py:33-36 @ 5927f36`)。
- **修复建议:** 运维层优先:在 FC 控制台为两函数设置实例并发/弹性上限并配置费用告警(零代码);如需应用层配额,因 FC 无状态,可用按 openid_hash 的轻量计数(如 OSS 计数对象或日志侧告警规则)实现每日签发上限,超限返回 429 类稳定错误码。
- **工作量:** S(平台配置层零代码即可闭环;应用层配额另计)
- **关联发现:** 无;关联线索: HYP-17、HYP-09
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-CODE-06: 进程中断残留的 `uploading` 状态项成为死态——自动驱动不拾取、无手动重传入口、不计入积压提示

- **维度:** 组件代码 (CODE)
- **严重度:** MEDIUM — 影响:上传中被杀进程/闪退的片段永久滞留 uploading 态——下次启动自动驱动只拾取 queued/pending_verify,视图层 uploading 不在任何可操作集合(无手动重传/重新 verify 按钮)也不计入"未上传 N 条"积压提示,UI 长期显示"上传中"蓝点;该片段音频未达 OSS、仅存本地临时文件(微信临时文件可能被系统回收),用户唯一出路是删除记录,录音随之丢失;可能性:需进程恰在 uploading 窗口内终止,而该窗口含最长 5+15+45 秒的三段退避等待与上传本身,录完即杀小程序/切走属现实操作(潜伏类:正常完成流程不触发,中断即爆)
- **证据:** `apps/miniprogram/utils/uploader.js:72 @ 5927f36`
  > `setStatus(STATUS_UPLOADING, { progress: 0 })` — 上传编排入口先把 uploading 即时落盘(onStatus→updateQueueItem→setStorageSync),随后经历 STS 请求与最多 4 次 OSS 尝试(退避 5s/15s/45s)。对照:自动驱动仅拾取两态 `apps/miniprogram/utils/queue_runtime.js:198,221 @ 5927f36`(`status !== STATUS_QUEUED` / `!== STATUS_PENDING_VERIFY` 即跳过;`pages/uploads/uploads.js:126,152 @ 5927f36` 同构);视图层 `apps/miniprogram/utils/uploads_view.js:25-39 @ 5927f36` 的 BACKLOG_STATUSES/MANUAL_RETRY_STATUSES/RE_VERIFY_STATUSES 三个集合均不含 uploading——该态无任何自动或用户可见恢复入口。
- **修复建议:** 启动/onShow 驱动前增加 stale-uploading 复位:把 `status === 'uploading'` 的项重置为 queued(或 manual_retry)再进入正常驱动——与 Worker 侧启动恢复扫描同一思路;或最小改动把 uploading 纳入 MANUAL_RETRY_STATUSES 提供手动出口。两方案任一均可单点闭环。
- **工作量:** M(同组件多文件:queue_runtime.js/uploads.js/uploads_view.js 及既有 node 测试)
- **关联发现:** 无;关联线索: 无(队列状态机普审产出)
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft
