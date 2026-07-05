# 契约漂移矩阵

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本矩阵是 Phase 2(契约抽取与漂移分析)的核心证据文档:行 = 契约要素(D-02 逐字段),列 = FC(`fc_shared`)/ Worker / 小程序(utils)三处实现(D-04 严格三列)+ 判定列。每个非 n/a 格标注状态词 + `path:line @ 5927f36` 行号证据(D-11,agree 格同样带行号);n/a 格写一句结构性理由代替行号(D-03)。全部证据出自 `git show 5927f36:<path>` / `git grep -n <pat> 5927f36 -- apps/`,禁止读工作树取证(D-05)。

## 判定标准与负面清单

### 格子状态词表

| 状态词 | 定义 |
|--------|------|
| `agree` | 该实现与其他参与实现在此契约要素上**语义一致**(字面差异不算分歧,见下) |
| `diverge` | 该实现与其他参与实现存在**语义分歧**——同样输入可产生不同的契约行为 |
| `absent` | 该实现**应参与**此契约要素但未实现(覆盖洞候选,per D-03) |
| `n/a` | **结构性不适用**——该实现在架构上不承担此要素的角色;格内写一句结构性理由代替行号(per D-03) |

**diverge 判定规则(RESEARCH Pitfall 5):** diverge 指**语义分歧**,不是字面差异。值形态不同但语义约定一致(两侧注释/文档均声明同一约定)的格标 `agree` 并在格内注明映射约定行号。典型案例:chunk_total 的小程序 manifest `null` → OSS meta `"0"` → Worker manifest `None` 三段映射。

**判定列规则(D-12):** 本阶段 02-01/02-02/02-03 一律填 `待判定`;四类标签(良性/潜伏/活跃/覆盖洞)与 F-CON-NN 链接由 02-04 回填。Postel 生产者-消费者宽严分析写入 F-CON 条目,不进矩阵。

### 负面清单(判定前置排除)

以下事项**不得**立为契约分歧(依据 `.planning/audit/DO-NOT-FIX.md` DNF-01~04 与 CHARTER 排除项表):

- **DNF-01~04 已裁定的故意设计**——包括 `issue-cedential` 域名拼写(DNF-02,阿里云分配的真实 URL)、小程序接收原始 STS 秘密下发(DNF-04)等,均不立 F-CON。
- **不引入 `docs/fc-transcribe-design.md` 目标态对照**(CHARTER 明确排除项):契约一致性以三处实现现状互相对照为准。
- chunk_total `null`↔`"0"`↔`None` 三段映射是文档化约定(`apps/miniprogram/utils/audio.js:156 @ 5927f36` 注释 + `apps/worker/src/soniscope_worker/poller.py:118 @ 5927f36` ManifestDraft docstring),不得机械判 diverge。

## 组① OSS 数据面

> D-01 组①:fragment_id、object key、全部 `x-oss-meta-*` 元数据字段。key 族六行由 02-01 Task 1 落格;元数据九行由 02-01 Task 2 落格。RESEARCH 勘察行号为起点,以下全部行号已经 `git show 5927f36:<path>` 逐一复核,以复核后实际行号为准。

