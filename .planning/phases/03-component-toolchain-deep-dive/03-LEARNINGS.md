---
phase: 03
phase_name: "component-toolchain-deep-dive"
project: "SoniScope — 上线前代码审计里程碑"
generated: "2026-07-05"
counts:
  decisions: 9
  lessons: 5
  patterns: 8
  surprises: 6
missing_artifacts:
  - "UAT.md"
---

# Phase 03 Learnings: component-toolchain-deep-dive

## Decisions

### 工具命中逐条人工核实,不做批量定性
258 条工具命中(mypy/ruff 门禁 + ruff 扩展集 + vulture + eslint + 五类秘密扫描)全部经 `git show 5927f36` 逐条人工核实后三态销号;探针信号(S110/S104/DTZ/S105/S106/ARG)明确"逐条核实未批量定性";apps/fc/tests/ 的 35 条命中也逐条核实后才全判误报。

**Rationale:** 成功判据 3 要求"无原始 linter 输出直接充当发现";批量定性会把工具的规则视角冒充审计判断,逐条核实才能把 15 条真确认项从 243 条误报里可靠分离。
**Source:** 03-02-SUMMARY.md, 03-VERIFICATION.md

---

### "可接受自评"经 D-10 上线语境裁定成立后记优点候选,不占发现 ID
HYP-04/09/10/12 等 CONCERNS.md 自评 "acceptable for MVP" 的条目,深挖证实自评成立后记为 RPT-06 优点候选兼 DNF 候选,不立发现;但同模块的独立缺陷(如 fc_deploy 备份失败不阻断)仍单独立 F-TOOL-02。

**Rationale:** 审计要区分"设计取舍成立"与"取舍范围内的独立缺陷"——前者进优点/Do-NOT-fix 通道,后者照常进台账,避免自评成立掩盖同模块真问题。
**Source:** 03-03-SUMMARY.md, 03-05-SUMMARY.md

---

### 假设的复合陈述拆半句回填:"细化"状态承载部分证实
HYP-16(代码半句证实,文档一致性半句移交 Phase 4)、HYP-18("两代 SDK 并存"证实,"仅脚本级"半句在 Worker 侧证伪)、HYP-03(实现形态证实,低端设备卡顿仅获方向性支持)均回填为"细化"而非"证实"。

**Rationale:** 复合假设各半句证据强度不同,一刀切"证实"会把未验证的半句一并背书;"细化"状态 + 半句级结论保持回填的精确性。
**Source:** 03-03-SUMMARY.md, 03-06-SUMMARY.md, 03-07-SUMMARY.md

---

### F-TOOL-05 定级 MEDIUM 而非 CRITICAL:凭证形态与时效决定锚点
test_asr.py 已提交的预签名 URL 证实后定级 MEDIUM:逐字命中 CHARTER『已过期凭证曾入库(泄露习惯风险)』锚——AccessKeyId 系 TMP. 前缀 STS 临时凭证、URL 内 Expires 时间戳可静态判定已过期、权限仅单对象 GET,不触 CRITICAL 的"有效长期凭证泄露"锚。

**Rationale:** 严重度按锚点对号而非按"凭证入库"字面惊悚度;过期临时凭证与有效长期 AK 的风险量级不同,锚点体系正是为此设计。
**Source:** 03-06-SUMMARY.md

---

### app.py 0.0.0.0 绑定销号降级:运行环境语境决定是否成立发现
ruff S104(bind-all)命中经人工核实降级不立发现:FC 容器内 0.0.0.0 为自定义运行时必需形态,平台网关是唯一公网入口。

**Rationale:** 安全规则的通用告警要放进部署语境判断;容器内 bind-all 与裸机 bind-all 的暴露面完全不同。
**Source:** 03-04-SUMMARY.md

---

### uploading 死态与无界重试同口径定级 MEDIUM 潜伏类
小程序队列 `uploading` 残留项不被自动驱动拾取、不在可操作按钮集合、不计积压提示(五文件共证)→ F-CODE-06 定级 MEDIUM 潜伏:正常完成流程不触发、进程中断即爆——与 F-CODE-02(sha256 失配/转码失败无界重下)采用同一定级口径。

**Rationale:** 同类失败模式(正常路径不触发、异常路径必然触发且无恢复通道)统一按"潜伏失配"MEDIUM 锚定级,保持台账内部一致性。
**Source:** 03-04-SUMMARY.md, 03-03-SUMMARY.md

