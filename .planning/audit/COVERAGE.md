# 覆盖台账

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本文档是 Phase 3(组件与工具链深潜)的覆盖台账——证据与判断分离,只登记"哪个对象、审到什么深度、过了哪些面、产出了什么",不承载发现正文(发现入 `findings/code.md` / `findings/toolchain.md`)。依据 D-01(覆盖策略 = 全模块普审 + 线索深挖:每个源码模块至少完整读一遍,20 处深挖点逐行深挖)、D-02(独立覆盖台账,仿 Phase 2 CONTRACT-MATRIX 先例,直接喂 RPT-07/RPT-08)、D-04(普审关注面清单化,每模块逐面过并标"已过面 N/9")。取证方法:证据一律提取自 `git show 5927f36:<path>` / `git grep -n <pat> 5927f36`,禁读工作树取证。

> **基线导出备注(D-08,供 03-01 Task 3 与后续计划复用):** 仪器扫描对象为基线导出副本,导出命令 `git archive 5927f36 apps scripts | tar -x -C <EXPORT>`,导出路径(会话 scratchpad,仓库外):`/private/tmp/claude-501/-Volumes-Data-ProjectCode-my-soniscope/1affd208-a109-4cfb-808a-b80c6e881ccb/scratchpad/baseline-5927f36`。若会话更替导致该路径失效,按上述命令重导出即可(内容由基线 SHA 唯一决定)。

## 普审关注面清单(D-04 定稿,9 面)

以下 9 面为全阶段"已过面 N/9"的分母定义,逐字采用 03-RESEARCH.md §Architecture Patterns 定稿表;每面锚定 CHARTER 严重度锚点:

| # | 关注面 | CHARTER 锚点 | 仪器辅助信号 |
|---|--------|--------------|--------------|
| 1 | 静默失败路径(异常吞并、except-pass、错误被忽略) | HIGH 静默转写失败 | ruff S110/BLE/TRY(探针已见 S110 ×1) |
| 2 | 数据丢失风险(`.done` 时序、原子 rename、临时文件清理) | CRITICAL 数据丢失 | 人工为主(CLAUDE.md 反模式清单) |
| 3 | 秘密处理违规(明文入日志、绕过 MaskedSecret/audit 洗涤) | CRITICAL 凭证泄漏 | 秘密扫描 + ruff S105/S106(探针 13 命中待核) |
| 4 | 硬编码云值与环境假设(region/URL/size/阈值散落) | MEDIUM 潜伏失配 | grep;D14-5 关联 |
| 5 | 时区/日期正确性(naive datetime、本地时区推导) | MEDIUM(F-CON-02 同族) | ruff DTZ(探针 DTZ011 ×2、DTZ005 ×1) |
| 6 | 死代码与不可达分支 | LOW | vulture + ruff ARG(探针 ARG ×37) |
| 7 | 注释/文档字符串与实态不符 | LOW(契约类→移交) | 人工 |
| 8 | 纯逻辑+IO注入模式违反(纯逻辑内直调 SDK/wx) | MEDIUM/LOW(CLAUDE.md 明示反模式) | 人工 |
| 9 | 重试/退避/上限等跨端约定的本端一致性 | MEDIUM | D14-2/D14-3 关联 |

## CODE 维度

47 个对象(worker 核心 14 + fc 12 + miniprogram 21),行数为 `git show 5927f36:<path> | wc -l` 实测值(源自 03-RESEARCH.md 审计对象全量清单);深度/已过面/产出三列由 03-03/03-04 回填:

