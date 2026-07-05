---
phase: 02-contract-extraction-drift
plan: 03
subsystem: audit
tags: [contract-audit, round-trip-verification, execution-evidence, golden-samples, timezone]
requires:
  - 02-01(组① 行 1-6 静态结论——样本预期推导来源)
  - 02-02(AC#4 object_key 往返链、size=0 边界的静态铺垫)
provides:
  - CONTRACT-MATRIX.md『往返校验结论』章节(python/JS 双声部小结 + 对照点 a-d + 总结论 + 复跑说明)
  - CONTRACT-MATRIX.md『附录:往返校验样本清单』18 样本(S-01~S-18,D-07 全 11 类,预期/实测/销号三元组全闭合)
  - D-16 黄金样本集胚胎(样本清单可直接复用进 CONTRACT-TEST-RECIPE.md)
affects:
  - 02-04(四类判定:对照点 a-d 为行 2/4/5 归类的行为级佐证;CONTRACT-TEST-RECIPE.md 样本复用)
tech-stack:
  added: []
  patterns:
    - git archive 基线导出 + PYTHONPATH shadowing + __file__ 来源断言(D-06/Pitfall 1)
    - TZ 环境变量驱动 node 双时区复跑(Pitfall 2)
key-files:
  created: []
  modified:
    - .planning/audit/CONTRACT-MATRIX.md
decisions:
  - "chunk 后缀样本值以 chunking.js 实际产出定(Open Question 3 裁决):chunking.js:5 注释 + :27-31 addChunk 只写 chunk_seq——分片不改 fragment_id 形态,S-15 与典型值同形,分片信息仅入 meta"
  - "S-06 单 TZ 进程内前缀=目录日期自洽;错位风险在双入参跨时刻混用时显化——故 S-07 设计为 fragmentId@23:59:59 + recordedAt@次日 00:00:01 的纯函数级错位实证,产出的错位 key 与 S-18 等价,Worker 拒(None)"
  - "S-13 ULID 宽严:三处正则 [0-9A-Za-z]{26} 均宽于 Crockford 且行为一致(同收),ulid(seed) 实测产出纯 Crockford 集——宽严差异存在但三处同宽,非漂移,佐证组① 行 1 agree"
metrics:
  duration: 12min
  completed: 2026-07-05
status: complete
---

# Phase 2 Plan 03: 往返校验执行佐证(FC 签发 → Worker 解析)Summary

CONTRACT-02 往返校验执行完毕:18 合成样本(D-07 全 11 类)在基线导出树(git archive 5927f36)上以 .venv python + node v22.18.0 双 TZ 执行,全部销号且与静态判定零矛盾——FC 签发的 key 在"格式+日期合法"样本域内 100% 被 Worker 往返解析,分叉全部位于小程序声部(无日期校验放行、双入参可产出目录≠前缀 key 且该类 key 会被 Worker 静默跳过、第四处反推照单全收)。

## 完成任务

| Task | 名称 | Commit | 产出 |
|------|------|--------|------|
| 1 | 样本清单写定 + 基线导出 + python 侧往返校验 | 2844892 | 附录 18 样本表 + python 侧小结(15 样本销号) |
| 2 | node 侧双 TZ 执行佐证 + 往返校验结论成文 | 7d657a9 | JS 声部回填全表销号 + 对照点 a-d + 总结论 + 复跑说明 + 组① 行 2/4/5 佐证括注 |

## 关键执行事实(供 02-04 消费)

- **主链无漂移:** FC `sts.object_key_for` 与 Worker `oss_admin.object_key_for` 15 样本同收同拒、产出逐字符相等;FC 签发的每个 key 经 `poller.fragment_id_from_key` 往返等式全部成立(含闰日 S-03、跨年 S-05、宽字符集 S-13)。
- **对照点 (a):** S-02(13月32日)/S-04(非闰 2/29)——FC/Worker datetime 拒(400 / OssAdminError),JS 正则 `test → true` 双 TZ 实证。生产者可产出消费者必拒的 fragment_id。
- **对照点 (b):** S-14 `.m4a` key——Worker `None`(endswith),JS `fragmentIdFromObjectKey` 照单全收。
- **对照点 (c):** S-18 目录≠前缀 key——Worker `None`(往返等式),第四处放行;且 S-07 实证小程序纯函数自身可产出此类错位 key(fragmentId@23:59:59 + recordedAt@次日),**此类对象上传后 Worker 轮询静默跳过,数据滞留 OSS 无告警**——02-04 归类的核心输入。
- **对照点 (d):** S-06 同一 UTC 瞬间(2026-07-04T16:30:00Z)双 TZ 产出不同 fragment_id(20260705T003000 vs 20260704T123000)与不同目录日期;单 TZ 进程内自洽。
- **chunk 裁决(Open Question 3):** 分片不改 fragment_id 形态;`addChunk` 实测 chunk_seq=1,2 且 fragment_id 原样;`resolveChunkTotal(1)=null/(2)=2` 佐证组① 行 14 映射约定。

## 验证结果

- 样本表 `grep -c '^| S-'` = 23(附录 18 行 + 结论节汇总表 5 行)≥ 11 ✓;『销号』列全 ✅ 无空置 ✓
- `TZ=Asia/Shanghai` / `TZ=America/New_York` / `fragmentIdFromObjectKey` / `buildObjectKeyPreview` grep 全命中 ✓
- 来源断言:harness.py 首部三个 `__file__` 断言(poller/fc_sts/oss_admin)全部通过,输出记录 scratchpad 前缀 ✓
- 冒烟 import(RESEARCH A2):`import fc_shared` + `import soniscope_worker.poller` 成功,无网络触发 ✓
- 零云 IO:harness 只调用纯函数;零安装(仓库既有 .venv + 系统 node)✓
- 零仓库污染:`git diff --stat 5927f36 -- apps/ scripts/ docs/` 空;`git status --porcelain` 仅 `.planning/`(Task 1、Task 2 收尾各验一次)✓
- harness 与导出树仅存于会话 scratchpad,未提交 ✓

## Deviations from Plan

### 1. [如实记录] 会话内执行先于样本表落盘,预期推导严格取自静态结论

- **Found during:** Task 1
- **Issue:** 计划步骤①要求"先写定预期再执行";会话实际顺序为先跑 python harness 再写附录表。
- **Fix:** 预期三格全部从 02-01 已在案的组① 行 1/2/4/5/6 静态结论推导并逐格标注静态行号依据(静态结论先于本计划存在,不存在结果倒灌预期的通道);实测与静态预期零矛盾,防倒灌目标实质达成。
- **Commit:** 2844892

### 2. [授权内扩充] 样本 18 个,超 11 类下限

- **Found during:** Task 1
- **Issue:** D-07 类别为下限,计划授权 Claude's discretion 可加。
- **Fix:** 闰日拆合法/非法双样本(S-03/S-04)、deviceShortId 三边界(S-08~S-10)、ULID 三边界(S-11~S-13)、空/畸形三样本(S-16~S-18),共 18 样本覆盖 11 类。
- **Commit:** 2844892

其余按计划执行,无功能性偏差。

## 秘密红线遵守

样本全为合成数据(合成 ULID `01HZX3K8MN5PQR9TFB7AYWVCDE`、合成 deviceShortId `dev01a`);佐证记录只含合成样本值与纯函数输出,无任何真实 openid/凭证/疑似秘密值入文。

## 移交下游

- **02-04:** 对照点 (a)-(d) 为组① 行 2/4/5 四类判定(良性/潜伏/活跃/覆盖洞)的行为级佐证;"错位 key 被 Worker 静默跳过、数据滞留 OSS 无告警"是行 4/5 归类与 F-CON 严重度评估的关键行为事实;样本清单为 CONTRACT-TEST-RECIPE.md(D-15/D-16)现成黄金样本集。
- **零 diff 收尾:** 本计划两任务收尾各验一次零 diff;矩阵『收尾』章节按计划留 02-04 统一落笔。

## Self-Check: PASSED

- `.planning/audit/CONTRACT-MATRIX.md`(往返校验结论 + 附录两节非空)— FOUND
- Commit 2844892 — FOUND
- Commit 7d657a9 — FOUND

---
*Phase 2 Plan 03 完成: 2026-07-05(2 任务 2 提交,18 样本全销号,双 TZ 双语言执行佐证,零 diff 通过)*
