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

| # | 命中(path:line @ 5927f36) | 规则/模式 | 销号 | 理由/去向 |
|---|---------------------------|-----------|------|-----------|
