# SoniScope 上线前代码审计报告

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本文件是本审计里程碑的最终报告主文件,覆盖 RPT-01~07 与 RPT-09;机械性长内容(RPT-08 追溯映射表、聚类明细)在附录分文件(D-14),由 05-03 产出并在附录索引章节链入。本报告为纯汇编产物:每个判断类字段(终级严重度、上线判定、聚类、工作包、处置)逐一取自 `.planning/audit/CALIBRATION.md` 已批准记录,组装零新判断;定位类字段(ID、维度、标题、工作量、概要)机械抽取自封版 findings/*.md。

## 方法声明

1. **条目底数与示例剔除:** findings/*.md 五份台账共 45 个 `^### F-` 条目 = **40 条真实发现 + 5 条 `F-*-00` schema 示例**;示例条目自带"Phase 5 汇总时剔除"注记,已剔除出本报告一切计数与表格(现场复核:`grep -hc '^### F-' .planning/audit/findings/*.md | paste -sd+ - | bc` → 45;`grep -h '^### F-' .planning/audit/findings/*.md | grep -vc '\-00:'` → 40)。
2. **汇总表排序规则:** 严重度降序(CRITICAL → HIGH → MEDIUM → LOW → INFO;词表五级齐备,本批 CRITICAL 0 条、HIGH 0 条,空档照常声明)→ 同级内工作量升序(S → M → L → XL,backlog 语义先修便宜的)→ 同级同档内按 ID 稳定排序(维度序 CON → CODE → TOOL → DOC → TEST,per CHARTER 五维度表,再按编号升序)。
3. **终级取值规则:** 某 ID 在 CALIBRATION.md 有调整记录则采用终级并标"经校准";无记录则原级照抄。本批扫描结论为**零拟调整、零并入**(经 D-02 批量呈报、用户 2026-07-05 `approve-all` 批准落账),故 40 条原级即终级,全表无"经校准"标注。
4. **CHARTER schema 字段 8/9 取舍注记:** CHARTER 九字段 schema 的字段 8(上线判定槽)与字段 9(`draft → calibrated` 状态槽)的台账回填预期由 CALIBRATION.md 承载——D-03(后定,locked)压过 schema 字面预期;findings/*.md 的上线判定槽与状态槽保持 as-built 封版不回写,一切终态以 CALIBRATION.md 与本报告为准。

**附加纪律:** 本报告不复制九字段全文与任何证据片段,每条发现只占表行 + 一句概要,详情一律链回封版 findings/*.md(D-15;链回映射见发现汇总表图例)。证据引用格式恒为 `path:line @ 5927f36`;秘密类证据只写位置与模式名,绝不复制值本体(CHARTER 秘密红线)。全文禁数值化质量评分与小时级工时估计(REQUIREMENTS Out of Scope),严重度只用五级词表、工作量只用 S/M/L/XL 档。

## 执行摘要

**审计缘由与范围:** SoniScope 处于部署上线阶段;本里程碑不新增功能、不修复代码,对基线 `5927f36` 的现有代码做一次全面审计,产出本份结构化审计报告作为正式对外上线前的把关(修复留给下一个里程碑)。审计范围为 CHARTER 定稿的五个维度:契约一致性(CON)、组件代码(CODE)、部署与验证工具链(TOOL)、文档配置一致性(DOC)、测试质量与覆盖(TEST);契约一致性以小程序、FC、Worker 三处实现的现状互相对照为准。**明确排除项**(CHARTER 范围与方法章节):FC 直转目标态对照(`docs/fc-transcribe-design.md`,切换障碍分析归 FC 直转切换里程碑)、渗透测试级安全审计、逐行审计 vendored `docs/example/start-fc-main/`、数值化质量评分、精确工时估计;另有 9 条扫描排除路径(vendored 仓/四套 AI 工具目录/scripts/ralph 等),但秘密/凭证扫描穿透全部排除目录。报告语言约定(RPT-09):中文正文 + 英文 ID/严重度/判定词/工作量档。

**按终级严重度的发现计数(现场 grep 实测,2026-07-05 实跑照录):**

```
$ grep -hc '^### F-' .planning/audit/findings/*.md | paste -sd+ - | bc
45
$ grep -h '^### F-' .planning/audit/findings/*.md | grep -vc '\-00:'
40
$ (以 ^### F- 为锚逐条 awk 抽取严重度字段,剔除 5 条 -00 示例)
MEDIUM 11 / LOW 26 / INFO 3(CRITICAL 0 / HIGH 0)
```

叠加 CALIBRATION.md 已批准的校准记录(调整 0 条、并入 0 条)后,终级分布与原级一致:**40 条真实发现 = CRITICAL 0 / HIGH 0 / MEDIUM 11 / LOW 26 / INFO 3**;工作量分布 S 32 / M 7 / L 1 / XL 0。无真实 CRITICAL/HIGH 发现:未发现有效长期凭证泄漏、认证绕过或上线即触发的数据丢失路径。

### 总体上线判定

**CONDITIONAL GO**(条件通过)。

推导链(D-11 机械推导,判定表见 CALIBRATION.md 逐条上线判定表,经 D-12 批准):BLOCKER 0 条、PRE-LAUNCH 3 条 → 命中推导规则第 2 条(无 BLOCKER 且存在 PRE-LAUNCH)→ **CONDITIONAL GO**。

**必做清单(全部 PRE-LAUNCH 条目,首批真实用户前完成):**

- `F-CODE-02`(MEDIUM/M,P-2)——持久性失败对象无计数/隔离/告警,静默失败不可发现;由工作包 WP-03 承载。
- `F-CODE-06`(MEDIUM/M,P-1)——uploading 死态用户可感知却无出口,非作者用户无法自救;由工作包 WP-04 承载。
- `F-DOC-03`(MEDIUM/S,P-1)——发布文档缺 ENV 生产翻转步骤,照做即误发 development 构建;由工作包 WP-07 承载。

其余 37 条全部 POST-LAUNCH,进入修复里程碑按发现汇总表排期,不阻断上线。

**根因聚类叙事(为什么会有这类问题,D-06 分析层,明细见 CALIBRATION.md 根因聚类划分节):** 40 条发现中 29 条归入五个根因簇——`CL-01`(fragment_id/object key 派生与校验逻辑多处独立实现,校验强度不一致)与 `CL-02`(跨端契约镜像常量靠注释约定同步,共享源与对称测试锁定双缺失)同源于双语言/多部署单元下"契约靠约定不靠机制"的结构现状;`CL-03`(失败/异常路径静默化——失败被吞、无计数、无告警、无恢复入口)源于错误路径普遍按"记录即处理"实现、缺失败升级面设计,三条 PRE-LAUNCH 中两条(F-CODE-02/06)出自此簇;`CL-04`(质量门禁声明面与实态失真)源于门禁配置演进滞后于仓库结构而声明层持续按"完整质量闸"表述;`CL-05`(文档叙述滞后于实施进度与文件迁移)源于权威文档迁移与实现推进后声明层未同步修订,第三条 PRE-LAUNCH(F-DOC-03)出自此簇。其余 11 条为无共同根因的孤条。

### 存在级观察与范围外事项

以下五项不占发现 ID(D-12 存在级/范围外口径),逐条回链 `HYPOTHESES.md` 防断链:

- **HYP-01(证实,存在级):** FC 直转转写已决策未实现——基线 `apps/fc/` 仅两函数目录,`transcribe-audio` 零代码,现役转写路径完全在 Worker 侧;实现属 **XL** 档(CHARTER 工作量分档示例即此项)。与 HYP-20 同根。
- **HYP-20(证实,存在级):** `transcribe-audio` FC 函数已决策未建,"常开本地 Worker 退出热路径"未达成;"阻塞部署阶段验收"半句属里程碑管理事实,超出代码审计判定范围,原样呈现。
- **HYP-11(细化,章程范围外):** "FC 直转将为 NLS 轮询等待付费"指向目标态设计(设计 §3.3),CHARTER 明确排除项写定不引入目标态对照——本审计不对该设计内容下判,切换障碍分析归 FC 直转切换里程碑。
- **HYP-18(细化,债务观察):** 两代 Aliyun SDK 并存——legacy `aliyun-python-sdk-core` 实为 Worker 声明的运行时依赖并承载生产转写主路径(非"仅脚本级"),与 `alibabacloud-*` v2 系并存的理解成本作为存量观察呈现,工具级无独立发现(发现面在 F-TOOL-05)。
- **HYP-21(证实,MVP 范围外):** 转写产物无任何读取 UI——与 PRD Non-goals(NG-1/NG-2,"本期不做 LLM 润色、不做日稿展现")口径一致,系明示 MVP 范围外的已决策范围落差。

## 上线判定准则

> 本章准则全文照搬 CALIBRATION.md 已批准定稿——准则依据 D-09(准则先行、逐条套用、判定与严重度独立评)与 D-10(上线语境 = 邀请制小范围真实用户、allowlist 扩容;非作者用户无法自救——不会重录、不看日志;用户可感知的卡死态与无提示失败权重上调;开放注册级滥用/频控风险不按公开口径拔高)定稿,**经 D-12 用户批准(2026-07-05 approve-all),见 CALIBRATION.md 呈报与批准记录节**。

### 判定词表与条款

| 条款 | 判定 | 定义 |
|------|------|------|
| B-1 | BLOCKER | 用户录音数据丢失或不可恢复,且上线即有现实触发路径 |
| B-2 | BLOCKER | 秘密/凭证泄漏,超出 DNF-04 已裁定的受限爆炸半径(单 key/仅 PutObject/≤900s) |
| B-3 | BLOCKER | 主链路(录音→上传→转写产出)对全部用户不可用 |
| P-1 | PRE-LAUNCH | 用户可感知的卡死态/无提示失败,且非作者用户无法自救(D-10 语境:不会重录、不看日志;此类权重上调) |
| P-2 | PRE-LAUNCH | 静默失败不可发现,排障需读代码或云端日志 |
| P-3 | PRE-LAUNCH | 运维者无法从日志/工件判断数据是否安全落地 |
| PL-1 | POST-LAUNCH | 其余全部:代码债、注释/文档漂移、缺测试锁定、开放注册级滥用/频控(D-10 明示不拔高)、INFO/acknowledge 条目 |

命中 B-1/B-2/B-3 任一为 BLOCKER;无 B 命中时,命中 P-1/P-2/P-3 任一为 PRE-LAUNCH;其余一律 PL-1 → POST-LAUNCH。

### D-11 总判定推导规则(机械,三档词)

1. 存在任一 BLOCKER → **NO-GO**
2. 无 BLOCKER 且存在任一 PRE-LAUNCH → **CONDITIONAL GO**(附 PRE-LAUNCH 必做清单,即全部 PRE-LAUNCH 条目 ID)
3. 全部 POST-LAUNCH → **GO**

## 发现汇总表

> 本表 40 行 = 45 条目 − 5 示例;终级含 **0** 条经校准(零调整经批准落账,见 CALIBRATION.md CAL 调整条目节)。本表是修复里程碑的 backlog 主体,也是 REPORT.md 中**唯一**以 `| F-` 开行的表(其他章节的成员引用一律置于单元格内或行内代码,供机械对账)。

**图例:** 终级严重度列 ∈ {CRITICAL, HIGH, MEDIUM, LOW, INFO}(本批仅 MEDIUM/LOW/INFO 出现);上线判定列 ∈ {BLOCKER, PRE-LAUNCH, POST-LAUNCH}(取自 CALIBRATION.md 逐条上线判定表);聚类列 = CL-NN(取自 CALIBRATION.md 根因聚类划分节)或『—』(未入簇孤条);处置列取值 ∈ {进工作包 WP-NN(取自 CALIBRATION.md 修复工作包划分节), 并入 F-XX-NN 处理(D-08 副条,本批 0 条), acknowledge 无需动作(D-07,INFO/良性行)}。详情按维度列链回封版台账,不复制九字段全文与证据片段(D-15):CON → `findings/contract.md`、CODE → `findings/code.md`、TOOL → `findings/toolchain.md`、DOC → `findings/docs-config.md`、TEST → `findings/test.md`。

| ID | 终级严重度 | 维度 | 标题 | 工作量 | 上线判定 | 聚类 | 处置 | 一句概要 |
|-----|-----------|------|------|--------|----------|------|------|----------|
| F-CON-02 | MEDIUM | CON | `buildObjectKeyPreview` 双独立入参 + 本地时区日期推导,可产出目录日期≠前缀日期的 object key | S | POST-LAUNCH | CL-01 | 进工作包 WP-01 | preview key 目录日期与前缀双独立来源可错位;当前上传链(AC#4)不经 preview,一旦复用即触 Worker 静默跳过 |
| F-CON-03 | MEDIUM | CON | key→fragment_id 第四处反推 `fragmentIdFromObjectKey` 无任何校验 | S | POST-LAUNCH | CL-01 | 进工作包 WP-01 | 第四处反推零校验照单全收,与 Worker 返回 None 行为分叉,异常 key 入队时可掩盖数据滞留 |
| F-TOOL-05 | MEDIUM | TOOL | test_asr.py 内置已过期的带签名 OSS 预签名 URL,签名 URL 入库先例成立 | S | POST-LAUNCH | CL-04 | 进工作包 WP-05 | 已过期 STS 预签名 URL 随脚本入库,无现行泄漏面但"签名 URL 可进 git"的惯性风险成立 |
| F-TOOL-06 | MEDIUM | TOOL | `make typecheck` 门禁在仓内结构性恒红(app.py 部署态导入) | S | POST-LAUNCH | CL-04 | 进工作包 WP-05 | mypy strict 门禁必然 exit 1,退出码无法区分旧错与新回归,红灯习惯化后等同无门禁 |
| F-DOC-03 | MEDIUM | DOC | 发布文档未覆盖小程序 config.js ENV 常量的生产翻转步骤 | S | PRE-LAUNCH | CL-05 | 进工作包 WP-07 | 照 deployment-guide 发布流程执行即把 development 门控带上线,体验用户可见开发者菜单并可开启故障注入 |
| F-TEST-03 | MEDIUM | TEST | scripts/ 三文件在全部静态门禁之外,已有违例与已提交签名 URL 实害样本 | S | POST-LAUNCH | CL-04 | 进工作包 WP-05 | scripts/ 变更不经任何静态检查,6 条门禁规则集内违例与 1 处签名 URL 已在 make lint 全绿下入库 |
| F-TEST-04 | MEDIUM | TEST | make 门禁二值信号无守护——JS 桥静默 skip、typecheck 非绿、执行环境依赖三处失真 | S | POST-LAUNCH | CL-04 | 进工作包 WP-05 | 三个独立失真点使门禁退出码不可信:全绿 ≠ 全跑、非绿 ≠ 代码错 |
| F-CODE-02 | MEDIUM | CODE | 持久性失败对象每轮重下重处理,无失败计数、隔离或告警升级面 | M | PRE-LAUNCH | CL-03 | 进工作包 WP-03 | 损坏/异常格式上传后转写永不产出且无告警,用户与运维均不可发现,排障需读 Worker 日志 |
| F-CODE-06 | MEDIUM | CODE | 进程中断残留的 uploading 状态项成为死态(不拾取、无手动入口、不计积压) | M | PRE-LAUNCH | CL-03 | 进工作包 WP-04 | 录完即杀小程序属现实操作,uploading 死态用户可感知却无任何出口,唯一出路删记录即丢录音 |
| F-TEST-05 | MEDIUM | TEST | 跨语言/跨份契约镜像常量与派生函数无对称测试锁定(7 个脆弱区共面) | M | POST-LAUNCH | CL-02 | 进工作包 WP-02 | 双语言镜像契约的一侧漂移不触发任何测试变红,契约失配以运行期错位而非提交期检出暴露 |
| F-TEST-06 | MEDIUM | TEST | 失败/恢复路径行为无测试兜底(6 个脆弱区共面) | M | POST-LAUNCH | CL-03 | 进工作包 WP-03 | 失败注入与恢复面在修复前无回归防线、修复后无验收断言可依,下个里程碑修复时须自带测试面 |
| F-CON-01 | LOW | CON | 小程序 fragment_id 校验缺日期合法性检查(FC/Worker 有,小程序无) | S | POST-LAUNCH | CL-01 | 进工作包 WP-01 | 正则仅形状校验,非法日期 fragment_id 靠 FC 400 唯一拦截;现实路径暂产不出非法值 |
| F-CON-06 | LOW | CON | 上传大小上限 50 MB 无小程序侧镜像常量或上传前预检 | S | POST-LAUNCH | CL-02 | 进工作包 WP-01 | 超限仅在 FC 侧事后 4xx 显式拒绝,用户得不到"文件过大"的可行动提示;600s 分片阈值下现实难触发 |
| F-CODE-01 | LOW | CODE | `process_plan` 声明 `fragments_root` 形参但函数体未使用 | S | POST-LAUNCH | — | 进工作包 WP-03 | 遗留 API 面误导调用方以为函数自带幂等判定,现有调用方行为正确 |
| F-CODE-03 | LOW | CODE | 原子写崩溃窗口残留的 `*.tmp` 孤儿文件无任何清理路径(fragment 目录内) | S | POST-LAUNCH | CL-03 | 进工作包 WP-03 | kill -9 落在毫秒级写入窗口时孤儿 tmp 永久残留;仅目录污染不影响正确性 |
| F-CODE-04 | LOW | CODE | `.env` 解析为不设边界的 CWD 向上搜索,与"仓库根目录 .env"文档口径不符 | S | POST-LAUNCH | — | 进工作包 WP-03 | 脱离 Makefile 从任意 CWD 直跑时祖先目录无关 .env 可静默劫持 SONISCOPE_HOME 解析 |
| F-CODE-05 | LOW | CODE | issue-credential 在 allowlist 之外无任何频控/配额面 | S | POST-LAUNCH | — | 进工作包 WP-09 | STS 签发与 pre-auth 微信上游调用均无上限,属成本/可用性面;D-10 明示不按公开注册口径拔高 |
| F-CODE-07 | LOW | CODE | 重试退避约定(5s/15s/45s、最多 3 次)四处独立落点,Worker 侧数值无字面锁定 | S | POST-LAUNCH | CL-02 | 进工作包 WP-02 | 任一端修改重试节奏不同步其余落点;基线四落点数值一致,漂移后果仅节奏失准 |
| F-CODE-08 | LOW | CODE | 小程序 FC 请求组装在 utils 与 pages 两份同构,仅注释约定同步 | S | POST-LAUNCH | CL-02 | 进工作包 WP-02 | 请求形态改动需人工同步两处,漏改侧收 FC 400 显式失败非静默 |
| F-TOOL-01 | LOW | TOOL | verify-prep STS 越权反例把非拒绝类异常误报为"疑似越权放行"且报告丢弃错误码 | S | POST-LAUNCH | CL-03 | 进工作包 WP-06 | 瞬时网络/SDK 异常被渲染为越权放行,操作者无从区分"策略失效"与"探测失败" |
| F-TOOL-02 | LOW | TOOL | deploy-fc 在预部署备份失败时不阻断部署,任意备份失败均降级为注记 | S | POST-LAUNCH | CL-03 | 进工作包 WP-06 | 备份失败后部署照常执行,被覆盖版本快照缺失,工具内回滚点丢失 |
| F-TOOL-03 | LOW | TOOL | test-verify-upload 向生产 recordings/ 前缀写测试对象,清理失败被静默吞掉 | S | POST-LAUNCH | CL-03 | 进工作包 WP-06 | 残留测试对象契约合法,落入 Worker 无界重试面形成每轮重复失败噪声,操作者不知残留 |
| F-TOOL-04 | LOW | TOOL | 小程序 JS 语义类缺陷无任何静态门禁,miniprogram_lint 规则面与语义检查零重叠 | S | POST-LAUNCH | CL-04 | 进工作包 WP-05 | 语义类缺陷在 make lint 全绿下静默入库;基线经 ESLint 量化为零真实缺陷,风险在未来变更 |
| F-TOOL-07 | LOW | TOOL | Makefile .PHONY 声明幻影目标 lint-miniprogram,按声明名调用即硬错误 | S | POST-LAUNCH | CL-04 | 进工作包 WP-05 | 声明面与实现面不一致;检查能力无缺失(make lint 已含),仅调用口径失效 |
| F-TOOL-08 | LOW | TOOL | 联调工具契约镜像集群(错误码/凭证字段/大小假设/合成 ID)靠注释约定同步,零测试兜底 | S | POST-LAUNCH | CL-02 | 进工作包 WP-02 | fc_shared 契约变更时无测试提醒同步工具侧镜像,漂移后果为工具误 FAIL 或静默欠验证 |
| F-DOC-01 | LOW | DOC | tech-spec 声称前端 sha256 用 wasm-crypto,实态为主线程同步纯 JS 实现 | S | POST-LAUNCH | CL-05 | 进工作包 WP-07 | 权威技术文档对 sha256 实现路径的描述与实态相反,误导性能排查方向 |
| F-DOC-02 | LOW | DOC | tech-spec 依赖清单失实(nls20180628 未装/承载主路径的 legacy SDK 未列) | S | POST-LAUNCH | CL-05 | 进工作包 WP-07 | 依赖清单双向失实,按文档重建环境无法复现转写路径,依赖风险评估整体漏看 |
| F-DOC-04 | LOW | DOC | AGENTS.md 声称未设 SONISCOPE_HOME 时回退 ~/SoniScope,实态无固定兜底直接报错 | S | POST-LAUNCH | CL-05 | 进工作包 WP-07 | 配置加载顺序声明与实态相反且与 tech-spec/deployment-guide 双文档冲突;报错文案本身给出正确指引 |
| F-DOC-05 | LOW | DOC | AGENTS.md 与两份子 README 的"现状/后续 story"叙述滞后于实施进度 | S | POST-LAUNCH | CL-05 | 进工作包 WP-07 | 三处叙述停留在占位/骨架时点,而基线已全量实现;按 README 判断组件成熟度会得出相反结论 |
| F-DOC-06 | LOW | DOC | 权威文档迁移至 `docs/v1.0.0 prd/` 后全仓旧路径引用死链(10 文件 ≈47 处) | S | POST-LAUNCH | CL-05 | 进工作包 WP-07 | AGENTS.md 17 处为主体,权威文档链首两环与两张导航表整体失效,循径寻文一律落空 |
| F-TEST-01 | LOW | TEST | 活体路径(真云鉴权/签发/校验)零自动化覆盖,缺一次性 code 即全 SKIP 且 exit 0 | S | POST-LAUNCH | CL-04 | 进工作包 WP-08 | 发布前若跳过手工联调,真云回归完全失守而工具链不报任何异常;仓库无 CI |
| F-TEST-07 | LOW | TEST | 低危功能缺失面的测试同步义务(6 个脆弱区共面) | S | POST-LAUNCH | — | 进工作包 WP-08 | 义务清单类:单独补测试无被测对象,修复原发现时按反向映射行同步立测试,防止测试再欠账 |
| F-TEST-09 | LOW | TEST | oss_sign 无『raw secret 不出现在表单/policy』负断言 | S | POST-LAUNCH | — | 进工作包 WP-08 | 签名组装若回归为秘密误入表单/policy 明文,现有测试不会变红;当前实现正确 |
| F-TEST-10 | LOW | TEST | 断言强度与测试卫生杂项(5 处聚合) | S | POST-LAUNCH | — | 进工作包 WP-08 | 五处轻量面合计削弱回归灵敏度与重构安全边际,均为维护成本类 |
| F-TEST-02 | LOW | TEST | pages 胶水层为四条流程的选择性驱动,index.js 其余 wx 交互路径无自动化驱动 | M | POST-LAUNCH | — | 进工作包 WP-08 | 录音主流程入口 796 行内未被 harness 驱动的胶水路径回归依赖人工,改动无测试变红信号 |
| F-TEST-08 | LOW | TEST | 手写 fake 与真实实现无行为面对齐锁定(FakeSource/RealOssSource 主证) | M | POST-LAUNCH | — | 进工作包 WP-08 | fake 与真实实现仅经 mypy 结构对齐,行为语义漂移时全部单测继续全绿 |
| F-CON-04 | LOW | CON | verify-upload 不校验 `x-oss-meta-sha256`,完整性确认只覆盖 size/etag | L | POST-LAUNCH | — | 进工作包 WP-03 | 同大小内容损坏可判 verified(假阳性);系 §4.2 文档化设计取舍,Worker sha256 兜底存在(闭环方案 L/保守告警方案 M 双口径,包内按保守口径计) |
| F-CON-05 | INFO | CON | 7 个 FC 错误码字面量在小程序实现代码零出现,经 body.error 通用透传 | S | POST-LAUNCH | CL-02 | acknowledge 无需动作 | 通用透传即 Postel 宽收的容错姿态,当前输入域内无任何行为分叉,良性 |
| F-DOC-07 | INFO | DOC | vendored Aliyun FC 示例仓 1,003 文件 ≈28 MB 整仓入库 | S | POST-LAUNCH | — | acknowledge 无需动作 | 存在级观察:仓库体积膨胀与全仓检索噪声,无运行时影响 |
| F-DOC-08 | INFO | DOC | agent 工具脚手架四目录重复,独立副本已实际漂移 | M | POST-LAUNCH | — | acknowledge 无需动作 | 存在级观察:单处修复会静默遗漏其余三处副本,无运行时影响 |

## 修复工作包

> 工作包为执行层(D-06,取自 CALIBRATION.md 修复工作包划分节):按共同修复位置分组、标依赖,可直接排期;包级工作量档为整体重估(D-04,包内共修一处时总量可小于各条之和)。INFO 条目(`F-CON-05`、`F-DOC-07`、`F-DOC-08`)不进工作包(D-07);本批无并入副条(D-08 判定 0 条)。**包排序用序数规则:先按包内最高终级严重度降序,同级按包级工作量档升序(S → M → L → XL),同级同档按 WP 编号稳定序——严禁折算数字比值(Out of Scope 禁数值评分)。** 据此排序:WP-01/02/03/04/05/07(包内最高 MEDIUM、档 M)→ WP-09(最高 LOW、档 S)→ WP-06/08(最高 LOW、档 M)。

### WP-01: 小程序 utils key/校验/预检族修复

- **成员:** `F-CON-01`、`F-CON-02`、`F-CON-03`、`F-CON-06`(包内最高严重度 MEDIUM)
- **共同修复位置:** `apps/miniprogram/utils/`(audio.js、upload_queue.js、config.js、uploader.js/verify.js 预检)+ 同一 node 测试文件族
- **包级工作量档:** M — 重估理由(D-04):四条各自 S(单文件),但共处同一组件同一测试族,合并实施为"同组件多文件"一档,总量小于 4×S 独立排期。
- **依赖:** 无(建议先于 WP-02 收口,见 WP-02 依赖)。

### WP-02: 契约镜像共享源提取与一致性测试绑定

- **成员:** `F-CODE-07`、`F-CODE-08`、`F-TOOL-08`、`F-TEST-05`(包内最高严重度 MEDIUM)
- **共同修复位置:** `apps/miniprogram/utils/`(共享常量模块、共享 fc_request util)+ `apps/worker/src/soniscope_worker/nls.py` 派生化 + 新增单个契约镜像一致性测试文件(pythonpath 双侧导入)
- **包级工作量档:** M — 重估理由(D-04):单一镜像一致性测试文件即可绑定全集群,共享源提取各为单文件小改;`F-TEST-05` 台账 M 主体即由本包一次性交付,合并后总量 < 各条之和。
- **依赖:** `F-TEST-05` 的 CON 侧四落点断言(`F-CON-01/02/03/06`)随 WP-01 成员修复同步落地,本包收口对账依赖 WP-01 完成。

### WP-03: Worker 失败路径升级面与运行时健壮性

- **成员:** `F-CODE-01`、`F-CODE-02`、`F-CODE-03`、`F-CODE-04`、`F-CON-04`、`F-TEST-06`(包内最高严重度 MEDIUM;含必做清单条目 `F-CODE-02`)
- **共同修复位置:** `apps/worker/src/soniscope_worker/`(poller.py、pipeline.py、audio.py、recovery.py、paths.py)+ 对应 pytest
- **包级工作量档:** M — 重估理由(D-04):主体为 `F-CODE-02`(M);`F-CON-04` 按其台账修复建议的保守告警方案口径与 `F-CODE-02`"同一动作面,可合并实施",包内计 M 而非台账字面 L(若修复里程碑改选闭环方案,`F-CON-04` 移出本包独立跨组件 L 排期);`F-CODE-01/03/04` 为同组件单文件 S 顺带;`F-TEST-06` 测试面随各成员修复分摊。
- **依赖:** 无实现顺序依赖;`F-TEST-06` 六脆弱区断言分摊 WP-03/WP-04/WP-06 三包,收口对账须三包全部完成后执行(挂本包)。

### WP-04: 小程序 uploading 死态恢复

- **成员:** `F-CODE-06`(包内最高严重度 MEDIUM;必做清单条目)
- **共同修复位置:** `apps/miniprogram/utils/queue_runtime.js`、`pages/uploads/uploads.js`、`utils/uploads_view.js` + node 测试(含 uploads_view.test.js:70 既有断言同步翻转,`F-TEST-06` 交叉点)
- **包级工作量档:** M — 台账原档照抄(单包单条不重估)。
- **依赖:** 无。

### WP-05: 静态门禁与质量闸修复

- **成员:** `F-TOOL-04`、`F-TOOL-05`、`F-TOOL-06`、`F-TOOL-07`、`F-TEST-03`、`F-TEST-04`(包内最高严重度 MEDIUM)
- **共同修复位置:** `pyproject.toml`、`Makefile`、`scripts/test_asr.py`(URL 常量移除 + 违例清理)、`apps/worker/tests/test_miniprogram_js.py`(node 缺失 fail)、`apps/worker/src/soniscope_worker/miniprogram_lint.py`(语义/秘密模式扩展)
- **包级工作量档:** M — 重估理由(D-04):六条各自 S(配置级/单文件),但分属门禁配置面的多个文件,合并为一档 M;`F-TEST-03/04` 与 `F-TOOL-05/06` 分别为同一缺陷的门禁面与工具面表达,共修一处(scripts 纳入门禁、typecheck 恢复可绿)同时销两条,总量 < 各条之和。
- **依赖:** 无跨包依赖(`F-TEST-04` 之②依赖同包 `F-TOOL-06`,包内自洽)。

### WP-07: 文档修订包(声明失实/死链/发布清单)

- **成员:** `F-DOC-01`、`F-DOC-02`、`F-DOC-03`、`F-DOC-04`、`F-DOC-05`、`F-DOC-06`(包内最高严重度 MEDIUM;含必做清单条目 `F-DOC-03`)
- **共同修复位置:** `docs/v1.0.0 prd/tech-spec.md`(两处措辞 + 依赖表行)、`AGENTS.md`(配置顺序 + 现状叙述 + 17 处死链)、`apps/fc/README.md`、`apps/miniprogram/README.md`、`docs/runbook/deployment-guide.md`(ENV 翻转清单项)等 ≈10 文件死链批量替换
- **包级工作量档:** M — 重估理由(D-04):全部为措辞/清单/机械替换 S 粒度,但横跨 ≈10 个文档文件(死链 ≈47 处),合并为一档 M;`F-DOC-06` 批量替换与 `F-DOC-04/05` 的 AGENTS.md 修订共修同文件,总量 < 各条之和。
- **依赖:** 无;`F-DOC-03` 的 ENV 翻转清单项建议在首次对外发布前完成(必做清单条目,见执行摘要)。

### WP-09: FC 运维配额配置(平台层零代码)

- **成员:** `F-CODE-05`(包内最高严重度 LOW)
- **共同修复位置:** FC 控制台(两函数实例并发/弹性上限 + 费用告警;应用层配额为可选后续)
- **包级工作量档:** S — 台账原档照抄(平台配置层零代码即可闭环)。
- **依赖:** 无。

### WP-06: 联调/部署工具失准修复

- **成员:** `F-TOOL-01`、`F-TOOL-02`、`F-TOOL-03`(包内最高严重度 LOW)
- **共同修复位置:** `apps/worker/src/soniscope_worker/`(verify_prep.py 三分渲染、fc_deploy.py 备份阻断、verify_upload_live.py 残留报告)+ 对应 pytest(FakeProbes/FakeFcApi 既有注入面)
- **包级工作量档:** M — 重估理由(D-04):三条各自 S 单文件,同组件多文件合并为 M。
- **依赖:** 无;`F-TEST-06` 中 `F-TOOL-01/02/03` 三行断言随本包落地(收口对账挂 WP-03)。

### WP-08: 测试强化包(活体清单化/驱动补齐/fake 对齐/负断言/卫生)

- **成员:** `F-TEST-01`、`F-TEST-02`、`F-TEST-07`、`F-TEST-08`、`F-TEST-09`、`F-TEST-10`(包内最高严重度 LOW)
- **共同修复位置:** 发布清单(runbook 勾选项,与 WP-07 同文件面可协同)、`apps/miniprogram/test/`(index.js 未驱动 handler 增补、oss_sign 负断言)、`apps/worker/tests/`(契约测试骨架、卫生整改)
- **包级工作量档:** M — 重估理由(D-04):主体 `F-TEST-02`/`F-TEST-08` 各 M,其余 S;`F-TEST-07` 为义务清单不新增独立工作量(随 WP-01/03/05/09 各成员修复分摊,本包收口对账)。
- **依赖:** `F-TEST-07` 收口对账依赖 WP-01/WP-03/WP-05/WP-09 完成;`F-TEST-01` 发布清单化建议先于首次对外发布执行。

**工作包成员并集对账等式(照录 CALIBRATION.md):** 37 = WP-01(4)+ WP-02(4)+ WP-03(6)+ WP-04(1)+ WP-05(6)+ WP-06(3)+ WP-07(6)+ WP-08(6)+ WP-09(1)= 40 − 3(INFO)− 0(并入副条)✓;成员无跨包重复。

## Do-NOT-fix 登记表

> RPT-05:以下条目为**故意设计**,修复里程碑不得"修复";全文与证据见 `DO-NOT-FIX.md`(D-08 预录入,逐条五字段)。DNF-04 归属经用户裁定维持(D-13)。

| ID | 标注 | 一句理由 | 证据链接 |
|-----|------|----------|----------|
| DNF-01 | `⚠ intentional — do not "fix"` | `whisper-local` 桩系 AGENTS.md 红线落地(本期不部署本地 Whisper),选用时受控报错并给出改配 `cloud-speech` 的可操作提示 | `DO-NOT-FIX.md` §DNF-01(`apps/worker/src/soniscope_worker/transcriber.py:144-165 @ 5927f36`) |
| DNF-02 | `⚠ intentional — do not "fix"` | `issue-cedential` 拼写域名系 Aliyun 真实分配值且已登记微信服务器域名白名单,任何"修正"操作即断线上功能 | `DO-NOT-FIX.md` §DNF-02(`apps/miniprogram/config.js:8-10 @ 5927f36`) |
| DNF-03 | `⚠ intentional — do not "fix"` | 两个 FC 函数入口按约定必须同名 `handler.py`,mypy 无法同 run 处理重名顶层模块;豁免系显式记录的工程取舍,逻辑下沉层 `fc_shared` 在 mypy strict 范围内 | `DO-NOT-FIX.md` §DNF-03(`pyproject.toml:30-32 @ 5927f36`) |
| DNF-04 | `⚠ intentional — do not "fix"` | 向客户端下发临时 STS 系 OSS 直传模式固有形态,爆炸半径受单 key/仅 PutObject/≤900s 严格限定并有 `make test-sts-escape` 实测背书;**经用户裁定维持(D-13),Phase 1 挂起的归属事项就此闭环** | `DO-NOT-FIX.md` §DNF-04(`apps/fc/shared/fc_shared/sts.py:102-114 @ 5927f36`,仅引字段名) |

## 优点盘点

> RPT-06:本节登记审计中经核实有效的设计与实现优点,**目的是防止修复里程碑把故意设计误当缺陷"优化"掉**。来源三处(D-16):①HYPOTHESES.md 中标注"RPT-06 优点候选"的七处备注(HYP-03/04/08/09/10/16/19);②DNF 4 条(故意设计即优点);③REQUIREMENTS 点名例(MaskedSecret、单键 STS、`.done` 状态机)。每条优点 = 一句陈述 + 既有台账证据行号引用;允许从 COVERAGE 既有行补录明显遗漏项但不新采证。

1. **双侧秘密脱敏机制经核实有效**——Worker 侧 `MaskedSecret` repr/str 前后 4 位掩码 + FC 侧 `is_sensitive` 精确名单+子串兜底双层洗涤与 `hash_openid` sha256 前缀,长期凭证与会话字段全覆盖(REQUIREMENTS 点名例 MaskedSecret 同条覆盖)。证据:`HYPOTHESES.md:96`(HYP-08 备注行)。
2. **单键 STS 最小权限策略**——`single_key_policy` Resource 精确单 object key 无路径通配、仅 `oss:PutObject`、时效恒 900 秒,且有 `make test-sts-escape` 越权反例实测背书(REQUIREMENTS 点名例单键 STS 同条覆盖)。证据:`HYPOTHESES.md:105`(HYP-09 备注行)。
3. **`.done` 文件状态机与原子写协议核查通过**——`.done` 最后写、任一阶段失败不建 `.done`、manifest→transcript→`.done` 落盘顺序原子化,幂等语义可靠(REQUIREMENTS 第三点名例,补录引 COVERAGE 既有行)。证据:`COVERAGE.md:32`(pipeline.py 行"`.done` 最后写…原子写协议核查通过")、`COVERAGE.md:36`(manifest.py 行"落盘顺序核查通过")。
4. **单线程文件状态机免锁简单性系可辩护取舍**——个人单用户场景片段到达率低,串行吞吐上限远未触及,单线程换取磁盘状态机免锁简单性经 D-10 裁定成立。证据:`HYPOTHESES.md:116`(HYP-10 备注行)。
5. **OSS 长期备份 + retranscribe 可重建**——音频有 OSS 备份、转写产物可经 retranscribe 自 OSS 重建,盘毁仅损失转写成本而非录音数据。证据:`HYPOTHESES.md:174`(HYP-16 备注行)。
6. **Transcriber/NlsBackend 双层 Protocol 隔离充分**——业务流程仅依赖 Protocol,ASR 引擎替换只需新实现类 + 工厂分支 + config.yaml 改名,不动流水线。证据:`HYPOTHESES.md:203`(HYP-19 备注行)。
7. **FC 部署工具高频操作覆盖完整**——备份/打包/仅代码更新/回滚/日志诊断五项完整覆盖高频操作,一次性 setup 已完成、两函数在线。证据:`HYPOTHESES.md:54`(HYP-04 备注行)。
8. **纯 JS sha256 系文档化的可辩护取舍**——docstring 自述本期取舍(wasm 属后续优化),正确性有已知向量 + node crypto 随机字节对照测试锁定;失败模式为保存路径卡顿而非数据丢失。证据:`HYPOTHESES.md:45`(HYP-03 备注行)。
9. **DNF 4 条故意设计即优点**——whisper-local 受控桩、issue-cedential 真实域名守卫、handler 同名约定下的豁免纪律、受限爆炸半径的 STS 直传形态,均为显式记录的工程取舍(见上节 Do-NOT-fix 登记表)。证据:`DO-NOT-FIX.md` §DNF-01~04。
10. **(补录)fc_deploy 错误文本脱敏管道**——`_redact_error_text` 对错误文本替换全部秘密 env 值 + LTAI/STS AK 模式,`.env` 装载值不入任何日志。证据:`COVERAGE.md:87`(fc_deploy.py 行既有"记 RPT-06 优点候选"标注)。
11. **(补录)联调工具拒绝响应泄漏反查**——fc_live 对拒绝场景响应做 STS 字段泄漏反查,verify_upload_live 对鉴权失败做对象信息泄漏反查,检查面主动防泄漏。证据:`COVERAGE.md:89`(fc_live.py 行)、`COVERAGE.md:90`(verify_upload_live.py 行,均为既有"记 RPT-06 优点候选"标注)。

## 分维度置信声明

> RPT-07:逐维度声明"审到多深、哪些区域仅轻度覆盖、哪里已检查无发现",供报告读者校准信任度。规模数字均经 2026-07-05 现场 grep 复核底稿,非转抄。

### 置信·CON

- **审到多深:** CONTRACT-MATRIX.md 51 行契约要素 × FC/Worker/小程序三列,非 n/a 格 **103** 格 = agree **91** / diverge **2** / absent **10**(现场复核:`grep -oE '\| agree ' | wc -l` → 91,diverge → 2,absent → 10);正文证据引用 235 处 `@ 5927f36`;18 个黄金样本(S-01~S-18)双 TZ 执行全销号;12 个 diverge/absent 格全部归入 F-CON-01~06(对账等式见 CONTRACT-MATRIX.md 机械对账节)。
- **已检查无发现(显式源):** 91 个 agree 格逐格带行号证据;重复逻辑普查 9 候选中 4 项"已检查,无新发现"(CONTRACT-MATRIX.md 机械对账第 6 条);FC↔Worker 主链 15 个样本同收同拒、往返等式全部成立、无行为分叉(往返校验总结论)。
- **轻度覆盖:** FC 直转目标态对照按章程排除(见执行摘要范围外事项);判定过程未撞见安全类顺带发现(findings/contract.md 批次导语)。

### 置信·CODE

- **审到多深:** COVERAGE.md CODE 维度 **47** 个对象(worker 核心 14 + fc 12 + miniprogram 21)全部普审且逐面过 **9/9** 关注面(D-04 九面清单:静默失败/数据丢失/秘密处理/硬编码云值/时区日期/死代码/注释失实/纯逻辑+IO 注入违反/跨端约定一致性);其中深挖点逐行深挖(CODE 侧 10 条 HYP + 5 条 D14 线索,20 处深挖点全下落)。
- **已检查无发现(显式源):** pipeline.py/nls.py/cli.py/manifest.py/transcriber.py/config.py/locks.py 等核心模块"无发现"行(COVERAGE.md CODE 表,如 :32-34);FC 侧 sts.py/env.py/audit.py/auth.py/app.py 五个深挖点显式无发现(COVERAGE.md:46-47,53,55,57);`.done` 时序与 OssSource 结构性无删除红线核查通过。
- **轻度覆盖:** cli.py 作 TOOL 子命令入口整体归 CODE 审一次(实体逻辑在 TOOL 侧模块行);9 条扫描排除路径按存在级处置不逐文件审计(D-09,排除 ≠ 免记录)。

### 置信·TOOL

- **审到多深:** COVERAGE.md TOOL 维度 **16** 个对象(worker 验证/运维模块 12 + scripts 3 + Makefile 1,合计约 5,800 行静读)全部 **9/9** 面;深挖 HYP-04(fc_deploy)/HYP-07(test_asr 签名 URL)/HYP-15(miniprogram_lint)/HYP-18(legacy SDK)与 D14-3(联调镜像);Makefile 45 目标逐个细读、危险目标(oss-delete-obj/rollback-fc/deploy-fc)逐个核查;D-08 零执行纪律(工具静读不运行,取证仅 `git show 5927f36:<path>`)。
- **已检查无发现(显式源):** retranscribe.py `.done` 绕行边界核查通过(COVERAGE.md:88);ops.py 无删除入口且自身即 R-07 红线自动核查器(COVERAGE.md:91);e2e.py 纯只读零云 IO(COVERAGE.md:92);gen_worker_config.sh 秘密写入面核查通过——模板恒写占位符、chmod 600 紧随生成(COVERAGE.md:100)。
- **轻度覆盖:** scripts/ 审计范围经 D-06 缩窄为三文件(scripts/ralph/ 属 agent 元工具排除);真云操作零执行,行为面判定依赖静读 + 既有测试证据。

### 置信·DOC

- **审到多深:** DOC-CLAIMS.md **23** 个文档对象、**198** 条声明逐条四态销号 = agree **146** / drift **9** / dead-ref **24** / 无法静态核实 **19**(现场复核 DOC-CLAIMS.md 四态分布合计表);PRD + tech-spec 深核 66 条、runbook 4 份 66 条、AGENTS.md/README×3/config.js 等 66 条。
- **agree 与"无法静态核实"分开陈述:** 146 条 agree 均有代码侧行号证据对照;**19 条"无法静态核实"为云端计费费率、控制台配置、机器侧环境等平台侧事实——如实标注、零猜测**,不计入一致性结论(如 CS-14/DG-19 成本表仅做跨文档口径自洽核对)。
- **已检查无发现(显式源):** runbook 部署步骤 ↔ fc_deploy.py 能力面对照**零 drift**——文档未声称任何工具不具备的能力(DOC-CLAIMS.md FD-09 行,HYP-04 runbook 保真度口径闭环)。
- **轻度覆盖:** 目标态 2 文档(fc-transcribe-design/multi-user-design)仅引用级审计(章程排除对照其内容);`docs/runbook/us-001-manual.html` 死链 census 计入但内容未审。

### 置信·TEST

- **审到多深:** TEST-AUDIT.md **41** 个测试模块(worker pytest 24 + fc pytest 7 + node 10)全部逐面过 **8/8** 质量检查面(断言强度/fake 漂移/隔离/契约常量锁定/秘密泄漏断言/静默 skip/错误路径/私有耦合);反向映射清单 **22** 行(Phase 2/3 全部 F-* 逐条反查测试兜底);门禁完整性三方对照 6 项(声称/静态/实跑);HYP-23 逐错误码 9/9 补偿事实清单、HYP-24 3/3 页面加载矩阵。
- **已检查无发现(显式源):** 2 处显式无发现——覆盖率门禁"无"为三方自洽事实(声称面显式自认,TEST-AUDIT.md D-11 对照行 4);反向映射 F-CON-05 行"无缺口"(错误码透传行为有断言锁定)。另 HYP-23 结论:FC handler 行为测试补偿充分(9/9 错误码入口级驱动);HYP-24 原假设证伪(3/3 注册页均被 node 测试真实加载)。
- **轻度覆盖:** 真云活体目标绝不执行(D-01),活体路径判定口径 = 静态 + 移交证据;行/分支覆盖率数字系本审计临时注入所得(pytest-cov ephemeral / node experimental),仅作证据引用非门禁产物。

### 仪器证据(scans/ 归档,全维度共用)

`scans/` 共 **9** 份归档:五档扫描销号(gates-baseline、ruff-extended、vulture、eslint、secrets)+ 覆盖率实测 2 份(coverage-pytest、coverage-node)+ 门禁实跑(gate-run-worktree)+ 微基准档案(microbench-sha256)。五档扫描 **258** 命中全部三态销号:gates-baseline 90 + ruff-extended 69 + vulture 1 + eslint 29 + secrets 69 = 258;**确认 15 / 误报 243 / 移交 0**(scans/secrets.md 尾部封版行),15 条确认项去向零未决占位(逐条下落见 COVERAGE.md 完成判定第 7 条)。秘密扫描按 CHARTER 穿透规则对基线全量执行(含全部排除目录),`.planning/audit/` 反扫零命中。

## 修复里程碑移交物

- **跨语言契约测试设计配方:** `CONTRACT-TEST-RECIPE.md`(黄金样本跨语言契约测试设计配方,D-16 五要素:单一 JSON 真值源 + pytest/node 双侧消费,样本集 = CONTRACT-MATRIX 附录 S-01~S-18 全合成数据)——**显式移交 FUTURE-02**(REQUIREMENTS v2 条目),设计深度达"修复里程碑拿到即可写代码,不用再设计"。
- **backlog 与排期清单使用说明:** 本报告"发现汇总表"(RPT-02)即修复里程碑的 backlog 全量清单(40 行逐条含严重度/工作量/判定/处置);"修复工作包"(RPT-04)的 WP-01~09 即排期阶段清单(按序数规则排序,含依赖),必做清单三条(`F-CODE-02`/`F-CODE-06`/`F-DOC-03`)由 WP-03/WP-04/WP-07 承载须先行。

## 附录索引

> 机械性长内容按 D-14 分文件承载,主报告在此链入(相对路径,与本文件同目录):

- **附录 A — RPT-08 可追溯映射表:** [REPORT-APPENDIX-A-traceability.md](REPORT-APPENDIX-A-traceability.md) — 29 条溯源闭环主表(25 HYP + 4 DNF,含报告落点与需求映射两列)、Known Bugs 显式无线索行照录、五维度"已检查,无发现"代表性记录、发现↔发现补边表(findings `关联发现` 字段规整转写 46 行)。
- **附录 B — CL-NN 根因聚类明细:** [REPORT-APPENDIX-B-clusters.md](REPORT-APPENDIX-B-clusters.md) — 5 簇根因明细照搬 CALIBRATION.md 零改判(根因陈述/成员/关联工作包互指/证据锚),未入簇孤条 11 条显式清单,成员全覆盖对账等式 29 + 11 = 40 ✓。

## 收尾验证

> 全套机械门禁逐条实跑照录(命令 + 实际输出 + 期望值命中 ✓,仿 HYPOTHESES.md 阶段收尾验证范式),2026-07-05 实跑。任何等式不中只修组装侧(报告/附录),封版台账与 CALIBRATION.md 已批准记录不动——本次实跑 **8/8 全部命中**,无需修正。

**1. 零 diff 验证(里程碑硬约束,ROADMAP 成功判据 5,CHARTER 写定命令):**

```
$ git diff --stat 5927f36 -- apps/ scripts/ docs/
(空输出)
$ git diff --stat 5927f36 -- apps/ scripts/ docs/ | wc -l
0
```

期望空输出——**命中 ✓**(apps/、scripts/、docs/ 相对基线 `5927f36` 零改动,全里程碑审计过程未触碰被审计代码)。

**2. 发现底数等式(findings 五文件):**

```
$ grep -hc '^### F-' .planning/audit/findings/*.md | paste -sd+ - | bc
45
$ grep -h '^### F-' .planning/audit/findings/*.md | grep -vc '\-00:'
40
```

期望 45(含 5 条 `F-*-00` schema 示例)与 40(剔除示例后真实发现)——**双命中 ✓**。

**3. 报告主表等式:**

```
$ grep -c '^| F-' .planning/audit/REPORT.md
40
$ grep '^| F-' .planning/audit/REPORT.md | grep -cE 'BLOCKER|PRE-LAUNCH|POST-LAUNCH'
40
```

发现汇总表 40 行(本文件唯一 `| F-` 开行表)且逐行携带三态判定;三态分解 = BLOCKER 0 + PRE-LAUNCH 3 + POST-LAUNCH 37 = 40——**命中 ✓**(与 CALIBRATION.md 逐条上线判定表终态一致)。

**4. 溯源等式(RPT-08 闭环):**

```
$ grep -c '^### HYP-' .planning/audit/HYPOTHESES.md
25
$ grep -c '^### DNF-' .planning/audit/DO-NOT-FIX.md
4
$ grep -c '^| HYP-' .planning/audit/REPORT-APPENDIX-A-traceability.md
25
$ grep -c '^| DNF-' .planning/audit/REPORT-APPENDIX-A-traceability.md
4
```

附录 A 主表 25 + 4 = **29** = HYPOTHESES 25 HYP + DO-NOT-FIX 4 DNF——**命中 ✓**(29 条溯源在报告侧全部有落点,断链自查见附录 A)。

**5. 校准等式:**

```
$ grep -c '^### CAL-' .planning/audit/CALIBRATION.md
0
$ grep -c '^### CL-' .planning/audit/CALIBRATION.md
5
$ grep -c '^### WP-' .planning/audit/CALIBRATION.md
9
$ grep -c '^### WP-' .planning/audit/REPORT.md
9
$ grep -c '^### CL-' .planning/audit/REPORT-APPENDIX-B-clusters.md
5
```

CAL 0(零拟调整、零并入,经批复确认;grep 计数 0 时退出码 1 属预期)/ CL 5 / WP 9 与 CALIBRATION.md 尾部对账逐项一致;报告 WP 小节数 9 = CALIBRATION WP 数;附录 B CL 数 5 = CALIBRATION CL 数——**全部命中 ✓**。

**6. 严重度分布复算(findings 现场 grep,叠加校准后对照执行摘要):**

```
$ for lvl in CRITICAL HIGH MEDIUM LOW INFO; do
    echo "$lvl $(grep -hc "^- \*\*严重度:\*\* $lvl" .planning/audit/findings/*.md | paste -sd+ - | bc)"
  done
CRITICAL 0
HIGH 0
MEDIUM 11
LOW 26
INFO 3
```

现场复算原级分布 CRITICAL 0 / HIGH 0 / MEDIUM 11 / LOW 26 / INFO 3(合计 40;`-00` 示例严重度槽为"(五级之一)"占位不计入);叠加 CALIBRATION.md 已批准校准(调整 0 条、并入 0 条)后终级分布不变,与执行摘要计数逐级相符——**命中 ✓**。

**7. 秘密反扫(COVERAGE 完成判定第 9 条同款,范围 `.planning/audit/` 全目录,含本阶段全部新文件 REPORT.md 与两附录):**

```
$ grep -rE 'OSSAccessKeyId=[0-9A-Za-z]{8,}|Signature=[0-9A-Za-z%+/=]{16,}|LTAI[0-9A-Za-z]{10,}' .planning/audit/
(零命中,exit=1)
```

期望零命中(exit 1)——**命中 ✓**(报告与附录全程只引位置+模式名,无任何秘密值本体二次入库,CHARTER 秘密红线守住)。

**8. 写入面复核(Pitfall 7:零 diff 命令不保护 apps/scripts/docs 之外的根文件):**

```
$ git status --porcelain
(空输出——本阶段全部改动已随任务提交)
$ git diff --name-only <阶段起点>..HEAD | grep -v '^\.planning/' | wc -l
0
```

工作树干净且本阶段全部提交涉及路径仅 `.planning/audit/` 三文件(REPORT.md + 两附录),无任何 `.planning/` 之外的写入——**命中 ✓**。

### 里程碑交付声明

全套机械门禁 **8/8 命中**。本审计里程碑最终交付物四件套:**`REPORT.md`(主报告)+ `REPORT-APPENDIX-A-traceability.md`(RPT-08 追溯映射)+ `REPORT-APPENDIX-B-clusters.md`(聚类明细)+ `CALIBRATION.md`(已批准校准台账,判断类字段唯一来源)**;修复里程碑移交物为 `CONTRACT-TEST-RECIPE.md`(FUTURE-02,见上文修复里程碑移交物章节)。总判定 **CONDITIONAL GO**,必做清单 `F-CODE-02`/`F-CODE-06`/`F-DOC-03` 三条先行,其余 37 条按发现汇总表进修复里程碑排期。

---
*SoniScope 上线前代码审计报告: 2026-07-05(40 条发现 = MEDIUM 11 / LOW 26 / INFO 3,总判定 CONDITIONAL GO,必做 3 条;附录 A 追溯映射 29 条闭环 + 附录 B 聚类 5 簇;收尾验证 8/8 门禁命中,零 diff 达成)*
