# 契约漂移矩阵

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本矩阵是 Phase 2(契约抽取与漂移分析)的核心证据文档:行 = 契约要素(D-02 逐字段),列 = FC(`fc_shared`)/ Worker / 小程序(utils)三处实现(D-04 严格三列)+ 判定列。每个非 n/a 格标注状态词 + `path:line @ 5927f36` 行号证据(D-11,agree 格同样带行号);n/a 格写一句结构性理由代替行号(D-03)。全部证据出自 `git show 5927f36:<path>` / `git grep -n <pat> 5927f36 -- apps/`,禁止读工作树取证(D-05)。

## 判定标准与负面清单

### 格子状态词表

| 状态词 | 定义 |
|--------|------|
| `agree` | 该实现与其他参与实现在此契约要素上**语义一致**(字面差异不算分歧,见下) |
| `diverge` | 该实现与其他参与实现存在**语义分歧**——同样输入可产生不同的契约行为 |
| `absent` | 该实现**应参与**此契约要素但未实现(覆盖洞候选,per D-03) |
| `n/a` | **结构性不适用**——该实现在架构上不承担此要素的角色;格内写一句结构性理由代替行号(per D-03) |

**diverge 判定规则(RESEARCH Pitfall 5):** diverge 指**语义分歧**,不是字面差异。值形态不同但语义约定一致(两侧注释/文档均声明同一约定)的格标 `agree` 并在格内注明映射约定行号。典型案例:chunk_total 的小程序 manifest `null` → OSS meta `"0"` → Worker manifest `None` 三段映射。

**判定列规则(D-12):** 本阶段 02-01/02-02/02-03 一律填 `待判定`;四类标签(良性/潜伏/活跃/覆盖洞)与 F-CON-NN 链接由 02-04 回填。Postel 生产者-消费者宽严分析写入 F-CON 条目,不进矩阵。

### 负面清单(判定前置排除)

以下事项**不得**立为契约分歧(依据 `.planning/audit/DO-NOT-FIX.md` DNF-01~04 与 CHARTER 排除项表):

- **DNF-01~04 已裁定的故意设计**——包括 `issue-cedential` 域名拼写(DNF-02,阿里云分配的真实 URL)、小程序接收原始 STS 秘密下发(DNF-04)等,均不立 F-CON。
- **不引入 `docs/fc-transcribe-design.md` 目标态对照**(CHARTER 明确排除项):契约一致性以三处实现现状互相对照为准。
- chunk_total `null`↔`"0"`↔`None` 三段映射是文档化约定(`apps/miniprogram/utils/audio.js:156 @ 5927f36` 注释 + `apps/worker/src/soniscope_worker/poller.py:118 @ 5927f36` ManifestDraft docstring),不得机械判 diverge。

## 组① OSS 数据面

