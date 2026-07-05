# 扫描档案:五类秘密扫描(脱敏)

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

per D-06(D-07 秘密扫描归本阶段,与 HYP-07 同批)/ D-07(命令+版本+输出存档)。五类模式命令逐字取自 CHARTER.md §秘密扫描穿透规则(穿透所有排除目录,对基线 commit 全量扫描);每条输出一律经脱敏管道处理,**本档案只含 `rev:path:line`,不含任何匹配内容列**(Pitfall 1 强制,CHARTER 秘密值本体红线)。命中 ≠ 发现:每条命中须人工核实(排除测试假值、文档示例、变量名自身)后才进台账——销号列由 03-02 填。

**工具版本:** git version 2.23.0(git grep 取证通道,仓库自带)

> **脱敏管道备注(对 RESEARCH #7 配方的一处修正):** RESEARCH 原文管道为 `cut -d: -f1,2`,但 `git grep -nE <pat> 5927f36 -- .` 的输出带 rev 前缀,字段实为 `rev:path:line:content`,`-f1,2` 会把行号一并剥掉。本档案改用 `cut -d: -f1-3`(保留 `rev:path:line`,仍剥离全部内容列),与 RESEARCH"只留 path:line,剥离内容列"的定稿意图一致,脱敏保证不变。五类 grep 模式本体与 CHARTER 原文逐字一致,未改动。

## 模式 1:长期 AK ID(LTAI 前缀)

```bash
git grep -nE 'LTAI[0-9A-Za-z]{10,}' 5927f36 -- . | cut -d: -f1-3
```

**命中计数:10**(RESEARCH 实测参考值 10 ✓)

```
5927f36:apps/worker/tests/test_config.py:37
5927f36:apps/worker/tests/test_config.py:48
5927f36:apps/worker/tests/test_fc_deploy.py:145
5927f36:apps/worker/tests/test_fc_deploy.py:151
5927f36:apps/worker/tests/test_fc_deploy.py:156
5927f36:apps/worker/tests/test_miniprogram_lint.py:126
5927f36:apps/worker/tests/test_miniprogram_lint.py:172
5927f36:apps/worker/tests/test_verify_prep.py:55
5927f36:apps/worker/tests/test_verify_prep.py:66
5927f36:apps/worker/tests/test_verify_prep.py:214
```

## 模式 2:签名 URL(test_asr.py 先例模式)

```bash
git grep -nE 'OSSAccessKeyId=' 5927f36 -- . | cut -d: -f1-3
```

**命中计数:4**(RESEARCH 实测参考值 4 ✓)

```
5927f36:.planning/codebase/CONCERNS.md:55
5927f36:.planning/codebase/CONCERNS.md:58
5927f36:.planning/research/PITFALLS.md:250
5927f36:scripts/test_asr.py:80
```

## 模式 3:签名参数

```bash
git grep -nE 'Signature=[0-9A-Za-z%+/=]{16,}' 5927f36 -- . | cut -d: -f1-3
```

**命中计数:1**(RESEARCH 实测参考值 1 ✓)

```
5927f36:scripts/test_asr.py:80
```

## 模式 4:appsecret 字面量赋值

```bash
git grep -niE 'app_?secret[[:space:]]*[:=]' 5927f36 -- . | cut -d: -f1-3
```

**命中计数:3**(RESEARCH 实测参考值 3 ✓)

```
5927f36:apps/fc/shared/fc_shared/env.py:52
5927f36:apps/fc/shared/fc_shared/env.py:148
5927f36:docs/runbook/fc-deploy.md:309
```

## 模式 5:STS token

```bash
git grep -nE 'SecurityToken=|security_token' 5927f36 -- . | cut -d: -f1-3
```

**命中计数:51**(RESEARCH 实测参考值 51 ✓)

```
5927f36:.planning/codebase/CONCERNS.md:73
5927f36:apps/fc/shared/fc_shared/audit.py:21
5927f36:apps/fc/shared/fc_shared/sts.py:42
5927f36:apps/fc/shared/fc_shared/sts.py:109
5927f36:apps/fc/shared/fc_shared/sts.py:169
5927f36:apps/fc/tests/test_fc_shared.py:195
5927f36:apps/fc/tests/test_fc_shared.py:208
5927f36:apps/fc/tests/test_issue_credential.py:82
5927f36:apps/fc/tests/test_issue_credential.py:111
5927f36:apps/fc/tests/test_issue_credential.py:198
5927f36:apps/fc/tests/test_sts.py:97
5927f36:apps/fc/tests/test_sts.py:109
5927f36:apps/miniprogram/test/fault_injection.test.js:122
5927f36:apps/miniprogram/test/oss_sign.test.js:40
5927f36:apps/miniprogram/test/oss_sign.test.js:69
5927f36:apps/miniprogram/test/redesign_view.test.js:114
5927f36:apps/miniprogram/test/uploader.test.js:16
5927f36:apps/miniprogram/test/uploads_view.test.js:17
5927f36:apps/miniprogram/utils/logger.js:1
5927f36:apps/miniprogram/utils/logger.js:4
5927f36:apps/miniprogram/utils/oss_sign.js:8
5927f36:apps/miniprogram/utils/oss_sign.js:51
5927f36:apps/miniprogram/utils/oss_sign.js:65
5927f36:apps/miniprogram/utils/uploader.js:7
5927f36:apps/miniprogram/utils/uploader.js:20
5927f36:apps/worker/src/soniscope_worker/fc_live.py:50
5927f36:apps/worker/src/soniscope_worker/fc_live.py:92
5927f36:apps/worker/src/soniscope_worker/fc_live.py:180
5927f36:apps/worker/src/soniscope_worker/fc_live.py:239
5927f36:apps/worker/src/soniscope_worker/fc_live.py:476
5927f36:apps/worker/src/soniscope_worker/fc_live.py:544
5927f36:apps/worker/src/soniscope_worker/sts_escape.py:223
5927f36:apps/worker/src/soniscope_worker/verify_prep.py:706
5927f36:apps/worker/tests/test_e2e_scenarios.py:38
5927f36:apps/worker/tests/test_fc_live.py:47
5927f36:apps/worker/tests/test_fc_live.py:143
5927f36:apps/worker/tests/test_fc_live.py:146
5927f36:apps/worker/tests/test_fc_live.py:302
5927f36:apps/worker/tests/test_miniprogram_lint.py:135
5927f36:apps/worker/tests/test_sts_escape.py:26
5927f36:docs/example/start-fc-main/custom-container-function/fc-custom-container-event-python3.9/src/code/app.py:20
5927f36:docs/example/start-fc-main/custom-container-function/fc-custom-container-event-python3.9/src/code/app.py:39
5927f36:docs/multi-user-design.md:258
5927f36:docs/v1.0.0 prd/tech-spec.md:373
5927f36:scripts/ralph/prd.json:141
5927f36:scripts/ralph/prd.json:228
5927f36:scripts/ralph/progress.txt:130
5927f36:scripts/ralph/progress.txt:163
5927f36:scripts/ralph/progress.txt:256
5927f36:scripts/ralph/progress.txt:324
5927f36:scripts/ralph/progress.txt:531
```

**合计:10 + 4 + 1 + 3 + 51 = 69 命中**(RESEARCH 实测参考值合计 69 ✓),全部待三态销号。

## 三态销号表(03-02 填)

核实方法:每条命中经 `git show 5927f36:<path>` 定位命中行人工判断(与 HYP-07 同批,D-06)。全表遵守 Pitfall 7 红线:仅记 path:line + 模式名 + 三态 + 去向,任何行不复制匹配值本体(含已过期值、测试假值)。行序与上方五模式输出一致。

| # | 命中(path:line @ 5927f36) | 规则/模式 | 销号 | 理由/去向 |
|---|---------------------------|-----------|------|-----------|
| 1 | apps/worker/tests/test_config.py:37 | LTAI 前缀 | 误报 | 测试假值(标识符自述 Example 样式),config 假配置构造 |
| 2 | apps/worker/tests/test_config.py:48 | LTAI 前缀 | 误报 | 同 #1,NLS 假配置构造 |
| 3 | apps/worker/tests/test_fc_deploy.py:145 | LTAI 前缀 | 误报 | 测试假值(自述 SECRETID 样式),经 monkeypatch 注入环境专为断言脱敏 |
| 4 | apps/worker/tests/test_fc_deploy.py:151 | LTAI 前缀 | 误报 | 同 #3,构造含假值的异常消息 |
| 5 | apps/worker/tests/test_fc_deploy.py:156 | LTAI 前缀 | 误报 | 同 #3,断言假值不出现在 summary 输出(泄露检测测试本体) |
| 6 | apps/worker/tests/test_miniprogram_lint.py:126 | LTAI 前缀 | 误报 | 测试假值,专为验证 scan_hardcoded_secrets 能检出 LTAI 模式 |
| 7 | apps/worker/tests/test_miniprogram_lint.py:172 | LTAI 前缀 | 误报 | 同 #6(自述 LEAKED 样式),验证 run_checks 检出泄露文件 |
| 8 | apps/worker/tests/test_verify_prep.py:55 | LTAI 前缀 | 误报 | 测试假值(Example 样式),假配置构造 |
| 9 | apps/worker/tests/test_verify_prep.py:66 | LTAI 前缀 | 误报 | 同 #8 |
| 10 | apps/worker/tests/test_verify_prep.py:214 | LTAI 前缀 | 误报 | 同 #8 |
| 11 | .planning/codebase/CONCERNS.md:55 | `OSSAccessKeyId=` 签名 URL 模式 | 误报 | 审计研究文档对 test_asr.py 事故的描述性引用(仅模式名叙述,无值) |
| 12 | .planning/codebase/CONCERNS.md:58 | `OSSAccessKeyId=` 签名 URL 模式 | 误报 | 同 #11,修复建议叙述 |
| 13 | .planning/research/PITFALLS.md:250 | `OSSAccessKeyId=` 签名 URL 模式 | 误报 | 研究文档红线示例引用(叙述"不得复制值本体"的规则本身),无值 |
| 14 | scripts/test_asr.py:80 | `OSSAccessKeyId=` 签名 URL 模式 | 确认 | DEFAULT_FILE_LINK 常量赋值行符合签名 URL 模式(值本体略,per CHARTER 秘密红线);:78 行内注释自认"OSS 签名 URL 会过期"——过期预签名 URL 曾入库先例的核实对象 → 深挖线索(03-06 test_asr 普审,HYP-07) |
| 15 | scripts/test_asr.py:80 | `Signature=` 签名参数模式 | 确认 | 与 #14 同一行同时命中签名参数模式(值本体略)→ 深挖线索(03-06 test_asr 普审,HYP-07) |
| 16 | apps/fc/shared/fc_shared/env.py:52 | app_secret 赋值模式 | 误报 | dataclass 字段类型声明(`wx_app_secret: str`),标识符非值 |
| 17 | apps/fc/shared/fc_shared/env.py:148 | app_secret 赋值模式 | 误报 | 从环境变量 WX_APP_SECRET 读取的代码行,无字面量值 |
| 18 | docs/runbook/fc-deploy.md:309 | app_secret 赋值模式 | 误报 | runbook 环境变量清单的尖括号占位符行,无实际值 |
| 19 | .planning/codebase/CONCERNS.md:73 | security_token 模式 | 误报 | 审计文档对 credential_response 字段的描述性引用,仅字段名 |
| 20 | apps/fc/shared/fc_shared/audit.py:21 | security_token 模式 | 误报 | SENSITIVE_FIELD_NAMES 脱敏字段名清单——恰为防泄露机制本体,非值 |
| 21 | apps/fc/shared/fc_shared/sts.py:42 | security_token 模式 | 误报 | StsCredential dataclass 字段声明,标识符;STS 原始凭证下发系 by-design(DNF-04) |
| 22 | apps/fc/shared/fc_shared/sts.py:109 | security_token 模式 | 误报 | credential_response 字段传递代码(cred 对象字段引用),同 #21(DNF-04) |
| 23 | apps/fc/shared/fc_shared/sts.py:169 | security_token 模式 | 误报 | AssumeRole 响应字段转换代码,同 #21(DNF-04) |
| 24 | apps/fc/tests/test_fc_shared.py:195 | security_token 模式 | 误报 | 断言 is_sensitive("security_token") 的字段名字符串,脱敏测试本体 |
| 25 | apps/fc/tests/test_fc_shared.py:208 | security_token 模式 | 误报 | 测试假值(自述 SECRET 样式),脱敏断言用 |
| 26 | apps/fc/tests/test_issue_credential.py:82 | security_token 模式 | 误报 | 测试假值(自述 fake 样式) |
| 27 | apps/fc/tests/test_issue_credential.py:111 | security_token 模式 | 误报 | 响应字段名清单断言,字段名字符串 |
| 28 | apps/fc/tests/test_issue_credential.py:198 | security_token 模式 | 误报 | 断言 payload 不含该字段名(泄露检测测试本体) |
| 29 | apps/fc/tests/test_sts.py:97 | security_token 模式 | 误报 | 测试假值(三字符占位) |
| 30 | apps/fc/tests/test_sts.py:109 | security_token 模式 | 误报 | 字段名清单断言 |
| 31 | apps/miniprogram/test/fault_injection.test.js:122 | security_token 模式 | 误报 | 测试假值(两字符占位) |
| 32 | apps/miniprogram/test/oss_sign.test.js:40 | security_token 模式 | 误报 | 测试假值(自述 xyz 占位样式) |
| 33 | apps/miniprogram/test/oss_sign.test.js:69 | security_token 模式 | 误报 | 断言表单字段等于假凭证字段,字段引用 |
| 34 | apps/miniprogram/test/redesign_view.test.js:114 | security_token 模式 | 误报 | 测试假值(单词占位) |
| 35 | apps/miniprogram/test/uploader.test.js:16 | security_token 模式 | 误报 | 测试假值(单词占位) |
| 36 | apps/miniprogram/test/uploads_view.test.js:17 | security_token 模式 | 误报 | 测试假值(单词占位) |
| 37 | apps/miniprogram/utils/logger.js:1 | security_token 模式 | 误报 | 模块头注释声明自动脱敏范围,字段名叙述 |
| 38 | apps/miniprogram/utils/logger.js:4 | security_token 模式 | 误报 | 同 #37,红线注释叙述 |
| 39 | apps/miniprogram/utils/oss_sign.js:8 | security_token 模式 | 误报 | 模块头注释红线声明("绝不在此打印"),字段名叙述 |
| 40 | apps/miniprogram/utils/oss_sign.js:51 | security_token 模式 | 误报 | credential 结构 docstring 注释,字段名叙述 |
| 41 | apps/miniprogram/utils/oss_sign.js:65 | security_token 模式 | 误报 | 从 FC 返回凭证读取字段的代码,字段引用非值 |
| 42 | apps/miniprogram/utils/uploader.js:7 | security_token 模式 | 误报 | 模块头注释红线声明,字段名叙述 |
| 43 | apps/miniprogram/utils/uploader.js:20 | security_token 模式 | 误报 | CREDENTIAL_FIELDS 字段名清单常量,字段名字符串 |
| 44 | apps/worker/src/soniscope_worker/fc_live.py:50 | security_token 模式 | 误报 | 必备凭证字段名清单常量,字段名字符串 |
| 45 | apps/worker/src/soniscope_worker/fc_live.py:92 | security_token 模式 | 误报 | dataclass 字段声明,标识符 |
| 46 | apps/worker/src/soniscope_worker/fc_live.py:180 | security_token 模式 | 误报 | 注释红线声明("绝不展示"),字段名叙述 |
| 47 | apps/worker/src/soniscope_worker/fc_live.py:239 | security_token 模式 | 误报 | FC 响应字段读取代码,字段引用 |
| 48 | apps/worker/src/soniscope_worker/fc_live.py:476 | security_token 模式 | 误报 | 凭证对象字段传递代码,字段引用 |
| 49 | apps/worker/src/soniscope_worker/fc_live.py:544 | security_token 模式 | 误报 | dataclass 字段声明,标识符 |
| 50 | apps/worker/src/soniscope_worker/sts_escape.py:223 | security_token 模式 | 误报 | getattr 字段读取代码,字段引用 |
| 51 | apps/worker/src/soniscope_worker/verify_prep.py:706 | security_token 模式 | 误报 | 凭证对象字段传递代码,字段引用 |
| 52 | apps/worker/tests/test_e2e_scenarios.py:38 | security_token 模式 | 误报 | 测试假值(自述 do-not-log 样式) |
| 53 | apps/worker/tests/test_fc_live.py:47 | security_token 模式 | 误报 | 测试假值(CAIS 前缀 + x 填充假形) |
| 54 | apps/worker/tests/test_fc_live.py:143 | security_token 模式 | 误报 | 置空字段模拟缺字段响应,字段引用 |
| 55 | apps/worker/tests/test_fc_live.py:146 | security_token 模式 | 误报 | 断言错误详情含字段名,字段名字符串 |
| 56 | apps/worker/tests/test_fc_live.py:302 | security_token 模式 | 误报 | 同 #54 |
| 57 | apps/worker/tests/test_miniprogram_lint.py:135 | security_token 模式 | 误报 | 测试函数名含该词(检出能力测试本体) |
| 58 | apps/worker/tests/test_sts_escape.py:26 | security_token 模式 | 误报 | 测试假值(自述 do-not-log 样式) |
| 59 | docs/example/start-fc-main/custom-container-function/fc-custom-container-event-python3.9/src/code/app.py:20 | security_token 模式 | 误报 | vendored 示例代码中被注释掉的 header 读取行(CHARTER 排除清单 #1;秘密穿透扫描已覆盖,核实无值) |
| 60 | docs/example/start-fc-main/custom-container-function/fc-custom-container-event-python3.9/src/code/app.py:39 | security_token 模式 | 误报 | 同 #59 |
| 61 | docs/multi-user-design.md:258 | security_token 模式 | 误报 | 设计文档 JSON 示例,字段值为省略号占位 |
| 62 | docs/v1.0.0 prd/tech-spec.md:373 | security_token 模式 | 误报 | tech-spec JSON 示例,字段值为省略号占位 |
| 63 | scripts/ralph/prd.json:141 | security_token 模式 | 误报 | agent 元文档验收标准叙述,字段名列举 |
| 64 | scripts/ralph/prd.json:228 | security_token 模式 | 误报 | 同 #63,脱敏要求叙述 |
| 65 | scripts/ralph/progress.txt:130 | security_token 模式 | 误报 | agent 进度日志叙述(带 token 建 client 的流程描述),无值 |
| 66 | scripts/ralph/progress.txt:163 | security_token 模式 | 误报 | 同 #65,SDK 用法笔记 |
| 67 | scripts/ralph/progress.txt:256 | security_token 模式 | 误报 | 同 #65,Protocol 注入点描述 |
| 68 | scripts/ralph/progress.txt:324 | security_token 模式 | 误报 | 同 #65,logger 脱敏字段描述 |
| 69 | scripts/ralph/progress.txt:531 | security_token 模式 | 误报 | 同 #65,test/ 目录豁免缘由描述 |

**对账等式:** 确认 2 + 误报 67 + 移交 0 = 命中总数 69 ✓

**移交说明:** 本档无移交项(文档类命中 #11-13/#18/#61-62 逐条核实均为占位符或模式名叙述,不构成 DOC 维度证据;测试类命中均为自述假值或脱敏测试本体)。

## 03-02 收尾核验记录(scans/ 反扫 + 零 diff)

**scans/ 目录秘密反扫**(收紧版三模式,销号表全部填毕后执行):

```bash
grep -rE 'OSSAccessKeyId=[0-9A-Za-z]{8,}|Signature=[0-9A-Za-z%+/=]{16,}|LTAI[0-9A-Za-z]{10,}' .planning/audit/scans/
# 实际输出:(空)——零命中 PASS,五档销号表未截入任何值本体
```

**零 diff 验证**(CHARTER D-03):

```bash
git diff --stat 5927f36 -- apps/ scripts/ docs/
# 实际输出:(空)——apps/、scripts/、docs/ 相对基线零改动,销号全程仅写 .planning/audit/
```

---
*五档三态销号封版: 2026-07-05(gates-baseline 90 + ruff-extended 69 + vulture 1 + eslint 29 + secrets 69 = 258 命中全部销号;确认 15 / 误报 243 / 移交 0;反扫零命中,零 diff 为空——03-02 收口)*
