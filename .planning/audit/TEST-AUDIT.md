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

## 反向映射清单(D-09)

**定级规则(预置,供 04-08 引用):** 脆弱区无测试兜底的缺口,定级参照原发现严重度;无关联脆弱区的一般覆盖缺口,按 CHARTER LOW 锚点(『lint/typecheck/测试覆盖缺口』类)定级。

**行集与去重说明:** 行集 = Phase 2/3 全部 22 条 F-* 发现(F-CON-01~06、F-CODE-01~08、F-TOOL-01~08)。CONTRACT-MATRIX 全部 12 个非 agree 格(组① 行 2/4/5/13、组② 行 35-41、组③ 行 46)经与既有 F-CON 去重核对,已由 F-CON-01~06 完整承载(对账依据:CONTRACT-MATRIX §机械对账第 3 条——12 格 = 5 条 × 1 格 + F-CON-05 × 7 格),矩阵追加行数 = 0。

**图例:** 兜底列取值 = `文件:行号 @ 5927f36`(有关联测试)或『无』;缺口判定列取值 = 终态(参照原严重度 / 无缺口)或占位态(静读不可定判,待 04-07 逐面普审佐证后销号)。兜底初判方法:按原发现证据字段符号执行 `git grep -n '<符号>' 5927f36 -- apps/worker/tests apps/fc/tests apps/miniprogram/test`;发现正文已含兜底证据的直接反查引用。

