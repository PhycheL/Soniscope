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

*(02-02 填)*

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