> D-01 组①:fragment_id、object key、全部 `x-oss-meta-*` 元数据字段。key 族六行由 02-01 Task 1 落格;元数据九行由 02-01 Task 2 落格。RESEARCH 勘察行号为起点,以下全部行号已经 `git show 5927f36:<path>` 逐一复核,以复核后实际行号为准。

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 1. fragment_id 格式正则 | agree `apps/fc/shared/fc_shared/sts.py:30-33 @ 5927f36`(`_FRAGMENT_ID_RE`,含命名捕获组) | agree `apps/worker/src/soniscope_worker/oss_admin.py:24-27 @ 5927f36`(`_FRAGMENT_ID_RE`,与 FC 逐字符相同) | agree `apps/miniprogram/utils/audio.js:95-96 @ 5927f36`(`FRAGMENT_ID_RE`,无命名捕获组但匹配语义等价) | 待判定 |
| 2. fragment_id 日期合法性校验 | agree `apps/fc/shared/fc_shared/sts.py:54-58 @ 5927f36`(正则命中后 `datetime()` 构造校验,非法抛 400 INVALID_REQUEST) | agree `apps/worker/src/soniscope_worker/oss_admin.py:45-49 @ 5927f36`(同样 `datetime.datetime()` 构造校验,非法抛 `OssAdminError`) | absent `apps/miniprogram/utils/audio.js:95-96 @ 5927f36`(正则仅 `\d{4}\d{2}\d{2}` 形状校验,匹配路径上无任何日期合法性检查;如 `20260231` 可通过) | 待判定 |
| 3. object key 模板 `recordings/<YYYY-MM-DD>/<id>.wav` | agree `apps/fc/shared/fc_shared/sts.py:46-59 @ 5927f36`(`object_key_for`,f-string 模板 :59) | agree `apps/worker/src/soniscope_worker/oss_admin.py:37-50 @ 5927f36`(`object_key_for`,f-string 模板 :50) | agree `apps/miniprogram/utils/audio.js:104-106 @ 5927f36`(`buildObjectKeyPreview`,字符串拼接 :105,`.wav` 来自 `OSS_OBJECT_KEY_EXT`) | 待判定 |
| 4. key 目录日期来源 | agree `apps/fc/shared/fc_shared/sts.py:54,59 @ 5927f36`(year/month/day 取自 fragment_id 正则捕获组前缀) | agree `apps/worker/src/soniscope_worker/oss_admin.py:45,50 @ 5927f36`(同 FC:取自 fragment_id 前缀) | diverge `apps/miniprogram/utils/audio.js:104-105,63-67 @ 5927f36`(`buildObjectKeyPreview(fragmentId, recordedAt)` 两个独立入参,日期取自 `objectKeyDate(recordedAt)` 本地时区,与 fragment_id 前缀无绑定) | 待判定 |
| 5. key → fragment_id 反推 | n/a — FC 只正向签发 object key(`object_key_for`),两个 handler 均无从 key 反推 fragment_id 的代码路径,结构上不承担反推角色 | agree `apps/worker/src/soniscope_worker/poller.py:47-61 @ 5927f36`(`fragment_id_from_key`,以 `object_key_for(fragment_id) == key` 往返校验 :57,连带保证格式、日期合法、目录日期与前缀一致) | diverge `apps/miniprogram/utils/upload_queue.js:38-44 @ 5927f36`(`fragmentIdFromObjectKey`,纯字符串切割:取最后一个 `/` 后、最后一个 `.` 前,无格式/日期/往返校验——普查发现的第四处实现) | 待判定 |
| 6. `.wav` 固定扩展名 | agree `apps/fc/shared/fc_shared/sts.py:59 @ 5927f36`(f-string 尾部硬编码 `.wav`) | agree `apps/worker/src/soniscope_worker/poller.py:53 @ 5927f36`(`key.endswith(".wav")` 过滤)+ `apps/worker/src/soniscope_worker/oss_admin.py:50 @ 5927f36`(f-string 尾部) | agree `apps/miniprogram/config.js:26 @ 5927f36`(`OSS_OBJECT_KEY_EXT = '.wav'` 常量,经 `apps/miniprogram/utils/audio.js:10 @ 5927f36` require,:105 拼接使用) | 待判定 |
| 7. `x-oss-meta-session-id` | n/a — FC 职责限于 STS 签发与 HeadObject 大小校验,无任何 meta 读写路径(见下方 FC 触点核实) | agree `apps/worker/src/soniscope_worker/poller.py:34 @ 5927f36`(`META_SESSION_ID` 常量)+ `poller.py:139 @ 5927f36`(`metadata_to_draft` 映射 `session_id`) | agree `apps/miniprogram/utils/audio.js:162 @ 5927f36`(`buildOssMetadata` 写入,`String(manifest.session_id \|\| '')`)(键名被测试锁定:`test/ids.test.js:128`) | 待判定 |
| 8. `x-oss-meta-chunk-seq` | n/a — 同上,FC 无 meta 读写路径 | agree `apps/worker/src/soniscope_worker/poller.py:35 @ 5927f36`(`META_CHUNK_SEQ`)+ `poller.py:140 @ 5927f36`(`_as_int` 映射 `chunk_seq`) | agree `apps/miniprogram/utils/audio.js:163 @ 5927f36`(写入 `String(manifest.chunk_seq)`)(测试锁定:`test/ids.test.js:129`) | 待判定 |
| 9. `x-oss-meta-chunk-total` | n/a — 同上,FC 无 meta 读写路径 | agree `apps/worker/src/soniscope_worker/poller.py:36 @ 5927f36`(`META_CHUNK_TOTAL`)+ `poller.py:134-136,141 @ 5927f36`(`_as_int` + `<=0 → None` 映射) | agree `apps/miniprogram/utils/audio.js:160,164 @ 5927f36`(`null → 0` 转换后写入)(测试锁定:`test/ids.test.js:130`) | 待判定 |
| 10. `x-oss-meta-recorded-at` | n/a — 同上,FC 无 meta 读写路径 | agree `apps/worker/src/soniscope_worker/poller.py:37 @ 5927f36`(`META_RECORDED_AT`)+ `poller.py:142 @ 5927f36`(字符串透传映射 `recorded_at`) | agree `apps/miniprogram/utils/audio.js:165 @ 5927f36`(写入 `String(manifest.recorded_at \|\| '')`)(测试锁定:`test/ids.test.js:131`) | 待判定 |
| 11. `x-oss-meta-duration` | n/a — 同上,FC 无 meta 读写路径 | agree `apps/worker/src/soniscope_worker/poller.py:38 @ 5927f36`(`META_DURATION`)+ `poller.py:143 @ 5927f36`(`_as_float` 映射 `duration_seconds`) | agree `apps/miniprogram/utils/audio.js:166 @ 5927f36`(写入 `String(manifest.duration_seconds)`)(测试锁定:`test/ids.test.js:132`) | 待判定 |
| 12. `x-oss-meta-original-format` | n/a — 同上,FC 无 meta 读写路径 | agree `apps/worker/src/soniscope_worker/poller.py:39 @ 5927f36`(`META_ORIGINAL_FORMAT`)+ `poller.py:144 @ 5927f36`(映射)+ `apps/worker/src/soniscope_worker/manifest.py:128-132 @ 5927f36`(meta 缺失时以 ffprobe 探测值回退) | agree `apps/miniprogram/utils/audio.js:167 @ 5927f36`(写入 `String(audio.original_format \|\| '')`)(测试锁定:`test/ids.test.js:133`) | 待判定 |
| 13. `x-oss-meta-sha256` | absent — verify-upload 职责即上传完整性校验,HeadObject 响应可携带该 meta 但实现只读 Content-Length/ETag(`apps/fc/shared/fc_shared/head.py:24-31 @ 5927f36` `ObjectHead` 仅四字段);`head.py:9-10 @ 5927f36` docstring 声明"无法校验 sha256,见 §4.2 注"——是否构成覆盖洞留 02-04 裁定 | agree `apps/worker/src/soniscope_worker/poller.py:40 @ 5927f36`(`META_SHA256`)+ `poller.py:145 @ 5927f36`(映射 `original_sha256`)+ `poller.py:272-283 @ 5927f36`(下载后 sha256 比对,不一致删 `.part` 重下) | agree `apps/miniprogram/utils/audio.js:168 @ 5927f36`(写入 `String(upload.original_sha256 \|\| '')`)(测试锁定:`test/ids.test.js:134`) | 待判定 |
| 14. chunk_total 语义映射(非分片 `null`→`"0"`→`None`) | n/a — FC 无 meta 读写路径,不参与该映射链 | agree `apps/worker/src/soniscope_worker/poller.py:116-118 @ 5927f36`(`ManifestDraft` docstring 声明 §3.2 约定:OSS `"0"` → manifest `None`)+ `poller.py:134-136 @ 5927f36`(转换实现) | agree `apps/miniprogram/utils/audio.js:156 @ 5927f36`(注释声明:非分片 chunk_total 在 OSS meta 中写 0,manifest 内为 null)+ `audio.js:160 @ 5927f36`(转换实现) | 待判定 |
| 15. recorded-at 值格式 | n/a — FC 无 meta 读写路径,不消费该值 | agree `apps/worker/src/soniscope_worker/poller.py:142 @ 5927f36`(不解析,字符串透传)+ `apps/worker/src/soniscope_worker/manifest.py:139 @ 5927f36`(原样写入 manifest `recorded_at`)——消费端对格式无断言,宽容透传 | agree `apps/miniprogram/utils/audio.js:76-85 @ 5927f36`(`toIso`:本地时区偏移 ISO 8601,如 `+08:00` 后缀;:165 写入) | 待判定 |