---

### 共享登记表的下落列留给收口计划统一回填
COVERAGE.md 深挖点登记表(20 行)的"下落"列,03-03/03-04/03-05 各自只把素材记入对象行备注,统一由 03-07 收口回填。

**Rationale:** 03-04(CODE)与 03-05(TOOL)属并行 wave,同表写入会产生冲突;素材分散落备注 + 收口集中裁定,兼顾并行效率与单一裁定点。
**Source:** 03-04-SUMMARY.md

---

### D14 债务线索经三要素框架逐条独立裁定,产出双态结论
六条 D14 移交线索各自走 D-13 三要素(①结构必要性 ②兜底机制 ③漂移后果):D14-2/3/4 立发现(F-CODE-07/08、F-TOOL-08),D14-1/5 裁"不构成债务"(跨语言/跨运行时结构必然 + 有兜底),结论不占 F-ID、落 COVERAGE 登记行并附三要素理由。

**Rationale:** "重复实现"不自动等于债务;三要素框架把裁定从直觉变成可复核的论证,"不构成债务"也是需要理由的正式下落。
**Source:** 03-07-SUMMARY.md

---

### D14-6 不重复立发现,让位既有 F-CON-03
key 反推第四处实现的债务实体与漂移后果已由 Phase 2 F-CON-03(MEDIUM)完整承载,CODE 维度三要素复核确认定性后销号落点直接指向 F-CON-03,避免同一事实双立。

**Rationale:** 跨维度审计中同一事实可能被两个维度各自撞见;先查既有台账再立新条,发现台账的去重责任在后来者。
**Source:** 03-07-SUMMARY.md

---

## Lessons

### git grep 带 rev 前缀时输出为四段,脱敏管道字段选择要按实际输出核对
RESEARCH 配方的脱敏管道 `cut -d: -f1,2` 在 `git grep <rev>` 输出(`rev:path:line:content` 四段)上会把行号剥掉,只剩 `rev:path`,销号表将无 path:line 可引。执行时修正为 `cut -d: -f1-3`(保留行号、内容列仍剥离)。

**Context:** 脱敏管道本身也是需要验证的代码;研究配方在真实输出形态上没跑过就可能有字段错位,执行者要先看一眼实际输出再套管道。
**Source:** 03-01-SUMMARY.md

---

### 自引计数是对账等式的顽固缺陷,每个新文档都要重新防
Phase 2 已出现过的自指问题在 Phase 3 再现两次:COVERAGE 完成判定 #2 的"待审"计数被判定文本自身污染(修复:字符类写法 `/## CODE 维[度]/`);验证时又发现 #3 的 `grep -c '| 9/9 |'` 字面命令返回 64(含判定行自匹配),声明值 63。

**Context:** 对账命令写进被统计的文档,自匹配问题必然反复出现;可选对策——行首锚定、字符类拆字、或显式注明"N = 正文 N-1 + 本行 1"。这是跨阶段复发问题,值得进章程级检查单。
**Source:** 03-07-SUMMARY.md, 03-VERIFICATION.md

---

