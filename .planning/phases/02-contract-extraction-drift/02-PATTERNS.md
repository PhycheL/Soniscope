# Phase 2: 契约抽取与漂移分析 - Pattern Map

**Mapped:** 2026-07-04
**Files analyzed:** 4(3 个仓库产物 + 1 组 scratchpad 临时 harness)
**Analogs found:** 4 / 4

> 本阶段是审计文档阶段:产物全部为 `.planning/audit/` 下 Markdown,零 diff(不改 apps/、scripts/、docs/)。
> 最近的模式来源不是产品代码,而是 Phase 1 已定稿的审计产物(CHARTER.md / HYPOTHESES.md / DO-NOT-FIX.md / findings 骨架)。
> 唯一涉及代码模式的产物是条件触发的 CONTRACT-TEST-RECIPE.md(伪代码设计稿),其分析对象是仓库既有测试桥接与 node:test 文件。

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.planning/audit/CONTRACT-MATRIX.md`(新建) | 审计证据文档(矩阵 + 附录 + 普查存档) | transform(基线取证 → 结构化对照表) | `.planning/audit/HYPOTHESES.md` + `.planning/audit/CHARTER.md` | role-match |
| `.planning/audit/findings/contract.md`(追加) | 发现台账(F-CON 条目) | transform(矩阵判定 → 九字段发现) | 同文件 F-CON-00 骨架 + CHARTER 九字段 schema + DNF 条目文风 | exact |
| `.planning/audit/CONTRACT-TEST-RECIPE.md`(条件新建) | 测试设计配方(仅设计不实现) | batch(黄金样本 → 双语言测试骨架伪代码) | `apps/worker/tests/test_miniprogram_js.py` + `apps/miniprogram/test/oss_sign.test.js` | role-match |
| scratchpad `harness.py` / `harness.js`(临时物,不入仓库) | 执行佐证脚本 | batch(样本值 → 纯函数输出对照) | RESEARCH Code Examples 配方 + `oss_sign.test.js` 的 require/常量模式 | role-match |

## Pattern Assignments

### `.planning/audit/CONTRACT-MATRIX.md`(审计证据文档,新建)

**Analogs:** `.planning/audit/HYPOTHESES.md`(分节台账 + 机械对账)、`.planning/audit/CHARTER.md`(证据格式 + 命令存档)、02-RESEARCH.md Pattern 1(矩阵格式,已由决策锁定)

**文件头模式**(HYPOTHESES.md:1-4,所有 Phase 1 审计产物统一):
```markdown
# 未验证假设清单

**Created:** 2026-07-04
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)
```
→ CONTRACT-MATRIX.md 头部照抄此三行结构:标题 + `**Created:**` + 基线引用行(全 SHA 只在 CHARTER 声明一次,per CHARTER D-02,正文一律短 SHA)。

**机械对账/可复核完成判定模式**(HYPOTHESES.md:6-12,`## 转换对账` 节):
```markdown
**29 条 CONCERNS.md 粗体线索 = 4 条 DNF 预录入(见 `.planning/audit/DO-NOT-FIX.md`)+ 25 条 HYP;…**

- 机械计数命令:`grep -cE '^\*\*[^*]+:\*\*$' .planning/codebase/CONCERNS.md` → **29**
- 本文件核对:`grep -c '^### HYP-' .planning/audit/HYPOTHESES.md` → **25**;…;25 + 4 = 29 ✓
```
→ 这是 D-13"扫描命令与结果存档、不接受主观查过了"的既有先例:普查章节每条 `git grep` 命令原文 + 输出结果照此模式归档,并给出行数对账等式(矩阵行数 × 参与列 vs `grep -c '@ 5927f36'` 计数,对应 02-RESEARCH Validation Architecture 的 doc check)。

**命令存档模式**(CHARTER.md:58-64,fenced bash + 行内中文注释):
```bash
git show 5927f36:apps/miniprogram/config.js | sed -n '1,30p'   # 按基线读文件(带行号定位)
git grep -n 'fragment_id' 5927f36 -- apps/                      # 按基线检索
git diff --stat 5927f36 -- apps/ scripts/ docs/                 # 零 diff 验证(期望空输出)
```
→ 普查章节的扫描命令(02-RESEARCH.md:166-172 五条 grep)与收尾零 diff 记录用同样的 fenced bash + 注释格式。

