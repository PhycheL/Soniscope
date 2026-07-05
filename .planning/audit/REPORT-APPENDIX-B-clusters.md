# 附录 B: CL-NN 根因聚类明细

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本文件是 `REPORT.md` 的附录 B(D-14 机械性长内容分文件),照搬 `CALIBRATION.md` §根因聚类划分节的逐簇明细,零改判。定位声明:**聚类为叠加层**(D-05)——成员 F-ID 全保留,不合并、不退役,聚类只作引用;**聚类是分析层**(D-06)——回答"为什么会有这类问题",与修复工作包 WP-NN(执行层,按共同修复位置分组)互指但不强制对齐,同簇成员可分属多包、同包成员可跨簇。每簇五要素:根因陈述 / 成员 F-ID 清单 / 关联工作包(WP-NN 互指,取自 REPORT.md 发现汇总表处置列)/ 证据锚(既有台账行引用)。标注"(元发现)"者为缺测试锁定类互指成员(Pitfall 6:元发现与其成员修复动作不同,非真重复)。

## 聚类明细(5 簇,照搬 CALIBRATION.md)

### CL-01: fragment_id/object key 派生与校验逻辑多处独立实现,校验强度不一致

- **根因陈述:** 同一 key 契约在 FC/Worker/小程序三端(加小程序内第四处反推)各自实现,无共享源;各落点校验强度自行取舍,生产端宽、消费端严的 Postel 失配由此系统性产生。
- **成员:** F-CON-01、F-CON-02、F-CON-03(共 3 条)
- **关联工作包:** WP-01(三成员全部进该包)
- **证据锚:** F-CON-03 关联发现字段自记"D14-6(第四处重复实现债务)"(findings/contract.md:83);F-CON-02 与 F-CON-03 关联字段互指(findings/contract.md:58,83);TEST-AUDIT.md 反向映射 F-CON-01/02/03 三行缺口判定共同归入 F-TEST-05(TEST-AUDIT.md:119-121)。

### CL-02: 跨端/跨份契约镜像常量靠注释约定同步,共享源与对称测试锁定双缺失

- **根因陈述:** 跨部署单元(Python/JS、worker/fc_shared)常量无法运行时共享属结构约束,但同包内重复(uploader/verify、utils/pages)与测试层可绑定而未绑定(pytest pythonpath 已具备条件)使镜像同步完全依赖注释与人工。
- **成员:** F-CON-05、F-CON-06、F-CODE-07、F-CODE-08、F-TOOL-08、F-TEST-05(元发现)(共 6 条)
- **关联工作包:** WP-02(F-CODE-07/08、F-TOOL-08、F-TEST-05)、WP-01(F-CON-06);F-CON-05 系 INFO acknowledge 不进包(D-07)
- **证据锚:** TEST-AUDIT.md 反向映射缺口归属等式"F-TEST-05(7:F-CON-01/02/03/06 + F-CODE-07/08 + F-TOOL-08)"(TEST-AUDIT.md:169,成员横跨 CL-01/CL-02);F-CODE-07 证据字段三要素裁定(findings/code.md:110);F-TOOL-08 证据字段三要素裁定"测试层完全可绑定两侧常量"(findings/toolchain.md:120);D14-2/3/4 销号记法(findings/code.md:113,127;findings/toolchain.md:123)。

### CL-03: 失败/异常路径静默化——失败被吞、无计数、无告警、无恢复入口

- **根因陈述:** 错误路径普遍按"记录即处理"实现(删 .part 重来、留档、except-pass、detail 注记),缺失败升级面设计(计数/阈值/隔离/显式报告),使持久性失败以静默循环或死态存在。
- **成员:** F-CODE-02、F-CODE-03、F-CODE-06、F-TOOL-01、F-TOOL-02、F-TOOL-03、F-TEST-06(元发现)(共 7 条;含必做清单条目 F-CODE-02/F-CODE-06 两条 PRE-LAUNCH)
- **关联工作包:** WP-03(F-CODE-02/03、F-TEST-06)、WP-04(F-CODE-06)、WP-06(F-TOOL-01/02/03)
- **证据锚:** TEST-AUDIT.md 缺口归属等式"F-TEST-06(6:F-CODE-02/03/06 + F-TOOL-01/02/03)"(TEST-AUDIT.md:169);F-TOOL-03 关联字段"F-CODE-02(残留对象落入其无界重试面)"(findings/toolchain.md:57);F-CODE-02 证据字段"_archive_failed docstring 与实态相悖"(findings/code.md:44)。