### 组① key 族证据摘录

**行 1 正则逐字符对照**(FC 与 Worker 完全一致;小程序无命名捕获组、字符类与锚点等价):

- FC / Worker(`sts.py:31-32` / `oss_admin.py:25-26 @ 5927f36`):`^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})T\d{6}` + `_[A-Za-z0-9]{4,8}_[0-9A-Za-z]{26}$`
- 小程序(`audio.js:96 @ 5927f36`):`/^\d{4}\d{2}\d{2}T\d{6}_[A-Za-z0-9]{4,8}_[0-9A-Za-z]{26}$/`

**行 2 差异点**:FC(`sts.py:56 @ 5927f36`)与 Worker(`oss_admin.py:47 @ 5927f36`)在正则命中后均执行 `datetime(int(year), int(month), int(day))` 合法性校验(行内注释 `noqa: DTZ001 - 仅校验日期合法性`);小程序正则命中即通过,无后续校验——往返校验样本高价值边界(02-03 输入)。

**行 4 差异点**:小程序 `objectKeyDate`(`audio.js:63-67 @ 5927f36`)基于 `date.getFullYear()/getMonth()/getDate()` 本地时区推导 `<YYYY-MM-DD>`;`buildObjectKeyPreview`(`audio.js:104 @ 5927f36`)的 `fragmentId` 与 `recordedAt` 为两个独立入参,目录日期与 fragment_id 时间前缀之间无一致性约束;FC/Worker 则从 fragment_id 前缀单一来源推导。

