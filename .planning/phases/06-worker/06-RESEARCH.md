# Phase 6: Worker 失败路径隔离与告警 - Research

**Researched:** 2026-07-06
**Domain:** Python 3.11 (mypy-strict) Worker daemon — 失败计数账本、阈值隔离、显式告警、查询/清除 CLI
**Confidence:** HIGH — 无外部依赖,全部基于已读源码 + 仓库既有资产;所有集成点行号经本次会话 `Read` 核实

## Summary

本 phase 关闭审计发现 F-CODE-02:让 Worker 对**下载/标准化前置阶段**的持久失败对象(sha256 失配、下载 error、探测/转码失败)有按 `fragment_id` 的失败计数账本、达阈值后从下载工作集排除(隔离)、隔离时打显式告警,并提供 `quarantine-list`/`clear-quarantine` 两个查询/清除 CLI。这是纯代码 + 配置改动,无新增外部依赖——账本用 stdlib `json` + 仓库既有 `recovery.atomic_write_json` 原子写,不引入任何第三方包。

关键发现:**生产运行路径是 `pipeline.py`,不是 `poller.py`**。`make worker-run` → `poller.run_worker_run`(poller.py:455)→ `pipeline.run_worker_pipeline`(pipeline.py:511)→ `run_pipeline_loop`/`run_pipeline_once`。`poller.py` 的 `poll_once`/`poll_loop`(poller.py:322/355)是 US-021 的早期独立循环,**当前无生产调用方**(仅 `run_test_poll_interval` 用于间隔校验)。因此隔离逻辑的**失败计数递增点**和**告警发出点**必须落在 `pipeline.run_pipeline_once`(pipeline.py:407-441),而**隔离跳过注入点**落在两条路径共用的纯函数 `plan_downloads`(poller.py:177)——两个 caller(poller.py:331、pipeline.py:397)都调它,在此加一个 `quarantine_check` 注入即同时覆盖。

