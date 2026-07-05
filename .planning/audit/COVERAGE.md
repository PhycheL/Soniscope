# 覆盖台账

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本文档是 Phase 3(组件与工具链深潜)的覆盖台账——证据与判断分离,只登记"哪个对象、审到什么深度、过了哪些面、产出了什么",不承载发现正文(发现入 `findings/code.md` / `findings/toolchain.md`)。依据 D-01(覆盖策略 = 全模块普审 + 线索深挖:每个源码模块至少完整读一遍,20 处深挖点逐行深挖)、D-02(独立覆盖台账,仿 Phase 2 CONTRACT-MATRIX 先例,直接喂 RPT-07/RPT-08)、D-04(普审关注面清单化,每模块逐面过并标"已过面 N/9")。取证方法:证据一律提取自 `git show 5927f36:<path>` / `git grep -n <pat> 5927f36`,禁读工作树取证。

> **基线导出备注(D-08,供 03-01 Task 3 与后续计划复用):** 仪器扫描对象为基线导出副本,导出命令 `git archive 5927f36 apps scripts | tar -x -C <EXPORT>`,导出路径(会话 scratchpad,仓库外):`/private/tmp/claude-501/-Volumes-Data-ProjectCode-my-soniscope/1affd208-a109-4cfb-808a-b80c6e881ccb/scratchpad/baseline-5927f36`。若会话更替导致该路径失效,按上述命令重导出即可(内容由基线 SHA 唯一决定)。

## 普审关注面清单(D-04 定稿,9 面)

以下 9 面为全阶段"已过面 N/9"的分母定义,逐字采用 03-RESEARCH.md §Architecture Patterns 定稿表;每面锚定 CHARTER 严重度锚点:

| # | 关注面 | CHARTER 锚点 | 仪器辅助信号 |
|---|--------|--------------|--------------|
| 1 | 静默失败路径(异常吞并、except-pass、错误被忽略) | HIGH 静默转写失败 | ruff S110/BLE/TRY(探针已见 S110 ×1) |
| 2 | 数据丢失风险(`.done` 时序、原子 rename、临时文件清理) | CRITICAL 数据丢失 | 人工为主(CLAUDE.md 反模式清单) |
| 3 | 秘密处理违规(明文入日志、绕过 MaskedSecret/audit 洗涤) | CRITICAL 凭证泄漏 | 秘密扫描 + ruff S105/S106(探针 13 命中待核) |
| 4 | 硬编码云值与环境假设(region/URL/size/阈值散落) | MEDIUM 潜伏失配 | grep;D14-5 关联 |
| 5 | 时区/日期正确性(naive datetime、本地时区推导) | MEDIUM(F-CON-02 同族) | ruff DTZ(探针 DTZ011 ×2、DTZ005 ×1) |
| 6 | 死代码与不可达分支 | LOW | vulture + ruff ARG(探针 ARG ×37) |
| 7 | 注释/文档字符串与实态不符 | LOW(契约类→移交) | 人工 |
| 8 | 纯逻辑+IO注入模式违反(纯逻辑内直调 SDK/wx) | MEDIUM/LOW(CLAUDE.md 明示反模式) | 人工 |
| 9 | 重试/退避/上限等跨端约定的本端一致性 | MEDIUM | D14-2/D14-3 关联 |

## CODE 维度

47 个对象(worker 核心 14 + fc 12 + miniprogram 21),行数为 `git show 5927f36:<path> | wc -l` 实测值(源自 03-RESEARCH.md 审计对象全量清单);深度/已过面/产出三列由 03-03/03-04 回填:

