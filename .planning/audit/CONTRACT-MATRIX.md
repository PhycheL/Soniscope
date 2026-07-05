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

**判定列规则(D-12):** 本阶段 02-01/02-02/02-03 一律填 `待判定`;四类标签(良性/潜伏/活跃/覆盖洞)与 F-CON-NN 链接由 02-04 回填。Postel 生产者-消费者宽严分析写入 F-CON 条目,不进矩阵。**(02-04 已全部回填:diverge/absent 格 → 四类标签 + F-CON 链接;agree 格 → `—`,行 14/20/21 附负面清单排除注,行 18/22/24 的既留裁决以判定列括注收口——12 个 diverge/absent 格对应 F-CON-01~06 六条发现,见 `findings/contract.md`。)**

### 负面清单(判定前置排除)

以下事项**不得**立为契约分歧(依据 `.planning/audit/DO-NOT-FIX.md` DNF-01~04 与 CHARTER 排除项表):

- **DNF-01~04 已裁定的故意设计**——包括 `issue-cedential` 域名拼写(DNF-02,阿里云分配的真实 URL)、小程序接收原始 STS 秘密下发(DNF-04)等,均不立 F-CON。
- **不引入 `docs/fc-transcribe-design.md` 目标态对照**(CHARTER 明确排除项):契约一致性以三处实现现状互相对照为准。
- chunk_total `null`↔`"0"`↔`None` 三段映射是文档化约定(`apps/miniprogram/utils/audio.js:156 @ 5927f36` 注释 + `apps/worker/src/soniscope_worker/poller.py:118 @ 5927f36` ManifestDraft docstring),不得机械判 diverge。

## 组① OSS 数据面

> D-01 组①:fragment_id、object key、全部 `x-oss-meta-*` 元数据字段。key 族六行由 02-01 Task 1 落格;元数据九行由 02-01 Task 2 落格。RESEARCH 勘察行号为起点,以下全部行号已经 `git show 5927f36:<path>` 逐一复核,以复核后实际行号为准。

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 1. fragment_id 格式正则 | agree `apps/fc/shared/fc_shared/sts.py:30-33 @ 5927f36`(`_FRAGMENT_ID_RE`,含命名捕获组) | agree `apps/worker/src/soniscope_worker/oss_admin.py:24-27 @ 5927f36`(`_FRAGMENT_ID_RE`,与 FC 逐字符相同) | agree `apps/miniprogram/utils/audio.js:95-96 @ 5927f36`(`FRAGMENT_ID_RE`,无命名捕获组但匹配语义等价) | — |
| 2. fragment_id 日期合法性校验 | agree `apps/fc/shared/fc_shared/sts.py:54-58 @ 5927f36`(正则命中后 `datetime()` 构造校验,非法抛 400 INVALID_REQUEST) | agree `apps/worker/src/soniscope_worker/oss_admin.py:45-49 @ 5927f36`(同样 `datetime.datetime()` 构造校验,非法抛 `OssAdminError`) | absent `apps/miniprogram/utils/audio.js:95-96 @ 5927f36`(正则仅 `\d{4}\d{2}\d{2}` 形状校验,匹配路径上无任何日期合法性检查;如 `20260231` 可通过)(02-03 执行佐证:S-02/S-04 非法日期 `FRAGMENT_ID_RE.test → true` 双 TZ 实证,佐证不改静态判据,见往返校验结论对照点 a) | 覆盖洞 → F-CON-01 |
| 3. object key 模板 `recordings/<YYYY-MM-DD>/<id>.wav` | agree `apps/fc/shared/fc_shared/sts.py:46-59 @ 5927f36`(`object_key_for`,f-string 模板 :59) | agree `apps/worker/src/soniscope_worker/oss_admin.py:37-50 @ 5927f36`(`object_key_for`,f-string 模板 :50) | agree `apps/miniprogram/utils/audio.js:104-106 @ 5927f36`(`buildObjectKeyPreview`,字符串拼接 :105,`.wav` 来自 `OSS_OBJECT_KEY_EXT`) | — |
| 4. key 目录日期来源 | agree `apps/fc/shared/fc_shared/sts.py:54,59 @ 5927f36`(year/month/day 取自 fragment_id 正则捕获组前缀) | agree `apps/worker/src/soniscope_worker/oss_admin.py:45,50 @ 5927f36`(同 FC:取自 fragment_id 前缀) | diverge `apps/miniprogram/utils/audio.js:104-105,63-67 @ 5927f36`(`buildObjectKeyPreview(fragmentId, recordedAt)` 两个独立入参,日期取自 `objectKeyDate(recordedAt)` 本地时区,与 fragment_id 前缀无绑定)(02-03 执行佐证:S-06 同一 UTC 瞬间双 TZ 产出不同目录日期,S-07 双入参错位实产目录≠前缀 key——见往返校验结论对照点 c/d) | 潜伏 → F-CON-02 |
| 5. key → fragment_id 反推 | n/a — FC 只正向签发 object key(`object_key_for`),两个 handler 均无从 key 反推 fragment_id 的代码路径,结构上不承担反推角色 | agree `apps/worker/src/soniscope_worker/poller.py:47-61 @ 5927f36`(`fragment_id_from_key`,以 `object_key_for(fragment_id) == key` 往返校验 :57,连带保证格式、日期合法、目录日期与前缀一致) | diverge `apps/miniprogram/utils/upload_queue.js:38-44 @ 5927f36`(`fragmentIdFromObjectKey`,纯字符串切割:取最后一个 `/` 后、最后一个 `.` 前,无格式/日期/往返校验——普查发现的第四处实现)(02-03 执行佐证:S-14 `.m4a` key、S-18 日期错位 key 均照单全收返回前缀 id,Worker 同输入均返回 `None`——见往返校验结论对照点 b/c) | 潜伏 → F-CON-03 |
| 6. `.wav` 固定扩展名 | agree `apps/fc/shared/fc_shared/sts.py:59 @ 5927f36`(f-string 尾部硬编码 `.wav`) | agree `apps/worker/src/soniscope_worker/poller.py:53 @ 5927f36`(`key.endswith(".wav")` 过滤)+ `apps/worker/src/soniscope_worker/oss_admin.py:50 @ 5927f36`(f-string 尾部) | agree `apps/miniprogram/config.js:26 @ 5927f36`(`OSS_OBJECT_KEY_EXT = '.wav'` 常量,经 `apps/miniprogram/utils/audio.js:10 @ 5927f36` require,:105 拼接使用) | — |
| 7. `x-oss-meta-session-id` | n/a — FC 职责限于 STS 签发与 HeadObject 大小校验,无任何 meta 读写路径(见下方 FC 触点核实) | agree `apps/worker/src/soniscope_worker/poller.py:34 @ 5927f36`(`META_SESSION_ID` 常量)+ `poller.py:139 @ 5927f36`(`metadata_to_draft` 映射 `session_id`) | agree `apps/miniprogram/utils/audio.js:162 @ 5927f36`(`buildOssMetadata` 写入,`String(manifest.session_id \|\| '')`)(键名被测试锁定:`test/ids.test.js:128`) | — |
| 8. `x-oss-meta-chunk-seq` | n/a — 同上,FC 无 meta 读写路径 | agree `apps/worker/src/soniscope_worker/poller.py:35 @ 5927f36`(`META_CHUNK_SEQ`)+ `poller.py:140 @ 5927f36`(`_as_int` 映射 `chunk_seq`) | agree `apps/miniprogram/utils/audio.js:163 @ 5927f36`(写入 `String(manifest.chunk_seq)`)(测试锁定:`test/ids.test.js:129`) | — |
| 9. `x-oss-meta-chunk-total` | n/a — 同上,FC 无 meta 读写路径 | agree `apps/worker/src/soniscope_worker/poller.py:36 @ 5927f36`(`META_CHUNK_TOTAL`)+ `poller.py:134-136,141 @ 5927f36`(`_as_int` + `<=0 → None` 映射) | agree `apps/miniprogram/utils/audio.js:160,164 @ 5927f36`(`null → 0` 转换后写入)(测试锁定:`test/ids.test.js:130`) | — |
| 10. `x-oss-meta-recorded-at` | n/a — 同上,FC 无 meta 读写路径 | agree `apps/worker/src/soniscope_worker/poller.py:37 @ 5927f36`(`META_RECORDED_AT`)+ `poller.py:142 @ 5927f36`(字符串透传映射 `recorded_at`) | agree `apps/miniprogram/utils/audio.js:165 @ 5927f36`(写入 `String(manifest.recorded_at \|\| '')`)(测试锁定:`test/ids.test.js:131`) | — |
| 11. `x-oss-meta-duration` | n/a — 同上,FC 无 meta 读写路径 | agree `apps/worker/src/soniscope_worker/poller.py:38 @ 5927f36`(`META_DURATION`)+ `poller.py:143 @ 5927f36`(`_as_float` 映射 `duration_seconds`) | agree `apps/miniprogram/utils/audio.js:166 @ 5927f36`(写入 `String(manifest.duration_seconds)`)(测试锁定:`test/ids.test.js:132`) | — |
| 12. `x-oss-meta-original-format` | n/a — 同上,FC 无 meta 读写路径 | agree `apps/worker/src/soniscope_worker/poller.py:39 @ 5927f36`(`META_ORIGINAL_FORMAT`)+ `poller.py:144 @ 5927f36`(映射)+ `apps/worker/src/soniscope_worker/manifest.py:128-132 @ 5927f36`(meta 缺失时以 ffprobe 探测值回退) | agree `apps/miniprogram/utils/audio.js:167 @ 5927f36`(写入 `String(audio.original_format \|\| '')`)(测试锁定:`test/ids.test.js:133`) | — |
| 13. `x-oss-meta-sha256` | absent — verify-upload 职责即上传完整性校验,HeadObject 响应可携带该 meta 但实现只读 Content-Length/ETag(`apps/fc/shared/fc_shared/head.py:24-31 @ 5927f36` `ObjectHead` 仅四字段);`head.py:9-10 @ 5927f36` docstring 声明"无法校验 sha256,见 §4.2 注"——是否构成覆盖洞留 02-04 裁定 | agree `apps/worker/src/soniscope_worker/poller.py:40 @ 5927f36`(`META_SHA256`)+ `poller.py:145 @ 5927f36`(映射 `original_sha256`)+ `poller.py:272-283 @ 5927f36`(下载后 sha256 比对,不一致删 `.part` 重下) | agree `apps/miniprogram/utils/audio.js:168 @ 5927f36`(写入 `String(upload.original_sha256 \|\| '')`)(测试锁定:`test/ids.test.js:134`) | 覆盖洞 → F-CON-04 |
| 14. chunk_total 语义映射(非分片 `null`→`"0"`→`None`) | n/a — FC 无 meta 读写路径,不参与该映射链 | agree `apps/worker/src/soniscope_worker/poller.py:116-118 @ 5927f36`(`ManifestDraft` docstring 声明 §3.2 约定:OSS `"0"` → manifest `None`)+ `poller.py:134-136 @ 5927f36`(转换实现) | agree `apps/miniprogram/utils/audio.js:156 @ 5927f36`(注释声明:非分片 chunk_total 在 OSS meta 中写 0,manifest 内为 null)+ `audio.js:160 @ 5927f36`(转换实现) | —(负面清单排除:chunk_total 三段映射为文档化约定,不立 F-CON) |
| 15. recorded-at 值格式 | n/a — FC 无 meta 读写路径,不消费该值 | agree `apps/worker/src/soniscope_worker/poller.py:142 @ 5927f36`(不解析,字符串透传)+ `apps/worker/src/soniscope_worker/manifest.py:139 @ 5927f36`(原样写入 manifest `recorded_at`)——消费端对格式无断言,宽容透传 | agree `apps/miniprogram/utils/audio.js:76-85 @ 5927f36`(`toIso`:本地时区偏移 ISO 8601,如 `+08:00` 后缀;:165 写入) | — |

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

