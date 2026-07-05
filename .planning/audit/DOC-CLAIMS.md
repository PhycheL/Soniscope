# DOC 声明核对清单

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本文档为 Phase 4 DOC 维度(AUDIT-03)的销号底稿——证据层:逐份文档抽取"可与代码/配置对照的声明",逐条以四态判定销号,每条附文档侧与代码侧双行号证据。发现正文不入本文件,判断层条目一律立入 `findings/docs-config.md`(九字段 schema),本文件销号行以 `→ F-DOC-NN` / `→ HYP-NN` 指针链接。范围分层 per D-05(深核/普审/只审引用与自洽/只记存在四层),核对方式 per D-07(可核声明清单式深核,延续 CONTRACT-MATRIX 范式),目标态排除 per D-06。全部证据出自 `git show 5927f36:<path>` / `git grep -n <pat> 5927f36`,禁止读工作树取证(CHARTER 取证纪律);PRD/tech-spec 路径含空格,取证命令须引号包裹(如 `git show '5927f36:docs/v1.0.0 prd/PRD_v1.md'`)。

## 四态词表

| 状态词 | 定义 |
|--------|------|
| `agree` | 文档声明与代码/配置实态**语义一致**(字面差异不算分歧——如文档写 50 MB 而代码写 52428800 字节,数值等价即 agree) |
| `drift` | 文档声明与代码/配置实态**不一致**,且声明引用的目标(路径/常量/行为)在基线存在——同一事实两侧口径相左 |
| `dead-ref` | 文档引用的路径/文件/命令/锚点在基线 `5927f36` **不存在**(死链、旧路径、已迁移目标) |
| `无法静态核实` | 声明指向**纯云端/平台侧事实**(控制台配置数值、微信平台登记值、Aliyun 侧真值),静态取证不可判——只标注,不猜测 |

## 负面清单(判定前置排除)

以下事项**不得**立为 F-DOC 发现(依据 `.planning/audit/DO-NOT-FIX.md` DNF-01~04 与 CHARTER 排除项表):

- **DNF-01~04 已裁定的故意设计**——命中时只写"核实结论 + 引 DNF 条目闭环",不立 F-DOC。点名在列:
  - `issue-cedential` 域名拼写(DNF-02,Aliyun 分配的真实 URL,文档/配置中该拼写的任何出现均按闭环处理);
  - `whisper-local` 转写器故意桩(DNF-01,文档对其"占位/本期不部署"的描述与实态一致即闭环);
  - FC `handler.py` 的 mypy strict 豁免(DNF-03,文档对该豁免的记载不作"覆盖缺口"判定)。
- **目标态两文档不做设计 vs 代码实态对照**——`docs/fc-transcribe-design.md` 与 `docs/multi-user-design.md` 系未来态设计文档(CHARTER 明确排除项 + D-06),只审其引用有效性与明显自相矛盾,不以代码现状评判其设计内容(章程排除)。
- **"文档滞后于目标态设计"不算 drift**——文档描述现状而目标态设计另有蓝图,属已知决策落差而非文档失实(Pitfall 8);drift 判定只针对"文档声明现状 ≠ 代码现状"。

## 覆盖总表(D-05 四层)

23 个对象逐行在列;状态列由各销号计划完成后改为终态("已审无发现"或 F-DOC-NN / HYP-NN 指针),04-05 收口清零。

| 对象 | 层级 | 销号节 | 状态 |
|------|------|--------|------|
| `docs/v1.0.0 prd/PRD_v1.md` | 深核 | §PRD_v1.md(04-03) | 已审:30 条销号无发现级 drift;dead-ref ×2 → HYP-02(04-05 聚合) |
| `docs/v1.0.0 prd/tech-spec.md` | 深核 | §tech-spec.md(04-03) | 已审:36 条销号;drift → F-DOC-01、F-DOC-02;dead-ref ×1 → HYP-02(04-05 聚合) |
| `docs/runbook/cloud-setup.md` | 深核 | (04-04) | 待审 |
| `docs/runbook/deployment-guide.md` | 深核 | (04-04) | 待审 |
| `docs/runbook/fc-deploy.md` | 深核 | (04-04) | 待审 |
| `docs/runbook/mvp-acceptance.md` | 深核 | (04-04) | 待审 |
| `AGENTS.md` | 深核 | (04-05) | 待审 |
| `README.md` | 深核 | (04-05) | 待审 |
| `apps/fc/README.md` | 深核 | (04-05) | 待审 |
| `apps/miniprogram/README.md` | 深核 | (04-05) | 待审 |
| `apps/miniprogram/config.js` | 深核 | (04-05) | 待审 |
| `docs/architecture/architecture-review-2026-07-02.md` | 普审 | (04-05) | 待审 |
| `docs/transcribe-approach-comparison.md` | 普审 | (04-05) | 待审 |
| `docs/agents/domain.md` | 普审 | (04-05) | 待审 |
| `docs/agents/issue-tracker.md` | 普审 | (04-05) | 待审 |
| `docs/agents/triage-labels.md` | 普审 | (04-05) | 待审 |
| `apps/miniprogram/project.config.json` | 普审(配置) | (04-05) | 待审 |
| `apps/miniprogram/app.json` | 普审(配置) | (04-05) | 待审 |
| `docs/fc-transcribe-design.md` | 只审引用与自洽 | (04-05) | 待审(目标态对照未审,章程排除) |
| `docs/multi-user-design.md` | 只审引用与自洽 | (04-05) | 待审(目标态对照未审,章程排除) |
| `docs/小程序原型/`(PixPin PNG ×4) | 只记存在 | (04-05) | 待审 |
| `docs/architecture/soniscope-mvp-architecture.drawio` | 只记存在 | (04-05) | 待审 |
| `docs/runbook/us-001-manual.html` | 只记存在 | (04-05) | 待审 |

## §PRD_v1.md 深核(04-03)

