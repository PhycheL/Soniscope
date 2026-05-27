# AGENTS.md

该文件用于在 AI 编码代理处理此仓库中的代码时提供指导。

---

## 项目概览

**日观声记（SoniScope）**：一个个人语音流水账记录工具的 MVP。微信小程序录音 → 阿里云 OSS 长期备份 → Python Worker 调用云端语音转文字 API 转写 → 本地按文件状态机落盘。

核心承诺：**用户说出口的话 100% 落到云端音频 + 本地文本，不丢、不重、不虚构**。

系统四层：**微信小程序（极薄前端）** · **阿里云函数计算 FC**（鉴权 + 凭证签发 + 上传校验）· **阿里云 OSS（私有 Bucket）**（音频长期备份）· **Python Worker**（轮询 + 下载 + 转写 + 落盘）。

---

## 技术栈

| 技术 | 用途 |
|------|------|
| 微信小程序（原生） | 前端录音、草稿、直传 OSS |
| Python 3.11+ | FC 函数与 Worker 统一运行时 |
| uv（workspace） | monorepo 下多子项目依赖管理 |
| Pydantic v2 / Typer / oss2 / PyYAML | Worker 配置 schema、CLI、OSS 客户端 |
| 阿里云 NLS（录音文件极速版） | 本期默认云端 ASR provider |
| ffmpeg / ffprobe（系统二进制） | Worker 端音频格式检测与转码 |
| mypy（strict）/ ruff / pytest | 类型检查 / Lint / 测试 |

---

## 命令

仓库根的 `Makefile` 是**唯一命令入口**，所有命令都在仓库根执行（不要 `cd` 进子目录）。

通用质量门：

```bash
make typecheck   # mypy strict
make lint        # ruff
make test        # pytest（单元测试用 mock，不打真实云端）
```

---

## 项目结构

```
my_soniscope/
├── apps/
│   ├── miniprogram/        # 微信小程序前端
│   ├── fc/<function>/      # 阿里云函数计算函数源码
│   └── worker/             # Python Worker（包名 soniscope-worker）
├── scripts/                # 跨组件运维与验证脚本
├── tests/fixtures/audio/   # 共享测试音频 fixture（sha256 登记在 runbook）
├── docs/
│   ├── PRD_v1.md           # 本期 PRD（权威）
│   ├── requirements_v5.md  # 需求文档
│   └── runbook/            # 人工准备登记表（非敏感）
├── pyproject.toml          # 根 uv workspace（不装业务依赖）
├── Makefile                # 唯一命令入口
└── AGENTS.md               # 本文件
```

**运行时数据目录**与代码仓库**严格分离**：由环境变量 `SONISCOPE_HOME`（默认 `~/SoniScope/`）指定，含 `config.yaml` / `inbox/` / `fragments/<date>/<fragment_id>/` / `tmp/`。**绝不进 git**。

---

## 架构

- **极薄前端 + 重后端**：业务规则（鉴权、签发、校验、转写、幂等）都在后端，小程序只做采集、上传、状态展示。
- **OSS object 是唯一数据契约**：连接小程序 → FC → Worker 三方。
- **状态机以硬盘真实文件为权威**：本地用 `manifest.json` + `.part` / `.tmp` / `.done` 旗标，不引入数据库（本期）；冲突时以"硬盘上实际有什么文件"为准，代码不能假设"我记得我做过 X"。
- **Transcriber 抽象**：本期实现云端 API 版本，本地 Whisper 仅保留占位骨架；切换 provider 只改 `config.yaml`，**不改业务代码**。

---

## 代码模式

### 命名约定
- Python 包：`soniscope_worker`，CLI 入口 `python -m soniscope_worker ...`
- FC 函数：目录用 snake_case（`apps/fc/issue_credential/`），函数 URL 用 kebab-case（`issue-credential`），二者不混用

### 文件组织
- monorepo + uv workspace；根 `pyproject.toml` 不装业务依赖
- 代码与运行时数据严格分离（运行时数据由 `$SONISCOPE_HOME` 指定）
- 本期不抽公共 Python 包：FC 与 Worker 如有重复逻辑各自保留，不为 DRY 引入额外模块
- 构建产物落 `build/`，已 gitignore

### 错误处理
- **网络错误 / 5xx**：指数退避重试；**4xx**（鉴权 / 配额）：立即失败，不重试
- 下载 / 转码失败：写入临时区或留档区，不污染最终 `fragments/` 目录

### 配置与敏感信息
- 配置走 Pydantic v2 schema；加载顺序 `$SONISCOPE_HOME/config.yaml` → `~/SoniScope/config.yaml`
- 缺失必填字段时一次性列出**所有**缺失项
- `access_key_secret` / `appkey` / `api_key` 在 `__repr__` / 日志中**只显示前后 4 位**

---

## 红线（违反即否决，无例外）

1. **小程序代码内绝不包含任何长期 AccessKey 或业务密钥**
2. **Worker 任何路径绝不调用 OSS `DeleteObject`**——OSS 永不删除
3. **STS 凭证必须精确到单个 object key**，不带通配符；有效期短于配置上限
4. **FC 接口必须有 openid allowlist 校验**，不接受匿名调用
5. **所有最终产物文件走"先 `.part` / `.tmp` → 校验 → 原子 rename → 最后写 `.done`"三段式协议**
6. **幂等以 `.done` 文件存在为准**，不因模型 / 参数版本变更自动重转（如需重转走显式 CLI）
7. **明文 AK / Secret 不进 git**：FC 端走环境变量；Worker 端走 `$SONISCOPE_HOME/config.yaml`（chmod 600）

---

## 测试

- **运行测试**：`make test`
- **测试位置**：`apps/<member>/tests/` + 跨组件 E2E 放 `tests/`，共享 fixture 在 `tests/fixtures/audio/`
- **测试模式**：单元测试中云端调用一律 **mock**，不打真实云端；真实云端验证通过专用 `make test-*-live` / E2E target 触发
- **崩溃恢复**：用 `kill -9` + 重启断言恢复，不依赖内存状态

---

## 验证

提交前必须跑通：

```bash
make typecheck && make lint && make test
```

---

## 关键文件

| 文件 | 用途 |
|------|------|
| `docs/PRD_v1.md` | **本期 MVP 的权威需求文档** |
| `docs/requirements/requirements_v5.md` | PRD 拆分前的原始需求；含 `manifest.json` 字段规范（§7.5） |
| `docs/runbook/cloud-setup.md` | 人工准备登记表（非敏感） |
| `pyproject.toml` / `Makefile` | uv workspace 配置 / 唯一命令入口 |
| `$SONISCOPE_HOME/config.yaml` | 运行时配置（含 AK），**不进 git** |

---

## 按需上下文

| 主题 | 文件 |
|------|------|
| 完整需求 / 各 user story 与 acceptance criteria | `docs/PRD_v1.md` |

---

## 备注

- **沟通语言**：与本项目维护者沟通默认中文。
