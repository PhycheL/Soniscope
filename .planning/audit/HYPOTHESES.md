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
- **状态:** 证实 — 基线 apps/fc 仅两函数目录,transcribe_audio 零代码,现役转写路径完全在 Worker 侧(nls filetrans)。
- **证据:** `git ls-tree 5927f36 apps/fc` → 仅 issue_credential/、verify_upload/、shared/、tests/ 与 README.md(无 transcribe_audio/);现役转写主路径 `apps/worker/src/soniscope_worker/nls.py:454-455 @ 5927f36`(filetrans 域名+版本消费点)、`apps/worker/src/soniscope_worker/transcriber.py:168-183 @ 5927f36`(工厂仅 cloud-speech/whisper-local 两分支,无 FC 直转实现)
- **备注:** 与 §Missing Critical Features 首条(HYP-20)同根,互以 ID 关联。架构分叉系已知决策落差而非代码缺陷,按 D-12 存在级处理不占发现 ID,供 RPT 汇总呈现(实现属 XL 档,CHARTER 工作量分档示例即此项)。03-04 回填。

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
- **状态:** 细化 — "纯 JS 实现 + 主线程全量字节同步哈希"半句证实(静态主判据);"低端设备 UI 卡顿"半句获微基准方向性支持但未经真机验证(Mac 环境非真机,量级参考);"与 wasm-crypto 处方不符"半句属实但系 docstring 自述的本期取舍而非未声明漂移。
- **证据:** 静态主判据:`apps/miniprogram/utils/sha256.js:9-18,66-135 @ 5927f36`(手写 K 表 + hashWords 同步实现,无任何异步/分块让出;padding 阶段整段复制输入 `:76-77`,峰值内存约 2× 音频字节)、`apps/miniprogram/pages/index/index.js:30,640 @ 5927f36`(调用链:require → 主线程 `sha256Hex(buf)`,输入为 readFileSync 全量音频字节;单条 `:630-645`、长录音逐片 `:582`)、数据量级 = 600 s 分片阈值下典型 ≈10 MB、上限 50 MB(`apps/miniprogram/config.js` 阈值 + FC MAX_UPLOAD_BYTES);取舍自述 `sha256.js:4-5 @ 5927f36`("本期先用纯 JS……wasm 化属后续性能优化")。微基准辅助证据(**Mac 环境非真机,量级参考**):`scans/microbench-sha256.md`——10 MiB 中位 136.5 ms、50 MiB 中位 682.7 ms(≈73 MB/s,O(n) 线性),真机低端设备按引擎差距推断进入秒级可感知卡顿区间。
- **备注:** 性能面不立独立发现:docstring 自述本期纯 JS 取舍(wasm 属后续优化),失败模式为保存路径 UI 卡顿而非数据丢失,个人单用户 MVP 语境(D-10)下属可辩护取舍——记 RPT-06/加固候选(wasm-crypto 或分块异步化),不占发现 ID(D-12);正确性有测试锁定(`apps/miniprogram/test/ids.test.js:139-163 @ 5927f36`,已知向量 + node crypto 随机字节对照)。与 D14-1(sha256 跨语言双实现债务)分立判断:本条裁性能疑点,重复实现债务的三要素裁定见 COVERAGE 深挖点登记 D14-1 行(结论:结构必然,不构成债务)。03-07 回填(D-16 微基准)。

### HYP-04: FC deploy tooling only supports code updates