> 对象:`docs/v1.0.0 prd/PRD_v1.md`(869 行 @ 5927f36)。取证命令:`git show '5927f36:docs/v1.0.0 prd/PRD_v1.md'`(路径空格引号)。抽取粒度 per D-07:命令/路径/常量/接口声明逐条,叙事类按声明句合并,纯产品愿景叙事不入清单。PRD 自declare "技术实现细节权威在 tech-spec,冲突以 tech-spec 为准"(`docs/v1.0.0 prd/PRD_v1.md:5 @ 5927f36`)——本节只核 PRD 直接给出字面值/行为的声明;PRD 转引 tech-spec 章节的声明由 §tech-spec.md 节承接。

| # | 文档侧声明 | 文档证据 | 代码/配置侧实态 | 代码证据 | 判定 |
|---|-----------|----------|----------------|----------|------|
| P-01 | 系统四层:小程序极薄前端 / FC 3.0 两个顶级 Web 函数(无 service 层)/ OSS 私有桶 / Python Worker | `docs/v1.0.0 prd/PRD_v1.md:17-21 @ 5927f36` | 基线 apps/ 恰为 miniprogram、fc(仅 issue_credential/verify_upload 两函数目录 + shared/tests)、worker 三分;无任何 service 层代码 | `git ls-tree 5927f36 apps/ apps/fc/` → 三 app + 两函数目录(另 HYP-01 证据行同源) | agree |
| P-02 | OSS Bucket `soniscope-audio`、region `cn-beijing`、endpoint `oss-cn-beijing.aliyuncs.com` | `docs/v1.0.0 prd/PRD_v1.md:20,86 @ 5927f36` | 小程序上传域名常量 `https://soniscope-audio.oss-cn-beijing.aliyuncs.com` 含同一桶名+region+endpoint 三要素;`OSS_REGION = 'cn-beijing'` | `apps/miniprogram/config.js:12,15 @ 5927f36` | agree |
| P-03 | 云端侧一次性资源事实:Bucket ACL=private、RAM 三子账号 + 角色 ARN `acs:ram::1633875501759333:role/soniscope-uploader-role`、FC HTTP 触发器 anonymous 配置、微信平台域名白名单已登记、真机 openid 已登记 | `docs/v1.0.0 prd/PRD_v1.md:86-89 @ 5927f36` | 均为控制台/平台侧配置,代码只经环境变量消费(`RAM_ROLE_ARN` 等) | `apps/fc/shared/fc_shared/env.py:56-66 @ 5927f36`(仅变量名装载,真值在云端) | 无法静态核实 |
| P-04 | FC 两公网 URL 字面值:`issue-cedential-ottfirocds.cn-beijing.fcapp.run`(拼写少 r)与 `verify-upload-nnjpaoamhw.cn-beijing.fcapp.run` | `docs/v1.0.0 prd/PRD_v1.md:108 @ 5927f36` | config.js 两常量逐字符同值,且 :8 注释明示拼写系 Aliyun 分配真实 URL 勿"修正" | `apps/miniprogram/config.js:8-11 @ 5927f36` | agree(闭环 DNF-02) |
| P-05 | 小程序 AppID `wx3f973c7297728b0c` | `docs/v1.0.0 prd/PRD_v1.md:89 @ 5927f36` | project.config.json appid 字段同值 | `apps/miniprogram/project.config.json:2 @ 5927f36` | agree |
| P-06 | STS 凭证精确到单 object key、仅本次指定 key 可写;越权 PutObject/GetObject/ListObjects/DeleteObject 全拒 | `docs/v1.0.0 prd/PRD_v1.md:31,207-208 @ 5927f36` | `single_key_policy` Resource 精确单 key 无通配符、Action 仅 `oss:PutObject`;fc_live 反例场景表含 delete_object 越权项 | `apps/fc/shared/fc_shared/sts.py:62-73 @ 5927f36`、`apps/worker/src/soniscope_worker/fc_live.py:72 @ 5927f36` | agree |
| P-07 | STS 凭证有效期 ≤ 15 分钟(S-02) | `docs/v1.0.0 prd/PRD_v1.md:814 @ 5927f36` | `STS_MAX_DURATION_SECONDS = 900`(= 15 分钟),签发恒传该值 | `apps/fc/shared/fc_shared/sts.py:24-25 @ 5927f36`、`apps/fc/issue_credential/handler.py:79 @ 5927f36`(引 HYP-09 证据行) | agree |
| P-08 | 上传大小上限经 FC 环境变量 `MAX_UPLOAD_BYTES` 可调;`size=60000000` → 400 `SIZE_EXCEEDED`,`size=10000000` → 正常签发 | `docs/v1.0.0 prd/PRD_v1.md:189,210 @ 5927f36` | 默认 `DEFAULT_MAX_UPLOAD_BYTES = 52428800`(50 MB),env 可覆盖;60000000 > 52428800 触发、10000000 通过,边界语义一致 | `apps/fc/shared/fc_shared/env.py:40-41,98-107,124 @ 5927f36` | agree |
| P-09 | 错误码字面值与状态码:`INVALID_CODE` 401、`OPENID_NOT_ALLOWED` 403、`SIZE_EXCEEDED` 400、`OBJECT_NOT_FOUND`、`SIZE_MISMATCH`(附 actual_size) | `docs/v1.0.0 prd/PRD_v1.md:204-210,253,433 @ 5927f36` | errors.py 同名常量 + 注释钉定同状态码;SIZE_MISMATCH 响应含 actual_size 字段 | `apps/fc/shared/fc_shared/errors.py:13-24 @ 5927f36`、`apps/fc/shared/fc_shared/head.py:44-49 @ 5927f36` | agree |
| P-10 | FC 鉴权三步走:wx code 换 openid → 检查 allowlist → 签发;`OPENID_ALLOWLIST` 环境变量逗号分隔多 openid | `docs/v1.0.0 prd/PRD_v1.md:183-184,703 @ 5927f36` | `authorize_request` 恰为 read body → code_to_openid → check_allowlist 三步;allowlist 经 env 装载为 tuple | `apps/fc/shared/fc_shared/auth.py:39-52 @ 5927f36`、`apps/fc/shared/fc_shared/env.py:53 @ 5927f36` | agree |
| P-11 | `/verify-upload` 用 HeadObject 校验对象存在 + 大小一致,失败返回明确原因码(不存在/大小不符/一致三态) | `docs/v1.0.0 prd/PRD_v1.md:234,704 @ 5927f36` | `verify_upload_result` 恰映射三态:不存在→OBJECT_NOT_FOUND、Content-Length 不符→SIZE_MISMATCH+actual_size、一致→verified:true | `apps/fc/shared/fc_shared/head.py:34-55 @ 5927f36` | agree |
| P-12 | 上传/verify/云端转写失败重试:自动重试 3 次(网络/5xx 退避,4xx 立即失败),间隔策略两语言一致 | `docs/v1.0.0 prd/PRD_v1.md:396,421,543,706 @ 5927f36` | JS `RETRY_DELAYS_MS = [5000,15000,45000]`、`MAX_UPLOAD_RETRIES = 3`;Python `RETRY_DELAYS_SECONDS = (5,15,45)`,4xx 立即抛 | `apps/miniprogram/utils/uploader.js:28-29 @ 5927f36`、`apps/worker/src/soniscope_worker/nls.py:45,262 @ 5927f36` | agree |
| P-13 | 上传列表展示八种状态:草稿/待上传(离线排队)/上传中/待 verify/上传成功(verified)/上传失败/待人工重传/待人工 verify | `docs/v1.0.0 prd/PRD_v1.md:446 @ 5927f36` | upload_queue.js 恰 8 个状态常量,STATUS_TEXT 中文文案逐一对应 | `apps/miniprogram/utils/upload_queue.js:9-27 @ 5927f36` | agree |
| P-14 | 本地缓存保留策略:仅 verified 且 ≥48h 才自动清理;verify 未通过永不自动删;手动删除带二次确认 | `docs/v1.0.0 prd/PRD_v1.md:422-426,705 @ 5927f36` | uploads 页自动清理仅命中 verified 且 verified_at 距今 ≥48h;queue_runtime docstring 同口径含手动删除二次确认 | `apps/miniprogram/pages/uploads/uploads.js:289-300 @ 5927f36`、`apps/miniprogram/utils/queue_runtime.js:2 @ 5927f36` | agree |
| P-15 | 长录音超阈值自动分片、多片共享 session_id、chunk_total 停止后回填;25 分钟录音 → 3 条 Fragment | `docs/v1.0.0 prd/PRD_v1.md:340-359,701 @ 5927f36` | 阈值常量 `CHUNK_MAX_DURATION_SECONDS = 600`(25 min = 1500 s → 3 片);chunking.js 实现 chunk_total 回填到 session 全部草案 | `apps/miniprogram/config.js:22-23 @ 5927f36`、`apps/miniprogram/utils/chunking.js:39-51 @ 5927f36` | agree |
| P-16 | fragment_id 前端生成全局唯一(ULID 随机性保证同秒不同);device_short_id 首启生成并持久化 | `docs/v1.0.0 prd/PRD_v1.md:361-383,702 @ 5927f36` | fragment_id 正则含 26 字符 ULID 段 + 4-8 字符 device 段(FC/Worker/小程序三处一致,契约矩阵行 1);app.js 首启 `ensureDeviceShortId` 持久化 | `apps/fc/shared/fc_shared/sts.py:29-33 @ 5927f36`、`apps/miniprogram/app.js:15-18 @ 5927f36` | agree |
| P-17 | 音频 sha256 在前端计算,经 OSS 用户自定义元数据(`x-oss-meta-*`)传递给 Worker(OQ-2/OQ-8) | `docs/v1.0.0 prd/PRD_v1.md:375,833,839 @ 5927f36` | 录音页主线程 `sha256Hex(buf)` 计算;`buildOssMetadata` 写 `x-oss-meta-sha256` 等 7 键;Worker 侧 `head_metadata` 读回 | `apps/miniprogram/pages/index/index.js:30,640 @ 5927f36`、`apps/miniprogram/utils/audio.js:157-169 @ 5927f36` | agree |
| P-18 | Worker 按 `config.yaml` 可配置 `poll.interval_seconds` 周期轮询 OSS `recordings/` 前缀 | `docs/v1.0.0 prd/PRD_v1.md:482,707 @ 5927f36` | Pydantic 配置含 `interval_seconds` 字段;poller 列举 recordings/ 前缀 | `apps/worker/src/soniscope_worker/config.py:51-54 @ 5927f36`、`apps/worker/src/soniscope_worker/poller.py:30,221-223 @ 5927f36` | agree |
| P-19 | Worker 任何路径不调用 OSS 删除接口,OSS 文件永不删除(G-3/FR-11/R-07) | `docs/v1.0.0 prd/PRD_v1.md:29,489,708,812 @ 5927f36` | `OssSource` Protocol 仅 list/head/download 三方法,docstring 明示"刻意不暴露任何删除方法";worker src 业务代码零 DeleteObject 调用(命中仅 cli docstring 与 fc_live 越权反例) | `apps/worker/src/soniscope_worker/poller.py:215-231 @ 5927f36`、`git grep -n 'DeleteObject\|delete_object' 5927f36 -- apps/worker/src/`(仅 cli.py:499 注释与 fc_live.py:72,509-512 反例) | agree |
| P-20 | 写入协议"先临时 → 原子 rename → 最后写 `.done`";启动时三目录恢复扫描(inbox→tmp→fragments) | `docs/v1.0.0 prd/PRD_v1.md:509-515,709-710 @ 5927f36` | pipeline docstring 钉定七阶段 + .done 最后 + 失败不建 .done;recovery 三段扫描实现 | `apps/worker/src/soniscope_worker/pipeline.py:5-20,273-275 @ 5927f36`、`apps/worker/src/soniscope_worker/recovery.py:196-250 @ 5927f36` | agree |
| P-21 | 幂等基于 `.done` 判定(存在即跳过,配置变更不自动重转);存量重转仅经 `retranscribe` CLI,flag 语义 `--upgrade`/`--force`/`--all-from` | `docs/v1.0.0 prd/PRD_v1.md:563-588,712 @ 5927f36` | 轮询只看 .done(存在即跳过不下载/转码/转写);CLI 三 flag 签名与 help 文案语义逐条一致 | `apps/worker/src/soniscope_worker/pipeline.py:15-16 @ 5927f36`、`apps/worker/src/soniscope_worker/cli.py:403-410 @ 5927f36` | agree |
| P-22 | Fragment 完成态五产物齐全:`audio.wav`/`manifest.json`/`transcript.json`/`transcript.txt`/`.done`;`.done` 为 0 字节旗标 | `docs/v1.0.0 prd/PRD_v1.md:596-613,713 @ 5927f36` | pipeline 七阶段落全五产物,"最后创建 0 字节 .done";完成日志自述"五产物齐全" | `apps/worker/src/soniscope_worker/pipeline.py:11-13,273-275 @ 5927f36` | agree |
| P-23 | `transcript.json` 为结构化 JSON(segments + 模型版本),`transcript.txt` 由 segments.text 拼接派生 | `docs/v1.0.0 prd/PRD_v1.md:606-607 @ 5927f36` | transcript 字段集 `segments/language/model/params_version/provider`;txt 由 `segments[].text` 顺序拼接派生 | `apps/worker/src/soniscope_worker/manifest.py:15-17,54 @ 5927f36` | agree |
| P-24 | 本期不部署本地 Whisper,转写全走云端 API;本地转写仅占位骨架,切换只改配置不改业务代码(NG-9/FR-14) | `docs/v1.0.0 prd/PRD_v1.md:3,530,711,730 @ 5927f36` | 工厂仅 cloud-speech/whisper-local 两分支;WhisperLocalTranscriber 占位抛 NotImplementedError 并提示改配 cloud-speech | `apps/worker/src/soniscope_worker/transcriber.py:144-165,168-183 @ 5927f36` | agree(闭环 DNF-01) |
| P-25 | PRD 全篇引用的 `make` 命令族(verify-prep/check-config/init-dirs/deploy-fc/test-fc-live/fc-logs/test-verify-upload/test-sts-escape/retranscribe/show-oss-object/oss-delete-obj/list-oss-objects/verify-e2e-\*/test-e2e-\*/verify-no-stale/verify-oss-retention 等)均实际存在 | `docs/v1.0.0 prd/PRD_v1.md:103-110,202-221,494-499,635-664 @ 5927f36` | Makefile 45 目标逐名核对全部在列(抽查 verify-prep :35、deploy-fc :41、test-fc-live :50、retranscribe :119、verify-oss-retention :140、verify-e2e-integrity :143) | `Makefile:35,41,50,119,140,143 @ 5927f36` | agree |
| P-26 | wx-login 失败验证使用 `tests/fixtures/wx-login-fixture.json` 中的伪造 code | `docs/v1.0.0 prd/PRD_v1.md:204 @ 5927f36` | 基线 tests/ 仅 audio/ 子目录,无 fixtures/ 目录;全仓检索该文件名仅 PRD 此一处命中;fc_live 实现自造伪造 code,不读任何 fixture 文件 | `git ls-tree -r 5927f36 tests/`(无 fixtures/)、`apps/worker/src/soniscope_worker/fc_live.py:61,286-298 @ 5927f36` | dead-ref |
| P-27 | 技术权威文档路径 `docs/tech-spec.md`(全篇 30+ 处转引锚点,如"权威定义在 docs/tech-spec.md") | `docs/v1.0.0 prd/PRD_v1.md:5,63,122,177,782-795 @ 5927f36` | 基线该路径无文件,实存 `docs/v1.0.0 prd/tech-spec.md`(权威文档迁移后 PRD 引用未随迁) | `git ls-tree 5927f36 docs/`(无 docs/tech-spec.md;有 `docs/v1.0.0 prd/tech-spec.md`) | dead-ref → HYP-02(聚合立条留 04-05,此处登记) |
| P-28 | 【HYP-21 专项】PRD 明示转写产物展示/日稿/LLM 润色为 MVP 范围外:"本期不做 LLM 润色、不做日稿展现"(:15)、NG-1 不做 LLM 润色与日稿生成、NG-2 不做日稿呈现界面且手机端不需要查看历史 Fragment 或日稿 | `docs/v1.0.0 prd/PRD_v1.md:15,722-723 @ 5927f36` | 代码实态与范围声明互证:小程序仅 index/uploads/dev 三页,全仓 miniprogram 源码零 `transcript` 命中(无任何转写产物读取 UI);Worker 无展示面(NG-8 口径) | `apps/miniprogram/app.json:2-6 @ 5927f36`、`git grep -ln 'transcript' 5927f36 -- apps/miniprogram/` → 0 文件 | agree → HYP-21(04-09 回填锚点:范围外定位与 PRD 范围声明一致,行号 :15,:722-723) |
| P-29 | 【HYP-16 半句专项】PRD 对单机单用户/离线滞留/本地盘权威边界的声明:核心承诺"云端音频 + 本地文本"双落点(:15)、G-1 中断自动恢复或显式提示(:27)、manifest.json 为权威状态来源(:596)、NG-4 只用 openid allowlist 单用户(:725) | `docs/v1.0.0 prd/PRD_v1.md:15,27,596,725 @ 5927f36` | 代码侧实态引 HYP-16 既有证据(不重复采证):单线程轮询 Worker 离线即无扫描 `poller.py:378-391 @ 5927f36`;对象永不删、重启按硬盘状态续、音频可自 OSS 重下 `pipeline.py:15-18 @ 5927f36`——PRD 未承诺 Worker 高可用或多机,离线滞留后补齐与 G-1"自动恢复"口径一致 | 引 HYPOTHESES.md HYP-16 证据行(`poller.py:378-391`、`pipeline.py:15-18` 等 @ 5927f36) | agree → HYP-16(半句;销号引 HANDOFF-PHASE4.md DOC 节第 1 条) |
| P-30 | ASR 选型登记(OQ-6):NLS 项目 `soniscope`、endpoint `cn-beijing`、模型"中文普通话(识音石 V1 - 端到端模型)"、无免费额度 | `docs/v1.0.0 prd/PRD_v1.md:90,837 @ 5927f36` | NLS 项目/appkey/模型选择为 Aliyun 控制台侧配置,运行时经 `$SONISCOPE_HOME/config.yaml`(仓外)装载,基线仓内无该项目名/appkey 真值可对照 | `apps/worker/src/soniscope_worker/config.py:63-75 @ 5927f36`(transcriber 配置字段仅 schema,真值仓外) | 无法静态核实 |

