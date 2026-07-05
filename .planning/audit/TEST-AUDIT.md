# TEST 覆盖台账与反向映射清单

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本文档是 Phase 4 TEST 维度(AUDIT-04)的覆盖台账与反向映射清单——证据与判断分离,本文件只登记对象/深度/已过面/线索,发现正文入 findings/test.md(判断层);本文件不承载任何 F-TEST 条目正文。取证纪律:证据一律提取自 `git show 5927f36:<path>` / `git grep -n <pat> 5927f36`,worktree 副本仅供执行(实跑),禁以工作树内容为静态取证依据。

> **worktree 执行区备注:** 测试实跑证据见 `scans/gate-run-worktree.md` 与 `scans/coverage-*.md`(04-01/04-02 产出)。执行环境重建命令:`git worktree add <scratchpad>/wt-5927f36 5927f36` + `uv sync --frozen`(scratchpad 为会话临时目录,仓库外)。

## 质量检查面清单(D-10 定稿,8 面)

以下 8 面为全阶段"已过面 N/8"的分母定义(04-07 逐模块逐面过账);每面锚定 CHARTER 严重度锚点或既有发现关联:

| # | 关注面 | 锚点/关联 | 仪器辅助信号 |
|---|--------|-----------|--------------|
| 1 | 断言强度:结果值断言 vs 仅『不抛异常』/存在性弱断言 | 缺口面属 CHARTER LOW『测试覆盖缺口』类 | 人工逐模块;`assert.ok`/裸 `assert` 密度可 grep 辅助 |
| 2 | fake 与真实实现漂移风险:手写 fake(FakeSource/FakeBackend/FakeApi 等)的行为是否有与真实 Protocol 实现对齐的锁定 | 潜伏失配类(CHARTER MEDIUM 同族) | TESTING.md『无 mock 框架,全手写 fake + DI』;fake 类清单 grep |
| 3 | 隔离与状态泄漏:tmp_path/环境变量/wx storage mock 是否互不污染,无 conftest 下的重复 setup 惯例 | 测试可信度基础面 | TESTING.md『无 conftest』;`monkeypatch.setenv` 分布 |
| 4 | 契约常量锁定:RETRY_DELAYS_SECONDS/RETRY_DELAYS_MS、错误码字符串(INVALID_CODE 等)、object key 格式等镜像常量是否在双语言测试中被字面断言 | CONTRACT-MATRIX 组③、F-CON 系、F-CODE-07/F-TOOL-08 | `git grep` 字面值断言命中 |
| 5 | 秘密泄漏断言:输出/日志/repr 无秘密断言的覆盖面 | CHARTER 秘密红线;test_config.py 泄漏断言先例 | `not in repr/stdout` 断言模式 grep |
| 6 | 静默 skip 路径:skipif/条件跳过使测试静默不跑 | D-11 门禁完整性输入;已知线索 `apps/worker/tests/test_miniprogram_js.py:24 @ 5927f36` | `skipif`/`skip` grep |
| 7 | 错误路径与边界覆盖:失败分支/异常路径是否有测试 | F-CODE 系脆弱区(F-CODE-02/03/06 等) | `pytest.raises` 分布;失败注入 fake 配置 |
| 8 | 测试与生产耦合:私有函数直测、对内部实现细节的脆弱耦合 | 重构脆性观察 | `_` 前缀符号在测试内的直引 grep |

## 逐对象台账(41 个测试模块)

对象清单以 `git ls-tree -r --name-only 5927f36 apps/worker/tests apps/fc/tests apps/miniprogram/test` 过滤 `test_*.py` 与 `*.test.js` 枚举——实测 41(worker 24 + fc 7 + node 10),与预期一致。行数为 `git show 5927f36:<path> | wc -l` 实测值;深度/已过面/产出三列由 04-07 回填(已过面初始 `0/8`,产出初始 `-`);备注列预置既有发现的已知线索,供 04-07 过账起点。

