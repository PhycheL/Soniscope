# Phase 3: 组件与工具链深潜 - Research

**Researched:** 2026-07-04
**Domain:** 静态代码审计(双语言仓库:Python 3.11+ / WeChat 小程序 JS)+ 审计仪器工具链
**Confidence:** HIGH(全部关键论断经本会话内工具实测验证,无外部依赖)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### 深潜覆盖策略与完成判定
- **D-01(覆盖策略 = 全模块普审 + 线索深挖):** 三层每个源码模块至少完整读一遍并记覆盖台账;14 条 CODE/TOOL 维度 HYP 与 6 条 D14 移交线索命中的区域逐行深挖。"已检查,无发现"落到模块粒度,支撑 RPT-07 分维度置信声明。
- **D-02(覆盖台账 = 独立 COVERAGE.md):** `.planning/audit/COVERAGE.md` 逐模块登记:路径、审计深度(普审/深挖)、产出发现 ID 或显式"无发现"、行数。仿 Phase 2 CONTRACT-MATRIX 先例——证据与判断分离,直接喂 RPT-07/RPT-08。
- **D-03(E2E/真云验证模块归 TOOL 维度):** Worker 包内的 `fc_live.py`、`e2e.py`、`e2e_scenarios.py`、`verify_upload_live.py`、`verify_prep.py`、`sts_escape.py`、`retranscribe.py` 等验证模块按功能归 AUDIT-02"部署与验证工具链",发现入 `findings/toolchain.md`;D14-3 线索落此。严重度按工具级影响定级,不套主链路锚点。
- **D-04(普审关注面清单化):** 规划时定稿一份固定普审检查面清单(静默失败路径、资源/临时文件泄漏、异常吞并、硬编码云值、死代码、注释与实态不符等),每面对应 CHARTER 严重度锚点(数据丢失/静默转写失败/凭证泄漏)。每模块逐面过,COVERAGE.md 标"已过面 N/N"。

#### 线索生成工具集边界
- **D-05(工具集 = 现有门禁 + 临时扩展分析器):** 除现有门禁(ruff/mypy/miniprogram_lint)外,临时增跑:ruff 扩大规则集(`--select` 命令行参数)、死代码扫描(vulture)、JS 侧无配置临时 ESLint(顺带量化 HYP-15 的漏报面)。全部命令行临时运行,零仓库写入(不得向仓库添加任何工具配置文件)。
- **D-06(D-07 秘密扫描归本阶段):** Phase 1 章程 D-07 的穿透式秘密扫描(LTAI 长期 AK、`OSSAccessKeyId=` 签名 URL、appsecret 等模式,全仓库含排除目录)随 TOOL 维度执行,与 HYP-07 核实同批。发现只引位置与模式名,不复制任何秘密值本体(含已过期值)。
- **D-07(扫描档案 + 三态销号):** 扫描命令、工具版本、原始输出存 `.planning/audit/scans/`;每条命中标三态销号:确认→成发现(附人工核实证据)/ 误报→记理由 / 移交→标目标维度。可复核,RPT-07 直接引用。
- **D-08(仪器可跑、对象不执行 —— 用户明确选择,比推荐项更严格):** 分析器(ruff/mypy/vulture/临时 ESLint/秘密扫描)作为**审计仪器**可直接命令调用产线索;**被审对象一律不执行**——不跑任何 make 目标(含 make test)、不执行 fc_deploy、不运行 scripts/ 脚本。工具链发现只能来自静读源码,不以"跑通与否"作证据。(注:Phase 4 审 `make test` 门禁完整性时自行决定执行口径,本决定只约束 Phase 3。)

#### HYP 假设与"MVP 可接受"自评的处理
- **D-09(本阶段直接回填 HYPOTHESES.md):** CODE/TOOL 维度 HYP 验证到哪条就地回填状态(证实/证伪/细化)+ `file:line @ 5927f36` 证据;Phase 4 只补未触及条目并做总对账。
- **D-10("MVP 可接受"自评本阶段就裁):** HYP-04/09/10/12 等 CONCERNS 自评"可接受"的条目,核实事实后直接评判断是否成立,以**上线语境**(而非开发语境)度量。不成立→正常分级入发现;成立→回填 HYP 并在备注标注 RPT-06 优点/DNF 候选身份(不占发现 ID,见 D-12)。
- **D-11(跨维度顺带证据 = 记录并移交):** 普审中撞见 DOC/TEST 维度 HYP 的证据(如 config.js 的 HYP-14),记入移交清单(file:line@5927f36 + 一句观察)随阶段产物交 Phase 4;HYP 状态不动、不立发现。延续 Phase 2 移交风格。
- **D-12(证伪/可接受成立不立发现):** 只回填 HYPOTHESES.md 状态与证据,COVERAGE.md 对应模块行引用;RPT-08 的"已检查,无发现"从 HYP 表与覆盖台账两处机械引用。发现台账保持"条条是问题"的信噪比。

#### D14 重复实现的债务判定口径
- **D-13(三要素判定框架):** 每条重复实现逐条评:① 结构必要性(跨部署单元无法共享 = 故意重复,如 FC↔Worker `object_key_for`;同包/同端内重复 = 可疑);② 兜底机制(测试锁定、单一真值源注释锚点有无);③ 漂移后果(静默丢数据 vs 仅工具失准)。三要素写进发现理由,判定可复核。
- **D-14(严重度锚漂移后果):** 触及主链路数据可见性的(如 D14-6 `fragmentIdFromObjectKey` 无校验切割)参照 CHARTER 主链锚点;纯维护成本/工具失准类(D14-2/D14-3)默认 LOW~MEDIUM。重复落点多、体量大不自动拔高。
- **D-15(逐条独立,聚类留 Phase 5):** 6 条 D14 各自走三要素判定、单独立发现(或单独记"不构成债务"结论),互相用关联发现字段串联;根因聚类是 Phase 5 RPT-04 的职责。RPT-08 要求每条移交线索有明确下落。
- **D-16(HYP-03 允许 scratchpad 微基准):** 仿 Phase 2 D-06:`git show 5927f36:apps/miniprogram/utils/sha256.js` 导出到仓库外临时区,node 对典型体量(10 分钟分片 ≈10MB)计时。结果作辅助证据,标注"Mac 环境非真机,量级参考";静态论证(算法实现、调用链、数据量级)仍为主判据。此为 D-08"对象不执行"的唯一例外类型——基线导出的纯函数佐证执行,与 Phase 2 先例同构。

