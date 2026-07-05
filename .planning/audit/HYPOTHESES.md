# 未验证假设清单

**Created:** 2026-07-04
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

## 转换对账

**29 条 CONCERNS.md 粗体线索 = 4 条 DNF 预录入(见 `.planning/audit/DO-NOT-FIX.md`)+ 25 条 HYP;另加 1 条 Known Bugs 显式"无线索"记录(不计入 29)。**

- 机械计数命令:`grep -cE '^\*\*[^*]+:\*\*$' .planning/codebase/CONCERNS.md` → **29**
- 本文件核对:`grep -c '^### HYP-' .planning/audit/HYPOTHESES.md` → **25**;`grep -c '^### DNF-' .planning/audit/DO-NOT-FIX.md` → **4**;25 + 4 = 29 ✓
- 勘误:01-RESEARCH.md 初版曾统计为 30 条,系 Fragile Areas 节误计为 6(实为 5);以上述机械计数 29 为准。

每条 HYP 是**线索不是答案**:只转写为可证实/证伪的陈述,不下结论。Phase 4(AUDIT-05)逐条回填状态(证实/证伪/细化),本清单与 DO-NOT-FIX.md 共同喂 RPT-08 可追溯映射表。转写 Security 类条目只引位置与模式名,不复制任何秘密值本体。

---

## Tech Debt

### HYP-01: FC-direct transcription decided but not implemented (largest open item)

- **来源:** CONCERNS.md §Tech Debt / FC-direct transcription decided but not implemented (largest open item)
- **假设:** 基线上 `apps/fc/` 仅存在 `issue_credential/` 与 `verify_upload/` 两个函数目录,已决策为主转写路径的 `transcribe_audio/` 无任何代码,已决策架构与已部署架构在基线处分叉。
- **待验证维度:** CODE
- **状态:** 未验证
- **备注:** 与 §Missing Critical Features 首条(HYP-20)同根,互以 ID 关联。

### HYP-02: Authoritative docs moved but deletions uncommitted and references stale

- **来源:** CONCERNS.md §Tech Debt / Authoritative docs moved but deletions uncommitted and references stale
- **假设:** `AGENTS.md`(及 `docs/fc-transcribe-design.md` 等多份文档)仍以旧路径引用 `docs/PRD_v1.md`、`docs/tech-spec.md`、`docs/deployment-guide.md`,而内容已迁至 `docs/v1.0.0 prd/` 与 `docs/runbook/`,权威文档链存在死链。
- **待验证维度:** DOC
- **状态:** 未验证
- **备注:** 条目中"deletions uncommitted"半句已被基线核实推翻(钉定时工作树干净、删除已随提交入库,见 CHARTER 基线章节);待验证的仅是"引用失效"半句。

### HYP-03: Pure-JS SHA-256 on the recording thread

- **来源:** CONCERNS.md §Tech Debt / Pure-JS SHA-256 on the recording thread
- **假设:** `apps/miniprogram/utils/sha256.js` 为纯 JS 实现并在主线程对完整音频字节哈希(最长 10 分钟分片),在低端设备上会造成 UI 卡顿,且与 AGENTS.md 的 wasm-crypto 处方不符。
- **待验证维度:** CODE
- **状态:** 未验证

### HYP-04: FC deploy tooling only supports code updates

- **来源:** CONCERNS.md §Tech Debt / FC deploy tooling only supports code updates
- **假设:** `fc_deploy.py` 仅实现 `update_code`;函数创建、OSS 事件触发器、env 配置、域名登记均为一次性手工 runbook 步骤,环境重建/灾备完全依赖 runbook 保真度。
- **待验证维度:** TOOL
- **状态:** 未验证
- **备注:** CONCERNS.md 自评可接受("Acceptable for single-developer MVP"),待 Phase 3/4 核实该判断是否成立(RESEARCH A4 分流依据)。

### HYP-05: Vendored Aliyun FC sample repository committed

