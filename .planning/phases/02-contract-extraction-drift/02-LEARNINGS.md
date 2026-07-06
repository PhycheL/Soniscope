---
phase: 02
phase_name: "contract-extraction-drift"
project: "SoniScope — 上线前代码审计里程碑"
generated: "2026-07-05"
counts:
  decisions: 8
  lessons: 6
  patterns: 8
  surprises: 5
missing_artifacts:
  - "UAT.md"
---

# Phase 02 Learnings: contract-extraction-drift

## Decisions

### FC 列元数据字段区分 n/a 与 absent 双语义
x-oss-meta 七字段的 FC 列不一刀切:六字段判 n/a(FC 生产代码零 meta 触点,职责结构性不触及),sha256 判 absent 候选(verify-upload 职责语义上应然参与,但 head.py docstring 引 tech-spec §4.2 声明设计上不校验)——是否构成覆盖洞的归类留给判定计划。

**Rationale:** "结构性不适用"与"应参与而未实现"是不同结论,机械统一标注会掩盖覆盖洞候选;裁决以 `git grep 'x-oss-meta' 5927f36 -- apps/fc/` 实测结果支撑。
**Source:** 02-01-SUMMARY.md

---

### chunk_total 三段映射按"语义分歧才是 diverge"判 agree
小程序 manifest `null` → OSS meta `"0"` → Worker manifest `None` 的字面差异判 agree:两侧注释/docstring 声明同一 §3.2 约定,属字面异/语义同,格内注明两侧映射约定行号。

**Rationale:** diverge 指语义分歧而非字面差异(判定标准章节明文);机械判 diverge 会制造伪发现。
**Source:** 02-01-SUMMARY.md, 02-01-PLAN.md

---

### 7 个错误码小程序格判 absent 但裁良性,合并单条 F-CON
classifyFcResponse 全文为证:小程序按 statusCode 段分支 + `data.error` 通用透传,7 个错误码字面量在实现代码零出现——7 格全 absent;但判定时裁良性合并为单条 F-CON-05(通用透传使每码行为等同,错误码对客户端是可用信息而非分支义务),absent 格不机械判覆盖洞。

**Rationale:** 状态词(静态事实)与四类归类(影响判断)分离;7 格同根因,一条发现 + 显式覆盖映射比 7 条重复发现更能驱动修复。
**Source:** 02-02-SUMMARY.md, 02-04-SUMMARY.md

---

### 行 4/5 裁潜伏而非活跃失配
key 目录日期来源(双独立入参本地时区)与第四处无校验反推两处 diverge 裁"潜伏":AC#4 约束下上传 key 用 FC 返回值,错位 key 不进 OSS——当前输入域无行为分叉,preview 复用即爆。

**Rationale:** 四类归类以"当前输入域内是否已产生行为分叉"为界;执行佐证(S-07 实证纯函数可产出错位 key)支撑"变更即爆"的潜伏定性而非活跃定性。
**Source:** 02-04-SUMMARY.md

---

### 普查命中的联调工具契约镜像拆矩阵新行
普查发现 fc_live.py/verify_upload_live.py 联调工具族是契约字面量的额外镜像声部,拆 3 个矩阵新行做语义对照(全 agree,fc_live.py:41 注释自证故意重复);组② Worker 列 n/a 裁决不变(工具非业务流水线)。

**Rationale:** D-14 规定普查命中的契约承载逻辑入矩阵;工具代码是镜像声部但不改变业务列的结构性裁决。
**Source:** 02-02-SUMMARY.md

---

### chunk 后缀样本值以 chunking.js 实际产出为准
Open Question 3 裁决:chunking.js `addChunk` 只写 chunk_seq,分片不改 fragment_id 形态——chunk 样本 S-15 与典型值同形,分片信息仅入 meta。

**Rationale:** 样本值不靠推测,以基线代码实际行为定;实测 `addChunk` 产出 chunk_seq=1,2 且 fragment_id 原样。
**Source:** 02-03-SUMMARY.md

---