**PRD 节机械对账:** 清单条目总数 **30**(P-01 ~ P-30);四态计数:agree **26**(内含闭环 DNF-01 ×1、DNF-02 ×1、→ HYP-21 结论行 ×1、→ HYP-16 结论行 ×1)+ drift **0** + dead-ref **2**(P-26、P-27;其中 → HYP-02 登记 ×1)+ 无法静态核实 **2**(P-03、P-30);复算:26 + 0 + 2 + 2 = 30 ✓。

## §tech-spec.md 深核(04-03)

> 对象:`docs/v1.0.0 prd/tech-spec.md`(782 行 @ 5927f36,自 declare"所有技术实现细节的唯一权威来源" :3)。取证命令:`git show '5927f36:docs/v1.0.0 prd/tech-spec.md'`。dead-ref 检查:文内全部相对路径/文档引用经 `git ls-tree -r --name-only 5927f36` 存在性核对。域名/URL 声明本节销**文档侧**行,配置侧对照行见 config.js 节(04-05)。

| # | 文档侧声明 | 文档证据 | 代码/配置侧实态 | 代码证据 | 判定 |
|---|-----------|----------|----------------|----------|------|
| T-01 | §1.1 四层架构:小程序 / FC 3.0 两顶级 Web 函数(无 service 层)/ OSS 私有桶 `soniscope-audio`(cn-beijing)/ Python Worker | `docs/v1.0.0 prd/tech-spec.md:13-18 @ 5927f36` | 基线 apps/ 三分、fc/ 仅两函数目录、无 service 层代码;桶名/region 常量在 config.js | `git ls-tree 5927f36 apps/ apps/fc/`、`apps/miniprogram/config.js:12,15 @ 5927f36` | agree |
| T-02 | §1.3 小程序代码绝不出现长期 AccessKey / 业务密钥 | `docs/v1.0.0 prd/tech-spec.md:39 @ 5927f36` | 自研 lint 以 `_AK_ID_RE`(LTAI 前缀)扫描小程序源;Phase 3 秘密五模式全仓扫描 miniprogram 零命中(scans/secrets.md 销号) | `apps/worker/src/soniscope_worker/miniprogram_lint.py:42,124-125 @ 5927f36` | agree |
| T-03 | §1.3/§3.2 OSS object 唯一数据契约:音频本体 + `x-oss-meta-*` 7 键(session-id/chunk-seq/chunk-total/recorded-at/duration/original-format/sha256),Worker HeadObject 读回 | `docs/v1.0.0 prd/tech-spec.md:40,178-190 @ 5927f36` | 前端 `buildOssMetadata` 恰写 7 键同名;Worker META_* 常量 + `head_metadata` 读回映射 manifest | `apps/miniprogram/utils/audio.js:157-169 @ 5927f36`、`apps/worker/src/soniscope_worker/poller.py:34-41,139-141,225-227 @ 5927f36` | agree |
| T-04 | §1.5 统一重试表:网络/5xx 退避 3 次(5s→15s→45s)、4xx 立即失败、Worker 下载失败删 `.part` 下轮重下 | `docs/v1.0.0 prd/tech-spec.md:53-62 @ 5927f36` | 双语言常量与语义逐条一致;下载失败/sha 失配删 `.part` 下轮重下 | `apps/miniprogram/utils/uploader.js:28-29 @ 5927f36`、`apps/worker/src/soniscope_worker/nls.py:45,262 @ 5927f36`、`poller.py:272-284 @ 5927f36` | agree |
| T-05 | 文档路径引用:头部"PRD(`docs/PRD_v1.md`)"(:3)与 §2.1 monorepo 树内 `docs/PRD_v1.md`、`docs/tech-spec.md` 两节点(:80-81) | `docs/v1.0.0 prd/tech-spec.md:3,80-81 @ 5927f36` | 基线 docs/ 顶层无此两文件,实存 `docs/v1.0.0 prd/PRD_v1.md` 与 `docs/v1.0.0 prd/tech-spec.md`(迁移后自引用未随迁);docs/runbook/ 引用(:82)存在无恙 | `git ls-tree -r --name-only 5927f36 docs/`(无顶层 PRD_v1.md/tech-spec.md) | dead-ref → HYP-02(聚合立条留 04-05,此处登记) |
| T-06 | §2.1 约定 6:FC 3.0 无 service 层;云端函数名 kebab-case、代码目录 snake_case 由部署脚本映射;启动命令 `python3 app.py`,app.py 由部署脚本复制到函数包根并转发 `handler.handler` | `docs/v1.0.0 prd/tech-spec.md:95 @ 5927f36` | fc_deploy `CUSTOM_RUNTIME_ENTRYPOINT = "app.py"`、打包时 copy2 至 staging 根;共享 app.py 转发 handler.handler | `apps/worker/src/soniscope_worker/fc_deploy.py:51,208-212 @ 5927f36`、`apps/fc/shared/app.py:17-31 @ 5927f36`(引 HYP-12 证据行) | agree |
| T-07 | §2.1 约定 7:Worker 模块清单 `__init__/__main__/cli/config/paths`(后续 story 按需扩展) | `docs/v1.0.0 prd/tech-spec.md:96 @ 5927f36` | 基线 soniscope_worker/ 26 模块,声明的 5 个全部在列;超出部分为声明自带的"按需扩展"语义覆盖 | `git ls-tree 5927f36 apps/worker/src/soniscope_worker/`(26 文件含全部 5 个) | agree |
| T-08 | §2.2 运行时目录布局:`inbox/<id>.part`、`inbox/failed/`、`fragments/<date>/<id>/` 五产物、`tmp/<id>.transcript.json.tmp` | `docs/v1.0.0 prd/tech-spec.md:100-117 @ 5927f36` | `.part` 命名 `part_path`;转码失败留档 `inbox/failed/`;五产物与 tmp 命名同 pipeline/recovery 实现 | `apps/worker/src/soniscope_worker/poller.py:79-81 @ 5927f36`、`audio.py:221-235 @ 5927f36`、`pipeline.py:11-13 @ 5927f36`、`recovery.py:196-250 @ 5927f36` | agree |
| T-09 | §2.3 config.yaml schema(oss 四字段/poll.interval_seconds/transcriber 十字段含 local.enabled)+ 加载顺序(env → 仓库根 .env,无固定兜底)+ 缺失字段一次性全列 | `docs/v1.0.0 prd/tech-spec.md:121-145 @ 5927f36` | Pydantic 模型字段逐一同名;paths 装载顺序 env → 向上找 .env → 报错无兜底;`_collect_validation_errors` 聚合报错 | `apps/worker/src/soniscope_worker/config.py:51-75 @ 5927f36`、`apps/worker/src/soniscope_worker/paths.py:49-63 @ 5927f36` | agree |
| T-10 | §2.3 安全要求:config.yaml 权限必须 600,`make check-config` 检查,非 600 则**警告** | `docs/v1.0.0 prd/tech-spec.md:147 @ 5927f36` | 恰 600 判定 + CLI 侧权限不符仅警告不拒载——与文档"警告"口径一致(HYP-08 细化边界即此,文档侧无夸大) | `apps/worker/src/soniscope_worker/config.py:148-150 @ 5927f36`、`cli.py:48-53 @ 5927f36` | agree |
| T-11 | §3.1 fragment_id 格式 `<YYYYMMDDTHHMMSS>_<deviceShortId 4-8 字符>_<26 字符 ULID>`;分片阈值前端常量 `CHUNK_MAX_DURATION_SECONDS = 600` | `docs/v1.0.0 prd/tech-spec.md:156-169 @ 5927f36` | 三处正则同语义(契约矩阵行 1 已三列 agree);config.js 常量同名同值 600 | `apps/fc/shared/fc_shared/sts.py:30-33 @ 5927f36`、`apps/miniprogram/config.js:22-23 @ 5927f36` | agree |
| T-12 | §3.2 object key 模板 `recordings/<YYYY-MM-DD>/<fragment_id>.wav`;`chunk_total=0` 表非分片、manifest 存 `null` | `docs/v1.0.0 prd/tech-spec.md:173-190 @ 5927f36` | FC/Worker f-string 模板一致(矩阵行 3);0↔null 三段映射双侧注释文档化(矩阵负面清单第三条即此约定) | `apps/fc/shared/fc_shared/sts.py:46-59 @ 5927f36`、`apps/worker/src/soniscope_worker/poller.py:134-141 @ 5927f36` | agree |
| T-13 | §3.3 manifest schema:字段来源分工(key 解析/meta 读回/本地计算)+ sha256 一致性规则(直通相等、转码必不同且不留 null) | `docs/v1.0.0 prd/tech-spec.md:192-238 @ 5927f36` | ManifestDraft 承载 meta 读回字段;build_manifest 组装 audio/upload/transcription 三节;直通路径 sha 相等有测试锁定(PRD P-22/US-019 同源) | `apps/worker/src/soniscope_worker/poller.py:114-141 @ 5927f36`、`apps/worker/src/soniscope_worker/manifest.py:108 @ 5927f36` | agree |
| T-14 | §3.4 transcript.json 恰五字段(segments/language/model/params_version/provider);`duration` 仅内存不落盘 | `docs/v1.0.0 prd/tech-spec.md:240-257 @ 5927f36` | `_TRANSCRIPT_JSON_FIELDS` 五元组同名;TranscriptResult 含 duration 且 as_dict 派生时剔除 | `apps/worker/src/soniscope_worker/transcriber.py:25-26,49-69 @ 5927f36`、`manifest.py:54 @ 5927f36` | agree |
| T-15 | §3.5 三段式协议表(下载 .part/转码 .wav.tmp/转写 tmp/.transcript.json.tmp/完成 .done)+ 同文件系统约束 + "当且仅当 .done 存在视为完成" | `docs/v1.0.0 prd/tech-spec.md:259-272 @ 5927f36` | pipeline 七阶段 .done 最后、失败不建 .done;中间态文件名与位置逐一同实现 | `apps/worker/src/soniscope_worker/pipeline.py:5-20,273-275 @ 5927f36`、`recovery.py:47-60 @ 5927f36` | agree |
| T-16 | §3.6 启动恢复三段扫描表(inbox .part/.wav.tmp → tmp .transcript.json.tmp → fragments 状态判定三分支) | `docs/v1.0.0 prd/tech-spec.md:274-297 @ 5927f36` | recovery 三段扫描实现与表逐行对应;"audio.wav 无 .done → 重转写"由 pipeline 恢复段承接 | `apps/worker/src/soniscope_worker/recovery.py:196-250 @ 5927f36`、`pipeline.py:281-295 @ 5927f36` | agree |
| T-17 | §3.7 幂等以 .done 为准(配置变更不自动重转);retranscribe 完整签名 `<id> [--all-from] [--upgrade] [--force]` 四行为表;file lock 防同 fragment 并发 | `docs/v1.0.0 prd/tech-spec.md:299-321 @ 5927f36` | 轮询只看 .done;CLI 三 flag help 语义逐条一致;fragment_lock 文件锁在案 | `apps/worker/src/soniscope_worker/pipeline.py:15-16 @ 5927f36`、`cli.py:403-410 @ 5927f36`、`locks.py:35-41 @ 5927f36` | agree |
| T-18 | §4.0 FC 运行时环境变量表 10 名(OSS_BUCKET/OSS_REGION/OSS_ENDPOINT/RAM_ROLE_ARN/ALIYUN_AK_ID/ALIYUN_AK_SECRET/WX_APPID/WX_APP_SECRET/OPENID_ALLOWLIST/MAX_UPLOAD_BYTES 默认 52428800) | `docs/v1.0.0 prd/tech-spec.md:331-342 @ 5927f36` | env.py 装载同名 10 变量;默认值常量 52428800 同值 | `apps/fc/shared/fc_shared/env.py:16-41,124 @ 5927f36` | agree |
| T-19 | §4.0 注:FC 两公网 URL(`issue-cedential-ottfirocds`/`verify-upload-nnjpaoamhw`)+ uploadFile 域名 `soniscope-audio.oss-cn-beijing.aliyuncs.com` | `docs/v1.0.0 prd/tech-spec.md:346 @ 5927f36` | config.js 三常量逐字符同值;`issue-cedential` 拼写系 Aliyun 真实分配(:8 注释)——核实结论闭环 DNF-02 不立 F-DOC;配置侧对照行见 config.js 节(04-05) | `apps/miniprogram/config.js:8-12 @ 5927f36` | agree(闭环 DNF-02) |
| T-20 | §4.1 请求字段(code/fragment_id/size)、鉴权三步与错误码、SIZE_EXCEEDED 响应含 limit_bytes/actual_bytes、STS 签发(单 key 精确 Resource、≤900s)、成功响应七字段 | `docs/v1.0.0 prd/tech-spec.md:350-379 @ 5927f36` | authorize_request 三步;check_size 恰带 limit_bytes/actual_bytes;assume_role 传 single_key_policy + STS_MAX_DURATION_SECONDS;credential_response 七字段(字段名引用,不涉真值,DNF-04 語境) | `apps/fc/shared/fc_shared/auth.py:39-52 @ 5927f36`、`sts.py:91-99,62-73,102-114 @ 5927f36`、`apps/fc/issue_credential/handler.py:71-81 @ 5927f36` | agree |
| T-21 | §4.2 verify-upload 请求(code/fragment_id/expected_size)+ HeadObject 三态响应表(OBJECT_NOT_FOUND/SIZE_MISMATCH+actual_size/verified:true+etag+size+last_modified) | `docs/v1.0.0 prd/tech-spec.md:385-401 @ 5927f36` | verify_upload_result 三态映射与响应字段逐一同名 | `apps/fc/shared/fc_shared/head.py:34-55 @ 5927f36` | agree |
| T-22 | §4.4 STS Policy 模板:单 Resource 无通配符、Action 仅 oss:PutObject、15 分钟过期、PutObject 天然可写 meta 无需额外 Action | `docs/v1.0.0 prd/tech-spec.md:425-440 @ 5927f36` | single_key_policy 逐字段同模板;时效恒 900s(引 HYP-09 证实行:Resource 精确单 key、单 Action) | `apps/fc/shared/fc_shared/sts.py:62-73,24-25 @ 5927f36` | agree |
| T-23 | §5.1 格式策略:ffprobe 检测真实格式不信扩展名、合规 WAV 直通/重封装、非 WAV ffmpeg 转码、失败留档 inbox/failed/ 不污染 fragments/ | `docs/v1.0.0 prd/tech-spec.md:467-473 @ 5927f36` | audio.py docstring 与实现逐条同款(探测/直通/转码/留档);_archive_failed 留档路径同 | `apps/worker/src/soniscope_worker/audio.py:5-14,43-64,134-142,221-235 @ 5927f36` | agree |
| T-24 | §5.2 转写策略:方案 A OSS 签名 URL(1 小时有效)首选、轮询超 50 分钟重签、方案 B direct 降级、日志打印 mode=oss-url / mode=direct-upload | `docs/v1.0.0 prd/tech-spec.md:475-480 @ 5927f36` | `SIGNED_URL_EXPIRES_SECONDS = 3600`、`RESIGN_THRESHOLD_SECONDS = 50 * 60` 超阈重签;双模式日志字样在案 | `apps/worker/src/soniscope_worker/nls.py:49-50,10,314-316 @ 5927f36` | agree |
| T-25 | §5.3 Transcriber Protocol 签名 `transcribe(fragment_id, audio_path, oss_key) -> TranscriptResult`、TranscriptResult 六字段、工厂表(cloud-speech 实转 / whisper-local 占位抛 NotImplementedError)、切 provider 只改配置 | `docs/v1.0.0 prd/tech-spec.md:484-520 @ 5927f36` | Protocol 签名逐参一致;dataclass 六字段同名;工厂两分支 + whisper 占位抛错(故意桩,闭环 DNF-01 不立 F-DOC) | `apps/worker/src/soniscope_worker/transcriber.py:81-90,49-62,144-165,168-183 @ 5927f36` | agree(闭环 DNF-01) |
| T-26 | §6.1 故障注入三开关名(mock-fc-url-broken/mock-network-offline/mock-verify-fail)、运行时切换无需改源码、仅非 production 可见 | `docs/v1.0.0 prd/tech-spec.md:529-535 @ 5927f36` | 三开关名逐字符一致且被测试锁定;门控实现经 config.ENV(小程序无 NODE_ENV 概念,文档 NODE_ENV 为泛称,语义一致——门控三重兜底见 HANDOFF DOC 节 HYP-14 第 2 条) | `apps/miniprogram/test/fault_injection.test.js:27-28 @ 5927f36`、`pages/uploads/uploads.js:164,331,353 @ 5927f36`、`pages/dev/dev.js:18 @ 5927f36` | agree |
| T-27 | §6.1 音频 sha256:"前端用 wasm-crypto 或类似库计算,避免主线程阻塞"(平台约束 bullet 与 SDK 接口表两处) | `docs/v1.0.0 prd/tech-spec.md:539,549 @ 5927f36` | 实态为手写纯 JS SHA-256 于主线程对全量音频字节同步哈希,无任何 wasm/异步/分块让出;代码 docstring 自认"本期先用纯 JS……wasm 化属后续性能优化"——文档声明与实现路径相反 | `apps/miniprogram/utils/sha256.js:4-5,9-18,66-135 @ 5927f36`、`pages/index/index.js:30,640 @ 5927f36`(引 HYP-03 静态主判据) | drift → F-DOC-01 |
| T-28 | §6.2 NLS 选型(项目 soniscope/识音石模型/无免费额度)与 §6.6 成本预估表(¥39.47/月等云端价格) | `docs/v1.0.0 prd/tech-spec.md:551-553,642-651 @ 5927f36` | NLS 项目配置与云端计费费率均为 Aliyun 平台侧事实,静态取证不可判(代码侧仅费率入参 `estimate_cost_yuan`) | `apps/worker/src/soniscope_worker/nls.py:108 @ 5927f36`(计算函数,费率真值云端) | 无法静态核实 |
| T-29 | §6.3 依赖清单:Worker(Python)依赖含 `alibabacloud-nls20180628` | `docs/v1.0.0 prd/tech-spec.md:562 @ 5927f36` | Worker 声明依赖中**无**该包;NLS filetrans 实际经 legacy `aliyun-python-sdk-core`(AcsClient/CommonRequest POP 形态)调用且该包未列入文档清单 | `apps/worker/pyproject.toml:8-15 @ 5927f36`(无 nls20180628,有 aliyun-python-sdk-core)、`apps/worker/src/soniscope_worker/nls.py:441-448,454-455 @ 5927f36`(引 HYP-18 证据行) | drift → F-DOC-02 |
| T-30 | §6.3 依赖清单:FC(Python)= 标准库 WSGI + `alibabacloud-sts20150401` + `alibabacloud-oss-v2`;部署侧 `alibabacloud-fc20230330` 不随函数打包 | `docs/v1.0.0 prd/tech-spec.md:560-561,600 @ 5927f36` | 两函数 requirements 与用途一致(issue: sts20150401 + tea-openapi;verify: oss-v2);fc20230330 仅 fc_deploy 使用不入 requirements——清单少列 sts SDK 配套客户端 tea-openapi,属完整性小疏漏非误导,登记不立发现 | `apps/fc/issue_credential/requirements.txt:3-4 @ 5927f36`、`apps/fc/verify_upload/requirements.txt:3 @ 5927f36`、`apps/worker/src/soniscope_worker/fc_deploy.py:13 @ 5927f36` | agree |
| T-31 | §6.3.1 测试音频:二进制不进 git、存 OSS sample/ 前缀、清单 tests/audio/fixtures.manifest.json、4 文件 sha256 表 | `docs/v1.0.0 prd/tech-spec.md:565-574 @ 5927f36` | 基线 tests/audio/ 仅 .md/.json 无二进制;manifest 4 条 sha256 与文档表逐字符一致;时长标称差(54s 文件标 ≈60s)系 manifest 自文档化约定(sha256 为唯一权威) | `git show 5927f36:tests/audio/fixtures.manifest.json`(4 sha256 逐一比对同值)、`git ls-tree -r 5927f36 tests/audio/` | agree |
| T-32 | §6.4 部署机制:打包落 build/fc/、部署前备份 build/fc/backup/<ts>/、部署日志含 zip sha256 + curl 存活、rollback-fc 从最新备份恢复、2xx 才算通过 | `docs/v1.0.0 prd/tech-spec.md:576-588 @ 5927f36` | fc_deploy build/fc/ 根、backup_dir、find_latest_backup、curl 存活验证与能力面五项(引 HYP-04 证实行) | `apps/worker/src/soniscope_worker/fc_deploy.py:185-190,208-216,236 @ 5927f36`、`fc_deploy.py:106-119 @ 5927f36` | agree |
| T-33 | §6.5 make target 清单(30 具名 target 表 + test-* 约定式命名) | `docs/v1.0.0 prd/tech-spec.md:602-640 @ 5927f36` | Makefile 45 目标覆盖表内全部具名项(同 P-25 抽查行号);oss-delete-obj 标"仅测试用"与红线说明同款注释在案 | `Makefile:35,41,50,119,140,143 @ 5927f36` | agree |
| T-34 | §6.7 前端 8 状态机与迁移规则(verified 唯一正常终态、手动重新 verify 可回 pending_verify) | `docs/v1.0.0 prd/tech-spec.md:653-687 @ 5927f36` | 8 状态常量与迁移语义同实现(queue_runtime 承载手动重传/重新 verify 迁移) | `apps/miniprogram/utils/upload_queue.js:9-27 @ 5927f36`、`utils/queue_runtime.js:2 @ 5927f36` | agree |
| T-35 | §6.8 成本可观测日志:`asr_call_completed` 结构化行九字段(fragment_id/audio_duration_seconds/elapsed_seconds/provider/model/estimated_cost_yuan/cumulative_calls_today/cumulative_duration_today_seconds) | `docs/v1.0.0 prd/tech-spec.md:689-714 @ 5927f36` | 构造函数返回 dict 字段与文档九字段逐一同名同序 | `apps/worker/src/soniscope_worker/nls.py:165-181 @ 5927f36` | agree |
| T-36 | 【HYP-16 半句专项】tech-spec 对单机单用户容量边界的声明:§1.3 状态机以硬盘真实文件为权威(:41)、§1.4 本地文件状态机保证重启/中断恢复(:49)、§4.0 OPENID_ALLOWLIST"单用户填 1 个"(:341)、§4.5 allowlist 环境变量硬编码(:461) | `docs/v1.0.0 prd/tech-spec.md:41,49,341,461 @ 5927f36` | 代码侧引 HYP-16 既有证据(不重复采证):单线程轮询、本地盘权威、重启按硬盘状态续(`poller.py:378-391`、`pipeline.py:15-18` @ 5927f36);allowlist 单点判定(`auth.py:33-36 @ 5927f36`,引 HYP-09)——tech-spec 未声明超出单机单用户实态的能力 | 引 HYPOTHESES.md HYP-16/HYP-09 证据行 | agree → HYP-16(半句;销号引 HANDOFF-PHASE4.md DOC 节第 1 条;runbook 侧同口径核对留 04-04) |

**tech-spec 节机械对账:** 清单条目总数 **36**(T-01 ~ T-36);四态计数:agree **32**(内含闭环 DNF-01 ×1、DNF-02 ×1、→ HYP-16 结论行 ×1)+ drift **2**(T-27 → F-DOC-01、T-29 → F-DOC-02)+ dead-ref **1**(T-05 → HYP-02 登记)+ 无法静态核实 **1**(T-28);复算:32 + 2 + 1 + 1 = 36 ✓。

**两节合计:** P 30 + T 36 = **66** 条销号;dead-ref 登记共 **3** 处(P-26、P-27、T-05,其中 → HYP-02 2 处)待 04-05 聚合;drift 发现级 **2** 条已立 F-DOC-01/F-DOC-02(见 findings/docs-config.md)。
