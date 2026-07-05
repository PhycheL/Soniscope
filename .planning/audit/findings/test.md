# 发现台账: 测试质量与覆盖 (TEST)

**Created:** 2026-07-04

本文件由 Phase 4 写入,ID 前缀 `F-TEST-NN`;schema 以 `.planning/audit/CHARTER.md` 为准。

### F-TEST-00: (schema 示例,非真实发现)

> 本条为 schema 示例,Phase 5 汇总时剔除。

- **维度:** 测试质量与覆盖 (TEST)
- **严重度:** (五级之一) — 影响:(一句场景语言);可能性:(一句触发条件)
- **证据:** `path:line @ 5927f36`(占位;从 `git show 5927f36:<path>` 提取)
  > (引用片段占位)
- **修复建议:** (一段占位)
- **工作量:** (S/M/L/XL 之一)
- **关联发现:** (F-XXX-NN 或 HYP-NN,无则写"无")
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

## 发现

> 04-08 判定产物(D-11 三方对照 + D-09/D-10 聚合):共 10 条发现——F-TEST-01(活体路径零自动化)、F-TEST-02(pages 选择性驱动)、F-TEST-03(scripts/ 门禁外+实害)、F-TEST-04(门禁二值信号无守护)、F-TEST-05(契约镜像无对称锁定,7 脆弱区共面)、F-TEST-06(失败/恢复路径无兜底,6 脆弱区共面)、F-TEST-07(低危功能缺失面测试同步义务,6 脆弱区共面)、F-TEST-08(fake 行为面无对齐锁定)、F-TEST-09(oss_sign 秘密负断言缺口)、F-TEST-10(断言强度与测试卫生杂项)。显式无发现清单:候选面『pages 胶水层无自动化测试』原表述经 04-07 HYP-24 专项证伪(3/3 注册页均被 node 测试真实加载),已检查,按实态缩窄为 F-TEST-02;D-11 对照行 4『无覆盖率门禁』三方自洽——已检查,无发现,不立条;反向映射 F-CON-05 行无缺口——已检查,无发现,不立条。HANDOFF-PHASE4.md TEST 节 3 条销号去向:第 1 条(HYP-22)→ F-TEST-01;第 2 条与第 3 条(HYP-25 ×2)→ F-TEST-03。

### F-TEST-01: 活体路径(真云鉴权/签发/校验)零自动化覆盖,缺一次性 code 即全 SKIP 且 exit 0

- **维度:** 测试质量与覆盖 (TEST)
- **严重度:** LOW — 影响:FC 联调与上传闭环的真云行为(STS 签发、HeadObject 校验、allowlist 拒绝)只能靠人工传入一次性 `wx.login` code 触发,发布前若跳过手工联调,真云回归完全失守而工具链不报任何异常(缺 code 场景标 SKIP、进程 exit 0);可能性:每次 FC/契约相关改动上线时暴露,仓库无 CI(无 `.github/`),执行全凭操作者自觉
- **证据:** `apps/worker/src/soniscope_worker/fc_live.py:15-16 @ 5927f36`、`apps/worker/src/soniscope_worker/verify_upload_live.py:14 @ 5927f36`
  > 『``wx.login`` code 是**一次性**的:每次调用 FC 都会消耗一个 code。…缺失的 code 对应场景标记为 SKIP。』(fc_live);『``wx.login`` code 一次性:每个需要 code 的场景缺 code 即标记 SKIP(本地 CI 也能 exit 0)。』(verify_upload_live)——TEST-AUDIT.md D-11 三方对照行 5 判定为缺口候选(实跑列不适用:真云目标绝不执行,静态+移交证据判定)
- **修复建议:** 短期把 `make test-fc-live` / `make test-verify-upload` 的执行与结果记录纳入发布清单为必过项(runbook 勾选项 + 输出留档);中期若引入 CI,因 wx.login code 一次性无法预置,可评估以测试环境专用凭证签发路径替代 code 依赖,使拒绝路径子集可自动回归
- **工作量:** S(发布清单化;测试凭证方案另计 M)
- **关联发现:** HYP-22(04-09 回填锚点);TEST-AUDIT.md D-11 对照行 5
- **上线判定:**
- **状态:** draft

