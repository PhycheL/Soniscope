# Phase 2: 契约抽取与漂移分析 - Research

**Researched:** 2026-07-05
**Domain:** 静态代码审计 — 跨语言(Python/JS)契约一致性对照,零 diff、零云 IO
**Confidence:** HIGH(全部关键事实经 `git show`/`git grep @ 5927f36` 实地核实)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### 契约要素清单边界(矩阵的行)
- **D-01(要素总范围 = 全接口契约):** ROADMAP 的"等"字封口为三组:① OSS 数据面 — fragment_id、object key、全部 `x-oss-meta-*` 元数据字段;② 小程序↔FC HTTP 契约 — issue-credential 与 verify-upload 的请求/响应 JSON 字段、错误码字符串(`errors.py` ↔ `uploader.js`/`verify.js` 逐字共享);③ 两侧镜像常量 — 重试节奏(5/15/45)、大小上限(50MB)等跨语言约定值。
- **D-02(行粒度 = 逐字段):** 每个元数据字段、每个 JSON 字段、每个错误码、每个镜像常量各占矩阵一行,每格独立标注状态 + 行号。预计 30-50 行,与 CONTRACT-01 "逐字段"措辞一致。
- **D-03(absent 双语义):** 格子状态区分 `n/a`(结构性不适用——该组件本就不参与此要素,如 HTTP 契约之于 Worker)与 `absent`(应参与而未实现,即覆盖洞候选)。CONTRACT-02 的覆盖洞判定直接从 absent 格读出。
- **D-04(对照声部 = 仅三列代码实现):** 矩阵严格三列(FC `fc_shared`、Worker、小程序 utils 的实现代码)。测试断言不占列,但可作格内辅助证据(证明常量被测试锁定)。文档中的契约声明不进矩阵——那是 Phase 4 AUDIT-03(DOC 维度)的地盘,避免两阶段重叠判定。

#### 校验方法(静态 vs 执行)
- **D-05(静态为判据 + 执行作佐证):** 所有 agree/diverge 判定以逐行静态对照为准,证据为 `path:line @ 5927f36`(遵循 CHARTER"证据一律出自 git show"条款)。往返校验与可疑格子额外本地执行两侧纯函数(python + node)跑样本值,执行结果作为辅助证据记入矩阵,不替代静态判据。
- **D-06(执行运行规则 = 基线抽取到临时区):** 被执行的模块用 `git show 5927f36:<path>` 导出到 `.planning` 与仓库工作区之外的临时目录(scratchpad)再运行——结构性保证跑的是基线代码且仓库零触碰,不依赖"工作树未漂移"这一运行时前提。
- **D-07(样本集 = 典型+边界清单化):** 规划时先写定往返校验样本清单:典型值(当日日期、标准 fragment_id)+ 边界(chunk 后缀、非 .wav 扩展名、跨时区/跨年日期、非法字符、空字段等)。每个样本的预期行为写进矩阵附录,跑完逐项销号。该清单同时是 CONTRACT-04 黄金样本配方的胚胎。
- **D-08(零云 IO):** Phase 2 完全离线。"FC 签发的 object key"以基线代码 `fc_shared/sts.py::object_key_for` 本地执行为准;不调线上 FC、不触 OSS、不消耗 wx code。线上部署实态与代码是否一致属部署验证议题,不在本里程碑。

#### 矩阵产物形态
- **D-09(矩阵独立成文件):** 漂移矩阵、往返校验记录、样本清单附录、普查章节统一放 `.planning/audit/CONTRACT-MATRIX.md`;`findings/contract.md` 只收判定后的 F-CON 发现,每条发现反向引用矩阵行,证据与判断分离。
- **D-10(四类分歧全部成发现):** 每条分歧无论良性/潜伏/活跃失配/覆盖洞都写一条 F-CON——良性→INFO/LOW,潜伏→MEDIUM 起,活跃失配→HIGH 起(参照 CHARTER 严重度锚点,"活跃失配使上传对 Worker 永久不可见"即 HIGH 锚点)。保证 RPT-02 backlog 与 RPT-08 追溯表全覆盖,且良性判定本身留下可复核痕迹。
- **D-11(每格附行号,含 agree 格):** agree 格同样写 `path:line @ 5927f36`——没有行号的 agree 只是断言不是证据,RPT-08 的"已检查无发现"需要可复核支撑。
- **D-12(Postel 分析住发现,矩阵只标类):** 矩阵行只标四类标签 + 发现 ID 链接;完整的生产者-消费者宽严分析(谁严谁宽、失配方向、触发条件)写在对应 F-CON 发现的证据/修复建议字段内。

#### 重复逻辑普查与配方触发(CONTRACT-03 / CONTRACT-04)
- **D-13(普查 = 候选清单 + 系统扫描,双保险):** ① 规划时枚举已知候选逐项核实:sha256、日期格式(`YYYY-MM-DD`)、ULID/fragment_id 生成、错误码字符串、重试表、大小上限、HMAC/OSS V4 签名、配置解析;② 用 `git grep`(基线 SHA)按契约关键词对 apps/ 三层做系统扫描捕漏,扫描命令与结果存档。每项结论(含"已检查无新发现")记录在 CONTRACT-MATRIX.md 普查章节——这是 CONTRACT-03 的可验收完成判定。
- **D-14(重复入矩阵,债务移交 Phase 3):** 普查命中的重复实现拆成矩阵新行做语义对照(分歧照常走四类判定成发现);"重复存在本身是否构成技术债"不在 CON 维度下判断,作为线索移交 Phase 3 CODE 维度——与 ROADMAP 既定分工(Phase 3 的契约类观察反向移交 Phase 2)对称。
- **D-15(配方触发线 = 非良性即触发):** 潜伏/活跃失配/覆盖洞任意一条出现即产出设计配方;仅有良性分歧不触发;若全部良性则在矩阵文件显式记录"无需配方"(满足 CONTRACT-04 的 else 分支)。
- **D-16(配方深度 = 可直接开工的设计稿):** 配方为 `.planning/audit/CONTRACT-TEST-RECIPE.md`,内容:黄金样本文件 schema 与存放位置、覆盖的契约要素(引用矩阵行)、pytest 与 node:test 两侧测试骨架伪代码、make 接入点、验收标准。样本值直接复用 D-07 的往返校验清单。修复里程碑拿到即可写代码,不用再设计。

