# 扫描档案:Python 覆盖率实测(worktree 专区,pytest-cov 临时注入)

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

per D-01(分级执行口径:仅白名单命令 pytest,真云目标 `make test-*`/`verify-*` 与被审脚本绝不执行)/ D-02(worktree 基线专区:全部实跑在仓库外基线专区 wt-5927f36 进行,主工作区零触碰)/ D-03(Python 覆盖率 = pytest-cov 命令行临时注入,`--with` 为 ephemeral overlay,不改 .venv 声明、不改 pyproject/uv.lock,零仓库配置写入)。全部数字照抄原始输出,本档只存档不判断——本档为 AUDIT-04 的纯输入证据,判断由 04-08 完成。

**Task 1 检查点确认记录:** pytest-cov 包合法性 blocking-human 检查点已于 2026-07-05 经用户人工核验(PyPI 页面确认归属 pytest-dev 官方组织,版本 7.1.0 与研究记录一致)并回复 "approved — 批准注入",首次 `uv run --with pytest-cov` 注入在获批后执行。

**工具版本:** uv 0.8.14 / pytest 9.1.1 / pytest-cov 7.1.0(底层 coverage 7.15.0)/ Python 3.12.11(专区 venv 解释器)

## 冒烟节:A1 口径验证(单文件先行)

```bash
cd "$WT" && uv run --frozen --with pytest-cov pytest apps/fc/tests/test_sts.py --cov=fc_shared --cov-report=term
```

**结果:exit=0,34 passed;覆盖表含 fc_shared 全部 9 个模块的数据行**(`apps/fc/shared/fc_shared/*.py` 逐行出数)。

**口径取定:** `--cov=fc_shared`(包名形式)对本 workspace 布局下经 pythonpath 导入的非安装包统计正常出数,A1 假设成立,**无需回退到路径形式 `--cov=apps/fc/shared`**。全量实测沿用 `--cov=soniscope_worker --cov=fc_shared` 双包名口径。

## 全量节:双包覆盖率实测

```bash
cd "$WT" && uv run --frozen --with pytest-cov pytest --cov=soniscope_worker --cov=fc_shared --cov-report=term-missing 2>&1 | tee <scratchpad>/coverage-pytest-raw.txt
```

**运行汇总(照抄):** collected 567 / 565 passed / 2 failed / 1 warning in 6.56s。2 条 FAILED(`test_retranscribe.py::test_run_retranscribe_config_missing`、`test_skeleton.py::test_cli_run_command_is_placeholder`)与 gate-run-worktree.md 门禁实跑观测为同两条(RuntimeHomeError:SONISCOPE_HOME 未设置,执行环境依赖现象照记),覆盖率采集不受影响,数字照抄。

**模块级行覆盖数字表(照抄 term-missing 输出的 Stmts/Miss/Cover 列):**

