# Do-NOT-fix 登记表(RPT-05 初稿)

**Created:** 2026-07-04
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本表按锁定决策 D-08 预录入:CONCERNS.md 中已标注"故意设计/不要修"的条目直接登记于此,**不转为待验证假设、后续阶段不再花力气验证**。Phase 5 组装 RPT-05 时由用户最终裁定各条去留。本表条目与 `.planning/audit/HYPOTHESES.md` 分流互补:同一 CONCERNS.md 条目只出现在一侧,头部对账等式见 HYPOTHESES.md。

所有证据行号提取自 `git show 5927f36:<path>`,不读工作树。

---

### DNF-01: `whisper-local` 转写器为故意桩

- **标注:** `⚠ intentional — do not "fix"`
- **来源:** CONCERNS.md §Tech Debt / `whisper-local` transcriber is a deliberate stub
- **证据:** `apps/worker/src/soniscope_worker/transcriber.py:144-165 @ 5927f36` — `WhisperLocalTranscriber.transcribe` 于 162-165 行抛出 `NotImplementedError`,docstring(145 行)明言"本期不部署本地 Whisper"
- **理由:** CONCERNS.md 原文:"Intentional per AGENTS.md red line (no faster-whisper/whisper.cpp this milestone) — do not 'fix' without a scope decision"。占位实现是 AGENTS.md 红线的落地,选择 `whisper-local` 时运行期报错并给出改配 `cloud-speech` 的可操作提示,属受控失败而非缺陷。
- **分流依据:** D-08 点名。

### DNF-02: `issue-cedential` 拼写域名为 Aliyun 真实分配值

- **标注:** `⚠ intentional — do not "fix"`
- **来源:** CONCERNS.md §Fragile Areas / The `issue-cedential` misspelled domain
- **证据:** `apps/miniprogram/config.js:8-10 @ 5927f36` — 第 10 行 `FC_ISSUE_CREDENTIAL_URL` 常量值为 `issue-cedential-ottfirocds.cn-beijing.fcapp.run`(少一个 r),第 8 行内联注释明确警告"是阿里云分配的真实 URL,不要'修正'拼写"
- **理由:** CONCERNS.md 原文:"Any well-meaning 'typo fix' (human or AI) breaks the miniprogram against the WeChat domain whitelist and the live function"。该子域名由 Aliyun 生成、已登记于微信服务器域名白名单,`make test-fc-live` 实测真实 URL;任何"改对"操作即刻断线上功能。
- **分流依据:** D-08 点名。

### DNF-03: FC `handler.py` 的 mypy strict 豁免

- **标注:** `⚠ intentional — do not "fix"`
- **来源:** CONCERNS.md §Fragile Areas / FC handlers excluded from mypy strict
- **证据:** `pyproject.toml:30-32 @ 5927f36` — `[tool.mypy]` 的 `files` 列表(32 行)不含 `apps/fc/issue_credential`、`apps/fc/verify_upload`,30-31 行注释写明缘由:"两个 handler.py 同名,避免 mypy 模块名冲突,沿用 US-005 约定",handler 仍受 ruff 检查
- **理由:** 两个 FC 函数入口按 FC 约定必须同名 `handler.py`,mypy 无法在同一 run 中处理重名顶层模块;豁免是显式记录的工程取舍(handler 保持薄壳,全部逻辑下沉 `fc_shared`,后者在 mypy strict 范围内)。
- **分流依据:** D-08 点名。
- **备注:** CONCERNS.md §Test Coverage Gaps 另有同主题条目("FC `handler.py` files outside mypy strict"),该条**不入本表**,由 HYPOTHESES.md 以 TEST 维度承接(HYP-23,仅验证"行为测试补偿充分"这一判断,不质疑豁免本身),两侧以 ID 交叉引用。

### DNF-04: 小程序接收原始 STS 秘密(by design)

- **标注:** `⚠ intentional — do not "fix"`
- **来源:** CONCERNS.md §Security Considerations / Miniprogram receives raw STS secrets (by design)
- **证据:** `apps/fc/shared/fc_shared/sts.py:102-114 @ 5927f36` — `credential_response` 返回体包含 `access_key_secret`(108 行)与 `security_token`(109 行)字段(此处仅引用代码标识符名,不涉任何真实密钥值)
- **理由:** CONCERNS.md 原文:"Inherent to the OSS direct-upload pattern; scoped to one key, PutObject-only, ≤900 s"。向客户端下发临时 STS 是 OSS 直传模式的固有形态,爆炸半径由 `single_key_policy` 严格限定(单 object key、仅 PutObject、≤900 秒),并有 `make test-sts-escape` 实测验证。
- **分流依据:** D-08 "等"字延伸(01-RESEARCH.md 假设 A3)——本条**非 D-08 逐字点名**,系研究阶段按"by design"标注归入;Phase 5 组装 RPT-05 时请用户对此条归属作最终裁定。

---

*Do-NOT-fix 登记表初稿: 2026-07-04(D-08 预录入,共 4 条;Phase 5 RPT-05 组装时用户裁定)*
