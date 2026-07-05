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
| `docs/v1.0.0 prd/PRD_v1.md` | 深核 | §PRD_v1.md(04-03) | 待审 |
| `docs/v1.0.0 prd/tech-spec.md` | 深核 | §tech-spec.md(04-03) | 待审 |
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