### Claude's Discretion
- 矩阵文件内部章节组织(按契约域分节还是单表)、表格具体列式排版——满足 D-02/D-11 的粒度与证据密度即可。
- 系统扫描的具体 grep 关键词集——D-13 候选清单是下限,扫描词可按勘察情况扩充。
- 往返校验边界样本的具体条目——D-07 给出的类别是下限,具体值由规划/执行敲定。

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONTRACT-01 | fragment_id / object key / `x-oss-meta-*` 契约在 FC、Worker、小程序三处实现逐字段抽取为漂移矩阵(行=契约要素,列=实现,格=agree/diverge/absent + 行号) | 本文"契约现场勘察"已定位三处实现的全部锚点行号(sts.py:46 / oss_admin.py:37 / poller.py:47 / audio.js:103-105、162-168 等),并给出矩阵行清单胚胎(~40 行,符合 D-02 的 30-50 预估);Code Examples 给出取证命令模板 |
| CONTRACT-02 | 往返校验(FC 签发 object key → Worker `fragment_id_from_key` 可否解析),分歧按四类分类 + Postel 宽严分析 | "执行佐证 harness 设计"章节给出经环境实测可行的双语言执行配方(基线导出 + PYTHONPATH shadowing + TZ 控制);"样本清单素材"章节按 D-07 类别给出边界样本候选,含已勘察出的高价值边界(JS 正则不校验日期合法性、chunk_total 0↔null、本地时区日期推导) |
| CONTRACT-03 | 重复逻辑普查:三处之外的契约相关跨语言重复实现系统排查 | "普查候选与扫描词"章节:D-13 候选逐项核实结果 + 已发现的第四处 key 反推实现(`upload_queue.js::fragmentIdFromObjectKey`)+ 系统扫描 grep 关键词集(可存档命令) |
| CONTRACT-04 | 非良性分歧触发黄金样本跨语言契约测试设计配方(仅设计不实现) | "State of the Art"章节梳理黄金样本/consumer-driven 契约测试的标准形态;D-16 内容清单 + 本仓库 pytest/node:test 双套件接入点(`apps/worker/tests/test_miniprogram_js.py` 桥接模式)已核实 |
</phase_requirements>

## Summary

本阶段不是软件开发阶段,而是纯证据收集与判定阶段:产物是三份 `.planning/audit/` 下的 Markdown(CONTRACT-MATRIX.md、findings/contract.md 增量、条件触发的 CONTRACT-TEST-RECIPE.md),约束是零 diff(不改 apps/、scripts/、docs/ 一行)、零云 IO、证据一律出自基线 `5927f36`。因此本研究的重心不是"用什么库",而是三件事:① 契约现场的精确锚点(矩阵行从哪里抽);② 执行佐证 harness 的可行配方(D-05/D-06 要求基线导出后本地跑通 python + node 两侧纯函数——已实测环境全部就绪);③ 取证与普查的命令模板(CHARTER 已定标准做法,直接沿用)。

勘察已确认:三处 `object_key_for`/`fragment_id_from_key` 实现、7 个 `x-oss-meta-*` 字段的写读两端、9 个 FC 错误码/reason 字符串、重试表与大小上限镜像常量的精确行号全部可定位;并发现一条三处之外的第四处 key 反推实现(`upload_queue.js::fragmentIdFromObjectKey`,无格式校验的字符串切割)——这直接验证了 D-13 普查的必要性,是普查候选清单的既得起点。执行 harness 的关键风险(worker 模块 import 链依赖 pydantic/yaml、fc_shared `__init__.py` 全量导入、audio.js require `../config`、JS 日期推导依赖本地时区)均已识别并给出实测可行的规避方案。

**Primary recommendation:** 按"先抽取(矩阵行 + agree/diverge 静态判定)→ 再执行佐证(harness 跑样本清单销号)→ 后判定(四类分类成 F-CON 发现)→ 条件产配方"的顺序组织计划;全部取证只用 `git show`/`git grep`/`git archive` 三个基线命令,执行佐证统一走 scratchpad 导出 + 仓库 .venv/系统 node,阶段收尾必跑零 diff 验证命令。

## Architectural Responsibility Map

本阶段无运行时架构;下表把阶段能力映射到证据来源与产物归属(供 planner 分配任务边界)。

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 矩阵行抽取与静态对照(CONTRACT-01) | 基线取证(`git show`/`git grep @ 5927f36`) | — | CHARTER D-02 条款:证据禁止出自工作树 |
| 往返校验执行佐证(CONTRACT-02) | scratchpad harness(`git archive` 导出 + repo `.venv` python + 系统 node) | 静态判据(执行只作佐证,D-05) | D-06:跑的必须是基线代码且仓库零触碰 |
| 四类分歧判定 + Postel 分析 | 人工判定,写入 `findings/contract.md`(F-CON) | 矩阵行标签(D-12:矩阵只标类) | 证据与判断分离(D-09) |
| 重复逻辑普查(CONTRACT-03) | `git grep <关键词> 5927f36 -- apps/` 系统扫描 | D-13 候选清单逐项核实 | 双保险;命令与结果存档为验收判定 |
| 测试配方设计(CONTRACT-04,条件触发) | `.planning/audit/CONTRACT-TEST-RECIPE.md` 纯文档 | D-07 样本清单复用 | 仅设计不实现;修复里程碑消费 |
| 阶段收尾零 diff 验证 | `git diff --stat 5927f36 -- apps/ scripts/ docs/`(期望空输出) | — | CHARTER D-03 硬约束,每阶段必跑并记录 |

## Standard Stack

本阶段**不安装任何外部包、不新增任何依赖**。全部工具为环境既有:

