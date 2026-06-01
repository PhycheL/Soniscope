# ─────────────────────────────────────────────────────────────────────────────
# SoniScope — 唯一命令入口
#
# 所有目标都在顶层运行，用户不需要 cd 到子目录。
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: install check-config init-dirs worker-run typecheck lint test

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

# ── 质量门 ──────────────────────────────────────────────────────────────────

typecheck:
	uv run --directory apps/worker mypy --strict src/

lint:
	uv run --directory apps/worker ruff check src/

test:
	uv run --directory apps/worker pytest -v
