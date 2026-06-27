# 日观声记 SoniScope —— 顶层 Makefile（唯一命令入口，用户无需 cd 进子目录）
#
# 命令随 story 分阶段实现。US-001 提供骨架级 install / check-config / init-dirs /
# worker-run / typecheck / lint / test；check-config 与 init-dirs 的完整逻辑在 US-002 实现。

.PHONY: install check-config init-dirs verify-prep worker-run \
	deploy-fc rollback-fc fc-logs test-fc-live test-verify-upload oss-delete-obj \
	show-oss-object test-sts-escape test-poll-interval \
	test-wav-passthrough test-audio-transcode-to-wav test-transcode-fail \
	test-crash-recovery simulate-worker-crash \
	test-fragment-integrity test-manifest-idempotent \
	test-transcribe-oss-url test-transcribe-direct test-transcribe-perf \
	test-download-interrupt test-no-redownload test-transcribe \
	retranscribe test-idempotent-skip test-no-auto-retranscribe \
	test-cli-retranscribe test-cli-upgrade \
	lint-miniprogram typecheck lint test help
.DEFAULT_GOAL := help

help: ## 显示可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## 安装所有 Python 依赖并生成 lock 文件（uv workspace）
	uv sync

check-config: ## 读取 config.yaml → 校验必填字段 → 打印脱敏摘要 → 检查 600 权限
	uv run python -m soniscope_worker check-config

init-dirs: ## 在 \$$SONISCOPE_HOME 下幂等创建 inbox/ inbox/failed/ fragments/ tmp/
	uv run python -m soniscope_worker init-dirs

verify-prep: ## 一键校验 US-001 人工准备产物（OSS/STS/FC/NLS/fixture/环境）
	uv run python -m soniscope_worker verify-prep

worker-run: ## 启动 Worker 主轮询
	uv run python -m soniscope_worker run

deploy-fc: ## 打包+备份+部署 FC 函数（FUNCTION=<name>；不传则部署两个函数）
	uv run python -m soniscope_worker deploy-fc $(if $(strip $(FUNCTION)),--function $(FUNCTION),)

rollback-fc: ## 从最新备份回滚 FC 函数（FUNCTION=<name>）
	uv run python -m soniscope_worker rollback-fc --function $(FUNCTION)

fc-logs: ## 拉取近 1 小时 FC 日志（FUNCTION=<name>）
	uv run python -m soniscope_worker fc-logs --function $(FUNCTION)

test-fc-live: ## issue-credential 云端联调（CODE= CODE_NOT_ALLOWED= SIZE_CODE= SKIP_EXPIRY=1）
	uv run python -m soniscope_worker test-fc-live \
		$(if $(strip $(CODE)),--code $(CODE),) \
		$(if $(strip $(CODE_NOT_ALLOWED)),--code-not-allowed $(CODE_NOT_ALLOWED),) \
		$(if $(strip $(SIZE_CODE)),--size-code $(SIZE_CODE),) \
		$(if $(strip $(SKIP_EXPIRY)),--skip-expiry,)

test-verify-upload: ## verify-upload 云端闭环（VERIFIED_CODE= NOT_FOUND_CODE= MISMATCH_CODE=）
	uv run python -m soniscope_worker test-verify-upload \
		$(if $(strip $(VERIFIED_CODE)),--verified-code $(VERIFIED_CODE),) \
		$(if $(strip $(NOT_FOUND_CODE)),--not-found-code $(NOT_FOUND_CODE),) \
		$(if $(strip $(MISMATCH_CODE)),--mismatch-code $(MISMATCH_CODE),)

oss-delete-obj: ## 【仅测试用】删除 OSS 对象构造缺失场景（FRAGMENT_ID=<id> YES=1 或 SONISCOPE_ALLOW_OSS_DELETE=1）
	uv run python -m soniscope_worker oss-delete-obj --fragment-id $(FRAGMENT_ID) \
		$(if $(strip $(YES)),--yes,)

show-oss-object: ## 查看 OSS 对象详情（FRAGMENT_ID=<id>：存在性/size/etag/last_modified/元数据）
	uv run python -m soniscope_worker show-oss-object --fragment-id $(FRAGMENT_ID)