**矩阵格证据格式**(02-RESEARCH.md:220-225 Pattern 1,由 D-11 锁定——agree 格同样带行号):
```markdown
| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|---|---|---|---|---|
| object key 模板 | agree `fc_shared/sts.py:59 @ 5927f36` | agree `oss_admin.py:50 @ 5927f36` | agree `audio.js:105 @ 5927f36` | — |
| fragment_id 日期合法性校验 | (状态) `sts.py:52-56 @ 5927f36` | (状态) `oss_admin.py:44-48 @ 5927f36` | (状态) `audio.js:95-97 @ 5927f36` | (四类标签 + F-CON-NN 链接) |
```
→ 格子状态词表:`agree` / `diverge` / `absent`(应参与未实现)/ `n/a`(结构性不适用,写一句理由代替行号,per D-03)。判定列只放四类标签 + F-CON 链接,Postel 分析不进矩阵(D-12)。

**表格风格**(CHARTER.md:110-116 严重度锚点表、DO-NOT-FIX.md 条目式):中文表头、场景语言、英文 ID/术语混排(RPT-09 风格已确立)。按 D-01 三组(OSS 数据面 / HTTP 契约 / 镜像常量)分节控制单表规模(Claude's discretion,防 Pitfall 8 行爆炸)。

**文档尾模式**(HYPOTHESES.md:227 / DO-NOT-FIX.md:47):
```markdown
---
*未验证假设清单: 2026-07-04(25 条 HYP + 1 条 Known Bugs 显式无线索记录;…)*
```
→ 收尾一行斜体:文档名 + 日期 + 关键计数摘要。CONTRACT-MATRIX.md 收尾章节另须记录零 diff 验证命令输出(期望空)。

---

### `.planning/audit/findings/contract.md`(发现台账,追加 F-CON 条目)

**Analog:** 同文件既有骨架 + CHARTER 九字段 schema(权威定义)

**追加位置**(findings/contract.md:21):新发现全部追加在 `## 发现` 标题之下;F-CON-00(第 7-19 行)是 schema 示例,**保留不动**(Phase 5 汇总时才剔除)。

**九字段条目模式**(CHARTER.md:139-151,逐字段固定顺序,ID 即小节标题):
```markdown
### F-CON-01: <一行标题>

- **维度:** 契约一致性 (CON)
- **严重度:** HIGH — 影响:上传对 Worker 永久不可见(静默数据滞留);可能性:仅在 fragment_id 格式变更时触发,当前格式下不触发
- **证据:** `apps/fc/shared/fc_shared/sts.py:95-102 @ 5927f36`
  > (引用的代码片段,从 git show 提取)
- **修复建议:** <一段>
- **工作量:** M(同组件多文件)
- **关联发现:** F-CODE-03;关联线索: HYP-07
- **上线判定:** (Phase 5 填,留空;取值 BLOCKER / PRE-LAUNCH / POST-LAUNCH)
- **状态:** draft(Phase 5 校准后改为 calibrated)
```

**本阶段特有的字段填法**(来自 CONTEXT D-09/D-10/D-12 + CHARTER 锚点):
- **严重度映射:** 良性→INFO/LOW;潜伏→MEDIUM 起;活跃失配→HIGH 起("活跃失配使上传对 Worker 永久不可见"是 CHARTER.md:113 的 HIGH 明文锚点)。理由固定格式 `影响:…;可能性:…`,禁数值评分(CHARTER.md:118)。
- **证据字段:** 除 `path:line @ 5927f36` + git show 引用片段外,反向引用 CONTRACT-MATRIX.md 矩阵行(D-09 证据与判断分离);Postel 生产者-消费者宽严分析(谁严谁宽、失配方向、触发条件)写在证据/修复建议字段内(D-12)。
- **关联发现字段:** 核心行挂 `HYP-13`(HYPOTHESES.md:124-129);sha256 相关行挂 `HYP-03`(HYPOTHESES.md:36-41);移交 Phase 3 的重复债务线索在此字段注明(D-14)。
- **工作量分档参照:** CHARTER.md:126-131 —— 跨 FC + Worker + 小程序三处同步的契约变更即 L 档的明文示例(CHARTER.md:130)。

**证据引用文风示例**(DO-NOT-FIX.md:24,行号 + 内容概述 + 不复制敏感值):
```markdown
- **证据:** `apps/miniprogram/config.js:8-10 @ 5927f36` — 第 10 行 `FC_ISSUE_CREDENTIAL_URL` 常量值为 `issue-cedential-ottfirocds.cn-beijing.fcapp.run`(少一个 r),第 8 行内联注释明确警告…
```

---

### `.planning/audit/CONTRACT-TEST-RECIPE.md`(条件新建,仅当出现非良性分歧,per D-15)

**Analogs:** `apps/worker/tests/test_miniprogram_js.py`(pytest→node 桥接,make 接入点)、`apps/miniprogram/test/oss_sign.test.js`(node:test 骨架 + 黄金样本常量形态)

**pytest→node 桥接模式**(test_miniprogram_js.py:1-36 @ 5927f36 —— 配方的 make 接入设计应复用此先例):
```python
"""把小程序 JS 单元测试(node 内置 test runner)纳入统一质量门 `make test`。…"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MINIPROGRAM_TEST_DIR = _REPO_ROOT / "apps" / "miniprogram" / "test"


@pytest.mark.skipif(shutil.which("node") is None, reason="node 不可用,跳过小程序 JS 单元测试")
def test_miniprogram_js_unit_tests() -> None:
    files = _test_files()
    # 该 node 版本 `node --test <dir>` 会把目录当模块加载,故传显式文件清单。
    result = subprocess.run(
        ["node", "--test", *files],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
```
关键可复用点:pytest 内起 `node --test` 子进程、node 缺席即 skip、显式文件清单(非目录)、`make test` 单一质量门。配方的 pytest 侧骨架伪代码照此结构,增加"读共享黄金样本 JSON"一步。

**node:test 骨架 + 黄金样本常量形态**(oss_sign.test.js:1-50 @ 5927f36):
```javascript
const test = require('node:test')
const assert = require('node:assert')

const oss = require('../utils/oss_sign')

test('HMAC-SHA256 与 node:crypto 一致(标准向量)', function () {
  const got = hmacSha256Hex('key', 'The quick brown fox jumps over the lazy dog')
  assert.strictEqual(got, 'f7bc83f43053…')
})

const CRED = {
  object_key: 'recordings/2026-06-27/20260627T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE.wav',
  // …access_key_secret: 'sts-secret-do-not-log'(测试假值,非真实秘密)
}
const META = {
  'x-oss-meta-session-id': '01HZX3K8MN5PQR9TFB7AYWVCDE',
  'x-oss-meta-chunk-seq': '1',
  'x-oss-meta-chunk-total': '0',
}
```
关键可复用点:zero-dep CommonJS `require`、中文测试名 + `function () {}` 风格、模块级 UPPER_SNAKE 样本常量——配方中黄金样本 JSON 的字段形态直接沿用 CRED/META 既有键名;测试文件命名沿用 `<module>.test.js` 于 `apps/miniprogram/test/`(仅纸面建议路径,本阶段不落文件)。

**配方文档结构**(由 D-16 锁定,无自由裁量):黄金样本文件 schema 与存放位置 → 覆盖的契约要素(引用矩阵行)→ pytest 与 node:test 双侧测试骨架伪代码 → make 接入点 → 验收标准。样本值直接复用 D-07 往返校验清单(02-RESEARCH.md:264-281 已给具体候选)。文档头/尾/基线引用格式同 CONTRACT-MATRIX.md(见上)。若全部良性不触发,则在 CONTRACT-MATRIX.md 显式记录"无需配方"(D-15 else 分支)。

---

### scratchpad `harness.py` / `harness.js`(临时执行佐证脚本,不入仓库)

**Analogs:** 02-RESEARCH.md Code Examples(:338-368,实测配方,直接照抄)+ 上述 oss_sign.test.js 的 require/样本常量模式

关键模式(全部来自 02-RESEARCH Pattern 2,经实测):
- 基线导出:`git archive 5927f36 apps/worker/src apps/fc/shared apps/miniprogram/utils apps/miniprogram/config.js | tar -x -C "$SCRATCH"`(整树导出保 import/require 结构;禁止手抄函数体)
- Python 侧:`PYTHONPATH="$SCRATCH/apps/worker/src:$SCRATCH/apps/fc/shared" <repo>/.venv/bin/python harness.py`;首行断言 `poller.__file__`/`fc_sts.__file__` 以 scratchpad 前缀开头,失败即中止(Pitfall 1 兜底)
- Node 侧:`TZ=Asia/Shanghai node harness.js` / `TZ=America/New_York node …`(时区敏感样本必须显式 TZ 且记入佐证记录,Pitfall 2)
- harness 只调用纯函数(`object_key_for`、`fragment_id_from_key`、`buildObjectKeyPreview`、`fragmentIdFromObjectKey`),样本值全为合成数据

## Shared Patterns

### 证据格式(全部三个仓库产物)
**Source:** CHARTER.md:14-15
**Apply to:** 矩阵每格(含 agree 格,D-11)、每条 F-CON 证据字段、配方引用
```markdown
单行证据 `path:line @ 5927f36`;多行证据 `path:10-25 @ 5927f36`。
证据一律提取自 `git show 5927f36:<path>`,禁止以工作树文件充当行号证据。
```

### 秘密类证据红线
**Source:** CHARTER.md:104
**Apply to:** 全部产物文档
```markdown
引用秘密类证据只写 `path:line @ 5927f36` + 模式名…,绝不复制值本体——哪怕已过期。
```
(DNF-04 的写法是范例:"此处仅引用代码标识符名,不涉任何真实密钥值",DO-NOT-FIX.md:41)

### 负面清单(判定前置排除)
**Source:** DO-NOT-FIX.md DNF-01~04 + CHARTER.md:41-47 排除项表
**Apply to:** 矩阵四类判定与 F-CON 立项
- `issue-cedential` 域名(DNF-02)、STS 原始秘密下发(DNF-04)等已裁定故意设计,不得立 F-CON
- 不引入 `docs/fc-transcribe-design.md` 目标态对照(CHARTER 明文排除)
- chunk_total `null`↔`"0"`↔`None` 三段映射是文档化约定(audio.js:157 注释 + poller.py ManifestDraft docstring)——"diverge 指语义分歧,不是字面差异"(Pitfall 5)

### 显式负向记录("已检查,无发现")
**Source:** HYPOTHESES.md:67-69(Known Bugs 节先例)
**Apply to:** 普查章节每项"无新发现"结论、agree 行
```markdown
**已检查,无已知 bug 线索。** CONCERNS.md 原文:"None detected in application code" — …
本条为显式负向记录,不设 HYP 编号…,喂 RPT-08 的"已检查,无发现"显式行。
```

### 文档语言与头尾格式
**Source:** 全部 Phase 1 产物(CHARTER/HYPOTHESES/DO-NOT-FIX/findings 骨架)
**Apply to:** 三个仓库产物
中文正文 + 英文 ID/术语(RPT-09);头部 `# 标题` + `**Created:**` + 基线引用行;尾部 `---` + 一行斜体摘要(名称 + 日期 + 关键计数)。

### 阶段收尾零 diff 验证
**Source:** CHARTER.md:16-22
**Apply to:** 阶段最后一个 plan
```bash
git diff --stat 5927f36 -- apps/ scripts/ docs/   # 输出必须为空;结果记录在案
```
收尾时 `git status` 应只见 `.planning/` 变更(Pitfall 6:该命令不保护根文件)。

## No Analog Found

无。全部产物均有强分析物:矩阵/台账/配方的文档形态由 Phase 1 产物 + CHARTER schema + 用户锁定决策完全覆盖;配方伪代码的两侧测试骨架有仓库既有先例(pytest 桥接 + node:test);harness 配方已由 02-RESEARCH 实测给定。矩阵表格的具体列式排版属 Claude's discretion(CONTEXT),以 02-RESEARCH Pattern 1 为起点即可。

## Metadata

**Analog search scope:** `.planning/audit/`(Phase 1 产物)、`apps/worker/tests/`、`apps/miniprogram/test/`(@ 基线 5927f36)
**Files scanned:** 8 个 audit 文档 + 2 个测试文件(基线读取)
**Pattern extraction date:** 2026-07-04
