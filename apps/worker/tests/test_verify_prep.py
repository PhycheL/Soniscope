"""US-004：`make verify-prep` 一键校验测试。

云端 / 系统依赖通过 `Probes` 协议注入 `FakeProbes`，全程不触网、不读真实云资源。
重点覆盖：各校验块 pass/fail 逻辑、AK Secret 不泄漏、汇总与退出码、成功末行文案、
缺失 config 的优雅失败、ProbeError 收敛为单项 fail。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from soniscope_worker.cli import app
from soniscope_worker.config import SoniScopeConfig
from soniscope_worker.verify_prep import (
    DEPLOY_AK_ID_ENV,
    DEPLOY_AK_SECRET_ENV,
    EXPECTED_BUCKET,
    EXPECTED_REGION,
    MIN_DISK_BYTES,
    STS_MAX_DURATION_SECONDS,
    SUCCESS_LINE,
    BucketInfo,
    CheckResult,
    EnvInfo,
    FcProbe,
    ProbeError,
    RealProbes,
    RepoLayout,
    StsCase,
    all_passed,
    check_config_security,
    check_env,
    check_fc,
    check_nls_result,
    check_oss_bucket,
    check_sts_escape,
    format_report,
    is_denied,
    nls_response_to_result,
    run_verify_prep,
    single_key_policy,
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

OSS_SECRET = "ossSecretValue1234567890ABCDEF"
NLS_SECRET = "nlsSecretValueABCDEFGH1234567890"

GOOD_NLS_RESULT: dict[str, object] = {
    "segments": [{"start": 0.0, "end": 2.5, "text": "今天天气不错"}],
    "language": "zh",
    "model": "中文普通话（识音石 V1 - 端到端模型)",
    "params_version": "v1",
    "provider": "aliyun-nls",
}


def _cfg() -> SoniScopeConfig:
    return SoniScopeConfig.model_validate(VALID_CONFIG)


def _write_config(tmp_path: Path, data: Mapping[str, object], mode: int = 0o600) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    p.chmod(mode)
    return p


class FakeProbes:
    """注入式探针：默认全绿，可逐项覆盖或令其抛 ProbeError。"""

    def __init__(
        self,
        *,
        env: EnvInfo | None = None,
        bucket: BucketInfo | None = None,
        sts: Sequence[StsCase] | None = None,
        fc: Mapping[str, FcProbe] | None = None,
        nls: Mapping[str, object] | None = None,
        fixtures: Sequence[CheckResult] | None = None,
        raise_on: frozenset[str] = frozenset(),
    ) -> None:
        self._env = env or EnvInfo(
            python_version=(3, 13, 2),
            home_writable=True,
            disk_free_bytes=MIN_DISK_BYTES * 2,
            tools={"ffmpeg": "/opt/homebrew/bin/ffmpeg", "ffprobe": "/opt/homebrew/bin/ffprobe"},
        )
        self._bucket = bucket or BucketInfo(exists=True, region=EXPECTED_REGION, acl="private")
        self._sts = sts if sts is not None else [
            StsCase("PutObject 越权其他 key", True, "AccessDenied"),
            StsCase("ListBucket", True, "AccessDenied"),
            StsCase("GetObject", True, "AccessDenied"),
            StsCase("过期后 PutObject", True, "ExpiredToken"),
        ]
        self._fc = fc or {}
        self._nls = nls if nls is not None else GOOD_NLS_RESULT
        self._fixtures = fixtures if fixtures is not None else [
            CheckResult("fixture sample-20s.wav（sha256 / duration / codec）", True, "OK"),
        ]
        self._raise_on = raise_on

    def env_info(self, home: Path) -> EnvInfo:
        if "env" in self._raise_on:
            raise ProbeError("env boom")
        return self._env

    def oss_bucket_info(self, cfg: SoniScopeConfig) -> BucketInfo:
        if "oss" in self._raise_on:
            raise ProbeError("oss boom")
        return self._bucket

    def sts_escape(self, cfg: SoniScopeConfig) -> Sequence[StsCase]:
        if "sts" in self._raise_on:
            raise ProbeError("sts boom")
        return self._sts

    def fc_curl(self, url: str) -> FcProbe:
        if "fc" in self._raise_on:
            raise ProbeError("fc boom")
        return self._fc.get(url, FcProbe(url=url, reachable=True, status=200))

    def nls_transcribe(self, cfg: SoniScopeConfig, audio: Path) -> Mapping[str, object]:
        if "nls" in self._raise_on:
            raise ProbeError("nls boom")
        return self._nls

    def fixture_results(self, audio_dir: Path, manifest_path: Path) -> Sequence[CheckResult]:
        if "fixtures" in self._raise_on:
            raise ProbeError("fixtures boom")
        return self._fixtures


# --- 纯校验逻辑 ----------------------------------------------------------------
def test_check_oss_bucket_ok() -> None:
    r = check_oss_bucket(BucketInfo(exists=True, region=EXPECTED_REGION, acl="private"))
    assert r.ok


@pytest.mark.parametrize(
    "info",
    [
        BucketInfo(exists=False, region=EXPECTED_REGION, acl="private"),
        BucketInfo(exists=True, region="cn-shanghai", acl="private"),
        BucketInfo(exists=True, region=EXPECTED_REGION, acl="public-read"),
    ],
)
def test_check_oss_bucket_fail(info: BucketInfo) -> None:
    assert not check_oss_bucket(info).ok


def test_check_env_all_ok() -> None:
    info = EnvInfo(
        python_version=(3, 11, 0),
        home_writable=True,
        disk_free_bytes=MIN_DISK_BYTES,
        tools={"ffmpeg": "/x/ffmpeg", "ffprobe": "/x/ffprobe"},
    )
    assert all(r.ok for r in check_env(info))


def test_check_env_fail_each_dimension() -> None:
    info = EnvInfo(
        python_version=(3, 10, 14),
        home_writable=False,
        disk_free_bytes=MIN_DISK_BYTES - 1,
        tools={"ffmpeg": None, "ffprobe": None},
    )
    results = check_env(info)
    assert all(not r.ok for r in results)
    names = {r.name for r in results}
    assert "Python 版本 >= 3.11" in names
    assert "ffmpeg 可执行" in names and "ffprobe 可执行" in names


def test_check_config_security_ok() -> None:
    results = check_config_security(_cfg(), Path("/x/config.yaml"), perm_is_600=True)
    assert all(r.ok for r in results)


def test_check_config_security_perm_and_empty_fields() -> None:
    data = {
        **VALID_CONFIG,
        "oss": {
            "endpoint": "",  # 制造空字段
            "bucket": "soniscope-audio",
            "access_key_id": "LTAI5tExampleAkId00000",
            "access_key_secret": OSS_SECRET,
        },
    }
    cfg = SoniScopeConfig.model_validate(data)
    results = check_config_security(cfg, Path("/x/config.yaml"), perm_is_600=False)
    perm = next(r for r in results if "权限" in r.name)
    fields = next(r for r in results if "非空" in r.name)
    assert not perm.ok
    assert not fields.ok
    assert "oss.endpoint" in fields.detail


def test_check_config_security_never_leaks_secret() -> None:
    results = check_config_security(_cfg(), Path("/x/config.yaml"), perm_is_600=True)
    blob = " ".join(f"{r.name} {r.detail} {r.fix_hint}" for r in results)
    assert OSS_SECRET not in blob
    assert NLS_SECRET not in blob


def test_check_sts_escape_ok() -> None:
    cases = [
        StsCase("a", True, "AccessDenied"),
        StsCase("b", True, "AccessDenied"),
        StsCase("c", True, "AccessDenied"),
        StsCase("d", True, "ExpiredToken"),
    ]
    assert check_sts_escape(cases).ok


def test_check_sts_escape_fail_if_any_allowed() -> None:
    cases = [StsCase("over-priv PutObject", False, "200 OK"), StsCase("b", True, "AccessDenied")]
    r = check_sts_escape(cases)
    assert not r.ok
    assert "over-priv PutObject" in r.detail


def test_check_sts_escape_fail_if_empty() -> None:
    assert not check_sts_escape([]).ok


def test_check_fc_ok_2xx() -> None:
    assert check_fc(FcProbe("https://x", reachable=True, status=200)).ok


def test_check_fc_fail_5xx() -> None:
    assert not check_fc(FcProbe("https://x", reachable=True, status=503)).ok


def test_check_fc_fail_unreachable() -> None:
    assert not check_fc(FcProbe("https://x", reachable=False, status=None, error="timeout")).ok


def test_check_nls_result_ok() -> None:
    assert check_nls_result(GOOD_NLS_RESULT).ok


def test_check_nls_result_missing_keys() -> None:
    assert not check_nls_result({"segments": [{"text": "x"}]}).ok


def test_check_nls_result_empty_segments() -> None:
    bad = {**GOOD_NLS_RESULT, "segments": []}
    assert not check_nls_result(bad).ok


# --- 编排 / 报告 / CLI ---------------------------------------------------------
def test_run_verify_prep_all_green(tmp_path: Path) -> None:
    cfg_path = _write_config(tmp_path, VALID_CONFIG)
    layout = RepoLayout(tmp_path)
    lines, code = run_verify_prep(FakeProbes(), layout=layout, cfg_path=cfg_path)
    assert code == 0
    assert lines[-1] == SUCCESS_LINE


def test_run_verify_prep_fail_propagates_nonzero(tmp_path: Path) -> None:
    cfg_path = _write_config(tmp_path, VALID_CONFIG)
    layout = RepoLayout(tmp_path)
    probes = FakeProbes(bucket=BucketInfo(exists=False, region="", acl=""))
    lines, code = run_verify_prep(probes, layout=layout, cfg_path=cfg_path)
    assert code == 1
    assert lines[-1] != SUCCESS_LINE
    assert SUCCESS_LINE not in lines


def test_run_verify_prep_probe_error_becomes_single_fail(tmp_path: Path) -> None:
    cfg_path = _write_config(tmp_path, VALID_CONFIG)
    layout = RepoLayout(tmp_path)
    probes = FakeProbes(raise_on=frozenset({"nls"}))
    lines, code = run_verify_prep(probes, layout=layout, cfg_path=cfg_path)
    assert code == 1
    assert any("nls boom" in line for line in lines)


def test_run_verify_prep_bad_perm_fails(tmp_path: Path) -> None:
    cfg_path = _write_config(tmp_path, VALID_CONFIG, mode=0o644)
    layout = RepoLayout(tmp_path)
    _, code = run_verify_prep(FakeProbes(), layout=layout, cfg_path=cfg_path)
    assert code == 1


def test_run_verify_prep_missing_config(tmp_path: Path) -> None:
    layout = RepoLayout(tmp_path)
    lines, code = run_verify_prep(FakeProbes(), layout=layout, cfg_path=tmp_path / "nope.yaml")
    assert code == 1
    assert any("config" in line.lower() for line in lines)


def test_run_verify_prep_report_has_no_secret(tmp_path: Path) -> None:
    cfg_path = _write_config(tmp_path, VALID_CONFIG)
    layout = RepoLayout(tmp_path)
    lines, _ = run_verify_prep(FakeProbes(), layout=layout, cfg_path=cfg_path)
    blob = "\n".join(lines)
    assert OSS_SECRET not in blob
    assert NLS_SECRET not in blob


def test_format_report_marks_pass_fail() -> None:
    results = [
        CheckResult("a", True, "ok"),
        CheckResult("b", False, "bad", "fix me"),
    ]
    text = "\n".join(format_report(results))
    assert "[PASS] a" in text
    assert "[FAIL] b" in text
    assert "fix me" in text
    assert not all_passed(results)


def test_repo_layout_paths() -> None:
    layout = RepoLayout(Path("/repo"))
    assert layout.audio_dir == Path("/repo/tests/audio")
    assert layout.sample_audio == Path("/repo/tests/audio/sample-20s.wav")
    assert layout.manifest_path == Path("/repo/tests/audio/fixtures.manifest.json")


def test_constants_match_runbook() -> None:
    assert EXPECTED_BUCKET == "soniscope-audio"
    assert EXPECTED_REGION == "cn-beijing"


def test_cli_verify_prep_missing_config_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 指向无 config 的临时 HOME，确保 CLI 优雅非零退出（不触网）。
    monkeypatch.setenv("SONISCOPE_HOME", str(tmp_path))
    result = runner.invoke(app, ["verify-prep"])
    assert result.exit_code == 1


# --- STS / NLS 纯逻辑 ----------------------------------------------------------
def test_single_key_policy_is_single_key_putobject_only() -> None:
    key = "recordings/2026-06-27/x.wav"
    policy = single_key_policy(key)
    stmts = policy["Statement"]
    assert isinstance(stmts, list) and len(stmts) == 1
    stmt = stmts[0]
    assert stmt["Action"] == ["oss:PutObject"]
    resource = stmt["Resource"]
    assert resource == [f"acs:oss:*:*:{EXPECTED_BUCKET}/{key}"]
    # 必须精确到单 key，不能含通配符（tech-spec §4.4）。
    assert "*" not in resource[0].split(EXPECTED_BUCKET + "/", 1)[1]


def test_is_denied_classification() -> None:
    assert is_denied("AccessDenied", expiry=False)
    assert not is_denied("", expiry=False)
    assert not is_denied("NoSuchKey", expiry=False)
    # 过期场景接受过期码与拒绝码。
    assert is_denied("ExpiredToken", expiry=True)
    assert is_denied("SecurityTokenExpired", expiry=True)
    assert is_denied("AccessDenied", expiry=True)
    # 越权（非过期）场景不接受过期码（过期码不代表权限边界被正确执行）。
    assert not is_denied("ExpiredToken", expiry=False)


def test_nls_response_to_result_maps_segments() -> None:
    resp: dict[str, object] = {
        "StatusText": "SUCCESS",
        "Result": {
            "Sentences": [
                {"BeginTime": 0, "EndTime": 2500, "Text": "今天天气不错"},
                {"BeginTime": 2500, "EndTime": 5100, "Text": "我准备去公园跑步"},
            ]
        },
    }
    result = nls_response_to_result(resp, _cfg())
    assert result["language"] == "zh"
    assert result["provider"] == "aliyun-nls"
    segments = result["segments"]
    assert isinstance(segments, list) and len(segments) == 2
    assert segments[0] == {"start": 0.0, "end": 2.5, "text": "今天天气不错"}
    # 映射结果必须能通过结构校验。
    assert check_nls_result(result).ok


def test_nls_response_to_result_empty_when_no_sentences() -> None:
    result = nls_response_to_result({"StatusText": "SUCCESS"}, _cfg())
    assert result["segments"] == []
    assert not check_nls_result(result).ok  # 空 segments 应判失败


# --- RealProbes 真实 IO 错误路径（不触网）-------------------------------------
def test_real_probes_sts_escape_requires_deploy_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DEPLOY_AK_ID_ENV, raising=False)
    monkeypatch.delenv(DEPLOY_AK_SECRET_ENV, raising=False)
    with pytest.raises(ProbeError, match="部署凭证"):
        RealProbes().sts_escape(_cfg())


def test_real_probes_sts_escape_missing_sdk_is_probe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # 有部署凭证但本环境未安装 STS/OSS SDK → 收敛为 ProbeError（不抛裸异常）。
    monkeypatch.setenv(DEPLOY_AK_ID_ENV, "deployIdPlaceholder")
    monkeypatch.setenv(DEPLOY_AK_SECRET_ENV, "deploySecretPlaceholder")
    with pytest.raises(ProbeError):
        RealProbes().sts_escape(_cfg())


def test_real_probes_nls_missing_audio_is_probe_error(tmp_path: Path) -> None:
    with pytest.raises(ProbeError, match="测试音频缺失"):
        RealProbes().nls_transcribe(_cfg(), tmp_path / "missing.wav")


def test_sts_max_duration_within_limit() -> None:
    assert STS_MAX_DURATION_SECONDS <= 900
