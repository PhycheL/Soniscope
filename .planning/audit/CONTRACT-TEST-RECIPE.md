# 黄金样本跨语言契约测试设计配方

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本配方为 CONTRACT-04 的条件产出(D-15 触发线:02-04 四类分布为 潜伏 2(F-CON-02/03)+ 覆盖洞 3(F-CON-01/04/06)+ 良性 1(F-CON-05)——存在非良性分歧,触发)。**仅设计不实现**:本阶段不落任何测试文件进 `apps/`(零 diff 硬约束);文中全部路径均为纸面建议,供修复里程碑直接开工。设计深度目标:修复里程碑拿到即可写代码,不用再设计(D-16)。

黄金样本集 = CONTRACT-MATRIX.md 附录 S-01~S-18 样本清单(D-07 → D-16 复用链);样本全部为合成数据(合成 ULID `01HZX3K8MN5PQR9TFB7AYWVCDE`、合成 deviceShortId `dev01a`,无任何真实 openid/凭证)。

## 1. 黄金样本文件 schema 与存放位置

**单一 JSON 真值源**,pytest 侧与 node:test 侧读同一个文件——任何一侧实现漂移都会以样本失配形式暴露。

- **建议路径(纸面):** `tests/contract/golden_samples.json`(与既有二进制 fixture 目录 `tests/audio/` 并列;两侧测试均从仓库根相对定位,pytest 用 `_REPO_ROOT`、node 用 `path.join(__dirname, '../../..')`,先例见 §3/§4)。
- **字段形态:** 键名沿用 `apps/miniprogram/test/oss_sign.test.js:1-50 @ 5927f36` 的 CRED/META 既有约定——`object_key` 同 CRED 键名;meta 样本(如需)用 `x-oss-meta-*` 全前缀键名(META 形态)。

```json
{
  "comment": "契约黄金样本单一真值源;来源 = CONTRACT-MATRIX.md 附录 S-01~S-18(@ 5927f36);全部合成数据",
  "fragment_id_samples": [
    {
      "id": "S-01",
      "fragment_id": "20260704T101500_dev01a_01HZX3K8MN5PQR9TFB7AYWVCDE",
      "expect": "accept",
      "expected_object_key": "recordings/2026-07-04/20260704T101500_dev01a_01HZX3K8MN5PQR9TFB7AYWVCDE.wav",
      "reject_kind": null,
      "note": "典型值"
    },
    {
      "id": "S-02",
      "fragment_id": "20261332T101500_dev01a_01HZX3K8MN5PQR9TFB7AYWVCDE",
      "expect": "reject",
      "expected_object_key": null,
      "reject_kind": "date",
      "js_regex_expect": true,
      "note": "非法日期(13 月 32 日)正则可过——F-CON-01 现状行为锁定"
    }
  ],
  "object_key_samples": [
    {
      "id": "S-14",
      "object_key": "recordings/2026-07-04/20260704T101500_dev01a_01HZX3K8MN5PQR9TFB7AYWVCDE.m4a",
      "worker_expect": null,
      "js_fourth_expect": "20260704T101500_dev01a_01HZX3K8MN5PQR9TFB7AYWVCDE",
      "note": "非 .wav key:Worker 拒(None),第四处照单全收——F-CON-03 现状行为锁定"
    }
  ]
}
```

- `expect`:`accept` / `reject`(FC/Worker 双侧同判——02-03 已实证 15 个 python 样本同收同拒)。
- `reject_kind`:`format` / `date`——断言拒绝类别,防"拒了但拒错原因"的假绿。
- `js_regex_expect`:JS 正则形状判定的**现状**预期(date 类样本为 `true`,即 F-CON-01 的放行现状;修复后翻转)。
- `js_fourth_expect`:第四处反推 `fragmentIdFromObjectKey` 的**现状**预期(修复 F-CON-03 后改为 `null`)。

## 2. 覆盖的契约要素

只覆盖非良性分歧涉及的要素 + 往返主链;每条引矩阵行与触发 F-CON:

| 矩阵行(组号+要素名) | 触发 F-CON | 样本(S-NN) | 断言内容 |
|----------------------|-----------|-------------|----------|
| 组① 行 1「fragment_id 格式正则」 | —(往返主链) | S-01, S-08~S-13, S-16, S-17 | 三处收拒同判(格式维度) |
| 组① 行 2「fragment_id 日期合法性校验」 | F-CON-01 | S-02, S-04(合法对照 S-03) | FC/Worker 拒(`reject_kind=date`);JS 正则现状放行锁定 |
| 组① 行 3「object key 模板」+ 行 6「.wav 固定扩展名」 | —(往返主链) | S-01, S-03, S-05, S-13, S-15 | FC/Worker 签发 key 逐字符相等且等于 `expected_object_key` |
| 组① 行 4「key 目录日期来源」 | F-CON-02 | S-06, S-07 | `buildObjectKeyPreview` 双入参错位产出目录≠前缀 key 的现状锁定;Worker 对等价 key 返回 None |
| 组① 行 5「key → fragment_id 反推」 | F-CON-03 | S-14, S-18 + 全部 accept 样本 | accept 样本往返等式 `fragment_id_from_key(key) == fragment_id`;S-14/S-18 Worker None vs 第四处 `js_fourth_expect` 现状锁定 |

