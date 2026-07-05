# 发现台账: 文档配置一致性 (DOC)

**Created:** 2026-07-04

本文件由 Phase 4 写入,ID 前缀 `F-DOC-NN`;schema 以 `.planning/audit/CHARTER.md` 为准。

### F-DOC-00: (schema 示例,非真实发现)

> 本条为 schema 示例,Phase 5 汇总时剔除。

- **维度:** 文档配置一致性 (DOC)
- **严重度:** (五级之一) — 影响:(一句场景语言);可能性:(一句触发条件)
- **证据:** `path:line @ 5927f36`(占位;从 `git show 5927f36:<path>` 提取)
  > (引用片段占位)
- **修复建议:** (一段占位)
- **工作量:** (S/M/L/XL 之一)
- **关联发现:** (F-XXX-NN 或 HYP-NN,无则写"无")
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

## 发现

> 04-03 判定产物(PRD + tech-spec 深核):共 2 条发现——F-DOC-01(tech-spec §6.1 sha256 wasm-crypto 声明与主线程纯 JS 实态相反)、F-DOC-02(tech-spec §6.3 Worker 依赖清单失实,nls20180628 未装而实际承载转写的 legacy SDK 未列);DNF 对照命中(`issue-cedential` 域名拼写 DNF-02、`whisper-local` 桩 DNF-01,双文档各命中)按负面清单核实闭环不立发现清单;dead-ref 登记 3 处(PRD `tests/fixtures/wx-login-fixture.json` 与 `docs/tech-spec.md` 旧路径、tech-spec `docs/PRD_v1.md`/monorepo 树旧路径,→ HYP-02)待 04-05 聚合立条;HYP-21 与 HYP-16(半句)核对结论行已落 DOC-CLAIMS.md 待 04-09 回填。销号底稿见 `.planning/audit/DOC-CLAIMS.md` §PRD_v1.md / §tech-spec.md 两节(P-01~P-30 + T-01~T-36)。

### F-DOC-01: tech-spec §6.1 声称前端 sha256 用 wasm-crypto 避免主线程阻塞,实态为主线程同步纯 JS 实现

- **维度:** 文档配置一致性 (DOC)
- **严重度:** LOW — 影响:自称"唯一技术权威来源"的 tech-spec 对 sha256 实现路径的描述与实态相反(两处声明 wasm-crypto,实为手写纯 JS 于主线程全量同步哈希),按文档排查低端机保存卡顿或评估录音线程阻塞风险时会被误导以为已 wasm 化,掩盖 HYP-03 已证实的主线程同步哈希疑点;可能性:仅在性能排查、真机卡顿评估或接手开发对照文档时触发,不改变运行时行为
- **证据:** `docs/v1.0.0 prd/tech-spec.md:539,549 @ 5927f36`
  > `:539`「**音频 sha256**：前端用 wasm-crypto 或类似库计算，避免主线程阻塞」;`:549` SDK 接口表 sha256 行「`wasm-crypto` 或同类 wasm 库（避免主线程阻塞）」——实态:`apps/miniprogram/utils/sha256.js:9-18,66-135 @ 5927f36`(手写 K 表 + hashWords 同步实现,无任何 wasm/异步/分块让出),`sha256.js:4-5 @ 5927f36` docstring 自认「本期先用纯 JS……wasm 化属后续性能优化」,调用链 `apps/miniprogram/pages/index/index.js:30,640 @ 5927f36`(主线程对 readFileSync 全量音频字节哈希)
- **修复建议:** 修订 tech-spec §6.1 两处(:539 平台约束 bullet 与 :549 SDK 接口表 sha256 行)措辞对齐实态——改为"本期为纯 JS 主线程同步实现(取舍自述见 sha256.js docstring),wasm 化/分块异步化列为后续性能优化";反向选项(落实 wasm 化)属性能加固,已在 HYP-03 记 RPT-06 加固候选,不由本条驱动。
- **工作量:** S(tech-spec 单文件两处措辞)
- **关联发现:** 无;关联线索: HYP-03(细化:纯 JS 主线程同步哈希半句证实)
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-DOC-02: tech-spec §6.3 依赖清单声称 Worker 依赖 `alibabacloud-nls20180628`,实际未装该包且承载转写主路径的 legacy SDK 未列入清单

