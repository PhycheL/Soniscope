# Phase 2: 契约抽取与漂移分析 - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning

<domain>
## Phase Boundary

产出系统核心契约在**小程序、FC、Worker 三处实现**的逐字段漂移矩阵(每格 agree/diverge/absent + 行号证据)、往返校验结论(FC 签发的 object key → Worker `fragment_id_from_key` 可否解析)、四类分歧判定(良性/潜伏/活跃失配/覆盖洞,含 Postel 宽严分析)、跨语言重复逻辑普查;若出现非良性分歧,另产出黄金样本跨语言契约测试的**设计配方**(仅设计不实现)。分歧发现按 CHARTER 九字段 schema 写入 `.planning/audit/findings/contract.md`(F-CON-NN)。

本阶段是纯证据收集与判定:零 diff(不改 apps/、scripts/、docs/ 任何一行)、零云 IO、不对照 FC 直转目标态设计。核心待验证假设为 HYP-13(fragment_id ↔ object_key 契约三处重复实现)。

</domain>

<decisions>
## Implementation Decisions

### 契约要素清单边界(矩阵的行)
- **D-01(要素总范围 = 全接口契约):** ROADMAP 的"等"字封口为三组:① OSS 数据面 — fragment_id、object key、全部 `x-oss-meta-*` 元数据字段;② 小程序↔FC HTTP 契约 — issue-credential 与 verify-upload 的请求/响应 JSON 字段、错误码字符串(`errors.py` ↔ `uploader.js`/`verify.js` 逐字共享);③ 两侧镜像常量 — 重试节奏(5/15/45)、大小上限(50MB)等跨语言约定值。
- **D-02(行粒度 = 逐字段):** 每个元数据字段、每个 JSON 字段、每个错误码、每个镜像常量各占矩阵一行,每格独立标注状态 + 行号。预计 30-50 行,与 CONTRACT-01 "逐字段"措辞一致。
- **D-03(absent 双语义):** 格子状态区分 `n/a`(结构性不适用——该组件本就不参与此要素,如 HTTP 契约之于 Worker)与 `absent`(应参与而未实现,即覆盖洞候选)。CONTRACT-02 的覆盖洞判定直接从 absent 格读出。
- **D-04(对照声部 = 仅三列代码实现):** 矩阵严格三列(FC `fc_shared`、Worker、小程序 utils 的实现代码)。测试断言不占列,但可作格内辅助证据(证明常量被测试锁定)。文档中的契约声明不进矩阵——那是 Phase 4 AUDIT-03(DOC 维度)的地盘,避免两阶段重叠判定。

### 校验方法(静态 vs 执行)
- **D-05(静态为判据 + 执行作佐证):** 所有 agree/diverge 判定以逐行静态对照为准,证据为 `path:line @ 5927f36`(遵循 CHARTER"证据一律出自 git show"条款)。往返校验与可疑格子额外本地执行两侧纯函数(python + node)跑样本值,执行结果作为辅助证据记入矩阵,不替代静态判据。
- **D-06(执行运行规则 = 基线抽取到临时区):** 被执行的模块用 `git show 5927f36:<path>` 导出到 `.planning` 与仓库工作区之外的临时目录(scratchpad)再运行——结构性保证跑的是基线代码且仓库零触碰,不依赖"工作树未漂移"这一运行时前提。
- **D-07(样本集 = 典型+边界清单化):** 规划时先写定往返校验样本清单:典型值(当日日期、标准 fragment_id)+ 边界(chunk 后缀、非 .wav 扩展名、跨时区/跨年日期、非法字符、空字段等)。每个样本的预期行为写进矩阵附录,跑完逐项销号。该清单同时是 CONTRACT-04 黄金样本配方的胚胎。
- **D-08(零云 IO):** Phase 2 完全离线。"FC 签发的 object key"以基线代码 `fc_shared/sts.py::object_key_for` 本地执行为准;不调线上 FC、不触 OSS、不消耗 wx code。线上部署实态与代码是否一致属部署验证议题,不在本里程碑。

### 矩阵产物形态
- **D-09(矩阵独立成文件):** 漂移矩阵、往返校验记录、样本清单附录、普查章节统一放 `.planning/audit/CONTRACT-MATRIX.md`;`findings/contract.md` 只收判定后的 F-CON 发现,每条发现反向引用矩阵行,证据与判断分离。
- **D-10(四类分歧全部成发现):** 每条分歧无论良性/潜伏/活跃失配/覆盖洞都写一条 F-CON——良性→INFO/LOW,潜伏→MEDIUM 起,活跃失配→HIGH 起(参照 CHARTER 严重度锚点,"活跃失配使上传对 Worker 永久不可见"即 HIGH 锚点)。保证 RPT-02 backlog 与 RPT-08 追溯表全覆盖,且良性判定本身留下可复核痕迹。
- **D-11(每格附行号,含 agree 格):** agree 格同样写 `path:line @ 5927f36`——没有行号的 agree 只是断言不是证据,RPT-08 的"已检查无发现"需要可复核支撑。
- **D-12(Postel 分析住发现,矩阵只标类):** 矩阵行只标四类标签 + 发现 ID 链接;完整的生产者-消费者宽严分析(谁严谁宽、失配方向、触发条件)写在对应 F-CON 发现的证据/修复建议字段内。

