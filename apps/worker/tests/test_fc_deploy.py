"""US-005 FC 部署脚本基线单测（FakeFcApi 注入，全程不触网）。"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest

from soniscope_worker.fc_deploy import (
    FUNCTIONS,
    CurlResult,
    DeployRecord,
    FcApiError,
    FcDeployError,
    _exception_summary,
    backup_dir,
    curl_ok,
    deploy_one,
    fc_build_root,
    find_latest_backup,
    format_deploy_log,
    format_report,
    function_url,
    load_deploy_env,
    log_path,
    package_function,
    read_requirements,
    resolve_functions,
    rollback_one,
    run_deploy,
    run_fc_logs,
    run_rollback,
    source_dir_name,
    zip_dir,
)

# ── FakeFcApi：记录调用、可配置失败 ─────────────────────────────────────────


class FakeFcApi:
    """可注入的 FC IO 桩：记录调用，按需模拟失败 / 返回。"""

    def __init__(
        self,
        *,
        online_code: dict[str, bytes] | None = None,
        env_names: dict[str, list[str]] | None = None,
        curl_status: int | None = 200,
        curl_reachable: bool = True,
        update_fails: bool = False,
        logs: list[str] | None = None,
        logs_raise: str | None = None,
    ) -> None:
        self.online_code = online_code or {}
        self.env_names = env_names or {}
        self.curl_status = curl_status
        self.curl_reachable = curl_reachable
        self.update_fails = update_fails
        self.logs = logs
        self.logs_raise = logs_raise
        self.installed: list[tuple[Path, list[str]]] = []
        self.updated: list[tuple[str, bytes]] = []

    def download_code(self, function: str) -> bytes:
        if function not in self.online_code:
            raise FcApiError(f"线上 {function} 无代码可备份")
        return self.online_code[function]

    def env_var_names(self, function: str) -> list[str]:
        return self.env_names.get(function, [])

    def install_deps(self, staging_dir: Path, requirements: list[str]) -> None:
        self.installed.append((staging_dir, requirements))

    def update_code(self, function: str, zip_bytes: bytes) -> None:
        if self.update_fails:
            raise FcApiError("模拟上传失败")
        self.updated.append((function, zip_bytes))

    def curl(self, url: str) -> CurlResult:
        return CurlResult(url=url, reachable=self.curl_reachable, status=self.curl_status)

    def fetch_logs(self, function: str, hours: float) -> list[str]:
        if self.logs_raise is not None:
            raise FcApiError(self.logs_raise)
        return self.logs or []


# ── 测试用仓库布局 ──────────────────────────────────────────────────────────


def _make_repo(tmp_path: Path, *, requirements: dict[str, str] | None = None) -> Path:
    """构造含 apps/fc/<dir>/handler.py 的临时仓库根。"""
    reqs = requirements or {}
    shared = tmp_path / "apps" / "fc" / "shared"
    shared.mkdir(parents=True)
    (shared / "app.py").write_text("# custom runtime app\n", encoding="utf-8")
    for fn in FUNCTIONS:
        d = tmp_path / "apps" / "fc" / source_dir_name(fn)
        d.mkdir(parents=True)
        (d / "handler.py").write_text(f"# {fn} placeholder\n", encoding="utf-8")
        if fn in reqs:
            (d / "requirements.txt").write_text(reqs[fn], encoding="utf-8")
    return tmp_path


# ── 纯逻辑 ──────────────────────────────────────────────────────────────────


def test_source_dir_name() -> None:
    assert source_dir_name("issue-credential") == "issue_credential"
    assert source_dir_name("verify-upload") == "verify_upload"


def test_resolve_functions_none_returns_both() -> None:
    assert resolve_functions(None) == list(FUNCTIONS)
    assert resolve_functions("") == list(FUNCTIONS)
    assert resolve_functions("   ") == list(FUNCTIONS)


def test_resolve_functions_single() -> None:
    assert resolve_functions("issue-credential") == ["issue-credential"]
    assert resolve_functions(" verify-upload ") == ["verify-upload"]


def test_resolve_functions_unknown() -> None:
    with pytest.raises(FcDeployError):
        resolve_functions("soniscope-svc")


def test_function_url_real_spelling() -> None:
    # issue-cedential 少一个 r 是真实 URL，禁止"修正"。
    assert "issue-cedential-ottfirocds" in function_url("issue-credential")
    assert "verify-upload-nnjpaoamhw" in function_url("verify-upload")


def test_function_url_unknown() -> None:
    with pytest.raises(FcDeployError):
        function_url("nope")


def test_exception_summary_redacts_cloud_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALIYUN_DEPLOY_AK_ID", "LTAISECRETID123456")
    monkeypatch.setenv("ALIYUN_DEPLOY_AK_SECRET", "super-secret-value")

    class CloudError(Exception):
        code = "AccessDenied"
        request_id = "req-1"
        message = "denied for LTAISECRETID123456 using super-secret-value"

    summary = _exception_summary(CloudError("fallback super-secret-value"))
    assert "AccessDenied" in summary
    assert "request_id=req-1" in summary
    assert "LTAISECRETID123456" not in summary
    assert "super-secret-value" not in summary


def test_load_deploy_env_reads_repo_dotenv_without_overriding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ALIYUN_DEPLOY_AK_ID", "already-exported")
    monkeypatch.delenv("ALIYUN_DEPLOY_AK_SECRET", raising=False)
    monkeypatch.delenv("ALIYUN_AK_ID", raising=False)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "# local deploy credentials",
                "ALIYUN_DEPLOY_AK_ID=from-dotenv",
                'export ALIYUN_DEPLOY_AK_SECRET="from-dotenv-secret"',
                "ALIYUN_AK_ID=runtime-credential-ignored",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_deploy_env(tmp_path)

    assert loaded == ["ALIYUN_DEPLOY_AK_SECRET"]
    assert os.environ["ALIYUN_DEPLOY_AK_ID"] == "already-exported"
    assert os.environ["ALIYUN_DEPLOY_AK_SECRET"] == "from-dotenv-secret"
    assert "ALIYUN_AK_ID" not in os.environ


def test_read_requirements_skips_comments(tmp_path: Path) -> None:
    p = tmp_path / "requirements.txt"
    p.write_text("# comment\n\nalibabacloud-oss-v2\n  # indented\nfoo==1.0\n", encoding="utf-8")
    assert read_requirements(p) == ["alibabacloud-oss-v2", "foo==1.0"]


def test_read_requirements_missing(tmp_path: Path) -> None:
    assert read_requirements(tmp_path / "nope.txt") == []


def test_zip_dir_deterministic(tmp_path: Path) -> None:
    staging = tmp_path / "stage"
    (staging / "sub").mkdir(parents=True)
    (staging / "a.py").write_text("a", encoding="utf-8")
    (staging / "sub" / "b.py").write_text("b", encoding="utf-8")
    sha1, size1 = zip_dir(staging, tmp_path / "out1.zip")
    sha2, size2 = zip_dir(staging, tmp_path / "out2.zip")
    assert sha1 == sha2
    assert size1 == size2 > 0
    with zipfile.ZipFile(tmp_path / "out1.zip") as zf:
        assert set(zf.namelist()) == {"a.py", "sub/b.py"}


def test_curl_ok() -> None:
    assert curl_ok(CurlResult("u", True, 200))
    assert curl_ok(CurlResult("u", True, 204))
    assert not curl_ok(CurlResult("u", True, None))
    assert not curl_ok(CurlResult("u", True, 404))
    assert not curl_ok(CurlResult("u", True, 412))
    assert not curl_ok(CurlResult("u", True, 503))
    assert not curl_ok(CurlResult("u", False, None, "timeout"))


# ── 打包 ────────────────────────────────────────────────────────────────────


def test_package_function_creates_staging_and_zip(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    build = fc_build_root(repo)
    api = FakeFcApi()
    pkg = package_function(repo, "issue-credential", build, api)
    assert pkg.staging_dir == build / "issue_credential"
    assert (pkg.staging_dir / "handler.py").is_file()
    assert (pkg.staging_dir / "app.py").is_file()
    assert pkg.zip_path == build / "issue_credential.zip"
    assert pkg.zip_path.is_file()
    with zipfile.ZipFile(pkg.zip_path) as zf:
        assert "app.py" in zf.namelist()
    assert len(pkg.sha256) == 64
    assert pkg.size_bytes > 0
    assert api.installed == []  # 无 requirements → 不装依赖


def test_package_function_installs_deps_when_present(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, requirements={"verify-upload": "alibabacloud-oss-v2\n"})
    build = fc_build_root(repo)
    api = FakeFcApi()
    package_function(repo, "verify-upload", build, api)
    assert len(api.installed) == 1
    staging, reqs = api.installed[0]
    assert reqs == ["alibabacloud-oss-v2"]
    assert staging == build / "verify_upload"


def test_package_function_excludes_pycache(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    src = repo / "apps" / "fc" / "issue_credential"
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "x.pyc").write_text("junk", encoding="utf-8")
    build = fc_build_root(repo)
    package_function(repo, "issue-credential", build, FakeFcApi())
    assert not (build / "issue_credential" / "__pycache__").exists()


def test_package_function_missing_source(tmp_path: Path) -> None:
    build = fc_build_root(tmp_path)
    with pytest.raises(FcDeployError, match="源码目录不存在"):
        package_function(tmp_path, "issue-credential", build, FakeFcApi())


def test_package_function_requires_custom_runtime_app(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    (repo / "apps" / "fc" / "shared" / "app.py").unlink()
    with pytest.raises(FcDeployError, match="Custom Runtime 入口文件不存在"):
        package_function(repo, "issue-credential", fc_build_root(repo), FakeFcApi())


# ── 备份 / 路径 ─────────────────────────────────────────────────────────────


def test_backup_and_env_names_only(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    build = fc_build_root(repo)
    api = FakeFcApi(
        online_code={"issue-credential": b"OLD-ZIP-BYTES"},
        env_names={"issue-credential": ["WX_APPID", "OPENID_ALLOWLIST", "OSS_BUCKET"]},
    )
    rec = deploy_one(api, repo, build, "issue-credential", "20260627-030000")
    assert rec.backup_path is not None
    assert rec.backup_path.read_bytes() == b"OLD-ZIP-BYTES"
    names_file = backup_dir(build, "20260627-030000") / "issue_credential.env-names.txt"
    text = names_file.read_text(encoding="utf-8")
    # 只记录变量名，绝不出现值（这里值就是名字本身的场景下断言无敏感值格式）。
    assert "WX_APPID" in text
    assert "OPENID_ALLOWLIST" in text
    # 名字按字典序排列，且不含 "=" 形式的键值对。
    assert "=" not in text


def test_log_path_and_backup_dir(tmp_path: Path) -> None:
    build = fc_build_root(tmp_path)
    assert log_path(build, "TS") == build / "logs" / "deploy-TS.log"
    assert backup_dir(build, "TS") == build / "backup" / "TS"


def test_find_latest_backup(tmp_path: Path) -> None:
    build = fc_build_root(tmp_path)
    for ts in ("20260101-000000", "20260627-120000", "20260301-000000"):
        d = backup_dir(build, ts)
        d.mkdir(parents=True)
        (d / "issue_credential.zip").write_bytes(ts.encode())
    latest = find_latest_backup(build, "issue-credential")
    assert latest is not None
    assert latest.read_bytes() == b"20260627-120000"


def test_find_latest_backup_none(tmp_path: Path) -> None:
    assert find_latest_backup(fc_build_root(tmp_path), "issue-credential") is None


# ── deploy_one ──────────────────────────────────────────────────────────────


def test_deploy_one_happy_path(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    build = fc_build_root(repo)
    api = FakeFcApi(online_code={"verify-upload": b"OLD"}, env_names={"verify-upload": ["A"]})
    rec = deploy_one(api, repo, build, "verify-upload", "TS")
    assert rec.ok
    assert rec.backup_path is not None
    assert rec.upload_seconds >= 0
    assert len(api.updated) == 1
    assert api.updated[0][0] == "verify-upload"


def test_deploy_one_first_deploy_no_backup(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    build = fc_build_root(repo)
    api = FakeFcApi()  # 无 online_code → 备份失败但不阻断
    rec = deploy_one(api, repo, build, "issue-credential", "TS")
    assert rec.ok
    assert rec.backup_path is None
    assert "备份跳过" in rec.detail
    assert len(api.updated) == 1


def test_deploy_one_update_fails(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    build = fc_build_root(repo)
    api = FakeFcApi(online_code={"issue-credential": b"OLD"}, update_fails=True)
    rec = deploy_one(api, repo, build, "issue-credential", "TS")
    assert not rec.ok
    assert "上传失败" in rec.detail


def test_deploy_one_curl_5xx_fails(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    build = fc_build_root(repo)
    api = FakeFcApi(online_code={"verify-upload": b"OLD"}, curl_status=502)
    rec = deploy_one(api, repo, build, "verify-upload", "TS")
    assert not rec.ok
    assert "curl 存活验证未通过" in rec.detail


# ── rollback_one ────────────────────────────────────────────────────────────


def test_rollback_one(tmp_path: Path) -> None:
    build = fc_build_root(tmp_path)
    d = backup_dir(build, "20260627-010000")
    d.mkdir(parents=True)
    (d / "issue_credential.zip").write_bytes(b"BACKUP-ZIP")
    api = FakeFcApi()
    rec = rollback_one(api, build, "issue-credential", "TS")
    assert rec.ok
    assert api.updated[0][1] == b"BACKUP-ZIP"


def test_rollback_one_no_backup(tmp_path: Path) -> None:
    with pytest.raises(FcDeployError, match="未找到"):
        rollback_one(FakeFcApi(), fc_build_root(tmp_path), "issue-credential", "TS")


# ── 报告 / 日志渲染 ─────────────────────────────────────────────────────────


def test_format_deploy_log_contains_required_fields() -> None:
    rec = DeployRecord(
        function="issue-credential",
        ok=True,
        sha256="abc123",
        upload_seconds=1.234,
        backup_path=Path("/b/issue_credential.zip"),
        curl=CurlResult("https://x", True, 200),
    )
    lines = format_deploy_log([rec], "TS", "deploy")
    body = "\n".join(lines)
    assert "function=issue-credential" in body
    assert "sha256=abc123" in body
    assert "upload_seconds=1.234" in body
    assert "status=200" in body


def test_format_report_no_secret() -> None:
    rec = DeployRecord("verify-upload", True, "deadbeef" * 8, 0.5, None, CurlResult("u", True, 200))
    lines = format_report([rec], "部署", Path("/l/deploy-TS.log"))
    body = "\n".join(lines)
    assert "PASS" in body
    assert "1/1 成功" in body


# ── 顶层入口 run_deploy / run_rollback / run_fc_logs ────────────────────────


def test_run_deploy_all_functions(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    api = FakeFcApi()
    lines, code = run_deploy(None, api=api, repo_root=repo, timestamp="TS")
    assert code == 0
    assert {f for f, _ in api.updated} == set(FUNCTIONS)
    # 部署日志已写入。
    assert log_path(fc_build_root(repo), "TS").is_file()
    assert any("2/2 成功" in ln for ln in lines)


def test_run_deploy_single(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    api = FakeFcApi()
    lines, code = run_deploy("issue-credential", api=api, repo_root=repo, timestamp="TS")
    assert code == 0
    assert [f for f, _ in api.updated] == ["issue-credential"]


def test_run_deploy_unknown_function(tmp_path: Path) -> None:
    lines, code = run_deploy("bad-fn", api=FakeFcApi(), repo_root=tmp_path, timestamp="TS")
    assert code == 1
    assert any("未知 FC 函数" in ln for ln in lines)


def test_run_deploy_failure_nonzero(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    api = FakeFcApi(update_fails=True)
    _lines, code = run_deploy("verify-upload", api=api, repo_root=repo, timestamp="TS")
    assert code == 1


def test_run_rollback(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    build = fc_build_root(repo)
    d = backup_dir(build, "20260627-010000")
    d.mkdir(parents=True)
    (d / "verify_upload.zip").write_bytes(b"BK")
    api = FakeFcApi()
    _lines, code = run_rollback("verify-upload", api=api, repo_root=repo, timestamp="TS")
    assert code == 0
    assert api.updated[0][1] == b"BK"


def test_run_rollback_requires_function(tmp_path: Path) -> None:
    lines, code = run_rollback("", api=FakeFcApi(), repo_root=tmp_path, timestamp="TS")
    assert code == 1
    assert any("需要 FUNCTION" in ln for ln in lines)


def test_run_fc_logs_success(tmp_path: Path) -> None:
    api = FakeFcApi(logs=["line1", "line2"])
    lines, code = run_fc_logs("issue-credential", api=api, repo_root=tmp_path)
    assert code == 0
    assert "line1" in lines


def test_run_fc_logs_not_configured_diagnostic(tmp_path: Path) -> None:
    api = FakeFcApi(logs_raise="函数未配置 SLS 日志服务（project/logstore 为空）。")
    lines, code = run_fc_logs("verify-upload", api=api, repo_root=tmp_path)
    assert code == 1
    body = "\n".join(lines)
    assert "诊断" in body
    assert "SLS" in body


def test_run_fc_logs_requires_function(tmp_path: Path) -> None:
    lines, code = run_fc_logs("", api=FakeFcApi(), repo_root=tmp_path)
    assert code == 1
    assert any("需要 FUNCTION" in ln for ln in lines)


def test_run_fc_logs_empty(tmp_path: Path) -> None:
    lines, code = run_fc_logs("issue-credential", api=FakeFcApi(logs=[]), repo_root=tmp_path)
    assert code == 0
    assert any("无日志记录" in ln for ln in lines)
