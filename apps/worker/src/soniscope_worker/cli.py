"""Worker CLI（基于 typer）。

US-001 提供骨架命令；US-002 增加 check-config / init-dirs。
主轮询与 retranscribe 等在后续 story 实现。
"""

import typer

from soniscope_worker import __version__
from soniscope_worker.config import (
    ConfigError,
    config_path,
    config_permission_is_600,
    load_config,
)
from soniscope_worker.paths import init_runtime_dirs

app = typer.Typer(
    add_completion=False,
    help="SoniScope Worker：轮询 OSS、标准化音频、云端 ASR、本地落盘。",
)


@app.command()
def run() -> None:
    """启动 Worker 主轮询循环（轮询 OSS recordings/、HeadObject 元数据、安全下载，US-021）。"""
    from soniscope_worker.poller import run_worker_run

    run_worker_run(log=typer.echo)


@app.command()
def version() -> None:
    """打印 Worker 版本号。"""
    typer.echo(__version__)


@app.command(name="check-config")
def check_config() -> None:
    """读取 config.yaml → 校验必填字段 → 打印脱敏摘要 → 检查权限是否为 600。"""
    path = config_path()
    try:
        cfg = load_config(path)
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if not config_permission_is_600(path):
        mode = oct(path.stat().st_mode & 0o777)
        typer.echo(
            f"⚠️  警告：{path} 权限为 {mode}，应为 600（请执行：chmod 600 {path}）",
            err=True,
        )

    typer.echo(f"config: {path}")
    for line in cfg.masked_summary():
        typer.echo(line)


@app.command(name="init-dirs")
def init_dirs() -> None:
    """在 $SONISCOPE_HOME 下幂等创建 inbox/ inbox/failed/ fragments/ tmp/。"""
    for d in init_runtime_dirs():
        typer.echo(f"ok  {d}")


@app.command(name="verify-prep")
def verify_prep() -> None:
    """一键校验 US-001 人工准备产物（OSS / STS / FC / NLS / fixture / 环境）。"""
    from soniscope_worker.verify_prep import run_verify_prep

    lines, code = run_verify_prep()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="deploy-fc")
def deploy_fc(
    function: str = typer.Option("", "--function", "-f", help="云端函数名（不传则部署全部）"),
) -> None:
    """打包 + 备份 + 部署 FC 函数（不传 --function 时部署 issue-credential 与 verify-upload）。"""
    from soniscope_worker.fc_deploy import run_deploy

    lines, code = run_deploy(function or None)
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="rollback-fc")
def rollback_fc(
    function: str = typer.Option("", "--function", "-f", help="云端函数名"),
) -> None:
    """从最新备份恢复指定 FC 函数代码。"""
    from soniscope_worker.fc_deploy import run_rollback

    lines, code = run_rollback(function)
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="fc-logs")
def fc_logs(
    function: str = typer.Option("", "--function", "-f", help="云端函数名"),
) -> None:
    """拉取指定 FC 函数近 1 小时日志（日志服务未配置时输出明确诊断）。"""
    from soniscope_worker.fc_deploy import run_fc_logs

    lines, code = run_fc_logs(function)
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-fc-live")
def test_fc_live(
    code: str = typer.Option(
        "", "--code", help="allowlist 内的一次性 wx.login code（成功 + STS 反例）"
    ),
    code_not_allowed: str = typer.Option(
        "", "--code-not-allowed", help="真实但不在 allowlist 的一次性 code（403 路径）"
    ),
    size_code: str = typer.Option(
        "", "--size-code", help="用于 size 超限场景的一次性 code（SIZE_EXCEEDED）"
    ),
    skip_expiry: bool = typer.Option(
        False, "--skip-expiry", help="跳过过期反例（避免等待 >= 900s）"
    ),
) -> None:
    """issue-credential 云端联调与 STS 安全反例（伪造 code / allowlist / 越权 / 过期 / size）。"""
    from soniscope_worker.fc_live import LiveOptions, run_test_fc_live

    opts = LiveOptions(
        allow_code=code,
        not_allowed_code=code_not_allowed,
        size_code=size_code,
        check_expiry=not skip_expiry,
    )
    lines, exit_code = run_test_fc_live(opts)
    for line in lines:
        typer.echo(line, err=exit_code != 0)
    raise typer.Exit(code=exit_code)