### 重复逻辑普查与配方触发(CONTRACT-03 / CONTRACT-04)
- **D-13(普查 = 候选清单 + 系统扫描,双保险):** ① 规划时枚举已知候选逐项核实:sha256、日期格式(`YYYY-MM-DD`)、ULID/fragment_id 生成、错误码字符串、重试表、大小上限、HMAC/OSS V4 签名、配置解析;② 用 `git grep`(基线 SHA)按契约关键词对 apps/ 三层做系统扫描捕漏,扫描命令与结果存档。每项结论(含"已检查无新发现")记录在 CONTRACT-MATRIX.md 普查章节——这是 CONTRACT-03 的可验收完成判定。
- **D-14(重复入矩阵,债务移交 Phase 3):** 普查命中的重复实现拆成矩阵新行做语义对照(分歧照常走四类判定成发现);"重复存在本身是否构成技术债"不在 CON 维度下判断,作为线索移交 Phase 3 CODE 维度——与 ROADMAP 既定分工(Phase 3 的契约类观察反向移交 Phase 2)对称。
- **D-15(配方触发线 = 非良性即触发):** 潜伏/活跃失配/覆盖洞任意一条出现即产出设计配方;仅有良性分歧不触发;若全部良性则在矩阵文件显式记录"无需配方"(满足 CONTRACT-04 的 else 分支)。
- **D-16(配方深度 = 可直接开工的设计稿):** 配方为 `.planning/audit/CONTRACT-TEST-RECIPE.md`,内容:黄金样本文件 schema 与存放位置、覆盖的契约要素(引用矩阵行)、pytest 与 node:test 两侧测试骨架伪代码、make 接入点、验收标准。样本值直接复用 D-07 的往返校验清单。修复里程碑拿到即可写代码,不用再设计。

### Claude's Discretion
- 矩阵文件内部章节组织(按契约域分节还是单表)、表格具体列式排版——满足 D-02/D-11 的粒度与证据密度即可。
- 系统扫描的具体 grep 关键词集——D-13 候选清单是下限,扫描词可按勘察情况扩充。
- 往返校验边界样本的具体条目——D-07 给出的类别是下限,具体值由规划/执行敲定。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 审计规则(Phase 1 定稿,全部硬约束)
- `.planning/audit/CHARTER.md` — 基线 `5927f36`、证据格式 `path:line @ 5927f36`、`git show`/`git grep` 取证命令、九字段发现 schema、F-CON ID 规则、严重度锚点、S/M/L/XL 分档、零 diff 验证命令(阶段收尾必跑)、台账写 `.planning/audit/findings/contract.md`
- `.planning/audit/HYPOTHESES.md` — HYP-13(三处契约重复实现)为本阶段核心假设;HYP-03(sha256)、HYP-24 等与普查候选相关
- `.planning/audit/DO-NOT-FIX.md` — 已裁定的故意设计(`issue-cedential` 域名等),矩阵对照时不得当作分歧"发现"

### 需求与路线图(定义本阶段验收)
- `.planning/REQUIREMENTS.md` — CONTRACT-01~04 完整需求文本
- `.planning/ROADMAP.md` — Phase 2 目标与 5 条成功判据;与 Phase 3 的移交分工

### 契约实现现场(审计对象,按基线 5927f36 读)
- `apps/fc/shared/fc_shared/sts.py` — FC 侧 `object_key_for`(:46)与 STS 单对象键策略
- `apps/worker/src/soniscope_worker/oss_admin.py` — Worker 侧 `object_key_for`(:37)
- `apps/worker/src/soniscope_worker/poller.py` — `fragment_id_from_key`(:47,round-trip 校验)、`META_PREFIX`、元数据归一化与 manifest 映射
- `apps/miniprogram/utils/`(audio.js、oss_sign.js、uploader.js、verify.js、chunking.js、ulid.js、sha256.js、upload_queue.js)— 小程序侧 key/元数据/签名/错误码分支实现
- `apps/fc/shared/fc_shared/errors.py` — 错误码字符串常量(HTTP 契约行的 FC 侧声部)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `git show 5927f36:<path>` / `git grep -n <pat> 5927f36 -- apps/` — CHARTER 实测可用的取证命令,矩阵取证与普查扫描直接用
- 侦察已定位三处契约实现锚点:`fc_shared/sts.py:46`、`oss_admin.py:37`、`poller.py:47`(均 @ 5927f36),矩阵核心行的起点
- `x-oss-meta-*` 触点分布已知:小程序 5 个 utils 文件 + Worker `poller.py`/`pipeline.py`,元数据行的对照范围
- 双语言测试套件(pytest + `node --test`)中对契约常量的断言可作 D-04 的格内辅助证据

### Established Patterns
- 纯逻辑 + 注入 IO 模式:三处契约逻辑均为纯函数(`object_key_for`、`fragment_id_from_key`、JS utils),D-05/D-06 的本地执行佐证因此可行、无需 mock 云端
- CHARTER 九字段 schema 与 F-CON-NN ID 规则已定稿,发现条目零设计成本
- Phase 1 产物风格:中文正文 + 英文 ID/术语,矩阵与配方文档沿用

### Integration Points
- `findings/contract.md`(已建骨架)— 本阶段唯一台账写入点;Phase 5 汇总合并
- CONTRACT-MATRIX.md 的 agree 行与普查"无新发现"记录 → RPT-08 可追溯映射表的"已检查,无发现"行
- 重复债务线索 → Phase 3 CODE 维度(D-14);Phase 3 的契约类观察反向流入本阶段矩阵
- CONTRACT-TEST-RECIPE.md(若触发)→ 修复里程碑(FUTURE-02)
- 阶段收尾:跑零 diff 验证命令并记录结果(CHARTER D-03 条款)

</code_context>

<specifics>
## Specific Ideas

- 用户对"完成判定可验收"要求明确:普查必须能证明"系统排查完成"——扫描命令与结果存档,不接受主观"查过了"。
- 样本清单被刻意设计为一物两用:先当往返校验的销号清单,后当黄金样本配方的样本集(D-07 → D-16 复用链)。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-契约抽取与漂移分析*
*Context gathered: 2026-07-05*
