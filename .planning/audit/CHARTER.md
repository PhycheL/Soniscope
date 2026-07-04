# 审计章程: SoniScope — 上线前代码审计

**Defined:** 2026-07-04
**基线 commit:** `5927f362785d44b085a791ca387732991012ce5a`

> 完整 SHA 全文只在上方声明一次;正文其余处一律使用 7 位短 SHA `5927f36`(per D-02)。

本章程在任何证据收集开始前定稿审计的全部标尺与边界。Phase 2–5 的任何审计者拿到本章程后可直接套用,无需再作解释;章程条款不留自由裁量空间。

## 审计基线

- **基线(per D-01):** 短 SHA `5927f36`(完整 SHA 见文档头部),分支 `ralph/soniscope-mvp-claude`。main 落后 53 提交且无独立提交,审计对象即本分支 tip。全程 5 个阶段所有证据统一引用这一个 SHA;后续 `.planning/` 提交推进 HEAD 不影响行号有效性。
- **钉定时工作树状态(CHARTER-01 dirty-tree 处置成文):** 干净。旧权威文档迁移(`docs/PRD_v1.md`、`docs/tech-spec.md`、`docs/deployment-guide.md` → `docs/v1.0.0 prd/` 与 `docs/runbook/`)已随提交入库——记录此事实即可,阻塞已自行解除。AGENTS.md 仍引用旧路径一事属 Phase 4 DOC 维度审计对象,本章程只记事实。
- **证据格式(per D-02):** 单行证据 `path:line @ 5927f36`;多行证据 `path:10-25 @ 5927f36`。
- **证据提取方法:** 证据一律提取自 `git show 5927f36:<path>`,禁止以工作树文件充当行号证据。`.planning/` 提交会持续推进 HEAD;从基线 SHA 取证是结构性免疫,读工作树不是。
- **零 diff 验证(per D-03):** 验证命令写定为:

  ```bash
  git diff --stat 5927f36 -- apps/ scripts/ docs/
  ```

  输出必须为空。Phase 2–5 每阶段收尾执行一次并记录结果;发现污染可定位到具体阶段。说明:该命令只保护 `apps/`、`scripts/`、`docs/` 三个目录;`Makefile`、`AGENTS.md`、`pyproject.toml`、`uv.lock` 等根文件同为审计对象但不在该命令保护范围,其证据有效性靠"证据一律出自 `5927f36`"条款兜底。
- **无例外协议(per D-04):** 任何发现——包括 CRITICAL(如泄露的有效凭证)——一律只进台账并标 BLOCKER;不中断审计、不重钉基线。云端操作(账号中删凭证、改环境变量等)绝不由审计者动手,同样只进台账。无例外、无自由裁量。

## 范围与方法

### 五个审计维度(CHARTER-04)

| # | 维度 | 短码 | 对应需求 | 执行阶段 |
|---|------|------|----------|----------|
| 1 | 契约一致性 | CON | CONTRACT-01~04 | Phase 2 |
| 2 | 组件代码(技术债/脆弱区) | CODE | AUDIT-01 | Phase 3 |
| 3 | 部署与验证工具链 | TOOL | AUDIT-02 | Phase 3 |
| 4 | 文档配置一致性 | DOC | AUDIT-03 | Phase 4 |
| 5 | 测试质量与覆盖 | TEST | AUDIT-04 | Phase 4 |

全部维度的证据统一引用审计基线 `5927f36`。

### 明确排除项

| 排除项 | 理由 |
|--------|------|
| FC 直转目标态对照(`docs/fc-transcribe-design.md`) | 契约一致性以小程序、FC、Worker 三处实现的现状互相对照为准,不引入目标态设计;切换障碍分析归 FC 直转切换里程碑 |
| 渗透测试级安全审计 | 非本次审计维度;顺带发现的安全问题仍记录并标注"顺带发现" |
| 逐行审计 vendored `docs/example/start-fc-main/`(29MB, 1003 文件) | 非项目代码;其存在本身作为一条发现,并从所有扫描中排除(见扫描排除清单) |
| 数值化质量评分 | 不可证伪,引发对数字而非发现的争论 |
| 精确工时估计 | 假精确;统一用 S/M/L/XL 分档(见工作量分档章节) |

### 双语言适配声明

本仓库为双语言仓库,审计判断标准分别适配:

- **Python 3.11+**(`apps/worker/`、`apps/fc/`):以 mypy-strict 与 ruff(`E`, `F`, `I`, `UP`, `B`)为既定质量门禁基准;`apps/fc/*/handler.py` 因模块名冲突为 ruff-only(pyproject.toml 已注释缘由),审计时不得以"缺 mypy 覆盖"苛责该豁免本身。
- **JavaScript(WeChat 小程序 CommonJS)**(`apps/miniprogram/`):无 npm 依赖、无构建步骤;以仓库既有惯例(纯逻辑 + IO 注入、`node --test` 可测性、`miniprogram_lint.py` 自定义门禁)为基准,不引入外部 JS lint 标准。

