"""FC shared configuration — environment variable reading and validation.

Reads FC-runtime environment variables and validates required ones are present.
Does NOT depend on any FC 2.0 service layer.
"""

from __future__ import annotations

import os
from typing import NamedTuple


class SharedConfig(NamedTuple):
    """Validated configuration read from FC environment variables.

    All values are guaranteed non-empty after :func:`read_shared_config` succeeds.
    """

    oss_bucket: str
    oss_region: str
    oss_endpoint: str
    wx_appid: str
    wx_app_secret: str
    ram_role_arn: str
    aliyun_ak_id: str
    aliyun_ak_secret: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def read_shared_config() -> SharedConfig:
    """Read and validate all required environment variables.

    Returns:
        SharedConfig with all fields populated.

    Raises:
        SystemExit: if any required variable is missing or empty.
    """
    required: dict[str, str] = {
        "OSS_BUCKET": os.environ.get("OSS_BUCKET", ""),
        "OSS_REGION": os.environ.get("OSS_REGION", ""),
        "OSS_ENDPOINT": os.environ.get("OSS_ENDPOINT", ""),
        "WX_APPID": os.environ.get("WX_APPID", ""),
        "WX_APP_SECRET": os.environ.get("WX_APP_SECRET", ""),
        "RAM_ROLE_ARN": os.environ.get("RAM_ROLE_ARN", ""),
        "ALIYUN_AK_ID": os.environ.get("ALIYUN_AK_ID", ""),
        "ALIYUN_AK_SECRET": os.environ.get("ALIYUN_AK_SECRET", ""),
    }

    missing = [name for name, value in required.items() if not value]
    if missing:
        msg = (
            f"[FC] Missing required environment variables: {', '.join(sorted(missing))}"
        )
        # In FC we have no CLI, so write to stderr and signal via response.
        import sys

        print(msg, file=sys.stderr)
        # We don't sys.exit() in FC handler context; caller checks for empty values.
        raise _ConfigError(msg, missing)

    return SharedConfig(
        oss_bucket=required["OSS_BUCKET"],
        oss_region=required["OSS_REGION"],
        oss_endpoint=required["OSS_ENDPOINT"],
        wx_appid=required["WX_APPID"],
        wx_app_secret=required["WX_APP_SECRET"],
        ram_role_arn=required["RAM_ROLE_ARN"],
        aliyun_ak_id=required["ALIYUN_AK_ID"],
        aliyun_ak_secret=required["ALIYUN_AK_SECRET"],
    )


class _ConfigError(RuntimeError):
    """Raised when required environment variables are missing."""

    def __init__(self, message: str, missing: list[str]) -> None:
        super().__init__(message)
        self.missing = missing