### Claude's Discretion
- 普审关注面清单的具体条目与分面粒度(D-04 给出方向与锚点对应要求,清单定稿留给规划)。
- 扩展分析器的具体规则集选择与版本(D-05 给出工具类别,ruff `--select` 集合、vulture/ESLint 参数由规划/执行敲定)。
- COVERAGE.md 与 scans/ 目录的内部排版组织——满足逐模块粒度与三态销号可复核即可。
- 发现 ID 前缀沿用 CHARTER 既定规则(F-CODE-NN / F-TOOL-NN 类),无需再议。

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUDIT-01 | 三层主体代码(apps/miniprogram、apps/fc、apps/worker)技术债与脆弱区域盘点;工具输出仅作线索,每条发现均经人工核实(原始 linter 输出不直接进报告) | 模块级覆盖清单(见"审计对象全量清单",62 个源文件 ≈15,400 行已按维度分类、附行数);扩展 ruff 规则集实测收敛到 69 命中;ESLint 临时配方实测产 43 问题;三态销号流程沿用 Phase 2 先例;普审关注面清单候选已给出并锚定 CHARTER 严重度 |
| AUDIT-02 | scripts/、Makefile、fc_deploy 等部署与验证工具链审计 | TOOL 维度对象清单定稿(scripts/ 缩窄 3 文件 + Makefile 45 目标 + Worker 包内 12 个验证/运维模块 ≈4,982 行,ops.py/latency.py/fixtures.py 归属已经 docstring 核实);CHARTER 五类秘密扫描命令实测命中计数 69(HYP-07 核实同批);扫描档案红线(禁存秘密值本体)已给出脱敏管道配方 |
</phase_requirements>

## Summary

本阶段是纯静态审计,不写任何产品代码、不装任何项目依赖。研究的核心问题是三个:①审计对象的精确边界与体量(多少文件、多少行、各归哪个维度);②审计仪器(ruff 扩展集、vulture、临时 ESLint、秘密扫描)在本机是否可用、以什么配方运行才既有信号又不违反零仓库写入/零 diff 红线;③已锁定决策(D-01~D-16)落到执行时的具体坑位。

三个问题在本会话内全部实测解决:审计对象共 62 个源文件 ≈15,400 行(CODE ≈10,400 行,TOOL ≈5,000 行,Makefile 45 目标),逐文件行数清单见下;全部仪器可用并已试跑——ruff 0.15.20 扩展集调参后收敛到 69 命中、vulture 2.16 经 `uvx` 可得、ESLint 9.39.4 经 `npx` + scratchpad 平面配置实测产出 43 问题(13 个 error 全为测试文件 Node 全局误报)、五类秘密扫描共 69 命中待三态销号。零 diff 已在研究时点验证为空(工作树 == 基线,apps/scripts/docs 三目录)。

