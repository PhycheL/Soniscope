---
phase: 02-contract-extraction-drift
plan: 04
subsystem: audit
tags: [contract-audit, four-category-triage, postel-analysis, findings-ledger, test-recipe, zero-diff]
requires:
  - 02-01(组① 静态判据——行 2/4/5/13 分歧格)
  - 02-02(组②/③ + 普查——行 35-41/46 分歧格与移交线索)
  - 02-03(往返校验对照点 a-d——归类的行为级佐证;S-01~S-18 黄金样本集)
provides:
  - CONTRACT-MATRIX.md 判定列全回填(12 diverge/absent 格四类标签 + F-CON 链接;agree 格 —;负面清单排除注)
  - findings/contract.md F-CON-01~06(九字段齐全,Postel 三要素住证据字段,全部挂 HYP-13)
  - CONTRACT-TEST-RECIPE.md(D-15 触发,D-16 五要素设计配方)
  - CONTRACT-MATRIX.md 收尾章节(零 diff 记录 + 机械对账 7 等式 + 成功判据自查)
affects:
  - Phase 3(D14-1~6 债务移交;F-CON-03/05 关联字段注明)
  - Phase 4(CLAUDE.md 错误码分支声明失实 DOC 移交)
  - Phase 5(F-CON 台账喂汇总校准;上线判定槽留空)
tech-stack:
  added: []
  patterns:
    - 四类判定标签 + F-CON 链接住矩阵、Postel 分析住台账(D-12 证据与判断分离)
    - 单条 F-CON 覆盖多格(F-CON-05 覆盖行 35-41 同根因 7 格),对账等式显式给出覆盖映射
    - 机械对账命令自指免疫(行首锚定 grep 模式排除收尾章节命令原文的自计数)
key-files:
  created:
    - .planning/audit/CONTRACT-TEST-RECIPE.md
  modified:
    - .planning/audit/CONTRACT-MATRIX.md
    - .planning/audit/findings/contract.md
    - .planning/REQUIREMENTS.md
decisions:
  - "行 35-41(7 错误码小程序 absent)裁良性单条 F-CON-05:通用透传使每码行为等同,错误码对客户端是可用信息而非分支义务——absent 格不机械判覆盖洞,依矩阵既留裁决权"
  - "行 4/5 裁潜伏而非活跃:AC#4 约束下上传 key 用 FC 返回值,错位 key 不进 OSS——当前输入域无行为分叉,preview 复用即爆"
  - "行 18/22/24 的 agree 格既留裁决以判定列括注收口(size=0 Postel 并入 F-CON-06 证据;expiration/endpoint 未消费裁单侧消费选择不立 F-CON),不破坏 diverge/absent = F-CON 对账等式"
  - "配方采用现状行为锁定原则:对 F-CON-01/02/03 分歧断言基线现状,修复以翻转断言显式过测试"
metrics:
  duration: ~25min
  completed: 2026-07-05
status: complete
---

# Phase 2 Plan 04: 四类判定、F-CON 台账与阶段封版 Summary

Phase 2 判定与收尾完成:12 个 diverge/absent 格全部归类(潜伏 2 / 覆盖洞 3 / 良性 1,活跃失配 0)并以 6 条九字段 F-CON 落台账(Postel 宽严三要素住证据字段,全部挂 HYP-13);非良性分歧触发 CONTRACT-TEST-RECIPE.md 成文(D-16 五要素,黄金样本复用 S-01~S-18,make test 零改动接入);矩阵收尾章节零 diff 记录 + 7 条机械对账等式全平,Phase 2 产物封版。

## 完成任务

| Task | 名称 | Commit | 产出 |
|------|------|--------|------|
| 1 | 四类分歧判定回填矩阵 + F-CON 发现写入台账 | 46b4326 | 判定列 51 行全回填;F-CON-01~06 入 findings/contract.md |
| 2 | 条件产出黄金样本契约测试设计配方 | 9deca27 | CONTRACT-TEST-RECIPE.md 新建;触发线裁决入矩阵收尾章节 |
| 3 | 阶段收尾——零 diff 验证记录与机械对账封版 | b1733a4 | 收尾章节(零 diff 记录/7 等式/成功判据自查/文档尾封版) |

## 判定结果一览