| 条目 | 原严重度 | 应重点覆盖行为 | 现有测试兜底(@ 5927f36) | 缺口判定 |
|------|----------|----------------|--------------------------|----------|
| F-CON-01 | LOW | 小程序侧 fragment_id 非法日期(13 月/非闰 2-29 类)应被拒绝 | `apps/worker/tests/test_oss_admin.py:75`、`apps/worker/tests/test_ops.py:74`(仅 Worker 消费端拒绝断言);小程序 `apps/miniprogram/test/ids.test.js:65-79` 的 FRAGMENT_ID_RE 断言仅正样本,无非法日期样本 | 缺口参照原严重度 LOW |
| F-CON-02 | MEDIUM | preview key 目录日期须与 fragment_id 前缀一致(双入参不得产出错位 key) | 无(`git grep buildObjectKeyPreview` 测试零命中);AC#4『上传 key 用 FC 返回值』仅有间接锁定(`apps/miniprogram/test/uploader.test.js:37` 断言凭证 object_key 透传) | 缺口参照原严重度 MEDIUM |
| F-CON-03 | MEDIUM | key 反推应拒绝非法/非 .wav/错位 key(与 Worker None 行为对齐) | 无(`git grep fragmentIdFromObjectKey` 测试零命中) | 缺口参照原严重度 MEDIUM |
| F-CON-04 | LOW | verify-upload 对 `x-oss-meta-sha256` 的取舍应有测试面表达;Worker 重下环无告警面 | 现行三态行为锁定:`apps/fc/tests/test_head.py:16-45`;生产端 meta 写入锁定:`apps/miniprogram/test/ids.test.js:134`;sha256 校验缺失面无测试(§4.2 设计取舍) | 缺口参照原严重度 LOW |
| F-CON-05 | INFO | 错误码经 body.error 通用透传行为保持稳定 | `apps/miniprogram/test/uploader.test.js:47-50,92-97`(码字符串透传断言) | 无缺口(良性,INFO 维持) |
| F-CON-06 | LOW | 小程序上传前应有 50 MB 预检或镜像常量 | FC 侧上限字面锁定:`apps/fc/tests/test_issue_credential.py:142,151`;小程序侧 `git grep '52428800\|MAX_UPLOAD' -- apps/miniprogram/test` 零预检命中(仅 MAX_UPLOAD_RETRIES 无关命中) | 缺口参照原严重度 LOW |
| F-CODE-01 | LOW | process_plan 幂等判定职责边界(fragments_root 未用)不被误信 | `apps/worker/tests/test_poller.py:171-172,188-189`(仅锁定调用形态,不能检测形参未用) | 缺口参照原严重度 LOW |
| F-CODE-02 | MEDIUM | 持久失败对象应有失败计数/隔离/告警(重复轮次不无界) | 单轮行为锁定:`apps/worker/tests/test_poller.py:182-191`(sha 失配删 .part)、`apps/worker/tests/test_pipeline.py:293`(失配无 .done)、`apps/worker/tests/test_audio.py:215`(探测失败留档);多轮重复/计数缺失面静读未见断言 | 补证中 |
| F-CODE-03 | LOW | fragment 目录内 mkstemp 孤儿 `*.tmp` 应有清理/检出路径 | 正常路径无残留锁定:`apps/worker/tests/test_recovery.py:47-53`;孤儿清理路径无测试(功能缺失) | 缺口参照原严重度 LOW |
| F-CODE-04 | LOW | `.env` 向上搜索应有仓库边界(或与文档口径一致) | 正向解析锁定:`apps/worker/tests/test_skeleton.py:52-58`;无界搜索行为无测试 | 缺口参照原严重度 LOW |
| F-CODE-05 | LOW | STS 签发与上游调用应有频控/配额面 | 无(功能缺失;`apps/fc/tests` 无频控/计数相关断言) | 缺口参照原严重度 LOW |
| F-CODE-06 | MEDIUM | uploading 残留项应有自动复位或手动出口 | 现行死态行为被正向锁定:`apps/miniprogram/test/uploads_view.test.js:70`(断言 uploading 不计积压)、`apps/miniprogram/test/uploader.test.js:84`(uploading 先落盘);恢复路径无测试(功能缺失,修复需同步改既有断言) | 缺口参照原严重度 MEDIUM |
| F-CODE-07 | LOW | 四落点重试常量的字面/结构锁定应对称 | `apps/miniprogram/test/uploader.test.js:55-56`、`apps/miniprogram/test/verify.test.js:54-55`(JS 字面锁定);`apps/worker/tests/test_nls.py:401,449-450`(结构锁定,数值字面无断言)——发现正文内已列,反查引用 | 缺口参照原严重度 LOW |
| F-CODE-08 | LOW | utils/pages 两份 FC 请求组装应有同步断言或共享源 | uploads 页参照实现有单测:`apps/miniprogram/test/uploader.test.js:11`(加载 pages/uploads/uploads.js);queue_runtime 编排有测试:`apps/miniprogram/test/redesign_view.test.js:146`;两份组装的同步断言静读未见 | 补证中 |
| F-TOOL-01 | LOW | 反例异常应三分(意外成功/拒绝/探测失败)不误报越权 | 现行二分行为锁定:`apps/worker/tests/test_verify_prep.py:234-251`;error_code 渲染缺失面无测试(功能缺失) | 缺口参照原严重度 LOW |
| F-TOOL-02 | LOW | 非首次部署备份失败应阻断(或显式 --force) | 首次部署跳过备份锁定:`apps/worker/tests/test_fc_deploy.py:331`;非首次备份失败不阻断面无区分测试 | 缺口参照原严重度 LOW |
| F-TOOL-03 | LOW | 清理失败应报告残留 key 不静默吞并 | 清理成功路径锁定:`apps/worker/tests/test_verify_upload_live.py:202-203,221-223`;失败吞并分支无测试 | 缺口参照原严重度 LOW |
| F-TOOL-04 | LOW | 小程序 JS 语义类静态门禁应存在 | 现有五族规则锁定:`apps/worker/tests/test_miniprogram_lint.py:53-180`;语义规则面无(功能缺失) | 缺口参照原严重度 LOW |
| F-TOOL-05 | MEDIUM | scripts/ 应有签名 URL/秘密模式静态门禁 | 无(scripts/ 零测试零门禁;原发现证据 `scripts/test_asr.py:79-81` 签名 URL 模式 + 签名参数模式,值本体略,per CHARTER 秘密红线) | 缺口参照原严重度 MEDIUM |
| F-TOOL-06 | MEDIUM | typecheck 门禁应可绿(退出码二值信号有效) | 无(门禁自身无测试;实跑证据见 `scans/gates-baseline.md` #1) | 缺口参照原严重度 MEDIUM |
| F-TOOL-07 | LOW | Makefile 声明面与实现面应一致(.PHONY 无幻影目标) | 无(Makefile 无对账测试) | 缺口参照原严重度 LOW |
| F-TOOL-08 | LOW | 联调工具契约镜像应有跨侧一致性测试绑定 | 自侧行为有测试:`apps/worker/tests/test_fc_live.py:105-112,126`(镜像常量自证消费);跨侧绑定断言无(发现自证『全集群零测试断言』) | 缺口参照原严重度 LOW |

**机械对账:** 行总数 = 22 条 F-* + 0 条矩阵追加 = 22;缺口判定分布 = 终态 20(参照原严重度 19 + 无缺口 1)+ 占位态 2(F-CODE-02、F-CODE-08,待 04-07 逐面普审销号);22 = 20 + 2 ✓
