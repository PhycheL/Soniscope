# Phase 4 移交清单

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本文档是 Phase 3 的跨维度顺带证据移交清单(per D-11):CODE/TOOL 普审中撞见 DOC/TEST 维度 HYP 的证据(如 config.js 的 HYP-14、scripts/ 的 HYP-25),只记录并移交 Phase 4,HYP 状态不动、不立发现。格式延续 Phase 2 CONTRACT-MATRIX ③债务移交记录的逐条 bullet 风格。逐条格式:

`- **(移交 Phase 4 <维度>,HYP-NN):** <一句观察> — <file:line @ 5927f36>`

## DOC 维度移交

- **(移交 Phase 4 DOC,HYP-16 文档一致性半句):** HYP-16 的代码实态半句已由 03-03 核实(单进程轮询 `apps/worker/src/soniscope_worker/poller.py:378-391 @ 5927f36`,Worker 离线即无转写、本地盘无副本),其"容量边界与文档声明的一致性"半句(PRD/tech-spec/runbook 对单机单用户边界的口径核对)属 Phase 4 DOC 维度,本计划未核对文档侧。
- **(移交 Phase 4 DOC,HYP-14):** config.js 的 ENV 常量基线现值即 `'development'`,生产发布依赖手工翻转该单点常量;带 development 上线时开发者菜单入口与故障注入门控全开——发布清单/文档是否覆盖该翻转步骤属 DOC 维度核对点 — `apps/miniprogram/config.js:29 @ 5927f36`(03-04 采证,HYP-14 状态未动)。
- **(移交 Phase 4 DOC,HYP-14):** 开发者菜单与故障注入的 production 门控实现完备(dev 页 onLoad/onShow/onToggleSwitch 三重门控 + fault_injection 生产读全关写忽略),门控实效完全取决于 ENV 发布时的实际取值,代码侧无发现——文档侧口径核对移交 — `apps/miniprogram/pages/dev/dev.js:18,28,52 @ 5927f36`、`apps/miniprogram/utils/fault_injection.js:38-40,82-107 @ 5927f36`(03-04 采证,HYP-14 状态未动)。

## TEST 维度移交

- **(移交 Phase 4 TEST,HYP-22):** 联调工具侧证据——fc_live 与 verify_upload_live 的全部真实鉴权/签发/校验场景依赖手工传入一次性 `wx.login` code,缺 code 即 SKIP(本地 CI exit 0 但活体路径零覆盖),与 HYP-22"CI 无法运行活体路径"假设同源 — `apps/worker/src/soniscope_worker/fc_live.py:15-16 @ 5927f36`(docstring:code 一次性、缺失场景标 SKIP)、`apps/worker/src/soniscope_worker/verify_upload_live.py:14 @ 5927f36`(同口径)(03-05 采证,HYP-22 状态未动)。
- **(移交 Phase 4 TEST,HYP-25):** scripts/ 缩窄清单三文件确在全部静态门禁之外——mypy `files` 与 ruff `src` 均只含 apps/ 四路径,Makefile lint 目标实际只跑 `ruff check apps/` 且行内注释自认"遗留 scripts/ 由各自 story 收口" — `pyproject.toml:32,50 @ 5927f36`、`Makefile:166-167 @ 5927f36`(03-06 采证,HYP-25 状态未动)。
- **(移交 Phase 4 TEST,HYP-25):** 门禁缺席已有实害样本:test_asr.py 存在门禁规则集(E,F,I,UP,B)内真实违例 6 条(UP009 ×1 / E501 ×4 / B904 ×1,逐条见 scans/gates-baseline.md #2-7)与已提交签名 URL(F-TOOL-05,位置 `scripts/test_asr.py:80 @ 5927f36`,只引位置不引值),均在 `make lint` 全绿下入库;fetch_test_fixtures.py 以 `# type: ignore`/`noqa` 自我豁免 — `scripts/test_asr.py:2,38,166,197,275,283 @ 5927f36`、`scripts/fetch_test_fixtures.py:42,103,108 @ 5927f36`(03-06 采证,HYP-25 状态未动)。