- **维度:** 文档配置一致性 (DOC)
- **严重度:** LOW — 影响:依赖清单是环境重建与供应链审查的依据,现状双向失实——按文档安装 `alibabacloud-nls20180628` 无法复现实际转写路径(该包根本不在依赖中),而真正承载生产 NLS filetrans 主路径的 legacy `aliyun-python-sdk-core` 在文档中不可见,依赖风险评估(HYP-18 两代 SDK 并存)按文档核对会整体漏看;可能性:环境重建、依赖升级排查或按清单做安全审计时触发
- **证据:** `docs/v1.0.0 prd/tech-spec.md:562 @ 5927f36`
  > 「Worker（Python） | `alibabacloud-oss-v2`、`pyyaml`、`pydantic>=2`、`typer`、`alibabacloud-nls20180628`；…」——实态:`apps/worker/pyproject.toml:8-15 @ 5927f36` 依赖清单为 pydantic/pyyaml/alibabacloud-oss-v2/alibabacloud-sts20150401/alibabacloud-tea-openapi/**aliyun-python-sdk-core**/alibabacloud-fc20230330,无 `alibabacloud-nls20180628`;NLS 调用实经 legacy AcsClient/CommonRequest(`apps/worker/src/soniscope_worker/nls.py:441-448,454-455 @ 5927f36`,引 HYP-18 证据行)
- **修复建议:** 修订 tech-spec §6.3 Worker 依赖行:删去 `alibabacloud-nls20180628`,改列 `aliyun-python-sdk-core`(注明 legacy POP/RPC 形态与 NLS filetrans 2018-08-17 消费点)及实际存在的 `alibabacloud-sts20150401`/`alibabacloud-tea-openapi`/`alibabacloud-fc20230330`(后者标注仅部署用),与 `apps/worker/pyproject.toml` 逐行对齐;未来若迁移到 alibabacloud-nls 系 SDK 再同步更新。
- **工作量:** S(tech-spec 单文件一处表行)
- **关联发现:** 无;关联线索: HYP-18(细化:两代 SDK 并存、legacy 承载生产主路径证实)
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

> 04-04 判定产物(runbook 4 份深核:cloud-setup 19 条 + mvp-acceptance 12 条 + deployment-guide 19 条 + fc-deploy 16 条,共 66 条销号):共 **1 条发现**——F-DOC-03(HYP-14 专项:发布文档未覆盖 config.js ENV 常量的生产翻转步骤,MEDIUM);runbook 步骤 ↔ fc_deploy.py 能力面对照零 drift(FD-09,HYP-04 runbook 保真度口径闭环,文档未声称工具不具备的能力);纯控制台/云端/机器侧事实 **14 条**如实标『无法静态核实』无猜测(CS ×8 / MA ×1 / DG ×3 / FD ×2);dead-ref **4 处**登记移交 04-05 聚合(CS-09、CS-15、MA-01、DG-01,→ HYP-02——其中 CS-15 系脚本旧路径 `./test/test_asr.py`,余三处为权威文档旧路径 `docs/PRD_v1.md`/`docs/tech-spec.md`);DNF-02(issue-cedential 拼写)命中 5 行(CS-08/MA-02/DG-09/DG-16/FD-12)全部核实闭环不立发现。销号底稿见 `.planning/audit/DOC-CLAIMS.md` §cloud-setup.md / §mvp-acceptance.md / §deployment-guide.md / §fc-deploy.md 四节。

### F-DOC-03: 发布文档未覆盖小程序 `config.js` ENV 常量的生产翻转步骤,照 deployment-guide 发布流程执行会把 development 门控带上线

