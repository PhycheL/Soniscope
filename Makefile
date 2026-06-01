# ─────────────────────────────────────────────────────────────────────────────
# SoniScope — 唯一命令入口
#
# 所有目标都在顶层运行，用户不需要 cd 到子目录。
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: install check-config init-dirs worker-run verify-prep typecheck lint test \
        deploy-fc rollback-fc fc-logs test-fc-live test-verify-upload \
        oss-delete-obj miniprogram-lint show-oss-object test-sts-escape

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
	@cd apps/miniprogram && node -c app.js && node -c utils/constants.js && node -c utils/logger.js && node -c utils/crypto.js && node -c utils/idgen.js && node -c utils/uploader.js && node -c utils/cleanup.js && node -c pages/index/index.js && node -c pages/upload-list/upload-list.js
	@echo "==> Miniprogram JS syntax OK"

# ── OSS 运维辅助 ──────────────────────────────────────────────────

show-oss-object:
	uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/show_oss_object.py" $(FRAGMENT_ID)

test-sts-escape:
	@echo "🧪 STS 越权验证"
	@echo "需要 STS 临时凭证（access_key_id / access_key_secret / security_token / object_key）"
	uv run --directory apps/worker --extra dev python "$(CURDIR)/scripts/test_sts_escape.py" $(STS_AK_ID) $(STS_AK_SECRET) $(STS_TOKEN) $(STS_OBJECT_KEY)