**范围界定:** F-CON-04(组① 行 13,verify-upload 不读 sha256)与 F-CON-06(组③ 行 46,小程序无大小预检)为**单侧缺失型覆盖洞**——缺失侧没有可对照的既有实现,黄金样本跨语言断言无从落笔;修复落地后按本配方模式追加样本(F-CON-06 建议 SZ 系列 size 边界样本:`0` / `52428800` / `52428801`,pytest 侧断言 `parse_size`/`check_size`(`sts.py:76-99 @ 5927f36`),node 侧断言新增预检常量与 FC 默认值一致)。F-CON-05(组② 行 35-41)为良性,不纳入覆盖。

**现状行为锁定原则:** 对 F-CON-01/02/03 的分歧行为,测试断言**基线现状**(JS 放行/照单全收)并在断言旁注释"修复 F-CON-NN 后翻转此断言"——这样配方落地即绿、任一侧未察觉的漂移立即红、修复动作以翻转断言的方式显式过测试。

## 3. pytest 侧测试骨架(伪代码)

照 `apps/worker/tests/test_miniprogram_js.py:1-36 @ 5927f36` 桥接先例结构(subprocess 起 node、node 缺席 skip、显式文件清单),增加"读共享黄金样本 JSON → 逐样本断言往返等式"一步:

```python
# 建议路径:apps/worker/tests/test_contract_golden.py(纸面建议,本阶段不落文件)
"""共享黄金样本契约测试:FC/Worker/小程序 key 契约以单一 JSON 真值源锁定(F-CON-01/02/03 回归护栏)。"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SAMPLES_PATH = _REPO_ROOT / "tests" / "contract" / "golden_samples.json"


def _samples() -> dict[str, list[dict[str, object]]]:
    return json.loads(_SAMPLES_PATH.read_text(encoding="utf-8"))


def test_fc_worker_object_key_roundtrip_per_sample() -> None:
    # from fc_shared import sts as fc_sts          (pytest pythonpath 已含 apps/fc/shared)
    # from soniscope_worker import oss_admin, poller
    # for s in _samples()["fragment_id_samples"]:
    #     if s["expect"] == "accept":
    #         fc_key = fc_sts.object_key_for(s["fragment_id"])
    #         wk_key = oss_admin.object_key_for(s["fragment_id"])
    #         assert fc_key == wk_key == s["expected_object_key"]          # 组① 行 3/6
    #         assert poller.fragment_id_from_key(fc_key) == s["fragment_id"]  # 往返等式,组① 行 5
    #     else:
    #         with pytest.raises(FcHttpError) as exc_fc: fc_sts.object_key_for(...)
    #         with pytest.raises(OssAdminError): oss_admin.object_key_for(...)
    #         # reject_kind == "date" → 断言消息含 "date";== "format" → 含 "format"(组① 行 1/2)
    ...


def test_worker_rejects_malformed_keys() -> None:
    # for s in _samples()["object_key_samples"]:   # S-14 / S-18
    #     assert poller.fragment_id_from_key(s["object_key"]) is None      # worker_expect
    ...


@pytest.mark.skipif(shutil.which("node") is None, reason="node 不可用,跳过 JS 侧黄金样本测试")
def test_js_contract_golden() -> None:
    # 显式文件清单(非目录)——node --test <dir> 会把目录当模块加载(桥接先例注释)
    files = [str(_REPO_ROOT / "apps" / "miniprogram" / "test" / "contract_golden.test.js")]
    result = subprocess.run(
        ["node", "--test", *files],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
```

先例要点保真:① `@pytest.mark.skipif(shutil.which("node") is None, ...)` node 缺席 skip;② 显式文件清单而非目录;③ `_REPO_ROOT` 相对定位;④ 全函数 `-> None` 注解(mypy strict,`apps/worker/tests` 在 strict 范围内)。

## 4. node:test 侧测试骨架(伪代码)

照 `apps/miniprogram/test/oss_sign.test.js @ 5927f36` 文风(zero-dep CommonJS require、中文测试名、`function () {}` 风格);模块级样本常量改为读同一 JSON:

