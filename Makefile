# ─────────────────────────────────────────────────────────────────────────────
# SoniScope — 唯一命令入口
#
# 所有目标都在顶层运行，用户不需要 cd 到子目录。
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: install check-config init-dirs worker-run verify-prep typecheck lint test \
        deploy-fc rollback-fc fc-logs test-fc-live test-verify-upload \
        oss-delete-obj miniprogram-lint show-oss-object test-sts-escape \
        list-oss-objects verify-no-stale verify-oss-retention \
        test-poll-interval test-wav-passthrough test-audio-transcode-to-wav \
        test-transcode-fail test-crash-recovery simulate-worker-crash \
        test-fragment-integrity test-manifest-idempotent \
        test-transcribe-oss-url test-transcribe-direct test-transcribe-perf \
        test-transcribe test-download-interrupt test-no-redownload \
        retranscribe test-idempotent-skip test-no-auto-retranscribe \
        test-cli-retranscribe test-cli-upgrade

# ── 安装 ────────────────────────────────────────────────────────────────────

install:
	@echo "==> uv sync (workspace)"
	uv sync --directory apps/worker
	@echo "==> install done"

# ── 配置检查 ────────────────────────────────────────────────────────────────

check-config:
	uv run --directory apps/worker python -m soniscope_worker check-config

# ── 运行时目录初始化 ────────────────────────────────────────────────────────

init-dirs:
	uv run --directory apps/worker python -m soniscope_worker init-dirs

# ── Worker 运行 ─────────────────────────────────────────────────────────────

worker-run:
	uv run --directory apps/worker python -m soniscope_worker run

# ── 准备校验 ────────────────────────────────────────────────────────────────

verify-prep:
	uv run --directory apps/worker python -m soniscope_worker verify-prep

# ── 质量门 ──────────────────────────────────────────────────────────────────

typecheck:
	uv run --directory apps/worker --extra dev mypy --strict src/

lint:
	uv run --directory apps/worker --extra dev ruff check src/

test:
	uv run --directory apps/worker --extra dev pytest -v

# ── FC 3.0 部署 ─────────────────────────────────────────────────────────────

deploy-fc:
	uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/deploy_fc.py" deploy $(FUNCTION)

rollback-fc:
	uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/deploy_fc.py" rollback $(FUNCTION)

fc-logs:
	uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/deploy_fc.py" logs $(FUNCTION)

# ── FC 云端联调 ─────────────────────────────────────────────────────────────

test-fc-live:
	uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/test_fc_live.py"

# ── FC verify-upload 云端闭环测试 ────────────────────────────────────────────

test-verify-upload:
	uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/test_verify_upload.py"

# ── OSS 运维辅助（仅测试用）──

oss-delete-obj:
	@echo "⚠️  仅测试用 — Worker 业务源码中不存在 DeleteObject 调用"
	@echo ""
	uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/oss_delete_obj.py" $(FRAGMENT_ID)

# ── 小程序代码静态检查 ──────────────────────────────────────────

miniprogram-lint:
	@echo "==> Miniprogram static check"
	@cd apps/miniprogram && node -c app.js && node -c utils/constants.js && node -c utils/logger.js && node -c utils/crypto.js && node -c utils/idgen.js && node -c utils/uploader.js && node -c utils/cleanup.js && node -c utils/dev-injector.js && node -c pages/index/index.js && node -c pages/upload-list/upload-list.js && node -c pages/dev-menu/dev-menu.js
	@echo "==> Miniprogram JS syntax OK"

# ── OSS 运维辅助 ──────────────────────────────────────────────────

show-oss-object:
	uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/show_oss_object.py" $(FRAGMENT_ID)

test-sts-escape:
	@echo "🧪 STS 越权验证"
	@echo "需要 STS 临时凭证（access_key_id / access_key_secret / security_token / object_key）"
	uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/test_sts_escape.py" $(STS_AK_ID) $(STS_AK_SECRET) $(STS_TOKEN) $(STS_OBJECT_KEY)

list-oss-objects:
	uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/list_oss_objects.py" $(DATE)

verify-no-stale:
	uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/verify_no_stale.py"

verify-oss-retention:
	uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/verify_oss_retention.py"

# ── Worker 运维 ────────────────────────────────────────────────────

test-poll-interval:
	@echo "🧪 Worker poll interval verification"
	@echo "Setting POLL_INTERVAL_SECONDS_OVERRIDE=30 and running one cycle"
	POLL_INTERVAL_SECONDS_OVERRIDE=30 uv run --directory apps/worker python -m soniscope_worker test-poll-cycle

# ── Worker 音频处理测试 ──────────────────────────────────────────────

test-wav-passthrough:
	@echo "🧪 WAV passthrough / lossless repackaging test"
	@echo "Running audio passthrough integration tests (requires ffprobe + tests/audio fixtures)"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestWavPassthrough or test_wav_passthrough" "$(CURDIR)/apps/worker/tests/test_us022.py"

test-audio-transcode-to-wav:
	@echo "🧪 m4a → WAV transcode verification"
	@echo "Running audio transcode integration tests (requires ffmpeg + tests/audio/sample-20s.m4a)"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestTranscode or test_transcode" "$(CURDIR)/apps/worker/tests/test_us022.py"