### 组① 元数据证据注记(行 7-15)

**FC 列 n/a/absent 裁决的静态支撑**:`git grep -n 'x-oss-meta' 5927f36 -- apps/fc/` 仅命中一处——`apps/fc/tests/test_fc_shared.py:196 @ 5927f36`(测试断言 `is_sensitive("x-oss-meta-sha256") is False`,属日志脱敏白名单测试,非契约读写触点)。FC 生产代码(`fc_shared/` 与两个 handler)零 `x-oss-meta` 触点。据此:行 7-12、14、15 判 n/a(FC 的 STS 签发 / HeadObject 大小校验职责结构上不触及这些字段);行 13(sha256)判 absent 候选——verify-upload 的职责语义(上传完整性校验)使其成为该字段的应然参与方,但 `head.py:9-10 @ 5927f36` docstring 引 tech-spec §4.2 注声明设计上不校验 sha256,是否定为覆盖洞由 02-04 归类。

**写读两端键名逐一对照**:小程序写入端 7 键(`audio.js:162-168 @ 5927f36`)与 Worker 读取端 7 常量(`poller.py:34-40 @ 5927f36`)逐字符一致(`session-id`/`chunk-seq`/`chunk-total`/`recorded-at`/`duration`/`original-format`/`sha256`);Worker `normalize_metadata`(`poller.py:85-93 @ 5927f36`)统一小写并剥离 `x-oss-meta-` 前缀后按短键匹配,兼容 SDK 读回时带/不带前缀两种形态。manifest 落盘链:`metadata_to_draft`(`poller.py:131-146 @ 5927f36`)→ `build_manifest`(`manifest.py:133-146 @ 5927f36` 区段逐字段透传)。

**行 14 判定依据(Pitfall 5)**:小程序 manifest `null` → OSS meta `"0"`(`audio.js:156,160 @ 5927f36`)与 Worker OSS `"0"` → manifest `None`(`poller.py:118,134-136 @ 5927f36`)两侧均以注释/docstring 声明同一 §3.2 约定——字面异/语义同,判 agree,不得机械判 diverge。

**行 15 注记**:生产端格式为本地时区偏移 ISO 8601(`toIso`,`audio.js:76-85 @ 5927f36`,注释示例 `2026-05-26T14:48:00+08:00`);Worker 消费端不解析该值(`poller.py:142 @ 5927f36` `meta.get(META_RECORDED_AT) or None` 透传字符串),manifest 原样落盘——静态层面无格式冲突;生产者-消费者宽严(Postel)分析按 D-12 留给 02-04 的 F-CON 条目。

## 组② 小程序↔FC HTTP 契约