### 测试配方采用"现状行为锁定"原则
CONTRACT-TEST-RECIPE.md 对 F-CON-01/02/03 等分歧断言基线现状行为,修复时以"翻转断言"显式过测试。

**Rationale:** 审计里程碑不改代码,配方若直接断言目标态会在现状下全红;锁定现状使测试立即可绿,修复里程碑的每个行为变更都必须显式翻转断言留痕。
**Source:** 02-04-SUMMARY.md

---

### agree 格的既留裁决用判定列括注收口,不破坏对账等式
行 18/22/24 等 agree 格附带的疑点(size=0 Postel 边界、expiration/endpoint 值无下游消费)以判定列括注处理:size=0 分析并入 F-CON-06 证据,未消费字段裁"单侧消费选择"不立 F-CON——保持 diverge/absent 格数 = F-CON 条数的对账等式成立。

**Rationale:** 对账等式是封版的机械可复核条件;agree 格的边缘疑点走括注与并入既有发现,而非破坏等式另立条目。
**Source:** 02-04-SUMMARY.md

---

## Lessons

### 研究勘察行号普遍有小幅偏差,落格前必须逐一复核
02-01 记录了 11 处勘察起点行号与 `git show 5927f36` 复核实际行号的偏差(多为 ±1-4 行,常见原因是注释行/函数声明行计入与否);02-02 又发现 errors.py:23-25 中 :25 为空行。全部以复核实际为准落格并如实记录偏差表。

**Context:** RESEARCH 阶段的行号只能当勘察起点;计划中"发现勘察行号有偏差以实际为准并如实记录"的明文授权让执行者无需升级即可修正,这一授权模式值得沿用。
**Source:** 02-01-SUMMARY.md, 02-02-SUMMARY.md

---

### 项目级文档声明不能当证据,须以代码实态裁决
CLAUDE.md 声明 "uploader.js branches on the same strings"(小程序按错误码字符串分支),被 classifyFcResponse 实态推翻:实际按 statusCode 段分支,7 码字面量零出现。声明失实作为 DOC 线索移交 Phase 4,不在契约矩阵立 DOC 判断。

**Context:** 审计取证只认基线代码;文档与实态的矛盾本身是发现素材,但要归入正确维度、由对应阶段裁决,不跨维度抢判。
**Source:** 02-02-SUMMARY.md, 02-04-SUMMARY.md

---

### 机械对账命令会自指:命令原文含被计数模式导致计数偏差
收尾章节写入的对账命令原文本身包含被计数的模式字面量(`@ 5927f36`、`✅`、`待判定`),使首轮记录数字与复算结果偏差 1。修正方式:改用行首锚定的自指免疫 grep 模式,或显式注明自指计数(如 236 = 正文 235 + 命令原文 1)。

**Context:** 任何"文档内命令统计文档自身"的对账设计都要预防自指;行首锚定(`^| S-`、`^### F-CON-`)是最简单的免疫手段。
**Source:** 02-04-SUMMARY.md

---

### 增量落格时的前向引用行号会失效,需后续任务回改
Task 1 落格时把普查新行编号预估为 44-46,组③ 落格(实际占行 44-48)后普查行变为 49-51,Task 2 提交内一并修正组② 的 3 处前向引用。

**Context:** 同一文档多任务增量写入时,前面任务对后面章节行号/编号的前向引用是脆弱的——要么用要素名等稳定标识引用,要么在编号确定后安排回改。
**Source:** 02-02-SUMMARY.md

---

### 执行顺序偏离"先预期后实测"时,可用既有静态结论补救防倒灌
计划要求先写定样本预期再执行;会话实际先跑了 python harness 再写附录表。补救:预期三格全部从 02-01 已在案的组① 静态结论推导并逐格标注静态行号依据——静态结论先于本计划存在,不存在结果倒灌预期的通道。

**Context:** "防结果倒灌预期"的实质是预期必须有独立于执行结果的来源;顺序颠倒时,只要预期推导锚定在时间上更早的在案证据,目标仍可达成,但应如实记录偏差。
**Source:** 02-03-SUMMARY.md

---