### F-TEST-02: pages 胶水层为四条流程的选择性驱动,index.js 其余 wx 交互路径无自动化驱动

- **维度:** 测试质量与覆盖 (TEST)
- **严重度:** LOW — 影响:`pages/index/index.js`(796 行,录音主流程入口)中未被四条流程(chunking/draft_confirm/ids/interruption)harness 驱动的胶水路径(showModal 确认流、storage IO 全路径、录音权限分支等)回归依赖人工,改动该区域无测试变红信号;可能性:index.js 为主流程高频改动面,改动未驱动区域即触发
- **证据:** TEST-AUDIT.md『HYP-24 专项』节(3/3 注册页被真实加载;index.js 被 4 文件 Page harness 驱动,行号在档);行覆盖实测数字:`pages/index/index.js` 行 87.94% / 分支 67.62% / 函数 68.25%(scans/coverage-node.md 文件级数字表,node v22.18.0 experimental 标注连带)——数字仅作证据引用,该文件承载 HYP-24 边界事实中『其余胶水无行覆盖实测支撑』的缺口面
  > TEST-AUDIT.md HYP-24 边界事实:『驱动为选择性:…四条流程的 handler 被 mock wx 驱动,796 行内其余胶水(如 showModal 流程、storage IO 全路径)的行覆盖比例无实测数据』——实测数据现由 scans/coverage-node.md 补齐引用
- **修复建议:** 沿既有『node Page harness + mock wx』模式为 index.js 未驱动 handler 增补用例,以 coverage-node.md 的函数覆盖列为选取索引逐个补齐
- **工作量:** M(单页多 handler + mock wx 适配)
- **关联发现:** HYP-24(04-09 回填锚点)
- **上线判定:**
- **状态:** draft

### F-TEST-03: scripts/ 三文件在全部静态门禁之外,已有违例与已提交签名 URL 实害样本