test-sts-escape: ## STS 单 key 越权验证：写其他 key 必须 AccessDenied（CODE= 可选走 FC）
	uv run python -m soniscope_worker test-sts-escape \
		$(if $(strip $(CODE)),--code $(CODE),)

test-poll-interval: ## 验证 Worker 按 poll.interval_seconds 周期扫描（EXPECTED=30 ITERATIONS=3）
	uv run python -m soniscope_worker test-poll-interval \
		$(if $(strip $(EXPECTED)),--expected $(EXPECTED),) \
		$(if $(strip $(ITERATIONS)),--iterations $(ITERATIONS),)

test-wav-passthrough: ## 用 sample-20s.wav 验证 WAV 直通（audio.sha256==original_sha256）
	uv run python -m soniscope_worker test-wav-passthrough

test-audio-transcode-to-wav: ## 用 sample-20s.m4a 验证非 WAV 转码为 WAV
	uv run python -m soniscope_worker test-audio-transcode-to-wav

test-transcode-fail: ## 用损坏音频验证转码失败留档到 inbox/failed/
	uv run python -m soniscope_worker test-transcode-fail

test-crash-recovery: ## 转写中 kill -9 → 重启清理 tmp 并重新转写补齐 transcript.json 与 .done
	uv run python -m soniscope_worker test-crash-recovery

simulate-worker-crash: ## 注入崩溃场景（CASE=missing-done|stale-part FRAGMENT_ID=<id>）
	uv run python -m soniscope_worker simulate-worker-crash \
		--case "$(CASE)" --fragment-id "$(FRAGMENT_ID)"

test-fragment-integrity: ## 跑完一条 Fragment 校验五产物齐全（audio/manifest/transcript.json/txt/.done）
	uv run python -m soniscope_worker test-fragment-integrity

test-manifest-idempotent: ## 同一固定 WAV 跑两次，除时间戳外 manifest 完全一致
	uv run python -m soniscope_worker test-manifest-idempotent

test-transcribe-oss-url: ## oss-url 模式转写 sample-20s.wav，校验 mode=oss-url 与 §5.4 基线
	uv run python -m soniscope_worker test-transcribe-oss-url

test-transcribe-direct: ## direct 模式转写 sample-20s.wav，校验 mode=direct-upload 且主干一致
	uv run python -m soniscope_worker test-transcribe-direct

test-transcribe-perf: ## 约 1 分钟音频端到端耗时与 P-01 基线阈值比较
	uv run python -m soniscope_worker test-transcribe-perf

test-download-interrupt: ## 下载中 kill -9 → 重启恢复后最终完成该 Fragment
	uv run python -m soniscope_worker test-download-interrupt

test-no-redownload: ## 证明已 .done Fragment 不会重新下载
	uv run python -m soniscope_worker test-no-redownload

test-transcribe: ## 用 sample-20s.wav 跑完整 Worker 转写，校验五产物与基线主干
	uv run python -m soniscope_worker test-transcribe

retranscribe: ## 显式重转（FRAGMENT_ID=<id> 单条；或 ARGS="--all-from <date> --upgrade" 批量）
	uv run python -m soniscope_worker retranscribe $(if $(strip $(FRAGMENT_ID)),$(FRAGMENT_ID),) $(ARGS)

test-idempotent-skip: ## 无 flag + .done 存在 → retranscribe 跳过且不改写产物
	uv run python -m soniscope_worker test-idempotent-skip

test-no-auto-retranscribe: ## 模型/参数变化时普通轮询不自动重转已 .done Fragment
	uv run python -m soniscope_worker test-no-auto-retranscribe

test-cli-retranscribe: ## --force 无条件重转并原子覆盖 transcript.json/txt
	uv run python -m soniscope_worker test-cli-retranscribe

test-cli-upgrade: ## --upgrade 只重转 model/params_version 不同的 Fragment
	uv run python -m soniscope_worker test-cli-upgrade

typecheck: ## mypy strict 类型检查
	uv run mypy

lint: ## ruff（workspace）+ 小程序源码静态检查；遗留 scripts/ 由各自 story 收口
	uv run ruff check apps/
	uv run python -m soniscope_worker lint-miniprogram

test: ## pytest 单元测试（mock 云端依赖）
	uv run pytest