### 上游计划留下的去向指针要在承接计划里显式闭环,即使计划没列该文件
03-02 在 scans/gates-baseline.md 留了 7 条"→ 深挖线索(03-06 …)"指针,03-06 计划正文未把该文件列为修改对象;执行时按台账闭环原则追记全部去向(#1→F-TOOL-06、#2-7→HANDOFF 移交),避免指针悬空。

**Context:** 多计划接力写审计台账时,"谁留的指针谁的下游闭环"不能只靠计划文件清单驱动;执行者要主动扫上游留下的占位。
**Source:** 03-06-SUMMARY.md

---

### 静态审计工具在这类代码库上的信噪比极低,只能当线索池
五档 258 命中最终确认 15、误报 243(94% 噪音):ruff 扩展集 69 中 5 真、eslint 29 全误报、秘密扫描 69 中 2 真。误报主因是仓库惯例(catch(e) 形参不用、`== null` 故意宽松、pytest/Protocol 签名契合)与测试自述假值。

**Context:** scans/(线索池)与 findings/(判断)物理分离的设计被证明必要;直接把工具输出当发现会让台账 94% 是垃圾。工具的真正价值在两条:提供人工普审的辅助信号,以及量化"漏报面底数"(如 eslint 0 error 证明 HYP-15 的漏报实害为零)。
**Source:** 03-02-SUMMARY.md, 03-05-SUMMARY.md

---

### 仓内直调 uv 会隐式创建 .venv 并可能更新 uv.lock,零写入约束需显式环境隔离
worktree 内无项目 venv 时,`uv run` 默认在仓库根创建 `.venv` 并可能更新 uv.lock,与零仓库写入约束冲突;处置为 `UV_PROJECT_ENVIRONMENT` 指向 scratchpad + `uv run --frozen`,直调前后零 diff 快查确认。

**Context:** 包管理器的隐式写入行为(venv 创建、lockfile 刷新)是零 diff 审计的暗礁;任何"只读"工具调用前要想清楚它会往哪写。
**Source:** 03-01-SUMMARY.md

---

## Patterns

### 扫描档案四件套:命令原文 + 工具版本行 + 完整输出 + 三态销号表
每份 scans/ 档案固定结构:文档头三件套 → 每扫描小节(fenced bash 命令原文 + 实测版本行 + 完整输出,路径改写为仓库相对)→ 末尾空销号表骨架(销号列由下一计划填)。

**When to use:** 任何把工具输出纳入审计证据链的场合——版本与命令入档使结果可复现,销号表使"输出已处理完"可验收。
**Source:** 03-01-SUMMARY.md, 03-01-PLAN.md

---

### 三态销号(确认/误报/移交)+ 跨档对账等式
每条命中销为确认/误报/移交三态之一,每档尾部对账等式(三数之和 = 命中总数)可复算;确认项必须有去向(F-ID/HYP/深挖线索),去向列零占位是收口条件。

**When to use:** 大量线索需要全量处置且要向外证明"没有漏掉任何一条"时;沿 Phase 2 先例,已成为本仓审计的标准动作。
**Source:** 03-02-SUMMARY.md

---

### 临时仪器包合法性走 blocking-human 检查点,预设兜底方案
经 uvx/npx 临时拉取的分析包(vulture/eslint)在运行前设 blocking-human 检查点:呈现 RESEARCH 的包合法性核实证据(官方 org、下载量、无 postinstall、已实测),用户批准后才拉取;计划同时预设兜底(ruff ARG/ERA + 人工普审替代),拒绝时降级而非停摆。

**When to use:** 审计/受限环境中需要引入任何未在项目依赖内的第三方可执行包时——供应链决策交人,且拒绝路径不阻塞阶段目标。
**Source:** 03-01-PLAN.md, 03-01-SUMMARY.md

---

### 秘密类扫描输出全程脱敏管道 + 收尾反扫双保险
秘密扫描输出经 cut 管道只留 `rev:path:line`(内容列物理剥离),档案内绝不出现匹配内容;每计划收尾对 `.planning/audit/` 跑秘密模式反扫(`OSSAccessKeyId=`/`Signature=`/`LTAI` 值形态)期望零命中。

**When to use:** 审计文档会永久入库而扫描目标可能含真实凭证时——入口脱敏防写入,出口反扫防遗漏,两道门缺一不可。
**Source:** 03-01-SUMMARY.md, 03-07-SUMMARY.md

---

### 覆盖台账以"待审"初始值 + 固定分母清单驱动完成判定
COVERAGE.md 63 对象行(路径|行数|维度|深度|已过面|产出|备注)初始全"待审",9 面关注面清单定稿为全阶段"已过面 N/9"的分母;各计划落格后 awk 区间检查"待审"残留为 0,收口时十条可复算等式全绿封版。

**When to use:** 多计划分摊大量对象的普审工作时——预登记全量对象 + 机械可查的"待审"残留,使"全覆盖"从声明变成可复算事实。
**Source:** 03-01-PLAN.md, 03-07-SUMMARY.md

---

### 逐模块读完立即落格,不攒批
普审执行采用"逐模块 git show 完整读 → 立即写 COVERAGE 行 + findings 条目"的增量节奏,而非读完一批再统一落格。

**When to use:** 长清单逐项审计时——增量落格使进度可中断可恢复,且避免批量回忆时的证据行号串位。
**Source:** 03-05-SUMMARY.md

---

### 销号确认项降级用"03-0N 人工核实下落"追记体例
销号表中先前标"确认"的项在深挖后降级(不立发现)时,不改写原始销号行,而是追记"03-0N 人工核实下落:<降级理由>"——原始线索文字保留、下落闭合。

**When to use:** 后续计划推翻或降级前序计划的初判时——追记而非改写保留判断演变的完整审计轨迹。
**Source:** 03-05-SUMMARY.md, 03-04-SUMMARY.md

---

### scratchpad 微基准三件套:来源断言 + 正确性对照 + 环境限定声明
性能佐证基准在 scratchpad 执行:脚本首部断言被 require 模块路径以 scratchpad 开头;计时前先与 node stdlib crypto 做正确性对照;结果档案通篇标注"Mac 环境非真机,量级参考"并附复跑说明。

**When to use:** 需要给静态论证补充量级级性能证据、但执行环境与生产环境不同时——三件套确保基准可信、可复跑、且不被过度解读。
**Source:** 03-07-SUMMARY.md, 03-07-PLAN.md

---

## Surprises

### make typecheck 在仓内结构性恒红,门禁二值信号早已失效
`apps/fc/shared/app.py:14` 的部署态导入 `from handler import handler`(handler.py 仅在部署 zip 内同目录)在 mypy strict files 范围内且无 override,导致 `make typecheck` exit 恒 1——门禁作为质量信号已失效却无人察觉(F-TOOL-06,MEDIUM)。

**Impact:** "有门禁"不等于"门禁在工作";恒红门禁比没有门禁更糟,因为它训练操作者忽略红色。修复里程碑需处理该结构性导入。
**Source:** 03-06-SUMMARY.md

---

### Makefile 声明了不存在的目标 lint-miniprogram
.PHONY 机械对账(声明集 vs 目标集 comm 比对)发现幻影条目:`lint-miniprogram` 在 .PHONY 列表但无对应规则,按声明名调用得 "No rule to make target" 硬错误——且 agent 文档以该名为调用口径(F-TOOL-07)。

**Impact:** 文档/声明与实际可调用面之间的漂移连 Makefile 自身也存在;.PHONY 完整性对账是低成本高收益的机械检查。
**Source:** 03-06-SUMMARY.md

---

### "legacy SDK 仅脚本级"的假设半句被证伪:它是生产主路径依赖
HYP-18 预设 aliyunsdkcore(legacy POP SDK)只在脚本层使用、不随 Worker/FC 打包;核实发现它是 `apps/worker/pyproject.toml:13` 的声明运行时依赖,且 `nls.py` 生产 filetrans 主路径全程经 legacy AcsClient——FC 侧才属实。

**Impact:** 该 SDK 的维护风险从"脚本级可忽略"升级为"转写主链依赖";假设回填为细化并如实记录半句证伪。
**Source:** 03-06-SUMMARY.md

---

### ESLint 与自研 miniprogram_lint 的规则面完全不重叠,但增量检出零真实缺陷
eslint 29 条 warning 全为仓库惯例内写法(误报),量化证明基线漏报实害为零;但 ESLint 语义类规则面(未用变量、宽松判空等)与 miniprogram_lint 现有规则面(域名/密钥/四件套)零交集。

**Impact:** HYP-15 的两个半句得到相反裁决(覆盖面狭窄证实、漏报实害证伪);缺口以 LOW 级 F-TOOL-04 入账并给出双选项修复建议(增补语义检查或零依赖 eslint 配置)。
**Source:** 03-02-SUMMARY.md, 03-05-SUMMARY.md

---

### 队列状态机存在漏态:uploading 残留项无任何恢复通道
小程序 8 状态上传队列中,`uploading` 状态在进程中断后成为死态——自动驱动只拾取 queued/pending_verify、不在任何可操作按钮集合、不计积压提示,五个文件交叉证实(F-CODE-06,MEDIUM)。

**Impact:** 普审的 9 面清单(而非工具扫描)捕获了本阶段最重要的小程序发现;状态机审计要枚举"每个状态是否有出边"。
**Source:** 03-04-SUMMARY.md

---

### 转码失败"不再重试"的 docstring 与实态相悖,与 sha256 失配合流成无界重试
audio.py `_archive_failed` docstring 声称失败留档后"不再重试",实态是留档不阻止下轮重下——与 poller 的 sha256 失配全量重下合流,使 F-CODE-02 从 LOW 升级 MEDIUM(一次损坏上传即构成现实触发条件)。

**Impact:** 注释与实态不符(9 面之一)不只是文档问题,它直接改变了另一发现的严重度;跨模块普审的发现合并机制(增补证据并升级)发挥了作用。
**Source:** 03-03-SUMMARY.md