| 路径 | 行数 | 维度 | 深度 | 已过面 | 产出 | 备注 |
|------|------|------|------|--------|------|------|
| `apps/worker/src/soniscope_worker/pipeline.py` | 875 | CODE | 深挖 | 9/9 | 无发现 | 深挖 HYP-10 证实:串行 for 循环 `pipeline.py:407-441 @ 5927f36` + 单线程主循环 `:485-506`(回填见 HYPOTHESES.md)。`.done` 最后写(`:274`/`:367`)、任一阶段失败不建 `.done`、原子写协议核查通过;F-CODE-02 消费端证据 `:412-422` |
| `apps/worker/src/soniscope_worker/nls.py` | 740 | CODE | 深挖 | 9/9 | 无发现 | 深挖 HYP-19 证据:filetrans 域名+版本经 `verify_prep.NLS_FILETRANS_VERSION = "2018-08-17"`(`verify_prep.py:87 @ 5927f36`,消费 `nls.py:454-455 @ 5927f36`),legacy `aliyunsdkcore` AcsClient(`verify_prep.py:775-776`)。D14-2 证据(D-15 只记不裁):`RETRY_DELAYS_SECONDS = (5.0, 15.0, 45.0)` 与 `MAX_RETRIES = 3` 均为独立字面量(`nls.py:45-46 @ 5927f36`),MAX 非 `len()` 派生;`_with_retries`(`:268-270`)当前 3 == len 自洽。RESIGN_THRESHOLD 续签逻辑(`:314-326`)无静默失败;秘密仅经 `.get_secret_value()` 入 SDK 参数,错误信息只含类名/错误码(`:428`/`:579`) |
| `apps/worker/src/soniscope_worker/cli.py` | 601 | CODE | 普审 | 9/9 | 无发现 | TOOL 子命令入口,实体逻辑见 TOOL 侧对应模块,整体归 CODE 审一次(RESEARCH Open Question 2 裁决)。全部子命令统一 `(lines, exit_code)` → `typer.Exit` 转换完整;`oss-delete-obj` 双闸门(--yes/SONISCOPE_ALLOW_OSS_DELETE)测试专用;face7 轻微:模块 docstring(`cli.py:1-5 @ 5927f36`)"主轮询与 retranscribe 等在后续 story 实现"滞后于实态(两者已实现 `:24-29`/`:401-423`),不立发现 |
| `apps/worker/src/soniscope_worker/poller.py` | 531 | CODE | 深挖 | 9/9 | F-CODE-01、F-CODE-02 | 深挖 HYP-10/16 证实:`poll_loop` 单线程 while 循环 `poller.py:378-391 @ 5927f36`,单机单配置 RealOssSource(`:395-451`)。D14-1 证据(只记不裁):Worker 侧 sha256 比对流程 `poller.py:261,272-284 @ 5927f36`,经 `fixtures.sha256_of`(stdlib hashlib)。契约观察移交:`fragment_id_from_key` 往返校验(`:47-61`)已由 Phase 2 矩阵覆盖(F-CON-02/03 引用行),本维度不判断。OssSource Protocol 结构性无删除能力(`:215-231`)红线核查通过 |
| `apps/worker/src/soniscope_worker/manifest.py` | 473 | CODE | 待审 | 待审 | 待审 | — |
| `apps/worker/src/soniscope_worker/recovery.py` | 465 | CODE | 待审 | 待审 | 待审 | — |
| `apps/worker/src/soniscope_worker/audio.py` | 412 | CODE | 待审 | 待审 | 待审 | — |
| `apps/worker/src/soniscope_worker/oss_admin.py` | 242 | CODE | 待审 | 待审 | 待审 | HYP-13 相关(契约观察→移交,成功判据 4) |
| `apps/worker/src/soniscope_worker/transcriber.py` | 183 | CODE | 待审 | 待审 | 待审 | 深挖:HYP-19(Protocol 隔离充分性);DNF-01 对照(勿把 whisper 桩当发现) |
| `apps/worker/src/soniscope_worker/config.py` | 150 | CODE | 待审 | 待审 | 待审 | 深挖:HYP-08(MaskedSecret/600 权限缓解核实) |
| `apps/worker/src/soniscope_worker/paths.py` | 117 | CODE | 待审 | 待审 | 待审 | — |
| `apps/worker/src/soniscope_worker/locks.py` | 64 | CODE | 待审 | 待审 | 待审 | — |
| `apps/worker/src/soniscope_worker/__main__.py` | 11 | CODE | 待审 | 待审 | 待审 | — |
| `apps/worker/src/soniscope_worker/__init__.py` | 7 | CODE | 待审 | 待审 | 待审 | — |
| `apps/fc/shared/fc_shared/sts.py` | 176 | CODE | 待审 | 待审 | 待审 | 深挖:HYP-09/17(单键策略核实);DNF-04 对照 |
| `apps/fc/shared/fc_shared/env.py` | 150 | CODE | 待审 | 待审 | 待审 | 深挖:HYP-08 |
| `apps/fc/shared/fc_shared/head.py` | 141 | CODE | 待审 | 待审 | 待审 | — |
| `apps/fc/issue_credential/handler.py` | 110 | CODE | 待审 | 待审 | 待审 | 深挖:HYP-17(无限流);DNF-03 对照(mypy 豁免勿当发现) |
| `apps/fc/verify_upload/handler.py` | 106 | CODE | 待审 | 待审 | 待审 | DNF-03 对照 |
| `apps/fc/shared/fc_shared/__init__.py` | 106 | CODE | 待审 | 待审 | 待审 | — |
| `apps/fc/shared/fc_shared/http.py` | 79 | CODE | 待审 | 待审 | 待审 | — |
| `apps/fc/shared/fc_shared/audit.py` | 62 | CODE | 待审 | 待审 | 待审 | 深挖:HYP-08(is_sensitive 洗涤核实) |
| `apps/fc/shared/fc_shared/wechat.py` | 52 | CODE | 待审 | 待审 | 待审 | — |
| `apps/fc/shared/fc_shared/auth.py` | 52 | CODE | 待审 | 待审 | 待审 | 深挖:HYP-09 |
| `apps/fc/shared/fc_shared/errors.py` | 51 | CODE | 待审 | 待审 | 待审 | D14 关联(错误码字面量真值源) |
| `apps/fc/shared/app.py` | 35 | CODE | 待审 | 待审 | 待审 | 深挖:HYP-12(wsgiref;S104 bind-all 探针命中待人工核实) |
| `apps/miniprogram/pages/index/index.js` | 796 | CODE | 待审 | 待审 | 待审 | D14-1(sha256 调用端 :30,640) |
| `apps/miniprogram/pages/uploads/uploads.js` | 387 | CODE | 待审 | 待审 | 待审 | D14-4(请求组装第二份 :340,365) |
| `apps/miniprogram/utils/queue_runtime.js` | 324 | CODE | 待审 | 待审 | 待审 | D14-4(请求组装 :94-128) |
| `apps/miniprogram/utils/uploads_view.js` | 304 | CODE | 待审 | 待审 | 待审 | — |
| `apps/miniprogram/utils/audio.js` | 185 | CODE | 待审 | 待审 | 待审 | HYP-13 相关(契约观察→移交) |
| `apps/miniprogram/utils/sha256.js` | 171 | CODE | 待审 | 待审 | 待审 | 深挖:HYP-03 + D14-1(D-16 微基准对象) |
| `apps/miniprogram/utils/uploader.js` | 164 | CODE | 待审 | 待审 | 待审 | D14-2(重试常量) |
| `apps/miniprogram/utils/verify.js` | 138 | CODE | 待审 | 待审 | 待审 | D14-2 |
| `apps/miniprogram/utils/fault_injection.js` | 124 | CODE | 待审 | 待审 | 待审 | HYP-14 顺带证据(→移交 Phase 4,D-11) |
| `apps/miniprogram/utils/oss_sign.js` | 121 | CODE | 待审 | 待审 | 待审 | — |
| `apps/miniprogram/utils/upload_queue.js` | 119 | CODE | 待审 | 待审 | 待审 | D14-6(`fragmentIdFromObjectKey` :38-44,关联 F-CON-03) |
| `apps/miniprogram/utils/ulid.js` | 92 | CODE | 待审 | 待审 | 待审 | — |
| `apps/miniprogram/utils/chunking.js` | 65 | CODE | 待审 | 待审 | 待审 | — |
| `apps/miniprogram/utils/hmac.js` | 64 | CODE | 待审 | 待审 | 待审 | — |
| `apps/miniprogram/pages/dev/dev.js` | 60 | CODE | 待审 | 待审 | 待审 | 小程序实为 3 页(index/uploads/dev,RESEARCH Pitfall 8);HYP-14 相关开发者页 |
| `apps/miniprogram/utils/logger.js` | 60 | CODE | 待审 | 待审 | 待审 | — |
| `apps/miniprogram/utils/device.js` | 60 | CODE | 待审 | 待审 | 待审 | — |
| `apps/miniprogram/utils/retention.js` | 56 | CODE | 待审 | 待审 | 待审 | — |
| `apps/miniprogram/utils/draft.js` | 52 | CODE | 待审 | 待审 | 待审 | — |
| `apps/miniprogram/config.js` | 41 | CODE | 待审 | 待审 | 待审 | HYP-14/D14-5 顺带证据;DNF-02 对照(勿"修正"拼写域名) |
| `apps/miniprogram/app.js` | 23 | CODE | 待审 | 待审 | 待审 | — |