| F-CON | 矩阵行 | 类别 | 严重度 | 一行摘要 |
|-------|--------|------|--------|----------|
| F-CON-01 | 组① 行 2 | 覆盖洞 | LOW | 小程序 fragment_id 缺日期合法性校验(FC 400 为唯一拦截点) |
| F-CON-02 | 组① 行 4 | 潜伏 | MEDIUM | buildObjectKeyPreview 双独立入参可产出目录≠前缀 key(preview 复用即触发 Worker 静默跳过) |
| F-CON-03 | 组① 行 5 | 潜伏 | MEDIUM | 第四处反推 fragmentIdFromObjectKey 零校验,与 Worker 严校验行为分叉 |
| F-CON-04 | 组① 行 13 | 覆盖洞 | LOW | verify-upload 不读 x-oss-meta-sha256,完整性闭环推迟到 Worker(§4.2 文档化取舍) |
| F-CON-05 | 组② 行 35-41(7 格) | 良性 | INFO | 7 错误码字面量小程序零实现,statusCode 段分支 + error 通用透传,行为无分叉 |
| F-CON-06 | 组③ 行 46 | 覆盖洞 | LOW | 50MB 上限无小程序镜像/预检(size=0 边界 Postel 注记并入本条) |

负面清单执行:行 14(chunk_total 文档化约定)、行 20/21(DNF-04 STS 秘密下发 by-design)判定列附排除注,未立 F-CON;DNF-01~03 无矩阵对照点。判定过程无安全类顺带发现。

## 验证结果

- 矩阵表格行内待判定残留 0;12 个 diverge/absent 格 F-CON 链接 12 处(5×1 + 1×7)✓
- F-CON 九字段齐全、顺序符合 CHARTER;严重度行含 `影响:`/`可能性:`,无数值评分;F-CON-00 示例未动 ✓
- 每条 F-CON 证据字段含矩阵行反向引用 + Postel 三要素(谁严谁宽/失配方向/触发条件)✓
- 配方含 D-16 五要素各自成节,样本引用 S-NN,pytest 骨架含 node 缺席 skip + 显式文件清单先例要点 ✓
- `git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出空;`git status --porcelain` 仅 `.planning/` ✓
- 收尾章节 7 条对账等式全平;文档尾斜体摘要含矩阵行数/F-CON 条数/样本数/配方产出 ✓

## Deviations from Plan

### 1. [如实记录] 机械对账命令自指修正

- **Found during:** Task 3
- **Issue:** 收尾章节写入的对账命令原文本身包含被计数的模式字面量(`@ 5927f36`、`✅`、`待判定`),使首轮记录数字与复算结果偏差 1。
- **Fix:** 等式 2/4/5 改用行首锚定的自指免疫 grep 模式或显式注明自指计数(如 236 = 正文 235 + 命令原文 1),复算全部吻合后封版。
- **Commit:** b1733a4

其余按计划执行:行 35-41 归良性、行 4/5 归潜伏均在矩阵既留裁决权与四类定义授权范围内(见 frontmatter decisions),无功能性偏差。

## 秘密红线遵守

F-CON 证据摘录与配方样本全部为合成值或代码结构引用(合成 ULID/deviceShortId、DNF-04 条目仅引标识符名),无任何真实凭证/openid/疑似秘密值入文(T-02-01 缓解)。

## 移交下游

- **Phase 3:** D14-1~6 债务线索(F-CON-03 挂 D14-6、F-CON-05 挂 D14-3、F-CON-04 挂 HYP-03/D14-1)。
- **Phase 4:** CLAUDE.md"uploader.js branches on the same strings"声明失实(F-CON-05 修复建议注明,矩阵组② 行 35-41 行下注)。
- **Phase 5:** F-CON-01~06 上线判定槽留空待填;F-CON-00 示例届时剔除;四类分布(2 潜伏 + 3 覆盖洞 + 1 良性)可直接喂汇总。
- **修复里程碑:** CONTRACT-TEST-RECIPE.md 可直接开工(建议路径/骨架/接入点/验收标准全给定)。

## Self-Check: PASSED

- `.planning/audit/CONTRACT-TEST-RECIPE.md` — FOUND
- `.planning/audit/CONTRACT-MATRIX.md` 收尾章节非空 — FOUND
- `findings/contract.md` F-CON-01~06 — FOUND
- Commit 46b4326 — FOUND
- Commit 9deca27 — FOUND
- Commit b1733a4 — FOUND

---
*Phase 2 Plan 04 完成: 2026-07-05(3 任务 3 提交 + 元数据提交;12 格 → 6 F-CON;配方产出;机械对账 7 等式全平,Phase 2 封版)*