> D-01 组②:issue-credential 与 verify-upload 的请求/响应 JSON 字段、7 个错误码字符串、2 个 verify reason。本组契约仅存在于小程序↔FC 之间,**Worker 列全部 n/a**(Worker 业务流水线只消费 OSS 数据面,不调用 FC HTTP 接口——结构性理由代替行号,per D-03/D-04;Worker 侧联调工具 fc_live.py / verify_upload_live.py 中的契约常量镜像属普查命中,见普查节行 49-51,不占本组 Worker 列)。小程序侧请求组装取 utils 层 `queue_runtime.js`(D-04 列限定 utils);pages 层存在同构第二份组装(`apps/miniprogram/pages/uploads/uploads.js:340,365 @ 5927f36`),作为行下注与普查移交线索记录,不占列。全部行号已经 `git show 5927f36:<path>` 逐一复核。

### 组②-a issue-credential 请求字段(行 16-18)

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 16. 请求字段 `code` | agree `apps/fc/shared/fc_shared/auth.py:48-50 @ 5927f36`(`require_fields(("code", *extra_fields))` :48、`str(body["code"])` :49 → jscode2session 换 openid :50) | n/a — Worker 不调用小程序↔FC HTTP 接口,无微信登录态 | agree `apps/miniprogram/utils/queue_runtime.js:103 @ 5927f36`(请求体键 `code`,值来自 wxLogin `queue_runtime.js:85-90 @ 5927f36`) | — |
| 17. 请求字段 `fragment_id` | agree `apps/fc/issue_credential/handler.py:45 @ 5927f36`(extra_fields 必填)+ `handler.py:50 @ 5927f36`(`str(ctx.body["fragment_id"])` → `object_key_for`) | n/a — 同上 | agree `queue_runtime.js:103 @ 5927f36`(键 `fragment_id`;经 `apps/miniprogram/utils/uploader.js:86 @ 5927f36` deps.requestSts 透传) | — |
| 18. 请求字段 `size` | agree `handler.py:48-49 @ 5927f36`(parse_size + check_size)+ `apps/fc/shared/fc_shared/sts.py:76-88 @ 5927f36`(`parse_size`:接受 int 或纯数字字符串、显式拒 bool、≤0 抛 400 INVALID_REQUEST) | n/a — 同上 | agree `queue_runtime.js:103 @ 5927f36`(键 `size`)+ `uploader.js:63 @ 5927f36`(值 = `manifest.audio.size_bytes`,缺失回退 `0`) | —(agree;size=0 边界的 Postel 宽严注记并入 F-CON-06 证据字段) |

**行 18 边界注记(size=0):** 小程序 manifest 缺失时发 `size=0`(`uploader.js:63 @ 5927f36` 的 `|| 0` 回退),FC `parse_size` 判 `size <= 0` 抛 400 INVALID_REQUEST(`sts.py:86-87 @ 5927f36`)——生产者可产出消费者必拒的值;宽严归类留 02-04 Postel 分析(D-12)。

### 组②-b issue-credential 响应字段(行 19-25)