- **来源:** CONCERNS.md §Tech Debt / FC deploy tooling only supports code updates
- **假设:** `fc_deploy.py` 仅实现 `update_code`;函数创建、OSS 事件触发器、env 配置、域名登记均为一次性手工 runbook 步骤,环境重建/灾备完全依赖 runbook 保真度。
- **待验证维度:** TOOL
- **状态:** 证实 — 部署工具能力面确为"备份/打包/仅代码更新/回滚/日志诊断"五项,无函数创建/触发器/env 配置/域名登记任何入口;环境重建依赖 runbook 保真度属实。
- **证据:** `apps/worker/src/soniscope_worker/fc_deploy.py:13 @ 5927f36`(docstring 自述"部署只更新代码包,不改 FC 环境变量/触发器/运行时规格/公网 URL")、`fc_deploy.py:106-119 @ 5927f36`(FcApi Protocol 全部 6 方法:download_code/env_var_names/install_deps/update_code/curl/fetch_logs,无 create/config 面)、`fc_deploy.py:667-672 @ 5927f36`(update_code 显式只传 UpdateFunctionInput(code=...),行内注释"只更新代码,不传 environment_variables / triggers / 运行规格")、`fc_deploy.py:611 @ 5927f36`("疑似首次部署"错误文案佐证首次创建不在工具能力内)
- **备注:** CONCERNS.md 自评可接受经 D-10 上线语境裁定**成立**:两函数已部署在线,工具完整覆盖高频操作(代码更新+备份+回滚+存活验证),一次性 setup 已完成;灾备重建依赖 runbook 保真度的口径核对属 Phase 4 DOC(runbook 审计)——记 RPT-06 优点候选兼 DNF 候选,不占发现 ID(D-12)。同模块顺带发现 F-TOOL-02(备份失败不阻断部署)独立立项,不影响本条裁定。03-05 回填。

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
- **状态:** 证实 — DEFAULT_FILE_LINK 确为已提交的带签名 OSS 预签名 GET URL(`OSSAccessKeyId=` 签名 URL 模式 + `Signature=` 签名参数模式同行双命中,AccessKeyId 为 TMP. 前缀 STS 临时凭证形态),过期状态可由 URL 内 `Expires=` unix 时间戳参数静态判定(对应 2026-05-29,早于审计日 2026-07-05),签名 URL 入库先例成立。
- **证据:** `scripts/test_asr.py:79-81 @ 5927f36`(双模式命中行,值本体略,per CHARTER 秘密红线)、`scripts/test_asr.py:78 @ 5927f36`(行内注释自认"OSS 签名 URL 会过期,过期后请用 --file-link 传新链接")、`scripts/test_asr.py:112-115 @ 5927f36`(--file-link 缺省链回落该常量,NLS_FILE_LINK 环境变量可覆盖)
- **备注:** → F-TOOL-05(MEDIUM,对照 CHARTER"已过期凭证曾入库(泄露习惯风险)"锚定级;非 CRITICAL:值已过期、STS 临时凭证、单对象 GET 范围)。scans/secrets.md #14/#15 销号去向闭环至该 ID。本条证据全程只引位置+模式名,不含任何值本体(含已过期值)。03-06 回填。

### HYP-08: Long-term credentials in FC env vars and local config.yaml

- **来源:** CONCERNS.md §Security Considerations / Long-term credentials in FC env vars and local config.yaml
- **假设:** `WX_APP_SECRET`、`ALIYUN_AK_ID`/`ALIYUN_AK_SECRET`、`RAM_ROLE_ARN` 以 FC 函数环境变量存放,Worker 侧 OSS/NLS 密钥明文存于 `$SONISCOPE_HOME/config.yaml`;CONCERNS.md 评现有缓解(`is_sensitive` 日志洗涤、`MaskedSecret`、600 权限校验)为 "Strong",该评价待核实。
- **待验证维度:** CODE
- **状态:** 细化 — 存放形态半句证实(FC 三组 env 变量 + Worker config.yaml 明文);"Strong" 缓解评价整体成立但有两处细化边界:Worker 600 权限校验在 CLI 侧仅警告不拒载,FC 侧秘密以普通 str 存 dataclass、无 MaskedSecret 同等类型级掩码(防线在 log_event 字段名洗涤 + 调用纪律)。
- **证据:** Worker 侧:`apps/worker/src/soniscope_worker/config.py:31-35 @ 5927f36`(MaskedSecret._display 前后 4 位脱敏)、`config.py:148-150 @ 5927f36`(恰 600 权限判定)、`apps/worker/src/soniscope_worker/cli.py:48-53 @ 5927f36`(权限不符仅警告不拒载);FC 侧:`apps/fc/shared/fc_shared/env.py:16-38 @ 5927f36`(RAM_ROLE_ARN/ALIYUN_AK_ID/ALIYUN_AK_SECRET/WX_APP_SECRET 经环境变量装载)、`env.py:89-91 @ 5927f36`(缺失仅报变量名不含值)、`apps/fc/shared/fc_shared/audit.py:14-31,40-45 @ 5927f36`(is_sensitive 精确名单 + 子串兜底双层洗涤)
- **备注:** 双侧脱敏机制(MaskedSecret / is_sensitive+hash_openid)经核实有效,记 RPT-06 优点候选;两处细化边界按 D-10 上线语境均不构成发现(600 警告方向安全、FC 现有 log 调用点全部只传安全标量),记加固候选不占发现 ID。03-04 回填(合并 03-03 worker 侧采证)。

### HYP-09: Single-user auth via openid allowlist

