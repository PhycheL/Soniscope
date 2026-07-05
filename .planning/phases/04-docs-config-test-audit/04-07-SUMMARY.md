---
phase: 04-docs-config-test-audit
plan: 7
subsystem: audit
tags: [test-audit, coverage-ledger, reverse-mapping, HYP-23, HYP-24, D-09, D-10]
requires:
  - "04-06(TEST-AUDIT.md 骨架:8 面清单 + 41 行台账 + 22 行反向映射)"
provides:
  - ".planning/audit/TEST-AUDIT.md — 41 行台账全量回填(8/8)+ HYP-23/HYP-24 专项事实清单 + 反向映射终态(22 = 22 + 0)"
affects:
  - "04-08(F-TEST 按面聚合立条:缺口候选面清单见本 SUMMARY『04-08 缺口候选面清单』节)"
  - "04-09(HYP-23/HYP-24 回填锚点:两个专项结论行在 TEST-AUDIT.md 在档)"
tech-stack:
  added: []
  patterns:
    - "取证一律 git show/git grep @ 5927f36;JS 页面加载须以变量形态检索(require(INDEX_PAGE)),字面 require 模式 grep 零命中"
    - "台账只登记线索与证据行号,判断(立条)留 04-08;『无缺口线索』亦逐行显式落账"
key-files:
  created: []
  modified:
    - .planning/audit/TEST-AUDIT.md
decisions:
  - "HYP-23 补偿事实:errors.py 实际枚举 9 码(计划预列 7 + INVALID_REQUEST/HEAD_OBJECT_FAILED),9/9 均有 handler 入口级行为覆盖;GET/POST/异常三类入口路径均被驱动"
  - "HYP-24 边界事实:3/3 注册页均被 node 测试真实加载,index.js(796 行)被 4 文件 Page harness 驱动——假设前提『页面无自动化测试』与实态不符,残余缺口是行覆盖比例无实测数据(coverage-node.md 未产出)"
  - "F-CODE-02 销号 → 缺口参照原严重度 MEDIUM(失败对象多轮重复/计数面零断言,重复轮次锁定仅及成功路径)"
  - "F-CODE-08 销号 → 缺口参照原严重度 LOW(两份 FC 请求组装各有测试但无跨份同步断言/共享源)"
metrics:
  duration: "~14min"
  completed: "2026-07-05"
status: complete
---

# Phase 4 Plan 7: 测试台账逐面普审与专项回填 Summary

41 个测试模块(worker 24 + fc 7 + node 10)按 D-10 的 8 面逐个过账完毕,台账全量 8/8 且产出/备注列非空;HYP-23 逐错误码补偿清单(9/9 有 handler 级覆盖)与 HYP-24 页面加载边界事实(index.js 实际被 4 文件加载,假设前提证伪)在档;反向映射 2 条占位态销号,终态 22 = 22 + 0。

## 完成内容

### Task 1: worker 侧 24 文件逐面普审(commit ef7442a)

- 24 行台账回填 8/8;面⑥全量命中登记(仓库唯一 skipif = `test_miniprogram_js.py:24`,node 缺失静默跳过全部 10 个 JS 测试 → D-11 指针)
- 面④核对:`test_nls.py:401,449-450` 重试常量结构锁定(sleeps==list(RETRY_DELAYS_SECONDS)),数值字面 5/15/45 无断言(F-CODE-07 反查);object key 格式字面锁定多处在档(test_ops/test_e2e_scenarios/test_fc_live)
- 面②抽查:`test_poller.py` FakeSource(:52-76)与 RealOssSource 仅经 Protocol 结构对齐(mypy strict),行为面无对齐锁定——线索登记不下判断

### Task 2: fc 侧 7 文件普审与 HYP-23 专项(commit dddcff8)

- 7 行台账回填 8/8;新增 TEST-AUDIT.md『HYP-23 专项』节
- 错误码全集以 errors.py 实际枚举为准 = 9 个(计划预列 7,另有 INVALID_REQUEST、HEAD_OBJECT_FAILED);逐码覆盖表 9 行,每行覆盖判定非空,全部『有』且 handler 入口级驱动
- handler 入口路径证据:importlib 唯一模块名动态加载双 handler(`test_fc_handlers.py:41-45,70`)= 绕开 mypy 豁免的行为级补偿;GET 存活 :83-85 / POST 成功 :99-121(issue)与 :105-122(verify)/ 异常分支 500/400/403 + 两侧上游失败无泄漏
- 结论行同时含 HYP-23(04-09 回填锚点)与 DNF-03 交叉引用,不质疑豁免本身

### Task 3: node 侧 10 文件普审、HYP-24 专项与反向映射收敛(commit e21be2e)