| 契约要素 | FC (fc_shared) | Worker | 小程序 (utils) | 判定 |
|----------|----------------|--------|----------------|------|
| 1. fragment_id 格式正则 | agree `apps/fc/shared/fc_shared/sts.py:30-33 @ 5927f36`(`_FRAGMENT_ID_RE`,含命名捕获组) | agree `apps/worker/src/soniscope_worker/oss_admin.py:24-27 @ 5927f36`(`_FRAGMENT_ID_RE`,与 FC 逐字符相同) | agree `apps/miniprogram/utils/audio.js:95-96 @ 5927f36`(`FRAGMENT_ID_RE`,无命名捕获组但匹配语义等价) | 待判定 |
| 2. fragment_id 日期合法性校验 | agree `apps/fc/shared/fc_shared/sts.py:54-58 @ 5927f36`(正则命中后 `datetime()` 构造校验,非法抛 400 INVALID_REQUEST) | agree `apps/worker/src/soniscope_worker/oss_admin.py:45-49 @ 5927f36`(同样 `datetime.datetime()` 构造校验,非法抛 `OssAdminError`) | absent `apps/miniprogram/utils/audio.js:95-96 @ 5927f36`(正则仅 `\d{4}\d{2}\d{2}` 形状校验,匹配路径上无任何日期合法性检查;如 `20260231` 可通过) | 待判定 |
| 3. object key 模板 `recordings/<YYYY-MM-DD>/<id>.wav` | agree `apps/fc/shared/fc_shared/sts.py:46-59 @ 5927f36`(`object_key_for`,f-string 模板 :59) | agree `apps/worker/src/soniscope_worker/oss_admin.py:37-50 @ 5927f36`(`object_key_for`,f-string 模板 :50) | agree `apps/miniprogram/utils/audio.js:104-106 @ 5927f36`(`buildObjectKeyPreview`,字符串拼接 :105,`.wav` 来自 `OSS_OBJECT_KEY_EXT`) | 待判定 |
| 4. key 目录日期来源 | agree `apps/fc/shared/fc_shared/sts.py:54,59 @ 5927f36`(year/month/day 取自 fragment_id 正则捕获组前缀) | agree `apps/worker/src/soniscope_worker/oss_admin.py:45,50 @ 5927f36`(同 FC:取自 fragment_id 前缀) | diverge `apps/miniprogram/utils/audio.js:104-105,63-67 @ 5927f36`(`buildObjectKeyPreview(fragmentId, recordedAt)` 两个独立入参,日期取自 `objectKeyDate(recordedAt)` 本地时区,与 fragment_id 前缀无绑定) | 待判定 |
| 5. key → fragment_id 反推 | n/a — FC 只正向签发 object key(`object_key_for`),两个 handler 均无从 key 反推 fragment_id 的代码路径,结构上不承担反推角色 | agree `apps/worker/src/soniscope_worker/poller.py:47-61 @ 5927f36`(`fragment_id_from_key`,以 `object_key_for(fragment_id) == key` 往返校验 :57,连带保证格式、日期合法、目录日期与前缀一致) | diverge `apps/miniprogram/utils/upload_queue.js:38-44 @ 5927f36`(`fragmentIdFromObjectKey`,纯字符串切割:取最后一个 `/` 后、最后一个 `.` 前,无格式/日期/往返校验——普查发现的第四处实现) | 待判定 |
| 6. `.wav` 固定扩展名 | agree `apps/fc/shared/fc_shared/sts.py:59 @ 5927f36`(f-string 尾部硬编码 `.wav`) | agree `apps/worker/src/soniscope_worker/poller.py:53 @ 5927f36`(`key.endswith(".wav")` 过滤)+ `apps/worker/src/soniscope_worker/oss_admin.py:50 @ 5927f36`(f-string 尾部) | agree `apps/miniprogram/config.js:26 @ 5927f36`(`OSS_OBJECT_KEY_EXT = '.wav'` 常量,经 `apps/miniprogram/utils/audio.js:10 @ 5927f36` require,:105 拼接使用) | 待判定 |

### 组① key 族证据摘录

**行 1 正则逐字符对照**(FC 与 Worker 完全一致;小程序无命名捕获组、字符类与锚点等价):

- FC / Worker(`sts.py:31-32` / `oss_admin.py:25-26 @ 5927f36`):`^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})T\d{6}` + `_[A-Za-z0-9]{4,8}_[0-9A-Za-z]{26}$`
- 小程序(`audio.js:96 @ 5927f36`):`/^\d{4}\d{2}\d{2}T\d{6}_[A-Za-z0-9]{4,8}_[0-9A-Za-z]{26}$/`

**行 2 差异点**:FC(`sts.py:56 @ 5927f36`)与 Worker(`oss_admin.py:47 @ 5927f36`)在正则命中后均执行 `datetime(int(year), int(month), int(day))` 合法性校验(行内注释 `noqa: DTZ001 - 仅校验日期合法性`);小程序正则命中即通过,无后续校验——往返校验样本高价值边界(02-03 输入)。

**行 4 差异点**:小程序 `objectKeyDate`(`audio.js:63-67 @ 5927f36`)基于 `date.getFullYear()/getMonth()/getDate()` 本地时区推导 `<YYYY-MM-DD>`;`buildObjectKeyPreview`(`audio.js:104 @ 5927f36`)的 `fragmentId` 与 `recordedAt` 为两个独立入参,目录日期与 fragment_id 时间前缀之间无一致性约束;FC/Worker 则从 fragment_id 前缀单一来源推导。

## 组② 小程序↔FC HTTP 契约

*(02-02 填)*

## 组③ 两侧镜像常量

*(02-02 填)*

## 重复逻辑普查

*(02-02 填)*

## 往返校验结论

*(02-03 填)*

## 附录:往返校验样本清单

*(02-03 填)*

## 收尾:零 diff 验证与对账

*(02-04 填)*

---
*契约漂移矩阵: 2026-07-05(组① key 族 6 行已落格,判定列待 02-04 回填)*