### CL-04: 质量门禁声明面与实态失真——范围缺口、恒红、静默 skip、活体依赖手工

- **根因陈述:** 门禁配置演进滞后于仓库结构(scripts/ 始终门禁外、app.py 部署态导入未豁免、JS 桥 skipif、无 CI),而声明层(AGENTS.md/Makefile help/TESTING.md)持续按"完整质量闸"口径表述,二值信号与声称能力双双失真。
- **成员:** F-TOOL-04、F-TOOL-05、F-TOOL-06、F-TOOL-07、F-TEST-01、F-TEST-03、F-TEST-04(共 7 条)
- **关联工作包:** WP-05(F-TOOL-04/05/06/07、F-TEST-03/04)、WP-08(F-TEST-01)
- **证据锚:** TEST-AUDIT.md 门禁完整性三方对照 6 项(判定分布"一致 2 + 缺口候选 4",TEST-AUDIT.md:163)与缺口候选去向反填(行 2/6 → F-TEST-04;行 3 → F-TEST-03;行 5 → F-TEST-01);F-TOOL-06 证据字段引 scans/gates-baseline.md #1 实测 exit=1(findings/toolchain.md:92);F-TOOL-05 复发风险面自记"scripts/ 无任何静态门禁可拦截(HYP-25)"(findings/toolchain.md:78)。

### CL-05: 文档叙述滞后于实施进度与文件迁移,未随代码演进同步修订

- **根因陈述:** 权威文档迁移(docs/v1.0.0 prd/)与实现推进(全量实现、依赖变更、纯 JS 取舍、ENV 门控)之后,声明层(AGENTS.md/README/tech-spec/runbook)未同步修订,产生死链、失实声明与步骤缺失三类漂移。
- **成员:** F-DOC-01、F-DOC-02、F-DOC-03、F-DOC-04、F-DOC-05、F-DOC-06(共 6 条;含必做清单条目 F-DOC-03 一条 PRE-LAUNCH)
- **关联工作包:** WP-07(六成员全部进该包)
- **证据锚:** DOC-CLAIMS.md 198 条声明四态销号(agree 146/drift 9/dead-ref 24/无法静态核实 19,findings/docs-config.md:63 批次导语);F-DOC-06 死链 census "10 文件 ≈47 处"(findings/docs-config.md:93-94);F-DOC-03 证据字段"架构评审已点名该风险但建议未落入任何 runbook"(findings/docs-config.md:56)。

## 未入簇孤条清单(无共同根因,不强行入簇——聚类层允许有未入簇发现)

F-CON-04(文档化设计取舍)、F-CODE-01(遗留 API 面)、F-CODE-04(搜索边界)、F-CODE-05(频控缺席)、F-DOC-07/F-DOC-08(存在级观察)、F-TEST-02(选择性驱动)、F-TEST-07(义务清单)、F-TEST-08(fake 对齐)、F-TEST-09(秘密负断言)、F-TEST-10(测试卫生),共 **11** 条(处置面:除 F-DOC-07/F-DOC-08 acknowledge 外,其余 9 条各随 WP-03/WP-08/WP-09 排期,见 REPORT.md 发现汇总表处置列)。

## 成员全覆盖对账等式(照录 CALIBRATION.md,仿 TEST-AUDIT 成员归属等式范式)

入簇 **29**(CL-01 ×3 + CL-02 ×6 + CL-03 ×7 + CL-04 ×7 + CL-05 ×6)+ 未入簇孤条 **11** = **40** ✓(与 findings 40 条真实发现底数、REPORT.md 发现汇总表 40 行一致;成员无跨簇重复)

```
$ grep -c '^### CL-' .planning/audit/REPORT-APPENDIX-B-clusters.md
5
$ grep -c '^### CL-' .planning/audit/CALIBRATION.md
5
```

附录簇数 = 校准台账簇数 = **5** ✓(逐簇成员清单照搬零改判)

---
*附录 B 聚类明细: 2026-07-05(5 簇照搬 CALIBRATION.md 零改判;入簇 29 + 孤条 11 = 40 ✓;每簇含 WP-NN 关联工作包互指;三条 PRE-LAUNCH 中 F-CODE-02/06 出自 CL-03、F-DOC-03 出自 CL-05)*
