---
phase: 03-component-toolchain-deep-dive
plan: 06
subsystem: audit-toolchain
tags: [audit, tool-dimension, scripts, makefile, hyp-07, secrets-redline]
requires:
  - "03-02 scans/secrets.md 三态销号表(#14/#15 确认待去向)与 scans/gates-baseline.md(#1-7 深挖线索)"
  - "03-05 findings/toolchain.md F-TOOL-01~04(编号顺延基点)与 HANDOFF TEST 节"
provides:
  - "COVERAGE.md TOOL 维度 16/16 全部落格(scripts 3 行 + Makefile 行,全 9/9 面)"
  - "findings/toolchain.md F-TOOL-05~07(HYP-07 核实结论 + 门禁恒红 + .PHONY 幻影)"
  - "HYPOTHESES.md HYP-07 证实 / HYP-18 细化(累计回填 13 条,TOOL 4 条全部闭环)"
  - "scans/secrets.md #14/#15 与 gates-baseline.md #1-7 销号去向闭环"
  - "HANDOFF-PHASE4.md TEST 节 HYP-25 两条移交证据"
affects:
  - "03-07(完成判定收口:TOOL 16/16 对账、深挖点 HYP-07/18 已落)"
  - "Phase 4 TEST(HYP-25 移交证据)"
  - "Phase 5(F-TOOL-05 MEDIUM 上线判定候选)"
tech-stack:
  added: []
  patterns:
    - "秘密类证据只写位置+模式名(Pitfall 7 红线):HYP-07/F-TOOL-05 全链路零值本体"
    - "Makefile .PHONY 完整性机械对账(comm 目标集 vs 声明集)"
key-files:
  created: []
  modified:
    - .planning/audit/findings/toolchain.md
    - .planning/audit/COVERAGE.md
    - .planning/audit/HYPOTHESES.md
    - .planning/audit/HANDOFF-PHASE4.md
    - .planning/audit/scans/secrets.md
    - .planning/audit/scans/gates-baseline.md
decisions:
  - "HYP-07 证实 → F-TOOL-05 定级 MEDIUM:逐字命中 CHARTER『已过期凭证曾入库(泄露习惯风险)』锚;AccessKeyId 系 TMP. 前缀 STS 临时凭证 + 已过期 + 单对象 GET,不触 CRITICAL 有效长期凭证锚"
  - "HYP-18 细化:两代 SDK 并存证实,但『仅脚本级、不随 Worker/FC 打包』半句在 Worker 侧证伪(aliyunsdkcore 是声明运行时依赖并承载生产 filetrans 主路径);FC 侧属实"
  - "gates-baseline #1(mypy 结构性 exit 1)静读核实立 F-TOOL-06(MEDIUM):门禁恒红使退出码信号失效,取 CHARTER MEDIUM 误导性锚系"
  - ".PHONY 幻影目标 lint-miniprogram 立 F-TOOL-07(LOW)而非 face7 备注:按声明名调用产生硬错误,且 agent 文档以该名为调用口径"
  - "test_asr.py appkey 明文回显(:328)记 face3 轻微不立发现:手工脚本终端回显操作者自供值,粘贴目标块不含该字段"
metrics:
  duration: "~14 min"
  completed: "2026-07-05"
status: complete
---

# Phase 3 Plan 06: scripts/ 与 Makefile 普审+深挖 Summary

**One-liner:** AUDIT-02 收尾——scripts/ 三文件(847 行)与 Makefile(45 目标)9 面全过审,HYP-07 点名线索核实证实并以零值泄漏方式立 F-TOOL-05(MEDIUM 已过期凭证入库锚),另立 F-TOOL-06(make typecheck 结构性恒红)与 F-TOOL-07(.PHONY 幻影目标),HYP-07/18 回填后 TOOL 维度 4 条 HYP 全部闭环。

## What Was Done

### Task 1: scripts/ 三文件普审+深挖(含 HYP-07 核实结论)— commit 11c707d