- **维度:** 文档配置一致性 (DOC)
- **严重度:** MEDIUM — 影响:deployment-guide 自称"从零到全链路上线的可逐步执行操作手册",其小程序发布节(§6.3-6.4:DevTools 上传 → 体验版 → 审核 → 发布)与附录 A 检查清单均无"把 `config.js:29` 的 `ENV = 'development'` 翻转为 `production`"步骤,§6.3 仅要求核对 FC/OSS URL——照文档逐步执行即把 development 原样发布,最终用户(含体验成员)可见开发者菜单并可开启故障注入开关(`mock-fc-url-broken`/`mock-verify-fail` 会直接使上传/verify 链路失败),开发者菜单与故障注入的三重 production 门控(代码侧已核实完备)全部落空;可能性:每次发布必经该流程且四份 runbook 与 AGENTS.md 零命中翻转步骤,翻转完全依赖记忆而非清单——架构评审文档已点名该单点风险并建议"构建期注入或发布 checklist 强制项",但建议未落入任何 runbook(对应 CHARTER MEDIUM 锚点『可诱发高危误操作的误导性文档(如 runbook 步骤与实态不符)』:发布 runbook 步骤不完备,照做即误发 development 构建)
- **证据:** `docs/runbook/deployment-guide.md:357-365,479-482 @ 5927f36`
  > §6.3-6.4 发布流程:「1. DevTools 点「上传」→ 微信管理后台「版本管理」设为体验版。…真机微信打开体验版验证全链路 verified 后，提交审核 → 发布正式版。」——全流程无 ENV 翻转项;§6.3 第 2 步仅「确认 `apps/miniprogram/config.js` 中的 FC / OSS URL 与 §6.2 一致」(:358)。全文档检索(`git grep -n 'ENV' 5927f36 -- docs/ AGENTS.md`、`git grep -ni 'production' 5927f36 -- docs/ AGENTS.md`,排除 vendored docs/example/)命中全集仅:`docs/architecture/architecture-review-2026-07-02.md:58,70,193`(:70「发版忘改会把开发者菜单与故障注入带上线」、:193 建议清单强制项——风险已知未落实)、`docs/v1.0.0 prd/tech-spec.md:529`、`docs/runbook/mvp-acceptance.md:138`(两处仅描述门控存在,均假设 production 已生效)。ENV 基线现值与门控实现证据(HANDOFF-PHASE4.md DOC 节第 2、3 条移交,03-04 采证):`apps/miniprogram/config.js:29 @ 5927f36`(`ENV = 'development'` 硬编码现值)、`apps/miniprogram/pages/dev/dev.js:18,28,52 @ 5927f36`(dev 页三重门控)、`apps/miniprogram/utils/fault_injection.js:38-40,82-107 @ 5927f36`(production 读全关写忽略——门控实效完全取决于 ENV 发布取值)
- **修复建议:** 在发布文档补齐 ENV 翻转为强制清单项(双落点):deployment-guide §6.4 发布步骤首条增加「发布前把 `apps/miniprogram/config.js` 的 `ENV` 由 `development` 改为 `production`,并在 DevTools 真机预览确认开发者菜单入口不可见」,附录 A"小程序"清单同步加一行勾选项;可选同步在 mvp-acceptance §0 验收前提补一条 ENV=production 断言。根治向(architecture-review :193 已建议):构建期注入 ENV 或 `miniprogram_lint.py` 增加发布态检查——属代码/工具改动,超出本发现文档修复范围,留待修复里程碑决策。
- **工作量:** S(deployment-guide 单文件两处清单行;可选 mvp-acceptance 一行)
- **关联发现:** 无;关联线索: HYP-14(证实方向:发布文档未覆盖翻转步骤;结论行 DOC-CLAIMS.md FD-16,04-09 回填锚点);销号引 HANDOFF-PHASE4.md DOC 节第 2、3 条
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

> 04-05 判定产物(AGENTS.md + README×3 + config.js 深核、两 JSON 普审、普审级 5 文档、目标态 2 文档引用级、存在级 3 组登记与 DOC 收口):共 **5 条发现**——F-DOC-04(AGENTS.md 配置回退声明失实,LOW)、F-DOC-05(AGENTS.md 与两份子 README 现状叙述滞后于实施进度,LOW)、F-DOC-06(HYP-02 聚合:权威文档迁移后旧路径引用全仓死链,LOW)、F-DOC-07(HYP-05:vendored Aliyun FC 示例仓 1003 文件 ≈28 MB 入库,INFO)、F-DOC-08(HYP-06:四套 agent 工具目录独立副本已实际漂移,INFO)。DNF 对照命中(issue-cedential 拼写 DNF-02 ×4:CF-02 核实结论行 + AG-29/AG-38/RF-01/RM-03;whisper-local 桩 DNF-01 ×2:AG-21/AG-34)按负面清单核实闭环不立发现;wasm-crypto 与 nls20180628 两处 AGENTS.md 同款失实声明判 drift 共证既有 F-DOC-01/F-DOC-02 不另立条(HYP-03 已裁定不复判)。ROADMAP 成功判据 1 两条点名线索核实结论均落档:issue-cedential 拼写域名(DOC-CLAIMS CF-02,agree 闭环 DNF-02 不立 F-DOC)、AGENTS.md 引用已删除文档(AG-01~17 逐处登记 → F-DOC-06 聚合)。销号底稿见 `.planning/audit/DOC-CLAIMS.md` §AGENTS.md / §README.md ×3 / §config.js / §project.config.json / §app.json / §普审级 5 文档 / §目标态 2 文档 / §存在级登记 / §DOC 总机械对账 各节(AG-01~39 + R-01 + RF-01~06 + RM-01~06 + CF-01~08 + PC-01~03 + AJ-01~03,共 66 条;阶段累计 198 条)。