最大的执行风险不是技术,而是纪律:**scans/ 档案若存"原始输出"会把秘密值本体永久提交进 git**(D-07 与 CHARTER 秘密红线在此有张力,必须用脱敏管道解决,配方见 Common Pitfalls #1);其次是仪器噪声(RUF001-003 中文字符误报 3,464 条、PLC0415 撞项目故意懒导入模式 100 条)必须在命令层排除,否则三态销号工作量爆炸。

**Primary recommendation:** 按"仪器扫描波 → CODE/TOOL 双线普审+深挖(可并行)→ D14 裁定 + 微基准 + 收尾核验"三波组织计划;所有仪器按本文档已实测的确切命令运行,基线导出到 scratchpad 后扫描(结构性免疫工作树污染),秘密扫描输出一律经 `cut -d: -f1,2` 脱敏后才入档。

## Architectural Responsibility Map

本阶段不写代码,"责任映射"映射的是**审计能力 → 维度归属 → 产物落点**(供 planner 校验任务分派、防维度错挂):

| Capability | Primary Owner | Secondary | Rationale |
|------------|--------------|-----------|-----------|
| 三层主体代码普审+深挖 | CODE 维度 → `findings/code.md` | COVERAGE.md 逐模块行 | AUDIT-01 正文;锚 CHARTER 主链严重度 |
| Worker 包内验证/运维模块审计 | TOOL 维度 → `findings/toolchain.md` | — | D-03 锁定;严重度按工具级影响,不套主链锚点 |
| scripts/(3 文件)+ Makefile + fc_deploy | TOOL 维度 → `findings/toolchain.md` | — | AUDIT-02 正文;Phase 1 D-06 缩窄清单 |
| 五类秘密扫描(全仓穿透) | TOOL 维度,与 HYP-07 同批 | scans/ 档案(脱敏) | D-06 锁定;命中≠发现,人工核实后才入台账 |
| 仪器扫描线索生成 | scans/ 档案 + 三态销号表 | 喂 CODE/TOOL 深挖 | D-05/D-07;原始 linter 输出不得直接充当发现(成功判据 3) |
| HYP 回填(CODE 10 条 + TOOL 4 条) | HYPOTHESES.md 就地改状态 | COVERAGE.md 引用 | D-09/D-12;证伪/可接受成立不占发现 ID |
| D14-1~6 债务裁定 | `findings/code.md` 或 `toolchain.md`(按落点) | 关联 F-CON-01~06 | D-13/D-14/D-15;逐条三要素、单独下落 |
| 跨组件契约类观察 | **不判断** → 移交清单 | Phase 2 矩阵 / Phase 4 | 成功判据 4;D-11 |
| DOC/TEST 维度顺带证据 | 移交清单(file:line + 一句观察) | Phase 4 输入 | D-11;HYP 状态不动 |
| HYP-03 微基准 | scratchpad(仓库外) | 辅助证据入 HYP-03 回填 | D-16 唯一执行例外 |
| 零 diff 收尾验证 | 阶段收尾任务 | 结果记录入阶段产物 | CHARTER D-03;研究时点已验证为空 |

## Standard Stack

本阶段的"栈"= 审计仪器。全部在本机实测通过(2026-07-04):

### Core(仪器,已验证版本)

| Instrument | Version | Purpose | 验证方式 |
|------------|---------|---------|----------|
| `git`(show/grep/archive/diff) | 仓库自带 | 唯一取证通道:`git show 5927f36:<path>`、`git grep -n <pat> 5927f36`、基线导出 | [VERIFIED: 本会话全部探针经其运行] |
| `uv` | 0.8.14 | 运行 ruff/mypy(仓内环境)与 uvx 临时工具 | [VERIFIED: `uv --version` 实测] |
| `ruff` | 0.15.20(仓内锁定版) | 现有门禁 + 扩展规则集线索生成 | [VERIFIED: `uv run ruff --version` + 扩展集试跑] |
| `mypy` | 2.1.0(仓内锁定版) | 现有门禁基线运行(strict 范围见 pyproject) | [VERIFIED: `uv run mypy --version`] |
| `vulture` | 2.16(经 `uvx`,不入仓) | Python 死代码扫描(D-05 点名) | [VERIFIED: `uvx vulture --version` 实测可得] |
| Node.js | v22.18.0 | 运行临时 ESLint 与 D-16 微基准 | [VERIFIED: `node --version`] |
| `eslint` | 9.39.4(经 `npx --yes eslint@9`,不入仓) | 小程序 JS 无仓内配置临时 lint(D-05 点名,量化 HYP-15 漏报面) | [VERIFIED: 端到端试跑产出 43 问题] |
| `miniprogram_lint` | 仓内(基线 218 行) | 现有门禁;直接调用 `uv run python -m soniscope_worker lint-miniprogram`(不经 make,D-08) | [VERIFIED: Makefile:168 确认该直调命令即 make 目标的实体] |

### Supporting

| 资产 | Purpose | When to Use |
|------|---------|-------------|
| scratchpad 基线导出:`git archive 5927f36 <paths> \| tar -x -C $EXPORT` | 仪器扫描的对象副本,结构性免疫工作树;ESLint 配置文件也放这里(零仓库写入) | ruff 扩展集/vulture/ESLint 扫描、D-16 微基准 |
| CHARTER 五类秘密扫描命令(`git grep -nE ... 5927f36 -- .`) | 穿透扫描,命令已由 Phase 1 写定,直接执行 | TOOL 维度扫描波,与 HYP-07 同批 |
| Phase 2 三态销号表结构(CONTRACT-MATRIX 普查节) | scans/ 档案的排版范本 | D-07 明示沿用 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `uvx vulture` | `uv pip install vulture` 进项目环境 | 后者污染项目 venv(虽不改仓库文件,但违背"临时运行"精神);uvx 已实测可用,无理由换 |
| `npx --yes eslint@9` + scratchpad 平面配置 | eslint@8 + `--no-eslintrc` 内联规则 | v8 已 EOL;v9 平面配置实测通过,配置文件放导出根目录即绕开 v9 basePath 匹配问题 |
| 对基线导出扫描 | 对工作树扫描(零 diff 已验证) | 工作树扫描在零 diff 成立时等价,但导出方案结构性免疫、与"证据一律出自 5927f36"条款同构;mypy/miniprogram_lint 例外(需仓内 uv 环境,见 Pitfall #6) |

**Installation:** 无任何安装写入仓库。vulture/eslint 均为临时获取(uvx/npx 缓存在用户目录)。注意区分:**零云 IO 约束的是被审系统的云(OSS/FC/NLS/微信)**;从 PyPI/npm 拉取审计仪器是工具获取,D-05 已明示允许"临时增跑",且本会话已实测网络可达。

## Package Legitimacy Audit

本阶段不向项目添加任何依赖;下表覆盖两个临时获取的仪器包:

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| vulture | PyPI | 项目 10+ 年,最新版 2026-03 | PyPI 无周下载信号 | github.com/jendrikseipp/vulture | [SUS](seam: unknown-downloads) | 保留 — 机械性误报:知名死代码工具、官方仓库明确;且本会话已实测运行(2.16)无异常 |
| eslint | npm | 项目 12+ 年,最新版 2026-06 | 135,465,836/周 | github.com/eslint/eslint | [SUS](seam: too-new,指最新版发布近) | 保留 — 机械性误报:1.35 亿周下载、官方 eslint org;本会话已实测运行(9.39.4)无异常,无 postinstall 脚本 |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** vulture、eslint — seam 判定均为机械性信号(PyPI 不提供下载量 / 最新版本发布日期近),非包身份可疑。两包均已在本研究会话中实际执行并产出预期结果。按协议,planner 可在首次仪器调用任务前保留一个轻量人工确认点;鉴于本会话已完成等效验证(版本、仓库、无 postinstall、实际运行),亦可引用本节作为已完成的核实证据。

## 审计对象全量清单(基线 5927f36,行数实测)

这是本阶段最重要的规划输入:D-01 要求逐模块覆盖,D-02 要求 COVERAGE.md 逐模块登记行数。以下清单可直接作为 COVERAGE.md 骨架。行数 = `git show 5927f36:<path> | wc -l` 实测。**测试文件(apps/*/tests/、apps/miniprogram/test/)不在本阶段覆盖对象内**——测试质量归 Phase 4 AUDIT-04。

### CODE 维度 — apps/worker 核心(14 模块,4,871 行)

| 模块 | 行数 | 深挖线索 |
|------|------|----------|
| `apps/worker/src/soniscope_worker/pipeline.py` | 875 | HYP-10(串行吞吐) |
| `apps/worker/src/soniscope_worker/nls.py` | 740 | HYP-19(2018 版 NLS API)、D14-2(重试常量) |
| `apps/worker/src/soniscope_worker/cli.py` | 601 | (CODE/TOOL 子命令混载,归 CODE,TOOL 子命令在 TOOL 侧引用) |
| `apps/worker/src/soniscope_worker/poller.py` | 531 | HYP-10、HYP-16;D14-1(sha256 比对流程) |
| `apps/worker/src/soniscope_worker/manifest.py` | 473 | — |
| `apps/worker/src/soniscope_worker/recovery.py` | 465 | — |
| `apps/worker/src/soniscope_worker/audio.py` | 412 | — |
| `apps/worker/src/soniscope_worker/oss_admin.py` | 242 | HYP-13 相关(契约观察→移交,成功判据 4) |
| `apps/worker/src/soniscope_worker/transcriber.py` | 183 | HYP-19(Protocol 隔离充分性);DNF-01 对照(勿把 whisper 桩当发现) |
| `apps/worker/src/soniscope_worker/config.py` | 150 | HYP-08(MaskedSecret/600 权限缓解核实) |
| `apps/worker/src/soniscope_worker/paths.py` | 117 | — |
| `apps/worker/src/soniscope_worker/locks.py` | 64 | — |
| `apps/worker/src/soniscope_worker/__main__.py` | 11 | — |
| `apps/worker/src/soniscope_worker/__init__.py` | 7 | — |

### CODE 维度 — apps/fc(12 文件,1,120 行)

| 模块 | 行数 | 深挖线索 |
|------|------|----------|
| `apps/fc/shared/fc_shared/sts.py` | 176 | HYP-09/17(单键策略核实);DNF-04 对照 |
| `apps/fc/shared/fc_shared/env.py` | 150 | HYP-08 |
| `apps/fc/shared/fc_shared/head.py` | 141 | — |
| `apps/fc/issue_credential/handler.py` | 110 | HYP-17(无限流);DNF-03 对照(mypy 豁免勿当发现) |
| `apps/fc/verify_upload/handler.py` | 106 | DNF-03 对照 |
| `apps/fc/shared/fc_shared/__init__.py` | 106 | — |
| `apps/fc/shared/fc_shared/http.py` | 79 | — |
| `apps/fc/shared/fc_shared/audit.py` | 62 | HYP-08(is_sensitive 洗涤核实) |
| `apps/fc/shared/fc_shared/wechat.py` | 52 | — |
| `apps/fc/shared/fc_shared/auth.py` | 52 | HYP-09 |
| `apps/fc/shared/fc_shared/errors.py` | 51 | D14 关联(错误码字面量真值源) |
| `apps/fc/shared/app.py` | 35 | HYP-12(wsgiref;探针实测 S104 bind-all-interfaces 命中在此附近,待人工核实) |

### CODE 维度 — apps/miniprogram(21 文件,3,406 行)

| 模块 | 行数 | 深挖线索 |
|------|------|----------|
| `apps/miniprogram/pages/index/index.js` | 796 | D14-1(sha256 调用端 :30,640) |
| `apps/miniprogram/pages/uploads/uploads.js` | 387 | D14-4(请求组装第二份 :340,365) |
| `apps/miniprogram/utils/queue_runtime.js` | 324 | D14-4(请求组装 :94-128) |
| `apps/miniprogram/utils/uploads_view.js` | 304 | — |
| `apps/miniprogram/utils/audio.js` | 185 | HYP-13 相关(契约观察→移交) |
| `apps/miniprogram/utils/sha256.js` | 171 | HYP-03 + D14-1(D-16 微基准对象) |
| `apps/miniprogram/utils/uploader.js` | 164 | D14-2(重试常量) |
| `apps/miniprogram/utils/verify.js` | 138 | D14-2 |
| `apps/miniprogram/utils/fault_injection.js` | 124 | HYP-14 顺带证据(→移交 Phase 4) |
| `apps/miniprogram/utils/oss_sign.js` | 121 | — |
| `apps/miniprogram/utils/upload_queue.js` | 119 | D14-6(`fragmentIdFromObjectKey` :38-44,关联 F-CON-03) |
| `apps/miniprogram/utils/ulid.js` | 92 | — |
| `apps/miniprogram/utils/chunking.js` | 65 | — |
| `apps/miniprogram/utils/hmac.js` | 64 | — |
| `apps/miniprogram/pages/dev/dev.js` | 60 | ⚠ CONTEXT 写"pages 两页",实为 **3 页**(index/uploads/dev)——覆盖清单以本表为准 |
| `apps/miniprogram/utils/logger.js` | 60 | — |
| `apps/miniprogram/utils/device.js` | 60 | — |
| `apps/miniprogram/utils/retention.js` | 56 | — |
| `apps/miniprogram/utils/draft.js` | 52 | — |
| `apps/miniprogram/config.js` | 41 | HYP-14/D14-5 顺带证据;DNF-02 对照(勿"修正"拼写域名) |
| `apps/miniprogram/app.js` | 23 | — |

### TOOL 维度 — Worker 包内验证/运维模块(12 模块,4,982 行)

D-03 点名 7 个;`ops.py`/`latency.py`/`fixtures.py` 经基线 docstring 核实同属运维/联调工具(ops.py:"OSS 与 E2E 运维辅助 make 命令"、latency.py:"verify-upload 等云端联调脚本…时延统计"、fixtures.py:"scripts/fetch_test_fixtures.py 作为薄 CLI 复用本模块"),按 D-03"等验证模块"归 TOOL;`miniprogram_lint.py` 是门禁工具本体(HYP-15/25 的审计对象),归 TOOL:

| 模块 | 行数 | 深挖线索 |
|------|------|----------|
| `apps/worker/src/soniscope_worker/verify_prep.py` | 924 | — |
| `apps/worker/src/soniscope_worker/fc_deploy.py` | 707 | HYP-04(仅 update_code) |
| `apps/worker/src/soniscope_worker/retranscribe.py` | 590 | (D-03 锁定归 TOOL) |
| `apps/worker/src/soniscope_worker/fc_live.py` | 556 | D14-3(契约镜像集群 :42-59,256) |
| `apps/worker/src/soniscope_worker/verify_upload_live.py` | 464 | D14-3(:34-35,201) |
| `apps/worker/src/soniscope_worker/ops.py` | 380 | — |
| `apps/worker/src/soniscope_worker/e2e.py` | 295 | — |
| `apps/worker/src/soniscope_worker/e2e_scenarios.py` | 268 | D14-3(导入消费端) |
| `apps/worker/src/soniscope_worker/sts_escape.py` | 268 | — |
| `apps/worker/src/soniscope_worker/fixtures.py` | 232 | D14-1(stdlib hashlib 侧 :21,118) |
| `apps/worker/src/soniscope_worker/miniprogram_lint.py` | 218 | HYP-15(规则覆盖面;ESLint 结果量化其漏报) |
| `apps/worker/src/soniscope_worker/latency.py` | 80 | — |

### TOOL 维度 — scripts/ 与 Makefile(4 项,1,018 行)

| 对象 | 行数 | 深挖线索 |
|------|------|----------|
| `scripts/test_asr.py` | 355 | **HYP-07**(`DEFAULT_FILE_LINK` 约 :80 过期预签名 URL——成功判据 2 点名必出核实结论)、HYP-18(legacy AcsClient SDK)、HYP-25 顺带证据(→移交 Phase 4) |
| `scripts/fetch_test_fixtures.py` | 249 | HYP-25 顺带证据(→移交) |
| `scripts/gen_worker_config.sh` | 243 | — |
| `Makefile` | 171(45 个目标) | 静读审计:目标间依赖、危险目标(deploy/rollback)防误触、注释与实态一致性;**不执行任何目标**(D-08) |

**体量合计:** CODE ≈9,397 行 / TOOL ≈6,000 行 / 总计 ≈15,400 行普审 + 20 处深挖点(14 HYP + 6 D14)。

## Architecture Patterns

### 执行流架构(三波)

```
Wave A: 仪器扫描波(产线索,不产发现)
  零 diff 前置验证 → git archive 基线导出到 scratchpad
  ├─ ruff 扩展集(对导出)──┐
  ├─ vulture(对导出)      │
  ├─ ESLint 临时配方(对导出)├─→ scans/ 档案(命令+版本+脱敏输出)
  ├─ mypy / miniprogram_lint │      ↓
  │  (仓内直调,门禁基线)  │   三态销号表(确认/误报/移交)
  └─ 五类秘密扫描(git grep 基线,输出脱敏)┘
                     ↓ 确认项 = 深挖线索
Wave B(可并行两计划):
  ├─ CODE 普审+深挖:47 文件逐模块过关注面 → findings/code.md + COVERAGE.md + CODE HYP 回填
  └─ TOOL 普审+深挖:16 对象逐模块过关注面 → findings/toolchain.md + COVERAGE.md + TOOL HYP 回填(含 HYP-07 结论)
                     ↓
Wave C: 裁定与收尾
  ├─ D14-1~6 三要素逐条裁定(引用 Wave B 证据,关联 F-CON-01~06)
  ├─ D-16 微基准(scratchpad,node 对 ≈10MB 计时)佐证 HYP-03
  ├─ D-11 跨维度移交清单定稿(→Phase 4)
  └─ 机械收尾:零 diff 验证 + COVERAGE 完整性核对 + HYP 回填计数核对
```

普审(Wave B)依赖扫描线索(Wave A)定深挖优先级,故 A 先行;B 内 CODE/TOOL 无写冲突(分别写 code.md/toolchain.md,COVERAGE.md 若两计划共写需分节或由单计划收口——planner 注意)。

### 普审关注面清单(D-04 授权裁量,建议 9 面)

每面锚定 CHARTER 严重度锚点;每模块过完标"已过面 N/9":

| # | 关注面 | CHARTER 锚点 | 仪器辅助信号 |
|---|--------|--------------|--------------|
| 1 | 静默失败路径(异常吞并、except-pass、错误被忽略) | HIGH 静默转写失败 | ruff S110/BLE/TRY(探针已见 S110 ×1) |
| 2 | 数据丢失风险(`.done` 时序、原子 rename、临时文件清理) | CRITICAL 数据丢失 | 人工为主(CLAUDE.md 反模式清单) |
| 3 | 秘密处理违规(明文入日志、绕过 MaskedSecret/audit 洗涤) | CRITICAL 凭证泄漏 | 秘密扫描 + ruff S105/S106(探针 13 命中待核) |
| 4 | 硬编码云值与环境假设(region/URL/size/阈值散落) | MEDIUM 潜伏失配 | grep;D14-5 关联 |
| 5 | 时区/日期正确性(naive datetime、本地时区推导) | MEDIUM(F-CON-02 同族) | ruff DTZ(探针 DTZ011 ×2、DTZ005 ×1) |
| 6 | 死代码与不可达分支 | LOW | vulture + ruff ARG(探针 ARG ×37) |
| 7 | 注释/文档字符串与实态不符 | LOW(契约类→移交) | 人工 |
| 8 | 纯逻辑+IO注入模式违反(纯逻辑内直调 SDK/wx) | MEDIUM/LOW(CLAUDE.md 明示反模式) | 人工 |
| 9 | 重试/退避/上限等跨端约定的本端一致性 | MEDIUM | D14-2/D14-3 关联 |

### Pattern: 三态销号表(沿用 Phase 2 先例)

scans/ 每个扫描一个小节:命令原文 + 工具版本 + 脱敏输出(或输出文件)+ 逐命中表:

```markdown
| # | 命中(path:line @ 5927f36) | 规则/模式 | 销号 | 理由/去向 |
|---|---------------------------|-----------|------|-----------|
| 1 | apps/fc/shared/app.py:NN | S104 | 确认 | → F-CODE-xx(附人工核实片段) |
| 2 | apps/.../errors.py:NN | S105 | 误报 | 错误码常量非口令 |
| 3 | apps/miniprogram/config.js:NN | 硬编码值 | 移交 | → Phase 4 DOC(HYP-14) |
```

### Anti-Patterns to Avoid

- **原始工具输出直接当发现:** 成功判据 3 明令禁止;每条发现必须有人工在 `git show 5927f36` 提取的引用片段。
- **把 DNF 条目再立发现:** DNF-01(whisper 桩)、DNF-02(拼写域名)、DNF-03(handler mypy 豁免)、DNF-04(小程序收原始 STS)已裁定为故意设计,普审撞见时对照 DO-NOT-FIX.md 跳过。
- **在组件维度内裁契约分歧:** 成功判据 4——契约类观察只记移交,判断权在 Phase 2 矩阵/Phase 4。
- **以"缺 mypy 覆盖"苛责 handler.py:** CHARTER 双语言适配声明明文禁止。
- **对小程序 JS 引入外部 lint 标准作为判据:** CHARTER 明文"以仓库既有惯例为基准";ESLint 结果只是线索与 HYP-15 漏报面量化,不是质量标准。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 秘密扫描模式 | 自拟新正则集 | CHARTER 五类命令原文照跑 | Phase 1 已定稿且实测可用;自拟模式破坏 RPT-07 可追溯性 |
| 基线取证 | 读工作树 + 手记行号 | `git show 5927f36:<path>` / `git grep -n <pat> 5927f36` | CHARTER 明令;工作树无结构性免疫 |
| Python 死代码检测 | grep 手工找未引用函数 | `uvx vulture`(2.16 已验证) | 作用域/动态引用分析非 grep 可及;误报由三态销号吸收 |
| JS 缺陷类检测 | 手写检查脚本 | `npx eslint@9` + scratchpad 平面配置(配方已实测) | D-05 点名 ESLint;手写脚本重蹈 HYP-15 覆辙 |
| 扫描档案格式 | 新发明格式 | Phase 2 CONTRACT-MATRIX 普查节的"命令存档+三态销号"结构 | D-07 明示沿用;RPT-07 消费端已适配 |
| 发现记录格式 | 自定字段 | CHARTER 九字段 schema(findings/*.md 已有 F-*-00 示例) | CHARTER-05 硬约束 |

**Key insight:** 本阶段一切"基础设施"(基线、schema、严重度、扫描命令、销号范式)都已在 Phase 1/2 定稿并实测,规划只需编排,不需发明。

## Common Pitfalls

### Pitfall 1: scans/ 档案把秘密值本体提交进 git(最高风险)
**What goes wrong:** D-07 说"原始输出存 `.planning/audit/scans/`",但五类秘密扫描的原始输出行**含匹配内容本身**(如 test_asr.py 的预签名 URL 全文)。`.planning/` 会被提交(commit_docs=true),一旦入库即构成 CHARTER 明文警告的"二次泄露",且永久。
**Why it happens:** D-07(存原始输出)与 CHARTER 秘密红线(绝不复制值本体)在秘密扫描这一类上冲突,D-06 已裁定红线优先("发现只引位置与模式名")。
**How to avoid:** 秘密类扫描的档案输出一律经脱敏管道:`git grep -nE '<pattern>' 5927f36 -- . | cut -d: -f1,2` (只留 path:line,剥离内容列);另记每模式命中计数。非秘密类扫描(ruff/vulture/ESLint)输出不含秘密,可存全文。
**Warning signs:** scans/ 任何文件里出现 `Signature=`、`OSSAccessKeyId=TMP`、`Expires=` 后跟长串字符。计划的 verify 步骤应加一条:对 scans/ 目录反跑五类模式 grep,期望零命中(模式名本身除外)。

### Pitfall 2: 仪器噪声未在命令层排除,三态销号工作量爆炸
**What goes wrong:** 裸跑 `ruff --select` 全集在本仓产 3,899 命中,其中 RUF001/002/003(中文全角字符"歧义 unicode")3,464 条、S101(tests 的 assert)163 条、PLC0415(顶层外导入)100 条——后者撞的是项目**故意的**懒导入模式(CLAUDE.md:"cloud SDKs are lazy-imported")。
**How to avoid:** 用实测配方(见 Code Examples):`--ignore PLC0415,TRY003,S101` 且不选 RUF 系,收敛到 69 命中;测试目录不在扫描路径内(Phase 4 范围)。
**Warning signs:** 任何单一扫描销号表超过 ~150 行,说明规则集没调好,应回头收窄而不是硬销。

### Pitfall 3: ESLint 误报淹没信号(Node 全局 / 平面配置 basePath)
**What goes wrong:** ①对 test/*.js 一起扫会报 `__dirname`/`Buffer` no-undef(实测 13 个 error 全是这个——node:test 文件合法使用 Node 全局);②ESLint v9 平面配置的 `files` 模式相对配置文件基路径解析,配置放 scratchpad、对象在仓内会匹配不到。
**How to avoid:** 配置文件与被扫对象同放 scratchpad 基线导出内(cd 到导出根再跑,配方已实测);扫描路径限定非测试 JS(`apps/miniprogram/{utils,pages}/**/*.js` + `app.js` + `config.js`),test/ 归 Phase 4。
**Warning signs:** 输出里出现 `no-undef` 且标识符是 `__dirname`/`Buffer`/`process` → 扫到了测试文件。

### Pitfall 4: 把 HYP-25 当本阶段回填对象
**What goes wrong:** CONTEXT 把 HYP-25(scripts/ 无 lint 门禁)列为"直接相关",但其维度是 **TEST**(Phase 4 回填)。本阶段回填集是 CODE 10 条(HYP-01/03/08/09/10/12/16/17/19/20)+ TOOL 4 条(HYP-04/07/15/18)= 14 条;HYP-25 的证据(如 pyproject mypy/ruff 范围不含 scripts/)走 D-11 移交,状态不动。
**How to avoid:** 计划里写死 14 条回填清单;移交清单单列 HYP-25/HYP-14 等顺带证据。

### Pitfall 5: COVERAGE.md 双计划并行写冲突
**What goes wrong:** CODE 与 TOOL 两计划并行(Wave B)都要写 COVERAGE.md,并行提交会冲突(Phase 2 分 findings 文件正是为避免此类冲突)。
**How to avoid:** 二选一:①COVERAGE.md 预建骨架分 CODE/TOOL 两节,各计划只动自己的节;②各计划产 COVERAGE-CODE.md/COVERAGE-TOOL.md 片段,Wave C 收口合并为 COVERAGE.md。D-02 只要求逐模块粒度可复核,两法皆合规。

### Pitfall 6: mypy/miniprogram_lint 在导出副本上跑不起来
**What goes wrong:** ruff/vulture/ESLint 对基线导出即可跑;但 mypy 需要项目依赖环境、miniprogram_lint 是仓内模块,只能在仓内经 `uv run` 直调。若机械套"一律对导出扫"会失败。
**How to avoid:** 分两类:导出扫描(ruff 扩展/vulture/ESLint/微基准)与仓内直调(`uv run mypy`、`uv run python -m soniscope_worker lint-miniprogram`);后者前后各跑一次零 diff 验证并记录,保证工作树 == 基线时段内完成。研究时点已验证零 diff 为空。
**Warning signs:** 直调命令带 `make` 前缀(违反 D-08 "不跑任何 make 目标")。

### Pitfall 7: 引用 HYP-07 证据时复制了 URL
**What goes wrong:** 核实 `scripts/test_asr.py` 约 :80 的 `DEFAULT_FILE_LINK` 时,顺手把整行代码作"证据片段"引进台账——该行内容就是预签名 URL 本体。
**How to avoid:** 该发现的证据片段只写 `scripts/test_asr.py:<行号> @ 5927f36` + "符合 `OSSAccessKeyId=` 签名 URL 模式(值本体略,per CHARTER 秘密红线)";引用片段可截变量名与赋值号,不截值。

### Pitfall 8: 小程序页面数记错导致覆盖漏页
**What goes wrong:** CONTEXT 记"pages 两页",基线实际有三页(index/uploads/**dev**)。dev.js(60 行)是开发者页,与 HYP-14(ENV 开关暴露开发者菜单)直接相关,漏审即漏一处顺带证据。
**How to avoid:** 覆盖清单以本文档"审计对象全量清单"为准(62 文件),不以 CONTEXT 的概数为准。

## Code Examples

全部命令已在本会话实测通过(2026-07-04,macOS,本仓库)。

### 1. 零 diff 前置/收尾验证(CHARTER 原文)
```bash
git diff --stat 5927f36 -- apps/ scripts/ docs/   # 期望:空输出(研究时点已实测为空)
```

### 2. 基线导出到 scratchpad(仪器扫描对象)
```bash
EXPORT="$SCRATCHPAD/baseline-5927f36"   # 仓库外临时区
mkdir -p "$EXPORT"
git archive 5927f36 apps scripts | tar -x -C "$EXPORT"
```

### 3. ruff 扩展规则集(实测配方,69 命中)
```bash
# 版本记录: ruff 0.15.20(uv.lock 锁定;pyproject 声明 >=0.4——版本差本身是 TOOL 维度观察点)
uv run ruff check --isolated --target-version py311 \
  --select S,BLE,TRY,DTZ,ARG,ERA,SIM,RET,PLC,PLE,PLW \
  --ignore PLC0415,TRY003,S101 \
  "$EXPORT/apps/worker/src" "$EXPORT/apps/fc" \
  "$EXPORT/scripts/test_asr.py" "$EXPORT/scripts/fetch_test_fixtures.py"
# --isolated 隔离仓内 pyproject 配置,保证规则集即命令所写
# 探针实测信号样本(含测试目录时): S110 try-except-pass ×1, S104 bind-all ×1,
#   DTZ011 ×2, DTZ005 ×1, S105/S106 ×13, ARG ×37 —— 均为线索,须逐条人工核实
```

### 4. vulture 死代码扫描(2.16 实测可得)
```bash
uvx vulture "$EXPORT/apps/worker/src" "$EXPORT/apps/fc" --min-confidence 80
# 已知误报类(销号时备查): Protocol 实现方法、typer 回调、WSGI 入口等动态引用 [ASSUMED]
```

### 5. ESLint 临时配方(9.39.4 端到端实测,43 问题)
```bash
# eslint.config.mjs 写到 $EXPORT 根(仓库外,满足 D-05 零仓库写入):
# export default [{ files:["**/*.js"],
#   languageOptions:{ ecmaVersion:2020, sourceType:"commonjs",
#     globals:{ wx:"readonly",App:"readonly",Page:"readonly",Component:"readonly",
#       getApp:"readonly",getCurrentPages:"readonly",module:"writable",require:"readonly",
#       exports:"writable",console:"readonly",setTimeout:"readonly",clearTimeout:"readonly",
#       setInterval:"readonly",clearInterval:"readonly",globalThis:"readonly" } },
#   rules:{ "no-undef":"error","no-unused-vars":"warn","no-shadow":"warn","eqeqeq":"warn",
#     "no-fallthrough":"error","no-unreachable":"error","no-dupe-keys":"error",
#     "no-redeclare":"error","no-empty":"warn","no-prototype-builtins":"warn",
#     "consistent-return":"warn","no-var":"off" } }];
cd "$EXPORT" && npx --yes eslint@9 --no-config-lookup -c eslint.config.mjs \
  "apps/miniprogram/utils/**/*.js" "apps/miniprogram/pages/**/*.js" \
  "apps/miniprogram/app.js" "apps/miniprogram/config.js"
# 探针(含 test/ 时)实测 43 问题:13 error 全为测试文件 Node 全局误报(见 Pitfall 3),
# 30 warning 以 no-unused-vars 为主 —— 即 HYP-15 漏报面的量化底数
```

### 6. 现有门禁基线(仓内直调,不经 make,D-08)
```bash
uv run mypy    # 版本 2.1.0;配置在根 pyproject.toml
uv run ruff check   # 门禁规则集 E,F,I,UP,B(与扩展集分开存档)
uv run python -m soniscope_worker lint-miniprogram   # Makefile:168 的实体命令直调
```

### 7. 五类秘密扫描(CHARTER 原文 + 脱敏管道;实测命中计数)
```bash
# 存档形态:命令原文 + 计数 + path:line 清单(cut 剥离内容列,per Pitfall 1)
git grep -nE 'LTAI[0-9A-Za-z]{10,}' 5927f36 -- . | cut -d: -f1,2          # 实测 10 命中
git grep -nE 'OSSAccessKeyId=' 5927f36 -- . | cut -d: -f1,2               # 实测 4 命中
git grep -nE 'Signature=[0-9A-Za-z%+/=]{16,}' 5927f36 -- . | cut -d: -f1,2 # 实测 1 命中
git grep -niE 'app_?secret[[:space:]]*[:=]' 5927f36 -- . | cut -d: -f1,2  # 实测 3 命中
git grep -nE 'SecurityToken=|security_token' 5927f36 -- . | cut -d: -f1,2 # 实测 51 命中
# 合计 69 命中待三态销号;命中 ≠ 发现(CHARTER 明文)
```

### 8. D-16 微基准(scratchpad,唯一执行例外)
```bash
git show 5927f36:apps/miniprogram/utils/sha256.js > "$EXPORT/sha256_baseline.js"
# node 计时脚本(写在 scratchpad):require 该文件,对 ≈10MB 随机 Buffer/字符串计时,
# 多轮取中位;结果标注"Mac 环境非真机,量级参考",作 HYP-03 辅助证据
node "$EXPORT/bench_sha256.js"
```

### 9. 机械收尾核验(供计划 verify 步骤)
```bash
grep -c '^### F-CODE-' .planning/audit/findings/code.md        # 发现计数(减去 F-CODE-00 示例)
grep -c '^### F-TOOL-' .planning/audit/findings/toolchain.md
grep -c '未验证' .planning/audit/HYPOTHESES.md                  # 14 条回填后应减少 14
git grep -nE 'OSSAccessKeyId=[^ ]|Signature=[0-9A-Za-z%+/=]{16,}' -- .planning/audit/scans/ ; echo "exit=$?"  # 期望无命中(exit=1),防二次泄露
git diff --stat 5927f36 -- apps/ scripts/ docs/                 # 期望空
```

## State of the Art

| Old Approach | Current Approach | 备注 |
|--------------|------------------|------|
| ESLint v8 `--no-eslintrc` + 内联 env | ESLint v9 平面配置 + `--no-config-lookup -c <file>` | v8 已 EOL;v9 配方本会话实测通过 [VERIFIED: 本地运行] |
| pyproject 声明 ruff>=0.4 时代的规则集 | 锁定版 0.15.20,S/BLE/TRY/DTZ/PL 等规则族齐备 | 扩展集可用性已实测;门禁与扩展集分开存档,版本差异本身记入 TOOL 观察 |

**Deprecated/outdated:** 无与本阶段直接相关的弃用项。HYP-18/HYP-19(legacy Aliyun SDK / 2018 版 NLS API)是**审计对象的**陈旧性问题,静读核实即可,不需外部验证其弃用时间表(引入目标态/未来性判断超出"现状互审"基准——若需弃用公告佐证,标注 [ASSUMED] 并留给发现的修复建议段)。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | vulture 对 Protocol 实现/typer 回调/WSGI 入口会产动态引用误报 [ASSUMED,训练知识] | Code Examples #4 | 低——三态销号本就逐条人工核实,误报只增少量销号工作 |
| A2 | `npx`/`uvx` 的网络可达性在执行时点仍成立(本会话实测可达)[ASSUMED 时效性] | Environment Availability | 中——若断网,ESLint/vulture 扫描缺席;兜底:ruff ARG/ERA + 人工普审仍覆盖死代码/未用变量面,COVERAGE.md 记"仪器缺席"即可,不阻塞阶段 |
| A3 | 探针所见 ruff 命中(S110/S104/DTZ 等)在限定非测试路径后仍存在(探针路径含 apps/fc/tests)[VERIFIED 命中存在,ASSUMED 归属非测试文件] | Architecture Patterns 关注面表 | 低——仅影响线索优先级,不影响方法 |

其余全部关键论断([VERIFIED] 标注项:仪器版本、命令配方、命中计数、文件行数、零 diff、模块归属 docstring)均在本会话内以工具实测确认。

## Open Questions

1. **COVERAGE.md 并行写入的具体机制(骨架分节 vs 分片合并)**
   - What we know: D-02 只约束粒度与可复核性;Phase 2 用分文件避免冲突。
   - What's unclear: planner 打算 Wave B 出几个并行计划。
   - Recommendation: 若 CODE/TOOL 并行,则预建分节骨架(Wave A 末尾任务建好),两计划各写各节;串行则无此问题。
2. **`cli.py`(601 行)的 TOOL 子命令部分如何计覆盖**
   - What we know: cli.py 混载主链与 ~30 个验证子命令的入口;实体逻辑都在被分类的模块里。
   - Recommendation: cli.py 整体归 CODE 普审一次,COVERAGE.md 备注"TOOL 子命令入口,实体逻辑见 TOOL 侧对应模块",避免双计双审。
3. **Makefile 审计粒度(45 目标逐个 vs 分组)**
   - What we know: 171 行、45 目标;D-08 禁执行,只能静读。
   - Recommendation: 按功能组(install/质量门禁/worker 运行/deploy/live 验证)过关注面,危险目标(deploy-fc/rollback/oss-delete-obj 类)逐个细读;COVERAGE.md 记 Makefile 一行 + 分组备注。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git(show/grep/archive) | 全部取证 | ✓ | 仓库自带 | —(无替代,硬依赖) |
| uv + 项目 venv | ruff/mypy/门禁直调 | ✓ | uv 0.8.14 | — |
| ruff | 门禁 + 扩展扫描 | ✓ | 0.15.20 | — |
| mypy | 门禁基线 | ✓ | 2.1.0 | — |
| vulture | 死代码扫描(D-05) | ✓(经 uvx,已实测) | 2.16 | ruff ARG/ERA + 人工;COVERAGE 记仪器缺席 |
| Node.js | ESLint + D-16 微基准 | ✓ | v22.18.0 | — |
| eslint | JS 临时 lint(D-05) | ✓(经 npx,已实测端到端) | 9.39.4 | miniprogram_lint + 人工普审;HYP-15 漏报面量化降级为定性 |
| 网络(PyPI/npm 工具获取) | uvx/npx 首次拉取 | ✓(本会话实测) | — | 见 Assumptions A2 |
| ffmpeg/ffprobe | 不需要(无对象执行) | n/a | — | — |
| 被审云资源(OSS/FC/NLS/微信) | **禁用**(零云 IO) | 禁 | — | — |

**Missing dependencies with no fallback:** 无。

## Validation Architecture

本阶段产物是审计文档,无代码测试框架适用;验收全部为机械命令(延续 Phase 2 "可机械验收"先例,亦是 CONTEXT specifics 的用户明确要求):

### Phase Requirements → 机械验收 Map

| Req / 成功判据 | 行为 | 验收命令 | 类型 |
|----------------|------|----------|------|
| AUDIT-01 / 判据 1 | 三层发现入台账、schema 合规 | `grep -c '^### F-CODE-' findings/code.md` ≥1(除示例);抽查每条含九字段(`grep -c '维度:\|严重度:\|证据:' ...`) | 机械 + 抽查 |
| AUDIT-02 / 判据 2 | 工具链发现入台账、HYP-07 有结论 | `grep -c '^### F-TOOL-' findings/toolchain.md`;`grep 'HYP-07' HYPOTHESES.md` 状态 ≠ 未验证 | 机械 |
| 判据 3 | 无原始输出充当发现 | 每条发现证据字段含 `@ 5927f36` 引用片段(`grep -L` 反查);scans/ 与 findings/ 分离存在 | 机械 + 抽查 |
| 判据 4 | 契约观察已移交不判断 | 移交清单文件存在;findings/code.md 中无 CON 维度字样发现 | 机械 |
| D-01/D-02 | 覆盖完整 | COVERAGE.md 行数 = 62 对象全出现(对照本文档清单 `grep -c`) | 机械 |
| D-09 | 14 条 HYP 回填 | HYPOTHESES.md 中 14 个指定 ID 状态 ≠ "未验证" | 机械 |
| D-07 | 扫描可复核 | scans/ 每扫描含命令+版本+销号表;秘密反扫零命中(Code Examples #9) | 机械 |
| 零 diff | 基线未污染 | `git diff --stat 5927f36 -- apps/ scripts/ docs/` 为空 | 机械 |

### Sampling Rate
- **每任务收尾:** 零 diff 快查(改动只应落 `.planning/`)。
- **每波收尾:** 对应机械验收命令 + scans/ 秘密反扫。
- **Phase gate:** 上表全绿 + 移交清单/COVERAGE/HYP 三处计数对账。

### Wave 0 Gaps
None — 台账骨架(code.md/toolchain.md 含 F-*-00 schema 示例)、CHARTER、HYPOTHESES.md、DO-NOT-FIX.md、D14 移交记录均已就绪;仅需 Wave A 首任务创建 `.planning/audit/scans/` 目录与 COVERAGE.md 骨架。

## Security Domain

本阶段不产代码,ASVS 应用控制类别(V2/V3/V4 等)不适用于阶段产物本身;安全责任集中在**审计过程自身的信息处置**:

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 秘密值本体经 scans/ 或 findings/ 二次入库 | Information Disclosure | 脱敏管道(`cut -d: -f1,2`)+ 收尾反扫(Code Examples #7/#9)+ CHARTER 值本体红线 |
| HYP-07 证据引用截入预签名 URL | Information Disclosure | 证据只写位置+模式名(Pitfall 7) |
| 审计中"顺手修复"污染基线 | Tampering(对审计完整性) | 零 diff 验证每任务/每波跑;无例外协议(CRITICAL 也只进台账) |
| 供应链:临时仪器包投毒 | Tampering | 包合法性核查已完成(vulture/eslint 官方仓库、无 postinstall,见 Package Legitimacy Audit);固定 `eslint@9`/uvx 官方源 |

被审对象中的安全问题(凭证处理、认证、STS 策略)按 CHARTER 严重度锚点作为**发现**记录(HYP-07/08/09/17 深挖点已列入对象清单),标注"顺带发现(out-of-dimension)"规则见 CHARTER。

## Project Constraints (from CLAUDE.md)

审计判断基准直接取自 CLAUDE.md 的既定事实(普审对照用,勿当新发现或反着违反):

- **GSD 工作流强制:** 文件改动须经 GSD 命令入口;本阶段一切写入限 `.planning/`。
- **反模式清单(普审关注面直接引用):** Worker 业务代码调 OSS DeleteObject;`.done` 早写/最终工件先于 `.done`;纯逻辑内直调云 SDK/wx API;绕过 Makefile 的 ad-hoc 脚本。
- **秘密红线:** MaskedSecret/`mask_secret()`/`fc_shared/audit.py` 洗涤/openid 只记 hash——普审第 3 面的"应然"基准。
- **既定豁免勿苛责:** handler.py ruff-only(mypy 模块名冲突)、`issue-cedential` 拼写域名、whisper-local 桩(均已 DNF 登记)。
- **约定基准:** 重试表 5s/15s/45s ×3 双语言镜像并有测试断言;错误码字符串跨语言逐字共享;`snake_case.py`/`camelCase` JS;中文注释带 US/AC 编号。
- **报告语言:** 中文正文 + 英文 ID/严重度术语(RPT-09,阶段产物同样遵守)。

## Sources

### Primary (HIGH confidence — 本会话工具实测)
- 本仓库基线 `5927f36`:`git ls-tree`/`git show | wc -l` 全量文件与行数清单;`git diff --stat` 零 diff 验证;模块 docstring 归属核实(ops/latency/fixtures/e2e)
- 仪器实测:`uv run ruff/mypy --version`、扩展集试跑(两轮,3,899→69 命中)、`uvx vulture --version`、`npx eslint@9` 端到端(含配置配方、43 问题、error 归因)、五类秘密扫描命中计数
- `.planning/audit/CHARTER.md`、`HYPOTHESES.md`(25 条全文)、`DO-NOT-FIX.md`(4 条)、`CONTRACT-MATRIX.md`(D14-1~6 移交记录)、`findings/*.md` 骨架、`REQUIREMENTS.md`、`ROADMAP.md`、`.planning/config.json`
- gsd-tools seam:package-legitimacy(vulture/eslint 信号)、classify-confidence

### Secondary (MEDIUM confidence)
- 无(本阶段无需外部文档;所有配方以本地实测代替引用)

### Tertiary (LOW confidence)
- Assumptions Log A1/A2(训练知识 + 时效性假设,均有兜底)

## Metadata

**Confidence breakdown:**
- 审计对象清单与体量: HIGH — 逐文件 `git show | wc -l` 实测,归属经 docstring 核实
- 仪器栈与配方: HIGH — 全部命令端到端试跑,含命中计数
- Pitfalls: HIGH(#1-#8 均由实测或锁定决策直接推出)
- 严重度/schema/流程: HIGH — Phase 1/2 已定稿文档直接引用

**Research date:** 2026-07-04
**Valid until:** 里程碑内长期有效(对象钉死在基线 `5927f36`,不随时间漂移;唯一时效项为 A2 网络可达性)
