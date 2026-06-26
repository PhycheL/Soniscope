# 日观声记 SoniScope —— 顶层 Makefile（唯一命令入口，用户无需 cd 进子目录）
#
# 命令随 story 分阶段实现。US-001 提供骨架级 install / check-config / init-dirs /
# worker-run / typecheck / lint / test；check-config 与 init-dirs 的完整逻辑在 US-002 实现。

.PHONY: install check-config init-dirs verify-prep worker-run \
	deploy-fc rollback-fc fc-logs test-fc-live test-verify-upload oss-delete-obj \
	typecheck lint test help
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

typecheck: ## mypy strict 类型检查
	uv run mypy

lint: ## ruff 静态检查（workspace 代码；遗留 scripts/ 由各自 story 收口）
	uv run ruff check apps/

test: ## pytest 单元测试（mock 云端依赖）
	uv run pytest