- **来源:** CONCERNS.md §Tech Debt / Vendored Aliyun FC sample repository committed
- **假设:** `docs/example/start-fc-main/` 为 29 MB、1,003 个跟踪文件的完整 vendored 副本,造成仓库膨胀、grep 噪声与误导性搜索命中。
- **待验证维度:** DOC
- **状态:** 未验证
- **备注:** 存在级问题(D-09):不逐文件审计,预计定级 LOW/INFO。

### HYP-06: Quadruplicated agent tooling directories

- **来源:** CONCERNS.md §Tech Debt / Quadruplicated agent tooling directories
- **假设:** GSD/agent 脚手架在 `.claude/`、`.cursor/`、`.codex/`、`.agents/` 四处重复,四份副本独立漂移,单处修复会静默遗漏其余三处。
- **待验证维度:** DOC
- **状态:** 未验证
- **备注:** 存在级问题(D-09):不逐文件审计,预计定级 LOW/INFO。

## Known Bugs

**已检查,无已知 bug 线索。** CONCERNS.md 原文:"None detected in application code" — `apps/` 源码无 TODO/FIXME/HACK 标记(仅有关于临时文件/占位桩的描述性注释),三套测试套件显式覆盖崩溃恢复、故障注入与幂等路径。本条为显式负向记录,不设 HYP 编号、不计入 29 条对账,喂 RPT-08 的"已检查,无发现"显式行。

## Security Considerations

### HYP-07: Committed presigned OSS URL with STS token

- **来源:** CONCERNS.md §Security Considerations / Committed presigned OSS URL with STS token
- **假设:** `scripts/test_asr.py` 的 `DEFAULT_FILE_LINK`(约 80 行,以 `git show 5927f36` 核实为准)内嵌符合 `OSSAccessKeyId=TMP.*` 模式的 STS 预签名 GET URL;token 已过期(Expires 时间戳 2026-05-29 已过)但入库先例使签名 URL 泄露常态化。
- **待验证维度:** TOOL
- **状态:** 未验证
- **备注:** 本条只引位置与模式名,不复制任何签名/token 值本体(含已过期值)。

### HYP-08: Long-term credentials in FC env vars and local config.yaml

- **来源:** CONCERNS.md §Security Considerations / Long-term credentials in FC env vars and local config.yaml
- **假设:** `WX_APP_SECRET`、`ALIYUN_AK_ID`/`ALIYUN_AK_SECRET`、`RAM_ROLE_ARN` 以 FC 函数环境变量存放,Worker 侧 OSS/NLS 密钥明文存于 `$SONISCOPE_HOME/config.yaml`;CONCERNS.md 评现有缓解(`is_sensitive` 日志洗涤、`MaskedSecret`、600 权限校验)为 "Strong",该评价待核实。
- **待验证维度:** CODE
- **状态:** 未验证

### HYP-09: Single-user auth via openid allowlist

- **来源:** CONCERNS.md §Security Considerations / Single-user auth via openid allowlist
- **假设:** 授权仅为 `OPENID_ALLOWLIST` 字符串成员判定,无会话、无限流、无按用户隔离;CONCERNS.md 评 STS 爆炸半径受 `single_key_policy` 严格约束(单 key、仅 PutObject、≤900 s)故可接受,该判断待核实。
- **待验证维度:** CODE
- **状态:** 未验证
- **备注:** CONCERNS.md 自评可接受("Acceptable and explicit for the personal-use MVP"),待 Phase 3/4 核实该判断是否成立(RESEARCH A4 分流依据)。

## Performance Bottlenecks

### HYP-10: Worker processes fragments sequentially in one process

