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
