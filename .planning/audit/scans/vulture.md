# 扫描档案:vulture 死代码扫描

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

per D-05(临时扩展分析器,uvx 临时获取零仓库写入)/ D-07(命令+版本+输出存档)。扫描对象为基线导出副本(导出路径见 COVERAGE.md 头部备注,`git archive 5927f36 apps scripts` 产物,结构性免疫工作树);输出中的导出前缀已统一改写为仓库相对路径,便于 `path:line @ 5927f36` 引用。包合法性已经 03-01 Task 2 人工批准(03-RESEARCH.md §Package Legitimacy Audit)。

**工具版本:** vulture 2.16(经 `uvx vulture --version` 实测;uvx 由 uv 0.8.14 提供)

## 扫描:worker src + fc 全量,置信度 ≥80

```bash
# $EXPORT = scratchpad 基线导出根(仓库外)
uvx vulture "$EXPORT/apps/worker/src" "$EXPORT/apps/fc" --min-confidence 80
```

**命中计数:1**(exit=3,vulture 约定:发现死代码时退出码非零)

```
apps/worker/src/soniscope_worker/miniprogram_lint.py:121: unused variable 'rel_path' (100% confidence)
```

**已知误报类预记(销号时备查,RESEARCH A1):** Protocol 实现方法、typer 回调、WSGI 入口等动态引用属 vulture 已知误报类——本次 `--min-confidence 80` 下均未出现,唯一命中为 100% 置信度未使用变量,仍须人工核实后销号(命中 ≠ 发现)。

## 三态销号表(03-02 填)

核实方法:命中经 `git show 5927f36:apps/worker/src/soniscope_worker/miniprogram_lint.py` 提取 115-140 行上下文并检索全部调用点后人工判断。

| # | 命中(path:line @ 5927f36) | 规则/模式 | 销号 | 理由/去向 |
|---|---------------------------|-----------|------|-----------|
| 1 | apps/worker/src/soniscope_worker/miniprogram_lint.py:121 | unused variable 'rel_path'(100% confidence) | 确认 | scan_hardcoded_secrets 声明 rel_path 形参却未使用,调用方(:190)传入 str(file) 落空——非 Protocol/typer/WSGI 动态引用误报类(RESEARCH A1 预记核对不符合),系真实未使用参数,与 ruff 扩展集 ARG001 同点命中互证 → 深挖线索(03-05 miniprogram_lint 普审,HYP-15) |

**对账等式:** 确认 1 + 误报 0 + 移交 0 = 命中总数 1 ✓

**移交说明:** 本档无移交项。