### 证据提取命令(标准做法)

```bash
git show 5927f36:apps/miniprogram/config.js | sed -n '1,30p'   # 按基线读文件(带行号定位)
git grep -n 'fragment_id' 5927f36 -- apps/                      # 按基线检索
git diff --stat 5927f36 -- apps/ scripts/ docs/                 # 零 diff 验证(期望空输出)
```

三条命令均已在本仓库实测可用。取证只用前两类命令;第三条是每阶段收尾的污染报警器,不是取证前提。

## 扫描排除清单

以下九条路径从常规逐文件审计扫描中排除(per D-05):

| # | 排除路径 | 理由 |
|---|----------|------|
| 1 | `docs/example/start-fc-main/` | vendored 外部仓库(29MB),非项目代码 |
| 2 | `scripts/ralph/` | agent 元工具,非部署/验证工具链 |
| 3 | `.claude/` | AI 工具目录(四套之一) |
| 4 | `.cursor/` | AI 工具目录(四套之二) |
| 5 | `.codex/` | AI 工具目录(四套之三) |
| 6 | `.agents/` | AI 工具目录(四套之四) |
| 7 | `openspec/` | 工作流状态,非审计对象 |
| 8 | `build/` | 构建产物 |
| 9 | `tests/audio/` | 二进制音频 fixture;fixture manifest/描述文件仍纳入 DOC 维度文档一致性审计 |

**AUDIT-02 scripts/ 审计范围缩窄(per D-06):** 部署与验证工具链维度(TOOL)的 scripts/ 审计范围仅为:`scripts/test_asr.py`、`scripts/fetch_test_fixtures.py`、`scripts/gen_worker_config.sh`(即 scripts/ 减去 ralph/)。

**存在级问题处置(per D-09):** 被排除目录的存在级问题照常进台账——如 vendored 仓库膨胀、四套 AI 工具目录漂移、`scripts/ralph/` 在仓——严重度预期 LOW/INFO,但不逐文件审计。排除 ≠ 免记录。

## 秘密扫描穿透规则

**穿透声明(per D-07):** 秘密/凭证扫描穿透所有排除目录,对基线 commit 全量扫描——`git grep <pattern> 5927f36 -- .` 天然覆盖该 commit 全部已跟踪文件(含 vendored、四套 AI 工具目录、`scripts/ralph/`),且免疫工作树未跟踪垃圾。

**穿透理由(先例):** `scripts/test_asr.py` 曾提交过期预签名 OSS URL(签名 URL 模式,`OSSAccessKeyId=` + `Signature=` 参数)。排除目录不扫描秘密会漏掉同类入库事故,故秘密扫描无排除区。

**五类模式命令(Phase 3 执行,本章程定义规则):**

```bash
git grep -nE 'LTAI[0-9A-Za-z]{10,}' 5927f36 -- .                # 1. 长期 AK ID(LTAI 前缀)
git grep -nE 'OSSAccessKeyId=' 5927f36 -- .                     # 2. 签名 URL(test_asr.py 先例模式)
git grep -nE 'Signature=[0-9A-Za-z%+/=]{16,}' 5927f36 -- .      # 3. 签名参数
git grep -niE 'app_?secret[[:space:]]*[:=]' 5927f36 -- .        # 4. appsecret 字面量赋值
git grep -nE 'SecurityToken=|security_token' 5927f36 -- .       # 5. STS token
```

**命中 ≠ 发现:** 模式命中后必须人工核实(排除测试假值、文档示例、变量名自身),核实后才进台账。

**秘密类证据红线:** 引用秘密类证据只写 `path:line @ 5927f36` + 模式名(如 `OSSAccessKeyId=` 签名 URL 模式),绝不复制值本体——哪怕已过期。台账与章程一旦提交即永久入库,复制值本体构成二次泄露。

## 严重度体系

五级严重度(CHARTER-02),每级以 SoniScope 场景锚点定义。边界情况以下表锚点示例封死;不存在锚点之外的裁量空间——若某发现无法对号入座,取其影响最接近的锚点级别并在理由中写明对应关系。

| 级别 | SoniScope 场景锚点 |
|------|--------------------|
| **CRITICAL** | 用户录音**数据丢失或不可恢复**(OSS 对象被删、`.done` 早写导致片段永久跳过);**有效长期凭证泄露**(在库 LTAI AK、`WX_APP_SECRET` 明文且仍有效);**认证绕过**(openid allowlist 失效) |
| **HIGH** | **静默转写失败**(音频安全但用户无感知得不到转写,如契约活跃失配使上传对 Worker 永久不可见);STS 权限越界(单对象键策略失效);崩溃恢复产出损坏工件 |
| **MEDIUM** | 潜伏失配(当前参数/格式下不触发,变更即爆);可诱发高危误操作的误导性文档(如 runbook 步骤与实态不符);已过期凭证曾入库(泄露习惯风险) |
| **LOW** | 技术债与非关键路径重复实现;文档死链/路径失效;lint/typecheck 覆盖缺口;非热路径性能问题 |
| **INFO** | 存在级观察(vendored 仓库膨胀、四套 AI 工具目录漂移——呼应 D-09 预期定级);风格不一致;值得记录但无行动必要的事实 |

