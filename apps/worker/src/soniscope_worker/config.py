"""Configuration schema, validation, and loading for SoniScope Worker.

Config is loaded from ``$SONISCOPE_HOME/config.yaml`` (defaulting to
``~/SoniScope/config.yaml``) and validated with Pydantic v2.

Sensitive fields (``access_key_secret``, ``appkey``, ``api_key``) are
masked in ``repr()``, ``str()``, and serialized output — only the first 4
and last 4 characters are shown.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError


# ---------------------------------------------------------------------------
# Secret masking
# ---------------------------------------------------------------------------

# Field names whose values should never be printed in full.
_SECRET_FIELD_NAMES: frozenset[str] = frozenset({
    "access_key_secret",
    "appkey",
    "api_key",
})


def mask_secret(value: str) -> str:
    """Return a masked version of *value* showing only the first 4 and last 4 chars.

    Values of 8 characters or fewer are replaced entirely with ``*``.
    """
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _mask_dict(data: dict[str, Any]) -> None:
    """Recursively mask sensitive values in *data* (mutates in place)."""
    for key in list(data):
        if key in _SECRET_FIELD_NAMES and isinstance(data[key], str):
            data[key] = mask_secret(data[key])
        elif isinstance(data[key], dict):
            _mask_dict(data[key])


# ---------------------------------------------------------------------------
# Config models
# ---------------------------------------------------------------------------


class OssConfig(BaseModel):
    """OSS (Object Storage Service) connection configuration."""

    endpoint: str = Field(..., description="OSS endpoint, e.g. oss-cn-beijing.aliyuncs.com")
    bucket: str = Field(..., description="OSS bucket name")
    access_key_id: str = Field(..., description="RAM user AccessKey ID")
    access_key_secret: str = Field(..., description="RAM user AccessKey Secret")


class PollConfig(BaseModel):
    """Polling configuration."""

    interval_seconds: int = Field(..., ge=1, description="OSS poll interval in seconds")


class TranscriberLocalConfig(BaseModel):
    """Sub-config for the local Whisper placeholder (not implemented in MVP)."""

    enabled: bool = Field(default=False, description="Enable local whisper (not implemented)")


class TranscriberConfig(BaseModel):
    """ASR transcriber configuration.

    Sensitive fields: ``appkey``, ``access_key_secret``.
    """

    name: str = Field(..., description="Transcriber factory key: cloud-speech | whisper-local")
    provider: str = Field(..., description="Provider name, e.g. aliyun-nls")
    model: str = Field(..., description="ASR model display name")
    params_version: str = Field(..., description="Parameter / prompt version tag, e.g. v1")
    api_endpoint: str = Field(..., description="ASR API endpoint, e.g. cn-beijing")
    appkey: str = Field(..., description="NLS project AppKey")
    access_key_id: str = Field(..., description="NLS AccessKey ID")
    access_key_secret: str = Field(..., description="NLS AccessKey Secret")
    upload_mode: str = Field(default="oss-url", description="Upload mode: oss-url | direct")
    local: TranscriberLocalConfig = Field(
        default_factory=TranscriberLocalConfig,
        description="Local whisper sub-config",
    )


class SoniScopeConfig(BaseModel):
    """Top-level SoniScope Worker configuration.

    Serialization (``repr``, ``str``, ``model_dump``, ``model_dump_json``)
    automatically masks all sensitive fields so they are safe to log or print.
    """

    oss: OssConfig
    poll: PollConfig
    transcriber: TranscriberConfig

    def __repr__(self) -> str:
        return self._build_masked_repr()

    def __str__(self) -> str:
        return self._build_masked_repr()

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Return a dict with all secret values masked."""
        result = super().model_dump(**kwargs)
        _mask_dict(result)
        return result

    def _build_masked_repr(self) -> str:
        """Return a JSON-ish repr with secrets masked."""
        import json as _json

        return _json.dumps(
            self.model_dump(),
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    def sanitized_summary(self) -> str:
        """Return a human-readable summary suitable for ``make check-config`` output.

        Every secret is shown in ``xxxx...xxxx`` form.
        """
        lines = [
            "=== SoniScope Config (secrets masked) ===",
            f"OSS endpoint:     {self.oss.endpoint}",
            f"OSS bucket:       {self.oss.bucket}",
            f"OSS AK ID:        {self.oss.access_key_id}",
            f"OSS AK Secret:    {mask_secret(self.oss.access_key_secret)}",
            f"Poll interval:    {self.poll.interval_seconds}s",
            "",
            f"Transcriber:      {self.transcriber.name}",
            f"  Provider:       {self.transcriber.provider}",
            f"  Model:          {self.transcriber.model}",
            f"  Params version: {self.transcriber.params_version}",
            f"  API endpoint:   {self.transcriber.api_endpoint}",
            f"  AppKey:         {mask_secret(self.transcriber.appkey)}",
            f"  NLS AK ID:      {self.transcriber.access_key_id}",
            f"  NLS AK Secret:  {mask_secret(self.transcriber.access_key_secret)}",
            f"  Upload mode:    {self.transcriber.upload_mode}",
            f"  Local enabled:  {self.transcriber.local.enabled}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ConfigValidationError(Exception):
    """Config validation failed with human-readable messages."""


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def resolve_config_path() -> Path:
    """Resolve the config file path.

    Returns ``$SONISCOPE_HOME/config.yaml`` when ``SONISCOPE_HOME`` is set,
    otherwise ``~/SoniScope/config.yaml``.
    """
    home = os.environ.get("SONISCOPE_HOME")
    if home:
        return Path(home) / "config.yaml"
    return Path.home() / "SoniScope" / "config.yaml"


def load_config(path: Path | None = None) -> SoniScopeConfig:
    """Load and validate ``config.yaml``.

    Args:
        path: Optional explicit path.  When ``None``, resolves via
            :func:`resolve_config_path`.

    Returns:
        Validated :class:`SoniScopeConfig`.

    Raises:
        FileNotFoundError: The config file does not exist.
        ConfigValidationError: Validation failed (missing / invalid fields).
    """
    config_path = path or resolve_config_path()

    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            f"Please create a config.yaml at this path.\n"
            f"See docs/runbook/cloud-setup.md for the expected schema."
        )

    with open(config_path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    try:
        return SoniScopeConfig.model_validate(raw)
    except ValidationError as exc:
        missing: list[str] = []
        other: list[str] = []
        for err in exc.errors():
            loc = " → ".join(str(p) for p in err["loc"])
            if err["type"] == "missing":
                missing.append(loc)
            else:
                other.append(f"  {loc}: {err.get('msg', err.get('type', 'unknown'))}")

        parts: list[str] = []
        if missing:
            missing.sort()
            parts.append(f"Missing required fields ({len(missing)}):")
            for m in missing:
                parts.append(f"  - {m}")
        if other:
            parts.append("Other validation errors:")
            parts.extend(other)

        raise ConfigValidationError("\n".join(parts)) from exc


def check_file_permissions(path: Path) -> tuple[bool, str]:
    """Verify *path* has mode ``600`` (owner read-write only).

    Returns:
        ``(ok, message)`` — *ok* is ``True`` when permissions are ``600``.
    """
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError as exc:
        return False, f"Cannot stat config file: {exc}"

    if mode == 0o600:
        return True, "Config file permissions OK (600)."
    current = oct(mode)[2:]
    return False, (
        f"⚠ WARNING: Config file permissions are {current}, expected 600.\n"
        f"  Run: chmod 600 {path}\n"
        f"  This file contains plaintext credentials — restrict access."
    )