- **来源:** CONCERNS.md §Performance Bottlenecks / Worker processes fragments sequentially in one process
- **假设:** Worker 轮询循环对每个片段串行执行下载→ffmpeg 转码→同步轮询 NLS(5 s 间隔)后才处理下一片段,单进程单线程构成吞吐上限。
- **待验证维度:** CODE
- **状态:** 证实 — 单进程单线程串行处理属实:每轮对 to_download 逐条 for 循环同步执行下载→标准化→同步转写(NLS 5 s 轮询),主循环单线程 while + sleep,无任何并发原语。
- **证据:** `apps/worker/src/soniscope_worker/pipeline.py:407-441 @ 5927f36`(单轮串行 for 循环,transcribe 同步调用)、`pipeline.py:485-506 @ 5927f36`(单线程主循环)、`apps/worker/src/soniscope_worker/nls.py:327 @ 5927f36`(`sleep(NLS_POLL_INTERVAL_SECONDS)` 同步轮询)、`apps/worker/src/soniscope_worker/poller.py:378-391 @ 5927f36`(poll_loop 单线程)
- **备注:** CONCERNS.md 自评 deliberate MVP choice 经 D-10 上线语境裁定**成立**:个人单用户场景片段到达率低,串行吞吐上限远未触及,单线程换取磁盘文件状态机免锁简单性是可辩护取舍——记 RPT-06 优点候选兼 DNF 候选,不占发现 ID(D-12)。03-03 回填。

### HYP-11: FC-direct will pay for NLS poll wait time

- **来源:** CONCERNS.md §Performance Bottlenecks / FC-direct will pay for NLS poll wait time
- **假设:** 规划中的 `transcribe-audio` 函数在 FC 调用内轮询 NLS(设计 §3.3),FC 计费将包含每片段 1–3 分钟的空转等待。
- **待验证维度:** DOC
- **状态:** 未验证
- **备注:** 涉 FC 直转目标态设计,属章程排除项(契约审计不引入目标态基准),预计 Phase 4 以"细化:范围外"关闭。

### HYP-12: `wsgiref.simple_server` as the FC custom runtime server

- **来源:** CONCERNS.md §Performance Bottlenecks / `wsgiref.simple_server` as the FC custom runtime server
- **假设:** `apps/fc/shared/app.py` 以 `wsgiref` `ThreadingWSGIServer` 承载 FC 自定义运行时,无请求限制、HTTP 健壮性最小化。
- **待验证维度:** CODE
- **状态:** 未验证
- **备注:** CONCERNS.md 自评可接受("Fine for MVP"),待 Phase 3/4 核实该判断是否成立(RESEARCH A4 分流依据)。

## Fragile Areas

### HYP-13: Duplicated fragment_id ↔ object_key contract logic

- **来源:** CONCERNS.md §Fragile Areas / Duplicated fragment_id ↔ object_key contract logic
- **假设:** `recordings/<YYYY-MM-DD>/<fragment_id>.wav` 契约在 FC(`fc_shared/sts.py`)、Worker(`oss_admin.py`/`poller.py`)、小程序(`utils/audio.js`)三处独立实现;三处现状是否互相一致待逐字段对照,且无单一跨组件契约测试兜底(失配后果:上传对 Worker 静默永久不可见)。
- **待验证维度:** CON
- **状态:** 未验证

### HYP-14: `ENV = 'development'` hardcoded in miniprogram config

- **来源:** CONCERNS.md §Fragile Areas / `ENV = 'development'` hardcoded in miniprogram config
- **假设:** `apps/miniprogram/config.js` 的 `ENV` 常量硬编码为 `'development'`,生产发布依赖手工翻转一处常量;该常量现值、发布清单与文档对其的口径是否一致待验证(带 `development` 上线会向最终用户暴露开发者菜单与故障注入开关)。
- **待验证维度:** DOC
- **状态:** 未验证

### HYP-15: Home-grown miniprogram lint instead of ESLint

- **来源:** CONCERNS.md §Fragile Areas / Home-grown miniprogram lint instead of ESLint
- **假设:** `miniprogram_lint.py` 自研 Python 静态检查器只捕获被教会的规则,ESLint 级别的缺陷类(未使用变量、作用域问题等)在小程序 JS 中静默通过。
- **待验证维度:** TOOL
- **状态:** 未验证

## Scaling Limits

### HYP-16: Single machine, single user, poll-based