```javascript
// 建议路径:apps/miniprogram/test/contract_golden.test.js(纸面建议,本阶段不落文件)
const test = require('node:test')
const assert = require('node:assert')
const fs = require('node:fs')
const path = require('node:path')

const audio = require('../utils/audio')
const queue = require('../utils/upload_queue')

// 与 pytest 侧读同一份真值源(单一 JSON,见配方 §1)
const SAMPLES = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', '..', '..', 'tests', 'contract', 'golden_samples.json'), 'utf8')
)

test('黄金样本:FRAGMENT_ID_RE 收拒与 FC/Worker 同判(格式维度;date 类样本为 F-CON-01 现状锁定)', function () {
  SAMPLES.fragment_id_samples.forEach(function (s) {
    const want = s.reject_kind === 'date' ? s.js_regex_expect /* 现状 true;修复 F-CON-01 后翻转 */
                                          : s.expect === 'accept'
    assert.strictEqual(audio.FRAGMENT_ID_RE.test(s.fragment_id), want, s.id)
  })
})

test('黄金样本:buildObjectKeyPreview 同 recordedAt 下与 expected_object_key 逐字符相等(组① 行 3/4)', function () {
  // 对 accept 样本:以 fragment_id 前缀日期构造 recordedAt,断言产出 === expected_object_key
  // S-07 错位样本:断言现状产出目录≠前缀(修复 F-CON-02 后翻转为单一来源推导)
})

test('黄金样本:fragmentIdFromObjectKey 现状行为锁定(S-14/S-18 照单全收;修复 F-CON-03 后改断 null)', function () {
  SAMPLES.object_key_samples.forEach(function (s) {
    assert.strictEqual(queue.fragmentIdFromObjectKey(s.object_key), s.js_fourth_expect, s.id)
  })
})
```

时区注意(02-03 Pitfall 2 先例):涉 `recordedAt` 的断言须对 TZ 不敏感(从 fragment_id 前缀构造本地 Date),或在修复里程碑的 CI 说明中固定 `TZ` 双跑——配方推荐前者,使 `make test` 单命令在任意 TZ 稳定。

## 5. make 接入点与验收标准

**接入方式(零 Makefile 改动,经既有桥接先例):**

- pytest 侧文件落 `apps/worker/tests/`——根 `pyproject.toml` 的 `testpaths` 已含该目录,自动进 `make test` 单一质量门。
- node:test 侧文件落 `apps/miniprogram/test/`——既有桥 `test_miniprogram_js.py::_test_files()` glob `*.test.js` 自动收编(`test_miniprogram_js.py:20-21 @ 5927f36`);§3 的 `test_js_contract_golden` 显式清单为可选的独立入口(便于单独跑契约断言),两者不冲突。
- 黄金样本 JSON 落 `tests/contract/`——新目录,不触碰审计排除区,亦不进任何扫描门禁。

**验收标准:**

1. `make test` 全绿:黄金样本 S-01~S-18 逐样本通过(含现状行为锁定断言);
2. 漂移即红:任一侧实现改动(FC `sts.py` / Worker `oss_admin.py`/`poller.py` / 小程序 `audio.js`/`upload_queue.js`)导致与样本失配时,对应测试失败并报出样本 ID;
3. 修复联动:修复 F-CON-01/02/03 时按骨架内注释翻转对应断言,翻转后 `make test` 仍全绿——断言翻转即修复完成的可机械验收信号;
4. 单一真值源:两侧测试不得内联复制样本值,一律读 `golden_samples.json`(防第四份字面量漂移,呼应 D14-3 教训)。

## 6. 样本值(S-NN 复用,D-07 → D-16 复用链)

样本值**逐一复用** CONTRACT-MATRIX.md『附录:往返校验样本清单』的 S-01~S-18(每样本注明来源 ID,预期三格与实测已在矩阵附录闭合销号):

| JSON 归属 | 来源 ID | 说明 |
|-----------|---------|------|
| `fragment_id_samples` | S-01(典型)、S-02(13月32日)、S-03(合法闰日)、S-04(非闰 2/29)、S-05(跨年)、S-08~S-10(deviceShortId 边界)、S-11~S-13(ULID 边界)、S-15(chunk 同形)、S-16/S-17(空/畸形) | `expect`/`reject_kind` 取矩阵附录预期列;S-02/S-04 附 `js_regex_expect: true` 现状锁定 |
| `object_key_samples` | S-14(`.m4a` key)、S-18(目录≠前缀 key) | `worker_expect: null` + `js_fourth_expect: <前缀 id>` 现状锁定 |
| 函数级场景(不进 JSON,直接写在测试内) | S-06(双 TZ 同瞬间)、S-07(双入参错位) | 依赖运行时构造 Date,以 fragment_id 前缀派生保持 TZ 无关(§4 时区注意) |

---
*黄金样本跨语言契约测试设计配方: 2026-07-05(D-15 触发:非良性分歧 5 条;覆盖矩阵组① 行 1-6 主链与 F-CON-01/02/03;样本复用 S-01~S-18;pytest+node:test 双骨架,make test 零改动接入;仅设计不实现)*
