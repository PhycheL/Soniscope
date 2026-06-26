"""配置 schema、脱敏加载器与必填字段校验（US-002）。

`config.yaml` 用 Pydantic v2 校验，敏感字段（access_key_secret / appkey / api_key）
在 repr / 日志中只显示前后 4 位。缺失必填字段时一次性列出所有缺失项并以非零退出。

加载顺序见 paths.soniscope_home()：① $SONISCOPE_HOME/config.yaml → ② ~/SoniScope/config.yaml。
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, SecretStr, ValidationError

from soniscope_worker.paths import soniscope_home


def config_path() -> Path:
    """返回 config.yaml 的预期路径（$SONISCOPE_HOME/config.yaml）。"""
    return soniscope_home() / "config.yaml"


def mask_secret(value: str) -> str:
    """脱敏摘要：长度 > 8 时显示前后 4 位，否则整体打码，空值返回空串。"""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


class MaskedSecret(SecretStr):
    """SecretStr 子类，repr / str 显示前后 4 位脱敏摘要而非全打码。"""

    def _display(self) -> str:
        return mask_secret(self.get_secret_value())


class ConfigError(Exception):
    """配置文件缺失、解析失败或必填字段缺失时抛出。"""


class OSSConfig(BaseModel):
    """OSS 访问配置（soniscope-local-reader 只读凭证）。"""

    endpoint: str
    bucket: str
    access_key_id: str
    access_key_secret: MaskedSecret


class PollConfig(BaseModel):
    """轮询配置。"""

    interval_seconds: int


class LocalConfig(BaseModel):
    """whisper-local 子配置开关，不参与工厂选择（工厂只看 transcriber.name）。"""

    enabled: bool = False


class TranscriberConfig(BaseModel):
    """转写器配置。"""

    name: str
    provider: str
    model: str
    params_version: str
    api_endpoint: str
    appkey: MaskedSecret
    access_key_id: str
    access_key_secret: MaskedSecret
    upload_mode: str
    local: LocalConfig = LocalConfig()


class SoniScopeConfig(BaseModel):
    """Worker 顶层配置。"""

    oss: OSSConfig
    poll: PollConfig
    transcriber: TranscriberConfig

    def masked_summary(self) -> list[str]:
        """生成脱敏摘要行，AK Secret / appkey 只显示前后 4 位，绝不输出明文。"""
        return [
            "[oss]",
            f"  endpoint           = {self.oss.endpoint}",
            f"  bucket             = {self.oss.bucket}",
            f"  access_key_id      = {self.oss.access_key_id}",
            f"  access_key_secret  = {self.oss.access_key_secret}",
            "[poll]",
            f"  interval_seconds   = {self.poll.interval_seconds}",
            "[transcriber]",
            f"  name               = {self.transcriber.name}",
            f"  provider           = {self.transcriber.provider}",
            f"  model              = {self.transcriber.model}",
            f"  params_version     = {self.transcriber.params_version}",
            f"  api_endpoint       = {self.transcriber.api_endpoint}",
            f"  appkey             = {self.transcriber.appkey}",
            f"  access_key_id      = {self.transcriber.access_key_id}",
            f"  access_key_secret  = {self.transcriber.access_key_secret}",
            f"  upload_mode        = {self.transcriber.upload_mode}",
            f"  local.enabled      = {self.transcriber.local.enabled}",
        ]


def _collect_validation_errors(exc: ValidationError) -> str:
    """把 Pydantic ValidationError 汇总为可读消息，缺失字段一次性全列出。"""
    missing: list[str] = []
    others: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err["loc"])
        if err["type"] == "missing":
            missing.append(loc)
        else:
            others.append(f"{loc}: {err['msg']}")
    lines: list[str] = []
    if missing:
        lines.append("缺失必填字段（请在 config.yaml 中补全）：")
        lines.extend(f"  - {name}" for name in missing)
    if others:
        lines.append("字段校验错误：")
        lines.extend(f"  - {item}" for item in others)
    return "\n".join(lines)


def load_config(path: Path | None = None) -> SoniScopeConfig:
    """加载并校验配置；文件缺失或字段缺失时抛出 ConfigError（含全部缺失项）。"""
    p = path or config_path()
    if not p.exists():
        raise ConfigError(
            f"配置文件不存在：{p}\n请参考 PRD US-001 (H) 准备 config.yaml 并 chmod 600。"
        )
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"config.yaml 解析失败：{exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"config.yaml 顶层应为映射（mapping），实际为：{type(raw).__name__}")
    try:
        return SoniScopeConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(_collect_validation_errors(exc)) from exc


def config_permission_is_600(path: Path) -> bool:
    """检查配置文件权限是否恰为 600（仅当前用户可读写）。"""
    return (path.stat().st_mode & 0o777) == 0o600
