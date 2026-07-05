# 校准台账(CALIBRATION)

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本文件依据锁定决策 D-01~D-04/D-08 记录跨维度对齐调级、真重复并入判定与工作量重估,并依据 D-05/D-06/D-09/D-10/D-11/D-12 承载根因聚类划分、修复工作包划分、上线判定准则全文与 40 条逐条上线判定。findings/*.md 封版不动,本文件是唯一调整记录载体(D-03)。**注记:** CHARTER 九字段 schema 字段 8/9(上线判定槽、`draft → calibrated`)的台账回填预期由本文件承载——D-03(后定,locked)压过 schema 字面预期;findings/*.md 的上线判定槽与状态槽保持 as-built,一切终态以本文件与最终报告为准。证据一律 `path:line @ 5927f36` 格式;秘密类证据只写位置与模式名,绝不复制值本体(CHARTER 秘密红线)。

---

## 逐条抽取与分布复核

> 抽取方法:以 `^### F-` 标题为唯一锚点逐条抽取,剔除 5 条 `F-*-00` schema 示例(RESEARCH Pitfall 1:上线判定槽存在带注记 27 条/裸槽 18 条两种格式,不依赖槽位文本);分布以现场 grep 实测为准(RESEARCH Pitfall 2:勿抄 CONTEXT.md 笔误)。

**现场复核命令与输出照录(2026-07-05 实跑):**

```
$ grep -hc '^### F-' .planning/audit/findings/*.md | paste -sd+ - | bc
45
$ grep -h '^### F-' .planning/audit/findings/*.md | grep -vc '\-00:'
40
$ (逐条目 awk 抽取严重度字段,剔除 -00)→ MEDIUM 11 / LOW 26 / INFO 3;CRITICAL 0 / HIGH 0
$ (逐条目 awk 抽取工作量字段,剔除 -00)→ S 32 / M 7 / L 1 / XL 0(唯一 L = F-CON-04 闭环方案口径)
$ git diff --stat 5927f36 -- apps/ scripts/ docs/ | wc -l
0
```

MEDIUM 11 条逐条归属(grep 实测):F-CON-02、F-CON-03、F-CODE-02、F-CODE-06、F-TOOL-05、F-TOOL-06、F-DOC-03、F-TEST-03、F-TEST-04、F-TEST-05、F-TEST-06。

**40 条真实发现清单(原级,校准前;修复建议与关联发现详见各封版台账,此处只列定位字段):**

| # | ID | 维度 | 严重度 | 工作量 | 标题(缩写) |
|---|-----|------|--------|--------|--------------|
| 01 | F-CON-01 | CON | LOW | S | 小程序 fragment_id 校验缺日期合法性检查 |
| 02 | F-CON-02 | CON | MEDIUM | S | buildObjectKeyPreview 双独立入参可产出错位 key |
| 03 | F-CON-03 | CON | MEDIUM | S | key→fragment_id 第四处反推无任何校验 |
| 04 | F-CON-04 | CON | LOW | L | verify-upload 不校验 x-oss-meta-sha256(闭环 L/保守 M 双口径) |
| 05 | F-CON-05 | CON | INFO | S | 7 个 FC 错误码字面量小程序零出现,经 body.error 通用透传 |
| 06 | F-CON-06 | CON | LOW | S | 上传大小上限 50 MB 无小程序侧镜像常量或预检 |
| 07 | F-CODE-01 | CODE | LOW | S | process_plan 声明 fragments_root 形参未使用 |
| 08 | F-CODE-02 | CODE | MEDIUM | M | 持久性失败对象每轮重下重处理,无失败计数/隔离/告警 |
| 09 | F-CODE-03 | CODE | LOW | S | 原子写崩溃窗口 *.tmp 孤儿文件无清理路径 |
| 10 | F-CODE-04 | CODE | LOW | S | .env 解析为不设边界的 CWD 向上搜索 |
| 11 | F-CODE-05 | CODE | LOW | S | issue-credential 在 allowlist 之外无频控/配额面 |
| 12 | F-CODE-06 | CODE | MEDIUM | M | uploading 残留态成死态:不拾取、无手动入口、不计积压 |
| 13 | F-CODE-07 | CODE | LOW | S | 重试退避约定四处独立落点,Worker 侧数值无字面锁定 |
| 14 | F-CODE-08 | CODE | LOW | S | FC 请求组装 utils 与 pages 两份同构,无共享源 |
| 15 | F-TOOL-01 | TOOL | LOW | S | verify-prep 越权反例把非拒绝类异常误报为疑似放行 |
| 16 | F-TOOL-02 | TOOL | LOW | S | deploy-fc 备份失败不阻断部署,降级为注记 |
| 17 | F-TOOL-03 | TOOL | LOW | S | test-verify-upload 测试对象清理失败被静默吞掉 |
| 18 | F-TOOL-04 | TOOL | LOW | S | 小程序 JS 语义类缺陷无任何静态门禁 |
| 19 | F-TOOL-05 | TOOL | MEDIUM | S | test_asr.py 内置已过期预签名 OSS URL,签名 URL 入库先例 |
| 20 | F-TOOL-06 | TOOL | MEDIUM | S | make typecheck 门禁结构性恒红(app.py 部署态导入) |
| 21 | F-TOOL-07 | TOOL | LOW | S | Makefile .PHONY 幻影目标 lint-miniprogram |
| 22 | F-TOOL-08 | TOOL | LOW | S | 联调工具契约镜像集群靠注释同步,零测试兜底 |
| 23 | F-DOC-01 | DOC | LOW | S | tech-spec 声称 sha256 用 wasm-crypto,实为主线程纯 JS |
| 24 | F-DOC-02 | DOC | LOW | S | tech-spec 依赖清单失实(nls20180628 未装/legacy SDK 未列) |
| 25 | F-DOC-03 | DOC | MEDIUM | S | 发布文档未覆盖 config.js ENV 生产翻转步骤 |
| 26 | F-DOC-04 | DOC | LOW | S | AGENTS.md 声称 ~/SoniScope 配置兜底,实态直接报错 |
| 27 | F-DOC-05 | DOC | LOW | S | AGENTS.md 与两份子 README 现状叙述滞后于实施进度 |
| 28 | F-DOC-06 | DOC | LOW | S | 权威文档迁移后旧路径引用全仓死链(10 文件 ≈47 处) |
| 29 | F-DOC-07 | DOC | INFO | S | vendored Aliyun FC 示例仓 1003 文件 ≈28 MB 入库 |
| 30 | F-DOC-08 | DOC | INFO | M | agent 工具脚手架四处重复,独立副本已实际漂移 |
| 31 | F-TEST-01 | TEST | LOW | S | 活体路径零自动化覆盖,缺 code 即全 SKIP 且 exit 0 |
| 32 | F-TEST-02 | TEST | LOW | M | pages 胶水层为选择性驱动,index.js 其余路径无自动化 |
| 33 | F-TEST-03 | TEST | MEDIUM | S | scripts/ 在全部静态门禁之外,已有违例与签名 URL 实害 |
| 34 | F-TEST-04 | TEST | MEDIUM | S | make 门禁二值信号无守护(JS 桥静默 skip 等三处失真) |
| 35 | F-TEST-05 | TEST | MEDIUM | M | 契约镜像常量与派生函数无对称测试锁定(7 脆弱区) |
| 36 | F-TEST-06 | TEST | MEDIUM | M | 失败/恢复路径行为无测试兜底(6 脆弱区) |
| 37 | F-TEST-07 | TEST | LOW | S | 低危功能缺失面的测试同步义务(6 脆弱区) |
| 38 | F-TEST-08 | TEST | LOW | M | 手写 fake 与真实实现无行为面对齐锁定 |
| 39 | F-TEST-09 | TEST | LOW | S | oss_sign 无 raw secret 不出现在表单/policy 负断言 |
| 40 | F-TEST-10 | TEST | LOW | S | 断言强度与测试卫生杂项(5 处聚合) |

---

## 跨维度对齐扫描(D-01 严重度 / D-04 工作量)

> 扫描口径(D-01):按主题横向比对同类问题在不同维度的定级,仅对"同类问题不同级"条目拟调整到统一 CHARTER 锚点(锚点表 `CHARTER.md:110-116 @ 工作树`,下同);单条原定级默认信任,不做全量复核。工作量同法(D-04,分档表 `CHARTER.md:126-131`)。

### 严重度对齐扫描记录(按主题)

| 主题 | 跨维度成员与现级 | 对照结论 |
|------|------------------|----------|
| 签名 URL/秘密门禁面 | F-TOOL-05(MEDIUM)× F-TEST-03(MEDIUM) | 同级一致;F-TEST-03 定级明文参照 F-TOOL-05(TEST-AUDIT.md 反向映射定级规则),共同命中 MEDIUM 锚"已过期凭证曾入库"(CHARTER.md:114) |
| 门禁二值信号失效 | F-TOOL-06(MEDIUM)× F-TEST-04(MEDIUM) | 同级一致;F-TEST-04 定级明文参照 F-TOOL-06,共同命中 MEDIUM 锚"误导性声明"系(CHARTER.md:114) |
| 契约镜像缺锁定 | F-CODE-07(LOW)× F-TOOL-08(LOW)× F-TEST-05(MEDIUM) | 无不一致:F-CODE-07/F-TOOL-08 同为纯维护成本类命中 LOW 锚"技术债与非关键路径重复实现"(CHARTER.md:115);F-TEST-05 系脆弱区缺口元发现,按 TEST-AUDIT 预置定级规则"参照组内最高原严重度"(组内含 F-CON-02/03 MEDIUM)取 MEDIUM——两套定级各有锚点依据,非同类问题不同级 |
| 潜伏失配类 | F-CON-02/F-CON-03(MEDIUM)× F-CODE-02/F-CODE-06(MEDIUM) | 同级一致,四条均命中 MEDIUM 锚"潜伏失配(当前参数/格式下不触发,变更/中断即爆)"(CHARTER.md:114) |
| 文档声明失实类 | F-DOC-01/02/04/05(LOW)× F-TOOL-07(LOW)对照 F-DOC-03(MEDIUM) | 级差有锚点依据非不一致:F-DOC-03 逐字命中 MEDIUM 锚"可诱发高危误操作的误导性文档(runbook 步骤与实态不符)"(CHARTER.md:114,照发布流程执行即误发 development 构建);其余五条为排查/导航误导,命中 LOW 锚"文档死链/路径失效"与技术债系(CHARTER.md:115) |
| 存在级观察 | F-CON-05(INFO)× F-DOC-07/F-DOC-08(INFO) | 同级一致,均命中 INFO 锚"存在级观察"(CHARTER.md:116,F-DOC-07/08 为锚点逐字点名项) |

**扫描完成,无跨维度不一致——严重度拟调整 0 条(零拟调整为合法结果,per 05-01-PLAN Task 1)。**

### 工作量对齐扫描记录(D-04 同法)

- S 档 32 条逐条核对:均为单文件/单配置粒度,一致命中分档表 S 行(CHARTER.md:128);无同类问题跨维度异档。
- M 档 7 条(F-CODE-02、F-CODE-06、F-DOC-08、F-TEST-02、F-TEST-05、F-TEST-06、F-TEST-08):均为同组件多文件或多落点分摊,一致命中 M 行(CHARTER.md:129)。
- L 档唯一条 F-CON-04:闭环方案跨 FC + 小程序,命中 L 行"跨组件"(CHARTER.md:130);台账已自带保守告警方案 M 的双口径注记,报告排序按台账字面 L 处理——不构成不一致,不调整。

**扫描完成,无跨维度不一致——工作量拟调整 0 条。**

### CAL 调整条目

本节承载全部 `### CAL-NN` 调整条目(五字段:调整类型、原值→终值、理由、锚点依据、批准记录)。本批扫描结果为**零拟调整、零并入**(见上文与下节),故本节无条目。**批准记录(适用于本节整体):** 经 D-02 批量呈报(第 1 批,与 D-12 合并交互),用户于 2026-07-05 批复 `approve-all`(整批通过,无逐条批注意见)——"零拟调整、零并入"的扫描结论与全部原级维持一并获批;40 条发现原级即终级,报告组装无"经校准"标注需求。

---

## 真重复并入判定(D-08)

> 判定标准(D-08):两条 ID 实质描述同一缺陷**且**修复建议字段为同一修复动作,方构成真重复;成立时选证据更完整者为主条,副条标"并入 F-XX-NN 处理"。注意 RESEARCH Pitfall 6:F-TEST-05/06/07 是"缺测试锁定"元发现,与其成员条目修复动作不同(补测试 vs 修代码),不是真重复,归聚类层互指。

| # | 候选群(RESEARCH 列出的重叠起点) | 缺陷本体对照 | 修复动作对照 | 判定 |
|---|----------------------------------|--------------|--------------|------|
| 1 | F-CODE-07 × F-TEST-05 × F-TOOL-08(重试常量四落点) | 常量重复落点 vs 缺测试锁定 vs 联调镜像集群 | 提取共享源/派生化 vs 补双侧字面断言 vs 增契约镜像一致性测试 | 非真重复(元发现互指 + 对象不同)→ 聚类 CL-02 互指 |
| 2 | F-CON-03 × F-CODE-08(D14-6 重复实现债务族) | key 反推第四处零校验 vs FC 请求组装两份同构 | 补形状校验/消除反推 vs 提取共享请求 util | 非真重复(不同对象不同动作)→ 聚类 CL-01/CL-02 各自归属 |
| 3 | F-CON-05/F-CON-06 × F-TOOL-08(镜像常量注释同步) | 错误码/上限在小程序缺席 vs 联调工具侧第二三份字面定义 | 引入按码分支/预检常量 vs 镜像一致性测试绑定 | 非真重复(消费端缺席与工具镜像是两类缺陷)→ 聚类 CL-02 互指 |
| 4 | F-CODE-02 × F-CON-04(保守方案)(静默失败面) | 无界重下无告警 vs verify 弱语义假阳性 | 失败计数+skiplist+告警(F-CON-04 保守方案与之"同一动作面,可合并实施",见 findings/code.md F-CODE-02 修复建议) | 非真重复(缺陷本体不同,仅修复动作面重叠)→ 工作包 WP-03 合并实施 |
| 5 | F-TEST-06 × F-CODE-02/03/06、F-TOOL-01/02/03(静默失败面) | 元发现(缺测试兜底) vs 六成员各自缺陷 | 补测试 vs 修代码 | 非真重复(Pitfall 6 逐字命中)→ 聚类 CL-03 互指 |
| 6 | F-DOC-04 × F-DOC-05(同文件 AGENTS.md) | 配置回退声明失实 vs 现状叙述滞后 | 修订不同章节不同声明 | 非真重复(同文件不同缺陷)→ 工作包 WP-07 合并实施 |

**判定完成:真重复并入 0 条,无副条。40 条发现 ID 全保留(D-05),重叠关系全部以聚类互指与工作包合并承载。**

---

## 根因聚类划分

> 聚类为分析层(D-06):按同一成因分组,回答"为什么会有这类问题",喂 RPT-01 摘要叙事;成员引用不合并不退役(D-05)。共 5 簇(预期 4~7 之内);无共同根因的孤条不强行入簇。标注"(元发现)"者为缺测试锁定类互指成员(Pitfall 6)。

### CL-01: fragment_id/object key 派生与校验逻辑多处独立实现,校验强度不一致

- **根因陈述:** 同一 key 契约在 FC/Worker/小程序三端(加小程序内第四处反推)各自实现,无共享源;各落点校验强度自行取舍,生产端宽、消费端严的 Postel 失配由此系统性产生。
- **成员:** F-CON-01、F-CON-02、F-CON-03
- **证据锚:** F-CON-03 关联发现字段自记"D14-6(第四处重复实现债务)"(findings/contract.md:83);F-CON-02 与 F-CON-03 关联字段互指(findings/contract.md:58,83);TEST-AUDIT.md 反向映射 F-CON-01/02/03 三行缺口判定共同归入 F-TEST-05(TEST-AUDIT.md:119-121)。

### CL-02: 跨端/跨份契约镜像常量靠注释约定同步,共享源与对称测试锁定双缺失

- **根因陈述:** 跨部署单元(Python/JS、worker/fc_shared)常量无法运行时共享属结构约束,但同包内重复(uploader/verify、utils/pages)与测试层可绑定而未绑定(pytest pythonpath 已具备条件)使镜像同步完全依赖注释与人工。
- **成员:** F-CON-05、F-CON-06、F-CODE-07、F-CODE-08、F-TOOL-08、F-TEST-05(元发现)
- **证据锚:** TEST-AUDIT.md 反向映射缺口归属等式"F-TEST-05(7:F-CON-01/02/03/06 + F-CODE-07/08 + F-TOOL-08)"(TEST-AUDIT.md:169,成员横跨 CL-01/CL-02);F-CODE-07 证据字段三要素裁定(findings/code.md:110);F-TOOL-08 证据字段三要素裁定"测试层完全可绑定两侧常量"(findings/toolchain.md:120);D14-2/3/4 销号记法(findings/code.md:113,127;findings/toolchain.md:123)。

### CL-03: 失败/异常路径静默化——失败被吞、无计数、无告警、无恢复入口

- **根因陈述:** 错误路径普遍按"记录即处理"实现(删 .part 重来、留档、except-pass、detail 注记),缺失败升级面设计(计数/阈值/隔离/显式报告),使持久性失败以静默循环或死态存在。
- **成员:** F-CODE-02、F-CODE-03、F-CODE-06、F-TOOL-01、F-TOOL-02、F-TOOL-03、F-TEST-06(元发现)
- **证据锚:** TEST-AUDIT.md 缺口归属等式"F-TEST-06(6:F-CODE-02/03/06 + F-TOOL-01/02/03)"(TEST-AUDIT.md:169);F-TOOL-03 关联字段"F-CODE-02(残留对象落入其无界重试面)"(findings/toolchain.md:57);F-CODE-02 证据字段"_archive_failed docstring 与实态相悖"(findings/code.md:44)。

### CL-04: 质量门禁声明面与实态失真——范围缺口、恒红、静默 skip、活体依赖手工

- **根因陈述:** 门禁配置演进滞后于仓库结构(scripts/ 始终门禁外、app.py 部署态导入未豁免、JS 桥 skipif、无 CI),而声明层(AGENTS.md/Makefile help/TESTING.md)持续按"完整质量闸"口径表述,二值信号与声称能力双双失真。
- **成员:** F-TOOL-04、F-TOOL-05、F-TOOL-06、F-TOOL-07、F-TEST-01、F-TEST-03、F-TEST-04
- **证据锚:** TEST-AUDIT.md 门禁完整性三方对照 6 项(判定分布"一致 2 + 缺口候选 4",TEST-AUDIT.md:163)与缺口候选去向反填(行 2/6 → F-TEST-04;行 3 → F-TEST-03;行 5 → F-TEST-01);F-TOOL-06 证据字段引 scans/gates-baseline.md #1 实测 exit=1(findings/toolchain.md:92);F-TOOL-05 复发风险面自记"scripts/ 无任何静态门禁可拦截(HYP-25)"(findings/toolchain.md:78)。

### CL-05: 文档叙述滞后于实施进度与文件迁移,未随代码演进同步修订

- **根因陈述:** 权威文档迁移(docs/v1.0.0 prd/)与实现推进(全量实现、依赖变更、纯 JS 取舍、ENV 门控)之后,声明层(AGENTS.md/README/tech-spec/runbook)未同步修订,产生死链、失实声明与步骤缺失三类漂移。
- **成员:** F-DOC-01、F-DOC-02、F-DOC-03、F-DOC-04、F-DOC-05、F-DOC-06
- **证据锚:** DOC-CLAIMS.md 198 条声明四态销号(agree 146/drift 9/dead-ref 24/无法静态核实 19,findings/docs-config.md:63 批次导语);F-DOC-06 死链 census "10 文件 ≈47 处"(findings/docs-config.md:93-94);F-DOC-03 证据字段"架构评审已点名该风险但建议未落入任何 runbook"(findings/docs-config.md:56)。

### 未入簇孤条(无共同根因,不强行入簇)

F-CON-04(文档化设计取舍)、F-CODE-01(遗留 API 面)、F-CODE-04(搜索边界)、F-CODE-05(频控缺席)、F-DOC-07/F-DOC-08(存在级观察)、F-TEST-02(选择性驱动)、F-TEST-07(义务清单)、F-TEST-08(fake 对齐)、F-TEST-09(秘密负断言)、F-TEST-10(测试卫生),共 11 条。

**聚类成员对账等式:** 入簇 29(CL-01 ×3 + CL-02 ×6 + CL-03 ×7 + CL-04 ×7 + CL-05 ×6)+ 孤条 11 = 40 ✓

---

## 修复工作包划分

> 工作包为执行层(D-06):按共同修复位置分组、标依赖,可直接排期;包级工作量档为整体重估(D-04,包内共修一处时总量可小于各条之和)。INFO 条目(F-CON-05、F-DOC-07、F-DOC-08)不进工作包(D-07);本批无并入副条(D-08 判定 0 条)。包级重估并入 D-02 同批呈报。

### WP-01: 小程序 utils key/校验/预检族修复

- **成员:** F-CON-01、F-CON-02、F-CON-03、F-CON-06
- **共同修复位置:** `apps/miniprogram/utils/`(audio.js、upload_queue.js、config.js、uploader.js/verify.js 预检)+ 同一 node 测试文件族
- **包级工作量档:** M — 重估理由:四条各自 S(单文件),但共处同一组件同一测试族,合并实施为"同组件多文件"一档(CHARTER.md:129),总量小于 4×S 独立排期。
- **依赖:** 无(建议先于 WP-02 收口,见 WP-02 依赖)。

### WP-02: 契约镜像共享源提取与一致性测试绑定

- **成员:** F-CODE-07、F-CODE-08、F-TOOL-08、F-TEST-05
- **共同修复位置:** `apps/miniprogram/utils/`(共享常量模块、共享 fc_request util)+ `apps/worker/src/soniscope_worker/nls.py` 派生化 + 新增单个契约镜像一致性测试文件(pythonpath 双侧导入,F-TOOL-08 修复建议)
- **包级工作量档:** M — 重估理由:单一镜像一致性测试文件即可绑定全集群(F-TOOL-08 修复建议),共享源提取各为单文件小改;F-TEST-05 台账 M 主体即由本包一次性交付,合并后总量 < 各条之和。
- **依赖:** F-TEST-05 的 CON 侧四落点断言(F-CON-01/02/03/06)随 WP-01 成员修复同步落地,本包收口对账依赖 WP-01 完成。

### WP-03: Worker 失败路径升级面与运行时健壮性

- **成员:** F-CODE-01、F-CODE-02、F-CODE-03、F-CODE-04、F-CON-04、F-TEST-06
- **共同修复位置:** `apps/worker/src/soniscope_worker/`(poller.py、pipeline.py、audio.py、recovery.py、paths.py)+ 对应 pytest
- **包级工作量档:** M — 重估理由:主体为 F-CODE-02(M);F-CON-04 按其台账修复建议的保守告警方案口径与 F-CODE-02"同一动作面,可合并实施"(findings/code.md:45),包内计 M 而非台账字面 L(若修复里程碑改选闭环方案,F-CON-04 移出本包独立跨组件 L 排期);F-CODE-01/03/04 为同组件单文件 S 顺带;F-TEST-06 测试面随各成员修复分摊。
- **依赖:** 无实现顺序依赖;F-TEST-06 六脆弱区断言分摊 WP-03/WP-04/WP-06 三包,收口对账须三包全部完成后执行(挂本包)。

### WP-04: 小程序 uploading 死态恢复

- **成员:** F-CODE-06
- **共同修复位置:** `apps/miniprogram/utils/queue_runtime.js`、`pages/uploads/uploads.js`、`utils/uploads_view.js` + node 测试(含 uploads_view.test.js:70 既有断言同步翻转,F-TEST-06 交叉点)
- **包级工作量档:** M — 台账原档照抄(单包单条不重估)。
- **依赖:** 无。

### WP-05: 静态门禁与质量闸修复

- **成员:** F-TOOL-04、F-TOOL-05、F-TOOL-06、F-TOOL-07、F-TEST-03、F-TEST-04
- **共同修复位置:** `pyproject.toml`、`Makefile`、`scripts/test_asr.py`(URL 常量移除 + 违例清理)、`apps/worker/tests/test_miniprogram_js.py`(node 缺失 fail)、`apps/worker/src/soniscope_worker/miniprogram_lint.py`(语义/秘密模式扩展)
- **包级工作量档:** M — 重估理由:六条各自 S(配置级/单文件),但分属门禁配置面的多个文件,合并为一档 M;F-TEST-03/04 与 F-TOOL-05/06 分别为同一缺陷的门禁面与工具面表达,共修一处(scripts 纳入门禁、typecheck 恢复可绿)同时销两条,总量 < 各条之和。
- **依赖:** 无跨包依赖(F-TEST-04 之②依赖同包 F-TOOL-06,包内自洽)。

### WP-06: 联调/部署工具失准修复

- **成员:** F-TOOL-01、F-TOOL-02、F-TOOL-03
- **共同修复位置:** `apps/worker/src/soniscope_worker/`(verify_prep.py 三分渲染、fc_deploy.py 备份阻断、verify_upload_live.py 残留报告)+ 对应 pytest(FakeProbes/FakeFcApi 既有注入面)
- **包级工作量档:** M — 重估理由:三条各自 S 单文件,同组件多文件合并为 M(CHARTER.md:129)。
- **依赖:** 无;F-TEST-06 中 F-TOOL-01/02/03 三行断言随本包落地(收口对账挂 WP-03)。

### WP-07: 文档修订包(声明失实/死链/发布清单)

- **成员:** F-DOC-01、F-DOC-02、F-DOC-03、F-DOC-04、F-DOC-05、F-DOC-06
- **共同修复位置:** `docs/v1.0.0 prd/tech-spec.md`(两处措辞 + 依赖表行)、`AGENTS.md`(配置顺序 + 现状叙述 + 17 处死链)、`apps/fc/README.md`、`apps/miniprogram/README.md`、`docs/runbook/deployment-guide.md`(ENV 翻转清单项)等 ≈10 文件死链批量替换
- **包级工作量档:** M — 重估理由:全部为措辞/清单/机械替换 S 粒度,但横跨 ≈10 个文档文件(死链 ≈47 处),合并为一档 M;F-DOC-06 批量替换与 F-DOC-04/05 的 AGENTS.md 修订共修同文件,总量 < 各条之和。
- **依赖:** 无;F-DOC-03 的 ENV 翻转清单项建议在首次对外发布前完成(见逐条判定表 PRE-LAUNCH)。

### WP-08: 测试强化包(活体清单化/驱动补齐/fake 对齐/负断言/卫生)

- **成员:** F-TEST-01、F-TEST-02、F-TEST-07、F-TEST-08、F-TEST-09、F-TEST-10
- **共同修复位置:** 发布清单(runbook 勾选项,与 WP-07 同文件面可协同)、`apps/miniprogram/test/`(index.js 未驱动 handler 增补、oss_sign 负断言)、`apps/worker/tests/`(契约测试骨架、卫生整改)
- **包级工作量档:** M — 重估理由:主体 F-TEST-02/F-TEST-08 各 M,其余 S;F-TEST-07 为义务清单不新增独立工作量(随 WP-01/03/05/09 各成员修复分摊,本包收口对账)。
- **依赖:** F-TEST-07 收口对账依赖 WP-01/WP-03/WP-05/WP-09 完成;F-TEST-01 发布清单化建议先于首次对外发布执行。

### WP-09: FC 运维配额配置(平台层零代码)

- **成员:** F-CODE-05
- **共同修复位置:** FC 控制台(两函数实例并发/弹性上限 + 费用告警;应用层配额为可选后续)
- **包级工作量档:** S — 台账原档照抄(平台配置层零代码即可闭环)。
- **依赖:** 无。

**工作包成员并集对账等式:** 37 = WP-01(4)+ WP-02(4)+ WP-03(6)+ WP-04(1)+ WP-05(6)+ WP-06(3)+ WP-07(6)+ WP-08(6)+ WP-09(1)= 40 − 3(INFO:F-CON-05/F-DOC-07/F-DOC-08)− 0(并入副条)✓;成员无跨包重复。

---

## 上线判定准则

> 准则定稿依据 D-09(准则先行、逐条套用、判定与严重度独立评——严重度≠紧迫度)与 D-10(上线语境 = 邀请制小范围真实用户、allowlist 扩容;非作者用户无法自救——不会重录、不看日志;用户可感知的卡死态与无提示失败权重上调;开放注册级滥用/频控风险不按公开口径拔高)。条款编号供逐条判定表引用;经用户批准(D-12)后生效。

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

---

## 逐条上线判定表

> 40 行全量;判定列取值 ∈ {BLOCKER, PRE-LAUNCH, POST-LAUNCH},条款列 ∈ {B-1,B-2,B-3,P-1,P-2,P-3,PL-1};判定与严重度独立评。本表是 CALIBRATION.md 中唯一以 `| F-` 开行的表(供机械对账)。

| ID | 判定 | 准则条款 | 一句理由 |
|-----|------|----------|----------|
| F-CON-01 | POST-LAUNCH | PL-1 | 现实路径产不出非法日期,且 FC 400 显式拦截非静默——契约债非上线阻断 |
| F-CON-02 | POST-LAUNCH | PL-1 | 当前上传链不经过 preview key(AC#4),无现实触发路径,潜伏债留修复里程碑 |
| F-CON-03 | POST-LAUNCH | PL-1 | 当前队列内 key 全部来自 FC 签发合法域,无现实触发路径 |
| F-CON-04 | POST-LAUNCH | PL-1 | 假阳性需绕过 OSS 传输层完整性保障(极低概率),且系文档化设计取舍,Worker sha256 兜底存在 |
| F-CON-05 | POST-LAUNCH | PL-1 | 良性 INFO(通用透传即 Postel 宽收姿态),acknowledge 无需动作 |
| F-CON-06 | POST-LAUNCH | PL-1 | 600s 分片阈值下现实难触发,且超限为显式 4xx 失败非静默 |
| F-CODE-01 | POST-LAUNCH | PL-1 | 遗留 API 面纯代码债,现有调用方行为正确 |
| F-CODE-02 | PRE-LAUNCH | P-2 | 损坏/异常格式上传后转写永不产出且无告警,用户与运维均不可发现,排障需读 Worker 日志——静默失败面,首批真实用户前须有升级告警 |
| F-CODE-03 | POST-LAUNCH | PL-1 | 毫秒级崩溃窗口 + 仅目录污染不影响正确性 |
| F-CODE-04 | POST-LAUNCH | PL-1 | 仅脱离 Makefile 从任意 CWD 直跑才触发,运维者即作者可自救 |
| F-CODE-05 | POST-LAUNCH | PL-1 | 开放注册级滥用/频控风险,D-10 明示不按公开口径拔高 |
| F-CODE-06 | PRE-LAUNCH | P-1 | 录完即杀小程序属现实操作,uploading 死态用户可感知却无任何出口,唯一出路删记录即丢录音——非作者用户无法自救(D-10 点名权重上调场景) |
| F-CODE-07 | POST-LAUNCH | PL-1 | 纯维护成本类代码债,基线四落点数值一致,漂移仅节奏失准 |
| F-CODE-08 | POST-LAUNCH | PL-1 | 纯维护成本,漏改侧收 FC 400 显式失败非静默 |
| F-TOOL-01 | POST-LAUNCH | PL-1 | 工具失准仅误导运维排查方向,运维者即作者,无生产数据面 |
| F-TOOL-02 | POST-LAUNCH | PL-1 | 部署工具回滚点缺失属运维债,git 重部署可兜底 |
| F-TOOL-03 | POST-LAUNCH | PL-1 | 联调工具残留属工具债,触发需清理恰好失败 |
| F-TOOL-04 | POST-LAUNCH | PL-1 | 静态门禁缺口属代码债,基线经 ESLint 量化为零真实缺陷 |
| F-TOOL-05 | POST-LAUNCH | PL-1 | URL 已过期且系 STS 临时凭证单对象 GET,无现行泄漏面(不触 B-2);惯性风险由门禁修复(WP-05)承接 |
| F-TOOL-06 | POST-LAUNCH | PL-1 | 门禁恒红不影响线上用户,属修复里程碑首要工具债 |
| F-TOOL-07 | POST-LAUNCH | PL-1 | 幻影目标硬错误可见且能力无缺失(make lint 已含该检查) |
| F-TOOL-08 | POST-LAUNCH | PL-1 | 缺测试锁定类,基线镜像值逐处一致,仅契约变更时触发 |
| F-DOC-01 | POST-LAUNCH | PL-1 | 文档漂移仅误导性能排查,不改变运行时行为 |
| F-DOC-02 | POST-LAUNCH | PL-1 | 依赖清单失实仅在环境重建/审计时误导,不影响线上 |
| F-DOC-03 | PRE-LAUNCH | P-1 | 照发布文档执行即把 development 门控带上线:体验用户可见开发者菜单并可开启故障注入使上传链路失败——用户可感知失败且无法自救;发布必经流程且翻转全凭记忆,首批用户前必须补清单项 |
| F-DOC-04 | POST-LAUNCH | PL-1 | 声明失实但报错文案本身给出正确指引,误导窗口有限 |
| F-DOC-05 | POST-LAUNCH | PL-1 | 叙述滞后仅影响 onboarding 判断,不影响运行时 |
| F-DOC-06 | POST-LAUNCH | PL-1 | 死链靠全仓搜索可自救,属文档债非上线阻断 |
| F-DOC-07 | POST-LAUNCH | PL-1 | 存在级观察(INFO),acknowledge 无需动作 |
| F-DOC-08 | POST-LAUNCH | PL-1 | 存在级观察(INFO),acknowledge 无需动作 |
| F-TEST-01 | POST-LAUNCH | PL-1 | 缺测试锁定类(PL-1 明列);短期发布清单化随 WP-08 执行,不构成上线阻断 |
| F-TEST-02 | POST-LAUNCH | PL-1 | 缺测试锁定类,回归风险面在未来改动而非上线时点 |
| F-TEST-03 | POST-LAUNCH | PL-1 | 缺门禁/测试锁定类(PL-1 明列),实害样本(过期 URL)已由 F-TOOL-05 单列判定 |
| F-TEST-04 | POST-LAUNCH | PL-1 | 门禁信号失真不影响线上用户,属修复里程碑工具债 |
| F-TEST-05 | POST-LAUNCH | PL-1 | 缺测试锁定类(PL-1 明列),风险在未来镜像漂移而非上线时点 |
| F-TEST-06 | POST-LAUNCH | PL-1 | 缺测试锁定类,系修复各原发现时的同步测试义务 |
| F-TEST-07 | POST-LAUNCH | PL-1 | 义务清单类,无独立被测对象,随修复分摊 |
| F-TEST-08 | POST-LAUNCH | PL-1 | 缺测试锁定类,当前基线无漂移证据 |
| F-TEST-09 | POST-LAUNCH | PL-1 | 缺测试锁定类,当前实现正确(秘密仅参与派生) |
| F-TEST-10 | POST-LAUNCH | PL-1 | 测试卫生杂项,纯维护成本类 |

**判定分布(终态,经 D-12 批准):** BLOCKER 0 / PRE-LAUNCH 3(F-CODE-02、F-CODE-06、F-DOC-03)/ POST-LAUNCH 37;0 + 3 + 37 = 40 ✓

**总判定推导(D-11,终态):** 无 BLOCKER、有 PRE-LAUNCH → **CONDITIONAL GO**(必做清单 = F-CODE-02、F-CODE-06、F-DOC-03;分别由 WP-03、WP-04、WP-07 承载)。

**与严重度直觉相厄条目(MEDIUM 却 POST-LAUNCH,D-12 抽样呈报对象):** F-CON-02、F-CON-03、F-TOOL-05、F-TOOL-06、F-TEST-03、F-TEST-04、F-TEST-05、F-TEST-06,共 8 条(理由见各行)。

---

## 呈报与批准记录

状态: 已批准落账

- **呈报批次:** 第 1 批(D-02 校准批量呈报 + D-12 判定准则批准与抽样呈报,合并为一次交互,per RESEARCH Pattern 2)
- **呈报日期:** 2026-07-05
- **呈报内容:** ①拟调整清单(本批 0 条,零拟调整记录见跨维度对齐扫描节)②真重复并入判定(本批 0 条)③上线判定准则全文(B-1~B-3/P-1~P-3/PL-1 + D-11 推导规则)④判定抽样(全部 PRE-LAUNCH 3 条 + 相厄条目 8 条;BLOCKER 0 条)⑤确认项:CHARTER schema 字段 8/9 台账回填预期由本文件承载、findings/*.md 不回写(RESEARCH 假设 A3)
- **批复记录:** 用户于 2026-07-05 批复,批复方式 = 整批通过;批复原文:"approve-all(整批通过 ①~⑤,无逐条批注意见)"。①~⑤ 全部生效:零拟调整/零并入落账;**判定准则 B-1~PL-1 与 D-11 推导规则经用户批准定稿(D-12 批准结论)**;40 条逐条判定与 CONDITIONAL GO 总判定推导获批为终态;A3 确认项通过——CHARTER schema 字段 8/9 由本文件承载,findings/*.md 保持封版不回写。

### 尾部对账等式(终稿实跑照录,2026-07-05)

```
$ grep -c '^### CAL-' .planning/audit/CALIBRATION.md
0
```
CAL 调整条目数 = **0**(零拟调整、零并入,经批复确认的合法结果;grep 计数 0 时退出码 1 属预期)✓

```
$ grep -c '^### CL-' .planning/audit/CALIBRATION.md
5
```
CL 簇数 = **5**(4~7 之内)✓

```
$ grep -c '^### WP-' .planning/audit/CALIBRATION.md
9
```
WP 包数 = **9** ✓

```
$ grep -c '^| F-' .planning/audit/CALIBRATION.md
40
```
判定表行数 = **40**(全文件唯一 `| F-` 开行表)✓

```
$ grep '^| F-' .planning/audit/CALIBRATION.md | grep -cE 'BLOCKER|PRE-LAUNCH|POST-LAUNCH'
40
```
三态判定计数和 = 0(BLOCKER)+ 3(PRE-LAUNCH)+ 37(POST-LAUNCH)= **40** ✓

工作包成员并集 = 37 = WP-01(4)+ WP-02(4)+ WP-03(6)+ WP-04(1)+ WP-05(6)+ WP-06(3)+ WP-07(6)+ WP-08(6)+ WP-09(1)= 40 − 3 INFO − 0 副条 ✓

```
$ git status --porcelain .planning/audit/findings/
(空输出)
```
findings 封版零改动(D-03)✓

```
$ git diff --stat 5927f36 -- apps/ scripts/ docs/ | wc -l
0
```
零 diff(CHARTER 写定命令,apps/scripts/docs 相对基线零改动)✓

---
*校准台账: 2026-07-05(40 条真实发现原级即终级;CAL 0 / CL 5 / WP 9;判定 BLOCKER 0 / PRE-LAUNCH 3 / POST-LAUNCH 37 → CONDITIONAL GO;D-02/D-12 双批准 approve-all 落账,findings 封版零回写)*