@app.command(name="oss-delete-obj")
def oss_delete_obj(
    fragment_id: str = typer.Option("", "--fragment-id", help="目标 fragment_id"),
    yes: bool = typer.Option(False, "--yes", help="确认删除（仅测试用）"),
) -> None:
    """⚠️ 仅测试用：删除指定 fragment 的 OSS 对象（构造 verify 失败场景）。

    需 --yes 或环境变量 SONISCOPE_ALLOW_OSS_DELETE=1；Worker 业务路径绝不删除 OSS。
    """
    import os

    from soniscope_worker.oss_admin import run_oss_delete_obj

    if not fragment_id.strip():
        typer.echo("缺少 --fragment-id（make oss-delete-obj FRAGMENT_ID=<id>）", err=True)
        raise typer.Exit(code=1)
    lines, code = run_oss_delete_obj(fragment_id, confirmed=yes, env=os.environ)
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-verify-upload")
def test_verify_upload(
    verified_code: str = typer.Option(
        "", "--verified-code", help="verified:true 场景的一次性 code（AC#3）"
    ),
    not_found_code: str = typer.Option(
        "", "--not-found-code", help="OBJECT_NOT_FOUND 场景的一次性 code（AC#4）"
    ),
    mismatch_code: str = typer.Option(
        "", "--mismatch-code", help="SIZE_MISMATCH 场景的一次性 code（AC#5）"
    ),
) -> None:
    """verify-upload 云端闭环联调（verified / 对象缺失 / 大小不一致 / 鉴权失败 + P95）。"""
    from soniscope_worker.verify_upload_live import (
        VerifyLiveOptions,
        run_test_verify_upload,
    )

    opts = VerifyLiveOptions(
        verified_code=verified_code,
        not_found_code=not_found_code,
        mismatch_code=mismatch_code,
    )
    lines, exit_code = run_test_verify_upload(opts)
    for line in lines:
        typer.echo(line, err=exit_code != 0)
    raise typer.Exit(code=exit_code)


@app.command(name="show-oss-object")
def show_oss_object(
    fragment_id: str = typer.Option("", "--fragment-id", help="目标 fragment_id"),
) -> None:
    """查看单个 OSS 对象详情（存在性 / size / etag / last_modified / 用户自定义元数据，US-017）。"""
    from soniscope_worker.oss_admin import run_show_oss_object

    if not fragment_id.strip():
        typer.echo("缺少 --fragment-id（make show-oss-object FRAGMENT_ID=<id>）", err=True)
        raise typer.Exit(code=1)
    lines, code = run_show_oss_object(fragment_id)
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-sts-escape")
def test_sts_escape(
    code: str = typer.Option(
        "", "--code", help="可选：allowlist 内一次性 wx.login code（走 FC 真实签发）"
    ),
) -> None:
    """STS 单 key 越权验证：用单文件 STS 写其他 key 必须被 OSS 拒（AccessDenied，US-017）。"""
    from soniscope_worker.sts_escape import StsEscapeOptions, run_test_sts_escape

    opts = StsEscapeOptions(code=code)
    lines, exit_code = run_test_sts_escape(opts)
    for line in lines:
        typer.echo(line, err=exit_code != 0)
    raise typer.Exit(code=exit_code)


@app.command(name="test-poll-interval")
def test_poll_interval(
    expected: int = typer.Option(
        30, "--expected", help="期望的 poll.interval_seconds（默认 30，AC#8）"
    ),
    iterations: int = typer.Option(3, "--iterations", help="实际扫描轮数（用于观测间隔）"),
) -> None:
    """验证 Worker 按 config.yaml 的 poll.interval_seconds 周期扫描 OSS（US-021 AC#8）。"""
    from soniscope_worker.poller import PollIntervalOptions, run_test_poll_interval

    opts = PollIntervalOptions(expected_interval=expected, iterations=iterations)
    lines, code = run_test_poll_interval(opts)
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-wav-passthrough")
def test_wav_passthrough() -> None:
    """用 sample-20s.wav 验证 WAV 直通/无损路径（audio.sha256 == original_sha256，US-022）。"""
    from soniscope_worker.audio import run_test_wav_passthrough

    lines, code = run_test_wav_passthrough()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-audio-transcode-to-wav")
def test_audio_transcode_to_wav() -> None:
    """用 sample-20s.m4a 验证非 WAV 转码为 WAV（输出可被 ffprobe 识别为 WAV，US-022）。"""
    from soniscope_worker.audio import run_test_audio_transcode_to_wav

    lines, code = run_test_audio_transcode_to_wav()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-transcode-fail")
def test_transcode_fail() -> None:
    """用损坏音频验证转码失败留档到 inbox/failed/、不污染 fragments/（US-022）。"""
    from soniscope_worker.audio import run_test_transcode_fail

    lines, code = run_test_transcode_fail()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-crash-recovery")
def test_crash_recovery() -> None:
    """模拟转写中 kill -9 后重启：清理 tmp 残留并重新转写补齐 transcript.json 与 .done。"""
    from soniscope_worker.recovery import run_test_crash_recovery

    lines, code = run_test_crash_recovery()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="simulate-worker-crash")
def simulate_worker_crash(
    case: str = typer.Option(
        ..., "--case", help="崩溃场景：missing-done | stale-part"
    ),
    fragment_id: str = typer.Option(..., "--fragment-id", help="目标 fragment_id"),
) -> None:
    """注入 Worker 崩溃场景（删 .done / 残留 .part），重启后由恢复扫描修复（US-023）。"""
    from soniscope_worker.recovery import run_simulate_worker_crash

    lines, code = run_simulate_worker_crash(case, fragment_id)
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-fragment-integrity")
def test_fragment_integrity() -> None:
    """跑完一条 Fragment 后校验 audio.wav/manifest/transcript.json/transcript.txt/.done 齐全。"""
    from soniscope_worker.manifest import run_test_fragment_integrity

    lines, code = run_test_fragment_integrity()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-manifest-idempotent")