## TOOL 维度

16 个对象(worker 验证/运维 12 + scripts 3 + Makefile 1);ops.py/latency.py/fixtures.py 归属已经基线 docstring 核实(RESEARCH):

| 路径 | 行数 | 维度 | 深度 | 已过面 | 产出 | 备注 |
|------|------|------|------|--------|------|------|
| `apps/worker/src/soniscope_worker/verify_prep.py` | 924 | TOOL | 待审 | 待审 | 待审 | — |
| `apps/worker/src/soniscope_worker/fc_deploy.py` | 707 | TOOL | 待审 | 待审 | 待审 | 深挖:HYP-04(仅 update_code) |
| `apps/worker/src/soniscope_worker/retranscribe.py` | 590 | TOOL | 待审 | 待审 | 待审 | D-03 锁定归 TOOL |
| `apps/worker/src/soniscope_worker/fc_live.py` | 556 | TOOL | 待审 | 待审 | 待审 | D14-3(契约镜像集群 :42-59,256) |
| `apps/worker/src/soniscope_worker/verify_upload_live.py` | 464 | TOOL | 待审 | 待审 | 待审 | D14-3(:34-35,201) |
| `apps/worker/src/soniscope_worker/ops.py` | 380 | TOOL | 待审 | 待审 | 待审 | — |
| `apps/worker/src/soniscope_worker/e2e.py` | 295 | TOOL | 待审 | 待审 | 待审 | — |
| `apps/worker/src/soniscope_worker/e2e_scenarios.py` | 268 | TOOL | 待审 | 待审 | 待审 | D14-3(导入消费端) |
| `apps/worker/src/soniscope_worker/sts_escape.py` | 268 | TOOL | 待审 | 待审 | 待审 | — |
| `apps/worker/src/soniscope_worker/fixtures.py` | 232 | TOOL | 待审 | 待审 | 待审 | D14-1(stdlib hashlib 侧 :21,118) |
| `apps/worker/src/soniscope_worker/miniprogram_lint.py` | 218 | TOOL | 待审 | 待审 | 待审 | 深挖:HYP-15(规则覆盖面;ESLint 结果量化其漏报) |
| `apps/worker/src/soniscope_worker/latency.py` | 80 | TOOL | 待审 | 待审 | 待审 | — |
| `scripts/test_asr.py` | 355 | TOOL | 待审 | 待审 | 待审 | 深挖:HYP-07(`DEFAULT_FILE_LINK` 约 :80 过期预签名 URL)、HYP-18(legacy AcsClient);HYP-25 顺带证据(→移交 Phase 4,D-11) |
| `scripts/fetch_test_fixtures.py` | 249 | TOOL | 待审 | 待审 | 待审 | HYP-25 顺带证据(→移交) |
| `scripts/gen_worker_config.sh` | 243 | TOOL | 待审 | 待审 | 待审 | — |
| `Makefile` | 171 | TOOL | 待审 | 待审 | 待审 | 45 个目标;静读审计,不执行任何目标(D-08);按功能组过关注面 + 危险目标逐个细读(RESEARCH Open Question 3 裁决) |