- **test_asr.py(355,深挖 HYP-07/HYP-18)**:
  - **HYP-07 证实 → F-TOOL-05(MEDIUM)**:`DEFAULT_FILE_LINK`(`scripts/test_asr.py:79-81 @ 5927f36`)确为已提交的带签名 OSS 预签名 GET URL——`OSSAccessKeyId=` 签名 URL 模式 + `Signature=` 签名参数模式同行双命中;过期状态可静态判定(URL 内 `Expires=` unix 时间戳参数对应 2026-05-29,早于审计日 2026-07-05);AccessKeyId 为 `TMP.` 前缀 STS 临时凭证形态(非 LTAI 长期 AK);:78 行内注释自认"OSS 签名 URL 会过期"。证据全链路(发现条目/回填/销号/移交)只写位置+模式名,引用片段仅截变量名与赋值号,零值本体。
  - **HYP-18 采证**:docstring 钉定 `aliyun-python-sdk-core==2.16.0`(`:22-23`),AcsClient(`:159,167`)/CommonRequest(`:174,217`)全程 legacy POP 形态。
  - HYP-25 顺带证据(门禁规则集内真实违例 6 条,gates-baseline #2-7)→ 只记 HANDOFF-PHASE4.md TEST 节,状态不动(Pitfall 4)。
- **fetch_test_fixtures.py(249)**:无发现。职责边界核实清晰(脚本管 IO 编排 + `.part`→`os.replace` 原子落盘 + finally 清理,校验纯逻辑全委托 fixtures.py);凭证仅入 StaticCredentialsProvider、错误只列字段名;.env 解析第三处实现与 gen_worker_config.sh 口径一致、与 paths.py 无界向上搜索相异(F-CODE-04 对照证据,不重复立)。
- **gen_worker_config.sh(243)**:无发现。秘密写入面通过——模板凭证恒写 `__FILL_ME__` 占位符,脚本全程不接触真实秘密;`chmod 600` 紧随生成且写入→chmod 窗口仅含占位符;`set -euo pipefail` 在位;覆盖需显式 `--force` 并提示后果;`--check` 仅回显占位符命中行。
- scans/secrets.md #14/#15 去向闭环至 F-TOOL-05。

### Task 2: Makefile 静读审计(45 目标)与 HYP-07/18 回填 — commit c8a51e4

- **Makefile(171 行,D-08 零执行静读)**:按 6 个功能组过 9 面;危险目标逐个细读结论——45 目标全部零 prerequisite(机械核对,无连带触发面);`oss-delete-obj` 唯一删除入口双闸门 + 【仅测试用】;`rollback-fc`/`fc-logs` 空 FUNCTION 缺参报错失败安全;`deploy-fc` 空 FUNCTION 双函数部署系 help 明示语义(备份缺口已由 F-TOOL-02 承接)。
- **F-TOOL-06(MEDIUM)**:`make typecheck` 在仓内结构性恒红——`apps/fc/shared/app.py:14 @ 5927f36` 部署态导入 `from handler import handler` 在 mypy strict `files` 范围内且无 override,exit 恒 1,门禁二值信号失效(gates-baseline #1 销号去向)。
- **F-TOOL-07(LOW)**:.PHONY 机械对账 45 目标全在列(46 条目),幻影条目 1 个——`lint-miniprogram` 无对应规则,按声明名调用得 "No rule to make target" 硬错误。
- 门禁口径观察点销号:lint 目标实际调用 `ruff check apps/`(`:167`),范围限定使 vendored/scripts 裸跑违例不入门禁,差异系调用口径而非配置;scripts/ 排除为注释自认(`:166`,HYP-25 证据面)。
- **HYP-07 回填(证实)**:状态 + 一句结论 + 三组位置证据(:79-81 双模式命中 / :78 自认注释 / :112-115 缺省链),备注引 F-TOOL-05 与 MEDIUM 锚对应关系。
- **HYP-18 回填(细化)**:两代并存证实;"仅脚本级"半句 Worker 侧证伪(`apps/worker/pyproject.toml:13`、`nls.py:441-448,454-455 @ 5927f36` 生产主路径经 legacy AcsClient),FC 侧属实(两函数 requirements.txt 无该包);不引入弃用时间表判断(RESEARCH §State of the Art 口径)。
- 尾部统计更新:累计回填 13 条,Phase 3 回填集仅余 HYP-03(03-07 微基准)。

## Verification Results

- Task 1 awk(COVERAGE scripts 三行无待审)→ PASS;findings/ 秘密反扫(`OSSAccessKeyId=[0-9A-Za-z]{8,}|Signature=...{16,}`)零命中 → PASS。
- Task 2 awk(Makefile 行无待审)→ PASS;HYP-07/18 状态均非"未验证"且各含 `@ 5927f36` 证据 → PASS。
- 全 .planning/audit/ 加严反扫(含 `Expires=[0-9]{6,}` 模式)零命中——零值泄漏成立。
- 零 diff:`git diff --stat 5927f36 -- apps/ scripts/ docs/` 输出为空 ✓。
- D-08 全程成立:三个脚本与全部 45 个 make 目标零执行,取证仅 `git show 5927f36:<path>`。
- 成功判据 2 闭合:TOOL 维度 16/16 落格,test_asr.py 点名线索有台账级核实结论(F-TOOL-05 + HYP-07 证实)。

## Deviations from Plan

**1. [Rule 2 - 台账闭环] gates-baseline.md #1-7 销号去向追记**
- **Found during:** Task 2
- **Issue:** 03-02 在 scans/gates-baseline.md 留有 7 条"→ 深挖线索(03-06 ...)"去向指针,计划正文未显式列该文件为修改对象(frontmatter 列了 scans/ruff-extended.md 但该档无 03-06 待办)
- **Fix:** 沿 03-05"销号去向反填"体例,#1 追记 F-TOOL-06 去向、#2-7 追记 HANDOFF 移交去向,并闭合 :39 的 lint 调用口径观察点
- **Files modified:** .planning/audit/scans/gates-baseline.md
- **Commit:** c8a51e4

(scans/ruff-extended.md 经核实无 03-06 待办项——scripts 侧唯一命中 #69 已在 03-02 销号为误报,故未修改该文件。)

## Findings Ledger Delta

| ID | 严重度 | 一行标题 |
|----|--------|----------|
| F-TOOL-05 | MEDIUM | test_asr.py 已提交过期预签名 STS URL,签名 URL 入库先例成立(HYP-07 证实) |
| F-TOOL-06 | MEDIUM | `make typecheck` 门禁仓内结构性恒红(app.py 部署态导入) |
| F-TOOL-07 | LOW | Makefile .PHONY 幻影目标 lint-miniprogram,按声明调用即硬错误 |

## For 03-07

- TOOL 维度收口输入:COVERAGE TOOL 16/16 全落格;深挖点登记表 HYP-04/07/15/18 与 D14-3 均已"已回填/证据齐备",CODE 侧 10 条 HYP 登记行下落与完成判定节由 03-07 统一收口。
- F-TOOL 真实条目累计 7 条(`grep -c '^### F-TOOL-'` → 8,含 F-TOOL-00 示例)。
- HYPOTHESES 尾部:13/25 已回填,Phase 3 集仅余 HYP-03(微基准,D-16)。

## Self-Check: PASSED

- [x] `.planning/phases/03-component-toolchain-deep-dive/03-06-SUMMARY.md` exists
- [x] Commits 11c707d / c8a51e4 exist on worktree branch
- [x] COVERAGE.md TOOL scripts 3 行 + Makefile 行无待审(awk → 0)
- [x] `grep -c '^### F-TOOL-'` → 8(含 F-TOOL-00 示例,真实 7 条)
- [x] findings/ 与全 audit/ 秘密反扫零命中;零 diff 为空

---
*03-06 Summary: 2026-07-05(TOOL 16/16 收口,F-TOOL-05~07 入账,HYP-07 证实/HYP-18 细化,零值泄漏、零 diff——AUDIT-02 对象全覆盖)*