def test_manifest_idempotent() -> None:
    """同一段固定 WAV 跑两次，校验除时间戳字段外 manifest 其他字段完全一致。"""
    from soniscope_worker.manifest import run_test_manifest_idempotent

    lines, code = run_test_manifest_idempotent()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-transcribe-oss-url")
def test_transcribe_oss_url() -> None:
    """oss-url 模式转写 sample-20s.wav，校验 mode=oss-url 与 runbook §5.4 基线（US-026）。"""
    from soniscope_worker.nls import run_test_transcribe_oss_url

    lines, code = run_test_transcribe_oss_url()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-transcribe-direct")
def test_transcribe_direct() -> None:
    """direct 模式转写 sample-20s.wav，校验 mode=direct-upload 且主干与 oss-url 一致（US-026）。"""
    from soniscope_worker.nls import run_test_transcribe_direct

    lines, code = run_test_transcribe_direct()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-transcribe-perf")
def test_transcribe_perf() -> None:
    """约 1 分钟音频端到端耗时与 P-01 基线阈值比较（US-026）。"""
    from soniscope_worker.nls import run_test_transcribe_perf

    lines, code = run_test_transcribe_perf()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-download-interrupt")
def test_download_interrupt() -> None:
    """下载中 kill -9 → 重启恢复后最终完成该 Fragment（US-027）。"""
    from soniscope_worker.pipeline import run_test_download_interrupt

    lines, code = run_test_download_interrupt()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-no-redownload")
def test_no_redownload() -> None:
    """证明已 .done 的 Fragment 不会被重新下载（US-027）。"""
    from soniscope_worker.pipeline import run_test_no_redownload

    lines, code = run_test_no_redownload()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-transcribe")
def test_transcribe() -> None:
    """用 sample-20s.wav 跑完整 Worker 转写，五产物齐全且 transcript.txt 含基线主干（US-027）。"""
    from soniscope_worker.pipeline import run_test_transcribe

    lines, code = run_test_transcribe()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="retranscribe")
def retranscribe(
    fragment_id: str = typer.Argument("", help="要重转的 fragment_id（单条；批量用 --all-from）"),
    all_from: str = typer.Option(
        "", "--all-from", help="批量重转该日期（YYYY-MM-DD）及之后的所有 Fragment"
    ),
    upgrade: bool = typer.Option(
        False, "--upgrade", help="仅对 manifest 中 model/params_version 与当前配置不同的重转"
    ),
    force: bool = typer.Option(False, "--force", help="无条件重转，原子覆盖 transcript"),
) -> None:
    """显式重转 Fragment（US-028，§3.7）：正常轮询只看 .done，本命令是唯一存量重转入口。"""
    from soniscope_worker.retranscribe import run_retranscribe

    lines, code = run_retranscribe(
        fragment_id=fragment_id or None,
        all_from=all_from or None,
        upgrade=upgrade,
        force=force,
    )
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-idempotent-skip")
def test_idempotent_skip() -> None:
    """无 flag + .done 存在时 retranscribe 跳过且不改写产物（US-028 AC#5）。"""
    from soniscope_worker.retranscribe import run_test_idempotent_skip

    lines, code = run_test_idempotent_skip()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-no-auto-retranscribe")
def test_no_auto_retranscribe() -> None:
    """模型/参数变化时普通轮询不自动重转已 .done 的 Fragment（US-028 AC#1）。"""
    from soniscope_worker.retranscribe import run_test_no_auto_retranscribe

    lines, code = run_test_no_auto_retranscribe()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-cli-retranscribe")
def test_cli_retranscribe() -> None:
    """--force 无条件重转并原子覆盖 transcript.json/txt（US-028 AC#6）。"""
    from soniscope_worker.retranscribe import run_test_cli_retranscribe

    lines, code = run_test_cli_retranscribe()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="test-cli-upgrade")
def test_cli_upgrade() -> None:
    """--upgrade 只重转 model/params_version 与当前配置不同的 Fragment（US-028 AC#7）。"""
    from soniscope_worker.retranscribe import run_test_cli_upgrade

    lines, code = run_test_cli_upgrade()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)


@app.command(name="lint-miniprogram")
def lint_miniprogram() -> None:
    """对 apps/miniprogram 做静态检查（配置/域名/页面/无硬编码密钥，US-011）。"""
    from soniscope_worker.miniprogram_lint import run_lint_miniprogram

    lines, code = run_lint_miniprogram()
    for line in lines:
        typer.echo(line, err=code != 0)
    raise typer.Exit(code=code)
