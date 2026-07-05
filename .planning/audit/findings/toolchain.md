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