| 路径 | 行数 | 侧 | 深度 | 已过面 | 产出 | 备注 |
|------|------|-----|------|--------|------|------|
| `apps/worker/tests/test_audio.py` | 321 | pytest-worker | - | 0/8 | - | 面⑦线索:转码/探测失败留档路径 :215(F-CODE-02 单轮证据) |
| `apps/worker/tests/test_config.py` | 208 | pytest-worker | - | 0/8 | - | 面⑤先例:test_secret_not_leaked_in_repr_and_summary |
| `apps/worker/tests/test_e2e.py` | 266 | pytest-worker | - | 0/8 | - | 真云编排逻辑的离线单测 |
| `apps/worker/tests/test_e2e_scenarios.py` | 209 | pytest-worker | - | 0/8 | - | — |
| `apps/worker/tests/test_fc_deploy.py` | 485 | pytest-worker | - | 0/8 | - | 面⑦线索::331 首次部署跳过备份分支(F-TOOL-02) |
| `apps/worker/tests/test_fc_live.py` | 381 | pytest-worker | - | 0/8 | - | 面④线索:镜像常量自证,零跨侧绑定(F-TOOL-08) |
| `apps/worker/tests/test_fixtures.py` | 244 | pytest-worker | - | 0/8 | - | 二进制夹具 manifest 校验 |
| `apps/worker/tests/test_latency.py` | 64 | pytest-worker | - | 0/8 | - | — |
| `apps/worker/tests/test_locks.py` | 64 | pytest-worker | - | 0/8 | - | — |
| `apps/worker/tests/test_manifest.py` | 303 | pytest-worker | - | 0/8 | - | 面⑦关注:落盘顺序/.done 时序 |
| `apps/worker/tests/test_miniprogram_js.py` | 36 | pytest-worker | - | 0/8 | - | JS 桥;面⑥已知线索 :24 skipif(node 缺失静默跳过) |
| `apps/worker/tests/test_miniprogram_lint.py` | 205 | pytest-worker | - | 0/8 | - | 现有五族规则锁定(F-TOOL-04 参照) |
| `apps/worker/tests/test_nls.py` | 544 | pytest-worker | - | 0/8 | - | 面④线索::401,449-450 重试常量结构锁定、数值字面无断言(F-CODE-07) |
| `apps/worker/tests/test_ops.py` | 330 | pytest-worker | - | 0/8 | - | :74 非法日期拒绝断言(F-CON-01 消费端) |
| `apps/worker/tests/test_oss_admin.py` | 200 | pytest-worker | - | 0/8 | - | :75 非法日期拒绝断言(F-CON-01 消费端) |
| `apps/worker/tests/test_pipeline.py` | 411 | pytest-worker | - | 0/8 | - | 面⑦线索::293 sha 失配无 .done(F-CODE-02 单轮证据) |
| `apps/worker/tests/test_poller.py` | 428 | pytest-worker | - | 0/8 | - | 面⑦线索::182-191 sha 失配删 .part(F-CODE-02);:171-172 process_plan 调用形态(F-CODE-01) |
| `apps/worker/tests/test_recovery.py` | 282 | pytest-worker | - | 0/8 | - | 面⑦线索::47-53 正常路径无 tmp 残留(F-CODE-03 参照) |
| `apps/worker/tests/test_retranscribe.py` | 303 | pytest-worker | - | 0/8 | - | — |
| `apps/worker/tests/test_skeleton.py` | 64 | pytest-worker | - | 0/8 | - | :52-58 .env 正向解析(F-CODE-04 参照);:39-49 直改 os.environ(面③线索) |
| `apps/worker/tests/test_sts_escape.py` | 130 | pytest-worker | - | 0/8 | - | 面⑤:报告不泄漏 AK Secret 断言(docstring 自述) |
| `apps/worker/tests/test_transcriber.py` | 158 | pytest-worker | - | 0/8 | - | — |
| `apps/worker/tests/test_verify_prep.py` | 438 | pytest-worker | - | 0/8 | - | 面⑦线索::234-251 check_sts_escape 二分行为锁定(F-TOOL-01) |
| `apps/worker/tests/test_verify_upload_live.py` | 276 | pytest-worker | - | 0/8 | - | 面⑤泄漏反查先例;:202-223 清理成功路径(F-TOOL-03 参照) |
| `apps/fc/tests/test_custom_runtime_app.py` | 57 | pytest-fc | - | 0/8 | - | — |
| `apps/fc/tests/test_fc_handlers.py` | 133 | pytest-fc | - | 0/8 | - | — |
| `apps/fc/tests/test_fc_shared.py` | 270 | pytest-fc | - | 0/8 | - | :196 is_sensitive 白名单断言(面⑤) |
| `apps/fc/tests/test_head.py` | 93 | pytest-fc | - | 0/8 | - | :16-45 verify 三态行为锁定(F-CON-04 参照) |
| `apps/fc/tests/test_issue_credential.py` | 229 | pytest-fc | - | 0/8 | - | 面④线索::142,151 上限 52428800 字面锁定(F-CON-06 FC 侧) |
| `apps/fc/tests/test_sts.py` | 163 | pytest-fc | - | 0/8 | - | 单 key policy 断言(HYP-09/17 关联) |
| `apps/fc/tests/test_verify_upload.py` | 203 | pytest-fc | - | 0/8 | - | — |
| `apps/miniprogram/test/chunking.test.js` | 220 | node | - | 0/8 | - | :168 FRAGMENT_ID_RE 正样本断言 |
| `apps/miniprogram/test/draft_confirm.test.js` | 208 | node | - | 0/8 | - | 手写 wx/Page mock 模式(面②③) |
| `apps/miniprogram/test/fault_injection.test.js` | 272 | node | - | 0/8 | - | — |
| `apps/miniprogram/test/ids.test.js` | 281 | node | - | 0/8 | - | :65-79 FRAGMENT_ID_RE 仅正样本(F-CON-01 缺口面);:134 meta sha256 写入锁定(F-CON-04 生产端) |
| `apps/miniprogram/test/interruption.test.js` | 197 | node | - | 0/8 | - | — |
| `apps/miniprogram/test/oss_sign.test.js` | 108 | node | - | 0/8 | - | 面⑤关注:签名派生链无秘密外泄 |
| `apps/miniprogram/test/redesign_view.test.js` | 213 | node | - | 0/8 | - | :146 queue_runtime.drive 编排测试(F-CODE-08 关联) |
| `apps/miniprogram/test/uploader.test.js` | 226 | node | - | 0/8 | - | 面④线索::55-56 重试常量字面锁定(F-CODE-07);:11 加载 uploads 页(F-CODE-08 参照实现);:47-50 错误码透传断言(F-CON-05) |
| `apps/miniprogram/test/uploads_view.test.js` | 288 | node | - | 0/8 | - | :70 断言 uploading 不计积压——现行死态行为正向锁定(F-CODE-06) |
| `apps/miniprogram/test/verify.test.js` | 351 | node | - | 0/8 | - | 面④线索::54-55 verify 重试常量字面锁定(F-CODE-07) |
