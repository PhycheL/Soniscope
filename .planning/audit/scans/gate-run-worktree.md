# 扫描档案:离线门禁基线实跑(worktree 专区)

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

per D-01(分级执行口径:离线门禁可跑,真云目标 `make test-*`/`verify-*` 与被审脚本绝不执行)/ D-02(worktree 基线专区:全部实跑在仓库外基线专区进行,主工作区零触碰)/ D-11(门禁完整性三方对照:本档提供『实跑观测』方的 collected/passed/skipped 三计数与反事实 SKIP 证据)。全部计数照抄原始输出,本档只存档不判断——销号判断由 04-08 D-11 三方对照完成。

**工具版本:** uv 0.8.14 / git 2.23.0 / node v22.18.0 / pytest 9.1.1(专区 venv,Python 3.12.11 解释器)

## worktree 专区备注(仿 COVERAGE.md 基线导出备注)

- **建区命令原文(主仓 `/Volumes/Data/ProjectCode/my_soniscope` 内执行):** `git worktree add "$WT" 5927f36`,其中 `WT=<会话 scratchpad>/wt-5927f36`
- **专区绝对路径:** `/private/tmp/claude-501/-Volumes-Data-ProjectCode-my-soniscope/298eef3f-7232-4386-a700-f7db47f5da56/scratchpad/wt-5927f36`(detached HEAD @ 5927f36,`git worktree list` 已确认恰 1 条)
- **钉版说明:** 专区内以 `uv sync --frozen` 装依赖(= `make install` 的钉版等价形式,防 uv.lock 漂移,Phase 3 gates-baseline.md 先例同款),**exit=0**
- **存续与重建:** 若会话更替致路径失效,按 `git worktree add <新路径> 5927f36` 重建即可(内容由基线 SHA 唯一决定);本专区由 04-02 覆盖率实测复用,用毕后 `git worktree remove --force` 拆除(本计划不拆区)
- **执行环境观测:** 实跑 shell 中 `SONISCOPE_HOME=<unset>`,专区位于 /private/tmp 下、上溯路径无 `.env`(与两条 FAILED 用例的 RuntimeHomeError 报错相关,见门禁实跑节注记)

## 门禁声称面实跑:make test(Makefile:170-171 @ 5927f36,实体命令 `uv run pytest`)

```bash
cd "$WT" && make test 2>&1 | tee <scratchpad>/gate-run-make-test.txt
```

**结果:exit=2,collected 567 / passed 565 / skipped 0**(failed 2;make 将 pytest exit 1 包装为 `make: *** [test] Error 1`)

```
================== 2 failed, 565 passed, 1 warning in 17.39s ===================
make: *** [test] Error 1
```

**FAILED 用例(照抄 short test summary):**

```
FAILED apps/worker/tests/test_retranscribe.py::test_run_retranscribe_config_missing
FAILED apps/worker/tests/test_skeleton.py::test_cli_run_command_is_placeholder
```

**注记:** 两条 FAILED 的断言现场均含 `RuntimeHomeError('未设置 SONISCOPE_HOME。请先 export SONISCOPE_HOME=... 或在仓库根目录 .env 中写入 ...')`——本次实跑环境 `SONISCOPE_HOME` 未设置且专区上溯路径无 `.env`(见专区备注),门禁结果对执行环境存在依赖的现象照记;非绿结果按 CHARTER 正常定级,此处只存档不判断,销号判断由 04-08 D-11 对照完成。

## 计数观测 1:pytest -rs(skip 原因保留,D-11 三计数)

```bash
cd "$WT" && uv run --frozen pytest -rs 2>&1 | tee <scratchpad>/gate-run-rs.txt
```

**结果:exit=1,collected 567 / passed 565 / skipped 0**(failed 2,与 make test 同两条,末行汇总照抄)

```
collected 567 items
...
=================== 2 failed, 565 passed, 1 warning in 5.69s ===================
```

**注记:** 全程无任何 SKIPPED 行(skipped=0,`-rs` 下 skip 原因区为空);JS 桥 `apps/worker/tests/test_miniprogram_js.py` 在本机(node v22.18.0 存在)下**实际执行且 passed**(进度行 `apps/worker/tests/test_miniprogram_js.py .` @ 33%)。此处只存档不判断,销号判断由 04-08 D-11 对照完成。

## 计数观测 2:pytest --collect-only(collected 底数)

```bash
cd "$WT" && uv run --frozen pytest --collect-only -q 2>&1 | tail -5 | tee <scratchpad>/gate-run-collect.txt
```

**结果:exit=0,collected 567**

```
567 tests collected in 0.10s
```

**注记:** collected 底数 567 与 -rs 实跑收集数一致(565 passed + 2 failed + 0 skipped = 567 ✓)。此处只存档不判断,销号判断由 04-08 D-11 对照完成。

## lock 漂移观测(门禁行为证据)

```bash
git -C "$WT" status --porcelain
```

**结果:exit=0,输出为空**——`make test`(实体命令 `uv run pytest`,不带 `--frozen`)运行后专区内 uv.lock 未被改动,无任何 tracked 文件漂移。

**注记:** worktree 为一次性基线副本,漂移(若有)不污染主仓;本次观测无漂移。此处只存档不判断,销号判断由 04-08 D-11 对照完成。

## 反事实观测:node 缺失 → JS 桥 SKIP(D-11『全绿≠全跑』证据)

本机 node 存在,skip 不会自然发生,须人工剔除 node 复现。PATH 剔除配方原文(专区内执行):

```bash
UV_BIN=$(command -v uv)                       # /Users/bemied/.local/bin/uv
NODE_DIR=$(dirname "$(command -v node)")      # /usr/local/bin(与 uv 不同目录,无连带失效)
NEWPATH=$(echo "$PATH" | tr ':' '\n' | grep -vxF "$NODE_DIR" | paste -sd: -)
PATH="$NEWPATH" "$UV_BIN" run --frozen pytest apps/worker/tests/test_miniprogram_js.py -rs
```

**结果:exit=0,collected 1 / passed 0 / skipped 1**(剔除后 `command -v node` 确认无命中)

```
apps/worker/tests/test_miniprogram_js.py s                               [100%]
SKIPPED [1] apps/worker/tests/test_miniprogram_js.py:24: node 不可用，跳过小程序 JS 单元测试
============================== 1 skipped in 0.01s ==============================
```

**注记:** 观测与预期一致——node 缺失时 JS 桥测试静默 SKIPPED 且进程 exit 0;skipif 静态依据为 `apps/worker/tests/test_miniprogram_js.py:24 @ 5927f36` 的 `shutil.which("node") is None` 条件(skip 原因行自报同一行号)。此处只存档不判断,销号判断由 04-08 D-11 对照完成。

## 零 diff 快查(主仓执行)

```bash
git -C /Volumes/Data/ProjectCode/my_soniscope diff --stat 5927f36 -- apps/ scripts/ docs/
# 实际输出:(空)——PASS,实跑全程主工作区零触碰
```

**执行历史声明:** 全程仅执行白名单命令(`git worktree add`、`uv sync --frozen`、`make test`、`uv run --frozen pytest ...`、`git status`/`git diff` 只读观测);未执行任何 `make test-*`、`make verify-*`、`scripts/test_asr.py`、`scripts/fetch_test_fixtures.py` 调用。

*离线门禁实跑归档: 2026-07-05(命令 7 条;三计数 collected/passed/skipped 已采;反事实 SKIP 观测 1 次;worktree 专区存续待 04-02)*