> D-01 组②:issue-credential 与 verify-upload 的请求/响应 JSON 字段、7 个错误码字符串、2 个 verify reason。本组契约仅存在于小程序↔FC 之间,**Worker 列全部 n/a**(Worker 业务流水线只消费 OSS 数据面,不调用 FC HTTP 接口——结构性理由代替行号,per D-03/D-04;Worker 侧联调工具 fc_live.py / verify_upload_live.py 中的契约常量镜像属普查命中,见普查节行 44-46,不占本组 Worker 列)。小程序侧请求组装取 utils 层 `queue_runtime.js`(D-04 列限定 utils);pages 层存在同构第二份组装(`apps/miniprogram/pages/uploads/uploads.js:340,365 @ 5927f36`),作为行下注与普查移交线索记录,不占列。全部行号已经 `git show 5927f36:<path>` 逐一复核。

### 组②-a issue-credential 请求字段(行 16-18)

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 16. 请求字段 `code` | agree `apps/fc/shared/fc_shared/auth.py:48-50 @ 5927f36`(`require_fields(("code", *extra_fields))` :48、`str(body["code"])` :49 → jscode2session 换 openid :50) | n/a — Worker 不调用小程序↔FC HTTP 接口,无微信登录态 | agree `apps/miniprogram/utils/queue_runtime.js:103 @ 5927f36`(请求体键 `code`,值来自 wxLogin `queue_runtime.js:85-90 @ 5927f36`) | 待判定 |
| 17. 请求字段 `fragment_id` | agree `apps/fc/issue_credential/handler.py:45 @ 5927f36`(extra_fields 必填)+ `handler.py:50 @ 5927f36`(`str(ctx.body["fragment_id"])` → `object_key_for`) | n/a — 同上 | agree `queue_runtime.js:103 @ 5927f36`(键 `fragment_id`;经 `apps/miniprogram/utils/uploader.js:86 @ 5927f36` deps.requestSts 透传) | 待判定 |
| 18. 请求字段 `size` | agree `handler.py:48-49 @ 5927f36`(parse_size + check_size)+ `apps/fc/shared/fc_shared/sts.py:76-88 @ 5927f36`(`parse_size`:接受 int 或纯数字字符串、显式拒 bool、≤0 抛 400 INVALID_REQUEST) | n/a — 同上 | agree `queue_runtime.js:103 @ 5927f36`(键 `size`)+ `uploader.js:63 @ 5927f36`(值 = `manifest.audio.size_bytes`,缺失回退 `0`) | 待判定 |

**行 18 边界注记(size=0):** 小程序 manifest 缺失时发 `size=0`(`uploader.js:63 @ 5927f36` 的 `|| 0` 回退),FC `parse_size` 判 `size <= 0` 抛 400 INVALID_REQUEST(`sts.py:86-87 @ 5927f36`)——生产者可产出消费者必拒的值;宽严归类留 02-04 Postel 分析(D-12)。

### 组②-b issue-credential 响应字段(行 19-25)