FC 侧 7 字段全部出自 `credential_response`(`sts.py:102-114 @ 5927f36`,docstring 自证"含 7 个字段,AC#6");小程序侧字段名清单与必备性校验统一在 `uploader.js:17-25 @ 5927f36`(`CREDENTIAL_FIELDS` 7 字段名与 FC 逐字符同名)+ `uploader.js:34-44 @ 5927f36`(200 且 7 字段全非空才判凭证有效,任一缺失判 `INCOMPLETE_CREDENTIAL` :45)。下表小程序格的"消费"指字段值的实际下游用途;**未消费的字段如实标注**。

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 19. 响应字段 `access_key_id` | agree `sts.py:107 @ 5927f36` | n/a — Worker 不消费 FC HTTP 响应 | agree `uploader.js:18 @ 5927f36`(必备)+ `apps/miniprogram/utils/oss_sign.js:63,71-72 @ 5927f36`(拼 x-oss-credential;formData :100) | — |
| 20. 响应字段 `access_key_secret` | agree `sts.py:108 @ 5927f36` | n/a — 同上 | agree `uploader.js:19 @ 5927f36` + `oss_sign.js:64,93 @ 5927f36`(仅入 V4 派生签名链,不落日志——`uploader.js:7 @ 5927f36` 注释红线) | —(DNF-04 对照点:STS 原始秘密下发系 by-design,负面清单排除,不立 F-CON) |
| 21. 响应字段 `security_token` | agree `sts.py:109 @ 5927f36` | n/a — 同上 | agree `uploader.js:20 @ 5927f36` + `oss_sign.js:65,81,102 @ 5927f36`(policy 条件 + formData) | —(DNF-04 对照点:同行 20 排除注) |
| 22. 响应字段 `expiration` | agree `sts.py:110 @ 5927f36` | n/a — 同上 | agree(键名与必备性)`uploader.js:21,35-37 @ 5927f36`(非空校验)——**值无任何下游消费**:`oss_sign.js` 不读该字段,表单 policy 过期用本地 `now + 900s` 独立推导(`oss_sign.js:16,91 @ 5927f36`);STS 过期实际由 OSS 服务端强制。消费缺席如实标注,02-04 已裁决(见判定列) | —(agree;expiration 值未消费系单侧消费选择,非语义分歧——STS 过期由 OSS 服务端强制、policy 过期本地独立推导(组③ 行 48),不立 F-CON) |
| 23. 响应字段 `bucket` | agree `sts.py:111 @ 5927f36`(值来自 FC env OSS_BUCKET,`handler.py:108 @ 5927f36`) | n/a — 同上 | agree `uploader.js:22 @ 5927f36` + `oss_sign.js:67,76 @ 5927f36`(policy bucket 条件) | — |
| 24. 响应字段 `endpoint` | agree `sts.py:112 @ 5927f36`(值来自 FC env OSS_ENDPOINT,`handler.py:108 @ 5927f36`) | n/a — 同上 | agree(键名与必备性)`uploader.js:23,35-37 @ 5927f36`(非空校验)——**值无下游消费**:上传 URL 用 `config.OSS_UPLOAD_URL`(`queue_runtime.js:154 @ 5927f36` → `oss_sign.js:60,110 @ 5927f36`),credential.endpoint 被忽略。如实标注,02-04 已裁决(见判定列) | —(agree;endpoint 值未消费同行 22 裁决——上传 URL 以 `config.OSS_UPLOAD_URL` 为单一真值源,不立 F-CON) |
| 25. 响应字段 `object_key` | agree `sts.py:113 @ 5927f36`(值由 `handler.py:50 @ 5927f36` 服务端从 fragment_id 解析,模板见组① 行 3) | n/a — 同上 | agree `uploader.js:24 @ 5927f36` + `oss_sign.js:66,77,97 @ 5927f36`(policy `eq $key` 精确条件 + formData key)+ `uploader.js:102,112 @ 5927f36`(AC#4 注释与日志) | — |

**行 25 AC#4 语义注记:** 小程序 object_key **用 FC 返回值,不由前端拼接覆盖**(`uploader.js:102 @ 5927f36` 注释、`oss_sign.js:50-52 @ 5927f36` docstring 双重声明)——这是往返链关键环:FC `object_key_for` 签发 → 小程序原样使用 → Worker `fragment_id_from_key` 反推。02-03 将对此链做执行佐证。小程序 `buildObjectKeyPreview`(组① 行 3/4)仅用于本地预览/去重键,不参与上传 key。

### 组②-c verify-upload 请求字段(行 26-28)

字段全集依据(RESEARCH Open Question 2 裁决):`apps/fc/verify_upload/handler.py:46-48 @ 5927f36`(`authorize_request(..., extra_fields=("fragment_id", "expected_size"))`)+ `handler.py:51-52 @ 5927f36`——请求字段全集 = `code` + `fragment_id` + `expected_size`,共 3 字段,无其他读取。

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 26. 请求字段 `code`(verify) | agree `auth.py:48-50 @ 5927f36`(与 issue-credential 同一共享鉴权路径;入口 `verify_upload/handler.py:46-48 @ 5927f36`) | n/a — Worker 不调用 FC HTTP 接口 | agree `queue_runtime.js:123 @ 5927f36`(键 `code`)+ `apps/miniprogram/utils/verify.js:68,71 @ 5927f36`(code 一次性,每轮重试重新 login) | — |
| 27. 请求字段 `fragment_id`(verify) | agree `verify_upload/handler.py:47 @ 5927f36`(必填)+ `handler.py:52 @ 5927f36`(`object_key_for`) | n/a — 同上 | agree `queue_runtime.js:123 @ 5927f36` + `verify.js:87 @ 5927f36`(透传) | — |
| 28. 请求字段 `expected_size` | agree `verify_upload/handler.py:51 @ 5927f36`(`parse_size(ctx.body.get("expected_size"))`,复用 `sts.py:76-88 @ 5927f36` 同一解析) | n/a — 同上 | agree `queue_runtime.js:123 @ 5927f36`(键 `expected_size`)+ `verify.js:59-60 @ 5927f36`(值 = `manifest.audio.size_bytes` 回退 `0`——同行 18 的 size=0 边界) | — |

### 组②-d verify-upload 响应字段(行 29-34)

字段全集依据(Open Question 2):FC 侧全部出自 `verify_upload_result`(`apps/fc/shared/fc_shared/head.py:34-55 @ 5927f36`,三态映射:不存在 / 大小不符 / 一致)——响应字段全集 = `verified` + `reason` + `actual_size` + `etag` + `size` + `last_modified`,共 6 字段。小程序侧分类在 `classifyVerifyResponse`(`verify.js:28-51 @ 5927f36`)。

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 29. 响应字段 `verified` | agree `head.py:43,45,51 @ 5927f36`(false 两分支 + true 分支均携带) | n/a — Worker 不消费 FC HTTP 响应 | agree `verify.js:32 @ 5927f36`(`data.verified === true` 严格布尔判定;非 true 一律走 unverified 分支 :40-44) | — |
| 30. 响应字段 `reason` | agree `head.py:43,47 @ 5927f36`(OBJECT_NOT_FOUND / SIZE_MISMATCH 两分支) | n/a — 同上 | agree `verify.js:42 @ 5927f36`(`String(data.reason)`,缺失回退 `'UNKNOWN'`)+ `verify.js:103 @ 5927f36`(随状态补丁落存;pages 展示端 `uploads.wxml:23 @ 5927f36` 渲染,不占列括注) | — |
| 31. 响应字段 `actual_size` | agree `head.py:48 @ 5927f36`(仅 SIZE_MISMATCH 分支携带) | n/a — 同上 | agree(提取)`verify.js:43 @ 5927f36`(actualSize)——**提取后未落存**:`verifyFragment` 状态补丁仅含 reason(`verify.js:101-105 @ 5927f36`)。如实标注 | — |
| 32. 响应字段 `etag` | agree `head.py:52 @ 5927f36` | n/a — 同上 | agree(提取)`verify.js:35 @ 5927f36`——verified 分支仅落存 verifiedAt(`verify.js:94-99 @ 5927f36`),etag 提取后丢弃。如实标注 | — |
| 33. 响应字段 `size` | agree `head.py:53 @ 5927f36`(Content-Length 回显) | n/a — 同上 | agree(提取)`verify.js:36 @ 5927f36`——同行 32,未落存 | — |
| 34. 响应字段 `last_modified` | agree `head.py:54 @ 5927f36` | n/a — 同上 | agree(提取)`verify.js:37 @ 5927f36`(lastModified)——同行 32,未落存 | — |

### 组②-e 错误码字符串(行 35-41)

**小程序侧裁决(RESEARCH Open Question 1,以 classifyFcResponse 全文为证):** 对照 `classifyFcResponse` 全文(`uploader.js:32-50 @ 5927f36`)与 `classifyVerifyResponse` 全文(`verify.js:28-51 @ 5927f36`)——**小程序不按错误码字符串分支**:uploader 按 `statusCode === 200` 与否二分(`uploader.js:34 @ 5927f36`);verify 按 200 / ≥500 / 其余 4xx 三段(`verify.js:31,46,49 @ 5927f36`);`data.error` 仅作通用透传(`uploader.js:48 @ 5927f36`、`verify.js:49 @ 5927f36` 的 `String(data.error)`)记录与展示,行为不依赖具体码值。7 个错误码字面量在小程序**实现代码**中零出现(`uploader.js:47 @ 5927f36` 提及 3 码但为注释非代码)。故 7 行小程序格统一判 **absent**(字面量未实现;通用透传使每码行为等同——是覆盖洞还是良性设计留 02-04 归类)。

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 35. 错误码 `INVALID_CODE`(401) | agree `apps/fc/shared/fc_shared/errors.py:13 @ 5927f36`(定义)+ `wechat.py:45,47,51 @ 5927f36`(raise) | n/a — Worker 不参与 HTTP 错误码契约(联调工具镜像见普查行 50) | absent — 字面量零出现,经 `uploader.js:48 @ 5927f36` 通用透传(测试锁定:`test/uploader.test.js` 含码字符串断言) | 良性 → F-CON-05 |
| 36. 错误码 `OPENID_NOT_ALLOWED`(403) | agree `errors.py:14 @ 5927f36` + `auth.py:36 @ 5927f36`(raise) | n/a — 同上 | absent — 同行 35 裁决 | 良性 → F-CON-05 |
| 37. 错误码 `INVALID_REQUEST`(400) | agree `errors.py:15 @ 5927f36` + `http.py:63,67,69,78 @ 5927f36` + `sts.py:53,58,79,85,87 @ 5927f36`(raise) | n/a — 同上 | absent — 同行 35 裁决 | 良性 → F-CON-05 |
| 38. 错误码 `SIZE_EXCEEDED`(400) | agree `errors.py:16 @ 5927f36` + `sts.py:93-99 @ 5927f36`(raise,附 limit_bytes / actual_bytes) | n/a — 同上 | absent — 同行 35 裁决(`uploader.js:47 @ 5927f36` 注释提及但非代码分支) | 良性 → F-CON-05 |
| 39. 错误码 `SERVER_MISCONFIGURED`(500) | agree `errors.py:17 @ 5927f36` + `issue_credential/handler.py:61 @ 5927f36`、`verify_upload/handler.py:63 @ 5927f36`(附 missing 变量名列表) | n/a — 同上 | absent — 同行 35 裁决 | 良性 → F-CON-05 |
| 40. 错误码 `STS_ISSUE_FAILED`(500) | agree `errors.py:18 @ 5927f36` + `issue_credential/handler.py:92 @ 5927f36` | n/a — 同上 | absent — 同行 35 裁决 | 良性 → F-CON-05 |
| 41. 错误码 `HEAD_OBJECT_FAILED`(500) | agree `errors.py:19 @ 5927f36` + `verify_upload/handler.py:93 @ 5927f36` | n/a — 同上 | absent — 同行 35 裁决 | 良性 → F-CON-05 |

**行 35-41 移交线索(Phase 4 DOC 维度):** CLAUDE.md("Naming Patterns"节)声明错误码字符串 "shared verbatim between Python FC handlers and miniprogram JS (`uploader.js` branches on the same strings)" 与实态不符——uploader.js 实为 statusCode 段分支 + `error` 字段通用透传,错误码字面量不在小程序实现代码中(上表逐行为证)。本矩阵不立 DOC 判断,仅记移交。

**行 35-41 错误响应包络注记:** FC 错误响应体固定含 `error` 字段(`errors.py:38 @ 5927f36` payload 组装),可选 `message` 与 extra 字段(如行 38 的 limit_bytes、行 39 的 missing);小程序仅读 `error` 一个键,extra 字段全部无消费——静态层面无键名冲突。

### 组②-f verify reason(行 42-43)

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 42. reason `OBJECT_NOT_FOUND` | agree `errors.py:23 @ 5927f36`(定义)+ `head.py:43 @ 5927f36`(响应组装) | n/a — Worker 不消费 verify 响应(联调工具镜像见普查行 51) | agree `verify.js:20 @ 5927f36`(`REASON_OBJECT_NOT_FOUND` 字面量逐字符一致)——分支仍为通用透传(`verify.js:42 @ 5927f36`),常量当前仅模块导出(`verify.js:134 @ 5927f36`)供测试/故障注入消费(测试锁定:`test/verify.test.js`;故障注入 mock 字面量 `queue_runtime.js:116 @ 5927f36`) | — |
| 43. reason `SIZE_MISMATCH` | agree `errors.py:24 @ 5927f36` + `head.py:47 @ 5927f36` | n/a — 同上 | agree `verify.js:21 @ 5927f36`(`REASON_SIZE_MISMATCH`)——同行 42(导出 `verify.js:135 @ 5927f36`) | — |

## 组③ 两侧镜像常量

> D-01 组③:跨语言镜像约定值(重试节奏、重试上限、大小上限、分片阈值、STS 时长)。本组是"两侧镜像"对照,列式仍用三列;不参与的列标 n/a + 结构性理由。全部行号已经 `git show 5927f36:<path>` 复核;grep 核实命令写入行下注(为普查节存档预铺)。

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 44. 重试节奏 5s→15s→45s | n/a — FC 是被重试的服务端,自身无重试表(两 handler 均单次调用云 API,失败即收敛 500) | agree `apps/worker/src/soniscope_worker/nls.py:45 @ 5927f36`(`RETRY_DELAYS_SECONDS = (5.0, 15.0, 45.0)`,秒,NLS 提交/查询重试)(测试锁定:`apps/worker/tests/test_nls.py:401,449-450`) | agree `apps/miniprogram/utils/uploader.js:28 @ 5927f36`(`RETRY_DELAYS_MS = [5000, 15000, 45000]`,毫秒,OSS 直传重试)+ `apps/miniprogram/utils/verify.js:16 @ 5927f36`(`VERIFY_RETRY_DELAYS_MS = [5000, 15000, 45000]`,毫秒,verify 重试——**JS 侧两份独立常量,两处行号均列**)(测试锁定:`test/uploader.test.js:55`、`test/verify.test.js:54`) | — |
| 45. 最多 3 次重试 | n/a — 同行 44 | agree `nls.py:46 @ 5927f36`(`MAX_RETRIES = 3`,**独立字面量**,与延时表长度无结构绑定) | agree `uploader.js:29 @ 5927f36`(`MAX_UPLOAD_RETRIES = RETRY_DELAYS_MS.length`,派生)+ `verify.js:17 @ 5927f36`(`MAX_VERIFY_RETRIES = VERIFY_RETRY_DELAYS_MS.length`,派生)(测试锁定:`test/uploader.test.js:56`、`test/verify.test.js:55`) | — |
| 46. 上传大小上限 50 MB | agree `apps/fc/shared/fc_shared/env.py:41 @ 5927f36`(`DEFAULT_MAX_UPLOAD_BYTES = 52428800`,可被 env `MAX_UPLOAD_BYTES` 覆盖;执行点 `sts.py:91-99 @ 5927f36` check_size)(测试锁定:`apps/fc/tests/test_issue_credential.py:142,151`) | n/a — Worker 只下载已入桶对象,不参与上传大小约束 | absent — 无镜像常量、无上传前预检:上限语义仅经 SIZE_EXCEEDED 错误码事后感知(组② 行 38)。覆盖洞候选,02-04 已裁决 | 覆盖洞 → F-CON-06 |
| 47. 分片阈值 600 s | n/a — FC 对分片阈值零感知(grep 裁决见行下注);分片对 FC 只显现为独立 fragment_id 的多次签发 | n/a — Worker 对分片阈值零感知(grep 裁决见行下注);分片对 Worker 只显现为 chunk-seq / chunk-total 元数据(组① 行 8/9) | agree `apps/miniprogram/config.js:22-23 @ 5927f36`(`CHUNK_MAX_DURATION_SECONDS = 600`,注释自证 tech-spec §3.1"本期作为前端常量管理") | — |
| 48. STS 时长 ≤900 s | agree `apps/fc/shared/fc_shared/sts.py:24-25 @ 5927f36`(`STS_MAX_DURATION_SECONDS = 900`;使用点 `issue_credential/handler.py:79 @ 5927f36`) | n/a — Worker 不使用 STS(用 config.yaml 长期 AK 走 OSS 只读) | agree `apps/miniprogram/utils/oss_sign.js:16 @ 5927f36`(`DEFAULT_POLICY_EXPIRE_SECONDS = 900`,表单 policy 过期镜像常量,注释自证"与 STS 有效期同量级即可,签名本身受 STS 过期约束";使用点 `oss_sign.js:61,91 @ 5927f36`)——注意小程序对响应字段 `expiration` 本体无消费(组② 行 22),900 镜像为独立本地常量 | — |

**行 46 grep 裁决依据(absent):**

```bash
git grep -nE '52428800|MAX_UPLOAD' 5927f36 -- apps/miniprogram/   # 小程序侧大小上限镜像核实
# 命中 5 行,全部为重试次数常量 MAX_UPLOAD_RETRIES(uploader.js:29,116,139,160)及其测试断言
# (test/uploader.test.js:56)——与大小上限语义无关;无 52428800、无任何大小预检常量 → 判 absent
```

**行 47 grep 裁决依据(FC/Worker 双 n/a):**

```bash
git grep -n '600' 5927f36 -- apps/fc/ apps/worker/src/   # FC/Worker 侧 600s 分片阈值感知核实
# 命中 30 行,逐条人工筛选全部为无关值:chmod 600 权限(config.py:148-150、cli.py:40-51、
# verify_prep.py:249-257)、3600 秒签名 URL 时长(nls.py:49,54,108)、16000 采样率
# (audio.py:82、nls.py:502)、500<=status<600 段判(verify_prep.py:301)、样本 fragment_id
# 内数字(e2e_scenarios.py:67、pipeline.py:558)——零分片阈值感知 → FC/Worker 双 n/a
```

**行 44/45 语义注记:** 三份重试表(nls.py / uploader.js / verify.js)作用于**不同操作**(NLS 转写调用 / OSS 直传 / FC verify 调用),镜像的是 AGENTS 错误处理节奏约定(三处注释均自证引用该约定);单位不同(秒 vs 毫秒)属字面差异语义一致(Pitfall 5)。JS 两份独立常量 + Worker 独立字面量 MAX_RETRIES 的重复实现债务线索移交 Phase 3(见普查节)。

## 重复逻辑普查

> CONTRACT-03,D-13 双保险:① 候选清单 9 项逐项核实 + ② `git grep` 基线系统扫描存档。命中处理规则(D-14 / Pitfall 7):实现代码命中且承载契约 → 矩阵新行(行 49-51);测试目录(`apps/miniprogram/test/`、`apps/worker/tests/`、`apps/fc/tests/`)命中 → 不占列,记为对应矩阵格"测试锁定"辅助证据;"重复实现本身是否构成技术债"不在 CON 维度判断,逐点移交 Phase 3 CODE 维度(③ 移交记录)。

### ① 候选清单逐项核实(9 项,D-13 + RESEARCH 定位表)

| # | 候选 | 核实证据 @ 5927f36 | 结论(新行 / 指针 / 已检查无新发现) |
|---|------|--------------------|--------------------------------------|
| 1 | sha256 | 小程序纯 JS SHA-256:`apps/miniprogram/utils/sha256.js:1,138-143 @ 5927f36`(手写算法,调用端 `pages/index/index.js:30,640 @ 5927f36`);Worker stdlib:`apps/worker/src/soniscope_worker/fixtures.py:21,118 @ 5927f36`(hashlib)+ `poller.py:26,251 @ 5927f36`(下载后比对流程) | **指针** — 契约值语义(`x-oss-meta-sha256` hex digest)已由组① 行 13 对照覆盖;算法级跨语言重复实现(手写 SHA-256 vs stdlib hashlib)确认存在 → 移交 D14-1(挂 **HYP-03**:主线程纯 JS 哈希性能疑点) |
| 2 | 日期格式 `YYYY-MM-DD` | `audio.js:63-67 @ 5927f36`(objectKeyDate 本地时区)vs `sts.py:54,59` / `oss_admin.py:45,50 @ 5927f36`(fragment_id 前缀拼接)已入组① 行 3/4;`poller.py:64-66 @ 5927f36` `date_of` 经核实为 `object_key_for(fragment_id).split("/")[1]` **复用单一来源派生**,非独立实现;`ops.py:64-68 @ 5927f36` 为运维 CLI 入参校验(fromisoformat),不承载三方契约 | **已检查,无新发现**(指针:组① 行 3/4) |
| 3 | ULID / fragment_id 生成 | `apps/miniprogram/utils/ulid.js:3-4 @ 5927f36`(注释自证 Crockford base32 ⊂ 正则 `[0-9A-Za-z]{26}`);FC/Worker 生产代码只解析不生成(组① 行 1/5) | **已检查,无新发现** — 生产链路生成端唯一;正则宽于 Crockford 字符集的宽严差异属 02-03 既定样本类别(组① 行 1 已覆盖格式对照)。联调工具存在合成 fragment_id 生成(见扫描 4 注记,归 D14-3) |
| 4 | 错误码字符串 | 已入组② 行 35-41;普查新命中:`fc_live.py:42-44 @ 5927f36`(ERR_* 三码第二份字面定义)、`verify_upload_live.py:34-35 @ 5927f36`(REASON_* 第三份字面定义);`e2e_scenarios.py:32-33 @ 5927f36` 从 fc_live 导入(消费端非独立副本) | **新行** — 行 50(错误码镜像)、行 51(reason 镜像);移交 D14-3 |
| 5 | 重试表 | 已入组③ 行 44-45(nls.py / uploader.js / verify.js 三份常量,JS 两份独立) | **指针**(组③ 行 44-45);移交 D14-2 |
| 6 | 大小上限 | 已入组③ 行 46;普查新命中:`fc_live.py:57-59 @ 5927f36`(SIZE_OK_BYTES=10MB / SIZE_EXCEEDED_BYTES=60MB,注释自证隐式编码"50MB 上限"假设) | **指针**(组③ 行 46)— fc_live 命中为隐式假设非字段级契约,记为行 46 辅助线索;移交 D14-3 |
| 7 | HMAC / OSS V4 签名 | `apps/miniprogram/utils/hmac.js` + `utils/oss_sign.js @ 5927f36` 为小程序侧唯一手写实现;Worker/FC 侧签名由 OSS SDK 内置(`poller.py` RealOssSource / `head.py:102-136 @ 5927f36` RealObjectHeader 均走 alibabacloud-oss-v2) | **已检查,无新发现** — 签名协议的对手方是 OSS 服务端而非三方互相,无跨语言重复实现(n/a 素材) |
| 8 | 配置解析 | 三种机制解析同族值:Worker `config.py`(pydantic + config.yaml)vs 小程序 `config.js:10-15,22-26 @ 5927f36`(硬编码常量模块)vs FC `env.py @ 5927f36`(环境变量)。同族值(region/bucket/endpoint/URL)在 Worker/FC 侧存于运行时配置(yaml/env),不在基线代码内 | **已检查,无新发现**(静态层面无可逐字段对照的代码内值重复;唯一代码内值为 config.js 硬编码侧)— "三机制并存 + 单侧硬编码"配置管理线索移交 D14-5 |
| 9 | 第四处 key 反推 | `upload_queue.js:38-44 @ 5927f36` `fragmentIdFromObjectKey` — 02-01 已落组① 行 5(小程序格 diverge) | **指针**(组① 行 5);移交 D14-6。另核实:小程序 FC 请求组装在 utils(`queue_runtime.js:94-108,110-128 @ 5927f36`)与 pages(`uploads.js:340,365 @ 5927f36`)存在两份同构实现 → 移交 D14-4 |

### 普查命中矩阵新行(行 49-51,D-14)

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 49. issue-credential 响应 7 字段名清单(联调工具第三份字面清单) | agree `sts.py:106-114 @ 5927f36`(credential_response 组装即字段名权威来源) | agree `apps/worker/src/soniscope_worker/fc_live.py:47-55 @ 5927f36`(`CREDENTIAL_FIELDS` 元组,7 字段名逐字符一致;`fc_live.py:41 @ 5927f36` 注释自证"与 fc_shared 保持一致,避免跨包导入"——文档化的故意重复)——注意:此为 Worker 侧**联调工具**,非业务流水线;组② 行 19-25 Worker 列 n/a 裁决不变 | agree `uploader.js:17-25 @ 5927f36`(`CREDENTIAL_FIELDS`,`uploader.js:16 @ 5927f36` 注释自证"与 fc_live.CREDENTIAL_FIELDS 一致") | — |
| 50. FC 错误码字符串镜像(联调工具第二份字面定义,3/7 码) | agree `errors.py:13,14,16 @ 5927f36`(INVALID_CODE / OPENID_NOT_ALLOWED / SIZE_EXCEEDED 定义端) | agree `fc_live.py:42-44 @ 5927f36`(ERR_INVALID_CODE / ERR_OPENID_NOT_ALLOWED / ERR_SIZE_EXCEEDED,值逐字符一致;消费端 `e2e_scenarios.py:32-33,210,228 @ 5927f36` 断言) | n/a — 小程序实现代码零字面量,裁决见组② 行 35-41(本行对照对象是 Worker 侧工具镜像) | — |
| 51. verify reason 字符串镜像(第三份字面定义) | agree `errors.py:23-24 @ 5927f36`(定义端) | agree `verify_upload_live.py:34-35 @ 5927f36`(REASON_OBJECT_NOT_FOUND / REASON_SIZE_MISMATCH,值逐字符一致,断言端 :158,181) | agree `verify.js:20-21 @ 5927f36`(同组② 行 42-43,常量命名与 Worker 工具侧同构 REASON_*) | — |

### ② 系统扫描存档(5 条命令,输出摘要 + 命中计数)

扫描范围 `apps/` 全树;计数按"实现命中"(生产 + 工具代码)与"测试命中"(三个测试目录)分栏,per Pitfall 7。

```bash
# 扫描 1:key / meta / fragment 族
git grep -nE 'recordings/|x-oss-meta|fragment_?[iI]d|object_?[kK]ey' 5927f36 -- apps/
# → 总命中 954(实现 618 / 测试 336)。实现命中 39 个文件逐一核查:FC 6 文件与小程序
#   utils 11 文件均已被组①/组② 行覆盖或为编排/展示层消费端(pages/*.js/wxml);Worker 18
#   文件中业务流水线(poller/oss_admin/manifest/pipeline/recovery/retranscribe/locks 等)已被
#   组① 覆盖,联调工具族(fc_live/verify_upload_live/e2e/e2e_scenarios/sts_escape/ops/
#   verify_prep/cli)命中收敛为行 49-51 与 D14-3。无其他新发现。

# 扫描 2:sha256 族
git grep -nE 'sha256|SHA-?256' 5927f36 -- apps/
# → 总命中 295(实现 172 / 测试 123)。实现命中即候选 1 的两侧实现 + 组① 行 13 触点;
#   排除项:fc_deploy.py:181,442(部署包指纹,非音频契约);hmac.js/oss_sign.js(签名族,
#   候选 7)。无新发现。

# 扫描 3:重试与大小数值族
git grep -nE '\b(5000|15000|45000)\b|\b(5\.0|15\.0|45\.0)\b|52428800' 5927f36 -- apps/
# → 总命中 30(实现 8 / 测试 22)。实现命中逐条:env.py:41、uploader.js:28、verify.js:16、
#   nls.py:45(均已入组③ 行 44-46);无关值 4 条人工排除:nls.py:53(NLS 轮询间隔)、
#   poller.py:43(扫描容差)、retranscribe.py:419(文档样例)、verify_prep.py:88(轮询间隔)。
#   测试命中含 uploader.test.js:55,112 / verify.test.js:54 等(组③ 行 44-45 测试锁定)与
#   test_issue_credential.py:142,151(行 46 测试锁定)。无新发现。

# 扫描 4:日期格式函数族
git grep -nE 'YYYY-MM-DD|toISOString|isoformat|strftime|getTimezoneOffset' 5927f36 -- apps/
# → 总命中 34(实现 33 / 测试 1)。契约承载命中已由组① 行 3/4/15 与候选 2 覆盖
#   (audio.js:63,77,103、sts.py:49、oss_admin.py:38、poller.py:65);其余人工排除:CLI 帮助
#   文本与运维入参(cli.py、ops.py、e2e.py、retranscribe.py)、部署时间戳(fc_deploy.py:463)、
#   transcript/expiration 时间戳(pipeline.py:88、nls.py:251、verify_prep.py:656,718)、
#   oss_sign.js:37(policy 过期 UTC,组③ 行 48)。注记:联调工具合成 fragment_id 时间前缀
#   (fc_live.py:256、verify_upload_live.py:201,strftime("%Y%m%dT%H%M%S") 与契约前缀格式
#   一致)→ 工具侧生成仅影响联调,不拆新行,归 D14-3 集群。

# 扫描 5:错误码字符串族
git grep -nE 'INVALID_CODE|OPENID_NOT_ALLOWED|SIZE_EXCEEDED|INVALID_REQUEST|OBJECT_NOT_FOUND|SIZE_MISMATCH|SERVER_MISCONFIGURED|STS_ISSUE_FAILED|HEAD_OBJECT_FAILED' 5927f36 -- apps/
# → 总命中 234(实现 135 / 测试 99)。实现命中文件分布:fc_shared 族 + 两 handler(定义与
#   raise,组② 行 35-43)、verify.js:6 / uploader.js:1 / queue_runtime.js:1 / uploads.js:1
#   (组② 已裁决:注释/mock,非分支字面量)、联调工具 fc_live.py:24 / verify_upload_live.py:20 /
#   e2e_scenarios.py:9 / cli.py:3 → 新发现即行 50/51。
```

### ③ 债务移交记录(D-14 → Phase 3 CODE 维度)

每点仅记线索,债务与否由 Phase 3 判定:

- **D14-1(移交 Phase 3):** sha256 跨语言双实现——小程序手写纯 JS 算法(`sha256.js`)vs Worker stdlib hashlib;关联 **HYP-03**(主线程哈希性能)。
- **D14-2(移交 Phase 3):** 重试节奏三份常量(`nls.py:45` / `uploader.js:28` / `verify.js:16`)+ Worker `MAX_RETRIES = 3` 独立字面量与延时表长度无结构绑定(JS 侧为 `.length` 派生)——同一约定四处落点。
- **D14-3(移交 Phase 3):** 联调工具契约镜像集群——`fc_live.py`(7 字段清单 :47-55、3 错误码 :42-44、50MB 隐式假设 :57-59、合成 fragment_id :256)、`verify_upload_live.py`(2 reason :34-35、合成 fragment_id :201)、`e2e_scenarios.py`(导入消费):契约变更需同步更新工具侧,当前靠注释约定("与 fc_shared 保持一致")无测试兜底。
- **D14-4(移交 Phase 3):** 小程序 FC 请求组装两份同构实现——utils `queue_runtime.js:94-128` 与 pages `uploads.js:340,365`。
- **D14-5(移交 Phase 3):** 配置三机制并存(pydantic yaml / env 解析 / 硬编码常量模块),小程序侧 `config.js:10-15` 为唯一代码内硬编码真实云值。
- **D14-6(移交 Phase 3):** key → fragment_id 反推第四处实现 `upload_queue.js:38-44`(`fragmentIdFromObjectKey`,无校验字符串切割;语义对照已在组① 行 5,小程序格 diverge)。
- **(移交 Phase 4 DOC,指针):** CLAUDE.md 错误码分支声明与实态不符——已在组② 行 35-41 行下注记录。

### ④ 完成判定(机械对账,CONTRACT-03 可复核收口)

- 扫描命令条数:**5**(上节 fenced bash 逐条存档,均可重放:`git grep ... 5927f36 -- apps/`)
- 总命中数:954 + 295 + 30 + 34 + 234 = **1547**(实现 618 + 172 + 8 + 33 + 135 = **966**;测试 336 + 123 + 22 + 1 + 99 = **581**;逐条分栏见各命令注释,复算:966 + 581 = 1547 ✓)
- 进矩阵新行数:**3**(行 49-51)
- 候选清单 9 项三态分布:新行 **1** 项(候选 4)+ 指针 **4** 项(候选 1/5/6/9)+ 已检查无新发现 **4** 项(候选 2/3/7/8);1 + 4 + 4 = 9 ✓
- 测试辅助证据("测试锁定"格内括注)数:本计划(02-02)新增 **6** 处(组② 行 35、行 42 各 1,组③ 行 44 两处、行 45、行 46 各 1);累计格内括注 = 02-01 的 7(组① 行 7-13)+ 02-02 的 6 = **13**;复算命令 `grep -o '测试锁定' .planning/audit/CONTRACT-MATRIX.md | wc -l` → **18**(= 13 格内 + 5 处非格内引用:普查规则句/扫描 3 存档注记×2/本行×2)
- 矩阵行总数:组① 15 + 组② 28 + 组③ 5 + 普查 3 = **51 行**(主体三组 48 行,D-02 预估 30-50 区间内;普查新行为 D-14 增量)

## 往返校验结论

> CONTRACT-02 执行佐证(02-03)。**执行结果只作佐证,判据以静态行号对照为准(D-05)**;全部执行跑在基线导出树上(`git archive 5927f36` → 会话 scratchpad,见附录复跑说明),零云 IO(D-08:"FC 签发的 key"即本地执行 `fc_shared/sts.py::object_key_for`)。

### python 侧小结(FC 签发 → Worker 解析)

harness 首部来源断言通过:`soniscope_worker.poller.__file__` 与 `fc_shared.sts.__file__` 均以 scratchpad 导出树前缀开头(Pitfall 1 兜底);冒烟 `import fc_shared` / `import soniscope_worker.poller` 成功,无网络触发(RESEARCH A2 证实:云 SDK 全 lazy import)。

逐样本记录(完整三元组见附录样本表『实测』列):

| 样本域 | FC 签发(`fc_sts.object_key_for`) | Worker 解析(`poller.fragment_id_from_key(FC key)`) |
|--------|------------------------------------|------------------------------------------------------|
| S-01/S-03/S-05/S-13/S-15(格式+日期均合法) | 签发 key,与 Worker `oss_admin.object_key_for` 产出**逐字符相等** | **可解析**,往返等式 `fragment_id_from_key(key) == fragment_id` 全部成立 |
| S-02/S-04(正则可过但日期非法) | **被拒**:`FcHttpError: 400 INVALID_REQUEST: invalid fragment_id date` | 不适用(FC 未签发 key);Worker `oss_admin.object_key_for` 同步被拒:`OssAdminError: 非法 fragment_id 日期` |
| S-08/S-09/S-10/S-11/S-12/S-16/S-17(格式非法) | **被拒**:`FcHttpError: 400 INVALID_REQUEST: invalid fragment_id format` | 不适用;Worker 侧同步被拒:`OssAdminError: 非法 fragment_id 格式` |
| S-14(非 `.wav` key,直接喂 Worker) | n/a(FC 只正向签发,组① 行 5) | **被拒**:`fragment_id_from_key` 返回 `None`(`poller.py:53 @ 5927f36` endswith 检查) |
| S-18(目录日期≠前缀日期的 key) | n/a(同上) | **被拒**:返回 `None`(`poller.py:57 @ 5927f36` 往返等式 `object_key_for(id) == key` 不成立) |

**python 侧结论:** FC `object_key_for` 与 Worker `oss_admin.object_key_for` 在全部 15 个 python 侧样本上行为逐样本一致(同收同拒,拒绝类别一致:格式/日期两类);FC 签发出的每一个 key 都能被 Worker `fragment_id_from_key` 解析且往返等式成立——**FC↔Worker 主链在样本域内无漂移**(与组① 行 1-6 静态判定一致,佐证不改判据)。

### JS 侧小结(小程序声部,双 TZ)

全部 JS 样本以 `TZ=Asia/Shanghai node <harness>` 与 `TZ=America/New_York node <harness>` 双跑;非时区敏感样本双 TZ 结果逐条相同。`FRAGMENT_ID_RE.test` 与 FC/Worker 正则在**格式维度**逐样本同判(S-01/03/05/13/15 通过,S-08~S-12/S-16/S-17 拒),分叉仅出现在日期合法性与 key 反推两处(见对照点)。`buildObjectKeyPreview` 在同 recordedAt 下产出与 FC 签发 key 逐字符相等(S-01 正向对照,双 TZ 同果)。

### 高价值对照点实测记录(a)-(d)

- **(a) 非法日期:FC/Worker datetime 拒 vs JS 正则放行(组① 行 2 absent 的行为化)** — S-02(13 月 32 日)与 S-04(非闰年 2/29):FC `FcHttpError: 400 INVALID_REQUEST: invalid fragment_id date`、Worker `OssAdminError: 非法 fragment_id 日期`;JS `FRAGMENT_ID_RE.test → true`(TZ=Asia/Shanghai 与 TZ=America/New_York 双跑均 true)。**生产者可产出消费者必拒的 fragment_id**(若前端日期构造异常,FC 侧 400 是唯一拦截点)。
- **(b) 非 .wav key:Worker endswith 拒 vs 第四处照单全收(组① 行 5 diverge 的行为化)** — S-14(`….m4a`):Worker `fragment_id_from_key → None`(`poller.py:53 @ 5927f36`);JS `fragmentIdFromObjectKey → '20260704T101500_dev01a_01HZX3K8MN5PQR9TFB7AYWVCDE'`(双 TZ 同,照单全收)。
- **(c) 目录日期≠前缀日期 key:Worker 往返等式拒 vs 第四处放行** — S-18(目录 `2026-07-05`/前缀 `20260704`):Worker → `None`(`poller.py:57 @ 5927f36` 往返等式不成立);JS `fragmentIdFromObjectKey` → 返回前缀 id(双 TZ 同)。且 S-07 实证**小程序自身就能产出这种错位 key**:`buildFragmentId` 于 23:59:59 构造、`buildObjectKeyPreview` 传入次日 00:00:01 的 recordedAt,产出 `recordings/2026-07-05/20260704T235959_….wav`(`dir-date != prefix-date → true`,双 TZ 同)——组① 行 4 双独立入参 diverge 的行为级证据。此类对象上传后 Worker 轮询将**静默跳过**(`fragment_id_from_key` 返回 None 即不入处理队列)。
- **(d) 跨时区日期错位:同一 UTC 瞬间双 TZ 产出不同 fragment_id/key** — S-06(UTC 2026-07-04T16:30:00Z):TZ=Asia/Shanghai → fid `20260705T003000_…`、key `recordings/2026-07-05/…`;TZ=America/New_York → fid `20260704T123000_…`、key `recordings/2026-07-04/…`。单 TZ 进程内前缀与目录日期自洽(`prefix==dirdate → true` 双 TZ 均真);错位风险在**双入参跨时刻/跨时区混用**时显化(见 c 的 S-07)。

### 总结论(CONTRACT-02 成功判据 2 的回答)

**FC 签发的 object key 在"正则格式合法 + 日期合法"的全部样本域内均可被 Worker `fragment_id_from_key` 解析且往返等式成立**(S-01/S-03/S-05/S-13/S-15 五样本实证,含闰日、跨年、宽字符集边界);FC 与 Worker 的签发/解析双侧在 15 个 python 样本上同收同拒、产出逐字符相等——主链(FC→OSS→Worker)无行为分叉。分叉全部位于**小程序声部**且与静态判定一致:① 日期合法性校验缺失(对照点 a,组① 行 2 absent);② 本地时区双入参日期推导可产出目录≠前缀的 key(对照点 c/d,组① 行 4 diverge)——此类 key 一旦真实上传,Worker 将静默跳过(数据滞留 OSS,无告警);③ 第四处反推 `fragmentIdFromObjectKey` 无任何校验(对照点 b/c,组① 行 5 diverge)。执行结果与静态判定**零矛盾**;四类归类(良性/潜伏/活跃/覆盖洞)与 Postel 宽严分析按 D-12 留给 02-04。

### harness 复跑说明(02-VALIDATION.md 可重放要求)

```bash
# 1. 基线导出(D-06;SCRATCH 为会话 scratchpad 下 phase2-baseline 目录,严禁指向仓库内)
mkdir -p "$SCRATCH"
git archive 5927f36 apps/worker/src apps/fc/shared apps/miniprogram/utils apps/miniprogram/config.js \
  | tar -x -C "$SCRATCH"

# 2. python 侧(解释器必须用仓库 .venv:poller import 链需 pydantic/yaml)
#    harness.py 首部含来源断言:poller/fc_sts/oss_admin 的 __file__ 均须以 $SCRATCH 开头
PYTHONPATH="$SCRATCH/apps/worker/src:$SCRATCH/apps/fc/shared" \
  /Volumes/Data/ProjectCode/my_soniscope/.venv/bin/python "$SCRATCH/harness.py"

# 3. node 侧(node v22.18.0 实测;require 导出树内 utils,audio.js 对 ../config 的相对 require 已保真)
TZ=Asia/Shanghai   node "$SCRATCH/harness.js"
TZ=America/New_York node "$SCRATCH/harness.js"
```

harness 只调用纯函数(`object_key_for` / `fragment_id_from_key` / `FRAGMENT_ID_RE` / `buildFragmentId` / `buildObjectKeyPreview` / `fragmentIdFromObjectKey` / `addChunk` / `resolveChunkTotal` / `ulid`),零云 IO(T-02-03 缓解);harness 与导出树仅存在于 scratchpad,不入仓库(T-02-04 缓解);样本全为合成数据(T-02-01 缓解)。

## 附录:往返校验样本清单

> D-07 样本清单(先预期后实测:预期三格从矩阵组① 行 1/2/4/5/6 静态结论推导写死,再执行验证)。样本**全部为合成数据**(合成 ULID 常量 `01HZX3K8MN5PQR9TFB7AYWVCDE`,合成 deviceShortId `dev01a`,不含任何真实 openid/凭证)。执行结果为佐证,判据以静态行号对照为准(D-05)。chunk 后缀样本值以 `chunking.js` 实际产出为准:经 `git show 5927f36:apps/miniprogram/utils/chunking.js` 核实(`chunking.js:5 @ 5927f36` 注释"每个分片独立 fragment_id,chunk_seq 从 1 递增"+ `:27-31` `addChunk` 只写 `chunk_seq` 字段),**分片不改变 fragment_id 形态**——chunk 场景 fragment_id 与典型值同形,分片信息仅入 `x-oss-meta-chunk-seq/total`(组① 行 8/9)。**TZ 声明:JS 执行佐证反映指定 TZ 下的行为**——全部 JS 样本以 `TZ=Asia/Shanghai node <harness>` 与 `TZ=America/New_York node <harness>` 双跑(Pitfall 2),时区敏感样本(S-06/S-07 及跨年 S-05)逐条记 TZ 于『实测』列。

| ID | 样本值 | 类别 | 预期(FC) | 预期(Worker) | 预期(小程序) | 实测 | 销号 |
|----|--------|------|----------|--------------|--------------|------|------|
| S-01 | `20260704T101500_dev01a_01HZX3K8MN5PQR9TFB7AYWVCDE` | 典型值 | 签发 `recordings/2026-07-04/<id>.wav`(`sts.py:46-59`) | `object_key_for` 同 FC;`fragment_id_from_key(FC key)` 往返成立(`poller.py:47-61`) | 正则通过(`audio.js:95-96`);同 recordedAt 下 `buildObjectKeyPreview` 产出同 key(`audio.js:104-106`) | py:FC/WK 签发 key 逐字符相等;往返等式 True。JS:正则通过;`buildObjectKeyPreview`(同 recordedAt)产出与 FC 签发 key 逐字符相等(TZ=Asia/Shanghai 与 TZ=America/New_York 双跑同果) | ✅ |
| S-02 | `20261332T101500_dev01a_…`(13 月 32 日) | 非法日期但正则可过 | 拒:400 INVALID_REQUEST(`sts.py:56-58` datetime 校验) | 拒:`OssAdminError`(`oss_admin.py:47-49`) | **正则通过**——无日期合法性校验(组① 行 2 absent) | py:FC `FcHttpError: 400 INVALID_REQUEST: invalid fragment_id date`;WK `OssAdminError: 非法 fragment_id 日期`。JS:**正则通过**(`FRAGMENT_ID_RE.test → true`,双 TZ 同)——非法日期放行实证(对照点 a) | ✅ |
| S-03 | `20240229T120000_dev01a_…`(合法闰日) | 闰日 | 签发 `recordings/2024-02-29/…` | 同 FC;往返成立 | 正则通过 | py:FC/WK 签发一致;往返 True。JS:正则通过(双 TZ 同) | ✅ |
| S-04 | `20250229T120000_dev01a_…`(非闰年 2/29) | 闰日(非法变体) | 拒:400 INVALID_REQUEST(datetime 校验) | 拒:`OssAdminError` | **正则通过**(同 S-02,行 2 absent) | py:FC 400 invalid fragment_id date;WK `OssAdminError: 非法 fragment_id 日期`。JS:**正则通过**(true,双 TZ 同)——非闰年 2/29 放行实证(对照点 a) | ✅ |
| S-05 | `20251231T235959_dev01a_…` | 跨年边界 | 签发 `recordings/2025-12-31/…` | 同 FC;往返成立 | 正则通过 | py:FC/WK 签发一致;往返 True。JS:正则通过(双 TZ 同) | ✅ |
| S-06 | 同一 recordedAt(UTC 2026-07-04T16:30:00Z)在两个 TZ 下构造 | 跨时区 | 对 JS 产出 fragment_id 施 `object_key_for`(前缀合法即签发——FC 对时区零感知,`sts.py:46-59` 只看字符串) | 对 JS 产出 key 施往返等式(前缀日期=目录日期则成立) | `fragmentTimestamp`/`objectKeyDate` 走本地时区(`audio.js:63-73`):两 TZ 下前缀与目录日期**均随 TZ 变**(组① 行 4 diverge) | TZ=Asia/Shanghai:fid `20260705T003000_…`、key `recordings/2026-07-05/…`;TZ=America/New_York:fid `20260704T123000_…`、key `recordings/2026-07-04/…`——同一 UTC 瞬间双 TZ 产出**不同 fragment_id 与目录日期**(对照点 d);单 TZ 内前缀=目录日期自洽(`prefix==dirdate → true` 双 TZ 均真) | ✅ |
| S-07 | fragmentId 于 23:59:59 构造,`buildObjectKeyPreview` 传入次日 00:00:01 的 recordedAt | 近午夜 | n/a — FC 无此双入参路径(单一来源,组① 行 4) | 对错位 key 施往返等式:预期拒(等价 S-18) | `buildObjectKeyPreview(fragmentId, recordedAt)` 两独立入参(`audio.js:104-106`):预期产出**目录日期≠前缀日期**的 key(组① 行 4 diverge 的行为化) | TZ=Asia/Shanghai 与 TZ=America/New_York 双跑同果:产出 `recordings/2026-07-05/20260704T235959_….wav`(**目录日期≠前缀日期**,`dir-date != prefix-date → true`);`fragmentIdFromObjectKey` 照单全收返回前缀 id;Worker 对等价错位 key 已证拒(S-18 → `None`,对照点 c) | ✅ |
| S-08 | `20260704T101500_abc_…`(deviceShortId 3 字符) | deviceShortId 过短 | 拒:400 格式(`[A-Za-z0-9]{4,8}` 不匹配) | 拒:`OssAdminError` 格式 | 正则拒(同一字符类,组① 行 1) | py:FC 400 invalid fragment_id format;WK `OssAdminError: 非法 fragment_id 格式`。JS:正则拒(false,双 TZ 同) | ✅ |
| S-09 | `20260704T101500_abcdefghi_…`(9 字符) | deviceShortId 过长 | 拒:400 格式 | 拒:格式 | 正则拒 | py:FC 400 format;WK 格式拒。JS:正则拒(false,双 TZ 同) | ✅ |
| S-10 | `20260704T101500_dev-1a_…`(含 `-`) | deviceShortId 非法字符 | 拒:400 格式 | 拒:格式 | 正则拒 | py:FC 400 format;WK 格式拒。JS:正则拒(false,双 TZ 同) | ✅ |
| S-11 | ULID 截为 25 字符 | ULID 过短 | 拒:400 格式(`{26}` 定长) | 拒:格式 | 正则拒 | py:FC 400 format;WK 格式拒。JS:正则拒(false,双 TZ 同) | ✅ |
| S-12 | ULID 加至 27 字符 | ULID 过长 | 拒:400 格式 | 拒:格式 | 正则拒 | py:FC 400 format;WK 格式拒。JS:正则拒(false,双 TZ 同) | ✅ |
| S-13 | `…_dev01a_01HZX3K8MNILOUabcdefghijkl`(含 Crockford 排除字符 I/L/O/U + 小写) | ULID 字符集宽严 | **接受并签发**(正则 `[0-9A-Za-z]{26}` 宽于 Crockford;`ulid.js` 实际生成集为 Crockford 大写子集) | 接受;往返成立 | 正则通过(同一宽字符类) | py:FC/WK 签发一致;往返 True——三处正则均宽于生成端字符集,行为一致故非漂移(组① 行 1 agree 佐证)。JS:正则通过(双 TZ 同);`ulid(seed)` 实测产出 26 字符纯 Crockford 集(`crockford-only=true`)——正则宽、生成端窄,三处放行行为一致 | ✅ |
| S-14 | `recordings/2026-07-04/<典型 id>.m4a` | 非 .wav key | n/a — FC 只正向签发(组① 行 5) | 拒:`fragment_id_from_key` 返回 None(`poller.py:53` endswith) | `fragmentIdFromObjectKey` **照单全收**(`upload_queue.js:38-44` 无校验切割,组① 行 5 diverge) | py:WK 返回 `None`。JS:`fragmentIdFromObjectKey` 照单全收返回前缀 id(双 TZ 同,对照点 b/c) | ✅ |
| S-15 | chunk 场景 fragment_id(经 `chunking.js` 核实与典型值同形,见节首注) | chunk 后缀 | 同 S-01(分片对 FC 只显现为独立 fragment_id 的多次签发,组③ 行 47) | 同 S-01(分片信息仅在 meta,组① 行 8/9) | 正则通过;`addChunk` 不改 fragment_id | py:FC/WK 签发一致;往返 True(与 S-01 同值同果)。JS:`addChunk` 实测 chunk_seq=1,2 且 fragment_id 原样不变、正则通过;`resolveChunkTotal(1)=null / (2)=2`(组① 行 14 约定佐证) | ✅ |
| S-16 | ``(空串) | 空/畸形 | 拒:400 格式 | 拒:格式 | 正则拒 | py:FC 400 format;WK 格式拒。JS:正则拒(false,双 TZ 同) | ✅ |
| S-17 | `20260704T101500dev01a01HZX…`(无 `_` 分隔) | 空/畸形 | 拒:400 格式 | 拒:格式 | 正则拒 | py:FC 400 format;WK 格式拒。JS:正则拒(false,双 TZ 同) | ✅ |
| S-18 | `recordings/2026-07-05/20260704T101500_dev01a_….wav`(目录日期≠前缀) | 空/畸形(日期错位 key) | n/a — FC 只正向签发 | 拒:往返等式不成立返回 None(`poller.py:57`) | `fragmentIdFromObjectKey` 照单全收(无往返校验) | py:WK 返回 `None`。JS:`fragmentIdFromObjectKey` 照单全收返回前缀 id(双 TZ 同,对照点 b/c) | ✅ |

**类别覆盖对账(D-07 全 11 类):** 典型值(S-01)/ 非法日期(S-02)/ 闰日(S-03,S-04)/ 跨年(S-05)/ 跨时区(S-06)/ 近午夜(S-07)/ deviceShortId 边界(S-08~S-10)/ ULID 边界(S-11~S-13)/ 非 .wav key(S-14)/ chunk 后缀(S-15)/ 空/畸形(S-16~S-18)——18 样本 ≥ 11 类下限。

## 收尾:零 diff 验证与对账

### 配方触发线裁决(D-15)

02-04 四类分布:潜伏 2(F-CON-02/03)+ 覆盖洞 3(F-CON-01/04/06)+ 良性 1(F-CON-05)——存在非良性分歧,**触发配方产出**:`.planning/audit/CONTRACT-TEST-RECIPE.md` 已成文(D-16 五要素,黄金样本复用附录 S-01~S-18,仅设计不实现)。

---
*契约漂移矩阵: 2026-07-05(组① 15 行 + 组② 28 行 + 组③ 5 行 + 普查新行 3 行 = 51 行落格;普查 5 命令存档、9 候选核实、D14-1~6 移交;往返校验 18 样本全销号 + 结论成文(02-03);判定列与零 diff 收尾待 02-04)*