| Name | Stmts | Miss | Cover |
|------|-------|------|-------|
| apps/fc/shared/fc_shared/__init__.py | 11 | 0 | 100% |
| apps/fc/shared/fc_shared/audit.py | 24 | 0 | 100% |
| apps/fc/shared/fc_shared/auth.py | 22 | 0 | 100% |
| apps/fc/shared/fc_shared/env.py | 56 | 0 | 100% |
| apps/fc/shared/fc_shared/errors.py | 26 | 0 | 100% |
| apps/fc/shared/fc_shared/head.py | 55 | 19 | 65% |
| apps/fc/shared/fc_shared/http.py | 35 | 2 | 94% |
| apps/fc/shared/fc_shared/sts.py | 62 | 11 | 82% |
| apps/fc/shared/fc_shared/wechat.py | 28 | 4 | 86% |
| apps/worker/src/soniscope_worker/__init__.py | 1 | 0 | 100% |
| apps/worker/src/soniscope_worker/__main__.py | 5 | 5 | 0% |
| apps/worker/src/soniscope_worker/audio.py | 213 | 102 | 52% |
| apps/worker/src/soniscope_worker/cli.py | 316 | 196 | 38% |
| apps/worker/src/soniscope_worker/config.py | 74 | 5 | 93% |
| apps/worker/src/soniscope_worker/e2e.py | 146 | 4 | 97% |
| apps/worker/src/soniscope_worker/e2e_scenarios.py | 116 | 6 | 95% |
| apps/worker/src/soniscope_worker/fc_deploy.py | 417 | 103 | 75% |
| apps/worker/src/soniscope_worker/fc_live.py | 235 | 43 | 82% |
| apps/worker/src/soniscope_worker/fixtures.py | 104 | 27 | 74% |
| apps/worker/src/soniscope_worker/latency.py | 34 | 0 | 100% |
| apps/worker/src/soniscope_worker/locks.py | 28 | 0 | 100% |
| apps/worker/src/soniscope_worker/manifest.py | 175 | 80 | 54% |
| apps/worker/src/soniscope_worker/miniprogram_lint.py | 135 | 11 | 92% |
| apps/worker/src/soniscope_worker/nls.py | 336 | 133 | 60% |
| apps/worker/src/soniscope_worker/ops.py | 201 | 21 | 90% |
| apps/worker/src/soniscope_worker/oss_admin.py | 133 | 50 | 62% |
| apps/worker/src/soniscope_worker/paths.py | 68 | 14 | 79% |
| apps/worker/src/soniscope_worker/pipeline.py | 357 | 153 | 57% |
| apps/worker/src/soniscope_worker/poller.py | 257 | 42 | 84% |
| apps/worker/src/soniscope_worker/recovery.py | 238 | 18 | 92% |
| apps/worker/src/soniscope_worker/retranscribe.py | 267 | 45 | 83% |
| apps/worker/src/soniscope_worker/sts_escape.py | 137 | 52 | 62% |
| apps/worker/src/soniscope_worker/transcriber.py | 63 | 1 | 98% |
| apps/worker/src/soniscope_worker/verify_prep.py | 451 | 170 | 62% |
| apps/worker/src/soniscope_worker/verify_upload_live.py | 238 | 58 | 76% |
| **TOTAL** | **5064** | **1375** | **73%** |

**版本采集命令原文:** `uv --version`;`uv run --frozen --with pytest-cov pytest --version`;`uv run --frozen --with pytest-cov python -c "import importlib.metadata as m; print(m.version('pytest-cov'))"`。

**零写入核查(实跑后):** 主仓 `git status --porcelain -- pyproject.toml uv.lock apps/worker/pyproject.toml` 输出为空;专区 `git status --porcelain` 输出为空——ephemeral overlay 未触碰任何声明文件,D-03 零仓库写入成立。

## 口径备注

1. **JS 桥盲区(Pitfall 3,D-04 双侧分测原因):** pytest-cov 对 `apps/worker/tests/test_miniprogram_js.py` 子进程内运行的 node 完全盲——本表中 JS 侧无任何数据行属统计口径使然,并非 JS 侧无测试执行(该桥用例本次实跑 passed)。JS 侧数字见 `coverage-node.md`,两档口径互不重叠,双语言证据须成对引用。
2. **纯输入证据(成功判据 3):** 本档数字仅按模块罗列,不附带任何阈值判断或质量结论;term-missing 的 Missing 行号段列不入档(原始输出留存会话 scratchpad `coverage-pytest-raw.txt`,不入仓),销号与定级判断由 04-08 完成。
3. **措辞约束:** 本档归档措辞遵守阶段机械验收口径,不使用定性评价字样,数字自明。

*Python 覆盖率实测归档: 2026-07-05(冒烟 1 次 + 全量 1 次;模块数据行 35 条 = fc_shared 9 + soniscope_worker 26,另 TOTAL 1 行;命令与版本全部在档)*