### 需求簿记要随计划完成即时回写,否则验证时出现状态不一致
02-VERIFICATION.md 发现 REQUIREMENTS.md 中 CONTRACT-01/03 复选框仍为未勾、追踪表为 Pending,而实质证据均已在案——02-01/02-02 完成时未回写 REQUIREMENTS.md(warning 级簿记遗漏,不阻断)。

**Context:** 多计划分摊同一需求时,先完成的计划容易漏掉需求状态回写;验证报告将其定级为 warning 并建议里程碑对账时补勾,是合理的处置分寸。
**Source:** 02-VERIFICATION.md

---

## Patterns

### git archive 基线导出 + PYTHONPATH shadowing + __file__ 来源断言
执行佐证跑在 `git archive 5927f36 ... | tar -x` 导出的基线树上(整树导出保 import/require 结构,禁止手抄函数体);harness 首部断言 `module.__file__` 以 scratchpad 前缀开头,断言失败即中止,防止误 import 工作树代码。

**When to use:** 需要对钉定基线代码做行为级验证、又必须防止工作树污染证据链时。
**Source:** 02-03-SUMMARY.md, 02-03-PLAN.md

---

### TZ 环境变量驱动双时区复跑
时区敏感样本(跨时区、近午夜、跨年)以 `TZ=Asia/Shanghai node <harness>` 与 `TZ=America/New_York node <harness>` 双跑,每条佐证记录写明 TZ,附录注明"JS 执行佐证反映指定 TZ 下的行为"。

**When to use:** 被测逻辑含本地时区依赖(如 JS `Date` 推导日期)时——单时区执行结果不可泛化,必须显式控制 TZ 并入档。
**Source:** 02-03-SUMMARY.md

---

### 先预期后实测的样本三元组(预期/实测/销号)
样本表每行先从静态结论推导写死三处预期行为,再执行回填实测列并销号;执行结果与静态判定矛盾时原样记录矛盾供判定计划裁决,不改静态状态词。

**When to use:** 用执行证据佐证静态审计结论时——三元组结构防结果倒灌预期,销号列使"全部样本已验证"可机械检查(销号列无空置)。
**Source:** 02-03-PLAN.md, 02-03-SUMMARY.md

---

### 执行结果只作佐证,静态行号对照是判据
矩阵状态词由静态对照决定;harness 执行结果以格内括注形式回填,佐证记录注明"执行结果为佐证,判据以静态行号对照为准"。

**When to use:** 审计基线钉定于某 SHA 时——执行环境(解释器版本、TZ、平台)引入的变量不应污染以代码文本为准的契约判定,行为证据用于支撑严重度与归类。
**Source:** 02-03-PLAN.md, 02-01-SUMMARY.md

---

### 证据住矩阵、判断住台账的分离(状态词 vs 四类归类 vs Postel 分析)
矩阵格只放状态词 + 行号证据;四类标签 + F-CON 链接回填判定列;Postel 宽严三要素(谁严谁宽/失配方向/触发条件)完整分析住 F-CON 发现的证据字段。矩阵与台账双向引用。

**When to use:** 证据收集与影响判定分属不同工作波次时——先封证据再判定,防止判断预设污染抽取;双向引用保可追溯。
**Source:** 02-04-SUMMARY.md, 02-04-PLAN.md

---

### 单条发现覆盖多个同根因格,对账等式显式给覆盖映射
F-CON-05 一条覆盖行 35-41 七格(同根因:通用透传),收尾对账等式显式写 `12 格 = 5×1 + 1×7`,保持机械可复算。

**When to use:** 多个矩阵格源于同一根因时——合并成一条发现避免修复清单膨胀,但对账等式必须写出映射,否则"格数 = 发现数"的检查会误报。
**Source:** 02-04-SUMMARY.md

---

### 普查双保险:候选清单逐项核实 + 系统扫描命令存档,三态收口
9 项候选逐项给出三态结论(拆矩阵新行 / 指针 / 已检查无新发现);5 条 `git grep ... 5927f36` 命令原文 + 命中计数存档;命中分栏处理(实现代码命中入矩阵,测试目录命中作"常量被测试锁定"辅助证据);末尾机械对账行(命令数/命中数/新行数/辅助证据数/无新发现数)。