### F-DOC-04: AGENTS.md 声称未设置 SONISCOPE_HOME 时回退 `~/SoniScope/config.yaml`,实态无任何固定兜底(直接报错)

- **维度:** 文档配置一致性 (DOC)
- **严重度:** LOW — 影响:AGENTS.md 是 AI 编码代理的首要工作规则文档,其配置加载顺序声明与实态相反——实态为进程 env → 向上搜索仓库根 .env → 抛 `RuntimeHomeError`(无任何 `~/SoniScope` 分支),且与 tech-spec §2.3"加载顺序 env → 仓库根 .env,无固定兜底"(T-09)、deployment-guide §1.2"脚本不兜底固定目录"(DG-06)双文档口径同时冲突;按 AGENTS.md 排查"未设置 SONISCOPE_HOME"问题或新环境搭建时会误以为存在家目录兜底;可能性:配置排障/新环境搭建/AI agent 按文档理解装载逻辑时触发;实际报错文案本身给出正确指引(export 或写 .env),误导窗口有限
- **证据:** `AGENTS.md:108-110 @ 5927f36`
  > 「配置加载顺序：1. `$SONISCOPE_HOME/config.yaml` 2. 未设置 `SONISCOPE_HOME` 时回退 `~/SoniScope/config.yaml`」——实态:`apps/worker/src/soniscope_worker/paths.py:49-63 @ 5927f36`(`soniscope_home()`:env 有值即用 → `_find_dotenv()` 向上搜索 .env → 否则 `raise RuntimeHomeError("未设置 SONISCOPE_HOME。请先 export……或在仓库根目录 .env 中写入……")`,无 `~/SoniScope` 分支);文档侧同款正确口径:`docs/v1.0.0 prd/tech-spec.md:121-145 @ 5927f36`(T-09)、`docs/runbook/deployment-guide.md:61-73 @ 5927f36`(DG-06)
- **修复建议:** 修订 AGENTS.md「运行时目录与配置」节配置加载顺序两行,对齐实态与 tech-spec/deployment-guide 口径:"1. 进程环境变量 `SONISCOPE_HOME` 2. 仓库根(向上搜索).env 中的 `SONISCOPE_HOME`;均未设置时报错退出,无固定目录兜底"。
- **工作量:** S(AGENTS.md 单文件两行措辞)
- **关联发现:** F-DOC-05(同文件 AGENTS.md 滞后声明);关联线索: 无
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-DOC-05: AGENTS.md 与两份子 README 的"现状/后续 story"叙述滞后于实施进度,声称占位/骨架而基线已全量实现

- **维度:** 文档配置一致性 (DOC)
- **严重度:** LOW — 影响:三处"现状"叙述停留在早期 story 时点,与基线全量实现实态相反——AGENTS.md 称"仓库仍处于 MVP 初期,`apps/`、`Makefile`、`pyproject.toml` 等会在对应 story 中创建"(三者全部实存并承载 45 个 make 目标与 26 个 worker 模块);apps/fc/README.md 称"`handler.py` 为占位 WSGI 处理器,真实业务逻辑在 US-006/007/009 实现"(两 handler 均已是含鉴权三步 + STS 签发 / HeadObject 三态校验的全量实现);apps/miniprogram/README.md 称"本 story(US-011)只交付骨架与环境配置"(基线已是三页 + 16 个 utils 模块的完整实现)——新读者或 AI agent 按 README 判断组件成熟度会得出与实态相反的结论(项目已处部署上线阶段);可能性:onboarding、代码走读或 AI agent 读 README 建立上下文时触发,不影响运行时行为
- **证据:** `AGENTS.md:25,89 @ 5927f36`、`apps/fc/README.md:31-34 @ 5927f36`、`apps/miniprogram/README.md:33-35 @ 5927f36`
  > AGENTS.md:89「`apps/`、`Makefile`、`pyproject.toml` 等会在对应 story 中创建」——实态 `git ls-tree --name-only 5927f36`(三者均在,另 .claude/.codex/ 也不在"已存在目录"清单);fc/README:33「`handler.py` 为占位 WSGI 处理器」——实态 `apps/fc/issue_credential/handler.py:71-81 @ 5927f36`(全量鉴权 + AssumeRole 签发)、`apps/fc/verify_upload/handler.py:40 @ 5927f36`;miniprogram/README:35「本 story（US-011）只交付骨架与环境配置」——实态 `git ls-tree -r --name-only 5927f36 apps/miniprogram/utils/`(16 个 utils 模块,录音/分片/8 状态队列/OSS V4 签名/verify/故障注入全在)
