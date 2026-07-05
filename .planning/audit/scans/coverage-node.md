# 扫描档案:JS 覆盖率实测(worktree 专区,node 内置 experimental)

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

per D-01(分级执行口径:仅白名单命令 `node --test`,真云目标与被审脚本绝不执行)/ D-02(worktree 基线专区:实跑在仓库外基线专区 wt-5927f36 进行,主工作区零触碰;用完即拆,拆区记录见尾部)/ D-04(JS 覆盖率 = node 内置 `--experimental-test-coverage` 直跑,绕过 pytest 桥、不改桥代码,数字标注 experimental 来源,与 Python 侧同格式归档)。全部数字照抄原始输出,本档只存档不判断——本档为 AUDIT-04 的纯输入证据,判断由 04-08 完成。

**工具版本:** node v22.18.0(内置 test runner + 覆盖率旗标)

## 命令节:JS 覆盖率实测(专区根目录内执行)

```bash
cd "$WT" && node --test --experimental-test-coverage --test-coverage-exclude='apps/miniprogram/test/**' apps/miniprogram/test/*.test.js 2>&1 | tee <scratchpad>/coverage-node-raw.txt
```

**运行汇总(照抄):** tests 126 / pass 126 / fail 0 / cancelled 0 / skipped 0 / todo 0,duration_ms 60.757708。

**文件级行覆盖数字表(照抄 node experimental coverage 报告的 line % / branch % / funcs % 列):**

| file | line % | branch % | funcs % |
|------|--------|----------|---------|
| apps/miniprogram/config.js | 100.00 | 100.00 | 100.00 |
| apps/miniprogram/pages/dev/dev.js | 95.00 | 100.00 | 87.50 |
| apps/miniprogram/pages/index/index.js | 87.94 | 67.62 | 68.25 |
| apps/miniprogram/pages/uploads/uploads.js | 89.66 | 77.91 | 80.30 |
| apps/miniprogram/utils/audio.js | 97.84 | 45.45 | 100.00 |
| apps/miniprogram/utils/chunking.js | 100.00 | 76.92 | 100.00 |
| apps/miniprogram/utils/device.js | 90.00 | 78.57 | 100.00 |
| apps/miniprogram/utils/draft.js | 100.00 | 66.67 | 100.00 |
| apps/miniprogram/utils/fault_injection.js | 96.77 | 91.30 | 100.00 |
| apps/miniprogram/utils/hmac.js | 96.88 | 93.33 | 100.00 |
| apps/miniprogram/utils/logger.js | 83.33 | 86.67 | 75.00 |
| apps/miniprogram/utils/oss_sign.js | 100.00 | 55.56 | 100.00 |
| apps/miniprogram/utils/queue_runtime.js | 83.33 | 69.44 | 75.00 |
| apps/miniprogram/utils/retention.js | 96.43 | 86.67 | 100.00 |
| apps/miniprogram/utils/sha256.js | 98.25 | 91.67 | 100.00 |
| apps/miniprogram/utils/ulid.js | 92.39 | 85.71 | 100.00 |
| apps/miniprogram/utils/upload_queue.js | 99.16 | 56.67 | 100.00 |
| apps/miniprogram/utils/uploader.js | 100.00 | 88.89 | 100.00 |
| apps/miniprogram/utils/uploads_view.js | 98.68 | 85.39 | 100.00 |
| apps/miniprogram/utils/verify.js | 92.75 | 80.56 | 100.00 |
| **all files** | **92.73** | **75.80** | **84.13** |

## 口径备注

1. **experimental 标注(D-04 硬要求):** 本表全部数字来源为 node v22.18.0 的 `--experimental-test-coverage` 旗标——该覆盖率能力在 node 22 处于 **experimental** 状态,数字口径以该实现为准,引用本档时须连带此标注。
2. **pages/ 出现注记 → HYP-24(04-08/04-09 消费):** 报告中出现 `apps/miniprogram/pages/uploads/uploads.js`(以及 `pages/index/index.js`、`pages/dev/dev.js`)系 uploader.test.js 等测试经"node Page harness + mock wx"模式加载真实页面文件所致——pages 胶水层实际进入了 node 测试执行面,这是 HYP-24(pages 胶水层测试边界)的有价值证据点,登记指针 `→ HYP-24(04-08/04-09 消费)`。
3. **测试文件自身排除确认(Pitfall 4):** 报告中无任何 `*.test.js` 数据行(计 0 条),`--test-coverage-exclude='apps/miniprogram/test/**'` 控噪已生效,表内均为被测源文件。
4. **与 coverage-pytest.md 口径互不重叠(双语言证据对称):** 本档仅覆盖 node 进程内加载的 JS 文件;Python 侧数字见 `coverage-pytest.md`(pytest-cov 对 node 子进程盲,反向亦然),两档须成对引用。
5. **纯输入证据(成功判据 3):** 本档数字仅按文件罗列,不附带任何阈值判断或质量结论;uncovered lines 列不入档(原始输出留存会话 scratchpad `coverage-node-raw.txt`,不入仓),措辞约束同 coverage-pytest.md 口径备注第 3 点。

## 专区拆除记录(D-02 用完即拆)

```bash
git -C /Volumes/Data/ProjectCode/my_soniscope worktree remove --force "<scratchpad>/wt-5927f36"   # exit=0(--force 因 .venv/.pytest_cache 等未跟踪文件,Pitfall 1)
git -C /Volumes/Data/ProjectCode/my_soniscope worktree list   # 无 wt-5927f36 残留(grep 计 0 条)
git -C /Volumes/Data/ProjectCode/my_soniscope worktree prune  # 兜底,exit=0
```

**零 diff 快查(拆区后主仓执行):** `git diff --stat 5927f36 -- apps/ scripts/ docs/` 实际输出为空——PASS,覆盖率实测全程主工作区零触碰。

*JS 覆盖率实测归档: 2026-07-05(experimental 标注在档;文件数据行 20 条 = pages 3 + utils 16 + config 1,另 all files 1 行;worktree 专区已拆除无残留)*