## 深挖点登记(20 处)

14 条 HYP(CODE 10 + TOOL 4,回填集写死,RESEARCH Pitfall 4)+ 6 条 D14 移交线索;命中模块路径照抄 03-RESEARCH.md 审计对象全量清单"深挖线索"列(HYP-01/20 为结构性缺席类,命中区域为 apps/fc/ 目录结构本身):

| 线索 | 维度 | 命中模块路径 | 下落 |
|------|------|--------------|------|
| HYP-01 | CODE | apps/fc/ 目录结构(transcribe_audio/ 缺席,基线仅 issue_credential/ 与 verify_upload/) | 待审 |
| HYP-03 | CODE | apps/miniprogram/utils/sha256.js(D-16 微基准对象) | 待审 |
| HYP-08 | CODE | apps/worker/src/soniscope_worker/config.py、apps/fc/shared/fc_shared/env.py、apps/fc/shared/fc_shared/audit.py | 待审 |
| HYP-09 | CODE | apps/fc/shared/fc_shared/sts.py、apps/fc/shared/fc_shared/auth.py | 待审 |
| HYP-10 | CODE | apps/worker/src/soniscope_worker/pipeline.py、apps/worker/src/soniscope_worker/poller.py | 待审 |
| HYP-12 | CODE | apps/fc/shared/app.py | 待审 |
| HYP-16 | CODE | apps/worker/src/soniscope_worker/poller.py | 待审 |
| HYP-17 | CODE | apps/fc/shared/fc_shared/sts.py、apps/fc/issue_credential/handler.py | 待审 |
| HYP-19 | CODE | apps/worker/src/soniscope_worker/nls.py、apps/worker/src/soniscope_worker/transcriber.py | 待审 |
| HYP-20 | CODE | apps/fc/ 目录结构(transcribe-audio 已决策未建) | 待审 |
| HYP-04 | TOOL | apps/worker/src/soniscope_worker/fc_deploy.py | 待审 |
| HYP-07 | TOOL | scripts/test_asr.py(DEFAULT_FILE_LINK 约 :80;与五类秘密扫描同批,D-06) | 待审 |
| HYP-15 | TOOL | apps/worker/src/soniscope_worker/miniprogram_lint.py | 待审 |
| HYP-18 | TOOL | scripts/test_asr.py(legacy AcsClient SDK) | 待审 |
| D14-1 | CODE | apps/miniprogram/utils/sha256.js、apps/miniprogram/pages/index/index.js(:30,640)、apps/worker/src/soniscope_worker/fixtures.py(:21,118)、apps/worker/src/soniscope_worker/poller.py(比对流程) | 待审 |
| D14-2 | CODE | apps/worker/src/soniscope_worker/nls.py(:45)、apps/miniprogram/utils/uploader.js(:28)、apps/miniprogram/utils/verify.js(:16) | 待审 |
| D14-3 | TOOL | apps/worker/src/soniscope_worker/fc_live.py(:42-59,256)、apps/worker/src/soniscope_worker/verify_upload_live.py(:34-35,201)、apps/worker/src/soniscope_worker/e2e_scenarios.py(导入消费端) | 待审 |
| D14-4 | CODE | apps/miniprogram/utils/queue_runtime.js(:94-128)、apps/miniprogram/pages/uploads/uploads.js(:340,365) | 待审 |
| D14-5 | CODE | apps/miniprogram/config.js(:10-15,唯一代码内硬编码真实云值) | 待审 |
| D14-6 | CODE | apps/miniprogram/utils/upload_queue.js(:38-44,`fragmentIdFromObjectKey` 无校验切割,关联 F-CON-03) | 待审 |

## 完成判定

(占位——03-07 收口时填:覆盖对象总数对账、深挖点逐点下落、已过面 9/9 全模块核对、可复算命令 + 数字 + ✓,格式仿 CONTRACT-MATRIX ④完成判定。)
