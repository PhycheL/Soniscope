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

对象清单以 `git ls-tree -r --name-only 5927f36 apps/worker/tests apps/fc/tests apps/miniprogram/test` 过滤 `test_*.py` 与 `*.test.js` 枚举——实测 41(worker 24 + fc 7 + node 10),与预期一致。行数为 `git show 5927f36:<path> | wc -l` 实测值;深度/已过面/产出三列已由 04-07 逐面普审回填完毕(41 行全部 8/8,产出/备注列非空);备注列含关键证据行号 @ 5927f36 与去向指针(→ F-TEST-NN / → D-11 / 反向映射;04-08 收口时产出列线索已反填终态 F-TEST 编号)。

| 路径 | 行数 | 侧 | 深度 | 已过面 | 产出 | 备注 |
|------|------|-----|------|--------|------|------|
| `apps/worker/tests/test_audio.py` | 321 | pytest-worker | 普审 | 8/8 | 面①/⑦线索:全文件零 pytest.raises,失败分支均以留档位置断言表达(断言面窄)→ F-TEST-10 | 面⑦ :215 转码/探测失败留档(F-CODE-02 单轮证据→反向映射);面③ tmp_path×16 全注入;面②⑤⑥⑧ grep 零命中 @ 5927f36 |
| `apps/worker/tests/test_config.py` | 208 | pytest-worker | 普审 | 8/8 | 无缺口线索 | 面⑤先例 :94-99 raw_secret not in repr/summary;面⑦ pytest.raises×3(收集式报错);面③ tmp_path×31/monkeypatch×5;面①强(38 断言零弱) @ 5927f36 |
| `apps/worker/tests/test_e2e.py` | 266 | pytest-worker | 普审 | 8/8 | 面①线索:编排结果多以 `assert code == 0` 表达(:149,173,217,250),报告内容值断言偏薄 → F-TEST-10 | 真云编排逻辑离线单测;面③ tmp_path×29;面⑥ 无 skip;面④ 无契约常量绑定(编排层,可接受) @ 5927f36 |
| `apps/worker/tests/test_e2e_scenarios.py` | 209 | pytest-worker | 普审 | 8/8 | 无缺口线索 | 面② FakeFcProbes/FakeStsProbes :47,72;面④ :34 ALLOWED_KEY key 格式字面 + 错误码字面 :63,132-133;面⑤ :181-188 report 无秘密断言 @ 5927f36 |
| `apps/worker/tests/test_fc_deploy.py` | 485 | pytest-worker | 普审 | 8/8 | 无新增线索(F-TOOL-02 已入反向映射) | 面⑦ :331 首次部署跳过备份分支(F-TOOL-02)+ raises×5;面② FakeFcApi :42;面⑤ :157 secret not in summary;面③ monkeypatch×8/tmp_path×67 @ 5927f36 |
| `apps/worker/tests/test_fc_live.py` | 381 | pytest-worker | 普审 | 8/8 | 无新增线索(F-TOOL-08 已入反向映射) | 面④ :51,105-126 错误码/key 镜像常量自证、零跨侧绑定(F-TOOL-08);面⑤ :124-126 STS 字段泄漏检出 + :325 报告无秘密;面② FakeProbes :55 @ 5927f36 |
| `apps/worker/tests/test_fixtures.py` | 244 | pytest-worker | 普审 | 8/8 | 无缺口线索 | 二进制夹具 manifest 校验;面⑦ raises×3;面③ tmp_path×26/monkeypatch×2;面①强(27 断言零弱) @ 5927f36 |
| `apps/worker/tests/test_latency.py` | 64 | pytest-worker | 普审 | 8/8 | 无缺口线索 | 面①强:pytest.approx 数值断言(:20-24 线性插值);面⑦ 空样本/超阈值失败分支 :47-56 全覆盖;纯函数无 IO @ 5927f36 |
| `apps/worker/tests/test_locks.py` | 64 | pytest-worker | 普审 | 8/8 | 无缺口线索 | 面⑦ LockBusyError 非阻塞互斥负例(fcntl 双 fd 实锁验证);面③ tmp_path×16 全注入;不同 fragment 独立性有断言 @ 5927f36 |
| `apps/worker/tests/test_manifest.py` | 303 | pytest-worker | 普审 | 8/8 | 面⑧线索:monkeypatch 直引私有 `_fixture_path`(:288,298)→ F-TEST-10(轻) | 面⑦ 落盘顺序/.done 时序核:5 产物齐全断言 :272-275(.done 0 字节)+ raises×2;面③ monkeypatch×2/tmp_path×3 @ 5927f36 |
| `apps/worker/tests/test_miniprogram_js.py` | 36 | pytest-worker | 普审 | 8/8 | 面⑥线索::24 skipif node 缺失→静默跳过全部 10 个 JS 测试(单点闸门)→ D-11 对照行 2 → F-TEST-04 | JS 桥;面① 仅 returncode==0 断言(:36,桥接性质透传 node 输出);面⑥ 为全 grep 唯一 skipif 命中 @ 5927f36 |
| `apps/worker/tests/test_miniprogram_lint.py` | 205 | pytest-worker | 普审 | 8/8 | 无新增线索(F-TOOL-04 已入反向映射) | 现有五族规则锁定 :53-180(F-TOOL-04);面⑤ :172-174 AK 模式(LTAI)检出正例;面③ tmp_path×32 @ 5927f36 |
| `apps/worker/tests/test_nls.py` | 544 | pytest-worker | 普审 | 8/8 | 面④线索:重试常量结构锁定 :401,449-450(sleeps==list(RETRY_DELAYS_SECONDS)),数值字面 5/15/45 无断言(F-CODE-07 已入反向映射 → F-TEST-05) | 面④ RESIGN_THRESHOLD_SECONDS :307 结构消费;面② _FakeBackend :58/_Clock :105 时钟注入;面⑦ raises×4 + 服务端/客户端异常分类 :455,466;面③ monkeypatch×4 @ 5927f36 |
| `apps/worker/tests/test_ops.py` | 330 | pytest-worker | 普审 | 8/8 | 无新增线索(F-CON-01 消费端已入反向映射) | :74 非法日期拒绝断言(F-CON-01);面④ :37-38,79 key 格式字面(`recordings/<date>/`);面② FakeSource :41;面③ tmp_path×37;面⑦ raises×2 @ 5927f36 |
| `apps/worker/tests/test_oss_admin.py` | 200 | pytest-worker | 普审 | 8/8 | 无新增线索(F-CON-01 消费端已入反向映射) | :75 非法日期拒绝断言(F-CON-01);面② FakeStore :21;面⑦ raises×2;面④ object_key_for 派生断言(生产端锁定) @ 5927f36 |
| `apps/worker/tests/test_pipeline.py` | 411 | pytest-worker | 普审 | 8/8 | 无新增线索(F-CODE-02 已入反向映射) | 面⑦ :293 sha 失配无 .done(F-CODE-02 单轮证据)+ :217-235 失败路径不建 .done(AC#2)+ :275 幂等跳过;零 pytest.raises 但失败经 .done 缺失断言表达(可接受);面③ tmp_path×24 @ 5927f36 |
| `apps/worker/tests/test_poller.py` | 428 | pytest-worker | 普审 | 8/8 | 面②线索:FakeSource(:52-76)与 RealOssSource 仅经 Protocol 结构对齐(mypy strict),行为面(网络错误语义/覆盖写语义)无对齐锁定 → F-TEST-08 | 面⑦ :182-191 sha 失配删 .part(F-CODE-02);:171-172 process_plan 调用形态(F-CODE-01);面④ key 反推拒绝负例(:80-89 非 .wav/错前缀);面③ tmp_path×30 @ 5927f36 |
| `apps/worker/tests/test_recovery.py` | 282 | pytest-worker | 普审 | 8/8 | 无新增线索(F-CODE-03 已入反向映射) | 面⑦ :47-53 正常路径无 tmp 残留(F-CODE-03 参照,孤儿清理路径无测试系功能缺失);面③ tmp_path×47 全注入;面①强(59 断言) @ 5927f36 |
| `apps/worker/tests/test_retranscribe.py` | 303 | pytest-worker | 普审 | 8/8 | 无缺口线索 | 面⑦ 幂等 skip 行为 :285-286 有锁定;面③ tmp_path×20/monkeypatch×1;面①强(52 断言) @ 5927f36 |
| `apps/worker/tests/test_skeleton.py` | 64 | pytest-worker | 普审 | 8/8 | 面③线索::39-49 直改 os.environ(try/finally 手工清理,与同文件 monkeypatch 惯例混用)→ F-TEST-10(轻);:33-35 无 SONISCOPE_HOME 注入 → D-11 对照行 6 → F-TEST-04 | :52-58 .env 正向解析(F-CODE-04 参照,无界搜索面无测试);面⑦ raises×1 @ 5927f36 |
| `apps/worker/tests/test_sts_escape.py` | 130 | pytest-worker | 普审 | 8/8 | 无缺口线索 | 面⑤ :110-114 report 无 `super-secret-do-not-log` 断言;面② FakeProbes :34;越权反例逻辑离线锁定 @ 5927f36 |
| `apps/worker/tests/test_transcriber.py` | 158 | pytest-worker | 普审 | 8/8 | 无缺口线索 | 面⑦ raises×2::68 未知 name→TranscriberError、:81 whisper-local→NotImplementedError(placeholder 行为锁定);面③ monkeypatch×1 @ 5927f36 |
| `apps/worker/tests/test_verify_prep.py` | 438 | pytest-worker | 普审 | 8/8 | 无新增线索(F-TOOL-01 已入反向映射) | 面⑦ :234-251 check_sts_escape 二分行为锁定(F-TOOL-01)+ raises×3;面⑤ :227 check_config_security 不泄密断言;面② FakeProbes :96;面③ monkeypatch×5/tmp_path×24 @ 5927f36 |
| `apps/worker/tests/test_verify_upload_live.py` | 276 | pytest-worker | 普审 | 8/8 | 无新增线索(F-TOOL-03 已入反向映射) | 面⑤ :51,58 泄漏检出断言(object info/verified true);:202-223 清理成功路径(F-TOOL-03,失败吞并分支无测试);面② FakeProbes :126 @ 5927f36 |
| `apps/fc/tests/test_custom_runtime_app.py` | 57 | pytest-fc | 普审 | 8/8 | 面⑧线索::57 直测私有 `_port()` → F-TEST-10(轻) | 面② fake handler 模块经 monkeypatch.setitem(sys.modules) 注入,application 委托行为锁定 :23-43;面③ monkeypatch×3(FC_SERVER_PORT 隔离) @ 5927f36 |
| `apps/fc/tests/test_fc_handlers.py` | 133 | pytest-fc | 普审 | 8/8 | 无缺口线索(HYP-23 补偿主承载,见专项节) | importlib 唯一模块名动态加载双 handler :41-45(绕开 mypy 豁免的行为级驱动);GET 存活 :83-85、缺 env 500 :92-101、非法 body 400 :106-114、403 :118-133 全部双 handler 参数化 @ 5927f36 |
| `apps/fc/tests/test_fc_shared.py` | 270 | pytest-fc | 普审 | 8/8 | 无缺口线索 | 面⑤ :185-188 hash_openid 非明文、:192-197 is_sensitive 白名单、:200-219 log_event 脱敏+None 省略;面④ :58,124 错误码字面锁定(`"INVALID_REQUEST"`/`"OPENID_NOT_ALLOWED"` 裸字符串);面⑦ raises×13 @ 5927f36 |
| `apps/fc/tests/test_head.py` | 93 | pytest-fc | 普审 | 8/8 | 无新增线索(F-CON-04 已入反向映射) | :16-45 verify 三态行为锁定(OBJECT_NOT_FOUND :17/SIZE_MISMATCH :25);面② stub 经 `_unwrap_to` :90-93 注入;面⑦ raises×2 @ 5927f36 |
| `apps/fc/tests/test_issue_credential.py` | 229 | pytest-fc | 普审 | 8/8 | 无新增线索(F-CON-06 已入反向映射) | 面④ :142,151 上限 52428800 字面锁定(F-CON-06 FC 侧);:122-137 单 key policy + `recordings/*` not in resource(最小权限负断言);面⑦ :215-228 签发失败 500 无泄漏(STS_ISSUE_FAILED);面③ monkeypatch×13 @ 5927f36 |
| `apps/fc/tests/test_sts.py` | 163 | pytest-fc | 普审 | 8/8 | 无缺口线索 | 单 key policy 断言(HYP-09/17 关联);面⑦ raises×5 + SIZE_EXCEEDED shared 级 :87;面①强(31 断言) @ 5927f36 |
| `apps/fc/tests/test_verify_upload.py` | 203 | pytest-fc | 普审 | 8/8 | 无缺口线索 | 面⑦ handler 级三态 :123-148(OBJECT_NOT_FOUND :130/SIZE_MISMATCH :144)+ :194-202 HeadObject 失败 500 无泄漏(HEAD_OBJECT_FAILED);面⑤ :175-188 伪造 code 不返回对象信息;面③ monkeypatch×6 @ 5927f36 |
| `apps/miniprogram/test/chunking.test.js` | 220 | node | 普审 | 8/8 | 无缺口线索 | HYP-24:加载 index 页 :17,105(Page harness);面④ :168 FRAGMENT_ID_RE 正样本断言(F-CON-01 同源);面③ require.cache 清理 :104 隔离惯例 @ 5927f36 |
| `apps/miniprogram/test/draft_confirm.test.js` | 208 | node | 普审 | 8/8 | 无缺口线索 | HYP-24:加载 index 页 :14,74;面②③ 手写 wx/Page mock(:69-74 loadPageConfig 模式),storage 每测新建对象隔离 @ 5927f36 |
| `apps/miniprogram/test/fault_injection.test.js` | 272 | node | 普审 | 8/8 | 无缺口线索 | HYP-24:加载 dev 页 :11,148,176,199 + uploads 页 :12,214-255;面⑦ 离线注入 queued 保持 :221-229、恢复自动上传 :230;面④ 开关名与 tech-spec §6.1 一致断言 :26;production 门控负例 :70-90,192 @ 5927f36 |
| `apps/miniprogram/test/ids.test.js` | 281 | node | 普审 | 8/8 | 无新增线索(F-CON-01/04 已入反向映射) | 面④ :65-79 FRAGMENT_ID_RE 仅正样本(F-CON-01 缺口面);:134 meta sha256 写入锁定(F-CON-04 生产端);HYP-24:加载 index 页 :19,211;面① assert.ok×13 多为存在性前置(可接受) @ 5927f36 |
| `apps/miniprogram/test/interruption.test.js` | 197 | node | 普审 | 8/8 | 无缺口线索 | HYP-24:加载 index 页 :13,53(harness 注释 :47);录音中断回调经 mock recorder 真实驱动(胶水层被驱动直接证据);面③ 每测清 require.cache + storage 注入 @ 5927f36 |
| `apps/miniprogram/test/oss_sign.test.js` | 108 | node | 普审 | 8/8 | 面⑤线索:秘密标记 `sts-secret-do-not-log`(:39)仅参与派生(:91),无『raw secret 不出现在表单/policy』负断言 → F-TEST-09 | 面④ :61-74 表单字段逐一强断言 + key=FC 返回值不被前端覆盖(AC#4);面①强(23 断言);纯函数无 IO @ 5927f36 |
| `apps/miniprogram/test/redesign_view.test.js` | 213 | node | 普审 | 8/8 | 无新增线索(F-CODE-08 已销号,见反向映射) | :146,163 queue_runtime.drive 编排(F-CODE-08);:126 FC URL 经 config 注入;面⑦ :169 缺 getNetworkType 视为离线负例 @ 5927f36 |
| `apps/miniprogram/test/uploader.test.js` | 226 | node | 普审 | 8/8 | 无新增线索(F-CODE-07/F-CON-05 已入反向映射) | 面④ :55-56 RETRY_DELAYS_MS=[5000,15000,45000]/MAX_UPLOAD_RETRIES=3 字面锁定(与 Python 5/15/45s 镜像,F-CODE-07)+ :47-50 错误码字面透传(F-CON-05);HYP-24:加载 uploads 页 :11,168;面⑦ 403 落盘 manual 状态 :199-206 @ 5927f36 |
| `apps/miniprogram/test/uploads_view.test.js` | 288 | node | 普审 | 8/8 | 无新增线索(F-CODE-06 已入反向映射) | :70 isBacklog('uploading')=false——现行死态行为正向锁定(F-CODE-06,修复需同步改此断言);HYP-24:加载 uploads 页 :11,222;面①强(57 断言零 assert.ok) @ 5927f36 |
| `apps/miniprogram/test/verify.test.js` | 351 | node | 普审 | 8/8 | 无新增线索(F-CODE-07 已入反向映射) | 面④ :54 VERIFY_RETRY_DELAYS_MS=[5000,15000,45000] 字面锁定(F-CODE-07)+ :48-50 INVALID_CODE 字面;HYP-24:加载 uploads 页 :11,236;面⑦ 重试穷尽→manual_verify 路径覆盖 @ 5927f36 |

## HYP-23 专项:FC handler 行为测试补偿事实清单

两个面向公网的 WSGI 入口 `handler.py` 处于 mypy strict 之外(DNF-03 豁免,本节不质疑豁免本身,仅登记行为测试补偿事实)。错误码全集以 `git show 5927f36:apps/fc/shared/fc_shared/errors.py` 实际枚举为准 = **9 个**(计划预列 7 个,另有 INVALID_REQUEST、HEAD_OBJECT_FAILED 两码,以实际枚举为准):

| 错误码(errors.py 行号) | fc/tests 行为覆盖(@ 5927f36) | handler 入口级驱动 |
|--------------------------|-------------------------------|---------------------|
| INVALID_CODE(:13) | 有:`test_fc_shared.py:163`、`test_issue_credential.py:187,196`、`test_verify_upload.py:180,188` | 是(伪造 code POST 双 handler) |
| OPENID_NOT_ALLOWED(:14) | 有:`test_fc_handlers.py:133`、`test_fc_shared.py:121-124,264` | 是(双 handler 参数化 403) |
| INVALID_REQUEST(:15) | 有:`test_fc_handlers.py:114`、`test_fc_shared.py:56-58,77`、`test_issue_credential.py:164,210` | 是(非法 body POST 双 handler) |
| SIZE_EXCEEDED(:16) | 有:`test_issue_credential.py:150`、`test_sts.py:87` | 是(issue-credential 400) |
| SERVER_MISCONFIGURED(:17) | 有:`test_fc_handlers.py:101`、`test_issue_credential.py:178`、`test_verify_upload.py:171` | 是(缺 env 500 双 handler + 各自专属 env) |
| STS_ISSUE_FAILED(:18) | 有:`test_issue_credential.py:228`(500 且无泄漏) | 是 |
| HEAD_OBJECT_FAILED(:19) | 有:`test_verify_upload.py:202`(500 且无泄漏) | 是 |
| OBJECT_NOT_FOUND(:23) | 有:`test_head.py:17`、`test_verify_upload.py:130` | 是(verified:false 三态) |
| SIZE_MISMATCH(:24) | 有:`test_head.py:25`、`test_verify_upload.py:144` | 是(verified:false 三态) |

**handler 入口路径驱动证据:** 双 handler 经 importlib 唯一模块名动态加载后作为 WSGI callable 被真实调用(`test_fc_handlers.py:41-45,70 @ 5927f36`):GET 存活探针 `test_fc_handlers.py:83-85`;POST 主流程成功路径 `test_issue_credential.py:99-121`(完整 STS 四字段)与 `test_verify_upload.py:105-122`(verified:true);异常分支 `test_fc_handlers.py:92-133`(500/400/403)+ 两侧上游失败 500 无泄漏(`test_issue_credential.py:215-228`、`test_verify_upload.py:194-202`)。

**结论行:** 补偿覆盖面事实清单 = 9/9 错误码均有行为测试且全部在 handler 入口级被驱动;GET/POST 成功/异常分支三类入口路径均被测试驱动;`fc_shared`(逻辑下沉层)本身在 mypy strict 范围内 → HYP-23(04-09 回填锚点;充分性判断在回填时依此清单下,不质疑 DNF-03 豁免本身)。

## HYP-24 专项:pages 胶水层加载边界事实

**检索方法备注:** 字面模式 `git grep "require.*pages/" 5927f36 -- apps/miniprogram/test` 为**零命中**——页面加载一律经 `path.resolve` 变量 + `require(INDEX_PAGE)` 形态,须以变量形态检索(`git grep "pages/"` 命中 10 处路径常量定义 + `require(<VAR>)` 8 处)。

**加载矩阵(app.json 注册 3 页,全部被 node 测试真实加载,@ 5927f36):**

| 页面 | 行数 | 加载测试(定义行,require 行) |
|------|------|------------------------------|
| `pages/index/index.js` | 796(`git show 5927f36:... \| wc -l` 实测) | `chunking.test.js:17,105`;`draft_confirm.test.js:14,74`;`ids.test.js:19,211`;`interruption.test.js:13,53` —— 4 文件均为 Page harness 模式(global.Page 捕获配置 + mock wx + require.cache 清理) |
| `pages/uploads/uploads.js` | — | `uploader.test.js:11,168`;`uploads_view.test.js:11,222`;`verify.test.js:11,236`;`fault_injection.test.js:12,214-255` |
| `pages/dev/dev.js` | — | `fault_injection.test.js:11,148,176,199` |

**边界事实:** `pages/index/index.js` **被测试加载**——HYP-24 假设前提『页面文件中的 wx-API 胶水层无自动化测试』与实态不符(TESTING.md 仅记 uploader.test.js 加载 uploads 页,漏记 index 页 4 处 harness 加载);但驱动为选择性:录音中断回调(interruption)、草稿确认(draft_confirm)、分片(chunking)、ID 生成(ids)四条流程的 handler 被 mock wx 驱动,796 行内其余胶水(如 showModal 流程、storage IO 全路径)的行覆盖比例无实测数据。

**结论行:** 页面级加载边界事实 = 3/3 注册页均被 node 测试真实加载;index.js(796 行)被 4 个测试文件经 Page harness 驱动(非『仅经抽出的纯 utils 模块测试』)→ HYP-24(04-09 回填锚点;coverage-node.md 的 pages/ 数据为实测佐证——04-02 已产出 `scans/coverage-node.md`,pages 三文件数据行在档:index.js 行 87.94% / 分支 67.62% / 函数 68.25%,uploads.js 行 89.66%,dev.js 行 95.00%,node experimental 标注连带;04-08 补引完毕,数字仅证据引用,判断入 F-TEST-02)。

## 反向映射清单(D-09)

**定级规则(预置,供 04-08 引用):** 脆弱区无测试兜底的缺口,定级参照原发现严重度;无关联脆弱区的一般覆盖缺口,按 CHARTER LOW 锚点(『lint/typecheck/测试覆盖缺口』类)定级。

**行集与去重说明:** 行集 = Phase 2/3 全部 22 条 F-* 发现(F-CON-01~06、F-CODE-01~08、F-TOOL-01~08)。CONTRACT-MATRIX 全部 12 个非 agree 格(组① 行 2/4/5/13、组② 行 35-41、组③ 行 46)经与既有 F-CON 去重核对,已由 F-CON-01~06 完整承载(对账依据:CONTRACT-MATRIX §机械对账第 3 条——12 格 = 5 条 × 1 格 + F-CON-05 × 7 格),矩阵追加行数 = 0。

**图例:** 兜底列取值 = `文件:行号 @ 5927f36`(有关联测试)或『无』;缺口判定列取值 = 终态(参照原严重度 / 无缺口)或占位态(静读不可定判,待 04-07 逐面普审佐证后销号)。兜底初判方法:按原发现证据字段符号执行 `git grep -n '<符号>' 5927f36 -- apps/worker/tests apps/fc/tests apps/miniprogram/test`;发现正文已含兜底证据的直接反查引用。

| 条目 | 原严重度 | 应重点覆盖行为 | 现有测试兜底(@ 5927f36) | 缺口判定 |
|------|----------|----------------|--------------------------|----------|
| F-CON-01 | LOW | 小程序侧 fragment_id 非法日期(13 月/非闰 2-29 类)应被拒绝 | `apps/worker/tests/test_oss_admin.py:75`、`apps/worker/tests/test_ops.py:74`(仅 Worker 消费端拒绝断言);小程序 `apps/miniprogram/test/ids.test.js:65-79` 的 FRAGMENT_ID_RE 断言仅正样本,无非法日期样本 | 缺口参照原严重度 LOW → F-TEST-05 |
| F-CON-02 | MEDIUM | preview key 目录日期须与 fragment_id 前缀一致(双入参不得产出错位 key) | 无(`git grep buildObjectKeyPreview` 测试零命中);AC#4『上传 key 用 FC 返回值』仅有间接锁定(`apps/miniprogram/test/uploader.test.js:37` 断言凭证 object_key 透传) | 缺口参照原严重度 MEDIUM → F-TEST-05 |
| F-CON-03 | MEDIUM | key 反推应拒绝非法/非 .wav/错位 key(与 Worker None 行为对齐) | 无(`git grep fragmentIdFromObjectKey` 测试零命中) | 缺口参照原严重度 MEDIUM → F-TEST-05 |
| F-CON-04 | LOW | verify-upload 对 `x-oss-meta-sha256` 的取舍应有测试面表达;Worker 重下环无告警面 | 现行三态行为锁定:`apps/fc/tests/test_head.py:16-45`;生产端 meta 写入锁定:`apps/miniprogram/test/ids.test.js:134`;sha256 校验缺失面无测试(§4.2 设计取舍) | 缺口参照原严重度 LOW → F-TEST-07 |
| F-CON-05 | INFO | 错误码经 body.error 通用透传行为保持稳定 | `apps/miniprogram/test/uploader.test.js:47-50,92-97`(码字符串透传断言) | 无缺口(良性,INFO 维持) |
| F-CON-06 | LOW | 小程序上传前应有 50 MB 预检或镜像常量 | FC 侧上限字面锁定:`apps/fc/tests/test_issue_credential.py:142,151`;小程序侧 `git grep '52428800\|MAX_UPLOAD' -- apps/miniprogram/test` 零预检命中(仅 MAX_UPLOAD_RETRIES 无关命中) | 缺口参照原严重度 LOW → F-TEST-05 |
| F-CODE-01 | LOW | process_plan 幂等判定职责边界(fragments_root 未用)不被误信 | `apps/worker/tests/test_poller.py:171-172,188-189`(仅锁定调用形态,不能检测形参未用) | 缺口参照原严重度 LOW → F-TEST-07 |
| F-CODE-02 | MEDIUM | 持久失败对象应有失败计数/隔离/告警(重复轮次不无界) | 单轮行为锁定:`apps/worker/tests/test_poller.py:182-191`(sha 失配删 .part)、`apps/worker/tests/test_pipeline.py:293`(失配无 .done)、`apps/worker/tests/test_audio.py:215`(探测失败留档);重复轮次锁定仅及成功路径:`test_pipeline.py:276,289`(.done 后仅下载一次/二轮跳过);失败对象多轮重复/计数面 `git grep '多轮\|failed_count\|attempt' 5927f36 -- <三文件>` 零命中,面⑦普审(test_poller/test_pipeline/test_e2e_scenarios 均 8/8)确认无断言 | 缺口参照原严重度 MEDIUM → F-TEST-06 |
| F-CODE-03 | LOW | fragment 目录内 mkstemp 孤儿 `*.tmp` 应有清理/检出路径 | 正常路径无残留锁定:`apps/worker/tests/test_recovery.py:47-53`;孤儿清理路径无测试(功能缺失) | 缺口参照原严重度 LOW → F-TEST-06 |
| F-CODE-04 | LOW | `.env` 向上搜索应有仓库边界(或与文档口径一致) | 正向解析锁定:`apps/worker/tests/test_skeleton.py:52-58`;无界搜索行为无测试 | 缺口参照原严重度 LOW → F-TEST-07 |
| F-CODE-05 | LOW | STS 签发与上游调用应有频控/配额面 | 无(功能缺失;`apps/fc/tests` 无频控/计数相关断言) | 缺口参照原严重度 LOW → F-TEST-07 |
| F-CODE-06 | MEDIUM | uploading 残留项应有自动复位或手动出口 | 现行死态行为被正向锁定:`apps/miniprogram/test/uploads_view.test.js:70`(断言 uploading 不计积压)、`apps/miniprogram/test/uploader.test.js:84`(uploading 先落盘);恢复路径无测试(功能缺失,修复需同步改既有断言) | 缺口参照原严重度 MEDIUM → F-TEST-06 |
| F-CODE-07 | LOW | 四落点重试常量的字面/结构锁定应对称 | `apps/miniprogram/test/uploader.test.js:55-56`、`apps/miniprogram/test/verify.test.js:54-55`(JS 字面锁定);`apps/worker/tests/test_nls.py:401,449-450`(结构锁定,数值字面无断言)——发现正文内已列,反查引用 | 缺口参照原严重度 LOW → F-TEST-05 |
| F-CODE-08 | LOW | utils/pages 两份 FC 请求组装应有同步断言或共享源 | uploads 页参照实现有单测:`apps/miniprogram/test/uploader.test.js:11,168`(加载 pages/uploads/uploads.js);queue_runtime 编排有测试:`apps/miniprogram/test/redesign_view.test.js:146,163`;面④/面⑧普审(两文件均 8/8)确认:两测试各驱动一份组装(uploader.test.js:68,92 mock requestSts;redesign_view.test.js:126 FC URL 经 config 注入),无任何跨份同步性断言或共享源绑定 | 缺口参照原严重度 LOW → F-TEST-05 |
| F-TOOL-01 | LOW | 反例异常应三分(意外成功/拒绝/探测失败)不误报越权 | 现行二分行为锁定:`apps/worker/tests/test_verify_prep.py:234-251`;error_code 渲染缺失面无测试(功能缺失) | 缺口参照原严重度 LOW → F-TEST-06 |
| F-TOOL-02 | LOW | 非首次部署备份失败应阻断(或显式 --force) | 首次部署跳过备份锁定:`apps/worker/tests/test_fc_deploy.py:331`;非首次备份失败不阻断面无区分测试 | 缺口参照原严重度 LOW → F-TEST-06 |
| F-TOOL-03 | LOW | 清理失败应报告残留 key 不静默吞并 | 清理成功路径锁定:`apps/worker/tests/test_verify_upload_live.py:202-203,221-223`;失败吞并分支无测试 | 缺口参照原严重度 LOW → F-TEST-06 |
| F-TOOL-04 | LOW | 小程序 JS 语义类静态门禁应存在 | 现有五族规则锁定:`apps/worker/tests/test_miniprogram_lint.py:53-180`;语义规则面无(功能缺失) | 缺口参照原严重度 LOW → F-TEST-07 |
| F-TOOL-05 | MEDIUM | scripts/ 应有签名 URL/秘密模式静态门禁 | 无(scripts/ 零测试零门禁;原发现证据 `scripts/test_asr.py:79-81` 签名 URL 模式 + 签名参数模式,值本体略,per CHARTER 秘密红线) | 缺口参照原严重度 MEDIUM → F-TEST-03 |
| F-TOOL-06 | MEDIUM | typecheck 门禁应可绿(退出码二值信号有效) | 无(门禁自身无测试;实跑证据见 `scans/gates-baseline.md` #1) | 缺口参照原严重度 MEDIUM → F-TEST-04 |
| F-TOOL-07 | LOW | Makefile 声明面与实现面应一致(.PHONY 无幻影目标) | 无(Makefile 无对账测试) | 缺口参照原严重度 LOW → F-TEST-07 |
| F-TOOL-08 | LOW | 联调工具契约镜像应有跨侧一致性测试绑定 | 自侧行为有测试:`apps/worker/tests/test_fc_live.py:105-112,126`(镜像常量自证消费);跨侧绑定断言无(发现自证『全集群零测试断言』) | 缺口参照原严重度 LOW → F-TEST-05 |

**机械对账(04-07 终态):** 行总数 = 22 条 F-* + 0 条矩阵追加 = 22;缺口判定分布 = 终态 22(参照原严重度 21 + 无缺口 1)+ 占位态 0(F-CODE-02、F-CODE-08 已由 04-07 逐面普审补证销号);22 = 22 + 0 ✓

## 门禁完整性三方对照(D-11)

**对照口径(结构先例:CONTRACT-MATRIX 行×列+判定列):** 声称 = 文档/Makefile help 文案层(AGENTS.md、`.planning/codebase/TESTING.md`、DOC-CLAIMS 销号行);静态配置 = `git show 5927f36:<path>` 提取的门禁配置实态;实跑观测 = `scans/gate-run-worktree.md`(04-01)与 `scans/coverage-*.md`(04-02)归档计数。判定列落终态;缺口候选行注去向(F-TEST 终态编号由收口反填)。

| # | 对照项 | 声称 | 静态配置 | 实跑观测 | 判定 |
|---|--------|------|----------|----------|------|
| 1 | pytest 套件范围 | `Makefile:170-171 @ 5927f36`(test 目标 = `uv run pytest`,help『pytest 单元测试(mock 云端依赖)』);`AGENTS.md:130,363 @ 5927f36`(make test 列为提交前最低质量门);DOC-CLAIMS DG-07 已 agree 销号(五目标实存同口径) | `pyproject.toml:56 @ 5927f36` testpaths = ["apps/worker/tests", "apps/fc/tests"];`pyproject.toml:58 @ 5927f36` pythonpath = ["apps/fc/shared"] | gate-run-worktree.md:collected 567 / passed 565 / failed 2 / skipped 0;`--collect-only` 底数 567 与 -rs 收集数一致 | **一致**(声称目标、静态 testpaths、实跑收集数三方吻合;2 条 FAILED 系执行环境依赖,单列行 6 判定) |
| 2 | JS 测试进门禁的路径 | `.planning/codebase/TESTING.md:15 @ 5927f36`(『so `make test` is the single quality gate』)、`:24`(『make test — includes JS tests via node』) | `apps/worker/tests/test_miniprogram_js.py:24 @ 5927f36` skipif `shutil.which("node") is None` → 静默 SKIP;pytest skip 不改退出码(exit 0) | 本机 node v22.18.0 存在时 JS 桥实际执行且 passed(gate-run-worktree.md -rs 观测,skipped 0);反事实剔除 node → collected 1 / skipped 1 / exit=0(gate-run-worktree.md 反事实观测节) | **缺口候选**(『全绿 ≠ 全跑』结构性缺口:node 缺失时 make test 全绿而 126 个 JS 用例 0 跑,声称『single quality gate 含 JS』落空)→ findings/test.md 立条 → F-TEST-04 |
| 3 | 静态门禁(lint/typecheck)范围 | `AGENTS.md:358-366 @ 5927f36`(make typecheck/lint/test 为提交前最低质量门,无范围限定语,全仓印象) | `pyproject.toml:32 @ 5927f36`(mypy files 仅 apps/ 四路径)、`pyproject.toml:50 @ 5927f36`(ruff src 仅 apps/ 四路径)、`Makefile:166-167 @ 5927f36`(lint 目标仅 `ruff check apps/`,行内注释自认『遗留 scripts/ 由各自 story 收口』) | 实害样本(移交证据,静态门禁自身无实跑面):test_asr.py 存在门禁规则集(E,F,I,UP,B)内违例 6 条(UP009×1/E501×4/B904×1,`scripts/test_asr.py:2,38,166,197,275,283 @ 5927f36`)与已提交签名 URL(OSS 签名 URL 模式,位置 `scripts/test_asr.py:80 @ 5927f36`,值本体不引),均在 make lint 全绿下入库 | **缺口候选**(scripts/ 在全部静态门禁之外且已有实害样本)→ findings/test.md 立条 → F-TEST-03;销号引 HANDOFF-PHASE4.md TEST 节第 2 条(门禁范围静态证据);销号引 HANDOFF-PHASE4.md TEST 节第 3 条(实害样本) |
| 4 | 覆盖率门禁 | 无——`.planning/codebase/TESTING.md:129 @ 5927f36`『None enforced — no pytest-cov dependency, no coverage config』(声称面显式自认无门禁) | 仓库无任何覆盖率配置:`git grep -in 'cov' 5927f36 -- pyproject.toml Makefile apps/worker/pyproject.toml` 零命中;无 coverage 相关 make 目标 | `scans/coverage-pytest.md` 与 `scans/coverage-node.md` 均系本审计临时注入所得(pytest-cov ephemeral `--with` / node `--experimental-test-coverage`),非任何门禁产物 | **一致**(『无覆盖率门禁』三方自洽的事实行)——不立条理由:声称与实态无落差且声称面显式自认;覆盖率数字用途限 F-TEST 证据引用(成功判据 3) |
| 5 | 活体路径(test-fc-live 等) | `Makefile:50,57 @ 5927f36`(test-fc-live / test-verify-upload 目标存在;DOC-CLAIMS DG-13/FD-13 agree 销号在案) | `apps/worker/src/soniscope_worker/fc_live.py:15-16 @ 5927f36`(wx.login code 一次性,缺失场景标 SKIP)、`apps/worker/src/soniscope_worker/verify_upload_live.py:14 @ 5927f36`(缺 code 即 SKIP,docstring 自述『本地 CI 也能 exit 0』)——全部真实鉴权/签发/校验场景依赖手工传入一次性 code | 不适用——真云目标绝不执行(D-01);本行判定口径 = 静态 + 移交证据判定 | **缺口候选**(活体路径零自动化覆盖:无 CI,本地缺 code 即全 SKIP 且 exit 0)→ findings/test.md 立条 → F-TEST-01;销号引 HANDOFF-PHASE4.md TEST 节第 1 条 |
| 6 | 门禁结果的执行环境依赖 | `AGENTS.md:358-364 @ 5927f36`(make test 为提交前最低质量门,门禁说明层无执行环境预置前提;SONISCOPE_HOME 预置属运行时文档口径) | `apps/worker/tests/test_skeleton.py:33-35 @ 5927f36`(invoke `run` 无 SONISCOPE_HOME 注入,依赖环境实态)、`apps/worker/tests/test_retranscribe.py:268-280 @ 5927f36`(monkeypatch 仅及 load_config,SONISCOPE_HOME 解析在其上游不受隔离) | gate-run-worktree.md:make test exit=2 / failed 2,两条 FAILED 断言现场均含 RuntimeHomeError(实跑 shell `SONISCOPE_HOME=<unset>` 且上溯无 .env);coverage-pytest.md 全量实跑同两条复现 | **缺口候选**(门禁结果对执行环境存在依赖:干净检出 + 未设 SONISCOPE_HOME 时 make test 非绿,门禁二值信号失真)→ findings/test.md 立条 → F-TEST-04 |

**HANDOFF TEST 3 条移交逐条销号:**

- 销号引 HANDOFF-PHASE4.md TEST 节第 1 条(HYP-22:fc_live/verify_upload_live 手工 code 依赖)→ 对照行 5 已消费,去向 F-TEST-01
- 销号引 HANDOFF-PHASE4.md TEST 节第 2 条(HYP-25:scripts/ 三文件在 mypy files 与 ruff src 之外,`pyproject.toml:32,50 @ 5927f36`、`Makefile:166-167 @ 5927f36`)→ 对照行 3 静态列已消费,去向 F-TEST-03
- 销号引 HANDOFF-PHASE4.md TEST 节第 3 条(HYP-25 实害样本:test_asr.py 6 条违例 + 已提交签名 URL 位置引用)→ 对照行 3 实跑/实害列已消费,去向 F-TEST-03

**机械对账行(D-11):** 对照项 6;判定分布 = 一致 2(行 1/4)+ 缺口候选 4(行 2/3/5/6);缺口候选去向 4/4 反填终态编号(行 2/6 → F-TEST-04;行 3 → F-TEST-03;行 5 → F-TEST-01);HANDOFF-PHASE4.md TEST 节 3 条移交全部显式销号(第 1 条 → 行 5;第 2/3 条 → 行 3)✓

## 总机械对账(04-08 收口)

- 台账:41 行 × 已过面 8/8(行计数等式沿 04-07 终态:`grep -c '^| \`apps/.*8/8'` = 41 = `grep -c '^| \`apps/'`)✓
- 反向映射:行总数 22 = 终态 22(缺口 21 行全部反填 F-TEST 编号 + 无缺口 1 行 F-CON-05)+ 占位 0 ✓
- 反向映射缺口归属等式:21 = F-TEST-03(1:F-TOOL-05)+ F-TEST-04(1:F-TOOL-06)+ F-TEST-05(7:F-CON-01/02/03/06 + F-CODE-07/08 + F-TOOL-08)+ F-TEST-06(6:F-CODE-02/03/06 + F-TOOL-01/02/03)+ F-TEST-07(6:F-CON-04 + F-CODE-01/04/05 + F-TOOL-04/07)✓
- 三方对照:对照项 6 = 一致 2 + 缺口候选 4;缺口候选去向 4/4 已反填终态编号(F-TEST-01/03/04)✓
- F-TEST 立条与候选面处置等式:候选面 6 面全处置 = 立条去向 10 条 + 显式无发现 0 面(面 1 → F-TEST-01;面 2 证伪缩窄 → F-TEST-02;面 3 → F-TEST-03;面 4 → F-TEST-04;面 5 按共同根因拆 3 条 → F-TEST-05/06/07;面 6 聚合拆 3 条 → F-TEST-08/09/10);另有 2 处显式『已检查,无发现』记 findings/test.md 批次导语(D-11 对照行 4 覆盖率门禁、反向映射 F-CON-05)✓

*TEST 覆盖台账: 2026-07-05(41 模块 × 8 面;反向映射 22 行终态;三方对照 6 项;F-TEST 10 条;HYP-22/23/24/25 锚点齐备)*