- **来源:** CONCERNS.md §Scaling Limits / Single machine, single user, poll-based
- **假设:** 单 Mac 单 Worker、单白名单 openid、轮询式架构:Worker 离线即无转写(音频滞留 OSS 待重启补齐),本地盘为权威存储且无副本(盘毁则转写全失,音频可自 OSS 重下),该容量边界与文档声明的一致性待核实。
- **待验证维度:** CODE
- **状态:** 细化 — 代码实态半句证实(单机单进程轮询、离线即滞留、本地盘权威且无副本);"与文档声明的一致性"半句属 Phase 4 DOC,已移交(HANDOFF-PHASE4.md DOC 节),本计划未核对文档侧。
- **证据:** `apps/worker/src/soniscope_worker/poller.py:378-391 @ 5927f36`(单线程轮询循环,Worker 离线即无扫描)、`poller.py:395-407 @ 5927f36`(RealOssSource 单 config 单桶,无多实例协调)、`apps/worker/src/soniscope_worker/pipeline.py:15-18 @ 5927f36`(docstring:对象永不删除,重启按硬盘状态续,音频可自 OSS 重下补全)
- **备注:** CONCERNS.md 自评可接受经 D-10 上线语境裁定**成立**:音频有 OSS 长期备份、转写产物可经 retranscribe 自 OSS 重建,盘毁仅损失转写成本而非录音数据,个人 MVP 边界可辩护——记 RPT-06 优点候选兼 DNF 候选,不占发现 ID。持久失败对象的无界重试面另立 F-CODE-02(关联本条)。03-03 回填。

### HYP-17: No FC rate limiting or quota per openid

- **来源:** CONCERNS.md §Scaling Limits / No FC rate limiting or quota per openid
- **假设:** `issue-credential` 对每个合法请求签发一份 STS、无上限;被攻陷的白名单客户端可无限刷上传(单对象仍受 50 MB `MAX_UPLOAD_BYTES` 约束)。
- **待验证维度:** CODE
- **状态:** 未验证

## Dependencies at Risk

### HYP-18: `aliyun-python-sdk-core` (legacy SDK) in `scripts/test_asr.py`

- **来源:** CONCERNS.md §Dependencies at Risk / `aliyun-python-sdk-core` (legacy SDK) in `scripts/test_asr.py`
- **假设:** 手工 ASR 探针脚本使用已弃代 Aliyun SDK(`AcsClient`),与 Worker 正式路径的 `alibabacloud-*` v2 SDK 并存两代 SDK 理解成本;仅脚本级影响、不随 Worker/FC 打包。
- **待验证维度:** TOOL
- **状态:** 未验证

### HYP-19: `alibabacloud-nls20180628` / NLS filetrans API (2018 vintage)

- **来源:** CONCERNS.md §Dependencies at Risk / `alibabacloud-nls20180628` / NLS filetrans API (2018 vintage)
- **假设:** 整条转写路径(现 Worker、未来 FC 直转)依赖 2018-08-17 版 NLS 录音文件识别 API,若 Aliyun 弃用则管线搁浅;`Transcriber` Protocol 对引擎的隔离是否足以支撑替换待核实。
- **待验证维度:** CODE
- **状态:** 证实 — 2018 版 API 依赖属实(filetrans 2018-08-17 + legacy aliyunsdkcore AcsClient 承载 oss-url 主路径);Protocol 隔离经核实**充分**:业务流程仅依赖 Transcriber Protocol,引擎替换只需新实现类 + 工厂分支 + config.yaml 改名,不动流水线。
- **证据:** `apps/worker/src/soniscope_worker/verify_prep.py:87 @ 5927f36`(`NLS_FILETRANS_VERSION = "2018-08-17"`)、`apps/worker/src/soniscope_worker/nls.py:454-455 @ 5927f36`(filetrans 域名 + 版本消费点)、`verify_prep.py:775-776 @ 5927f36`(legacy `aliyunsdkcore` AcsClient/CommonRequest)、`apps/worker/src/soniscope_worker/transcriber.py:81-90,168-183 @ 5927f36`(Transcriber Protocol + 工厂分发,隔离面)
- **备注:** 弃用风险为外部依赖风险(Aliyun 侧不可控),代码级无发现(COVERAGE nls.py/transcriber.py 行"无发现");Transcriber/NlsBackend 双层 Protocol 分层记 RPT-06 优点候选。direct 降级模式(FlashRecognizer)走独立网关端点(`nls.py:507 @ 5927f36`),filetrans 弃用时可作短期退路。03-03 回填。

