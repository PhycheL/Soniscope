"""US-002：配置 schema、脱敏加载器、必填字段校验与运行时目录初始化测试。

所有测试使用临时目录与显式路径，不触碰真实 $SONISCOPE_HOME。
"""

import textwrap
from collections.abc import Mapping
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from soniscope_worker.cli import app
from soniscope_worker.config import (
    ConfigError,
    SoniScopeConfig,
    config_permission_is_600,
    load_config,
    mask_secret,
)
from soniscope_worker.paths import (
    fragments_dir,
    inbox_dir,
    inbox_failed_dir,
    init_runtime_dirs,
    runtime_dirs,
    tmp_dir,
)

runner = CliRunner()

VALID_CONFIG = {
    "oss": {
        "endpoint": "oss-cn-beijing.aliyuncs.com",
        "bucket": "soniscope-audio",
        "access_key_id": "LTAI5tExampleAkId00000",
        "access_key_secret": "ossSecretValue1234567890ABCDEF",
    },
    "poll": {"interval_seconds": 60},
    "transcriber": {
        "name": "cloud-speech",
        "provider": "aliyun-nls",
        "model": "中文普通话（识音石 V1 - 端到端模型)",
        "params_version": "v1",
        "api_endpoint": "cn-beijing",
        "appkey": "1k8tqkjQsq65wp2m",
        "access_key_id": "LTAI5tNlsAkId000000000",
        "access_key_secret": "nlsSecretValueABCDEFGH1234567890",
        "upload_mode": "oss-url",
        "local": {"enabled": False},
    },
}


def _write_config(tmp_path: Path, data: Mapping[str, object], mode: int = 0o600) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    p.chmod(mode)
    return p


# --- mask_secret ---------------------------------------------------------


def test_mask_secret_long_value_shows_first_last_4() -> None:
    assert mask_secret("ABCDEFGHIJKL") == "ABCD...IJKL"


def test_mask_secret_short_value_fully_masked() -> None:
    assert mask_secret("short8x") == "*" * 7


def test_mask_secret_empty() -> None:
    assert mask_secret("") == ""


# --- schema coverage & masking -------------------------------------------


def test_load_valid_config(tmp_path: Path) -> None:
    cfg = load_config(_write_config(tmp_path, VALID_CONFIG))
    assert isinstance(cfg, SoniScopeConfig)
    assert cfg.oss.bucket == "soniscope-audio"
    assert cfg.poll.interval_seconds == 60
    assert cfg.transcriber.name == "cloud-speech"
    assert cfg.transcriber.upload_mode == "oss-url"
    assert cfg.transcriber.local.enabled is False
    # 明文可通过 get_secret_value 取回供业务调用
    assert cfg.oss.access_key_secret.get_secret_value() == "ossSecretValue1234567890ABCDEF"
    assert cfg.transcriber.appkey.get_secret_value() == "1k8tqkjQsq65wp2m"


def test_secret_not_leaked_in_repr_and_summary(tmp_path: Path) -> None:
    cfg = load_config(_write_config(tmp_path, VALID_CONFIG))
    raw_secret = "ossSecretValue1234567890ABCDEF"
    assert raw_secret not in repr(cfg)
    summary = "\n".join(cfg.masked_summary())
    assert raw_secret not in summary
    assert "1k8tqkjQsq65wp2m" not in summary  # appkey 也脱敏
    # 摘要里出现脱敏摘要（前后 4 位）
    assert "ossS...CDEF" in summary


# --- missing fields ------------------------------------------------------


def test_missing_fields_listed_all_at_once(tmp_path: Path) -> None:
    broken = {
        "oss": {"endpoint": "oss-cn-beijing.aliyuncs.com", "bucket": "soniscope-audio"},
        "poll": {},
        "transcriber": {"name": "cloud-speech"},
    }
    with pytest.raises(ConfigError) as exc_info:
        load_config(_write_config(tmp_path, broken))
    msg = str(exc_info.value)
    # 一次性列出多个缺失字段（覆盖 oss / poll / transcriber 三个分支）
    assert "oss.access_key_id" in msg
    assert "oss.access_key_secret" in msg
    assert "poll.interval_seconds" in msg
    assert "transcriber.provider" in msg
    assert "transcriber.upload_mode" in msg


def test_missing_config_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as exc_info:
        load_config(tmp_path / "nonexistent.yaml")
    assert "不存在" in str(exc_info.value)


def test_non_mapping_yaml_raises(tmp_path: Path) -> None:
    p = tmp_path / "config.yaml"
    p.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)


# --- permission check ----------------------------------------------------


def test_permission_check_600(tmp_path: Path) -> None:
    p = _write_config(tmp_path, VALID_CONFIG, mode=0o600)
    assert config_permission_is_600(p) is True


def test_permission_check_not_600(tmp_path: Path) -> None:
    p = _write_config(tmp_path, VALID_CONFIG, mode=0o644)
    assert config_permission_is_600(p) is False


# --- runtime dirs --------------------------------------------------------


def test_init_runtime_dirs_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))
    expected = {inbox_dir(), inbox_failed_dir(), fragments_dir(), tmp_dir()}
    assert set(runtime_dirs()) == expected
    # 第一次创建
    created = init_runtime_dirs()
    for d in created:
        assert d.is_dir()
    # 再次调用幂等，不报错
    again = init_runtime_dirs()
    assert again == created
    assert inbox_failed_dir().is_dir()


# --- CLI commands --------------------------------------------------------


def test_cli_check_config_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))
    _write_config(tmp_path, VALID_CONFIG, mode=0o600)
    result = runner.invoke(app, ["check-config"])
    assert result.exit_code == 0
    assert "soniscope-audio" in result.stdout
    assert "ossSecretValue1234567890ABCDEF" not in result.stdout


def test_cli_check_config_missing_field_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent("oss:\n  bucket: x\n"), encoding="utf-8")
    p.chmod(0o600)
    result = runner.invoke(app, ["check-config"])
    assert result.exit_code == 1


def test_cli_init_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))
    result = runner.invoke(app, ["init-dirs"])
    assert result.exit_code == 0
    assert (tmp_path / "inbox" / "failed").is_dir()
    assert (tmp_path / "fragments").is_dir()
    assert (tmp_path / "tmp").is_dir()


def test_cli_init_dirs_requires_existing_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_home = tmp_path / "missing"
    monkeypatch.setenv("SONISCOPE_HOME", str(missing_home))
    result = runner.invoke(app, ["init-dirs"])
    assert result.exit_code == 1
    assert "SONISCOPE_HOME 不存在" in result.stderr
    assert not missing_home.exists()