FC 侧 7 字段全部出自 `credential_response`(`sts.py:102-114 @ 5927f36`,docstring 自证"含 7 个字段,AC#6");小程序侧字段名清单与必备性校验统一在 `uploader.js:17-25 @ 5927f36`(`CREDENTIAL_FIELDS` 7 字段名与 FC 逐字符同名)+ `uploader.js:34-44 @ 5927f36`(200 且 7 字段全非空才判凭证有效,任一缺失判 `INCOMPLETE_CREDENTIAL` :45)。下表小程序格的"消费"指字段值的实际下游用途;**未消费的字段如实标注**。

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 19. 响应字段 `access_key_id` | agree `sts.py:107 @ 5927f36` | n/a — Worker 不消费 FC HTTP 响应 | agree `uploader.js:18 @ 5927f36`(必备)+ `apps/miniprogram/utils/oss_sign.js:63,71-72 @ 5927f36`(拼 x-oss-credential;formData :100) | 待判定 |
| 20. 响应字段 `access_key_secret` | agree `sts.py:108 @ 5927f36` | n/a — 同上 | agree `uploader.js:19 @ 5927f36` + `oss_sign.js:64,93 @ 5927f36`(仅入 V4 派生签名链,不落日志——`uploader.js:7 @ 5927f36` 注释红线) | 待判定 |
| 21. 响应字段 `security_token` | agree `sts.py:109 @ 5927f36` | n/a — 同上 | agree `uploader.js:20 @ 5927f36` + `oss_sign.js:65,81,102 @ 5927f36`(policy 条件 + formData) | 待判定 |
| 22. 响应字段 `expiration` | agree `sts.py:110 @ 5927f36` | n/a — 同上 | agree(键名与必备性)`uploader.js:21,35-37 @ 5927f36`(非空校验)——**值无任何下游消费**:`oss_sign.js` 不读该字段,表单 policy 过期用本地 `now + 900s` 独立推导(`oss_sign.js:16,91 @ 5927f36`);STS 过期实际由 OSS 服务端强制。消费缺席如实标注,归类留 02-04 | 待判定 |
| 23. 响应字段 `bucket` | agree `sts.py:111 @ 5927f36`(值来自 FC env OSS_BUCKET,`handler.py:108 @ 5927f36`) | n/a — 同上 | agree `uploader.js:22 @ 5927f36` + `oss_sign.js:67,76 @ 5927f36`(policy bucket 条件) | 待判定 |
| 24. 响应字段 `endpoint` | agree `sts.py:112 @ 5927f36`(值来自 FC env OSS_ENDPOINT,`handler.py:108 @ 5927f36`) | n/a — 同上 | agree(键名与必备性)`uploader.js:23,35-37 @ 5927f36`(非空校验)——**值无下游消费**:上传 URL 用 `config.OSS_UPLOAD_URL`(`queue_runtime.js:154 @ 5927f36` → `oss_sign.js:60,110 @ 5927f36`),credential.endpoint 被忽略。如实标注,归类留 02-04 | 待判定 |
| 25. 响应字段 `object_key` | agree `sts.py:113 @ 5927f36`(值由 `handler.py:50 @ 5927f36` 服务端从 fragment_id 解析,模板见组① 行 3) | n/a — 同上 | agree `uploader.js:24 @ 5927f36` + `oss_sign.js:66,77,97 @ 5927f36`(policy `eq $key` 精确条件 + formData key)+ `uploader.js:102,112 @ 5927f36`(AC#4 注释与日志) | 待判定 |

**行 25 AC#4 语义注记:** 小程序 object_key **用 FC 返回值,不由前端拼接覆盖**(`uploader.js:102 @ 5927f36` 注释、`oss_sign.js:50-52 @ 5927f36` docstring 双重声明)——这是往返链关键环:FC `object_key_for` 签发 → 小程序原样使用 → Worker `fragment_id_from_key` 反推。02-03 将对此链做执行佐证。小程序 `buildObjectKeyPreview`(组① 行 3/4)仅用于本地预览/去重键,不参与上传 key。

### 组②-c verify-upload 请求字段(行 26-28)

字段全集依据(RESEARCH Open Question 2 裁决):`apps/fc/verify_upload/handler.py:46-48 @ 5927f36`(`authorize_request(..., extra_fields=("fragment_id", "expected_size"))`)+ `handler.py:51-52 @ 5927f36`——请求字段全集 = `code` + `fragment_id` + `expected_size`,共 3 字段,无其他读取。

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 26. 请求字段 `code`(verify) | agree `auth.py:48-50 @ 5927f36`(与 issue-credential 同一共享鉴权路径;入口 `verify_upload/handler.py:46-48 @ 5927f36`) | n/a — Worker 不调用 FC HTTP 接口 | agree `queue_runtime.js:123 @ 5927f36`(键 `code`)+ `apps/miniprogram/utils/verify.js:68,71 @ 5927f36`(code 一次性,每轮重试重新 login) | 待判定 |
| 27. 请求字段 `fragment_id`(verify) | agree `verify_upload/handler.py:47 @ 5927f36`(必填)+ `handler.py:52 @ 5927f36`(`object_key_for`) | n/a — 同上 | agree `queue_runtime.js:123 @ 5927f36` + `verify.js:87 @ 5927f36`(透传) | 待判定 |
| 28. 请求字段 `expected_size` | agree `verify_upload/handler.py:51 @ 5927f36`(`parse_size(ctx.body.get("expected_size"))`,复用 `sts.py:76-88 @ 5927f36` 同一解析) | n/a — 同上 | agree `queue_runtime.js:123 @ 5927f36`(键 `expected_size`)+ `verify.js:59-60 @ 5927f36`(值 = `manifest.audio.size_bytes` 回退 `0`——同行 18 的 size=0 边界) | 待判定 |

### 组②-d verify-upload 响应字段(行 29-34)

字段全集依据(Open Question 2):FC 侧全部出自 `verify_upload_result`(`apps/fc/shared/fc_shared/head.py:34-55 @ 5927f36`,三态映射:不存在 / 大小不符 / 一致)——响应字段全集 = `verified` + `reason` + `actual_size` + `etag` + `size` + `last_modified`,共 6 字段。小程序侧分类在 `classifyVerifyResponse`(`verify.js:28-51 @ 5927f36`)。

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 29. 响应字段 `verified` | agree `head.py:43,45,51 @ 5927f36`(false 两分支 + true 分支均携带) | n/a — Worker 不消费 FC HTTP 响应 | agree `verify.js:32 @ 5927f36`(`data.verified === true` 严格布尔判定;非 true 一律走 unverified 分支 :40-44) | 待判定 |
| 30. 响应字段 `reason` | agree `head.py:43,47 @ 5927f36`(OBJECT_NOT_FOUND / SIZE_MISMATCH 两分支) | n/a — 同上 | agree `verify.js:42 @ 5927f36`(`String(data.reason)`,缺失回退 `'UNKNOWN'`)+ `verify.js:103 @ 5927f36`(随状态补丁落存;pages 展示端 `uploads.wxml:23 @ 5927f36` 渲染,不占列括注) | 待判定 |
| 31. 响应字段 `actual_size` | agree `head.py:48 @ 5927f36`(仅 SIZE_MISMATCH 分支携带) | n/a — 同上 | agree(提取)`verify.js:43 @ 5927f36`(actualSize)——**提取后未落存**:`verifyFragment` 状态补丁仅含 reason(`verify.js:101-105 @ 5927f36`)。如实标注 | 待判定 |
| 32. 响应字段 `etag` | agree `head.py:52 @ 5927f36` | n/a — 同上 | agree(提取)`verify.js:35 @ 5927f36`——verified 分支仅落存 verifiedAt(`verify.js:94-99 @ 5927f36`),etag 提取后丢弃。如实标注 | 待判定 |
| 33. 响应字段 `size` | agree `head.py:53 @ 5927f36`(Content-Length 回显) | n/a — 同上 | agree(提取)`verify.js:36 @ 5927f36`——同行 32,未落存 | 待判定 |
| 34. 响应字段 `last_modified` | agree `head.py:54 @ 5927f36` | n/a — 同上 | agree(提取)`verify.js:37 @ 5927f36`(lastModified)——同行 32,未落存 | 待判定 |

### 组②-e 错误码字符串(行 35-41)

**小程序侧裁决(RESEARCH Open Question 1,以 classifyFcResponse 全文为证):** 对照 `classifyFcResponse` 全文(`uploader.js:32-50 @ 5927f36`)与 `classifyVerifyResponse` 全文(`verify.js:28-51 @ 5927f36`)——**小程序不按错误码字符串分支**:uploader 按 `statusCode === 200` 与否二分(`uploader.js:34 @ 5927f36`);verify 按 200 / ≥500 / 其余 4xx 三段(`verify.js:31,46,49 @ 5927f36`);`data.error` 仅作通用透传(`uploader.js:48 @ 5927f36`、`verify.js:49 @ 5927f36` 的 `String(data.error)`)记录与展示,行为不依赖具体码值。7 个错误码字面量在小程序**实现代码**中零出现(`uploader.js:47 @ 5927f36` 提及 3 码但为注释非代码)。故 7 行小程序格统一判 **absent**(字面量未实现;通用透传使每码行为等同——是覆盖洞还是良性设计留 02-04 归类)。

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 35. 错误码 `INVALID_CODE`(401) | agree `apps/fc/shared/fc_shared/errors.py:13 @ 5927f36`(定义)+ `wechat.py:45,47,51 @ 5927f36`(raise) | n/a — Worker 不参与 HTTP 错误码契约(联调工具镜像见普查行 44) | absent — 字面量零出现,经 `uploader.js:48 @ 5927f36` 通用透传(测试锁定:`test/uploader.test.js` 含码字符串断言) | 待判定 |
| 36. 错误码 `OPENID_NOT_ALLOWED`(403) | agree `errors.py:14 @ 5927f36` + `auth.py:36 @ 5927f36`(raise) | n/a — 同上 | absent — 同行 35 裁决 | 待判定 |
| 37. 错误码 `INVALID_REQUEST`(400) | agree `errors.py:15 @ 5927f36` + `http.py:63,67,69,78 @ 5927f36` + `sts.py:53,58,79,85,87 @ 5927f36`(raise) | n/a — 同上 | absent — 同行 35 裁决 | 待判定 |
| 38. 错误码 `SIZE_EXCEEDED`(400) | agree `errors.py:16 @ 5927f36` + `sts.py:93-99 @ 5927f36`(raise,附 limit_bytes / actual_bytes) | n/a — 同上 | absent — 同行 35 裁决(`uploader.js:47 @ 5927f36` 注释提及但非代码分支) | 待判定 |
| 39. 错误码 `SERVER_MISCONFIGURED`(500) | agree `errors.py:17 @ 5927f36` + `issue_credential/handler.py:61 @ 5927f36`、`verify_upload/handler.py:63 @ 5927f36`(附 missing 变量名列表) | n/a — 同上 | absent — 同行 35 裁决 | 待判定 |
| 40. 错误码 `STS_ISSUE_FAILED`(500) | agree `errors.py:18 @ 5927f36` + `issue_credential/handler.py:92 @ 5927f36` | n/a — 同上 | absent — 同行 35 裁决 | 待判定 |
| 41. 错误码 `HEAD_OBJECT_FAILED`(500) | agree `errors.py:19 @ 5927f36` + `verify_upload/handler.py:93 @ 5927f36` | n/a — 同上 | absent — 同行 35 裁决 | 待判定 |

**行 35-41 移交线索(Phase 4 DOC 维度):** CLAUDE.md("Naming Patterns"节)声明错误码字符串 "shared verbatim between Python FC handlers and miniprogram JS (`uploader.js` branches on the same strings)" 与实态不符——uploader.js 实为 statusCode 段分支 + `error` 字段通用透传,错误码字面量不在小程序实现代码中(上表逐行为证)。本矩阵不立 DOC 判断,仅记移交。

**行 35-41 错误响应包络注记:** FC 错误响应体固定含 `error` 字段(`errors.py:38 @ 5927f36` payload 组装),可选 `message` 与 extra 字段(如行 38 的 limit_bytes、行 39 的 missing);小程序仅读 `error` 一个键,extra 字段全部无消费——静态层面无键名冲突。

### 组②-f verify reason(行 42-43)

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 42. reason `OBJECT_NOT_FOUND` | agree `errors.py:23 @ 5927f36`(定义)+ `head.py:43 @ 5927f36`(响应组装) | n/a — Worker 不消费 verify 响应(联调工具镜像见普查行 46) | agree `verify.js:20 @ 5927f36`(`REASON_OBJECT_NOT_FOUND` 字面量逐字符一致)——分支仍为通用透传(`verify.js:42 @ 5927f36`),常量当前仅模块导出(`verify.js:134 @ 5927f36`)供测试/故障注入消费(测试锁定:`test/verify.test.js`;故障注入 mock 字面量 `queue_runtime.js:116 @ 5927f36`) | 待判定 |
| 43. reason `SIZE_MISMATCH` | agree `errors.py:24 @ 5927f36` + `head.py:47 @ 5927f36` | n/a — 同上 | agree `verify.js:21 @ 5927f36`(`REASON_SIZE_MISMATCH`)——同行 42(导出 `verify.js:135 @ 5927f36`) | 待判定 |

## 组③ 两侧镜像常量

*(02-02 填)*

## 重复逻辑普查

*(02-02 填)*

## 往返校验结论

*(02-03 填)*

## 附录:往返校验样本清单

*(02-03 填)*

## 收尾:零 diff 验证与对账

*(02-04 填)*

---
*契约漂移矩阵: 2026-07-05(组① OSS 数据面 15 行全部落格:key 族 6 行 + 元数据 9 行;判定列待 02-04 回填)*
