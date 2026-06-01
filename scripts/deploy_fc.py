"""FC 3.0 deploy / rollback / logs operations.

Used by the top-level Makefile.  Requires ``alibabacloud-fc20230330`` which
is declared as a dev dependency of the worker (so ``uv run`` can find it) but
is NOT bundled into FC function zip archives.

Usage::

    python scripts/deploy_fc.py deploy issue-credential
    python scripts/deploy_fc.py deploy verify-upload
    python scripts/deploy_fc.py deploy          # both functions
    python scripts/deploy_fc.py rollback issue-credential
    python scripts/deploy_fc.py logs issue-credential
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve repo root (this file lives in scripts/)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent

FC_SRC_DIR = REPO_ROOT / "apps" / "fc"
BUILD_DIR = REPO_ROOT / "build" / "fc"

# Mapping from kebab-case cloud function name to snake_case source directory.
FUNCTION_DIR_MAP: dict[str, str] = {
    "issue-credential": "issue_credential",
    "verify-upload": "verify_upload",
}

ALL_FUNCTIONS: list[str] = list(FUNCTION_DIR_MAP.keys())

# ---------------------------------------------------------------------------
# Aliyun FC 3.0 SDK helpers
# ---------------------------------------------------------------------------


def _get_fc_client():
    """Return a configured FC 3.0 client."""
    deploy_ak_id = os.environ.get("ALIYUN_DEPLOY_AK_ID")
    deploy_ak_secret = os.environ.get("ALIYUN_DEPLOY_AK_SECRET")

    if not deploy_ak_id or not deploy_ak_secret:
        print(
            "ERROR: ALIYUN_DEPLOY_AK_ID and ALIYUN_DEPLOY_AK_SECRET must be set.",
            file=sys.stderr,
        )
        print(
            "  Expected source: local .env file (gitignored) or CI secret.",
            file=sys.stderr,
        )
        sys.exit(1)

    from alibabacloud_fc20230330.client import Client
    from alibabacloud_tea_openapi.models import Config as FCConfig

    cfg = FCConfig(
        access_key_id=deploy_ak_id,
        access_key_secret=deploy_ak_secret,
        region_id="cn-beijing",
        endpoint="fc20230330.cn-beijing.aliyuncs.com",
    )
    return Client(cfg)


def _fc_function_name(kebab_name: str) -> str:
    """Return the full FC 3.0 function resource name.

    In FC 3.0 the function name IS just the kebab-case name — there is no
    service layer.
    """
    return kebab_name


# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------


def _snake_dir(function: str) -> str:
    """Return the snake_case source directory name for *function*."""
    return FUNCTION_DIR_MAP[function]


def _package_function(function: str) -> Path:
    """Create a zip archive for *function* and return its path.

    Each function is packaged independently: only its own ``handler.py`` plus
    any loose files in the src directory go in.  Deployment-time dependencies
    (alibabacloud-fc20230330) are **not** bundled.
    """
    src_dir = FC_SRC_DIR / _snake_dir(function)
    if not src_dir.is_dir():
        print(f"ERROR: source directory not found: {src_dir}", file=sys.stderr)
        sys.exit(1)

    build_func_dir = BUILD_DIR / function
    build_func_dir.mkdir(parents=True, exist_ok=True)

    zip_path = build_func_dir / f"{function}.zip"

    files: list[Path] = list(src_dir.rglob("*"))
    # Filter out __pycache__ and .pyc
    files = [f for f in files if "__pycache__" not in f.parts and not f.suffix == ".pyc"]

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in files:
            if fp.is_file():
                # Store relative to src_dir so the zip root contains handler.py etc.
                arcname = fp.relative_to(src_dir)
                zf.write(fp, arcname)

    return zip_path


def _sha256_hex(path: Path) -> str:
    """Return the hex-encoded SHA-256 of *path*."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------


