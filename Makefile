# ─────────────────────────────────────────────────────────────────────────────
# SoniScope — 唯一命令入口
#
# 所有目标都在顶层运行，用户不需要 cd 到子目录。
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: install check-config init-dirs worker-run verify-prep typecheck lint test

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