- **来源:** CONCERNS.md §Security Considerations / Single-user auth via openid allowlist
- **假设:** 授权仅为 `OPENID_ALLOWLIST` 字符串成员判定,无会话、无限流、无按用户隔离;CONCERNS.md 评 STS 爆炸半径受 `single_key_policy` 严格约束(单 key、仅 PutObject、≤900 s)故可接受,该判断待核实。
- **待验证维度:** CODE
- **状态:** 证实 — 业务鉴权确为 allowlist 字符串成员判定单点(无会话/无频控/无按用户隔离);single_key_policy 约束经逐行核实属实:Resource 精确单 object key 无路径通配、仅 oss:PutObject、时效恒为 900 秒。
- **证据:** `apps/fc/shared/fc_shared/auth.py:33-36,50-51 @ 5927f36`(check_allowlist 成员判定即全部业务鉴权)、`apps/fc/shared/fc_shared/sts.py:62-73 @ 5927f36`(single_key_policy 精确单 key、单 Action)、`sts.py:25 @ 5927f36` + `apps/fc/issue_credential/handler.py:79 @ 5927f36`(duration 恒传 STS_MAX_DURATION_SECONDS = 900)
- **备注:** CONCERNS.md 自评可接受经 D-10 上线语境裁定**成立**:个人单用户 MVP,单凭证爆炸半径受单 key policy 严格限定且有 `make test-sts-escape` 实测背书——记 RPT-06 优点候选兼 DNF 候选,不占发现 ID(D-12);"无限流"半句的上线风险面另立 F-CODE-05(关联 HYP-17)。03-04 回填。

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
- **状态:** 证实 — wsgiref ThreadingWSGIServer(daemon threads)承载生产运行时属实,无请求上限/超时/HTTP 加固;健壮性与请求边界实际依托 FC 平台网关(容器无公网直连面)。
- **证据:** `apps/fc/shared/app.py:17-31 @ 5927f36`(ThreadingWSGIServer + make_server + serve_forever 全部运行时形态)、`app.py:27 @ 5927f36`(容器内 0.0.0.0 监听,S104 探针命中经 scans/ruff-extended.md #1 人工核实为 FC 自定义运行时必需形态)
- **备注:** CONCERNS.md 自评可接受("Fine for MVP")经 D-10 上线语境裁定**成立**:FC 网关为唯一公网入口并承担请求限制/超时职责,容器内 wsgiref 只服务平台转发流量,个人量级下无实测瓶颈——记 DNF 候选,不占发现 ID(D-12)。03-04 回填。

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
- **状态:** 细化 — "只捕获被教会的规则"半句证实:规则面仅五族(appid/页面四件套/合法域名+拼写守卫/JSON 可解析/硬编码密钥启发式),零 JS 语义规则,ESLint 级缺陷类结构性静默通过;"静默通过即有漏报实害"半句在基线上证伪:ESLint 量化底数为 0 error / 29 warning 且逐条核实全为仓库惯例误报(无一真实缺陷)。
- **证据:** `apps/worker/src/soniscope_worker/miniprogram_lint.py:65-77,80-104,107-118,182-186,42-46,121-128 @ 5927f36`(规则清单全集五族,逐条行号见 COVERAGE 行备注);量化底数引 `scans/eslint.md` 尾部"HYP-15 量化小结":增量检出 0 error / 29 warning(no-unused-vars ×21 / eqeqeq ×7 / 遗留 eslint-disable ×1,全数误报),两工具规则面完全不重叠;`apps/miniprogram/utils/logger.js:40 @ 5927f36` 遗留 eslint-disable 注释旁证开发期曾预期 ESLint 存在
- **备注:** 覆盖缺口本身按 CHARTER LOW 锚点"lint/typecheck 覆盖缺口"立发现 F-TOOL-04(风险面在未来变更而非存量,修复给双选项:增补语义检查或引入零依赖 eslint 配置);判据遵守 CHARTER 双语言适配——ESLint 是线索底数不是标准。03-05 回填。

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
- **状态:** 证实 — 全链路(handler 与 fc_shared)无任何频控/配额/计数面:每个鉴权通过的 POST 触发一次 AssumeRole 无上限,且每个匿名 POST 在 allowlist 判定前即消耗一次 jscode2session 上游调用(pre-auth 成本面)。
- **证据:** `apps/fc/issue_credential/handler.py:71-81 @ 5927f36`(每合法请求一次 AssumeRole,无计数/窗口/配额判定)、`apps/fc/shared/fc_shared/auth.py:50 @ 5927f36`(code 换 openid 先于 allowlist 判定执行)、`apps/fc/shared/fc_shared/sts.py:91-99 @ 5927f36`(check_size 为唯一按请求约束,仅限单对象 50 MB)
- **备注:** 本条无 CONCERNS 可接受自评,经 03-04 深挖立发现 F-CODE-05(LOW:成本/可用性面,单凭证爆炸半径仍受单 key policy 约束,见 HYP-09)。03-04 回填。

## Dependencies at Risk

### HYP-18: `aliyun-python-sdk-core` (legacy SDK) in `scripts/test_asr.py`

- **来源:** CONCERNS.md §Dependencies at Risk / `aliyun-python-sdk-core` (legacy SDK) in `scripts/test_asr.py`
- **假设:** 手工 ASR 探针脚本使用已弃代 Aliyun SDK(`AcsClient`),与 Worker 正式路径的 `alibabacloud-*` v2 SDK 并存两代 SDK 理解成本;仅脚本级影响、不随 Worker/FC 打包。
- **待验证维度:** TOOL
- **状态:** 细化 — "两代 SDK 并存"半句证实(test_asr.py 全程 legacy AcsClient/CommonRequest POP 形态);"仅脚本级影响、不随 Worker/FC 打包"半句在 Worker 侧证伪:aliyunsdkcore 是 apps/worker 声明的运行时依赖并承载生产转写主路径(nls.py 经 verify_prep._import_nls_core 构造 AcsClient),FC 侧属实(两函数 requirements.txt 均无该包)。
- **证据:** `scripts/test_asr.py:22-23,159,167,174,217 @ 5927f36`(docstring 钉定 `aliyun-python-sdk-core==2.16.0`;AcsClient/CommonRequest 用法)、`apps/worker/pyproject.toml:13 @ 5927f36`(`aliyun-python-sdk-core>=2.16.0` 声明依赖)、`apps/worker/src/soniscope_worker/nls.py:441-448,454-455 @ 5927f36`(生产 oss-url 主路径经 legacy AcsClient 构造 filetrans 请求)、`apps/fc/issue_credential/requirements.txt:3-4` / `apps/fc/verify_upload/requirements.txt:3 @ 5927f36`(FC 依赖清单无 aliyunsdkcore)
- **备注:** 评估以现状互审为基准,不引入弃用时间表判断(03-RESEARCH §State of the Art 口径);生产侧 legacy SDK 证据与 HYP-19 回填同源互引(`verify_prep.py:775-776` 即 `_import_nls_core` 实体)。两代 SDK 并存的理解成本属存量技术债观察,工具级无独立发现(test_asr.py 的发现面在 F-TOOL-05)。03-06 回填。

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
- **状态:** 证实 — transcribe-audio 零代码属实(基线 apps/fc 仅 issue_credential/verify_upload 两函数目录);"常开本地 Worker"现状由 Worker 侧轮询主循环承担全部转写。
- **证据:** `git ls-tree 5927f36 apps/fc` → 无 transcribe_audio/ 目录;现役依赖 `apps/worker/src/soniscope_worker/poller.py:378-391 @ 5927f36`(Worker 单线程轮询为唯一转写驱动)、`apps/worker/src/soniscope_worker/nls.py:454-455 @ 5927f36`(filetrans 消费点)
- **备注:** 与 §Tech Debt 首条(HYP-01)同根,互以 ID 关联,证据同源。缺失系已决策未实现的范围落差,按 D-12 存在级不占发现 ID(实现属 XL 档);"阻塞部署阶段验收"半句属里程碑管理事实,超出代码审计判定范围,原样移交 RPT 汇总。03-04 回填。

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

*未验证假设清单: 2026-07-04(25 条 HYP + 1 条 Known Bugs 显式无线索记录;对账 25 + 4 DNF = 29,Phase 4 AUDIT-05 逐条回填)。回填进度:已回填 14 条(03-03:HYP-10 证实、HYP-16 细化、HYP-19 证实;03-04:HYP-01 证实、HYP-08 细化、HYP-09 证实、HYP-12 证实、HYP-17 证实、HYP-20 证实;03-05:HYP-04 证实、HYP-15 细化;03-06:HYP-07 证实、HYP-18 细化;03-07:HYP-03 细化,2026-07-05)——Phase 3 回填集 14 条(CODE 10:HYP-01/03/08/09/10/12/16/17/19/20 + TOOL 4:HYP-04/07/15/18)累计 14/14 全部闭环 ✓;余 11 条未验证(均属 Phase 4 维度:DOC 6 + TEST 4 + CON 1)。*