### Core
| 工具 | 版本(实测) | 用途 | 为何标准 |
|------|------------|------|----------|
| `git show` / `git grep` / `git archive` / `git diff --stat` | git 2.23.0 [VERIFIED: 本机实测] | 基线取证、普查扫描、基线导出、零 diff 验证 | CHARTER 写定的标准做法,前两类已在仓库实测可用;`git archive 5927f36 <path> \| tar -x` 本次亦实测可用 |
| repo `.venv` python | Python(pydantic 2.13.4、yaml 可 import)[VERIFIED: 本机实测] | 执行 FC/Worker 侧纯函数佐证 | `make install` 产物,含 worker 全部依赖,免网络安装(守住零云 IO 精神) |
| node | v22.18.0 [VERIFIED: 本机实测] | 执行小程序侧纯函数佐证 | 仓库既有 JS 测试即用 `node --test`;utils 为零依赖 CommonJS,`require` 即可运行 |
| 系统 python3 | 3.13.2 [VERIFIED: 本机实测] | 备选:执行 `fc_shared`(纯 stdlib import 链)时可不经 .venv | fc_shared/sts.py 仅依赖 stdlib + 同包 errors.py |

### Supporting
| 工具 | 用途 | When to Use |
|------|------|-------------|
| scratchpad 目录(`/private/tmp/claude-501/...juju/scratchpad` 或执行时会话自带) | D-06 的基线代码导出运行区 | 所有执行佐证;严禁把 harness 写进仓库工作区 |
| `uv run --project /Volumes/Data/ProjectCode/my_soniscope python` | .venv 的等价入口 | 若直接调 `.venv/bin/python` 不便时 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `git archive \| tar -x` 整树导出 | 逐文件 `git show > file` | 逐文件会丢目录结构,`audio.js` 的 `require('../config')` 与 `soniscope_worker` 包内相对 import 会断;整树导出结构性保真,首选 |
| repo `.venv` python | scratchpad 内新建 venv + pip install pydantic pyyaml | 需要网络下载,且引入"harness 环境≠仓库环境"的解释成本;.venv 已含全部依赖,直接用 |
| 在导出代码上直接 import | 手抄函数体进 harness | 手抄即篡改证据链,禁止(见 Don't Hand-Roll) |

**Installation:** 无需安装。执行前只需确认(见 Environment Availability)。

## Package Legitimacy Audit

**不适用。** 本阶段零安装、零新依赖——产物全部为 `.planning/audit/` 下 Markdown 文档,执行佐证复用仓库既有 `.venv` 与系统 node。无包需要审计。

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## 契约现场勘察(矩阵行清单胚胎)

以下锚点全部经 `git show`/`git grep @ 5927f36` 核实 [VERIFIED: codebase @ 5927f36]。这是 planner 拆分矩阵行任务的直接素材;**注意:本节只列"对照点",不预判 agree/diverge——判定是执行阶段的工作**。

### 组① OSS 数据面(D-01 ①)

| 契约要素 | FC (`fc_shared`) | Worker | 小程序 |
|----------|------------------|--------|--------|
| fragment_id 格式正则 | `sts.py:28-32`(`_FRAGMENT_ID_RE`,含命名捕获组 + 后续 `datetime()` 日期合法性校验) | `oss_admin.py:24-27`(同名正则)| `audio.js:95-97`(`FRAGMENT_ID_RE`,**无** datetime 合法性校验——往返样本高价值边界)|
| object key 模板 `recordings/<YYYY-MM-DD>/<id>.wav` | `sts.py:46-59`(`object_key_for`,日期取自 fragment_id 前缀)| `oss_admin.py:37-50`(`object_key_for`)| `audio.js:103-105`(`buildObjectKeyPreview`,**日期取自 `recordedAt` 本地时区**,与 fragment_id 前缀为两个独立入参)|
| key → fragment_id 反推 | n/a 候选(FC 只正向签发)| `poller.py:47-60`(`fragment_id_from_key`,往返校验式)| `upload_queue.js:36-44`(`fragmentIdFromObjectKey`,纯字符串切割无校验——普查发现的第四处)|
| `.wav` 固定扩展名 | `sts.py:59`(f-string 尾部)| `poller.py:52`(endswith 检查)| `config.js`(`OSS_OBJECT_KEY_EXT` 常量,由 `audio.js:10` require)|
| 7 个 `x-oss-meta-*` 字段(session-id/chunk-seq/chunk-total/recorded-at/duration/original-format/sha256) | n/a 候选(FC 不读写 meta;是否该读属覆盖洞判定)| `poller.py:33-40`(META_* 常量)、`poller.py:85-93`(`normalize_metadata` 前缀剥离)、`poller.py:132+`(manifest 映射)| `audio.js:158-170`(`buildOssMetadata` 写入端,162-168 逐键)|
| chunk_total 语义(非分片) | — | `poller.py` ManifestDraft docstring:OSS `"0"` → manifest `None` | `audio.js:157`:manifest `null` → OSS meta `"0"` |
| recorded-at 值格式 | — | `poller.py` 映射端 | `audio.js:75-86`(`toIso`,本地时区偏移 ISO 8601)|

### 组② 小程序↔FC HTTP 契约(D-01 ②)

| 契约要素 | FC 侧 | 小程序侧 | Worker |
|----------|-------|----------|--------|
| issue-credential 请求字段(code/fragment_id/size) | `issue_credential/handler.py` + `sts.py:74-90`(`parse_size`)| `uploader.js`(请求组装)| n/a |
| issue-credential 响应 7 字段 | `sts.py:102-114`(`credential_response`)| `uploader.js:102`(AC#4:object_key 用 FC 返回值不由前端拼接——往返链的关键环)| n/a |
| verify-upload 请求/响应字段(verified/reason/…) | `verify_upload/handler.py` + `fc_shared/head.py` | `verify.js` | n/a |
| 7 个 HTTP 错误码字符串 | `errors.py:13-19`(INVALID_CODE/OPENID_NOT_ALLOWED/INVALID_REQUEST/SIZE_EXCEEDED/SERVER_MISCONFIGURED/STS_ISSUE_FAILED/HEAD_OBJECT_FAILED)| `uploader.js`/`verify.js` 的分支字面量(勘察见 JS 侧仅 `verify.js:20-21` 有 reason 字面量;错误码分支的实际存在性/缺席是矩阵要回答的问题)| n/a |
| 2 个 verify reason(OBJECT_NOT_FOUND/SIZE_MISMATCH) | `errors.py:23-25` | `verify.js:20-21`(REASON_* 常量)| n/a |

### 组③ 两侧镜像常量(D-01 ③)

| 契约要素 | 一侧 | 另一侧 |
|----------|------|--------|
| 重试节奏 5/15/45、最多 3 次 | `nls.py:45`(`RETRY_DELAYS_SECONDS = (5.0, 15.0, 45.0)`)| `uploader.js:28-29`(`RETRY_DELAYS_MS = [5000,15000,45000]`)、`verify.js:16-17`(`VERIFY_RETRY_DELAYS_MS`)|
| 上传大小上限 50 MB | `env.py:41`(`DEFAULT_MAX_UPLOAD_BYTES = 52428800`)| 小程序侧是否有对应常量/预检待矩阵回答(absent/n/a 判定点)|
| 分片阈值 600 s | — | `config.js:22-23`(`CHUNK_MAX_DURATION_SECONDS = 600`);Worker/FC 侧是否有感知待判定 |
| STS 时长 ≤900 s | `sts.py:24-25`(`STS_MAX_DURATION_SECONDS = 900`)| 小程序对 expiration 的消费方式待判定 |

行数合计约 35-45 行(逐字段展开后),落在 D-02 预估的 30-50 区间内。

## 普查候选与扫描词(CONTRACT-03 素材)

D-13 候选清单逐项勘察结果(核实=定位到具体文件,判定留给执行):

| 候选 | 勘察定位 [VERIFIED: codebase @ 5927f36] |
|------|------|
| sha256 | JS 纯实现 `utils/sha256.js`;Worker `fixtures.py`(hashlib)+ `poller.py` 比对逻辑;关联 HYP-03 |
| 日期格式 `YYYY-MM-DD` | `audio.js::objectKeyDate`(本地时区)vs `sts.py`/`oss_admin.py`(从 fragment_id 前缀拼接)vs `poller.py::date_of`(从 key 切割)|
| ULID / fragment_id 生成 | `utils/ulid.js`(唯一生成端);FC/Worker 只解析不生成(n/a 判定素材)|
| 错误码字符串 | `errors.py` ↔ `verify.js:20-21`(reason);uploader.js 错误码分支存在性待查 |
| 重试表 | `nls.py:45` ↔ `uploader.js:28` ↔ `verify.js:16`(注意:JS 有两份)|
| 大小上限 | `env.py:41` 单侧;对侧 absent/n/a 待判定 |
| HMAC / OSS V4 签名 | `utils/hmac.js` + `utils/oss_sign.js`(小程序侧);Worker 侧 SDK 内置(n/a 判定素材)|
| 配置解析 | Worker `config.py`(pydantic)vs 小程序 `config.js`(常量模块)vs FC `env.py`(env 解析)——三种机制解析同族值 |
| **新发现:key 反推第四处** | `upload_queue.js:36-44`(`fragmentIdFromObjectKey`)——三处已知实现之外,普查起点即有一命中 |

系统扫描关键词集(下限,Claude's discretion 可扩充;命令须存档):

```bash
git grep -nE 'recordings/|x-oss-meta|fragment_?[iI]d|object_?[kK]ey' 5927f36 -- apps/
git grep -nE 'sha256|SHA-?256' 5927f36 -- apps/
git grep -nE '\b(5000|15000|45000)\b|\b(5\.0|15\.0|45\.0)\b|52428800' 5927f36 -- apps/
git grep -nE 'YYYY-MM-DD|toISOString|isoformat|strftime|getTimezoneOffset' 5927f36 -- apps/
git grep -nE 'INVALID_CODE|OPENID_NOT_ALLOWED|SIZE_EXCEEDED|INVALID_REQUEST|OBJECT_NOT_FOUND|SIZE_MISMATCH|SERVER_MISCONFIGURED|STS_ISSUE_FAILED|HEAD_OBJECT_FAILED' 5927f36 -- apps/
```

注意排除 `apps/miniprogram/test/`、`apps/worker/tests/`、`apps/fc/tests/` 命中作为矩阵列(D-04:测试不占列,只作格内辅助证据),但测试命中**应记录**为常量锁定证据。

## Architecture Patterns

### System Architecture Diagram

本阶段的"架构"是证据流水线:

```text
基线 5927f36 (git object store, 只读)
   │
   ├─ git show/grep ──────────► 静态对照 ──► CONTRACT-MATRIX.md 矩阵格
   │                             (判据, D-05)      │  agree/diverge/absent/n/a + path:line
   │                                               │
   ├─ git archive | tar -x ──► scratchpad 导出树   │
   │                             │                 │
   │                    python(.venv) + node       │
   │                    跑 D-07 样本清单 ──────────► 矩阵附录(执行佐证, 逐项销号)
   │                             (佐证, 不替代判据)  │
   │                                               ▼
   │                                    四类判定(良性/潜伏/活跃失配/覆盖洞)
   │                                               │
   │                                               ▼
   │                              findings/contract.md (F-CON-NN, 九字段 schema,
   │                               Postel 分析住发现内, D-12)
   │                                               │
   │                              非良性存在? ──yes─► CONTRACT-TEST-RECIPE.md (D-15/D-16)
   │                                        └─no──► 矩阵内显式记录"无需配方"
   │
   └─ 收尾: git diff --stat 5927f36 -- apps/ scripts/ docs/  (期望空, 结果记录)
```

### Recommended Project Structure(产物)

```text
.planning/audit/
├── CONTRACT-MATRIX.md        # 新建:漂移矩阵 + 往返校验记录 + 样本清单附录 + 普查章节(含扫描命令存档)
├── CONTRACT-TEST-RECIPE.md   # 条件新建:仅当出现非良性分歧(D-15)
└── findings/contract.md      # 追加:F-CON-NN(九字段 schema, F-CON-00 示例已在骨架内)
```

### Pattern 1: 矩阵格证据格式(D-11)

**What:** 每格 = 状态标签 + `path:line @ 5927f36`,agree 格同样带行号。
**When to use:** 矩阵所有格。n/a 格写一句结构性理由代替行号(如"Worker 不参与 HTTP 契约")。

```markdown
| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|---|---|---|---|---|
| object key 模板 | agree `fc_shared/sts.py:59 @ 5927f36` | agree `oss_admin.py:50 @ 5927f36` | agree `audio.js:105 @ 5927f36` | — |
| fragment_id 日期合法性校验 | (状态) `sts.py:52-56 @ 5927f36` | (状态) `oss_admin.py:44-48 @ 5927f36` | (状态) `audio.js:95-97 @ 5927f36` | (四类标签 + F-CON-NN 链接) |
```

### Pattern 2: 执行佐证 harness(D-05/D-06,已实测可行)

**What:** `git archive` 把基线代码整树导出到 scratchpad,python 用 PYTHONPATH 让导出树遮蔽已安装包,node 直接 require 导出树;每次运行先断言模块来源指向 scratchpad。
**When to use:** 往返校验样本清单销号 + 可疑格子的行为对照。
**关键实测事实:**
- `poller.py` import 链:`soniscope_worker.config`(→ pydantic + yaml)、`.fixtures`、`.oss_admin`、`.paths` — 因此**必须用 repo `.venv` 的 python** 才 import 得动 [VERIFIED: git show import 头 + .venv import 实测]
- `fc_shared/sts.py` 仅依赖 stdlib + 同包 `.errors`;但 `import fc_shared.sts` 会触发 `fc_shared/__init__.py` 全量导入(`__init__.py:16+`)——若其中任何子模块顶层 import 云 SDK 会连坐。仓库红线是云 SDK 全部 lazy import,且 .venv 本身装有这些 SDK,双保险 [VERIFIED: __init__.py 头 + CLAUDE.md lazy-import 约定]
- `audio.js:10` `require('../config')` — 导出树必须同时含 `apps/miniprogram/config.js` 并保持目录结构 [VERIFIED: git show]
- JS 侧 `objectKeyDate`/`fragmentTimestamp`/`toIso` 全部依赖**本地时区**(`localDateParts`/`getTimezoneOffset`)——跨时区样本用 `TZ=<zone> node ...` 控制 [VERIFIED: git show audio.js:63-86]
- PYTHONPATH 条目在 sys.path 中先于 site-packages(含 editable install 的 .pth),导出树可靠遮蔽已安装的 soniscope-worker [ASSUMED — 标准 CPython 行为;harness 内以 `__file__` 断言兜底,断言失败即中止]

### Pattern 3: F-CON 发现条目(CHARTER 九字段)

九字段 schema、ID 规则、严重度锚点、S/M/L/XL 分档全部照抄 `.planning/audit/CHARTER.md`;`findings/contract.md` 已有 F-CON-00 示例骨架。发现须:反向引用矩阵行(D-09)、Postel 宽严分析写在证据/修复建议字段(D-12)、四类→严重度映射按 D-10(良性→INFO/LOW、潜伏→MEDIUM 起、活跃失配→HIGH 起)。关联字段挂 HYP-13(核心假设)及相关 HYP(如 sha256 行挂 HYP-03)。

### Anti-Patterns to Avoid

- **把 DO-NOT-FIX 条目当分歧发现:** `issue-cedential` 拼写域名(DNF-02)、小程序接收原始 STS 秘密(DNF-04)等已裁定故意设计,矩阵对照时不得再立 F-CON(CONTEXT canonical_refs 明令)。
- **读工作树取证:** 一切行号出自 `git show 5927f36:<path>`;工作树只是碰巧干净,不是证据来源(CHARTER 结构性免疫条款)。
- **预判代替对照:** 勘察发现的"疑点"(JS 正则无日期校验、chunk_total 0↔null、第四处反推实现)是**待对照线索**,不是结论;每条须走静态对照 + 样本执行后才判类。
- **矩阵里写 Postel 长分析:** D-12 — 矩阵格只标四类标签 + F-CON 链接,分析住发现。
- **把执行结果当判据:** D-05 — 执行只是佐证;agree/diverge 的裁决理由必须能从静态行号对照独立成立。
- **harness 写进仓库:** 任何辅助脚本只存在于 scratchpad;`.planning/` 只收 Markdown 产物。收尾零 diff 命令是报警器。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 基线代码导出 | 手抄函数体 / 复制粘贴进 harness | `git archive 5927f36 <paths> \| tar -x -C $SCRATCH` | 手抄即引入转录误差,佐证结论失去证据效力;整树导出保 import/require 结构 |
| Python 执行环境 | scratchpad 里 pip install 新环境 | repo `.venv/bin/python` + PYTHONPATH 遮蔽 | 零网络、零新依赖;.venv 已含 pydantic 2.13.4/yaml [VERIFIED: 实测] |
| 发现记录格式 | 自定义条目模板 | CHARTER 九字段 schema + `findings/contract.md` 既有 F-CON-00 骨架 | Phase 5 汇总合并依赖统一 schema |
| 严重度/工作量判定标准 | 临场发明 | CHARTER 严重度锚点表 + S/M/L/XL 判定标准 | 锚点封死裁量空间,"活跃失配使上传对 Worker 永久不可见"= HIGH 明文锚点 |
| 普查完成判定 | 主观"查过了" | 扫描命令 + 输出结果原样存档在矩阵普查章节 | 用户明确要求可复核的"系统排查完成"证明(CONTEXT specifics)|
| JS 日期边界控制 | 改 harness 代码里的 Date 构造 | `TZ=<zone>` 环境变量驱动 node 进程 | 不触碰导出代码,一份代码多时区复跑 |

**Key insight:** 本阶段的"工具链"就是 git 的三个只读命令 + 两个既有解释器;任何自建工具都在稀释证据链的可信度。

## D-07 样本清单素材(往返校验边界候选)

D-07 类别为下限,以下为勘察后建议的具体化(执行时可再扩充;每个样本须在矩阵附录写预期行为再销号):

| 类别(D-07) | 具体样本候选 | 勘察依据 |
|------|------|------|
| 典型值 | `20260704T101500_dev01a_01HZX3K8MN5PQR9TFB7AYWVCDE`(仓库测试通用形态)| 测试文件普遍使用此形态 [VERIFIED: test/oss_sign.test.js:43 等] |
| 非法日期但正则可过 | `20261332T101500_...`(13 月 32 日)| FC/Worker 有 `datetime()` 合法性校验,JS 正则无——三处行为可能分叉的高价值样本 |
| 闰日/跨年 | `20240229T...`(合法闰日)、`20251231T235959_...` | 日期合法性 + 目录日期一致性双重检验 |
| 跨时区 | 同一 `recordedAt` 在 `TZ=Asia/Shanghai` 与 `TZ=America/New_York` 下跑 `buildObjectKeyPreview` + `buildFragmentId` | JS 侧日期取本地时区;fragment_id 前缀与 key 目录日期是否恒一致是往返核心 |
| 近午夜 | `recordedAt = 23:59:59` 本地时刻 | `buildObjectKeyPreview(fragmentId, recordedAt)` 两入参独立,近午夜是否可能错位 |
| deviceShortId 边界 | 3 字符(过短)、9 字符(过长)、含 `-`/`_` 非法字符 | 正则 `[A-Za-z0-9]{4,8}` 三处一致性 |
| ULID 边界 | 25/27 字符、含 `I/L/O/U`(Crockford 排除字符,但三处正则用 `[0-9A-Za-z]` 宽于 Crockford)| 正则宽严 vs ulid.js 实际生成字符集 |
| 非 .wav key | `recordings/2026-07-04/<id>.m4a` | `fragment_id_from_key` 的 endswith 拒绝路径 vs `fragmentIdFromObjectKey` 的照单全收 |
| chunk 后缀 | 分片场景的 fragment_id 形态(以 `chunking.js` 实际产出为准)| D-07 点名类别 |
| 空/畸形 | 空串、无 `_` 分隔、目录日期与前缀日期不一致的 key(`recordings/2026-07-05/20260704T...wav`)| `fragment_id_from_key` 往返等式恰好防这个;第四处实现防不防? |

此清单同时是 CONTRACT-TEST-RECIPE.md 黄金样本集的胚胎(D-07→D-16 复用链)。

## Common Pitfalls

### Pitfall 1: harness import 到已安装包而非基线导出树
**What goes wrong:** `.venv` 里 editable-install 的 soniscope-worker 遮蔽 scratchpad 导出树,跑的是工作树代码。
**Why it happens:** sys.path 顺序误判。
**How to avoid:** PYTHONPATH 前置导出树;harness 首行断言 `soniscope_worker.__file__`/`fc_shared.__file__` 以 scratchpad 前缀开头,失败即退出。
**Warning signs:** `__file__` 指向 `/Volumes/Data/ProjectCode/my_soniscope/`。

### Pitfall 2: JS 本地时区污染样本结论
**What goes wrong:** 时区相关样本在执行机默认时区(可能非 Asia/Shanghai)下跑出的结果被当成"小程序行为"。
**Why it happens:** `audio.js` 日期系列函数全走本地时区,WeChat 真机时区≠审计机时区。
**How to avoid:** 所有 JS 时区敏感样本显式 `TZ=` 运行且把 TZ 记进佐证记录;矩阵附录注明"执行佐证反映指定 TZ 下的行为"。
**Warning signs:** 佐证记录里没写 TZ。

### Pitfall 3: 把"疑点"直接写成 diverge
**What goes wrong:** 勘察印象(如 JS 正则缺日期校验)未经完整静态对照就落格,四类判定失去 Postel 分析支撑。
**Why it happens:** 疑点看似显然。
**How to avoid:** 每格必须先落两侧行号证据再落状态;判类走 F-CON 条目的宽严分析(D-12),矩阵只回填标签。
**Warning signs:** 格里有状态没行号,或有 diverge 无对应 F-CON。

### Pitfall 4: DO-NOT-FIX / 排除项误入矩阵发现
**What goes wrong:** `issue-cedential` 域名、STS 原始秘密下发被当契约分歧立 F-CON;或对照引入 `docs/fc-transcribe-design.md` 目标态。
**How to avoid:** 计划里显式引用 DNF-01~04 与 CHARTER 排除项表作为矩阵判定的负面清单;目标态对照是 CHARTER 明文排除项。
**Warning signs:** F-CON 证据引用 docs/ 设计文档。

### Pitfall 5: chunk_total 这类"故意不对称"误判
**What goes wrong:** 小程序 manifest `null` ↔ OSS meta `"0"` ↔ Worker manifest `None` 的三段映射被机械判 diverge。
**Why it happens:** 值形态不同但语义约定一致(§3.2 约定,两侧注释均声明)[VERIFIED: audio.js:157 注释 + poller.py ManifestDraft docstring]。
**How to avoid:** 判定标准写清:"diverge 指语义分歧,不是字面差异";字面异/语义同的格标 agree 并在格内注明映射约定行号。
**Warning signs:** 仅因类型/字面不同就判 diverge。

### Pitfall 6: 零 diff 验证的保护范围误解
**What goes wrong:** 以为 `git diff --stat 5927f36 -- apps/ scripts/ docs/` 覆盖一切;实际 Makefile、pyproject.toml 等根文件不在其内。
**How to avoid:** 本阶段本就不应触碰任何仓库文件(.planning 除外);收尾除跑命令外,git status 应只见 `.planning/` 变更。
**Warning signs:** 收尾时 status 出现非 .planning 路径。

### Pitfall 7: 普查扫描命中测试文件后处理不当
**What goes wrong:** 测试文件里的契约字面量(如 test/oss_sign.test.js 的样本 key)被立为第四声部,违反 D-04;或被直接丢弃,丢失"常量被测试锁定"的辅助证据。
**How to avoid:** 扫描结果分两栏归档:实现命中(进矩阵行)/测试命中(格内辅助证据)。

### Pitfall 8: 矩阵行爆炸失控
**What goes wrong:** 普查命中 + HTTP 字段逐个展开后行数远超 50,矩阵可读性崩坏、工期失控。
**How to avoid:** 按 D-02 预估 30-50 行为健康区间;普查新行只收"承载契约的逻辑"(CONTRACT-03 原文限定),非契约重复移交 Phase 3(D-14)。矩阵按三组分节(Claude's discretion)控制单表规模。

## Code Examples

以下命令均已在本机实测或由 CHARTER 声明实测 [VERIFIED: 本机实测 / CHARTER]。

### 取证:按基线读文件与检索

```bash
git show 5927f36:apps/fc/shared/fc_shared/sts.py | sed -n '40,60p'
git grep -n 'x-oss-meta' 5927f36 -- apps/
```

### 基线导出到 scratchpad(执行佐证前置)

```bash
SCRATCH=<会话 scratchpad>/phase2-baseline
mkdir -p "$SCRATCH"
git -C /Volumes/Data/ProjectCode/my_soniscope archive 5927f36 \
  apps/worker/src apps/fc/shared apps/miniprogram/utils apps/miniprogram/config.js \
  | tar -x -C "$SCRATCH"
```

### Python 侧 harness 运行(往返校验)

```bash
# harness.py 用 Write 工具写入 $SCRATCH(不落仓库);内容要点:
#   import sys; import soniscope_worker.poller as poller; import fc_shared.sts as fc_sts
#   assert poller.__file__.startswith("<SCRATCH>"), poller.__file__   # 来源断言
#   assert fc_sts.__file__.startswith("<SCRATCH>"), fc_sts.__file__
#   key = fc_sts.object_key_for(sample)          # FC 签发路径(D-08: 本地执行为准)
#   round_trip = poller.fragment_id_from_key(key)  # Worker 解析路径
PYTHONPATH="$SCRATCH/apps/worker/src:$SCRATCH/apps/fc/shared" \
  /Volumes/Data/ProjectCode/my_soniscope/.venv/bin/python "$SCRATCH/harness.py"
```

### Node 侧 harness 运行(小程序声部,含时区控制)

```bash
# harness.js 写入 $SCRATCH;require 导出树(config.js 相对路径已保真):
#   const audio = require('<SCRATCH>/apps/miniprogram/utils/audio.js')
#   const uq = require('<SCRATCH>/apps/miniprogram/utils/upload_queue.js')
TZ=Asia/Shanghai node "$SCRATCH/harness.js"
TZ=America/New_York node "$SCRATCH/harness.js"   # 跨时区样本复跑
```

### 阶段收尾:零 diff 验证(CHARTER D-03,必跑必记)

```bash
git diff --stat 5927f36 -- apps/ scripts/ docs/   # 期望空输出;结果记入矩阵文件收尾章节
```

## State of the Art

CONTRACT-04 配方对应的业界标准形态(仅供配方设计参考,决策已被 D-16 锁定):

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| 两侧各写各的单元测试断言常量 | 共享黄金样本文件(单一 JSON/fixture 为真值源),双语言测试套件同读 | 契约漂移在 `make test` 即暴露,而非线上静默失配 [ASSUMED — 黄金样本/golden file 测试为业界通行模式] |
| 跨语言契约靠文档同步 | consumer-driven / 双端往返测试(producer 产出 → consumer 解析 → 断言等式)| 本仓库 `fragment_id_from_key` 已内建往返等式思想,配方可直接延伸 [VERIFIED: poller.py:47-60 docstring] |

配方接入点(已核实):本仓库已有 pytest → node 桥接先例 `apps/worker/tests/test_miniprogram_js.py`(pytest 内起 `node --test`,node 缺席则 skip)[VERIFIED: CLAUDE.md + testpaths 配置]——配方的 make 接入设计应复用该桥接模式,样本文件位置建议在配方中给出仓库内路径(实现属修复里程碑,本阶段仅纸面设计,不违反零 diff)。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PYTHONPATH 条目先于 site-packages/editable .pth,导出树可靠遮蔽已安装包 | Pattern 2 | 佐证跑到工作树代码;已设计 `__file__` 断言兜底,断言失败即暴露,残余风险≈0 |
| A2 | `fc_shared/__init__.py` 的全量子模块导入不会在 import 时触网(云 SDK 全 lazy) | Pattern 2 | import 失败或意外网络调用;.venv 含全部 SDK 兜底 import,零云 IO 由"不调用任何网络函数"保证——计划应含一次冒烟 import 验证 |
| A3 | 黄金样本/consumer-driven 为跨语言契约测试的业界标准形态 | State of the Art | 仅影响配方措辞;配方结构已被 D-16 锁定,不依赖此论断 |
| A4 | 矩阵行数落在 30-50(勘察估算 ~40) | 契约现场勘察 | 若普查命中远超预期,行数上探;D-14 的移交规则与"仅限承载契约的逻辑"限定是泄压阀 |

## Open Questions

1. **uploader.js 是否真的逐字分支 FC 错误码?**
   - What we know:CLAUDE.md 声称"uploader.js branches on the same strings";grep 只在 `verify.js:20-21` 见 reason 字面量,uploader.js 未见错误码字面量命中。
   - What's unclear:uploader.js 可能按 statusCode 段而非错误码字符串分支——这正是矩阵 HTTP 组要回答的 agree/absent/n/a 判定,不是研究该预判的。
   - Recommendation:列为矩阵行,执行时以 `classifyFcResponse` 全文对照裁决;CLAUDE.md 声明与实态不符本身可能是 Phase 4 DOC 维度线索(记入移交)。
2. **verify-upload 的请求/响应字段全集**
   - What we know:reason 两常量、HEAD_OBJECT_FAILED 码已定位;handler.py 与 head.py 未逐行展开。
   - Recommendation:planner 把"verify-upload 字段抽取"设为独立矩阵子任务,以 `git show 5927f36:apps/fc/verify_upload/handler.py` + `fc_shared/head.py` 为准。
3. **chunking 场景的 fragment_id 形态**
   - What we know:`chunking.js` 存在、`CHUNK_MAX_DURATION_SECONDS=600`;分片是否影响 fragment_id/key 形态未展开。
   - Recommendation:D-07 已点名"chunk 后缀"样本类别;执行时以 chunking.js 实际产出定样本值。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git(show/grep/archive/diff)| 全部取证与导出 | ✓ | 2.23.0(基线命令实测可用)| — |
| repo `.venv` python(pydantic+yaml)| Python 侧执行佐证 | ✓ | pydantic 2.13.4 in venv | `uv run --project <repo> python`(uv 0.8.14 ✓)|
| node | JS 侧执行佐证 | ✓ | v22.18.0 | 无 node 时 JS 声部退化为纯静态判定(D-05 允许:静态本就是判据)|
| 系统 python3 | fc_shared 纯 stdlib 备选 | ✓ | 3.13.2 | .venv python |
| scratchpad 目录 | D-06 基线运行区 | ✓ | 会话自带 | — |
| 网络 / 云凭证 | — | 不需要 | — | D-08 零云 IO,结构性无此依赖 |

**Missing dependencies with no fallback:** 无。全部就绪。

## Validation Architecture

> 本阶段产物为审计文档,不写产品代码、不新增测试;"验证"= 产物完备性与零 diff 检查,均为 <30s 命令。

### Test Framework
| Property | Value |
|----------|-------|
| Framework | 无新增(仓库既有 pytest/node:test 不被本阶段触碰)|
| Quick run command | 见下表逐需求命令 |
| Full suite command | 阶段收尾组合检查(下表全部 + 零 diff)|

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONTRACT-01 | 矩阵存在且每格带行号证据 | doc check | `grep -c '@ 5927f36' .planning/audit/CONTRACT-MATRIX.md`(应 ≥ 行数×参与列数量级)| ❌ 本阶段产出 |
| CONTRACT-02 | 往返校验记录 + 样本逐项销号 | doc check + harness rerun | 矩阵附录逐样本有"预期/实测/销号"三元组;harness 命令可重放 | ❌ 本阶段产出 |
| CONTRACT-03 | 普查命令与结果存档,含"无新发现"显式行 | doc check | 矩阵普查章节含每条扫描命令原文 + 输出归档 | ❌ 本阶段产出 |
| CONTRACT-04 | 配方成文或"无需配方"显式记录 | doc check | `ls .planning/audit/CONTRACT-TEST-RECIPE.md \|\| grep '无需配方' CONTRACT-MATRIX.md` | ❌ 条件产出 |
| (CHARTER D-03) | 仓库零污染 | smoke | `git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空 | ✓ 命令已定 |
| (D-10) | 每条 diverge 有对应 F-CON | doc cross-check | 矩阵 diverge 格的 F-CON 链接与 `grep '^### F-CON-' findings/contract.md` 对账 | ❌ 本阶段产出 |

### Sampling Rate
- **Per task commit:** 零 diff 命令(空输出)+ 本任务产物文档的自查 grep
- **Phase gate:** 上表全部通过 + 零 diff 结果记录在案

### Wave 0 Gaps
None — 本阶段不需要测试基础设施;harness 脚本属 scratchpad 临时物,不入仓库。

## Security Domain

> 本阶段为只读审计,不新增运行时代码或攻击面;ASVS 运行时类目(V2/V3/V4 认证/会话/访问控制)结构性 n/a。适用的安全约束来自 CHARTER,全部为文档纪律:

| 约束 | Standard Control |
|------|-----------------|
| 秘密类证据红线 | 矩阵/发现引用疑似秘密只写 `path:line @ 5927f36` + 模式名,**绝不复制值本体**(含已过期值)——.planning 提交即永久入库(CHARTER 红线)|
| 顺带安全发现 | 契约对照中若顺带撞见安全问题,照常九字段进台账并标 `顺带发现(out-of-dimension)`,不自动升级严重度(CHARTER 条款)|
| 无例外协议 | 即使发现 CRITICAL 级契约问题,只进台账标注,不中断审计、不动云端、不改代码(CHARTER D-04)|
| harness 安全 | 执行佐证只调用纯函数,不 import 任何会发起网络的调用路径;样本值全为合成数据,不含真实 openid/凭证 |

### Known Threat Patterns
本阶段唯一现实威胁是**审计产物自身泄密**(把代码中读到的敏感字符串抄进 .planning 文档),缓解即上表第一条红线;执行 agent 的 prompt/计划中应显式重申。

## Sources

### Primary (HIGH confidence)
- `git show`/`git grep`/`git archive` @ `5927f36` — 全部契约锚点行号、import 链、常量值(本次会话逐条实测)
- `.planning/audit/CHARTER.md` — 证据格式、schema、严重度锚点、零 diff 命令、秘密红线
- `.planning/audit/HYPOTHESES.md`(HYP-03/13/24)、`.planning/audit/DO-NOT-FIX.md`(DNF-01~04)
- `.planning/phases/02-contract-extraction-drift/02-CONTEXT.md` — 全部锁定决策
- 本机环境探针:git 2.23.0 / node v22.18.0 / python3 3.13.2 / uv 0.8.14 / .venv(pydantic 2.13.4)

### Secondary (MEDIUM confidence)
- `./.claude/CLAUDE.md` — 架构与约定描述(个别声明与实态的出入本身即审计对象,见 Open Question 1)

### Tertiary (LOW confidence)
- 黄金样本/consumer-driven 契约测试为业界标准形态 — 训练知识,[ASSUMED],仅影响配方措辞

## Project Constraints (from CLAUDE.md)

- 产出形态:仅审计报告不改代码;修复留给下一里程碑(与零 diff 硬约束同义)
- 审计基准:三处实现现状互相对照,不引入目标态设计(`docs/fc-transcribe-design.md` 排除)
- 报告标准:严重度分级 + file:line 证据 + 修复建议 + 工作量分档,报告可直接驱动下个里程碑
- 双语言适配:Python 以 mypy-strict/ruff 为基准,JS 以仓库自有惯例为基准,不引入外部 JS lint 标准
- `issue-cedential` 拼写域名为真实分配值,永不"修正"(DNF-02)
- GSD 工作流强制:文件变更须经 GSD 命令入口(本阶段产物经 gsd-execute-phase 执行)
- 报告语言:中文正文 + 英文 ID/术语(RPT-09,Phase 1 产物风格已确立)

## Metadata

**Confidence breakdown:**
- 契约现场锚点:HIGH — 全部行号经 git show/grep @ 基线逐条核实
- 执行 harness 可行性:HIGH — 环境探针 + import 链 + archive 导出均实测;仅 sys.path 遮蔽顺序为标准行为假设且有 `__file__` 断言兜底
- 方法论(矩阵/四类/配方):HIGH — 全部由用户锁定决策 + CHARTER 条款给定,无自由裁量
- 矩阵行数估算:MEDIUM — ~40 行为勘察估算,普查可能上探(D-14 为泄压阀)

**Research date:** 2026-07-05
**Valid until:** 基线 `5927f36` 不变则长期有效(审计对象钉死于 git object store;唯一时效性依赖是本机环境探针,建议执行前复跑)
