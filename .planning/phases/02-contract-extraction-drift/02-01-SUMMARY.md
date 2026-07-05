---
phase: 02-contract-extraction-drift
plan: 01
subsystem: audit
tags: [contract-audit, drift-matrix, oss-data-plane, forensics]
requires: []
provides:
  - CONTRACT-MATRIX.md 骨架(8 章节)与判定标准/负面清单
  - 组① OSS 数据面 15 行三列证据(key 族 6 行 + 元数据 9 行)
affects:
  - 02-02(组②③/普查续写同文件)
  - 02-03(往返校验样本以行 2/4/5 边界为高价值输入)
  - 02-04(判定列回填与 F-CON 立项)
tech-stack:
  added: []
  patterns:
    - git show/git grep 基线取证(禁工作树取证,D-05)
    - 矩阵格 状态词 + path:line @ 5927f36 证据格式(D-11)
key-files:
  created:
    - .planning/audit/CONTRACT-MATRIX.md
  modified: []
decisions:
  - "FC 列 x-oss-meta 七字段:六字段判 n/a(零生产触点,职责结构不触及),sha256 判 absent 候选(verify-upload 职责语义应然参与但 head.py docstring 引 §4.2 注声明不校验)——覆盖洞归类留 02-04"
  - "行 14 chunk_total null→\"0\"→None 按 Pitfall 5 判 agree(两侧注释/docstring 声明同一 §3.2 约定,字面异/语义同)"
  - "行 4(key 目录日期来源)与行 5(key 反推)小程序格判 diverge:静态对照完整(独立入参本地时区推导 / 无校验字符串切割),非勘察疑点直落"
metrics:
  duration: 8min
  completed: 2026-07-05
status: complete
---

# Phase 2 Plan 01: 契约漂移矩阵骨架与组① OSS 数据面抽取 Summary

组① OSS 数据面 15 行逐字段静态抽取完成:FC/Worker 的 fragment_id 契约逐字符一致,小程序在日期合法性校验(absent)、key 目录日期来源(本地时区独立入参,diverge)、key 反推(无校验字符串切割,diverge)三处偏离;7 个 x-oss-meta-* 键名写读两端逐字符一致,FC 生产代码零 meta 触点。

## 完成任务

| Task | 名称 | Commit | 产出 |
|------|------|--------|------|
| 1 | 建矩阵骨架并抽取组① key 族六行 | fd3caef | 8 章节骨架 + 判定标准/负面清单 + 行 1-6 |
| 2 | 抽取组① 元数据九行 | a7a17c8 | 行 7-15 + FC 触点核实注记 |

## 关键静态事实(供 02-03/02-04 消费)

- **行 1(正则):** FC `sts.py:30-33` 与 Worker `oss_admin.py:24-27` 逐字符相同;小程序 `audio.js:95-96` 无命名捕获组但匹配语义等价——三处 agree。
- **行 2(日期合法性):** FC/Worker 正则命中后均做 `datetime()` 构造校验;小程序无任何日期合法性检查(如 `20260231` 可通过正则)——小程序 absent,02-03 往返样本高价值边界。
- **行 4(目录日期来源):** FC/Worker 从 fragment_id 前缀单一来源推导;小程序 `buildObjectKeyPreview(fragmentId, recordedAt)` 两个独立入参 + `objectKeyDate` 本地时区——diverge,跨午夜/跨时区可致目录日期与前缀不一致。
- **行 5(key 反推):** Worker `poller.py:47-61` 往返校验式;小程序 `upload_queue.js:38-44` 纯字符串切割无校验(普查发现的第四处实现);FC n/a(只正向签发)。
- **行 7-13(x-oss-meta 七字段):** 写端 `audio.js:162-168` 与读端 `poller.py:34-40` 键名逐字符一致;FC 生产代码零触点(`git grep 'x-oss-meta' 5927f36 -- apps/fc/` 仅命中测试文件脱敏断言)。
- **行 13(sha256)FC 列:** absent 候选——HeadObject 可携带该 meta 但 `ObjectHead` 只读四字段;`head.py:9-10` docstring 引 tech-spec §4.2 注声明设计上不校验 sha256。
- **行 14/15:** chunk_total 三段映射两侧文档化约定一致(agree);recorded-at 生产端本地时区偏移 ISO 8601,消费端不解析透传(静态无冲突,Postel 分析留 02-04)。

## 验证结果

- `grep -o '@ 5927f36' | wc -l` = **71**(≥ 30 达标;Task 1 后为 28 ≥ 12)
- `grep -c 'x-oss-meta-'` = **10**(≥ 7 达标)
- 8 个 `## ` 章节齐备;FC key 反推格 n/a 无行号仅结构性理由(D-03)
- 零 diff:`git diff --stat 5927f36 -- apps/ scripts/ docs/` 空输出(Task 1、Task 2 收尾各验一次)
- `git status --porcelain` 仅见 `.planning/` 路径
- 人工抽查 3 格(`sts.py:59` / `audio.js:164` / `poller.py:118`)`git show 5927f36:<path> | sed -n '<line>p'` 全部命中

## Deviations from Plan

### 勘察行号偏差修正(计划明文授权:"发现勘察行号有偏差以实际为准并如实记录")

RESEARCH 勘察起点行号与 `git show 5927f36` 复核实际行号的差异,全部以实际为准落格:

| 勘察起点 | 复核实际 | 要素 |
|----------|----------|------|
| `sts.py:28-32` | `sts.py:30-33` | FC `_FRAGMENT_ID_RE` |
| `audio.js:95-97` | `audio.js:95-96` | 小程序 `FRAGMENT_ID_RE` |
| `audio.js:103-105` | `audio.js:104-106` | `buildObjectKeyPreview`(:103 为注释行) |
| `poller.py:47-60` | `poller.py:47-61` | `fragment_id_from_key` |
| `poller.py:52` | `poller.py:53` | `.wav` endswith 检查 |
| `upload_queue.js:36-44` | `upload_queue.js:38-44` | `fragmentIdFromObjectKey`(:36-37 为注释) |
| `audio.js:157` | `audio.js:156` | chunk_total 映射约定注释(:157 为函数声明行) |
| `audio.js:158-170` | `audio.js:162-168` | 逐键写入行(157-170 为整函数) |
| `audio.js:75-86` | `audio.js:76-85` | `toIso`(:75 为注释) |
| `poller.py:33-40` | `poller.py:34-40` | META_* 七常量(:33 为 META_PREFIX) |
| `poller.py:132+` | `poller.py:131-146` | `metadata_to_draft` |

其余按计划执行,无功能性偏差。

## 秘密红线遵守

矩阵全部证据摘录为正则字面、模板字符串、键名常量与约定注释——无任何疑似秘密值本体入文。

## 移交下游

- **02-02:** 组②③/普查章节骨架已留位;负面清单与状态词表可直接沿用。
- **02-03:** 行 2(JS 无日期校验)、行 4(本地时区日期推导)、行 5(无校验反推)为往返校验样本的三个已确认高价值边界。
- **02-04:** 判定列 15 个 `待判定`;行 13 FC absent 候选的覆盖洞归类;行 4/5 diverge 的 Postel 宽严分析与 F-CON 立项。

## Self-Check: PASSED

- `.planning/audit/CONTRACT-MATRIX.md` — FOUND
- Commit fd3caef — FOUND
- Commit a7a17c8 — FOUND

---
*Phase 2 Plan 01 完成: 2026-07-05(2 任务 2 提交,组① 15 行落格,零 diff 通过)*
