# 发现台账: 部署与验证工具链 (TOOL)

**Created:** 2026-07-04

本文件由 Phase 3 写入,ID 前缀 `F-TOOL-NN`;schema 以 `.planning/audit/CHARTER.md` 为准。

### F-TOOL-00: (schema 示例,非真实发现)

> 本条为 schema 示例,Phase 5 汇总时剔除。

- **维度:** 部署与验证工具链 (TOOL)
- **严重度:** (五级之一) — 影响:(一句场景语言);可能性:(一句触发条件)
- **证据:** `path:line @ 5927f36`(占位;从 `git show 5927f36:<path>` 提取)
  > (引用片段占位)
- **修复建议:** (一段占位)
- **工作量:** (S/M/L/XL 之一)
- **关联发现:** (F-XXX-NN 或 HYP-NN,无则写"无")
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

## 发现

> 03-05 判定产物(Worker 包内 12 个验证/运维模块,4,982 行,D-03 归 TOOL 维度):普审 12 模块 + 深挖 HYP-04(fc_deploy)/HYP-15(miniprogram_lint)/D14-3 证据采集(fc_live/verify_upload_live/e2e_scenarios,只采证不裁定,裁定留 03-07)。严重度按工具级影响定级(D-03):工具失准/误导操作者/危险操作防护缺失;工具可触发真云破坏性操作时按后果如实定级。scans/ 销号确认项(ruff #41/#45/#49、vulture #1)逐条核实下落见各条目与 COVERAGE 备注。

### F-TOOL-01: verify-prep STS 越权反例把非拒绝类异常误报为"疑似越权放行"且报告丢弃错误码

- **维度:** 部署与验证工具链 (TOOL)
- **严重度:** LOW — 影响:安全自检工具在瞬时网络/SDK 异常时向操作者报告"疑似越权放行",误导其排查 RAM policy(实际策略未被验证也未失效),且汇总报告不含错误码无从区分;可能性:真云探测中瞬时网络错误/超时属常态,任一反例遇到非 AccessDenied/Expired 类异常即触发
- **证据:** `apps/worker/src/soniscope_worker/verify_prep.py:747-753,275-293 @ 5927f36`
  > `_run_oss_op`:任意异常均提取错误码返回(`except Exception as exc: return _oss_error_code(exc)`),仅操作成功返回空串;`is_denied`(`:349-356`)对不在 `OSS_DENIED_CODES`/`OSS_EXPIRED_CODES` 名单内的码(如超时/连接错误经 `_oss_error_code` 兜底截取 `text[:80]`)一律判 `denied=False`;`check_sts_escape`(`:277,284`)将 `denied=False` 的反例统一渲染为"未被拒绝(疑似越权放行):" + 反例名——`StsCase.error_code` 字段未进入报告,操作者无法区分"操作真的成功了"(策略失效,CRITICAL 级信号)与"操作因无关错误未执行"(探测失败,应重跑)
- **修复建议:** `check_sts_escape` 按 `error_code` 三分:空串(操作意外成功)→ 维持"疑似越权放行"措辞;命中拒绝/过期码 → pass;其余码 → 单独渲染为"探测未完成(错误码: X),请重跑"并在 detail 中带出 error_code。纯函数改动,现有 FakeProbes 单测可直接覆盖三分支。
- **工作量:** S(单文件)
- **关联发现:** 无;关联线索: 无
- **上线判定:**
- **状态:** draft

### F-TOOL-02: deploy-fc 在预部署备份失败时不阻断部署,任意备份失败均被降级为"备份跳过"注记

- **维度:** 部署与验证工具链 (TOOL)
- **严重度:** LOW — 影响:部署是覆盖线上函数代码的破坏性真云操作,预部署快照是其唯一工具内回滚点;备份因瞬时网络/云端错误失败时部署照常执行,本次被覆盖版本的快照缺失,`make rollback-fc` 只能回到更早备份(恢复被覆盖版本需回到 git 重部署);可能性:任何非首次部署遇到 download_code/env_var_names 瞬时失败即触发,报告仅以 detail 注记且整体仍可 PASS
- **证据:** `apps/worker/src/soniscope_worker/fc_deploy.py:380-386 @ 5927f36`
  > `try: backup_path = _write_backup(...) except FcApiError as exc: detail.append(f"备份跳过:{exc}")` — 行内注释"首次部署时线上可能尚无代码可备份,不阻断部署"只论证了首次部署场景,但 `except FcApiError` 捕获全部备份失败类别(网络错误、凭证问题、SDK 调用失败均收敛为 FcApiError,`:616-617,622-623,637-638`),实现面宽于注释声明的意图;备份失败后 `pkg = package_function(...)` 与 `api.update_code(...)` 照常执行(`:386-390`)
- **修复建议:** 区分"首次部署(线上无代码 URL,`:611` 已有专用错误文案)"与其他备份失败:仅前者跳过备份继续;其余失败默认中止部署并提示重跑,或要求显式 `--force` 才可无备份部署。`deploy_one` 为注入 FakeFcApi 的纯编排函数,单测可直接覆盖两分支。
- **工作量:** S(单文件)
- **关联发现:** 无;关联线索: HYP-04(能力边界同模块)
- **上线判定:**
- **状态:** draft

### F-TOOL-03: test-verify-upload 向生产 recordings/ 前缀写入契约合法 key 的测试对象,清理失败被静默吞掉

- **维度:** 部署与验证工具链 (TOOL)
- **严重度:** LOW — 影响:残留测试对象位于 Worker 轮询前缀且 fragment_id 往返校验可通过,Worker 会当作真实片段下载→ffmpeg 转码失败→归档 inbox/failed/,且留档不阻止下轮重下(F-CODE-02),形成每轮重复的失败处理与日志噪声(对象永不删除,残留即永久);可能性:verified/mismatch 场景的清理为 best-effort 静默吞任意异常,删除失败时报告无任何提示,操作者不知残留
- **证据:** `apps/worker/src/soniscope_worker/verify_upload_live.py:257-262,276-277,287-288 @ 5927f36`
  > `_try_delete`:`except Exception: pass`(行内 noqa 注释"清理失败忽略(不影响主断言)"——不影响断言结论成立,但残留事实同样不进报告);测试 key 经 `object_key_for(fid := make_fid())` 生成(`:276`),即 `recordings/<date>/<id>.wav` 生产数据契约前缀 + 合法 fragment_id,Worker `fragment_id_from_key` 往返校验对其放行(对照 `apps/worker/src/soniscope_worker/poller.py:47-61 @ 5927f36`)
- **修复建议:** `_try_delete` 捕获异常后将"清理失败,残留 key=<object_key>"写入 LiveResult detail 或报告尾部提示行(不改变退出码),给操作者手动清理入口(`make oss-delete-obj` 已存在);或测试对象改用非 recordings/ 前缀 + 显式 expected_size 断言路径(需 FC 侧同 key 约束配合,改动面更大)。
- **工作量:** S(单文件)
- **关联发现:** F-CODE-02(残留对象落入其无界重试面);关联线索: 无
- **上线判定:**
- **状态:** draft

### F-TOOL-04: 小程序 JS 语义类缺陷无任何静态门禁,miniprogram_lint 规则面与语义检查零重叠

- **维度:** 部署与验证工具链 (TOOL)
- **严重度:** LOW — 影响:未用变量/宽松相等误用/不可达分支/未定义引用等语义类缺陷在 `make lint` 全绿下静默入库,页面胶水层又无自动化测试(HYP-24),此类回归只能真机暴露;可能性:基线现状经 ESLint 量化为零真实缺陷(scans/eslint.md:0 error/29 warning 全数为仓库惯例误报),风险面在未来变更而非存量
- **证据:** `apps/worker/src/soniscope_worker/miniprogram_lint.py:65-128,178-191 @ 5927f36`
  > 规则清单全集(逐条):① project.config.json 可解析 + appid 匹配(`:65-77`);② app.json pages 非空 + 必需页面 + 四件套齐全(`:80-104`);③ config.js 三合法域名 + issue-cedential 拼写守卫(`:107-118`);④ 全量 .json 可解析(`:182-186`);⑤ 硬编码密钥启发式——LTAI AK 正则(`:42`)+ 敏感键字面量赋值正则(`:43-46`),test/ 豁免(`:187-189`)。五族规则全部为配置完整性/秘密扫描,无一条 JS 语义规则——与 ESLint 检出面(scans/eslint.md 量化小结:no-unused-vars/eqeqeq 等)完全不重叠;logger.js:40 遗留 `eslint-disable` 注释旁证开发期曾预期 ESLint 存在(scans/eslint.md #15)
- **修复建议:** 按 CHARTER 双语言适配(ESLint 是线索底数不是标准)给两个等价选项:在 miniprogram_lint 增补少量高价值语义检查(如未用 catch 绑定之外的未用变量、`==`/`!=` 非判空场景),或引入一份零依赖平面 eslint 配置(03-RESEARCH 已有实测配方)作为 `make lint` 可选步骤并按仓库惯例关闭 catch-e/eq-null 两类规则(基线即刻零告警)。任选其一即可关闭本缺口。
- **工作量:** S(单文件或单配置文件)
- **关联发现:** 无;关联线索: HYP-15、HYP-24(页面胶水层无测试,TEST 维度)
- **上线判定:**
- **状态:** draft

> 03-06 判定产物(AUDIT-02 收尾:scripts/ 缩窄清单三文件 847 行 + Makefile 171 行 45 目标):普审 fetch_test_fixtures.py / gen_worker_config.sh / Makefile,深挖 test_asr.py(HYP-07 核实结论 + HYP-18 采证)。严重度按工具级影响定级(D-03);D-08 零执行——三个脚本与全部 make 目标均未运行,取证仅 `git show 5927f36:<path>`;HYP-07 证据全程遵守 CHARTER 秘密值本体红线(只写位置+模式名,不含任何值本体,含已过期值)。

### F-TOOL-05: test_asr.py 内置样例 URL 为已提交的带签名 OSS 预签名 URL(已过期),签名 URL 入库先例成立

- **维度:** 部署与验证工具链 (TOOL)
- **严重度:** MEDIUM — 影响:符合签名 URL 模式的完整预签名 GET URL(含 STS 临时 AccessKeyId 与签名参数)随脚本入库,git 历史不可撤回,构成"签名 URL 可以进 git"的先例惯性(对照 CHARTER MEDIUM 锚点"已过期凭证曾入库(泄露习惯风险)",逐字命中);URL 已过期且为 STS 临时凭证 + 单对象 GET 范围,无现行可利用价值,不触 CRITICAL"有效长期凭证泄露"锚;可能性:入库已是基线既成事实,风险面在惯性复发——:78 行内注释明示"过期后请用 --file-link 传新链接",下次更新若再以字面量内置新 URL 即重演,且 scripts/ 无任何静态门禁可拦截(HYP-25)
- **证据:** `scripts/test_asr.py:79-81 @ 5927f36`(`OSSAccessKeyId=` 签名 URL 模式 + `Signature=` 签名参数模式同行双命中,值本体略,per CHARTER 秘密红线)
  > `DEFAULT_FILE_LINK = (` — 常量赋值即完整预签名 URL 字面量(此处仅引变量名与赋值号,不截值本体)。过期状态可静态判定:URL 内 `Expires=` 参数为 unix 时间戳,对应 2026-05-29,早于审计日 2026-07-05;AccessKeyId 为 `TMP.` 前缀(STS 临时凭证形态,非 LTAI 长期 AK)。佐证::78 行内注释自认"OSS 签名 URL 会过期,过期后请用 --file-link 传新链接";:112-115 `--file-link` 缺省链回落至该常量(NLS_FILE_LINK 环境变量可覆盖)。
- **修复建议:** 移除 `DEFAULT_FILE_LINK` 字面量:缺省改为仅读 `NLS_FILE_LINK` 环境变量,未设置时按既有缺参路径(exit 2)退出并提示——脚本已具 `--file-link`/`NLS_FILE_LINK` 双通道(:112-115),改动即删常量 + 调整缺省值。配套把签名 URL 模式纳入 scripts/ 可用的静态门禁(miniprogram_lint 的密钥启发式只扫小程序;将 scripts/ 纳入 lint 范围或增仓库级预提交 grep,与 HYP-25 移交项同一修复面)。git 历史清洗(filter-repo)属可选项:值已过期且系临时凭证,清洗收益低于历史重写成本,留给修复里程碑裁量。
- **工作量:** S(单文件;门禁增补另计,与 HYP-25 修复面合并)
- **关联发现:** 无;关联线索: HYP-07(本条即其核实结论,证实)、HYP-25(scripts/ 无门禁,TEST 维度移交);scans/secrets.md #14/#15 销号去向即本条
- **上线判定:**
- **状态:** draft

### F-TOOL-06: `make typecheck` 门禁在仓内结构性恒红——app.py 的部署态导入使 mypy strict 必然 exit 1

- **维度:** 部署与验证工具链 (TOOL)
- **严重度:** MEDIUM — 影响:mypy strict 是仓库声明的核心质量门禁(pyproject strict + `make typecheck` 唯一类型闸),但该目标每次运行必以既有结构性错误退出,退出码永远无法区分"仅结构性旧错"与"引入了新类型回归",门禁二值信号失效——新回归只能靠肉眼比对错误列表发现,操作者对红灯习惯化后等同无门禁(对照 CHARTER MEDIUM"可诱发高危误操作的误导性文档"锚系:门禁声明口径(可通过的质量闸)与实态(结构性不可绿)不符,取影响最接近锚点);可能性:恒定——基线事实,任何时点运行 `make typecheck` 即现
- **证据:** `apps/fc/shared/app.py:14 @ 5927f36`、`pyproject.toml:32,37-45 @ 5927f36`、`Makefile:163-164 @ 5927f36`
  > `from handler import handler as application` — `handler.py` 仅在部署 zip 内与 app.py 同目录(fc_deploy vendoring 部署形态),仓内 `apps/fc/shared/` 无该模块;mypy `files` 含 `apps/fc/shared`(pyproject.toml:32),overrides 名单(:37-45)仅含云 SDK 五项、无 `handler`,strict 下 import-not-found 必报;`make typecheck` 即 `uv run mypy`(Makefile:163-164)。实测佐证:scans/gates-baseline.md 门禁基线直调 `uv run mypy` exit=1,全部输出恰此一条命中(#1)。
- **修复建议:** 三选一,均为配置级改动:①在 app.py:14 加 `# type: ignore[import-not-found]` + 行内注释说明部署态导入(最小改动);②pyproject 增补 `[[tool.mypy.overrides]] module = ["handler"]` + `ignore_missing_imports = true`(与"两个 handler.py 故意不查"的既定豁免口径一致,需注释说明缘由);③mypy `files` 排除 app.py 单文件。任选其一后 `make typecheck` 恢复可绿基线,新类型回归重新可由退出码捕获。
- **工作量:** S(单文件配置)
- **关联发现:** 无;关联线索: HYP-12(app.py 运行时形态,CODE 侧无发现)、HYP-23(handler.py mypy 豁免系故意,TEST 维度——本条不质疑豁免本身,只针对门禁恒红);scans/gates-baseline.md #1 销号去向即本条
- **上线判定:**
- **状态:** draft

### F-TOOL-07: Makefile .PHONY 声明幻影目标 lint-miniprogram,按声明名调用即硬错误

- **维度:** 部署与验证工具链 (TOOL)
- **严重度:** LOW — 影响:Makefile 声明面与实现面不一致——`.PHONY` 含 `lint-miniprogram` 但全文件无对应规则,按声明名调用 `make lint-miniprogram` 得 "No rule to make target" 硬错误;小程序 lint 能力无缺失(经 `make lint` 第二条命令执行,README 口径正确);可能性:操作者/agent 按声明名调用即触发——基线 `.claude/CLAUDE.md` 恰以 `make lint-miniprogram` 为该检查的调用口径(该文件属排除目录,仅作旁证)
- **证据:** `Makefile:19,166-168 @ 5927f36`
  > :19 `.PHONY` 列表含 `lint-miniprogram`;机械对账:全文件 45 个已定义目标全数在 `.PHONY`(46 条目),幻影条目仅此 1 个,无对应 `lint-miniprogram:` 规则;实体命令在 `lint` 目标内(:168 `uv run python -m soniscope_worker lint-miniprogram`)。旁证:`.claude/CLAUDE.md:53 @ 5927f36` 以 "via `make lint-miniprogram`" 表述调用方式(排除目录,口径漂移仅记事实);`apps/miniprogram/README.md:27 @ 5927f36` 正确经 `make lint` 表述。
- **修复建议:** 二选一:①新增独立目标 `lint-miniprogram: ## 小程序源码静态检查`(命令即 :168 现有行),与 `.PHONY` 及 agent 文档口径对齐——更符合仓库"每个 make 目标映射一个子命令"惯例;②从 `.PHONY` 移除该条目并同步修正 `.claude/CLAUDE.md:53` 表述。
- **工作量:** S(单文件)
- **关联发现:** 无;关联线索: HYP-15(miniprogram_lint 规则面同模块,TOOL 已回填)
- **上线判定:**
- **状态:** draft

> 03-07 判定产物(D14-3 三要素裁定,D-15 独立下落;证据由 03-05 采集,见 COVERAGE fc_live/verify_upload_live/e2e_scenarios/sts_escape 行备注):立发现 F-TOOL-08(LOW,工具失准类,D-14 口径)。三要素(①结构必要性 ②兜底机制 ③漂移后果)写入证据字段裁定段。

### F-TOOL-08: 联调工具契约镜像集群(错误码/凭证字段清单/大小假设/合成 fragment_id)靠注释约定同步,零测试兜底

- **维度:** 部署与验证工具链 (TOOL)
- **严重度:** LOW — 影响:工具失准类——fc_shared 契约变更(错误码更名、凭证字段增删、MAX_UPLOAD_BYTES 调整、fragment_id 语法变更)时无任何测试提醒同步工具侧镜像:漂移后果大多为联调工具可见 FAIL(误导操作者向线上排查而实为工具过时),少数为静默欠验证(FC 新增凭证字段不会进入 CREDENTIAL_FIELDS 完整性断言与拒绝响应泄漏反查清单,检查面滞后);纯工具级影响无生产数据面,对照 CHARTER LOW"lint/typecheck 覆盖缺口"同族锚(验证工具检查面缺口);可能性:仅在契约变更时触发,基线镜像值与 fc_shared 逐项一致(03-05 已逐处核实)
- **证据:** `apps/worker/src/soniscope_worker/fc_live.py:41-59,254-258 @ 5927f36`、`apps/worker/src/soniscope_worker/verify_upload_live.py:33-35,199-203 @ 5927f36`
  > `# FC issue-credential 响应 / 错误码(与 fc_shared 保持一致,避免跨包导入)。` → `ERR_INVALID_CODE = "INVALID_CODE"` 等 3 码第二份字面定义(:42-44);`CREDENTIAL_FIELDS` 7 字段清单锚 tech-spec §4.1 非 fc_shared(:46-55);`SIZE_OK_BYTES = 10_000_000` / `SIZE_EXCEEDED_BYTES = 60_000_000` 以注释字面编码"50MB 上限"假设、未引用 env.py `MAX_UPLOAD_BYTES` 常量(:57-59);`make_fragment_id` 合成 ID 注释自证正则子集(:254-258)。verify_upload_live 同构:`REASON_OBJECT_NOT_FOUND`/`REASON_SIZE_MISMATCH` 第三份字面定义锚 tech-spec §4.2(:33-35)+ 合成 ID 第六处(:199-203)。集群消费端:`e2e_scenarios.py:31-40 @ 5927f36` 确为导入消费非第四份副本;顺带同族:`sts_escape.py:127-129,256-258 @ 5927f36`(key 模板手拼 + key→id 切割,自产自洽)。
  >
  > **三要素裁定(D-13):** ① 结构必要性:部分成立——worker 包运行时不依赖 fc_shared(部署单元分离),fc_live 注释自述"避免跨包导入"系故意的运行时隔离;但同仓同语言且 pytest 已配 `pythonpath = ["apps/fc/shared"]`(`pyproject.toml:58 @ 5927f36`),**测试层**完全可绑定两侧常量而不引入运行时耦合——"无法共享"在测试层不成立,镜像无绑定 = 可疑。② 兜底机制:注释锚点覆盖不全——仅 3 错误码有"与 fc_shared 保持一致"锚(fc_live.py:41),7 字段清单/2 reason 锚 tech-spec 文档而非代码真值源,50MB 假设与合成 ID 仅自证注释;**全集群零测试断言**。③ 漂移后果:工具失准两向——契约收紧/更名时工具误 FAIL(可见,但把操作者导向线上排查);契约扩展时工具静默欠验证(新增凭证字段不入完整性断言 fc_live.py:47-55 与泄漏反查 :152-156,泄漏检查面滞后于契约)。无生产链路污染面(合成 key 反例安全性已在 COVERAGE fc_live 行核实)。
- **修复建议:** 增加一个契约镜像一致性测试(落 apps/fc/tests 或 apps/worker/tests,pythonpath 使 fc_shared 与 soniscope_worker 可同时导入):断言 fc_live `ERR_*` == fc_shared.errors 对应常量、verify_upload_live `REASON_*` 同构、`CREDENTIAL_FIELDS` 与 `credential_response` 输出字段集一致、`SIZE_OK_BYTES < DEFAULT_MAX_UPLOAD_BYTES < SIZE_EXCEEDED_BYTES`、`make_fragment_id()` 产物通过 `fc_shared.sts` 与 `oss_admin` 双侧校验——单测试文件即可绑定全集群,运行时零耦合,契约漂移即测试变红。
- **工作量:** S(单测试文件新增)
- **关联发现:** F-CON-05(其关联字段已挂 D14-3,错误码镜像同源);关联线索: D14-3(CONTRACT-MATRIX ③移交记录第 3 条销号)、HYP-22(联调工具活体路径依赖,TEST 维度移交);矩阵普查表行 50-51、组③ 行 46 辅助线索
- **上线判定:**
- **状态:** draft