**评级理由格式:** 每个评级必须附一行定性理由,固定格式为 `影响:…;可能性:…`。禁止任何数值化评分形式——数值分数不可证伪,会引发对数字而非发现本身的争论(REQUIREMENTS.md Out of Scope 禁令);理由只用场景语言,不出现任何评分数字或量表。

**顺带安全发现:** 不设自动升级规则。安全类顺带发现与其他发现同用影响×可能性定级,仅在台账条目加 `顺带发现(out-of-dimension)` 标注,保持单一定级口径。

## 工作量分档

S/M/L/XL 四档(CHARTER-03),判定标准如下;**禁止小时级精确估计**——任何发现的工作量只用档位表达,不写具体时长数字。

| 档位 | 判定标准 | SoniScope 示例 |
|------|----------|----------------|
| **S** | ≤单文件 | 改 `apps/miniprogram/config.js` 一处常量 |
| **M** | 同组件多文件 | `fc_shared` 内多文件调整 |
| **L** | 跨组件 | fragment_id 格式变更需 FC + Worker + 小程序三处同步 |
| **XL** | 需独立阶段 | 实现 `transcribe-audio` FC 函数 |

## 发现记录 schema 与台账布局

### 九字段 schema(CHARTER-05)

每条发现一个 Markdown 小节,九字段固定顺序,第一字段(ID)即小节标题本身:

```markdown
### F-CON-01: <一行标题>

- **维度:** 契约一致性 (CON)
- **严重度:** HIGH — 影响:上传对 Worker 永久不可见(静默数据滞留);可能性:仅在 fragment_id 格式变更时触发,当前格式下不触发
- **证据:** `apps/fc/shared/fc_shared/sts.py:95-102 @ 5927f36`
  > (引用的代码片段,从 git show 提取)
- **修复建议:** <一段>
- **工作量:** M(同组件多文件)
- **关联发现:** F-CODE-03;关联线索: HYP-07
- **上线判定:** (Phase 5 填,留空;取值 BLOCKER / PRE-LAUNCH / POST-LAUNCH)
- **状态:** draft(Phase 5 校准后改为 calibrated)
```

字段说明:

1. **ID** — `###` 标题本身,格式见下方 ID 规则
2. **维度** — 五维度之一(中文名 + 短码)
3. **严重度** — 五级之一 + 影响×可能性一行理由(格式见严重度体系章节)
4. **证据** — `path:line @ 5927f36` + 从 `git show` 提取的引用片段;秘密类证据遵守值本体红线
5. **修复建议** — 一段,可直接驱动修复里程碑
6. **工作量** — S/M/L/XL 之一(见工作量分档章节)
7. **关联发现** — 承载发现↔发现与发现↔HYP 链接,喂 RPT-08 可追溯映射表
8. **上线判定** — Phase 5 填,建槽留空;取值 BLOCKER / PRE-LAUNCH / POST-LAUNCH
9. **状态** — `draft` / `calibrated`,Phase 5 校准留痕

### ID 规则

- **发现:** `F-<维度码>-NN` — `F-CON-NN` / `F-CODE-NN` / `F-TOOL-NN` / `F-DOC-NN` / `F-TEST-NN`。加 `F-` 前缀以区别于需求 ID(`CONTRACT-NN` 已被 REQUIREMENTS.md 占用)。
- **假设:** `HYP-NN`(CONCERNS.md 线索转写,Phase 4 关闭)
- **Do-NOT-fix:** `DNF-NN`(RPT-05 预录入)

### 台账布局

`findings/` 按维度分 5 个文件:

| 文件 | 维度 | 写入阶段 |
|------|------|----------|
| `findings/contract.md` | CON | Phase 2 |
| `findings/code.md` | CODE | Phase 3 |
| `findings/toolchain.md` | TOOL | Phase 3 |
| `findings/docs-config.md` | DOC | Phase 4 |
| `findings/test.md` | TEST | Phase 4 |

分文件理由:Phase 2 与 Phase 3 同波次并行写入,单一台账文件会产生写冲突;每阶段只写自己维度的文件,Phase 5 汇总合并。

台账与报告一律落在 `.planning/audit/`,严禁写入 `apps/`、`scripts/`、`docs/`(零 diff 硬约束)。配套文件 `HYPOTHESES.md`(假设清单)与 `DO-NOT-FIX.md`(RPT-05 预录入)由本阶段 plan 02 产出。

---
*审计章程定稿: 2026-07-04*