**When to use:** 回答"X 之外还有没有 Y"类完备性问题时——候选清单防漏、系统扫描防盲区、命令存档使"查过了"可复核,三态收口使完成判定可验收。
**Source:** 02-02-SUMMARY.md, 02-02-PLAN.md

---

### 阶段封版:零 diff 记录 + 机械对账等式 + 成功判据自查 + 文档尾摘要
收尾章节记录零 diff 命令原文与实际输出(空)、多条可复算对账等式(任一不平须修复后封版)、ROADMAP 成功判据逐条打勾并注章节指针、文档尾一行斜体摘要(关键计数)。

**When to use:** 多计划协作写同一产物文档的阶段收尾——封版章节使后续阶段/验证者可独立复算全部关键数字。
**Source:** 02-04-SUMMARY.md, 02-04-PLAN.md

---

## Surprises

### 小程序对 7 个错误码字符串零字面量,推翻项目文档声明
Open Question 1 裁决结果出乎预期:uploader.js 按 statusCode===200 二分、verify.js 按 200/≥500/4xx 三段,`data.error` 仅 String() 透传——CLAUDE.md "uploader.js branches on the same strings" 声明与实态完全不符(uploader.js:47 提及 3 码但为注释)。

**Impact:** 组② 7 行小程序格全 absent;产生 Phase 4 DOC 维度移交线索(文档声明失实);错误码契约的"共享标识符"叙事需要修正。
**Source:** 02-02-SUMMARY.md

---

### 错位 key 上传后 Worker 静默跳过,数据滞留 OSS 无告警
S-07 实证小程序纯函数自身可产出目录≠前缀的错位 key(fragmentId@23:59:59 + recordedAt@次日 00:00:01);S-18 实证此类 key 被 Worker `fragment_id_from_key` 往返等式拒绝返回 None——该类对象上传后 Worker 轮询静默跳过,数据滞留 OSS 且无任何告警。

**Impact:** 这是 F-CON-02/03 潜伏定级与严重度评估的核心行为事实;"静默跳过无告警"的失败模式比预想的"报错可见"更危险。
**Source:** 02-03-SUMMARY.md

---

### FC↔Worker 主链 100% 无漂移
15 个 python 侧样本中 FC `sts.object_key_for` 与 Worker `oss_admin.object_key_for` 同收同拒、产出逐字符相等,FC 签发的每个 key 经 Worker 往返解析全部成立(含闰日、跨年、宽字符集边界)——核心假设 HYP-13 所担忧的三处重复实现,其中两处 Python 实现完全一致。

**Impact:** 契约漂移全部集中在小程序 JS 声部;修复面比"三处互相漂移"的最坏预期显著收窄。
**Source:** 02-03-SUMMARY.md

---

### FC 响应字段 expiration/endpoint 经校验后零下游消费
小程序对 issue-credential 响应做 7 字段非空校验,但 expiration 与 endpoint 校验后无任何下游消费:policy 过期本地用 now+900s 独立推导,上传 URL 用 config.OSS_UPLOAD_URL;verify 响应的 actual_size/etag/size/last_modified 提取后也未随状态补丁落存。

**Impact:** 契约的"必备性"与"实际使用"脱节——字段名一致的 agree 格背后仍有单侧消费选择问题,判定时以括注收口而非立发现。
**Source:** 02-02-SUMMARY.md

---

### 活跃失配为零:12 个分歧格无一在当前输入域产生行为分叉
最终四类分布:潜伏 2 / 覆盖洞 3 / 良性 1 / 活跃失配 0。AC#4(object_key 用 FC 返回值)这一处约定实质挡住了全部潜在的活跃失配路径。

**Impact:** 上线风险画像好于预期——无需 BLOCKER 级契约修复;但两条潜伏发现(MEDIUM)的触发条件(preview 复用)须在修复里程碑封死。
**Source:** 02-04-SUMMARY.md
