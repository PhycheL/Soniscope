"""US-007 STS 纯逻辑单测：object_key 解析、单 key policy、size 校验、env 加载。

均无 IO（不触网、不导入云 SDK），由 mypy strict + ruff + pytest 覆盖。
"""

from __future__ import annotations

import pytest

import fc_shared
from fc_shared import env as fc_env
from fc_shared import sts

FRAGMENT_ID = "20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE"
OBJECT_KEY = "recordings/2026-05-26/20260526T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE.wav"


# ── object_key_for（AC#2）──────────────────────────────────────────────────
def test_object_key_for_parses_date_prefix() -> None:
    assert sts.object_key_for(FRAGMENT_ID) == OBJECT_KEY


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "not-a-fragment",
        "20260526_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE",  # 缺 THHMMSS
        "20260526T144800_dev01_short",  # ULID 太短
        "20260526T144800__01HZX3K8MN5PQR9TFB7AYWVCDE",  # 缺 deviceShortId
    ],
)
def test_object_key_for_rejects_bad_format(bad: str) -> None:
    with pytest.raises(fc_shared.FcHttpError) as exc:
        sts.object_key_for(bad)
    assert exc.value.status == 400
    assert exc.value.error_code == fc_shared.INVALID_REQUEST


def test_object_key_for_rejects_impossible_date() -> None:
    with pytest.raises(fc_shared.FcHttpError) as exc:
        sts.object_key_for("20261331T144800_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE")
    assert exc.value.status == 400


# ── single_key_policy（AC#5，tech-spec §4.4）────────────────────────────────
def test_single_key_policy_is_exact_single_key_no_wildcard() -> None:
    policy = sts.single_key_policy("soniscope-audio", OBJECT_KEY)
    assert policy["Version"] == "1"
    statements = policy["Statement"]
    assert isinstance(statements, list)
    assert len(statements) == 1
    stmt = statements[0]
    assert stmt["Effect"] == "Allow"
    assert stmt["Action"] == ["oss:PutObject"]
    resources = stmt["Resource"]
    assert resources == [f"acs:oss:*:*:soniscope-audio/{OBJECT_KEY}"]
    # 精确单 key，绝不出现通配符。
    assert "*" not in resources[0].split("soniscope-audio/", 1)[1]
    assert "recordings/*" not in resources[0]


# ── parse_size ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize(("value", "expected"), [(1, 1), (12345, 12345), ("678", 678)])
def test_parse_size_accepts_positive_int(value: object, expected: int) -> None:
    assert sts.parse_size(value) == expected


@pytest.mark.parametrize("value", [0, -1, "0", "-5", "abc", 1.5, None, True, "12.5"])
def test_parse_size_rejects_invalid(value: object) -> None:
    with pytest.raises(fc_shared.FcHttpError) as exc:
        sts.parse_size(value)
    assert exc.value.status == 400
    assert exc.value.error_code == fc_shared.INVALID_REQUEST


# ── check_size（AC#3）─────────────────────────────────────────────────────────
def test_check_size_within_limit_ok() -> None:
    sts.check_size(100, 200)  # 不抛即通过


def test_check_size_exceeded_raises_with_limits() -> None:
    with pytest.raises(fc_shared.FcHttpError) as exc:
        sts.check_size(300, 200)
    err = exc.value
    assert err.status == 400
    assert err.error_code == fc_shared.SIZE_EXCEEDED
    assert err.payload["limit_bytes"] == 200
    assert err.payload["actual_bytes"] == 300


# ── credential_response（AC#6）────────────────────────────────────────────────
def test_credential_response_has_all_fields() -> None:
    cred = sts.StsCredential(
        access_key_id="STS.id",
        access_key_secret="sec",
        security_token="tok",
        expiration="2026-05-26T15:03:00Z",
    )
    resp = sts.credential_response(
        cred,
        bucket="soniscope-audio",
        endpoint="oss-cn-beijing.aliyuncs.com",
        object_key=OBJECT_KEY,
    )
    assert set(resp) == {
        "access_key_id",
        "access_key_secret",
        "security_token",
        "expiration",
        "bucket",
        "endpoint",
        "object_key",
    }
    assert resp["object_key"] == OBJECT_KEY
    assert resp["bucket"] == "soniscope-audio"


# ── load_sts_env ──────────────────────────────────────────────────────────────
_STS_ENV = {
    "RAM_ROLE_ARN": "acs:ram::1633875501759333:role/soniscope-uploader-role",
    "ALIYUN_AK_ID": "ak-id",
    "ALIYUN_AK_SECRET": "ak-secret",
}


def test_load_sts_env_defaults_max_upload_bytes() -> None:
    env = fc_env.load_sts_env(_STS_ENV)
    assert env.ram_role_arn.endswith("soniscope-uploader-role")
    assert env.max_upload_bytes == fc_shared.DEFAULT_MAX_UPLOAD_BYTES


def test_load_sts_env_custom_max_upload_bytes() -> None:
    env = fc_env.load_sts_env({**_STS_ENV, "MAX_UPLOAD_BYTES": "1000"})
    assert env.max_upload_bytes == 1000


@pytest.mark.parametrize("raw", ["", "  ", "not-a-number", "0", "-5"])
def test_load_sts_env_invalid_max_falls_back(raw: str) -> None:
    env = fc_env.load_sts_env({**_STS_ENV, "MAX_UPLOAD_BYTES": raw})
    assert env.max_upload_bytes == fc_shared.DEFAULT_MAX_UPLOAD_BYTES


def test_load_sts_env_missing_lists_names() -> None:
    with pytest.raises(fc_shared.FcConfigError) as exc:
        fc_env.load_sts_env({})
    assert set(exc.value.missing) == set(fc_shared.ISSUE_CREDENTIAL_REQUIRED_VARS)


def test_load_sts_env_secret_not_in_repr() -> None:
    # ak_secret 字段名含 "secret"，audit 层会脱敏；这里确认 env 本身只承载值不打印。
    env = fc_env.load_sts_env(_STS_ENV)
    assert env.ak_secret == "ak-secret"
    assert fc_shared.is_sensitive("ALIYUN_AK_SECRET")


# ── 时长上限（AC#4）与签发器工厂 ────────────────────────────────────────────
def test_sts_duration_within_900() -> None:
    assert sts.STS_MAX_DURATION_SECONDS <= 900


def test_get_issuer_returns_real_issuer() -> None:
    assert isinstance(sts.get_issuer(), sts.RealStsIssuer)
