# 日观声记 SoniScope —— 顶层 Makefile（唯一命令入口，用户无需 cd 进子目录）
#
# 命令随 story 分阶段实现。US-001 提供骨架级 install / check-config / init-dirs /
# worker-run / typecheck / lint / test；check-config 与 init-dirs 的完整逻辑在 US-002 实现。

.PHONY: install check-config init-dirs worker-run typecheck lint test help
.DEFAULT_GOAL := help

help: ## 显示可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## 安装所有 Python 依赖并生成 lock 文件（uv workspace）
	uv sync

check-config: ## 读取 config.yaml → 打印脱敏摘要 → 校验必填字段（完整实现见 US-002）
	@echo "check-config: 完整配置校验将在 US-002 实现"

init-dirs: ## 在 \$$SONISCOPE_HOME 下创建 inbox/ fragments/ tmp/（完整实现见 US-002）
	@echo "init-dirs: 运行时目录初始化将在 US-002 实现"

worker-run: ## 启动 Worker 主轮询
	uv run python -m soniscope_worker run

typecheck: ## mypy strict 类型检查
	uv run mypy

lint: ## ruff 静态检查（workspace 代码；遗留 scripts/ 由各自 story 收口）
	uv run ruff check apps/

test: ## pytest 单元测试（mock 云端依赖）
	uv run pytest