**Primary recommendation:** 新建 `apps/worker/src/soniscope_worker/quarantine.py`,承载纯逻辑(账本 schema、`is_quarantined` 判据、`record_failure` read-modify-write、告警行组装)+ IO(`load_ledger`/`save_ledger` 复用 `atomic_write_json`);给 `plan_downloads` 增加可选 `quarantine_check: Callable[[str], bool] | None` 参数(与既有 `done_check` 同构),在 `pipeline.run_pipeline_once` 里读账本注入、失败时递增、跨阈值时告警;`PollConfig` 加 `max_fragment_failures: int = 3`;CLI 加 `quarantine-list` / `clear-quarantine` 两个子命令 + Makefile 两个目标。**隔离判据写成与工作集解耦的纯函数**(D-10 + deferred FC 迁移复用要求)。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** 用**单一 JSON 账本**记录按 fragment 的失败历史,位于 `inbox/failed/ledger.json`(与既有转码留档 `inbox/failed/<id>.part` 同目录)。key=`fragment_id`,value 至少含 `{attempt 计数, 最后失败原因/阶段, first_seen, last_seen}`。一个账本同时支撑 WKR-01(历史)、WKR-02(阈值判定)、WKR-03(诊断)。
- **D-02:** 不用纯进程内计数 — 架构红线要求 Worker 状态可从磁盘推导,重启不能丢失隔离状态。
- **D-03:** 账本写入沿用仓库既有原子写协议(temp → atomic rename),与 `inbox/`/`tmp`/`fragments/` 同文件系统前提一致。Worker 单线程轮询,账本无并发写风险。
- **D-04:** 阈值**进 `config.yaml`**(在 `PollConfig` 新增字段,如 `max_fragment_failures`),Pydantic 校验,**默认 3**(与既有 `RETRY_DELAYS_SECONDS` 最多 3 次的重试约定一致)。运维改值无需改代码。
- **D-05:** 所有隔离类失败类型**共用同一个阈值**,不按类型分开(sha256 失配虽极低可能,仍走同一阈值,保持逻辑简单)。
- **D-06:** 隔离**持久保留**直到 operator 显式处理,不自动过期重试(避免周期性回到无界循环,违背"持久失败应被显式发现和处理"的初衷)。
- **D-07:** 新增一个**专用 CLI 子命令 + make 目标**(命名如 `clear-quarantine` / `worker-clear-quarantine`,支持 `FRAGMENT_ID=<id>` 单条或 `--all`)清空账本对应条目 → 下一轮重新下载。**不扩展 `retranscribe`**:`retranscribe` 用 `scan_fragments` 面向已有 `audio.wav` 的 fragment 目录,而隔离对象在 sha256/转码阶段就失败、从未生成 fragment 目录,两者正交,职责分离。
- **D-08:** WKR-03 用**日志 + 查询 CLI 两者**:隔离发生时打一条**显式告警日志行**,含四要素 `fragment_id` + 失败原因 + attempt count + 下一步处理建议(如"已隔离,运维用 clear-quarantine 解除")。沿用既有 `typer.echo` / 注入 `log` 通道。新增一个**查询 CLI**(如 `quarantine-list` / `worker-quarantine-list`)列出当前隔离清单,与 `clear-quarantine` 配套 — 一个看、一个清。
- **D-09:** 计入隔离账本的失败**仅限 fragment 目录创建前的前置失败**:`sha256_mismatch` + 下载 `error` + 探测/标准化(ffmpeg)失败。**不含 NLS 转写失败** — 转写失败发生在 `audio.wav` 已就绪之后,由 `process_pending` 恢复,且 NLS 自身已有 5/15/45s 重试;纳入会与既有语义重叠并可能误隔离可恢复片段。此范围与 F-CODE-02 原始判定一致。
- **D-10:** 既有 `.done` 幂等跳过路径必须保持不变(成功标准 #4)。隔离逻辑只作用于**无 `.done` 且失败计数超阈值**的对象;已完成 fragment 永远走原有跳过路径。
- **D-11:** 同步修正 `audio.py` `_archive_failed` docstring 中"不再重试"的错误表述,使其与新的隔离语义一致(留档本身不阻止重试,阈值隔离才阻止)。

### Claude's Discretion

- 账本 JSON 的确切字段命名、schema 版本字段是否需要、CLI 子命令的精确命名与 flag 形态 — 交给 planning/研究阶段按仓库既有命名约定(`snake_case`、UPPER_SNAKE 常量、每 make 目标映射一 CLI 子命令)定稿。
- 隔离对象在账本外是否额外落一个 skiplist 文件,还是账本本身即隔离依据(attempt >= 阈值即视为隔离) — 倾向后者(单一真相源),但由研究确认与 `plan_downloads` 的集成点最简。

### Deferred Ideas (OUT OF SCOPE)

- **NLS 转写失败的隔离/计数** — 转写阶段失败(fragment 目录已建)有独立恢复语义与 NLS 自带重试,本 phase 不纳入;若未来发现转写侧也无界重试,另开条目。
- **F-CON-04(verify-upload 校验 sha256)** — POST-LAUNCH,独立工作包,不在 v1.1。
- **F-CODE-03(孤儿 `*.tmp` 清理)/ F-CODE-04(`.env` 无界向上搜索)** — 同为 POST-LAUNCH Worker 债务,不在本 phase。
- **账本自动过期/TTL 重试策略** — 明确否决(D-06)。
- **FC 直转迁移复用面**(`docs/fc-transcribe-design.md` §3.6)— 仅登记,不动手。见 Assumptions/Architecture 中"解耦要求"。
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WKR-01 | Worker can persist per-fragment failure history for `sha256_mismatch`, audio probe failure, and audio standardization failure. | 账本模块(§Standard Stack `quarantine.py`)+ 计数递增点(pipeline.run_pipeline_once:407-441 消费 `ObjectOutcome.status != downloaded` 与 `process_part` 返回 `STAGE_STANDARDIZE` failed)。账本落 `inbox/failed/ledger.json`,`atomic_write_json` 原子写(D-01/D-03)。 |
| WKR-02 | Worker can stop unbounded redownload/reprocess loops by skipping or quarantining a fragment after a configured failure threshold. | 隔离跳过注入点 `plan_downloads`(poller.py:177)新增 `quarantine_check` 参数(与 `done_check` 同构),新增 `ScanPlan.skipped_quarantined`;阈值 `PollConfig.max_fragment_failures` 默认 3(config.py:51,D-04)。纯判据 `is_quarantined(attempt, threshold)`。 |
| WKR-03 | Operator can identify quarantined fragments from explicit alert logs or local diagnostic state (fragment_id, reason, attempt, next action). | 告警行四要素固定顺序(D-08);查询 CLI `quarantine-list` + 清除 CLI `clear-quarantine`(cli.py 委托模式:27,Makefile 目标参考 retranscribe:119)。 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **仅审计→修复里程碑,窄爆炸半径**:只修 F-CODE-02,不顺带修 F-CODE-01/03/04、F-CON-04(仅 D-11 的 docstring 交集动作可做)。
- **双语言仓库,本 phase 纯 Python**:改动全在 `apps/worker/src/soniscope_worker/`;无小程序 JS 改动。
- **mypy --strict**:覆盖 `apps/worker/src` + `apps/worker/tests`(pyproject.toml:32,`files=[...]`)。新模块必须全量类型注解,含测试函数 `-> None`。
- **ruff**:`E,F,I,UP,B`,line-length 100,target py311(pyproject.toml:47-53)。
- **`from __future__ import annotations`**:新模块首行 import 加(仓库 20/26 模块惯例)。
- **纯逻辑 + 注入 IO**:判据(是否超阈值)必须纯函数;账本读写 IO 用可注入 callable,单测不触盘/不触网。
- **磁盘即权威状态**:隔离状态落盘可推导,重启不丢(D-01/D-02)。
- **原子写协议**:temp → rename;复用 `recovery.atomic_write_json`(D-03),勿自造。
- **UPPER_SNAKE 模块常量并被测试断言**:失败原因/状态、账本 schema 键、告警前缀应为模块级常量(如 `ObjectOutcome.status`、`STAGE_*` 惯例)。
- **每 make 目标映射一 CLI 子命令**:两个新命令各配一个 Makefile 目标。
- **Chinese 注释 + 模块 docstring(purpose + 关联发现/AC + invariants)**:沿用。
- **秘密红线**:账本只存 `fragment_id` + 原因 + 计数 + 时间戳,绝不含 AK/token/明文(本 phase 无秘密面,但告警行不得回显敏感值)。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 失败计数账本读写(WKR-01) | Worker pipeline (本地磁盘 IO) | — | 状态从磁盘推导;唯一在本地进程 `inbox/failed/` 落盘 |
| 隔离判据(attempt ≥ 阈值 → 排除,WKR-02) | Worker 纯逻辑 (`quarantine.py`) | — | 无 IO 纯函数,可单测;FC 迁移可平移换输入(deferred) |
| 隔离跳过集成(从下载工作集排除) | Worker pipeline (`plan_downloads` 注入点) | — | `plan_downloads` 是两条循环共用的纯计划函数 |
| 阈值配置(D-04) | Worker config (Pydantic) | — | `config.yaml` 唯一配置真相源 |
| 告警发出(WKR-03) | Worker pipeline (注入 `log`) | — | 沿用既有 `typer.echo`/注入 log 通道 |
| 查询/清除隔离(WKR-03/D-07) | Worker CLI (Typer) | Worker 纯逻辑(账本增删) | 每 make 目标映射一 CLI 子命令 |

**Not this phase:** OSS/FC/miniprogram 各层均无改动;NLS 转写失败(fragment 目录已建之后)不计入账本(D-09)。

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `json` | 3.11 | 账本序列化/反序列化 | 已被 `recovery.atomic_write_json` / `retranscribe._read_manifest` 使用,零新依赖 [VERIFIED: 源码 recovery.py:63-65] |
| Python stdlib `pathlib.Path` | 3.11 | 账本路径 `inbox/failed/ledger.json` | 全仓路径操作惯例 [VERIFIED: 源码] |
| `pydantic` (v2) | 已装 (config.py 依赖) | `PollConfig.max_fragment_failures` 校验 | 既有 config schema 用它;`BaseModel` 字段加默认值 + 校验 [VERIFIED: 源码 config.py:12,51] |
| `typer` | >=0.12 (已装) | 两个新 CLI 子命令 | 全部 CLI 用它,委托模式固定 [VERIFIED: 源码 cli.py:7,18] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `recovery.atomic_write_json` | 仓库内 | 账本原子写(temp→rename) | 每次 `save_ledger`(D-03) [VERIFIED: 源码 recovery.py:63] |
| `locks.fragment_lock` | 仓库内 | 若账本 read-modify-write 需跨进程互斥 | 见 Pitfall 3:单进程轮询无需,但 CLI clear 与 worker 并发写属边缘场景 [VERIFIED: 源码 locks.py:40] |
| `paths.inbox_failed_dir()` | 仓库内 | 解析 `$SONISCOPE_HOME/inbox/failed/` | 账本目录定位 [VERIFIED: 源码 paths.py:83] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 单一 `ledger.json`(D-01) | 每 fragment 一个 `<id>.fail.json` | 违背 D-01 单账本决策;operator 需翻多文件;放弃 |
| 账本即隔离依据(attempt≥阈值) | 额外 skiplist 文件 | 双真相源易漂移;Discretion 已倾向单账本;采纳单账本 |
| stdlib `json` | pydantic 账本 model | 账本 schema 简单(dict of dict),pydantic 增复杂度且账本非配置;用 dataclass + json 更贴 recovery/poller 惯例 |

**Installation:** 无 — 零新依赖。所有能力用 stdlib + 已装的 pydantic/typer + 仓库内既有函数实现。

## Package Legitimacy Audit

**N/A — 本 phase 不安装任何外部包。** 全部实现基于 Python stdlib(`json`/`pathlib`/`datetime`)、已装依赖(`pydantic` v2、`typer`)与仓库内既有模块(`recovery`/`locks`/`paths`/`config`)。无 `requirements.txt` / `pyproject.toml` 依赖变更。

## Architecture Patterns

### System Architecture Diagram

```text
                        make worker-run
                              │
                    poller.run_worker_run (poller.py:455)
                              │  (纯委托)
              pipeline.run_worker_pipeline (pipeline.py:511)
                              │
              pipeline.run_pipeline_loop (pipeline.py:445)
                              │
        ┌─────────── run_pipeline_once (pipeline.py:375) ────────────┐
        │                                                            │
   source.list_recordings()                              [每轮] load_ledger()
        │                                                     inbox/failed/ledger.json
        ▼                                                            │
   plan_downloads(listings,                                          │
     done_check=…,                ◄──── 注入 ────  quarantine_check(fid):
     quarantine_check=…)  (poller.py:177)          is_quarantined(ledger[fid].attempt,
        │                                                            threshold)  [纯]
        ├─ skipped_done          (既有 .done 幂等,D-10 不变)
        ├─ skipped_quarantined   (新增:超阈值排除,WKR-02)
        ├─ ignored_keys
        └─ to_download
              │
              ▼  for item in to_download:
        process_plan(item)  (poller.py:248) → ObjectOutcome.status
              │
      ┌───────┴─────────────────────────────────────────┐
      │ status == "downloaded"          status != "downloaded"
      │        │                         (sha256_mismatch / error)  ── D-09 计入
      ▼        │                                  │
  process_part(part) (pipeline.py:150)            ▼
      │  standardize() (audio.py:145)      record_failure(ledger, fid, reason)
      │        │                                  │  attempt += 1
      │  std.ok == False (STAGE_STANDARDIZE) ── D-09 计入   │
      │        └────────────► record_failure ─────┤
      │  (transcribe/manifest 失败:fragment 目录已建 → 不计入,D-09)
      ▼        │                                  ▼
  成功 → .done │                          if attempt == threshold:
  → clear_entry(ledger, fid) (可选,见 Open Q)     emit 告警行(4 要素,WKR-03)
                                                  save_ledger()

  独立 CLI 进程:
   quarantine-list  → load_ledger → 打印隔离清单(attempt ≥ 阈值者)
   clear-quarantine → load_ledger → 删 FRAGMENT_ID 条目 或 --all → save_ledger
                       → 下一轮 plan_downloads 不再排除 → 重新下载
```

### Recommended Project Structure
```
apps/worker/src/soniscope_worker/
├── quarantine.py       # 新增:账本 schema + 纯判据 is_quarantined + record_failure
│                       #       + load_ledger/save_ledger(IO)+ 告警行组装 + run_quarantine_list/run_clear_quarantine
├── poller.py           # 改:plan_downloads 加 quarantine_check 参数;ScanPlan 加 skipped_quarantined
├── pipeline.py         # 改:run_pipeline_once 读账本注入 + 失败递增 + 跨阈值告警;clear on success
├── config.py           # 改:PollConfig 加 max_fragment_failures;masked_summary 加一行
├── audio.py            # 改:_archive_failed docstring 修正(D-11,仅注释)
└── cli.py              # 改:加 quarantine-list / clear-quarantine 两个 @app.command
apps/worker/tests/
└── test_quarantine.py  # 新增:纯判据多轮累积、阈值隔离、告警、CLI;既有 test_pipeline/test_poller 增回归断言
Makefile                # 改:加 quarantine-list / clear-quarantine 两个目标
```

### Pattern 1: 注入式跳过集成(与 done_check 同构)
**What:** `plan_downloads` 已用 `done_check: Callable[[str, str], bool]` 注入 `.done` 判定。隔离跳过用同一手法:加 `quarantine_check: Callable[[str], bool] | None = None`。
**When to use:** WKR-02 隔离排除。默认 `None` 保持既有 caller 与全部现有测试不变(向后兼容)。
**Example:**
```python
# Source: 改造 poller.py:177-197(既有 done_check 模式)
@dataclass(frozen=True)
class ScanPlan:
    to_download: list[PollPlan] = field(default_factory=list)
    skipped_done: list[str] = field(default_factory=list)
    skipped_quarantined: list[str] = field(default_factory=list)  # 新增
    ignored_keys: list[str] = field(default_factory=list)

def plan_downloads(
    listings: list[OssListing],
    *,
    done_check: Callable[[str, str], bool],
    quarantine_check: Callable[[str], bool] | None = None,  # 新增,默认 None 向后兼容
) -> ScanPlan:
    plan = ScanPlan()
    for lst in listings:
        fid = fragment_id_from_key(lst.key)
        if fid is None:
            plan.ignored_keys.append(lst.key)
            continue
        date = date_of(fid)
        if done_check(fid, date):           # D-10:.done 幂等永远优先
            plan.skipped_done.append(fid)
            continue
        if quarantine_check is not None and quarantine_check(fid):  # WKR-02
            plan.skipped_quarantined.append(fid)
            continue
        plan.to_download.append(PollPlan(fid, lst.key, date, lst.size))
    return plan
```

### Pattern 2: 纯隔离判据 + 解耦(FC 迁移复用要求)
**What:** 隔离**决策**是纯函数,只吃 `(attempt, threshold)`,不吃 `plan_downloads` 的下载集本身。这样 deferred 的 FC 直转迁移可把输入从下载集平移到 `recordings−transcripts` 差集而无需改判据(CONTEXT deferred + D-10 动机)。
**When to use:** WKR-02 判据核心。
**Example:**
```python
# Source: 新建 quarantine.py(纯逻辑,无 IO)
def is_quarantined(attempt: int, *, threshold: int) -> bool:
    """attempt 达到/超过阈值即视为已隔离(单一真相源:账本本身即隔离依据,Discretion)。"""
    return attempt >= threshold
```
判据独立于"谁在调它"——`plan_downloads` 传的 `quarantine_check` 只是 `lambda fid: is_quarantined(ledger.get(fid, 0), threshold=cfg)` 的薄封装。

### Pattern 3: 账本 read-modify-write 复用原子写
**What:** 失败递增 = 读账本 → 改一条 → 原子写回。复用 `recovery.atomic_write_json`(D-03),勿自造 temp/rename。
**Example:**
```python
# Source: 新建 quarantine.py,IO 段;复用 recovery.py:63 atomic_write_json
from soniscope_worker.recovery import atomic_write_json

LEDGER_FILENAME = "ledger.json"

def ledger_path(failed_root: Path) -> Path:
    return failed_root / LEDGER_FILENAME

def load_ledger(failed_root: Path) -> dict[str, dict[str, Any]]:
    p = ledger_path(failed_root)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}          # 损坏账本降级为空,不杀守护进程(Pitfall 2)
    return data if isinstance(data, dict) else {}

def save_ledger(failed_root: Path, ledger: dict[str, dict[str, Any]]) -> None:
    atomic_write_json(ledger_path(failed_root), ledger)   # temp→rename,D-03
```

### Pattern 4: 告警行四要素固定顺序(便于 grep + pytest 断言)
**What:** D-08 要求告警含 `fragment_id` / reason / attempt / next-action,固定顺序。
**Example:**
```python
# Source: 新建 quarantine.py;沿用 poller/pipeline 的 "[标签] ..." 日志前缀惯例
QUARANTINE_ALERT_PREFIX = "[quarantine]"
NEXT_ACTION_HINT = "已隔离,运维用 `make clear-quarantine FRAGMENT_ID=<id>` 解除后下一轮重下"

def quarantine_alert_line(fragment_id: str, reason: str, attempt: int) -> str:
    return (
        f"{QUARANTINE_ALERT_PREFIX} fragment_id={fragment_id} reason={reason} "
        f"attempt={attempt} next={NEXT_ACTION_HINT}"
    )
```

### Anti-Patterns to Avoid
- **把隔离判定硬编进 poller 下载循环**:会随 poller 被 FC 迁移删除;必须是解耦纯函数(deferred 复用要求)。
- **在 `process_plan`(poller.py:248)内递增账本**:该函数是无 IO-side-effect 的单对象处理纯逻辑(除删本地 .part);计数应在**消费端** `run_pipeline_once` 递增,保持 `process_plan` 可单测不触账本。
- **NLS 转写失败递增账本**:违背 D-09;转写失败发生在 fragment 目录已建之后,由 `process_pending` + NLS 自带重试处理。
- **自造 temp+rename 写账本**:必须复用 `atomic_write_json`(D-03/CLAUDE.md)。
- **改 `retranscribe.py` 语义**:D-07 明确正交;隔离对象从未生成 fragment 目录,`scan_fragments` 看不到它们。
- **让隔离逻辑绕过或改动 `.done` 判定**:D-10 红线;`skipped_done` 分支永远先于 `skipped_quarantined`。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 账本原子写 | 自造 mkstemp+os.replace | `recovery.atomic_write_json` (recovery.py:63) | 已实现三段式协议 + 异常清理 [VERIFIED: 源码] |
| `.done` 完成标记 | 新完成检测 | 既有 `done_marker_path`/`create_done_marker` | D-10 不动既有幂等路径 [VERIFIED: 源码 poller.py:74, recovery.py:101] |
| fragment 目录锁 | 自造 flock | `locks.fragment_lock` (locks.py:40) | 仅账本并发写边缘场景才需;已实现跨进程 advisory 锁 [VERIFIED: 源码] |
| 运行时目录解析 | 自造路径拼接 | `paths.inbox_failed_dir()` (paths.py:83) | 统一 `$SONISCOPE_HOME` 解析 [VERIFIED: 源码] |
| 配置校验 | 手写字段检查 | pydantic `PollConfig` 字段 + 默认值 | 既有 `_collect_validation_errors` 汇总缺失项 [VERIFIED: 源码 config.py:51,109] |

**Key insight:** 本 phase 90% 是"把既有资产接线",不是造新机制。唯一真新代码是 `quarantine.py` 的账本 schema + 纯判据 + 告警组装。

## Runtime State Inventory

**触发判定:本 phase 是"新增运行时状态"而非 rename/refactor/migration。** 但因引入一个**新的持久磁盘文件**(`inbox/failed/ledger.json`),仍逐项确认既有运行时状态不受破坏:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | 新增 `inbox/failed/ledger.json`(本 phase 创建的唯一新持久文件);既有 `inbox/failed/<id>.part` 转码留档并置**不受影响** | 新建账本读写代码;无迁移(全新文件,首轮为空 `{}`) |
| Live service config | 无 — 本 phase 不动 OSS/FC/NLS 任何云端配置 | None — 纯本地 Worker 改动 |
| OS-registered state | 无 — Worker 是 `make worker-run` 前台进程,无 launchd/systemd/pm2 注册 | None — 验证:CLAUDE.md 述 Worker 为 long-running local process,无 OS 注册 |
| Secrets/env vars | 无新增 — 账本不含秘密;`max_fragment_failures` 非秘密配置项 | None |
| Build artifacts | 无 — 纯 src 改动,不改 `pyproject.toml` 依赖/打包;`quarantine.py` 随 hatchling wheel 自动纳入 `src/soniscope_worker` | None(不需重装,editable/uv workspace 自动可见) |

**恢复扫描交互(必须验证):** `recovery.recover_inbox`(recovery.py:196)按后缀清理 `inbox/` 下 `*.part` 与 `*.wav.tmp`。账本名 `ledger.json` **不匹配** `.part`/`.wav.tmp` 后缀,故启动恢复扫描**不会误删账本**——但账本落在 `inbox/failed/`(inbox 的子目录),而 `_remove_by_suffix`(recovery.py:181)只 `root.iterdir()` 非递归,不进子目录。**结论:账本安全,恢复扫描不触及 `inbox/failed/`。** 计划阶段应加一条测试断言 recover 后 ledger.json 仍在。

## Common Pitfalls

### Pitfall 1: 改错循环(poller vs pipeline)
**What goes wrong:** 把计数/告警加到 `poller.poll_once`(poller.py:322),但生产不走它——`make worker-run` 走 `pipeline.run_pipeline_once`。改了 poller 则线上无效果。
**Why it happens:** poller.py 与 pipeline.py 各有一套 list→plan→process 循环;poller 的那套是 US-021 遗留独立循环,仅 `run_test_poll_interval` 引用。
**How to avoid:** **计数递增点 + 告警发出点落 `pipeline.run_pipeline_once`(pipeline.py:407-441)**;隔离跳过注入点落**共用**的 `plan_downloads`(两 caller 都调:poller.py:331、pipeline.py:397)。
**Warning signs:** 若只有 poller.py 改动而 pipeline.py 未动,线上不生效。

### Pitfall 2: 账本损坏杀死守护进程
**What goes wrong:** `json.loads` 遇半写/手改坏的 `ledger.json` 抛异常,若未捕获会中断轮询循环。
**Why it happens:** kill -9 落在写账本瞬间(虽有原子写,但边缘)、或运维手误编辑。
**How to avoid:** `load_ledger` catch `(OSError, json.JSONDecodeError)` 降级为 `{}`(见 Pattern 3),沿用 `pipeline.process_pending`(pipeline.py:327)对损坏 manifest 的同款容错。
**Warning signs:** 单轮扫描抛未捕获异常——`run_pipeline_loop`(pipeline.py:499)有兜底 `except` 但会丢当轮。

### Pitfall 3: 账本并发写(worker vs clear-quarantine CLI)
**What goes wrong:** Worker 轮询正写账本递增,同时运维跑 `make clear-quarantine` 删条目——两个进程 read-modify-write 同一 `ledger.json`,后写覆盖前写(lost update)。
**Why it happens:** D-03 假设"单线程轮询无并发写风险",但 clear-quarantine 是**独立进程**,与 worker 进程并发。
**How to avoid:** 两种可接受方案(计划阶段选一):(a) 接受该竞态——原子 rename 保证账本永不半写,最坏是一次 clear 被一次 record 覆盖,运维重跑 clear 即可(低频人工操作,D-06 隔离持久,损失有限);(b) 账本读改写包一层 `fragment_lock(tmp_root, "_ledger")` 或专用锁文件(locks.py:40 已支持)。**推荐 (a) 并在告警/文档注明**,除非计划阶段判定 (b) 成本低。研究判定:(a) 足够,因隔离态 attempt≥阈值后 worker 不再递增该 fid(已被 `skipped_quarantined` 排除,不再 process),故 clear 与 record 撞同一 fid 的窗口极小。
**Warning signs:** clear 后下一轮该 fid 仍被跳过。

### Pitfall 4: 成功后是否清账本条目(幂等/回归)
**What goes wrong:** fragment 失败 2 次(未达阈值 3)后第 3 次成功,若不清账本条目,账本残留 `attempt=2`;下次同 fid 再失败 1 次即达阈值被误隔离。
**Why it happens:** F-CODE-02 场景是"持久失败",但偶发失败后成功属正常。
**How to avoid:** `process_part` 成功(`FragmentResult.ok`,pipeline.py:276)后调 `clear_entry(ledger, fid)`。这也让"既有成功路径"账本干净——但注意:成功后 `.done` 已建,下一轮 `skipped_done` 优先,该 fid 本就不会再 process。清条目主要防"未来同 fid 复用"与账本无限增长。**计划阶段决策点**(见 Open Questions Q1)。
**Warning signs:** test 覆盖"失败 N 次后成功 → 账本无残留"。

### Pitfall 5: 阈值语义歧义(attempt 从 0 还是 1;`>=` 还是 `>`)
**What goes wrong:** "默认 3"到底是"第 3 次失败后隔离"还是"失败 3 次后第 4 次才隔离"。
**How to avoid:** 固定语义:每次前置失败 `attempt += 1`;`is_quarantined = attempt >= threshold`。threshold=3 → 累计 3 次失败后即隔离(下一轮排除)。与 `RETRY_DELAYS_SECONDS`(5/15/45,共 3 次)的"最多试 3 次"约定对齐(D-04)。UPPER_SNAKE 常量 + 测试字面断言锁定语义。

## Code Examples

### 计数递增 + 告警(pipeline.run_pipeline_once 消费端改造)
```python
# Source: 改造 pipeline.py:405-441(run_pipeline_once 主循环)
# 每轮开头读账本一次;循环内递增;结束/每次改动后写回。
ledger = load_ledger(failed_root)
threshold = max_fragment_failures   # 从 config 传入

def _record_and_maybe_alert(fid: str, reason: str) -> None:
    entry = record_failure(ledger, fid, reason, now=_now_iso())  # attempt += 1, last_seen 更新
    if entry["attempt"] == threshold:                            # 恰好跨阈值那一次告警(Pitfall 5)
        log(quarantine_alert_line(fid, reason, entry["attempt"]))
    save_ledger(failed_root, ledger)

for item in plan.to_download:
    if item.fragment_id in seen:
        continue
    seen.add(item.fragment_id)
    outcome = process_plan(item, source, inbox_root=inbox_root, fragments_root=fragments_root)
    if outcome.status != "downloaded" or outcome.part_path is None or outcome.draft is None:
        _record_and_maybe_alert(item.fragment_id, outcome.status)   # D-09:sha256_mismatch / error
        results.append(FragmentResult(item.fragment_id, STATUS_FAILED, STAGE_DOWNLOAD, detail=outcome.detail))
        continue
    frag_result = process_part(...)
    if frag_result.status == STATUS_FAILED and frag_result.stage == STAGE_STANDARDIZE:
        _record_and_maybe_alert(item.fragment_id, "standardize_failed")  # D-09:探测/转码失败
    elif frag_result.ok:
        clear_entry(ledger, item.fragment_id); save_ledger(failed_root, ledger)  # Pitfall 4
    results.append(frag_result)
```
**注意 D-09 边界:** 只有 `STAGE_STANDARDIZE` 的 failed 计入;`STAGE_TRANSCRIBE`/`STAGE_MANIFEST_*` 的 failed **不计入**(fragment 目录已建,NLS 有自带重试)。`process_part` 返回的 `FragmentResult.stage`(pipeline.py:98)提供精确阶段判别。

### 隔离跳过注入(pipeline 读账本 → 传 quarantine_check)
```python
# Source: 改造 pipeline.py:397(plan_downloads 调用点)
ledger = load_ledger(failed_root)
plan = plan_downloads(
    listings,
    done_check=lambda fid, date: done_marker_path(fragments_root, date, fid).exists(),
    quarantine_check=lambda fid: is_quarantined(
        int(ledger.get(fid, {}).get("attempt", 0)), threshold=max_fragment_failures
    ),
)
log(f"[pipeline] ... 跳过(.done) {len(plan.skipped_done)}，"
    f"隔离 {len(plan.skipped_quarantined)}，忽略 {len(plan.ignored_keys)}")
```

### PollConfig 加阈值字段
```python
# Source: 改造 config.py:51-55
class PollConfig(BaseModel):
    """轮询配置。"""
    interval_seconds: int
    max_fragment_failures: int = 3   # D-04:达此失败次数即隔离,默认 3(对齐 RETRY_DELAYS 3 次)
# masked_summary(config.py:93)加一行:
#   f"  max_fragment_failures = {self.poll.max_fragment_failures}",
```
**向后兼容:** 有默认值 → 既有 `config.yaml` 无此字段仍能加载(pydantic 用默认)。既有 `test_config.py` 不 break。

### CLI 子命令(委托模式,参考 cli.py:401 retranscribe)
```python
# Source: 新增 cli.py @app.command
@app.command(name="quarantine-list")
def quarantine_list() -> None:
    """列出当前被隔离(失败计数达阈值)的 fragment 及原因/计数(WKR-03,D-08)。"""
    from soniscope_worker.quarantine import run_quarantine_list
    lines, code = run_quarantine_list()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)

@app.command(name="clear-quarantine")
def clear_quarantine(
    fragment_id: str = typer.Option("", "--fragment-id", help="要解除隔离的 fragment_id"),
    all_: bool = typer.Option(False, "--all", help="清空整个隔离账本"),
) -> None:
    """解除隔离:删账本对应条目 → 下一轮重新下载(WKR-03,D-07)。"""
    from soniscope_worker.quarantine import run_clear_quarantine
    lines, code = run_clear_quarantine(fragment_id=fragment_id or None, clear_all=all_)
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)
```

### Makefile 目标(参考 Makefile:119 retranscribe / :64 oss-delete-obj)
```makefile
quarantine-list: ## 列出当前被隔离的 fragment(失败计数达阈值)及原因/计数
	uv run python -m soniscope_worker quarantine-list

clear-quarantine: ## 解除隔离(FRAGMENT_ID=<id> 单条;或 ALL=1 全清)→ 下一轮重下
	uv run python -m soniscope_worker clear-quarantine \
		$(if $(strip $(FRAGMENT_ID)),--fragment-id $(FRAGMENT_ID),) \
		$(if $(strip $(ALL)),--all,)
```
**别忘 `.PHONY`**(Makefile:6-19)加这两个目标名。

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 失败即删 `.part` 等下一轮重下,无上限(F-CODE-02) | 失败计数账本 + 阈值隔离 + 告警 | 本 phase | 持久失败对象不再无界重下 |
| `_archive_failed` docstring 称"不再重试"(误导) | docstring 更正:留档不阻止重试,阈值隔离才阻止 | 本 phase (D-11) | 语义与实现一致 |

**Deprecated/outdated:** 无 — 本 phase 只增不删既有行为面(D-10 保 `.done` 路径原样)。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 成功后清账本条目(Pitfall 4)是期望行为 | Pitfalls/Code Examples | 若用户要求"成功也保留失败历史",需改为不清或加 `resolved_at` 标记;属 Discretion 内的 schema 决策,planner 可定 |
| A2 | 账本并发写取"接受竞态"(Pitfall 3 方案 a) | Pitfalls | 若判定需强一致,加 `_ledger` 锁(locks.py 已支持),成本低 |
| A3 | 告警在 attempt 恰等于 threshold 那一轮发一次(非每轮)| Validation/Code | 若要求每轮隔离都告警(避免运维错过单次),改为每次 skipped_quarantined 时也可选 info 日志;四要素告警语义不变 |
| A4 | reason 取值用既有 `ObjectOutcome.status`(downloaded/sha256_mismatch/error)+ 新增 `standardize_failed` 字符串常量 | Code Examples | 若要更细(probe_failed vs transcode_failed),需在 `standardize` 返回区分;`StandardizeResult.detail`(audio.py:127)已含信息,可派生 |

## Open Questions

1. **成功后是否清除账本条目?**
   - What we know:D-06 说隔离持久保留直到 operator 处理;但那指**已隔离**(attempt≥阈值)条目。未达阈值的偶发失败后成功,清不清是独立问题。
   - What's unclear:是否保留"失败历史"用于诊断(WKR-01 说 persist failure history)。
   - Recommendation:成功清 `attempt` 计数以防误隔离(Pitfall 4),但可保留一个 `last_success_at` 或直接删条目。倾向**删条目**(账本 = 当前"有问题"清单,单一真相源)。planner 定 schema 时敲定。

2. **reason 粒度(A4):探测失败 vs 转码失败是否分开记?**
   - What we know:D-05 共用一个阈值,不按类型分开**隔离**;但**记录**的 reason 可细分供诊断。
   - Recommendation:reason 记细分字符串(便于 WKR-03 诊断),阈值判定只看 attempt 总数(D-05)。`standardize` 已能区分(FixtureError=探测 / AudioToolError=转码,audio.py:184/223)。

## Environment Availability

**N/A(基本)** — 本 phase 纯本地 Python 代码/配置改动,无新增外部工具/服务依赖。既有 `ffmpeg`/`ffprobe` 是 audio 标准化的既有依赖(本 phase 只改 `_archive_failed` docstring,不改转码逻辑)。测试用注入 fake,不需真实 ffmpeg。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 (root `pyproject.toml`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`:`testpaths=["apps/worker/tests","apps/fc/tests"]`,`pythonpath=["apps/fc/shared"]` |
| Quick run command | `uv run pytest apps/worker/tests/test_quarantine.py -x` |
| Full suite command | `make test`(= `uv run pytest`) |
| Static gates | `make typecheck`(mypy --strict,新模块必过)+ `make lint`(ruff E,F,I,UP,B) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WKR-01 | sha256_mismatch/探测/标准化失败各递增账本一次;账本落盘可重读 | unit | `pytest apps/worker/tests/test_quarantine.py -k record` | ❌ Wave 0 |
| WKR-01 | 多轮失败累积:同 fid 连续 N 轮失败 → attempt=N | unit(property-ish) | `pytest .../test_quarantine.py -k accumulate` | ❌ Wave 0 |
| WKR-02 | attempt≥threshold 的 fid 被 `plan_downloads` 排入 `skipped_quarantined`,不进 to_download | unit | `pytest apps/worker/tests/test_poller.py -k quarantine` | ⚠️ 既有 test_poller.py 增用例 |
| WKR-02 | 阈值来自 config,默认 3;改 config 改变隔离点 | unit | `pytest .../test_config.py -k max_fragment` + `test_quarantine.py` | ⚠️ 既有 test_config.py 增用例 |
| WKR-02 | is_quarantined 纯判据边界(attempt=threshold-1 不隔离,=threshold 隔离) | unit(example+boundary) | `pytest .../test_quarantine.py -k is_quarantined` | ❌ Wave 0 |
| WKR-03 | 恰跨阈值那轮发一条含 4 要素(fid/reason/attempt/next)的告警行 | unit | `pytest .../test_quarantine.py -k alert` | ❌ Wave 0 |
| WKR-03 | quarantine-list 列出隔离清单;clear-quarantine 单条/--all 删条目 | unit | `pytest .../test_quarantine.py -k cli` | ❌ Wave 0 |
| #4 回归 | 既有 `.done` 幂等跳过路径不变(D-10) | unit(non-regression) | `make test-no-redownload` + `pytest test_pipeline.py -k done` | ✅ 既有,须保持绿 |
| #4 回归 | 成功路径下账本被清/不误隔离 | unit | `pytest .../test_quarantine.py -k success_clears` | ❌ Wave 0 |
| 状态安全 | 启动恢复扫描不误删 `inbox/failed/ledger.json` | unit | `pytest .../test_recovery.py -k ledger` | ⚠️ 既有 test_recovery.py 增用例 |

### Sampling Rate
- **Per task commit:** `uv run pytest apps/worker/tests/test_quarantine.py -x` + `make typecheck`(改动文件)
- **Per wave merge:** `make test`(全 pytest,含 test_poller/test_pipeline/test_config/test_recovery 回归)+ `make lint`
- **Phase gate:** `make test` + `make typecheck` + `make lint` 全绿;`make test-no-redownload`(D-10 幂等非回归)绿,才进 `/gsd-verify-work`

### 采样策略(Nyquist:什么必须被采、用何种测试)
- **多轮失败累积**(奈奎斯特核心:失败是跨轮离散事件)→ **held-out 多轮驱动**:构造注入 `FakeSource`(每轮 list 同一 key)+ 强制失败(download_error 或损坏 body),连续跑 3+ 轮 `run_pipeline_once`,断言账本 attempt 逐轮 +1、第 3 轮末尾 fid 进 `skipped_quarantined`、第 4 轮 `to_download` 为空且 download_calls 不再增。这是防"每轮重下"回归的关键采样。
- **阈值跨越点**(边界)→ **boundary example tests**:attempt=threshold-1 不隔离、=threshold 隔离、告警恰发一次(用可捕获 `log` 列表断言行数与内容)。
- **纯判据 is_quarantined**→ 纯函数 example + 边界(0/threshold-1/threshold/threshold+1),无 IO,最快采样。
- **告警 4 要素**→ 字符串断言固定顺序含 `fragment_id=`/`reason=`/`attempt=`/`next=`(便于未来 grep)。
- **D-10 非回归**(既有成功幂等跳过)→ 复用既有 `make test-no-redownload` + test_pipeline `.done` 用例,须保持绿——这是成功标准 #4 显式要求。
- **状态可从磁盘推导**(重启不丢隔离)→ 写账本 → 新建 `load_ledger` 读回 → 断言隔离态仍成立(模拟重启)。

### Wave 0 Gaps
- [ ] `apps/worker/tests/test_quarantine.py` — 覆盖 WKR-01/02/03 纯判据、record_failure、告警、CLI、多轮累积、成功清除、损坏账本降级、磁盘重读(新建)
- [ ] `apps/worker/tests/test_poller.py` — 增 `plan_downloads(quarantine_check=…)` → `skipped_quarantined` 用例(既有文件增用例)
- [ ] `apps/worker/tests/test_pipeline.py` — 增 run_pipeline_once 多轮失败隔离 + 成功清账本 + D-09 边界(transcribe 失败不计入)用例(既有文件增用例)
- [ ] `apps/worker/tests/test_config.py` — 增 `max_fragment_failures` 默认值 + 校验 + summary 行用例(既有文件增用例)
- [ ] `apps/worker/tests/test_recovery.py` — 增 recover 不误删 ledger.json 用例(既有文件增用例)
- [ ] 框架无需安装:pytest/mypy/ruff 均已在 uv workspace(`make test/typecheck/lint` 现成)

## Security Domain

`security_enforcement=true`,ASVS L1。本 phase 无网络端点、无认证面、无秘密处理,安全面窄:

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Worker 本地进程,无认证面 |
| V3 Session Management | no | 无会话 |
| V4 Access Control | no | 无多用户 |
| V5 Input Validation | yes | CLI `FRAGMENT_ID` 经 `object_key_for` 往返校验(oss_admin);账本 JSON 损坏降级为空(不信任磁盘内容) |
| V6 Cryptography | no | 无加密面(sha256 是完整性比对,既有,不在本 phase 改动) |
| V7 Error Handling & Logging | yes | 告警行只含 fid/reason/attempt/next——**不得回显秘密**(CLAUDE.md 红线);损坏账本不杀进程 |

### Known Threat Patterns for Worker 本地进程
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 恶意/损坏 `ledger.json` 触发解析崩溃(DoS 守护进程)| Denial of Service | `load_ledger` catch `(OSError, json.JSONDecodeError)` 降级 `{}`(Pitfall 2)|
| clear-quarantine 传非法 `FRAGMENT_ID` | Tampering/Input | 复用 `object_key_for` 往返校验非法 fid(oss_admin,retranscribe/oss-delete-obj 同款)|
| 告警行泄露敏感值 | Information Disclosure | 四要素仅结构化非敏感字段;fid 非秘密;不 log 账本原始 body 以外内容 |
| 账本无界增长(每个失败 fid 一条,永不清)| DoS(磁盘)| 成功清条目(Pitfall 4)+ clear-quarantine 运维出口;个人应用规模下条目数极小 |

## Sources

### Primary (HIGH confidence)
- 源码 `apps/worker/src/soniscope_worker/poller.py`(plan_downloads:177、ObjectOutcome:235、process_plan:248、poll_once:322、run_worker_run:455)— 本次 Read 全文核实
- 源码 `pipeline.py`(run_pipeline_once:375、消费端:407-441、run_worker_pipeline:511、run_pipeline_loop:445)— 全文核实
- 源码 `audio.py`(_archive_failed:134、standardize:145、探测失败:184、转码失败:223)— 全文核实
- 源码 `config.py`(PollConfig:51、masked_summary:85、_collect_validation_errors:109)— 全文核实
- 源码 `recovery.py`(atomic_write_json:63、create_done_marker:101、recover_inbox:196、_remove_by_suffix:181)— 全文核实
- 源码 `locks.py`(fragment_lock:40)、`paths.py`(inbox_failed_dir:83)、`cli.py`(委托模式全览、retranscribe:401)、`retranscribe.py`(CLI/纯判据 should_retranscribe:82)、`Makefile`(retranscribe:119、oss-delete-obj:63、.PHONY:6)— 全文核实
- `.planning/audit/findings/code.md` §F-CODE-02、`.planning/audit/REPORT.md`(WP-03:151、必做清单:42/99)、`.planning/REQUIREMENTS.md`(WKR-01/02/03)、`.planning/ROADMAP.md` §Phase 6、`06-CONTEXT.md`(D-01~D-11)— 全文核实
- `pyproject.toml`(mypy strict files:32、ruff:47、pytest testpaths:55)、`.planning/config.json`(nyquist_validation:true、security_enforcement:true)— 核实

### Secondary (MEDIUM confidence)
- 无 — 未用 WebSearch;全部基于仓库源码(本地权威源)

### Tertiary (LOW confidence)
- 无

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 零新依赖,全部既有资产,行号核实
- Architecture: HIGH — 集成点(plan_downloads/run_pipeline_once)源码逐行确认;poller vs pipeline 生产路径辨明
- Pitfalls: HIGH — 竞态/损坏/改错循环/阈值语义均从源码结构推导
- Validation: HIGH — 测试框架现成,requirement→test 全映射

**Research date:** 2026-07-06
**Valid until:** 代码基线稳定(无外部版本漂移风险);建议 30 天内消费,或 poller.py/pipeline.py 有改动时复核集成点行号

## RESEARCH COMPLETE