## Missing Critical Features

### HYP-20: `transcribe-audio` FC function (decided, unbuilt)

- **来源:** CONCERNS.md §Missing Critical Features / `transcribe-audio` FC function (decided, unbuilt)
- **假设:** 已决策的主转写路径 `transcribe-audio` 无任何代码,阻塞 FC 直转架构的部署阶段验收与"常开本地 Worker 退出热路径"。
- **待验证维度:** CODE
- **状态:** 未验证
- **备注:** 与 §Tech Debt 首条(HYP-01)同根,互以 ID 关联。

### HYP-21: Transcript consumption/display

- **来源:** CONCERNS.md §Missing Critical Features / Transcript consumption/display
- **假设:** 转写产物(本地 `transcript.txt`/`transcript.json` 或切换后的 OSS `transcripts/*.md`)无任何读取 UI;CONCERNS.md 称此为明示 MVP 范围外(无日稿展示、无 LLM 润色),该定位与 PRD 范围声明的一致性待核实。
- **待验证维度:** DOC
- **状态:** 未验证

## Test Coverage Gaps

### HYP-22: No automated cross-component E2E without manual WeChat codes

- **来源:** CONCERNS.md §Test Coverage Gaps / No automated cross-component E2E without manual WeChat codes
- **假设:** 真实小程序→FC→OSS→Worker 链路需手工传入新鲜 `wx.login` code(`make test-fc-live CODE=...`),CI 无法运行活体路径,微信认证握手或线上 FC 配置的回归只能在手工验收时暴露。
- **待验证维度:** TEST
- **状态:** 未验证

### HYP-23: FC `handler.py` files outside mypy strict

- **来源:** CONCERNS.md §Test Coverage Gaps / FC `handler.py` files outside mypy strict
- **假设:** 两个面向公网的 WSGI 入口 `handler.py` 无类型级检查;`apps/fc/tests/` 行为测试对该缺口的补偿是否充分待核实。
- **待验证维度:** TEST
- **状态:** 未验证
- **备注:** 豁免本身系故意设计,见 DO-NOT-FIX.md DNF-03(两侧以 ID 交叉引用);本条**仅**验证"行为测试补偿充分"这一判断,不质疑豁免本身。

### HYP-24: Miniprogram page-level code (`pages/index/index.js`, 796 lines) tested only via extracted pure modules

- **来源:** CONCERNS.md §Test Coverage Gaps / Miniprogram page-level code (`pages/index/index.js`, 796 lines) tested only via extracted pure modules
- **假设:** 页面文件中的 wx-API 胶水层(录音回调、storage IO、showModal 流程)无自动化测试,node 测试仅覆盖其委托的纯 `utils/` 模块;页面与 utils 之间的接线缺陷只能真机暴露。
- **待验证维度:** TEST
- **状态:** 未验证

### HYP-25: `scripts/` excluded from lint/typecheck

- **来源:** CONCERNS.md §Test Coverage Gaps / `scripts/` excluded from lint/typecheck
- **假设:** `scripts/test_asr.py`(355 行)与 `scripts/fetch_test_fixtures.py` 在 `pyproject.toml` 的 mypy/ruff 范围之外,静态质量无门禁。
- **待验证维度:** TEST
- **状态:** 未验证

---

*未验证假设清单: 2026-07-04(25 条 HYP + 1 条 Known Bugs 显式无线索记录;对账 25 + 4 DNF = 29,Phase 4 AUDIT-05 逐条回填)。回填进度:已回填 3 条(HYP-10 证实、HYP-16 细化、HYP-19 证实,03-03,2026-07-05),余 22 条未验证。*