test-transcode-fail:
	@echo "🧪 Transcode failure scenario (corrupt audio → inbox/failed/)"
	@echo "Running transcode failure tests"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestTranscodeFail or test_transcode_fail or test_failed" "$(CURDIR)/apps/worker/tests/test_us022.py"

# ── Worker 崩溃恢复测试 ────────────────────────────────────────────

test-crash-recovery:
	@echo "🧪 Worker crash recovery verification (US-023)"
	@echo "Running crash recovery unit tests"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestCrashRecovery or test_crash_recovery or TestRecoveryScan or test_recovery or TestAtomics or test_atomic" "$(CURDIR)/apps/worker/tests/test_us023.py"

simulate-worker-crash:
	@echo "🧪 Simulate Worker crash scenario"
	CASE="$(CASE)" FRAGMENT_ID="$(FRAGMENT_ID)" uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/simulate_worker_crash.py"

# ── Worker fragment 完整性测试 ──────────────────────────────────────────

test-fragment-integrity:
	@echo "🧪 Fragment integrity — 5 products in completed directory"
	@echo "Running fragment integrity tests"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestFragmentIntegrity or test_fragment_integrity or TestManifestIntegrity or test_manifest_integrity or test_five_products or test_completed_directory" "$(CURDIR)/apps/worker/tests/test_us024.py"

test-manifest-idempotent:
	@echo "🧪 Manifest idempotency — same WAV twice → same manifest (except timestamps)"
	@echo "Running manifest idempotency tests"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestManifestIdempotent or test_idempotent or test_same_wav_twice" "$(CURDIR)/apps/worker/tests/test_us024.py"

# ── Worker 转写测试 ────────────────────────────────────────────────────

test-transcribe-oss-url:
	@echo "🧪 NLS oss-url mode — transcribe via OSS presigned URL"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestPresignedUrlGeneration or TestUploadModeDispatch or TestNlsToTranscriptResult or test_oss_url" "$(CURDIR)/apps/worker/tests/test_us026.py"

test-transcribe-direct:
	@echo "🧪 NLS direct mode — transcribe via direct file upload"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestDirectMode or TestUploadModeDispatch or TestNlsToTranscriptResult or test_direct" "$(CURDIR)/apps/worker/tests/test_us026.py"

test-transcribe-perf:
	@echo "🧪 NLS transcription performance baseline"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestCostLogging or TestRetryLogic or test_cost or test_retry or test_perf or TestPollWith" "$(CURDIR)/apps/worker/tests/test_us026.py"

# ── Worker 转写重转 (US-028) ──────────────────────────────────────────────

retranscribe:
	uv run --directory apps/worker python -m soniscope_worker retranscribe $(ARGS) $(FRAGMENT_ID)

# 幂等跳过测试
test-idempotent-skip:
	@echo "🧪 Idempotent skip — .done fragment skipped in normal polling"
	@echo "Running idempotent skip tests"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestIdempotentSkip or test_idempotent_skip or test_done_skip or test_poll_skip_done" "$(CURDIR)/apps/worker/tests/test_us028.py"

# 非自动重转测试
test-no-auto-retranscribe:
	@echo "🧪 No auto retranscribe — config changes do not trigger re-transcription in normal poll"
	@echo "Running no-auto-retranscribe tests"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestNoAutoRetranscribe or test_no_auto or test_config_change_no_retrigger" "$(CURDIR)/apps/worker/tests/test_us028.py"

# CLI retranscribe 测试
test-cli-retranscribe:
	@echo "🧪 CLI retranscribe — single fragment force retranscribe"
	@echo "Running CLI retranscribe tests"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestCliRetranscribe or test_cli_retranscribe or test_force_retranscribe or test_single_retranscribe" "$(CURDIR)/apps/worker/tests/test_us028.py"

# CLI upgrade 批量测试
test-cli-upgrade:
	@echo "🧪 CLI upgrade — batch retranscribe with --upgrade flag"
	@echo "Running CLI upgrade tests"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestCliUpgrade or test_cli_upgrade or test_upgrade_retranscribe or test_batch_retranscribe or test_all_from" "$(CURDIR)/apps/worker/tests/test_us028.py"

# ── Worker 转写集成测试（US-027）────────────────────────────────────────

test-transcribe:
	@echo "🧪 Full Worker transcription pipeline (download → transcribe → .done)"
	@echo "Running transcription pipeline integration tests"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestTranscribePipeline or TestPollCycleIntegration or test_poll_cycle or test_transcribe or test_full_pipeline or TestResumeIncomplete or test_resume" "$(CURDIR)/apps/worker/tests/test_us027.py"

test-download-interrupt:
	@echo "🧪 Download interrupt — kill -9 during download, restart completes"
	@echo "Running download interrupt recovery tests"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestDownloadInterrupt or test_download_interrupt or test_restart_completes" "$(CURDIR)/apps/worker/tests/test_us027.py"

test-no-redownload:
	@echo "🧪 No redownload — .done fragments skipped in poll cycle"
	@echo "Running idempotency tests (OSS call counting)"
	@uv run --directory apps/worker --extra dev pytest -v -k "TestNoRedownload or test_no_redownload or test_skip_done or test_idempotent_poll" "$(CURDIR)/apps/worker/tests/test_us027.py"