- 10 行台账回填 8/8;面④ JS 镜像常量字面锁定在档(RETRY_DELAYS_MS=[5000,15000,45000]、MAX_UPLOAD_RETRIES=3、错误码裸字符串)
- HYP-24 专项节:检索方法备注(字面 `require.*pages/` 零命中,须按变量形态查)+ 加载矩阵(3/3 注册页全部被加载;index.js 被 chunking/draft_confirm/ids/interruption 4 文件 Page harness 加载,行号在档)+ 明确判定『index.js 被测试加载,HYP-24 假设前提与实态不符』;coverage-node.md 未产出,留 04-08 补引指针
- 反向映射销号:F-CODE-02 → MEDIUM 终态(test_pipeline.py:276,289 重复轮次锁定仅及成功路径;失败多轮面 grep 零命中);F-CODE-08 → LOW 终态(uploader.test.js:68,92 与 redesign_view.test.js:126 各驱动一份组装,无跨份同步断言)
- 机械对账终态:41 行全 8/8(行计数等式成立);22 = 22 终态 + 0 占位 ✓

## 04-08 缺口候选面清单(线索层,判断留 04-08)

| # | 来源文件 | 面 | 线索 |
|---|----------|-----|------|
| 1 | test_miniprogram_js.py | ⑥ | :24 skipif node 缺失→静默跳过全部 10 个 JS 测试(单点闸门)→ D-11 三方对照 |
| 2 | test_nls.py | ④ | 重试常量结构锁定、数值字面 5/15/45 无断言(F-CODE-07 已承载) |
| 3 | test_poller.py | ② | FakeSource 与 RealOssSource 行为面无对齐锁定(签名经 mypy 结构对齐) |
| 4 | test_audio.py | ①/⑦ | 全文件零 pytest.raises,失败分支均以留档位置断言表达 |
| 5 | test_e2e.py | ① | 编排结果多为 `assert code == 0`(:149,173,217,250),报告内容值断言偏薄 |
| 6 | test_manifest.py | ⑧ | monkeypatch 直引私有 `_fixture_path`(:288,298)(轻) |
| 7 | test_skeleton.py | ③ | :39-49 直改 os.environ 与 monkeypatch 惯例混用(轻) |
| 8 | test_custom_runtime_app.py | ⑧ | :57 直测私有 `_port()`(轻) |
| 9 | oss_sign.test.js | ⑤ | 秘密标记仅参与派生(:39,91),无『raw secret 不出现在表单/policy』负断言 |

反向映射终态缺口(20 条参照原严重度,已含 F-CODE-02 MEDIUM/F-CODE-08 LOW 新销号)与上表合并后由 04-08 按面聚合立 F-TEST 条目。

## 验证结果

- `grep -c '^| \`apps/.*8/8'` = 41 = `grep -c '^| \`apps/'`(台账行计数等式成立)
- `grep -c '补证中'` = 0(反向映射零占位残留)
- HYP-23 专项表 9 行 = errors.py 实际枚举数;结论行含 HYP-23 + DNF-03
- HYP-24 结论行含 index.js 被加载的明确判定;RETRY_DELAYS_MS 核对在档
- 封版产物零改动:`git diff --stat 5927f36 -- apps/ scripts/ docs/` 为空(T-04-16 mitigate;全程纯 git show/git grep 静读,未实跑任何测试)
- T-04-15 mitigate:F-TOOL-05 行沿用 04-06 写法(仅位置+模式名,无值本体);oss_sign 秘密标记仅引测试自造样本名,无真实凭证

## Deviations from Plan

**1. [证据修正] HYP-24 指定的检索模式零命中,改用变量形态检索**
- **Found during:** Task 3
- **Issue:** 计划指定 `git grep -n "require.*pages/" 5927f36 -- apps/miniprogram/test` 全量命中——实际零命中,因页面加载一律经 `path.resolve` 变量 + `require(INDEX_PAGE)` 形态
- **处理:** 以 `git grep "pages/"`(路径常量定义 10 处)+ `require(<VAR>)`(8 处)双检索还原完整加载矩阵,并把检索方法备注写入 HYP-24 专项节,防后续复核踩同一坑
- **影响:** 无负面——反而发现 TESTING.md 漏记 index 页 4 处 harness 加载,HYP-24 假设前提被证伪(这是本计划最重要的单条事实发现)
- **Commit:** e21be2e

**2. [枚举修正] HYP-23 错误码行数 9 ≠ 计划预列 7**
- **Found during:** Task 2
- **Issue:** 计划预列 7 码;`errors.py @ 5927f36` 实际枚举 9 码(另有 INVALID_REQUEST :15、HEAD_OBJECT_FAILED :19)
- **处理:** 按计划明示『以实际枚举为准』扩为 9 行,全部逐码登记
- **Commit:** dddcff8

其余按计划逐字执行。

## Known Stubs

无。台账 41 行、专项两节、反向映射 22 行均为终态;唯一外部缺位是 coverage-node.md(pages/ 行覆盖率实测佐证),系 04-01/04-02 范围产物未产出,已在 HYP-24 结论行留 04-08 补引指针,非本计划 stub。

## Threat Flags

无新增安全面。T-04-15(台账备注列凭证模式只记位置+模式名)与 T-04-16(纯静读、files_modified 仅 TEST-AUDIT.md、封版产物零改动)两项 mitigation 均已落实,见验证结果。

## Self-Check: PASSED

- FOUND: .planning/audit/TEST-AUDIT.md(41 行 8/8、HYP-23/HYP-24 两专项节、反向映射终态)
- FOUND: commit ef7442a(Task 1)
- FOUND: commit dddcff8(Task 2)
- FOUND: commit e21be2e(Task 3)
