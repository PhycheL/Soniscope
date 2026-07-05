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
