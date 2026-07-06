# Roadmap: SoniScope

## Milestones

- ✅ **v1.0 上线前审计** — Phases 1-5, shipped 2026-07-06. 归档: [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md); requirements: [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md); audit: [v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md).
- ◆ **v1.1 上线前修复** — Phases 6-8, planned 2026-07-06. Scope: PRE-LAUNCH findings `F-CODE-02`、`F-CODE-06`、`F-DOC-03`.

## Phases

<details>
<summary>✅ v1.0 上线前审计 (Phases 1-5) — SHIPPED 2026-07-06</summary>

- [x] Phase 1: 审计章程与基线 (2/2 plans) — completed 2026-07-04
- [x] Phase 2: 契约抽取与漂移分析 (4/4 plans) — completed 2026-07-05
- [x] Phase 3: 组件与工具链深潜 (7/7 plans) — completed 2026-07-05
- [x] Phase 4: 文档配置与测试审计 (9/9 plans) — completed 2026-07-05
- [x] Phase 5: 汇总校准与报告组装 (3/3 plans) — completed 2026-07-05

</details>

<details open>
<summary>◆ v1.1 上线前修复 (Phases 6-8) — PLANNED</summary>

- [ ] Phase 6: Worker 失败路径隔离与告警 — covers WKR-01/WKR-02/WKR-03 (`F-CODE-02`)
- [ ] Phase 7: 小程序 uploading 死态恢复 — covers MP-01/MP-02/MP-03 (`F-CODE-06`)
- [ ] Phase 8: 发布 production ENV 清单 — covers DOC-01/DOC-02 (`F-DOC-03`)

</details>

## Phase Details

### Phase 6: Worker 失败路径隔离与告警

**Goal:** 持久失败对象不再造成每轮重下重处理,并能被操作者明确发现和处理。

**Requirements:** WKR-01, WKR-02, WKR-03

**Success criteria:**

1. `sha256_mismatch`、探测失败、标准化失败均会记录按 fragment 的失败历史。
2. 达到阈值后,同一 OSS object 在后续轮询中被跳过或隔离,不会继续无界下载。
3. 告警/诊断输出包含 `fragment_id`、原因、attempt count 和下一步处理建议。
4. pytest 覆盖多轮失败、阈值隔离、告警/诊断状态与既有成功路径幂等跳过。

### Phase 7: 小程序 uploading 死态恢复

**Goal:** 中断残留的 `uploading` 录音不再卡死,自动驱动或用户手动操作都能把它带回可恢复路径。

**Requirements:** MP-01, MP-02, MP-03

**Success criteria:**

1. 启动/onShow 驱动前 stale `uploading` 项会被识别并复位到 `queued` 或 `manual_retry` 等可处理状态。
2. 上传列表把 stale `uploading` 项纳入积压提示或手动恢复集合,用户不需要删除记录自救。
3. `queue_runtime` 与 uploads 页同构路径保持行为一致。
4. node 测试覆盖 stale `uploading` 恢复,并同步更新 `uploads_view.test.js` 中现行死态断言。

### Phase 8: 发布 production ENV 清单

**Goal:** 发布文档不再依赖记忆翻转 ENV,照文档发布不会把开发者菜单与故障注入带给最终用户。

**Requirements:** DOC-01, DOC-02

**Success criteria:**

1. `docs/runbook/deployment-guide.md` 小程序发布步骤在上传前明确要求 `ENV=production`。
2. 发布清单包含真机确认开发者菜单不可见、故障注入不可用。
3. 文档保留 `issue-cedential` 真实 URL 拼写,不误改 DNF-02。
4. 文档检查可通过 `rg "ENV|production|开发者菜单|故障注入" docs/runbook/deployment-guide.md` 找到发布前强制项。

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. 审计章程与基线 | v1.0 | 2/2 | Complete | 2026-07-04 |
| 2. 契约抽取与漂移分析 | v1.0 | 4/4 | Complete | 2026-07-05 |
| 3. 组件与工具链深潜 | v1.0 | 7/7 | Complete | 2026-07-05 |
| 4. 文档配置与测试审计 | v1.0 | 9/9 | Complete | 2026-07-05 |
| 5. 汇总校准与报告组装 | v1.0 | 3/3 | Complete | 2026-07-05 |
| 6. Worker 失败路径隔离与告警 | v1.1 | 0/0 | Planned | — |
| 7. 小程序 uploading 死态恢复 | v1.1 | 0/0 | Planned | — |
| 8. 发布 production ENV 清单 | v1.1 | 0/0 | Planned | — |

## Next

**Phase 6: Worker 失败路径隔离与告警** — 关闭 `F-CODE-02`,让持久失败对象有计数、隔离和告警。

`$gsd-discuss-phase 6` — gather context and clarify approach

Also: `$gsd-plan-phase 6` — skip discussion, plan directly