| 路径 | 行数 | 维度 | 深度 | 已过面 | 产出 | 备注 |
|------|------|------|------|--------|------|------|
| `apps/worker/src/soniscope_worker/pipeline.py` | 875 | CODE | 深挖 | 9/9 | 无发现 | 深挖 HYP-10 证实:串行 for 循环 `pipeline.py:407-441 @ 5927f36` + 单线程主循环 `:485-506`(回填见 HYPOTHESES.md)。`.done` 最后写(`:274`/`:367`)、任一阶段失败不建 `.done`、原子写协议核查通过;F-CODE-02 消费端证据 `:412-422` |
| `apps/worker/src/soniscope_worker/nls.py` | 740 | CODE | 深挖 | 9/9 | 无发现 | 深挖 HYP-19 证据:filetrans 域名+版本经 `verify_prep.NLS_FILETRANS_VERSION = "2018-08-17"`(`verify_prep.py:87 @ 5927f36`,消费 `nls.py:454-455 @ 5927f36`),legacy `aliyunsdkcore` AcsClient(`verify_prep.py:775-776`)。D14-2 证据(D-15 只记不裁):`RETRY_DELAYS_SECONDS = (5.0, 15.0, 45.0)` 与 `MAX_RETRIES = 3` 均为独立字面量(`nls.py:45-46 @ 5927f36`),MAX 非 `len()` 派生;`_with_retries`(`:268-270`)当前 3 == len 自洽。RESIGN_THRESHOLD 续签逻辑(`:314-326`)无静默失败;秘密仅经 `.get_secret_value()` 入 SDK 参数,错误信息只含类名/错误码(`:428`/`:579`) |
| `apps/worker/src/soniscope_worker/cli.py` | 601 | CODE | 普审 | 9/9 | 无发现 | TOOL 子命令入口,实体逻辑见 TOOL 侧对应模块,整体归 CODE 审一次(RESEARCH Open Question 2 裁决)。全部子命令统一 `(lines, exit_code)` → `typer.Exit` 转换完整;`oss-delete-obj` 双闸门(--yes/SONISCOPE_ALLOW_OSS_DELETE)测试专用;face7 轻微:模块 docstring(`cli.py:1-5 @ 5927f36`)"主轮询与 retranscribe 等在后续 story 实现"滞后于实态(两者已实现 `:24-29`/`:401-423`),不立发现 |
| `apps/worker/src/soniscope_worker/poller.py` | 531 | CODE | 深挖 | 9/9 | F-CODE-01、F-CODE-02 | 深挖 HYP-10/16 证实:`poll_loop` 单线程 while 循环 `poller.py:378-391 @ 5927f36`,单机单配置 RealOssSource(`:395-451`)。D14-1 证据(只记不裁):Worker 侧 sha256 比对流程 `poller.py:261,272-284 @ 5927f36`,经 `fixtures.sha256_of`(stdlib hashlib)。契约观察移交:`fragment_id_from_key` 往返校验(`:47-61`)已由 Phase 2 矩阵覆盖(F-CON-02/03 引用行),本维度不判断。OssSource Protocol 结构性无删除能力(`:215-231`)红线核查通过 |
| `apps/worker/src/soniscope_worker/manifest.py` | 473 | CODE | 普审 | 9/9 | 无发现 | 落盘顺序核查通过:`write_fragment_outputs` 原子写 manifest→transcript.json(经 tmp/)→transcript.txt→`.done` 最后(`manifest.py:226-232 @ 5927f36`);face7 轻微:`UploadInfo` 注释(`:91`)称 original_sha256/original_size_bytes"可显式覆盖"但 dataclass 无该字段,不立发现 |
| `apps/worker/src/soniscope_worker/recovery.py` | 465 | CODE | 普审 | 9/9 | F-CODE-03 | 三段恢复扫描按后缀清理仅中间态(`.part`/`.wav.tmp`/`.transcript.json.tmp`),误删面核查通过;`.done` 无任何删除路径(simulate 工具除外,显式测试用);缺口:fragment 目录内 mkstemp 孤儿 `*.tmp` 无清理路径 → F-CODE-03;`remove_empty_dirs` 默认 False 安全 |
| `apps/worker/src/soniscope_worker/audio.py` | 412 | CODE | 普审 | 9/9 | F-CODE-02(增补证据) | 直通/转码均原子 rename(`audio.py:203,238 @ 5927f36`),失败留档 inbox/failed/ 不污染 fragments/(`:185,225`);但留档不阻止下轮重下(`_archive_failed` docstring "不再重试"与实态相悖)→ 并入 F-CODE-02 并升级 MEDIUM;ffmpeg 子进程 S603/S607 已在 scans 销号(误报,固定参数列表) |
| `apps/worker/src/soniscope_worker/oss_admin.py` | 242 | CODE | 普审 | 9/9 | 无发现 | 契约观察移交:`object_key_for`(`oss_admin.py:37-50 @ 5927f36`)三处重复实现与往返校验已由 Phase 2 矩阵组①行 2/4/5 覆盖(F-CON-01/02/03 引用 `:45-49/:50`),本维度不判断(成功判据 4/D-11)。DeleteObject 仅测试用且双闸门(`delete_allowed :53-55` + cli --yes/env),业务路径 OssSource 结构性无删除——红线核查通过;输出无 AK 明文(`:209/:240` 仅异常类名) |
| `apps/worker/src/soniscope_worker/transcriber.py` | 183 | CODE | 深挖 | 9/9 | 无发现 | 深挖 HYP-19(Protocol 隔离):`Transcriber` Protocol(`transcriber.py:81-90 @ 5927f36`)+ 工厂分发(`:168-183`),业务流程仅依赖 Protocol,引擎替换只需新实现类 + 工厂分支 + config.yaml 改名——隔离充分(证据供 HYP-19 回填)。DNF-01 对照命中:`WhisperLocalTranscriber.transcribe`(`:156-165`)抛 NotImplementedError 附可操作提示,系故意桩,负面清单排除不立发现 |
| `apps/worker/src/soniscope_worker/config.py` | 150 | CODE | 深挖 | 9/9 | 无发现 | 深挖 HYP-08 证据(本计划只采证不回填,回填在 03-04):`MaskedSecret._display`(`config.py:31-35 @ 5927f36`)repr/str 前后 4 位脱敏;`masked_summary`(`:85-106`)经 MaskedSecret __str__ 输出,无明文;`config_permission_is_600`(`:148-150`)恰 600 判定,但 CLI 侧仅警告不拒载(`cli.py:48-53 @ 5927f36`);边界细节:`mask_secret`(`:22-28`)对 9-16 字符短秘密暴露 8 字符占比过半(现实 Aliyun AK secret 30 字符/appkey 较长,边界性),供 03-04 合并 FC env.py 侧证据裁定;`yaml.safe_load`(`:137`)非 unsafe load ✓ |
| `apps/worker/src/soniscope_worker/paths.py` | 117 | CODE | 普审 | 9/9 | F-CODE-04 | `.env` 向上搜索(`paths.py:38-46 @ 5927f36`)自 CWD 无界直至根目录,与错误信息/config.py 注释"仓库根目录 .env"口径不符 → F-CODE-04;`init_runtime_dirs` 幂等、home 不存在显式拒绝(`:103-112`) |
| `apps/worker/src/soniscope_worker/locks.py` | 64 | CODE | 普审 | 9/9 | 无发现 | flock advisory 排他锁按 fragment 粒度,跨进程互斥(主轮询 vs retranscribe)语义与 §3.7 一致;锁文件 0 字节不参与恢复扫描(docstring 明示 by-design);获取失败路径(LOCK_NB → LockBusyError)与 fd 关闭(finally)完整 |
| `apps/worker/src/soniscope_worker/__main__.py` | 11 | CODE | 普审 | 9/9 | 无发现 | 纯入口委托 cli.app,无逻辑面 |
| `apps/worker/src/soniscope_worker/__init__.py` | 7 | CODE | 普审 | 9/9 | 无发现 | 仅 `__version__ = "0.1.0"`;docstring "US-001 仅建立骨架"措辞滞后(face7 轻微),不立发现 |
| `apps/fc/shared/fc_shared/sts.py` | 176 | CODE | 深挖 | 9/9 | 无发现 | 深挖 HYP-09/17:`single_key_policy`(`sts.py:62-73 @ 5927f36`)Resource 精确单 object key 无路径通配、仅 `oss:PutObject`,时效由 handler 固定传 `STS_MAX_DURATION_SECONDS = 900`(`sts.py:25 @ 5927f36`)——收窄程度与 docstring 红线(`:9-10`)一致;AssumeRole 失败不在本模块捕获,由 handler 统一收敛 500(见 handler 行)。DNF-04 对照:`credential_response`(`:102-114`)向小程序下发原始 STS 秘密系 by-design,负面清单排除不立发现;策略实现本身未见缺陷 |
| `apps/fc/shared/fc_shared/env.py` | 150 | CODE | 深挖 | 9/9 | 无发现 | 深挖 HYP-08 采证(回填见 HYPOTHESES.md):三组必填变量仅存名字常量(`env.py:16-38 @ 5927f36`),缺失时 FcConfigError 只列变量名不含值(`:89-91,117-119,140-142`);秘密以普通 `str` 存 frozen dataclass(StsEnv/VerifyEnv/FcEnv,`:44-79`),无 Worker 侧 MaskedSecret 同等类型级掩码,防线在 log_event 字段名洗涤 + 调用纪律(docstring `:46,60-61,74-75` 明示"绝不进日志")——细化点入 HYP-08 回填,不立发现。`_parse_max_upload_bytes` 非法值静默回退默认 50MB(`:98-107`,face1 轻微:回退方向安全,无告警日志,不立发现) |
| `apps/fc/shared/fc_shared/head.py` | 141 | CODE | 普审 | 9/9 | 无发现 | 错误分支完整性核查通过:404/NoSuchKey → `ObjectHead(exists=False)`(`head.py:127-130 @ 5927f36`),其余异常上抛由 handler 收敛 500;三态映射(`:42-55`)与 docstring 一致(仅校验存在性 + Content-Length,etag 只回传不比对,docstring `:9-10` 明示 HeadObject 无法校验 sha256);`_oss_error_code` 递归 unwrap 有终止条件(`:85-93`);读凭证仅入 SDK 参数不入日志/响应 |
| `apps/fc/issue_credential/handler.py` | 110 | CODE | 深挖 | 9/9 | F-CODE-05 | 深挖 HYP-17:allowlist 之外无任何频控/配额——每个鉴权通过的 POST 触发一次 AssumeRole 无上限(`handler.py:71-81 @ 5927f36`),且每个匿名 POST 在鉴权前即触发一次 jscode2session 上游调用(pre-auth 成本面,`fc_shared/auth.py:50 @ 5927f36`)→ F-CODE-05。DNF-03 对照:mypy strict 豁免系显式工程取舍(pyproject 注释),负面清单排除不立发现(handler ruff-only)。秘密面:STS 签发失败统一 500,日志仅 reason=异常类名(`:82-93`)✓ |
| `apps/fc/verify_upload/handler.py` | 106 | CODE | 普审 | 9/9 | 无发现 | DNF-03 对照:mypy 豁免同 issue_credential,负面清单排除不立发现。校验失败错误码路径完整:FcConfigError→500 SERVER_MISCONFIGURED(仅变量名)、FcHttpError→对应 4xx 稳定码、HeadObject 异常→500 HEAD_OBJECT_FAILED(仅异常类名)、业务三态走 200 响应体 reason(`handler.py:53-106 @ 5927f36`);无限流面与 issue-credential 同构,由 F-CODE-05 一并覆盖不重复立 |
| `apps/fc/shared/fc_shared/__init__.py` | 106 | CODE | 普审 | 9/9 | 无发现 | re-export 门面无逻辑面;`__all__`(`__init__.py:56-106 @ 5927f36`)与实际导入一致,vendoring 部署形态在 docstring 明示 |
| `apps/fc/shared/fc_shared/http.py` | 79 | CODE | 普审 | 9/9 | 无发现 | 错误路径统一 400 INVALID_REQUEST(空体/非法 JSON/非对象/缺字段,`http.py:54-79 @ 5927f36`),无静默分支;CONTENT_LENGTH 解析异常回退 0 → 按空体 400(`:56-59`);请求体无应用层大小上限,依托 FC 平台请求边界(face4 轻微,不立发现) |
| `apps/fc/shared/fc_shared/audit.py` | 62 | CODE | 深挖 | 9/9 | 无发现 | 深挖 HYP-08(is_sensitive 洗涤覆盖面):精确名单 13 项(`audit.py:14-29 @ 5927f36`)+ 子串兜底 secret/token/appkey/api_key/session_key/password(`:31`),覆盖全部长期凭证与会话字段;边界:`ak_id`/`openid` 等非命中名不脱敏——现有调用点均只传 openid_hash(auth.py 组装)与安全标量,纪律依赖面作为细化点入 HYP-08 回填,不立发现;`hash_openid` sha256 前 16 位(`:35-37`)✓ |
| `apps/fc/shared/fc_shared/wechat.py` | 52 | CODE | 普审 | 9/9 | 无发现 | 任意失败(网络/非 dict/无 openid)统一 401 INVALID_CODE,异常链不外传 code/secret(`wechat.py:41-51 @ 5927f36`);secret 经查询串传 jscode2session 系微信开放接口固有形态,URL 不入任何日志;`timeout=10` 显式(`:25`) |
| `apps/fc/shared/fc_shared/auth.py` | 52 | CODE | 深挖 | 9/9 | 无发现 | 深挖 HYP-09 采证(回填见 HYPOTHESES.md):鉴权 = JSON 校验 → code 换 openid → allowlist 字符串成员判定(`auth.py:33-52 @ 5927f36`),无会话/无频控/无按用户隔离,与假设一致;AuthContext 提供 openid_hash 供日志(`:24-30`),openid 明文不出鉴权层 |
| `apps/fc/shared/fc_shared/errors.py` | 51 | CODE | 普审 | 9/9 | 无发现 | D14-3 关联证据(D-15 只记不裁,供 03-07 裁定):稳定错误码字面量真值源 `errors.py:13-24 @ 5927f36`(7 个 HTTP 错误码 + 2 个 verify reason),小程序 JS 按同字符串分支、联调工具镜像同集群;FcHttpError payload 仅含稳定码 + 安全文案(`:34-43`),FcConfigError 只列变量名(`:46-51`) |
| `apps/fc/shared/app.py` | 35 | CODE | 深挖 | 9/9 | 无发现 | 深挖 HYP-12:wsgiref `ThreadingWSGIServer`(daemon threads)为生产运行时(`app.py:17-31 @ 5927f36`),无请求上限/超时/HTTP 加固,健壮性依托 FC 网关边界——MVP 自评经 D-10 裁定成立,回填见 HYPOTHESES.md(RPT-06/DNF 候选)。S104 bind-all 销号确认项人工核实下落:容器内 `0.0.0.0` 监听(`:27`)为 FC 自定义运行时必需形态(平台网关为唯一公网入口,容器无直连面),不立发现,去向已回填 scans/ruff-extended.md #1 |
| `apps/miniprogram/pages/index/index.js` | 796 | CODE | 深挖 | 9/9 | 无发现 | 深挖 D14-1 证据(D-15 只记不裁):sha256 调用端 `index.js:30 @ 5927f36`(require)与 `:640`(`sha256Hex(buf)`);主线程同步全量读文件 + 哈希于保存路径(`:630-645` 单条、`:582` 长录音逐片),数据量级 = 原始音频全字节(单片 mp3 ≤600s 常态、上限 50MB)。中断保护去重(`_interruptHandled` `:156-165`)、中断草稿即时落盘(`:325`)核查通过;`_computeOriginalSha256` 失败返回空串不阻断入队且有错误日志(`:629-645`,face1 受控降级,Worker 侧空 sha256 跳过比对);storage 读取 catch 回退安全;page=IO 层职责 by-design |
| `apps/miniprogram/pages/uploads/uploads.js` | 387 | CODE | 深挖 | 9/9 | F-CODE-06(共证) | 深挖 D14-4 证据(只记不裁):FC 请求组装第二份 `uploads.js:330-345,347-370 @ 5927f36`(wx.request data 行 `:340`/`:365`),与 queue_runtime.js:94-128 同构。队列状态机漏态:自动驱动仅拾取 queued(`:126`)与 pending_verify(`:152`),`uploading` 残留无恢复路径 → F-CODE-06 共证。`_readQueue` catch 回退 [];自动清理仅删本地文件、保留队列记录与 OSS 对象(`:289-303`)红线核查通过 |
| `apps/miniprogram/utils/queue_runtime.js` | 324 | CODE | 深挖 | 9/9 | F-CODE-06(共证) | 深挖 D14-4 证据(只记不裁):`queue_runtime.js:94-128 @ 5927f36` wxRequestSts/wxRequestVerify 与 uploads.js 同构两份,docstring(`:5-6`)自述"与 uploads 页保持一致、参照实现不改"——重复系已声明状态。`drive()` 仅拾取 queued/pending_verify(`:198,221`)→ F-CODE-06 主证。`:232` 残留脚手架注释 `PLACEHOLDER_PUBLIC`(face6 轻微,不立发现);isOnline 缺 getNetworkType 保守视为离线(`:62-81`) |
| `apps/miniprogram/utils/uploads_view.js` | 304 | CODE | 普审 | 9/9 | F-CODE-06(共证) | `uploading` 不在 BACKLOG_STATUSES/MANUAL_RETRY_STATUSES/RE_VERIFY_STATUSES 任何可操作集合(`uploads_view.js:25-39 @ 5927f36`)——F-CODE-06 视图面证据(无手动出口、不计积压);纯函数视图模型,relativeDay 本地时区仅展示用途(face5 自洽) |
| `apps/miniprogram/utils/audio.js` | 185 | CODE | 普审 | 9/9 | 无发现 | 契约观察移交(成功判据 4/D-11):fragment_id/object_key 派生与 `FRAGMENT_ID_RE`(`audio.js:95-106 @ 5927f36`)、本地时区日期段(`localDateParts` `:52-61`)已由 Phase 2 矩阵组① 覆盖(F-CON-01/02 引用行,HYP-13 归 CON 维度),本维度不判断不重复立。chunk_total null→OSS meta "0" 映射(`:157-170`)与 chunking.js 语义一致(face9) |
| `apps/miniprogram/utils/sha256.js` | 171 | CODE | 深挖 | 9/9 | 无发现(静态采证) | 深挖 HYP-03 静态论证采证(D-16 微基准与 HYP-03 回填留 03-07):纯 JS SHA-256(K 表 `sha256.js:9-18 @ 5927f36`、`hashWords` `:66-135`)同步执行,padding 阶段整段复制输入(`:76-77`,峰值内存约 2× 音频字节);调用链 = index.js readFileSync→sha256Hex 主线程;与 AGENTS wasm-crypto 处方的差异系 docstring(`:4-5`)自述取舍(本期纯 JS,wasm 属后续优化)。D14-1 双实现证据:本文件 vs Worker stdlib hashlib(fixtures.py :21,118) |
| `apps/miniprogram/utils/uploader.js` | 164 | CODE | 深挖 | 9/9 | F-CODE-06(共证) | 深挖 D14-2 证据(D-15 只记不裁):`RETRY_DELAYS_MS = [5000, 15000, 45000]`(`uploader.js:28 @ 5927f36`)、`MAX_UPLOAD_RETRIES = RETRY_DELAYS_MS.length`(`:29`,JS 侧 length 派生,对照 Worker MAX_RETRIES 独立字面量)。STATUS_UPLOADING 先落盘(`:72`)后进入可含 65s 退避的上传窗口,进程中断即残留 → F-CODE-06 时序主证。凭证仅入表单构造,日志只记 object_key/状态/错误码(`:110-113`)face3 核查通过 |
| `apps/miniprogram/utils/verify.js` | 138 | CODE | 深挖 | 9/9 | 无发现 | 深挖 D14-2 证据(只记不裁):`VERIFY_RETRY_DELAYS_MS = [5000, 15000, 45000]`(`verify.js:16 @ 5927f36`)、MAX 派生 `.length`(`:17`)。四分类 verified/unverified/retryable/fatal(`:28-51`)错误路径完整;每次重试重新登录(code 一次性,`:67-82`);4xx 不重试、5xx/网络退避与 AGENTS 约定一致(face9) |
| `apps/miniprogram/utils/fault_injection.js` | 124 | CODE | 普审 | 9/9 | 无发现 | HYP-14 顺带证据→移交 Phase 4 DOC(HANDOFF-PHASE4.md,状态不动):production 门控双兜底——`isDevEnv`(`fault_injection.js:38-40 @ 5927f36`)+ loadFaults/saveFaults 生产读全关写忽略(`:82-107`);门控实效完全取决于 config.js ENV 常量发布现值 |
| `apps/miniprogram/utils/oss_sign.js` | 121 | CODE | 普审 | 9/9 | 无发现 | 秘密处理面核查通过:access_key_secret 仅入 HMAC 派生链(`oss_sign.js:93 @ 5927f36`),security_token 入表单字段系 OSS PostObject 协议必需(`:81,102`),模块零日志(docstring `:8` 红线);policy 条件精确 `eq $key`(`:77`)与 FC 单 key STS 对齐(face9);region 缺省回退 'cn-beijing'(`:59`,face4 轻微,调用方恒传 config 值,不立发现) |
| `apps/miniprogram/utils/upload_queue.js` | 119 | CODE | 深挖 | 9/9 | F-CODE-06(共证) | 深挖 D14-6 证据(D-15 只记不裁,关联 F-CON-03):`fragmentIdFromObjectKey`(`upload_queue.js:38-44 @ 5927f36`)无校验字符串切割(去目录去扩展名),key↔id 第四处实现;US-015 后仅作 manifest 缺失时回退(`:53-54`)。八状态常量真值源(`:9-16`),`uploading` 定义于此而无恢复语义 → F-CODE-06 状态集证据;appendQueuedFragment 按 fragmentId 去重(`:75-84`) |
| `apps/miniprogram/utils/ulid.js` | 92 | CODE | 普审 | 9/9 | 无发现 | Crockford base32 26 字符,monotonicFactory 同毫秒递增随机段保证唯一(`ulid.js:76-85 @ 5927f36`);Math.random 非密码学随机仅作 ID 用途,无秘密语义(face3) |
| `apps/miniprogram/utils/chunking.js` | 65 | CODE | 普审 | 9/9 | 无发现 | 阈值消费 config 单一常量(`chunking.js:12 @ 5927f36`);chunk_total 单片 null/多片 N(`:40-55`)与 audio.js buildOssMetadata(null→"0")跨模块语义一致(face9) |
| `apps/miniprogram/utils/hmac.js` | 64 | CODE | 普审 | 9/9 | 无发现 | 标准 HMAC 构造(BLOCK_SIZE 64、超长 key 先哈希、ipad/opad,`hmac.js:13-36 @ 5927f36`);base64 纯实现(小程序无 btoa,`:45-58`);零日志零 IO(face3) |
| `apps/miniprogram/pages/dev/dev.js` | 60 | CODE | 普审 | 9/9 | 无发现 | 小程序实为 3 页(index/uploads/dev,RESEARCH Pitfall 8)。HYP-14 顺带证据→移交 Phase 4 DOC(HANDOFF-PHASE4.md,状态不动):开发者菜单三重 ENV 门控(onLoad/onShow/onToggleSwitch,`dev.js:18,28,52 @ 5927f36`),production 下入口不可见 + 页面兜底文案 |
| `apps/miniprogram/utils/logger.js` | 60 | CODE | 普审 | 9/9 | 无发现 | 敏感键正则覆盖 AK/secret/token/session_key/api_key/password(`logger.js:8-9 @ 5927f36`),递归脱敏 + 前后 4 位掩码(`:11-32`);仅对象参数脱敏、标量透传属调用纪律面——现有调用点均以对象字段传值,face3 核查通过 |
| `apps/miniprogram/utils/device.js` | 60 | CODE | 普审 | 9/9 | 无发现 | 持久化失败仍返回本次生成值并注释声明降级语义(`device.js:46-51 @ 5927f36`,face1 受控);6 字符落 fragment_id 正则 4-8 区间(`:10-14`) |
| `apps/miniprogram/utils/retention.js` | 56 | CODE | 普审 | 9/9 | 无发现 | 自动清理三重前提 verified + 未清理 + 48h(`retention.js:19-34 @ 5927f36`),未 verified 永不自动删(AC#6);OSS 对象永不删除红线 docstring 明示,face2 核查通过 |
| `apps/miniprogram/utils/draft.js` | 52 | CODE | 普审 | 9/9 | 无发现 | 单槽位中断草稿(`draft.js:13-14 @ 5927f36`)后到覆盖前份系 US-013 AC#2/#6 明示设计语义(face2 对照设计不立发现);恢复提示纯函数 |
| `apps/miniprogram/config.js` | 41 | CODE | 普审 | 9/9 | 无发现 | DNF-02 对照:`issue-cedential` 拼写域名(`config.js:10 @ 5927f36`)系 Aliyun 真实分配值(`:8` 注释明示勿"修正"),负面清单排除不立发现。D14-5 证据(D-15 只记不裁):唯一代码内硬编码真实云值 `:10-15`。HYP-14 顺带证据→移交 Phase 4 DOC(HANDOFF-PHASE4.md,状态不动):`ENV = 'development'`(`:29`)现值即 development,生产发布依赖手工翻转该单点常量 |
| `apps/miniprogram/app.js` | 23 | CODE | 普审 | 9/9 | 无发现 | 极薄入口:device_short_id 幂等生成(`app.js:16 @ 5927f36`),globalData 仅 env/deviceShortId,无长期密钥无业务鉴权(docstring 红线一致,face3) |

## TOOL 维度

16 个对象(worker 验证/运维 12 + scripts 3 + Makefile 1);ops.py/latency.py/fixtures.py 归属已经基线 docstring 核实(RESEARCH):

| 路径 | 行数 | 维度 | 深度 | 已过面 | 产出 | 备注 |
|------|------|------|------|--------|------|------|
| `apps/worker/src/soniscope_worker/verify_prep.py` | 924 | TOOL | 普审 | 9/9 | F-TOOL-01 | 前置检查完整清单核实:Python≥3.11/HOME 可写/磁盘≥50GiB/ffmpeg+ffprobe(`verify_prep.py:182-227 @ 5927f36`,REQUIRED_TOOLS/MIN_DISK_BYTES 消费点)+ config 权限/必填字段(`:249-272`,只列字段名不打印值,face3 通过);报告路径异常处理完整:每个探针块独立 try/ProbeError → 单项 fail(`:400-465`),ConfigError → 显式 FAIL 报告(`:909-920`),无静默吞并。误报面:STS 反例对非拒绝类异常的误导性诊断 → F-TOOL-01;face7 轻微:`_verify_prep_object_key` docstring"不会真正写入"(`:660`)与反例 4 实际 PutObject 尝试(`:573-574`)措辞相悖(仅策略失效时才真写入,且该 key 不匹配 fragment 正则、Worker 往返校验会跳过,无主链污染面),不立发现;检查用真实云值(bucket/ARN/FC URL `:44-54`)系验证工具期望值 by-design;scans #61/#62-65(S105 env 名/TRY300 风格)销号维持误报 |
| `apps/worker/src/soniscope_worker/fc_deploy.py` | 707 | TOOL | 深挖 | 9/9 | F-TOOL-02 | 深挖 HYP-04 证实(回填见 HYPOTHESES.md):能力面 = 备份/打包/仅代码更新/回滚/日志诊断,`FcApi` Protocol 全部 6 方法无 create_function/触发器/env 配置面(`fc_deploy.py:106-119 @ 5927f36`);`update_code` 显式只传 code(`:667-672` 注释 + UpdateFunctionInput(code=code));docstring 自述"只更新代码包"(`:13`)。备份失败分支不阻断部署 → F-TOOL-02;回滚路径核查:恒回最新备份,无备份显式拒绝(`:422-427`),`rollback_one` 的 timestamp 形参未使用(ruff #41)但 CLI 面一致(`cli.py:97-107 @ 5927f36` 仅 --function,help 即"从最新备份恢复"),API 级签名误导降级不立发现;`fetch_logs` 系自述故意桩(`:704-707` "US-008 联调时补全",诊断信息可操作),hours 未使用(ruff #45)为桩的结构性结果,降级不立发现;凭证面核查通过:备份只记 env 变量名(`:367-370`),`_redact_error_text`(`:331-338`)对错误文本替换全部秘密 env 值 + LTAI/STS. AK 模式,`.env` 装载值不入任何日志——脱敏管道记 RPT-06 优点候选;SHARED_PARENT vendoring:共享包缺失静默跳过(`:200-204` docstring 自述便于单测,真实仓库恒存在;app.py 缺失则显式拒绝 `:210-211`),脆弱点可控不立发现 |
| `apps/worker/src/soniscope_worker/retranscribe.py` | 590 | TOOL | 普审 | 9/9 | 无发现 | D-03 点名的 `.done` 绕行边界核查通过,误触面受控:单条路径 fragment_id 经 `object_key_for` 合法性校验后仅定位 `fragments/<date>/<id>/`(`retranscribe.py:142-148 @ 5927f36`),非法 ID 显式 failed;批量 `--all-from` 命中集 = 日期字典序筛选 + 逐条同一决策函数(`:255-258`),无 flag 时仍只重转无 `.done` 者;`--force` 无条件覆盖系 docstring 决策表明示语义(`:14-19`),覆盖为原子 rename、audio.wav 与 OSS 对象不动,无数据丢失面;`.done` 全程零删除路径,转写失败不覆盖产物不重建 `.done`(`:185` 行内注释 + 实现一致);与主轮询共用 fragment_lock 互斥(`:180`)。备注(不立发现):决策(.done 检查)在锁外执行,竞态最坏结果为冗余重转(原子覆盖收敛,安全);重转覆盖为逐文件原子而非跨文件事务,崩溃窗口可留 manifest.transcription 与 transcript 内容短暂不一致(--upgrade 可自愈收敛);`--all-from` 日期串无格式校验,格式错误时字典序比较命中 0 并有"命中 N 个"显式日志,不静默;`--force --all-from` 无二次确认,后果限云端 ASR 成本与转写重生成(无删除面),工具级影响不足立发现;scans #57-59(ARG002 stub 桩)销号维持误报 |
| `apps/worker/src/soniscope_worker/fc_live.py` | 556 | TOOL | 深挖 | 9/9 | 无发现(D14-3 证据移交) | 深挖 D14-3 四处证据逐处核实(D-15 只采证不裁定,裁定留 03-07):① 3 错误码第二份字面定义 `fc_live.py:42-44 @ 5927f36`(INVALID_CODE/OPENID_NOT_ALLOWED/SIZE_EXCEEDED),"与 fc_shared 保持一致,避免跨包导入"注释锚点**有**(`:41`);② 7 字段清单 `CREDENTIAL_FIELDS :47-55`,锚点为 tech-spec §4.1/AC#4(`:46`),无 fc_shared 锚点;③ 50MB 隐式假设 `:57-59`(SIZE_OK=10MB/SIZE_EXCEEDED=60MB,注释"50MB 上限"为字面假设,未引用 env.py MAX_UPLOAD_BYTES 常量);④ 合成 fragment_id `make_fragment_id :254-258`(第五处 fragment_id 语法镜像,`:257` 注释自证正则子集,未 import FC/Worker 实现)。反例安全面核查通过:delete/put 反例目标均为本次合成 fragment_id 派生 key(线上不存在对象),策略失效最坏结果为写入/删除不存在的合成 key,无真实录音波及(`:483-515`);拒绝场景响应做 STS 字段泄漏反查(`:152-156`,记 RPT-06 优点候选);凭证仅内存持有,detail 只含 object_key/状态码/错误码(face3 通过);`_now()` 用 UTC(`:272-273`,face5);scans #46(S105 PASS 常量)销号维持误报 |
| `apps/worker/src/soniscope_worker/verify_upload_live.py` | 464 | TOOL | 待审 | 待审 | 待审 | D14-3(:34-35,201) |
| `apps/worker/src/soniscope_worker/ops.py` | 380 | TOOL | 待审 | 待审 | 待审 | — |
| `apps/worker/src/soniscope_worker/e2e.py` | 295 | TOOL | 待审 | 待审 | 待审 | — |
| `apps/worker/src/soniscope_worker/e2e_scenarios.py` | 268 | TOOL | 待审 | 待审 | 待审 | D14-3(导入消费端) |
| `apps/worker/src/soniscope_worker/sts_escape.py` | 268 | TOOL | 待审 | 待审 | 待审 | — |
| `apps/worker/src/soniscope_worker/fixtures.py` | 232 | TOOL | 待审 | 待审 | 待审 | D14-1(stdlib hashlib 侧 :21,118) |
| `apps/worker/src/soniscope_worker/miniprogram_lint.py` | 218 | TOOL | 待审 | 待审 | 待审 | 深挖:HYP-15(规则覆盖面;ESLint 结果量化其漏报) |
| `apps/worker/src/soniscope_worker/latency.py` | 80 | TOOL | 待审 | 待审 | 待审 | — |
| `scripts/test_asr.py` | 355 | TOOL | 待审 | 待审 | 待审 | 深挖:HYP-07(`DEFAULT_FILE_LINK` 约 :80 过期预签名 URL)、HYP-18(legacy AcsClient);HYP-25 顺带证据(→移交 Phase 4,D-11) |
| `scripts/fetch_test_fixtures.py` | 249 | TOOL | 待审 | 待审 | 待审 | HYP-25 顺带证据(→移交) |
| `scripts/gen_worker_config.sh` | 243 | TOOL | 待审 | 待审 | 待审 | — |
| `Makefile` | 171 | TOOL | 待审 | 待审 | 待审 | 45 个目标;静读审计,不执行任何目标(D-08);按功能组过关注面 + 危险目标逐个细读(RESEARCH Open Question 3 裁决) |

## 深挖点登记(20 处)

14 条 HYP(CODE 10 + TOOL 4,回填集写死,RESEARCH Pitfall 4)+ 6 条 D14 移交线索;命中模块路径照抄 03-RESEARCH.md 审计对象全量清单"深挖线索"列(HYP-01/20 为结构性缺席类,命中区域为 apps/fc/ 目录结构本身):

| 线索 | 维度 | 命中模块路径 | 下落 |
|------|------|--------------|------|
| HYP-01 | CODE | apps/fc/ 目录结构(transcribe_audio/ 缺席,基线仅 issue_credential/ 与 verify_upload/) | 待审 |
| HYP-03 | CODE | apps/miniprogram/utils/sha256.js(D-16 微基准对象) | 待审 |
| HYP-08 | CODE | apps/worker/src/soniscope_worker/config.py、apps/fc/shared/fc_shared/env.py、apps/fc/shared/fc_shared/audit.py | 待审 |
| HYP-09 | CODE | apps/fc/shared/fc_shared/sts.py、apps/fc/shared/fc_shared/auth.py | 待审 |
| HYP-10 | CODE | apps/worker/src/soniscope_worker/pipeline.py、apps/worker/src/soniscope_worker/poller.py | 待审 |
| HYP-12 | CODE | apps/fc/shared/app.py | 待审 |
| HYP-16 | CODE | apps/worker/src/soniscope_worker/poller.py | 待审 |
| HYP-17 | CODE | apps/fc/shared/fc_shared/sts.py、apps/fc/issue_credential/handler.py | 待审 |
| HYP-19 | CODE | apps/worker/src/soniscope_worker/nls.py、apps/worker/src/soniscope_worker/transcriber.py | 待审 |
| HYP-20 | CODE | apps/fc/ 目录结构(transcribe-audio 已决策未建) | 待审 |
| HYP-04 | TOOL | apps/worker/src/soniscope_worker/fc_deploy.py | 待审 |
| HYP-07 | TOOL | scripts/test_asr.py(DEFAULT_FILE_LINK 约 :80;与五类秘密扫描同批,D-06) | 待审 |
| HYP-15 | TOOL | apps/worker/src/soniscope_worker/miniprogram_lint.py | 待审 |
| HYP-18 | TOOL | scripts/test_asr.py(legacy AcsClient SDK) | 待审 |
| D14-1 | CODE | apps/miniprogram/utils/sha256.js、apps/miniprogram/pages/index/index.js(:30,640)、apps/worker/src/soniscope_worker/fixtures.py(:21,118)、apps/worker/src/soniscope_worker/poller.py(比对流程) | 待审 |
| D14-2 | CODE | apps/worker/src/soniscope_worker/nls.py(:45)、apps/miniprogram/utils/uploader.js(:28)、apps/miniprogram/utils/verify.js(:16) | 待审 |
| D14-3 | TOOL | apps/worker/src/soniscope_worker/fc_live.py(:42-59,256)、apps/worker/src/soniscope_worker/verify_upload_live.py(:34-35,201)、apps/worker/src/soniscope_worker/e2e_scenarios.py(导入消费端) | 待审 |
| D14-4 | CODE | apps/miniprogram/utils/queue_runtime.js(:94-128)、apps/miniprogram/pages/uploads/uploads.js(:340,365) | 待审 |
| D14-5 | CODE | apps/miniprogram/config.js(:10-15,唯一代码内硬编码真实云值) | 待审 |
| D14-6 | CODE | apps/miniprogram/utils/upload_queue.js(:38-44,`fragmentIdFromObjectKey` 无校验切割,关联 F-CON-03) | 待审 |

## 完成判定

(占位——03-07 收口时填:覆盖对象总数对账、深挖点逐点下落、已过面 9/9 全模块核对、可复算命令 + 数字 + ✓,格式仿 CONTRACT-MATRIX ④完成判定。)