- **修复建议:** 三文件"现状/后续 story"节改写为部署阶段实态:AGENTS.md 项目类型节删去"MVP 初期/会在对应 story 中创建"叙述并更新已存在目录清单;apps/fc/README.md「现状(US-005)」节改述两函数已全量实现;apps/miniprogram/README.md「后续 story」节改述 US-012~US-020 已交付。均为叙述性修订,无代码改动。
- **工作量:** S(三文件各一节措辞)
- **关联发现:** F-DOC-04(同文件 AGENTS.md);关联线索: 无
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-DOC-06: 【HYP-02 聚合】权威文档迁移至 `docs/v1.0.0 prd/` 后,全仓 10 文件的旧路径引用未随迁——AGENTS.md 17 处死链为主体,权威文档链首两环全部指向不存在的路径

- **维度:** 文档配置一致性 (DOC)
- **严重度:** LOW — 影响:`docs/PRD_v1.md` 与 `docs/tech-spec.md` 旧路径在基线不存在(实体在 `docs/v1.0.0 prd/`),而 AGENTS.md 优先级链(:5,6)、四份 runbook 权威链、PRD/tech-spec 自引用、设计/对比文档引用全部仍指旧路径——按引用寻文一律落空;AGENTS.md 是 AI 编码代理首要规则文档,其"关键文件"与"按需查阅"两张导航表(:405-424)整体失效,代理与新读者循径找不到权威文档,需靠全仓搜索自救;另有 cloud-setup §5.4 联调脚本旧路径 `./test/test_asr.py`(实存 `scripts/test_asr.py`,CS-15)与 PRD 引用的不存在 fixture 文件(P-26)两处异源死链;可能性:每次按文档链寻源必触发,是审计中命中面最广的单一文档问题(10 文件 ≈47 处命中)——对应 CHARTER LOW 锚点『文档死链/路径失效』
- **证据:** `git grep -n 'docs/PRD_v1.md\|docs/tech-spec.md\|docs/deployment-guide.md' 5927f36 -- AGENTS.md docs/`(排除 vendored docs/example/)全量命中 census:
  > **AGENTS.md ×17**(:5,6,69,157,337,375,405,406,416,417,418,419,420,421,422,423,424——逐处登记见 DOC-CLAIMS.md AG-01~AG-17);**设计文档 ×4**:`docs/fc-transcribe-design.md:5`、`docs/multi-user-design.md:5,599,600`(04-RESEARCH 预核 3 处,实测 :600 亦命中,census +1);**runbook ×4**:`docs/runbook/cloud-setup.md:83`(CS-09)、`docs/runbook/mvp-acceptance.md:3,5`(MA-01)、`docs/runbook/deployment-guide.md:5`(DG-01);**普审文档 ×1**:`docs/transcribe-approach-comparison.md:5`;**存在级对象 ×1**:`docs/runbook/us-001-manual.html:471`(census 计入,内容未审);**权威文档自引用**:`docs/v1.0.0 prd/PRD_v1.md` ×19(:5,63,122,177,188,236,365,389,413,476,509,534,565,596,598,714,784,847,869——P-27)、`docs/v1.0.0 prd/tech-spec.md:3,80-81`(T-05)。存在性判定:`git ls-tree -r --name-only 5927f36 docs`(顶层无 PRD_v1.md/tech-spec.md,实体在 `docs/v1.0.0 prd/`;旧路径 `docs/deployment-guide.md` 全仓零命中)。附注两处异源死链同锚点并档:`docs/runbook/cloud-setup.md:151 @ 5927f36`(`./test/test_asr.py`,实存 `scripts/test_asr.py`,CS-15)、`docs/v1.0.0 prd/PRD_v1.md:204 @ 5927f36`(`tests/fixtures/wx-login-fixture.json` 基线不存在,fc_live 实现自造伪造 code,P-26)
