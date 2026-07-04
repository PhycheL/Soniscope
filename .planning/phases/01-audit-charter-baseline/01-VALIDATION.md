---
phase: 1
slug: audit-charter-baseline
status: final
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-04
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | 无需测试框架 — 纯文档阶段;验证 = shell 机械检查(仓库自有 pytest/node:test 与本阶段无关,不触碰) |
| **Config file** | none — 无 Wave 0 需求 |
| **Quick run command** | `test -z "$(git diff --stat 5927f36 -- apps/ scripts/ docs/)"` |
| **Full suite command** | 下方 Per-Task Verification Map 全部 grep/计数检查逐条执行 |
| **Estimated runtime** | ~2 秒 |

---

## Sampling Rate

- **After every task commit:** Run `test -z "$(git diff --stat 5927f36 -- apps/ scripts/ docs/)"`(零 diff quick 检查)
- **After every plan wave:** Run 全部 grep/计数检查(下表 Automated Command 列)
- **Before `/gsd-verify-work`:** 全部检查通过
- **Max feedback latency:** 5 秒

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | CHARTER-01, CHARTER-04 | T-01-01/T-01-02/T-01-03 | 秘密先例只引位置+模式名;零 diff 保持 | smoke | `test "$(grep -c '5927f362785d44b085a791ca387732991012ce5a' .planning/audit/CHARTER.md)" -eq 1 && grep -q '@ 5927f36' .planning/audit/CHARTER.md && for p in start-fc-main scripts/ralph openspec tests/audio; do grep -qF "$p" .planning/audit/CHARTER.md \|\| exit 1; done` | ❌ 本阶段产出 | ⬜ pending |
| 1-01-02 | 01 | 1 | CHARTER-02, CHARTER-03, CHARTER-05 | — | 无裁量措辞、无数值评分/小时估计 | smoke | `for s in CRITICAL HIGH MEDIUM LOW INFO; do grep -q "$s" .planning/audit/CHARTER.md \|\| exit 1; done && grep -q XL .planning/audit/CHARTER.md && ! grep -qE '[0-9]+([.][0-9]+)?[[:space:]]*小时' .planning/audit/CHARTER.md` | ❌ 本阶段产出 | ⬜ pending |
| 1-01-03 | 01 | 1 | CHARTER-05 | — | N/A | smoke | `for f in contract code toolchain docs-config test; do test -f ".planning/audit/findings/$f.md" \|\| exit 1; done && grep -q 'F-CON-00' .planning/audit/findings/contract.md` | ❌ 本阶段产出 | ⬜ pending |
| 1-02-01 | 02 | 1 | CHARTER-05 | T-01-04/T-01-05 | 秘密模式负向 grep 零命中 | smoke | `test "$(grep -c '^### DNF-' .planning/audit/DO-NOT-FIX.md)" -eq 4 && test "$(grep -c '@ 5927f36' .planning/audit/DO-NOT-FIX.md)" -ge 4` | ❌ 本阶段产出 | ⬜ pending |
| 1-02-02 | 02 | 1 | CHARTER-05 | T-01-04/T-01-06 | 1:1 转写对账等式成立;秘密模式零命中 | integration | `HYP=$(grep -c '^### HYP-' .planning/audit/HYPOTHESES.md); DNF=$(grep -c '^### DNF-' .planning/audit/DO-NOT-FIX.md); SRC=$(grep -cE '^[*][*][^*]+:[*][*]$' .planning/codebase/CONCERNS.md); test $((HYP + DNF)) -eq "$SRC"` | ❌ 本阶段产出 | ⬜ pending |
| 1-02-03 | 02 | 1 | CHARTER-05 | — | N/A | smoke | `grep -q '已解除' .planning/STATE.md` | ✅ | ⬜ pending |
| (不变量) | 01+02 | 1 | 零 diff 总规则 | T-01-02/T-01-05 | apps/、scripts/、docs/ 相对基线零改动 | smoke | `test -z "$(git diff --stat 5927f36 -- apps/ scripts/ docs/)"` | ✅ 命令已实测 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.(纯文档阶段,无测试基础设施需求;全部验证为现成 shell 命令,git 2.23.0 已实测可用。)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 章程条款可"无解释直接套用"(措辞精确性) | CHARTER-02/03 | 措辞是否留下解释空间无法机械判定 | `/gsd-verify-work` 时人工抽读严重度锚点与工作量分档,确认无需追加解释即可套用于任一 CONCERNS.md 条目 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references(无 MISSING)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-04
