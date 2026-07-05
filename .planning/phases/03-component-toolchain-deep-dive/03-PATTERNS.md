# Phase 3: 组件与工具链深潜 - Pattern Map

**Mapped:** 2026-07-04
**Files analyzed:** 7 类产物(6 个仓内文件/目录 + 1 类 scratchpad 仓外工件)
**Analogs found:** 6 / 7(HYPOTHESES.md 回填格式无已完成先例,需按既有条目结构推导)

> 本阶段是纯静态审计,不写任何产品源码;全部"新建/修改文件"均为 `.planning/audit/` 下的审计台账文档。因此本图谱的"analog"不是源码文件,而是 Phase 1/2 已封版的审计文档——它们是 CONTEXT.md 逐条点名的先例(D-02"仿 CONTRACT-MATRIX 先例"、D-07"沿用三态销号"、D-11"延续 Phase 2 移交风格"、D-16"仿 Phase 2 D-06")。所有行号引用针对**工作树当前版本**的 `.planning/` 文档(它们不受基线钉定约束,且自 Phase 2 封版后未再改动)。

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.planning/audit/COVERAGE.md`(新建) | 覆盖台账(证据与判断分离) | 逐模块表格登记 + 机械对账收口 | `.planning/audit/CONTRACT-MATRIX.md`(表格落格 + ④完成判定 + 机械对账) | role-match(D-02 明示仿此先例) |
| `.planning/audit/scans/*.md`(新建目录) | 扫描档案 | 命令存档 + 逐命中三态销号表 | `CONTRACT-MATRIX.md` §重复逻辑普查 ①候选表 + ②系统扫描存档 + 附录销号表 | exact(D-07 明示沿用) |
| `.planning/audit/findings/code.md`(追加) | 发现台账 (CODE) | append-only 九字段条目 | `.planning/audit/findings/contract.md` F-CON-01~06(真实条目)+ 本文件 F-CODE-00 骨架 | exact |
| `.planning/audit/findings/toolchain.md`(追加) | 发现台账 (TOOL) | append-only 九字段条目 | 同上(F-TOOL-00 骨架已就位) | exact |
| `.planning/audit/HYPOTHESES.md`(就地改) | 假设清单回填 | in-place 字段变更(状态 + 证据 + 备注) | 自身条目结构(HYP-02 备注含"半句已被推翻"的部分证伪措辞先例) | role-match(无已完成回填先例,格式需规划定稿) |
| Phase 4 移交清单(新建,落点属 Claude 裁量) | 跨维度移交记录 | 逐条 bullet:线索号 + file:line@5927f36 + 一句观察 + 去向 | `CONTRACT-MATRIX.md:255-265` ③债务移交记录(D14-1~6) | exact(D-11 明示延续) |
| scratchpad 工件(基线导出 / eslint.config.mjs / bench_sha256.js)(仓外) | 审计仪器脚手架 | git archive 导出 + 命令调用 | `CONTRACT-MATRIX.md:311-329` harness 复跑说明 + 03-RESEARCH.md Code Examples #2/#5/#8 | exact(D-16 明示同构) |

## Pattern Assignments

### `.planning/audit/findings/code.md` 与 `findings/toolchain.md`(发现台账,append-only)

**Analog:** `.planning/audit/findings/contract.md`(F-CON-01~06 六条真实条目)+ `.planning/audit/CHARTER.md:139-163`(九字段 schema 定义)

**九字段条目结构**(schema 权威定义 `CHARTER.md:139-151`;骨架 `findings/code.md:7-19` / `findings/toolchain.md:7-19` 已内置 F-*-00 示例):

```markdown
### F-CODE-01: <一行标题>

- **维度:** 组件代码 (CODE)
- **严重度:** <五级之一> — 影响:<一句场景语言>;可能性:<一句触发条件>
- **证据:** `path:line @ 5927f36`
  > (从 git show 5927f36 提取的引用片段)
- **修复建议:** <一段,可直接驱动修复里程碑>
- **工作量:** <S/M/L/XL>(判定标准 CHARTER.md:124-131)
- **关联发现:** F-XXX-NN;关联线索: HYP-NN(无则写"无")
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft
```

**真实条目的证据字段写法**(`findings/contract.md:25-39`,F-CON-01——注意证据字段的三层结构:行号引用 + 引用片段 blockquote + 对照/佐证段):

```markdown
- **严重度:** LOW — 影响:前端若因缺陷构造出非法日期 fragment_id,FC 侧 400 INVALID_REQUEST 是唯一拦截点,上传显式失败进入重试/manual_retry,无静默数据丢失;可能性:小程序时间前缀由 Date 对象经 localDateParts 生成,现实路径产不出 13 月 32 日类值,仅在日期构造逻辑变更或引入外部输入时触发
- **证据:** `apps/miniprogram/utils/audio.js:95-96 @ 5927f36`(矩阵反向引用:组① 行 2「fragment_id 日期合法性校验」小程序格 absent)
  > `const FRAGMENT_ID_RE = /^\d{4}\d{2}\d{2}T\d{6}_[A-Za-z0-9]{4,8}_[0-9A-Za-z]{26}$/` — 正则仅做形状校验……对照:FC `apps/fc/shared/fc_shared/sts.py:54-58 @ 5927f36` 与 Worker `apps/worker/src/soniscope_worker/oss_admin.py:45-49 @ 5927f36` ……
```

**严重度理由固定格式**(`CHARTER.md:118`):`影响:…;可能性:…` 一行定性,禁止任何数值评分;边界情况对号 `CHARTER.md:108-116` 锚点表(TOOL 维度按 D-03 用工具级影响,不套主链锚点)。

**D14 裁定条目的增量要求**(D-13):三要素(结构必要性/兜底机制/漂移后果)写进理由;关联发现字段反向引用 F-CON-01~06 与 D14-N——可仿 `findings/contract.md:83` F-CON-03 的关联字段写法:

```markdown
- **关联发现:** F-CON-02;关联线索: HYP-13;矩阵组① 行 5;D14-6(第四处重复实现债务,移交 Phase 3 CODE 维度)
```

**"发现"节前的判定说明段**(`findings/contract.md:23`——`## 发现` 标题下先放一段 blockquote 总述判定产物与计数,再逐条列发现):

```markdown
## 发现

> 02-04 判定产物:……(归类分布 + 负面清单排除计数 + 顺带发现声明)
```

**秘密类证据红线**(`CHARTER.md:104` + RESEARCH Pitfall 7,HYP-07 条目必用):证据只写 `scripts/test_asr.py:<行号> @ 5927f36` + 模式名(如"`OSSAccessKeyId=` 签名 URL 模式"),引用片段可截变量名与赋值号,绝不截值本体。参照 `DO-NOT-FIX.md:41` 的写法先例:"(此处仅引用代码标识符名,不涉任何真实密钥值)"。

---

### `.planning/audit/scans/*.md`(扫描档案 + 三态销号)

**Analog:** `CONTRACT-MATRIX.md` §重复逻辑普查(D-07 明示沿用该结构)

**命令存档格式**(`CONTRACT-MATRIX.md:210-253`,②系统扫描存档——fenced bash 块内:命令原文 + `# →` 注释记总命中数(实现/测试分栏)+ 逐条人工筛选结论):

```bash
# 扫描 3:重试与大小数值族
git grep -nE '\b(5000|15000|45000)\b|…|52428800' 5927f36 -- apps/
# → 总命中 30(实现 8 / 测试 22)。实现命中逐条:env.py:41、uploader.js:28、…(均已入组③ 行 44-46);
#   无关值 4 条人工排除:nls.py:53(NLS 轮询间隔)、…。无新发现。
```

Phase 3 增量:每个扫描小节须加**工具版本行**(D-07 要求"命令、工具版本、原始输出";Phase 2 的 git grep 无版本概念,ruff/vulture/ESLint 有——版本已由 RESEARCH 实测:ruff 0.15.20 / vulture 2.16 / eslint 9.39.4 / mypy 2.1.0 / node v22.18.0)。

**三态销号表格式**(逐命中表,03-RESEARCH.md:273-279 已给出 Phase 3 适配版;列结构源自 `CONTRACT-MATRIX.md:190-200` ①候选清单表与 `:335-354` 附录样本销号表):

```markdown
| # | 命中(path:line @ 5927f36) | 规则/模式 | 销号 | 理由/去向 |
|---|---------------------------|-----------|------|-----------|
| 1 | apps/fc/shared/app.py:NN | S104 | 确认 | → F-CODE-xx(附人工核实证据) |
| 2 | apps/.../errors.py:NN | S105 | 误报 | 错误码常量非口令 |
| 3 | apps/miniprogram/config.js:NN | 硬编码值 | 移交 | → Phase 4 DOC(HYP-14) |
```

**秘密扫描脱敏管道**(RESEARCH Pitfall 1 强制;CHARTER 五类命令原文 `CHARTER.md:94-100`):

```bash
git grep -nE 'LTAI[0-9A-Za-z]{10,}' 5927f36 -- . | cut -d: -f1,2   # 只留 path:line,剥离内容列
```

**三态分布对账句式**(`CONTRACT-MATRIX.md:272`——收口时给出可复算等式):

```markdown
候选清单 9 项三态分布:新行 1 项 + 指针 4 项 + 已检查无新发现 4 项;1 + 4 + 4 = 9 ✓
```

---

### `.planning/audit/COVERAGE.md`(覆盖台账)

**Analog:** `CONTRACT-MATRIX.md`(D-02:"仿 Phase 2 CONTRACT-MATRIX 先例——证据与判断分离")

**文件头格式**(`CONTRACT-MATRIX.md:1-6` 同构;所有审计文档统一头):

```markdown
# 覆盖台账

**Created:** <date>
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

<一段:本文档角色 + 引用锁定决策号(D-01/D-02)+ 取证方法声明>
```

**逐模块表格**:列 = 路径 / 行数 / 维度 / 审计深度(普审/深挖) / 已过面 N/9 / 产出(发现 ID 或显式"无发现") / 备注。骨架数据直接取 03-RESEARCH.md"审计对象全量清单"(62 文件,行数已实测)。行内引用状态词 + 去向的落格风格仿 `CONTRACT-MATRIX.md:37-51` 矩阵行(每格自含证据或结论,不留裁量)。

**并行写入防冲突**(RESEARCH Pitfall 5 + `CHARTER.md:183` 分文件理由先例):CODE/TOOL 两计划并行时,预建分节骨架(`## CODE 维度` / `## TOOL 维度`)各写各节,或分片后 Wave C 收口合并——与 Phase 2"分 findings 文件避免写冲突"同理。

**cli.py 双维度备注写法**(RESEARCH Open Question 2 裁决):cli.py 整体归 CODE 一行,备注"TOOL 子命令入口,实体逻辑见 TOOL 侧对应模块"——避免双计双审。

**完成判定节**(仿 `CONTRACT-MATRIX.md:267-274` ④完成判定——逐条给出可复算命令 + 数字 + ✓):

```markdown
- 覆盖对象总数:62(对照 03-RESEARCH.md 清单,`grep -cE '^\| \`' COVERAGE.md` → 62 ✓)
- 深挖点:20(14 HYP + 6 D14),逐点有发现 ID 或显式结论 ✓
```

---

### `.planning/audit/HYPOTHESES.md`(就地回填 14 条)

**Analog:** 自身条目结构(无已完成回填先例——回填格式属规划定稿项,但字段槽位已就位)

**现有条目结构**(`HYPOTHESES.md:36-41`,HYP-03 为例——回填只动"状态"行并增补证据/备注行,不动来源与假设正文):

```markdown
### HYP-03: Pure-JS SHA-256 on the recording thread

- **来源:** CONCERNS.md §Tech Debt / Pure-JS SHA-256 on the recording thread
- **假设:** `apps/miniprogram/utils/sha256.js` 为纯 JS 实现并在主线程对完整音频字节哈希……
- **待验证维度:** CODE
- **状态:** 未验证          ← 回填改为:证实 / 证伪 / 细化 + 一句结论
```

**部分证伪的措辞先例**(`HYPOTHESES.md:34`,HYP-02 备注——回填"细化"态可仿此句式):

```markdown
- **备注:** 条目中"deletions uncommitted"半句已被基线核实推翻(钉定时工作树干净、删除已随提交入库,见 CHARTER 基线章节);待验证的仅是"引用失效"半句。
```

**回填增量要求**(D-09/D-10/D-12):状态行附 `file:line @ 5927f36` 证据;"可接受成立"的条目(HYP-04/09/10/12 类)在备注标注 RPT-06 优点/DNF 候选身份,不占发现 ID。文件尾部斜体统计行(`HYPOTHESES.md:227`)需同步更新回填计数。

**本阶段回填集写死**(RESEARCH Pitfall 4):CODE 10 条(HYP-01/03/08/09/10/12/16/17/19/20)+ TOOL 4 条(HYP-04/07/15/18)= 14 条;HYP-25/HYP-14 等只走移交,状态不动。

---

### Phase 4 移交清单(新建)

**Analog:** `CONTRACT-MATRIX.md:255-265` ③债务移交记录(D-11:"延续 Phase 2 移交风格")

**逐条 bullet 格式**(每条:编号(去向)+ 一句观察 + 行号证据 + 关联 ID):

```markdown
- **D14-2(移交 Phase 3):** 重试节奏三份常量(`nls.py:45` / `uploader.js:28` / `verify.js:16`)+ Worker `MAX_RETRIES = 3` 独立字面量与延时表长度无结构绑定(JS 侧为 `.length` 派生)——同一约定四处落点。
- **(移交 Phase 4 DOC,指针):** CLAUDE.md 错误码分支声明与实态不符——已在组② 行 35-41 行下注记录。
```

Phase 3 适配:去向标 Phase 4 DOC/TEST + 对应 HYP 号(如 HYP-14/HYP-25);每条 = `file:line@5927f36 + 一句观察`,HYP 状态不动、不立发现(D-11)。落点文件名属 Claude 裁量(可入 `.planning/audit/` 或阶段目录;须满足 RESEARCH 机械验收"移交清单文件存在")。

---

### scratchpad 工件(基线导出 / ESLint 配置 / D-16 微基准)——仓外,零仓库写入

**Analog:** `CONTRACT-MATRIX.md:311-329` harness 复跑说明(Phase 2 D-06 先例,D-16 明示同构)

**基线导出 + 结构性零触碰保证**(`CONTRACT-MATRIX.md:313-317` + `:320-322` 来源断言):

```bash
# SCRATCH 为会话 scratchpad 下目录,严禁指向仓库内
mkdir -p "$SCRATCH"
git archive 5927f36 apps scripts | tar -x -C "$SCRATCH"
# Phase 2 先例:harness 首部含来源断言——被 require/import 模块的 __file__ 均须以 $SCRATCH 开头
```

**微基准复跑说明的存档义务**(`CONTRACT-MATRIX.md:329`):harness 只调用纯函数、零云 IO、仅存在于 scratchpad 不入仓库;结论入 HYP-03 回填时标注"Mac 环境非真机,量级参考"(D-16)。复跑命令块(含 TZ/PYTHONPATH 等环境前缀)存入阶段产物,仿 Phase 2 把复跑说明写进 CONTRACT-MATRIX 的做法。

**仪器确切命令**:全部直接取 03-RESEARCH.md Code Examples #2-#8(已实测配方,含 ruff `--isolated --select ... --ignore PLC0415,TRY003,S101`、vulture `--min-confidence 80`、eslint 平面配置全文)——Don't Hand-Roll 表明令不得自拟。

## Shared Patterns

### 证据引用格式(全部产物通用)
**Source:** `CHARTER.md:14-15`(格式定义)+ `:56-64`(取证命令)
```markdown
单行:`path:line @ 5927f36`;多行:`path:10-25 @ 5927f36`
提取:git show 5927f36:<path> / git grep -n <pat> 5927f36 -- apps/(禁读工作树取证)
```

### 文档头三件套 + 尾部斜体封版行
**Source:** `CONTRACT-MATRIX.md:1-6` 与 `:393-394`;`HYPOTHESES.md:1-4`;`DO-NOT-FIX.md:1-8`
**Apply to:** COVERAGE.md、scans/ 各文件、移交清单
```markdown
# <标题>
**Created:** <date>
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)
…
---
*<文档名>: <date>(<一行收口统计:N 条落格 / 对账等式 / 零 diff 结果>——Phase 3 产物封版)*
```

### 零 diff 验证记录(每计划收尾 + 阶段收尾)
**Source:** `CONTRACT-MATRIX.md:364-371`
````markdown
### 零 diff 验证记录(CHARTER D-03,每阶段必跑必记)

```bash
git diff --stat 5927f36 -- apps/ scripts/ docs/
# 实际输出:(空)——apps/、scripts/、docs/ 相对基线零改动
```

`git status --porcelain` 检查结论:输出仅含 `.planning/` 路径条目……
````
Phase 3 增量:scans/ 秘密反扫(RESEARCH Code Examples #9)加入收尾核验——`git grep -nE 'OSSAccessKeyId=[^ ]|Signature=…' -- .planning/audit/scans/` 期望零命中。

### 机械对账收口(可复算命令 + 数字 + ✓)
**Source:** `CONTRACT-MATRIX.md:373-381`(7 条等式先例)
**Apply to:** COVERAGE.md 完成判定、阶段收尾、各计划 verify 步骤
```markdown
1. **发现计数** — `grep -c '^### F-CODE-' .planning/audit/findings/code.md` → N(扣 F-CODE-00 示例)
2. **回填计数** — 14 个指定 HYP ID 状态 ≠ "未验证" ✓
3. **对账等式** — 确认 X + 误报 Y + 移交 Z = 命中总数 ✓
```

### DNF 负面对照(普审撞见时跳过,不立发现)
**Source:** `DO-NOT-FIX.md:12-43`(DNF-01~04)+ `CONTRACT-MATRIX.md:23-29` 负面清单节先例
**Apply to:** CODE/TOOL 普审全部模块;对照点已标注在 RESEARCH 对象清单(transcriber.py→DNF-01、config.js→DNF-02、handler.py→DNF-03、sts.py→DNF-04)。矩阵判定列的排除注写法可仿:`—(DNF-04 对照点:STS 原始秘密下发系 by-design,负面清单排除,不立 F-CON)`(`CONTRACT-MATRIX.md:95`)。

### 中文正文 + 英文 ID/严重度术语
**Source:** 全部 Phase 1/2 产物(如 `findings/contract.md` 通篇)
**Apply to:** 所有 Phase 3 产物——严重度写 `LOW/MEDIUM/HIGH/CRITICAL/INFO`、ID 写 `F-CODE-NN/HYP-NN/D14-N`,正文与理由用中文场景语言。

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `HYPOTHESES.md` 的"已完成回填"条目 | 假设回填 | in-place 字段变更 | 25 条 HYP 全部仍为"未验证",无一条完成态先例;回填格式(状态词取值、证据行位置)需规划定稿——建议:状态行 `证实/证伪/细化 — <一句结论>`,下增 `- **证据:**` 行,备注行承载 RPT-06/DNF 候选标记,与 HYP-02 既有备注措辞同风格 |

## Metadata

**Analog search scope:** `.planning/audit/`(CHARTER/HYPOTHESES/DO-NOT-FIX/CONTRACT-MATRIX/findings/)、`.planning/phases/02-*/`(目录结构核对)
**Files scanned:** 8(CHARTER.md、HYPOTHESES.md、DO-NOT-FIX.md、CONTRACT-MATRIX.md、findings/contract.md、findings/code.md、findings/toolchain.md、phase 目录清单)
**Pattern extraction date:** 2026-07-04