- **修复建议:** 批量路径替换:`docs/PRD_v1.md` → `docs/v1.0.0 prd/PRD_v1.md`、`docs/tech-spec.md` → `docs/v1.0.0 prd/tech-spec.md`(10 文件 ≈45 处,机械可完成;注意新路径含空格,Markdown 链接需引号/转义处理,html 内 1 处同步);cloud-setup:151 改 `scripts/test_asr.py`;PRD:204 fixture 引用改述为 fc_live 自造伪造 code 的实际口径(或补建 fixture,二选一由修复里程碑决策)。替代方案:把两权威文档迁回 `docs/` 顶层(改动面更小但需用户对目录布局重新决策)。
- **工作量:** S(批量机械替换 + 2 处措辞;若选迁回方案则为目录决策 + 2 次 git mv)
- **关联发现:** F-DOC-04/F-DOC-05(AGENTS.md 同文件);关联线索: HYP-02(证实方向:引用失效半句全量坐实;"deletions uncommitted"半句已被基线核实推翻——CHARTER 基线章节,04-09 回填锚点)
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-DOC-07: 【HYP-05】vendored Aliyun FC 示例仓 `docs/example/start-fc-main/` 以 1,003 个跟踪文件、约 28 MB 整仓入库

- **维度:** 文档配置一致性 (DOC)
- **严重度:** INFO — 影响:存在级观察(CHARTER INFO 锚点逐字点名"vendored 仓库膨胀"):完整第三方示例仓入库造成仓库体积膨胀与全仓检索噪声——本审计全程 grep 均需显式排除 `docs/example/`,未排除时旧路径/常量检索会混入大量无关命中;可能性:全仓搜索、clone、依赖扫描类操作必然经过,无运行时影响
- **证据:** `git ls-tree -r --name-only 5927f36 docs/example/start-fc-main | wc -l` → **1003**;`git ls-tree -r -l 5927f36 docs/example/start-fc-main` blob 合计 **28,227,670 字节(≈28 MB)**——与 HYP-05 假设"29 MB、1,003 个跟踪文件"文件数逐一吻合(字节数为 blob 合计口径,量级一致)
- **修复建议:** 移除 vendored 副本,以 README 一行登记上游仓库 URL + 所需参考的具体文件/commit 替代(或 git submodule/sparse 引用);若确需离线保留,至少在 `.gitattributes` 标 `linguist-vendored` 并在检索惯例中固化排除口径。按 D-09 存在级处置,不逐文件审计。
- **工作量:** S(单目录删除 + 一行登记;历史体积不回收属 git 常识,不在本条范围)
- **关联发现:** 无;关联线索: HYP-05(证实方向:存在级底数坐实,04-09 回填锚点)
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-DOC-08: 【HYP-06】agent 工具脚手架在 `.agents/`、`.claude/`、`.codex/`、`.cursor/` 四处重复,独立副本已实际漂移

- **维度:** 文档配置一致性 (DOC)
- **严重度:** INFO — 影响:存在级观察(CHARTER INFO 锚点逐字点名"四套 AI 工具目录漂移"):同一 agent 脚手架四处副本(.agents 54 / .claude 440 / .codex 420 / .cursor 468 个跟踪文件)各自独立演进,单处修复会静默遗漏其余三处——抽样已见实际漂移:同名工作流文件在三目录 blob 各异;可能性:任何对 agent 规则/工作流的修改必触发同步问题,无运行时影响(均为工具目录,审计范围排除区,per D-09 存在级照记)
- **证据:** `git ls-tree -d --name-only 5927f36` → `.agents/`、`.claude/`、`.codex/`、`.cursor/` 四目录并存(文件数 54/440/420/468);漂移抽样:`gsd-core/workflows/execute-plan.md` 在 .claude/.codex/.cursor 三处 blob **各异**(`774f39f` / `92d5572` / `b418a23`,`git ls-tree 5927f36 <dir>/gsd-core/workflows/execute-plan.md`);结构漂移:`commands/prime.md` 在 .agents/.claude/.cursor 三处同 blob(`93515c0`)而 .codex 布局完全不同(无 commands/ 同名文件)
- **修复建议:** 收敛为单一权威源(如 `.agents/` 或独立 tooling 仓)+ 各工具目录由安装/同步脚本生成;短期最小动作:在 AGENTS.md 登记"四目录副本关系与权威侧"约定,修改时四处同步。按 D-09 存在级处置,不逐文件审计。
- **工作量:** M(需盘点四目录差异并定权威侧;同步机制属工具链改动)
- **关联发现:** 无;关联线索: HYP-06(证实方向:四目录并存与独立漂移坐实,04-09 回填锚点)
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft
