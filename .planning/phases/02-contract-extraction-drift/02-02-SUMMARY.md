---
phase: 02-contract-extraction-drift
plan: 02
subsystem: audit
tags: [contract-audit, drift-matrix, http-contract, mirror-constants, duplication-census]
requires:
  - 02-01(矩阵骨架、判定标准/负面清单、组① 15 行)
provides:
  - 组② 小程序↔FC HTTP 契约 28 行(请求 3+3、响应 7+6、错误码 7、reason 2)
  - 组③ 两侧镜像常量 5 行(重试节奏/3 次/50MB/600s/STS 900s)
  - CONTRACT-03 普查章节:9 候选核实 + 5 条扫描命令存档 + 普查新行 49-51 + D14-1~6 移交 + 机械对账
affects:
  - 02-03(往返校验:AC#4 object_key 链执行佐证;size=0 边界样本)
  - 02-04(判定列回填 51 行;expiration/endpoint 未消费、错误码 absent×7、50MB absent 的归类)
  - Phase 3(D14-1~6 重复债务线索)
  - Phase 4(CLAUDE.md 错误码分支声明不符 DOC 线索)
tech-stack:
  added: []
  patterns:
    - git show/git grep 基线取证(D-05,零工作树取证)
    - 扫描命令原文 + 命中计数分栏存档(D-13 机械对账模式)
key-files:
  created: []
  modified:
    - .planning/audit/CONTRACT-MATRIX.md
decisions:
  - "错误码 7 行小程序格统一判 absent(Open Question 1 裁决):classifyFcResponse 全文为证,小程序按 statusCode 段分支 + data.error 通用透传,7 码字面量在实现代码零出现;CLAUDE.md 'branches on the same strings' 声明不符记 Phase 4 DOC 移交,不在本矩阵立 DOC 判断"
  - "响应字段 expiration/endpoint 判 agree(键名与必备性)但格内如实标注值无下游消费(policy 过期本地 now+900s 独立推导;上传 URL 用 config.OSS_UPLOAD_URL)——归类留 02-04"
  - "50MB 小程序格判 absent(grep 存档为据:无镜像常量无预检,上限仅经 SIZE_EXCEEDED 事后感知),覆盖洞候选;600s FC/Worker 双 n/a(30 命中人工筛选全部无关值)"
  - "普查命中联调工具契约镜像(fc_live.py/verify_upload_live.py)拆 3 新行(49-51)做语义对照(全 agree,注释自证故意重复);组② Worker 列 n/a 裁决不变(工具非业务流水线)"
metrics:
  duration: 10min
  completed: 2026-07-05
status: complete
---

# Phase 2 Plan 02: 组②③ HTTP 契约与镜像常量抽取 + 重复逻辑普查 Summary

组② 28 行 + 组③ 5 行 + 普查新行 3 行落格(矩阵累计 51 行,证据密度 230 处 `@ 5927f36`):HTTP 契约字段名两侧逐字符一致但小程序对 expiration/endpoint 零消费、对 7 个错误码字符串零字面量(statusCode 段分支 + 通用透传,推翻 CLAUDE.md 声明);50MB 上限小程序侧 absent;普查确认联调工具族(fc_live/verify_upload_live)为契约字面量的额外镜像声部。

## 完成任务

| Task | 名称 | Commit | 产出 |
|------|------|--------|------|
| 1 | 组② HTTP 契约逐字段抽取(含 verify-upload 全集展开与错误码分支裁决) | 8a66a26 | 行 16-43(28 行)+ Open Question 1/2 行号级答案 |
| 2 | 组③ 镜像常量行抽取 | 20a4277 | 行 44-48(5 行)+ 2 条 grep 裁决存档 |
| 3 | 重复逻辑普查(D-13 双保险 + D-14 移交) | e37fa8a | 9 候选核实表 + 5 命令存档 + 行 49-51 + D14-1~6 + 机械对账 |

## 关键静态事实(供 02-03/02-04 消费)

- **Open Question 1 裁决(行 35-41):** 小程序不按错误码字符串分支——uploader.js:34 按 statusCode===200 二分、verify.js:31,46,49 按 200/≥500/4xx 三段;`data.error` 仅 String() 透传(uploader.js:48、verify.js:49);uploader.js:47 提及 3 码但为注释。7 码小程序格全 absent。
- **Open Question 2 裁决(行 26-34):** verify-upload 请求全集 = code/fragment_id/expected_size(handler.py:46-48,51-52);响应全集 = verified/reason/actual_size/etag/size/last_modified 6 字段(head.py:34-55 三态映射)。
- **未消费字段(行 22/24/31-34):** expiration、endpoint 经 7 字段非空校验后零下游消费;actual_size/etag/size/last_modified 在 classifyVerifyResponse 提取后未随状态补丁落存。
- **size=0 边界(行 18/28):** 小程序 manifest 缺失时发 size=0(uploader.js:63 / verify.js:59-60 的 `|| 0`),FC parse_size 判 ≤0 抛 400 INVALID_REQUEST(sts.py:86-87)——02-03 高价值样本。
- **AC#4 往返链(行 25):** object_key 用 FC 返回值(oss_sign.js:77 `eq $key` 精确条件),02-03 执行佐证目标。
- **组③:** 重试节奏 JS 两份独立常量(uploader.js:28 / verify.js:16)+ Worker MAX_RETRIES 独立字面量(nls.py:46,与表长无绑定);STS 900s 在小程序有独立镜像 oss_sign.js:16。
- **普查:** poller.py date_of 复用 object_key_for 派生非第四处实现;ULID 生产链路生成端唯一;HMAC/签名无跨语言重复;配置三机制并存无代码内值重复;联调工具镜像 → 行 49-51(全 agree,fc_live.py:41 注释自证故意重复)。

## 验证结果

- 9 个错误码/reason 字符串逐一 grep 命中矩阵 ✓;`credential_response` 命中 ✓
- 4 个常量标识符(52428800/CHUNK_MAX_DURATION_SECONDS/RETRY_DELAYS/STS_MAX_DURATION_SECONDS)grep 命中 ✓
- `grep -c 'git grep'` = 11 ≥ 5 ✓;fragmentIdFromObjectKey/HYP-03/移交 Phase 3/无新发现 全部命中 ✓
- 证据密度:`grep -o '@ 5927f36' | wc -l` = **230**(02-01 后为 71)
- 零 diff:`git diff --stat 5927f36 -- apps/ scripts/ docs/` 空输出(三任务收尾各验一次);`git status --porcelain` 仅见 `.planning/`
- 人工抽查 4 格(sts.py:110 / verify.js:42 / env.py:41 / oss_sign.js:16)`git show | sed -n '<line>p'` 全部命中
- Worker 列组② 全部 n/a + 结构性理由,无行号(D-03)✓

## Deviations from Plan

### 1. [行号以实际为准] reason 定义行号 errors.py:23-24(计划勘察值 23-25)

- **Found during:** Task 1
- **Issue:** RESEARCH 勘察行号 `errors.py:23-25` 中 :25 为空行,实际定义在 :23-24
- **Fix:** 按 git show 复核实际行号落格(02-01 同款授权模式:勘察行号偏差以实际为准)
- **Commit:** 8a66a26

### 2. [Rule 1 - 一致性修正] 组② 普查行号前向引用修正(44-46 → 49-51)

- **Found during:** Task 2
- **Issue:** Task 1 落格时普查新行编号预估为 44-46,组③ 落格(行 44-48)后应为 49-51
- **Fix:** Task 2 提交内一并修正组② 的 3 处前向引用
- **Commit:** 20a4277

### 3. [如实记录] 主体行数 48(计划预估 35-45)

- **Found during:** Task 2 收尾
- **Issue:** verify-upload 响应按实际代码展开为 6 字段、请求 3 字段,组② 达 28 行,三组主体合计 48 行,略超计划预估区间上沿
- **Fix:** 无需修正——仍在 D-02 锁定的 30-50 健康区间内;机械对账行如实记录 51 行总数(含普查 3 行)
- **Commit:** e37fa8a

## 秘密红线遵守

矩阵新增证据全部为字段名、错误码/reason 字符串(errors.py 注释自证为公开稳定标识符)、数值常量与注释摘录;STS 凭证字段仅引用字段名(access_key_secret 等标识符),无任何值本体入文。

## 移交下游

- **02-03:** size=0 边界(行 18/28)、AC#4 object_key 往返链(行 25)、expiration 未消费(行 22)为执行佐证输入。
- **02-04:** 51 个 `待判定`;重点归类:行 22/24(未消费 agree)、行 35-41(absent×7 是覆盖洞还是良性透传设计)、行 46(50MB absent 覆盖洞候选)、行 31-34(提取后丢弃)。
- **Phase 3:** D14-1~6(sha256 双实现挂 HYP-03、重试表四落点、联调工具镜像集群、请求组装双份、配置三机制、key 反推第四处)。
- **Phase 4:** CLAUDE.md 错误码分支声明与实态不符(组② 行 35-41 行下注)。

## Self-Check: PASSED

- `.planning/audit/CONTRACT-MATRIX.md` — FOUND
- Commit 8a66a26 — FOUND
- Commit 20a4277 — FOUND
- Commit e37fa8a — FOUND

---
*Phase 2 Plan 02 完成: 2026-07-05(3 任务 3 提交,组②③ + 普查落格,矩阵 51 行,零 diff 通过)*