def _download_from_url(url: str, dest: Path) -> None:
    """Download a file from a presigned URL and write to *dest*."""
    result = subprocess.run(
        ["curl", "-s", "-f", "-L", "-o", str(dest), "--max-time", "60", url],
        capture_output=True,
        text=True,
        timeout=75,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Download failed: {result.stderr.strip()}")


def _backup_function(function: str) -> None:
    """Download the current function code from FC and save as a local backup."""
    client = _get_fc_client()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_dir = BUILD_DIR / "backup" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{function}.zip"

    try:
        fcn_name = _fc_function_name(function)
        from alibabacloud_fc20230330.models import (
            GetFunctionCodeRequest,
            GetFunctionRequest,
        )

        resp = client.get_function(fcn_name, GetFunctionRequest())

        # Log env var names (not values) for the backup record.
        env_var_names: list[str] = []
        if hasattr(resp.body, "environment_variables") and resp.body.environment_variables:
            env_var_names = list(resp.body.environment_variables.keys())

        backup_meta = {
            "function": function,
            "timestamp": timestamp,
            "environment_variable_names": env_var_names,
        }
        meta_path = backup_dir / f"{function}.meta.json"
        meta_path.write_text(json.dumps(backup_meta, indent=2))

        # Download actual code zip via GetFunctionCode → presigned OSS URL
        try:
            code_resp = client.get_function_code(fcn_name, GetFunctionCodeRequest())
            code_url = getattr(code_resp.body, "url", None)
            if code_url:
                _download_from_url(code_url, backup_path)
                print(f"  [backup] saved: {backup_path}")
            else:
                print(
                    f"  [backup] WARNING: get_function_code returned no URL "
                    f"for {function}; recording meta only."
                )
        except Exception as code_exc:
            print(
                f"  [backup] WARNING: could not download code for {function}: "
                f"{code_exc}; recording meta only."
            )

        return backup_path

    except Exception as exc:
        # Function may not exist yet — that's fine for first deploy.
        msg = str(exc).lower()
        if "not found" in msg or "functionnotfound" in msg or "does not exist" in msg:
            print(f"  [backup] function {function} does not exist yet — skip backup.")
            return None
        print(f"  [backup] WARNING: backup failed for {function}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------


def deploy(function: str) -> bool:
    """Package and upload *function* to FC 3.0.

    Steps:
    1. Backup current online code.
    2. Package function source as zip.
    3. Upload to FC 3.0.
    4. Write deploy log.
    5. Curl the function URL to verify it's alive.

    Returns True on success.
    """
    print(f"\n{'='*60}")
    print(f"  deploy-fc: {function}")
    print(f"{'='*60}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    # 1. Backup
    print("  [1/4] backup …")
    _backup_function(function)

    # 2. Package
    print("  [2/4] packaging …")
    zip_path = _package_function(function)
    zip_sha256 = _sha256_hex(zip_path)
    print(f"        zip: {zip_path}")
    print(f"        sha256: {zip_sha256}")
    print(f"        size: {zip_path.stat().st_size} bytes")

    # 3. Upload
    print("  [3/4] uploading to FC 3.0 …")
    client = _get_fc_client()
    fcn_name = _fc_function_name(function)

    t0 = time.monotonic()
    try:
        # Read the zip bytes, base64-encode for FC SDK
        code_bytes = zip_path.read_bytes()
        b64_code = base64.b64encode(code_bytes).decode("ascii")

        from alibabacloud_fc20230330.models import (
            InputCodeLocation,
            UpdateFunctionInput,
            UpdateFunctionRequest,
        )

        update_req = UpdateFunctionRequest(
            body=UpdateFunctionInput(
                code=InputCodeLocation(zip_file=b64_code),
            )
        )
        client.update_function(fcn_name, update_req)
        elapsed = time.monotonic() - t0
        print(f"        uploaded in {elapsed:.1f}s")
    except Exception as exc:
        elapsed = time.monotonic() - t0
        print(f"        UPLOAD FAILED ({elapsed:.1f}s): {exc}", file=sys.stderr)
        _write_deploy_log(function, timestamp, zip_sha256, elapsed, success=False, error=str(exc))
        return False

    # 4. Curl survival check
    print("  [4/4] curl survival check …")
    alive, curl_output = _curl_survival_check(function)
    if alive:
        print(f"        OK: {curl_output}")
    else:
        print(f"        FAIL: {curl_output}", file=sys.stderr)

    # Write deploy log
    _write_deploy_log(function, timestamp, zip_sha256, elapsed, success=alive)

    return alive


def _curl_survival_check(function: str) -> tuple[bool, str]:
    """Hit the FC function's public URL and check it returns non-5xx."""
    urls = {
        "issue-credential": "https://issue-cedential-ottfirocds.cn-beijing.fcapp.run",
        "verify-upload": "https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run",
    }
    url = urls.get(function)
    if not url:
        return False, f"Unknown function: {function}"

    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "10", url],
            capture_output=True,
            text=True,
            timeout=15,
        )
        http_code_str = result.stdout.strip()
        try:
            http_code = int(http_code_str)
        except ValueError:
            return False, f"unexpected curl output: {http_code_str!r}"

        if 200 <= http_code < 600:
            return True, f"HTTP {http_code}"
        return False, f"HTTP {http_code} (unexpected)"
    except subprocess.TimeoutExpired:
        return False, "curl timed out"
    except Exception as exc:
        return False, str(exc)


def _write_deploy_log(
    function: str,
    timestamp: str,
    zip_sha256: str,
    upload_elapsed: float,
    success: bool,
    error: str | None = None,
) -> None:
    """Write a structured deploy log entry."""
    logs_dir = BUILD_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"deploy-{timestamp}.log"

    lines = [
        f"function: {function}",
        f"timestamp: {timestamp}",
        f"zip_sha256: {zip_sha256}",
        f"upload_elapsed_seconds: {upload_elapsed:.1f}",
        f"success: {success}",
    ]
    if error:
        lines.append(f"error: {error}")

    log_path.write_text("\n".join(lines) + "\n")
    print(f"  [log] {log_path}")


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


def rollback(function: str) -> bool:
    """Restore *function* from the most recent local backup."""
    print(f"\n{'='*60}")
    print(f"  rollback-fc: {function}")
    print(f"{'='*60}")

    backups_dir = BUILD_DIR / "backup"
    if not backups_dir.is_dir():
        print("  ERROR: No backups found.", file=sys.stderr)
        return False

    # Find the most recent backup for this function
    backup_zips: list[tuple[Path, str]] = []  # (path, timestamp)
    for ts_dir in sorted(backups_dir.iterdir(), reverse=True):
        if not ts_dir.is_dir():
            continue
        candidate = ts_dir / f"{function}.zip"
        if candidate.is_file():
            backup_zips.append((candidate, ts_dir.name))

    if not backup_zips:
        print(f"  ERROR: No backup found for function {function}.", file=sys.stderr)
        return False

    backup_path, ts = backup_zips[0]
    print(f"  Restoring from backup: {backup_path}")

    client = _get_fc_client()
    fcn_name = _fc_function_name(function)

    t0 = time.monotonic()
    try:
        code_bytes = backup_path.read_bytes()
        b64_code = base64.b64encode(code_bytes).decode("ascii")

        from alibabacloud_fc20230330.models import (
            InputCodeLocation,
            UpdateFunctionInput,
            UpdateFunctionRequest,
        )

        update_req = UpdateFunctionRequest(
            body=UpdateFunctionInput(
                code=InputCodeLocation(zip_file=b64_code),
            )
        )
        client.update_function(fcn_name, update_req)
        elapsed = time.monotonic() - t0
        print(f"  Restored {function} from {ts} in {elapsed:.1f}s")

        # Curl check
        print("  curl survival check …")
        alive, curl_output = _curl_survival_check(function)
        if alive:
            print(f"        OK: {curl_output}")
        else:
            print(f"        FAIL: {curl_output}", file=sys.stderr)

        return alive
    except Exception as exc:
        elapsed = time.monotonic() - t0
        print(f"  Rollback FAILED ({elapsed:.1f}s): {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------


def fc_logs(function: str) -> bool:
    """Fetch recent FC logs for *function* via SLS or explain why they aren't
    available."""
    print(f"\n{'='*60}")
    print(f"  fc-logs: {function}")
    print(f"{'='*60}")

    client = _get_fc_client()
    fcn_name = _fc_function_name(function)

    try:
        from alibabacloud_fc20230330.models import GetFunctionRequest

        resp = client.get_function(fcn_name, GetFunctionRequest())

        # Check if SLS log config exists
        log_config = getattr(resp.body, "log_config", None) if hasattr(resp.body, "log_config") else None
        if log_config:
            project = getattr(log_config, "project", None)
            logstore = getattr(log_config, "logstore", None)
            if project and logstore:
                print(f"  SLS project: {project}")
                print(f"  SLS logstore: {logstore}")
                print()
                print(
                    "  ℹ  SLS log retrieval requires a separate SLS client. "
                    "Use the Alibaba Cloud console or SLS CLI for direct log access."
                )
                print(f"     Project:  {project}")
                print(f"     Logstore: {logstore}")
                print(f"     Function: {function}")
                return True
            else:
                print(
                    "  ℹ  Log service is not configured for this function.\n"
                    "     To configure:\n"
                    "     1. Go to FC 3.0 console → Functions → {function}\n"
                    "     2. Edit → Logging → Enable SLS log collection\n"
                    "     3. Select or create a project and logstore\n"
                )
                return True
        else:
            print(
                "  ℹ  Log service is not configured for this function.\n"
                "     To enable: FC 3.0 console → Functions → {function} → Edit → Logging"
            )
            return True

    except Exception as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FC 3.0 deploy / rollback / logs",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    deploy_p = sub.add_parser("deploy", help="Package and upload function(s) to FC 3.0")
    deploy_p.add_argument(
        "function",
        nargs="?",
        choices=ALL_FUNCTIONS + [None],
        default=None,
        help=f"Function name (kebab-case); omit to deploy all ({', '.join(ALL_FUNCTIONS)})",
    )

    rollback_p = sub.add_parser("rollback", help="Restore function from most recent backup")
    rollback_p.add_argument(
        "function",
        choices=ALL_FUNCTIONS,
        help="Function name (kebab-case)",
    )

    logs_p = sub.add_parser("logs", help="Fetch/view FC function logs")
    logs_p.add_argument(
        "function",
        choices=ALL_FUNCTIONS,
        help="Function name (kebab-case)",
    )

    args = parser.parse_args()

    ok = True

    if args.command == "deploy":
        if args.function:
            ok = deploy(args.function)
        else:
            for fn in ALL_FUNCTIONS:
                if not deploy(fn):
                    ok = False

    elif args.command == "rollback":
        ok = rollback(args.function)

    elif args.command == "logs":
        ok = fc_logs(args.function)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