- **维度:** 测试质量与覆盖 (TEST)
- **严重度:** MEDIUM — 影响:scripts/ 内代码变更不经任何静态检查即可入库,已实证门禁规则集(E,F,I,UP,B)内违例 6 条与 1 处已提交 OSS 签名 URL 在 make lint 全绿下入库——秘密类内容再次入库无任何工具检出面;可能性:任何人改动 scripts/ 即触发,实害样本已存在于基线(非假设场景)
- **证据:** `pyproject.toml:32,50 @ 5927f36`(mypy files 与 ruff src 均仅 apps/ 四路径)、`Makefile:166-167 @ 5927f36`(lint 目标仅 `ruff check apps/`,行内注释自认『遗留 scripts/ 由各自 story 收口』)
  > 违例位置:`scripts/test_asr.py:2,38,166,197,275,283 @ 5927f36`(UP009×1/E501×4/B904×1,逐条见 scans/gates-baseline.md #2-7);签名 URL:`scripts/test_asr.py:80 @ 5927f36`(OSS 签名 URL 模式,值本体不引,per CHARTER 秘密红线);`scripts/fetch_test_fixtures.py:42,103,108 @ 5927f36` 以 `# type: ignore`/`noqa` 自我豁免
- **修复建议:** 将 scripts/ 纳入 ruff src 与 mypy files(或先最小化:Makefile lint 目标追加 `ruff check scripts/`);把 miniprogram_lint 的秘密模式扫描(AK 模式/签名 URL 模式)扩展至 scripts/;清理 test_asr.py 既有违例并使已提交签名 URL 失效
- **工作量:** S(配置两处 + 违例清理单文件)
- **关联发现:** HYP-25(04-09 回填锚点)、F-TOOL-05(严重度参照该发现 MEDIUM;定级规则见 TEST-AUDIT.md 反向映射节首)
- **上线判定:**
- **状态:** draft

### F-TEST-04: make 门禁二值信号无守护——JS 桥静默 skip、typecheck 非绿、执行环境依赖三处失真

- **维度:** 测试质量与覆盖 (TEST)
- **严重度:** MEDIUM — 影响:三个独立失真点使门禁退出码不可信,『全绿 ≠ 全跑、非绿 ≠ 代码错』:①node 缺失时 126 个 JS 用例静默 0 跑且 exit 0(全绿假象,声称『single quality gate 含 JS』落空);②make typecheck 基线非绿使二值信号长期失效(F-TOOL-06);③未设 SONISCOPE_HOME 的干净环境 make test 非绿(2 条用例依赖环境实态),操作者无从区分代码错与环境错;可能性:①在无 node 的新机器/精简环境即触发;②基线当前即处该状态;③任何干净检出即复现(gate-run-worktree.md 已实证)
- **证据:** `apps/worker/tests/test_miniprogram_js.py:24 @ 5927f36`(skipif `shutil.which("node") is None`)
  > 反事实实跑:剔除 node 后 `collected 1 / skipped 1 / exit=0`(scans/gate-run-worktree.md 反事实观测节);环境依赖实跑:make test exit=2 / failed 2,断言现场均含 RuntimeHomeError(scans/gate-run-worktree.md);静态依赖面:`apps/worker/tests/test_skeleton.py:33-35 @ 5927f36`(invoke `run` 无 SONISCOPE_HOME 注入)、`apps/worker/tests/test_retranscribe.py:268-280 @ 5927f36`(monkeypatch 仅及 load_config,SONISCOPE_HOME 解析在其上游);typecheck 非绿本体见 F-TOOL-06 与 scans/gates-baseline.md #1
- **修复建议:** ①JS 桥把 node 缺失从 skip 改为 fail(或 make test 前置 `command -v node` 检查并显式报错);②按 F-TOOL-06 修复 typecheck 至可绿;③两条环境依赖用例以 monkeypatch 注入 SONISCOPE_HOME(或显式隔离解析链),使 make test 在干净环境可绿
- **工作量:** S(三处均单文件粒度;typecheck 修复工作量随 F-TOOL-06)
- **关联发现:** F-TOOL-06(严重度参照该发现 MEDIUM;定级规则见 TEST-AUDIT.md 反向映射节首)、HYP-25 同族门禁完整性;TEST-AUDIT.md D-11 对照行 2/6
- **上线判定:**
- **状态:** draft

### F-TEST-05: 跨语言/跨份契约镜像常量与派生函数无对称测试锁定(7 个脆弱区共面)

- **维度:** 测试质量与覆盖 (TEST)
- **严重度:** MEDIUM — 影响:双语言镜像契约(fragment_id 校验、object key 派生、重试常量、错误码、上限值、FC 请求组装)的一侧漂移不会触发任何测试变红,契约失配以运行期错位暴露而非提交期检出;可能性:任一侧修改镜像落点即触发,Phase 2/3 已为该族立 7 条脆弱区发现
- **证据:** TEST-AUDIT.md 反向映射清单 F-CON-01/02/03/06、F-CODE-07/08、F-TOOL-08 七行(逐行兜底证据与缺口在档)
  > 缺口面清单:小程序 FRAGMENT_ID_RE 无非法日期负样本(`apps/miniprogram/test/ids.test.js:65-79 @ 5927f36` 仅正样本);buildObjectKeyPreview / fragmentIdFromObjectKey 测试 grep 零命中;52428800 上限小程序侧无预检断言;`apps/worker/tests/test_nls.py:401,449-450 @ 5927f36` 重试常量仅结构锁定、数值字面无断言;两份 FC 请求组装无跨份同步断言(uploader.test.js:68,92 与 redesign_view.test.js:126 各驱动一份);fc_live 镜像常量零跨侧绑定(`apps/worker/tests/test_fc_live.py:105-126 @ 5927f36` 自证消费)
- **修复建议:** 为每个镜像落点建立双侧字面断言对——以 JS 侧字面锁定(`apps/miniprogram/test/uploader.test.js:55-56 @ 5927f36`)为模板补齐 Python 侧数值断言与缺失函数直测;修复对应原发现(共享源/派生化)时同步落测试
- **工作量:** M(七落点分属 5 个测试文件,各自 S 粒度)
- **关联发现:** F-CON-01、F-CON-02、F-CON-03、F-CON-06、F-CODE-07、F-CODE-08、F-TOOL-08(严重度参照组内最高 F-CON-02/F-CON-03 MEDIUM;定级规则见 TEST-AUDIT.md 反向映射节首)
- **上线判定:**
- **状态:** draft

### F-TEST-06: 失败/恢复路径行为无测试兜底(6 个脆弱区共面)

- **维度:** 测试质量与覆盖 (TEST)
- **严重度:** MEDIUM — 影响:失败注入与恢复面(持久失败对象多轮重复、孤儿 tmp 清理、uploading 死态恢复、备份失败阻断、清理失败报告、越权反例三分)在修复前无回归防线、修复后无验收断言可依,下个里程碑修这些点时须自带测试面;可能性:对应原发现修复时必然触发(下个里程碑主工作面),其中 F-CODE-06 的现行死态行为已被既有断言正向锁定,修复漏改断言会直接翻红误导
- **证据:** TEST-AUDIT.md 反向映射清单 F-CODE-02/03/06、F-TOOL-01/02/03 六行(逐行兜底证据与缺口在档)
  > 关键交叉点:`apps/miniprogram/test/uploads_view.test.js:70 @ 5927f36` 断言 uploading 不计积压——F-CODE-06 修复需同步翻转该断言;失败对象多轮/计数面 grep 零命中(F-CODE-02,重复轮次锁定仅及成功路径 `test_pipeline.py:276,289 @ 5927f36`)
- **修复建议:** 修复各原发现时按反向映射行『应重点覆盖行为』列同步立测试;F-CODE-06 修复方案须包含 uploads_view.test.js:70 既有断言的同步改写
- **工作量:** M(随六条原发现修复分摊,每处 S 粒度)
- **关联发现:** F-CODE-02、F-CODE-03、F-CODE-06、F-TOOL-01、F-TOOL-02、F-TOOL-03(严重度参照组内最高 F-CODE-02/F-CODE-06 MEDIUM;定级规则见 TEST-AUDIT.md 反向映射节首)
- **上线判定:**
- **状态:** draft

### F-TEST-07: 低危功能缺失面的测试同步义务(6 个脆弱区共面)

- **维度:** 测试质量与覆盖 (TEST)
- **严重度:** LOW — 影响:该组测试缺口系对应功能本身缺失的衍生面(频控、.env 搜索边界、JS 语义 lint、Makefile 对账、sha256 取舍面、遗留形参),单独补测试无被测对象,风险敞口已由原发现承载——本条登记的是修复时的测试同步义务,防止功能补上而测试再欠账;可能性:仅在对应原发现修复时触发
- **证据:** TEST-AUDIT.md 反向映射清单 F-CON-04、F-CODE-01/04/05、F-TOOL-04/07 六行(逐行兜底证据与缺口在档)
  > 六行缺口判定均为『缺口参照原严重度 LOW』;兜底列或为『无』(F-CODE-05/F-TOOL-07)或仅覆盖现行行为正面(如 `apps/worker/tests/test_skeleton.py:52-58 @ 5927f36` 仅 .env 正向解析)
- **修复建议:** 修复原发现时按反向映射行『应重点覆盖行为』列同步立测试,不单独先行补测
- **工作量:** S(义务清单,随各原发现修复分摊)
- **关联发现:** F-CON-04、F-CODE-01、F-CODE-04、F-CODE-05、F-TOOL-04、F-TOOL-07(全组原发现均 LOW,严重度参照;定级规则见 TEST-AUDIT.md 反向映射节首)
- **上线判定:**
- **状态:** draft

### F-TEST-08: 手写 fake 与真实实现无行为面对齐锁定(FakeSource/RealOssSource 主证)

- **维度:** 测试质量与覆盖 (TEST)
- **严重度:** LOW — 影响:全仓『手写 fake + DI』模式下,fake 与真实 Protocol 实现仅经 mypy strict 做签名结构对齐,行为语义(网络错误分类、覆盖写语义、分页/截断行为)无对齐锁定——云 SDK 升级或真实实现行为漂移时全部单测继续全绿;可能性:升级 `alibabacloud-oss-v2` 或改写 RealOssSource 时触发,当前基线无漂移证据
- **证据:** `apps/worker/tests/test_poller.py:52-76 @ 5927f36`(FakeSource 定义,04-07 面②抽查线索行)
  > 台账备注:『FakeSource(:52-76)与 RealOssSource 仅经 Protocol 结构对齐(mypy strict),行为面(网络错误语义/覆盖写语义)无对齐锁定』;TESTING.md 自述『无 mock 框架,全手写 fake + DI』——该模式为仓库普遍形态,OssSource 为主证样本
- **修复建议:** 为关键 Protocol(OssSource 优先)增补契约测试骨架:同一断言集分别驱动 fake 与真实实现的可离线子集(参数校验、错误分类映射);至少在 fake 类 docstring 锚定所镜像的真实行为语义与实现行号,让漂移在 review 面可见
- **工作量:** M(骨架一次性 + 逐 Protocol 增补)
- **关联发现:** 无(按 CHARTER LOW『测试覆盖缺口』锚点定级;D-10 八面之面②)
- **上线判定:**
- **状态:** draft

### F-TEST-09: oss_sign 无『raw secret 不出现在表单/policy』负断言

- **维度:** 测试质量与覆盖 (TEST)
- **严重度:** LOW — 影响:OSS V4 签名表单组装若回归为把原始 STS secret 误置入表单字段或 policy 明文,现有测试不会变红——秘密红线面在该模块无负断言防线(Python 侧泄漏负断言先例 `apps/worker/tests/test_config.py:94-99 @ 5927f36` 未在 JS 侧复刻);可能性:签名逻辑重构或字段增补时触发,当前实现正确(秘密仅参与派生)
- **证据:** `apps/miniprogram/test/oss_sign.test.js:39,91 @ 5927f36`
  > 秘密标记 `sts-secret-do-not-log`(:39)仅参与签名派生(:91),全文件无『raw secret 不出现在表单/policy』的 not-includes 负断言(04-07 面⑤线索行)
- **修复建议:** 在 oss_sign.test.js 增补负断言:遍历 buildPostObjectForm 产出的全部字段值与 policy 明文,断言不含注入的 secret 标记字符串(与 test_config.py 泄漏断言先例对称)
- **工作量:** S(单测试文件增补)
- **关联发现:** 无(CHARTER 秘密红线关联面;D-10 八面之面⑤)
- **上线判定:**
- **状态:** draft

### F-TEST-10: 断言强度与测试卫生杂项(普审轻量线索聚合,5 处)

- **维度:** 测试质量与覆盖 (TEST)
- **严重度:** LOW — 影响:五处轻量面合计削弱回归灵敏度与重构安全边际——异常语义变化、报告内容错漏、私有符号更名时测试或不变红或误翻红;可能性:对应模块重构或报错语义变化时触发,均为维护成本类
- **证据:** 04-07 台账候选面 #4/#5/#6/#7/#8 聚合(行号均 @ 5927f36)
  > ①`apps/worker/tests/test_audio.py` 全文件零 pytest.raises,失败分支以留档位置断言表达(断言面窄);②`apps/worker/tests/test_e2e.py:149,173,217,250` 编排结果多为 `assert code == 0`,报告内容值断言偏薄;③`apps/worker/tests/test_manifest.py:288,298` monkeypatch 直引私有 `_fixture_path`;④`apps/worker/tests/test_skeleton.py:39-49` 直改 os.environ 与 monkeypatch 惯例混用;⑤`apps/fc/tests/test_custom_runtime_app.py:57` 直测私有 `_port()`
- **修复建议:** 增量整改(可随各文件下次触碰时顺带):异常路径改用 pytest.raises 表达、编排测试补报告内容值断言、私有符号直引改经公开面或 fixture、环境变量统一走 monkeypatch
- **工作量:** S(五处均单文件小改)
- **关联发现:** 无(按 CHARTER LOW『测试覆盖缺口』锚点定级;D-10 八面之面①/③/⑧)
- **上线判定:**
- **状态:** draft
