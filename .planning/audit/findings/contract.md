# 发现台账: 契约一致性 (CON)

**Created:** 2026-07-04

本文件由 Phase 2 写入,ID 前缀 `F-CON-NN`;schema 以 `.planning/audit/CHARTER.md` 为准。

### F-CON-00: (schema 示例,非真实发现)

> 本条为 schema 示例,Phase 5 汇总时剔除。

- **维度:** 契约一致性 (CON)
- **严重度:** (五级之一) — 影响:(一句场景语言);可能性:(一句触发条件)
- **证据:** `path:line @ 5927f36`(占位;从 `git show 5927f36:<path>` 提取)
  > (引用片段占位)
- **修复建议:** (一段占位)
- **工作量:** (S/M/L/XL 之一)
- **关联发现:** (F-XXX-NN 或 HYP-NN,无则写"无")
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

## 发现

> 02-04 判定产物:CONTRACT-MATRIX.md 全部 12 个 diverge/absent 格(组① 行 2/4/5/13、组② 行 35-41、组③ 行 46)的四类归类与 Postel 宽严分析。F-CON-05 单条覆盖行 35-41 共 7 格(同一根因:消费端不按错误码分支)。负面清单排除的 diverge/absent 格数为 0(DNF 对照点行 14/20/21 均为 agree 格,排除注在矩阵判定列)。判定过程未撞见安全类顺带发现。

### F-CON-01: 小程序 fragment_id 校验缺日期合法性检查(FC/Worker 有,小程序无)

- **维度:** 契约一致性 (CON)
- **严重度:** LOW — 影响:前端若因缺陷构造出非法日期 fragment_id,FC 侧 400 INVALID_REQUEST 是唯一拦截点,上传显式失败进入重试/manual_retry,无静默数据丢失;可能性:小程序时间前缀由 Date 对象经 localDateParts 生成,现实路径产不出 13 月 32 日类值,仅在日期构造逻辑变更或引入外部输入时触发
- **证据:** `apps/miniprogram/utils/audio.js:95-96 @ 5927f36`(矩阵反向引用:组① 行 2「fragment_id 日期合法性校验」小程序格 absent)
  > `const FRAGMENT_ID_RE = /^\d{4}\d{2}\d{2}T\d{6}_[A-Za-z0-9]{4,8}_[0-9A-Za-z]{26}$/` — 正则仅做形状校验,匹配路径上无任何日期合法性检查。对照:FC `apps/fc/shared/fc_shared/sts.py:54-58 @ 5927f36` 与 Worker `apps/worker/src/soniscope_worker/oss_admin.py:45-49 @ 5927f36` 在正则命中后均执行 `datetime(int(year), int(month), int(day))` 合法性校验,非法即拒。
  >
  > 执行佐证(02-03 对照点 a):S-02(13 月 32 日)/S-04(非闰年 2/29)——JS `FRAGMENT_ID_RE.test → true`(双 TZ 实证),FC `FcHttpError: 400 INVALID_REQUEST: invalid fragment_id date`、Worker `OssAdminError: 非法 fragment_id 日期`。
  >
  > **Postel 宽严分析:** 生产者(小程序)宽——正则只做形状校验;消费者(FC/Worker)严——datetime 构造校验非法即拒。失配方向:宽生产者可产出严消费者必拒的 fragment_id(生产端放行、消费端 400)。触发条件:前端日期构造异常时才现实触发;当前 Date 生成链无非法日期通道,FC 400 为链路唯一拦截点。
- **修复建议:** 在 `audio.js` 的 fragment_id 校验路径(FRAGMENT_ID_RE 命中后)补日期合法性检查——以 `new Date(y, m-1, d)` 构造后回读年月日比对(JS Date 会自动进位,回读不等即非法),与 FC/Worker 的 datetime 校验语义对齐;`test/ids.test.js` 补 S-02/S-04 两个非法日期样本断言拒绝。
- **工作量:** S(单文件 `apps/miniprogram/utils/audio.js` + 既有测试文件补样本)
- **关联发现:** 关联线索: HYP-13;矩阵组① 行 2;02-03 样本 S-02/S-04(对照点 a);黄金样本配方覆盖(CONTRACT-TEST-RECIPE.md)
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-CON-02: `buildObjectKeyPreview` 双独立入参 + 本地时区日期推导,可产出目录日期≠前缀日期的 object key

- **维度:** 契约一致性 (CON)
- **严重度:** MEDIUM — 影响:若该类错位 key 成为真实上传 key,Worker `fragment_id_from_key` 往返等式不成立返回 None,轮询静默跳过——上传对 Worker 永久不可见,数据滞留 OSS 无告警(CHARTER HIGH 锚点场景);可能性:当前上传 key 采用 FC 返回值(AC#4,矩阵组② 行 25),preview key 仅用于本地预览/去重,错位 key 不进 OSS——当前链路不触发,一旦 preview 值被复用为上传 key 或对账键即爆
- **证据:** `apps/miniprogram/utils/audio.js:104-106,63-67 @ 5927f36`(矩阵反向引用:组① 行 4「key 目录日期来源」小程序格 diverge)
  > ```javascript
  > function buildObjectKeyPreview(fragmentId, recordedAt) {
  >   return 'recordings/' + objectKeyDate(recordedAt) + '/' + fragmentId + OSS_OBJECT_KEY_EXT
  > }
  > ```
  > `fragmentId` 与 `recordedAt` 为两个独立入参:目录日期取自 `objectKeyDate(recordedAt)` 本地时区(`audio.js:63-67`),与 fragment_id 时间前缀之间无一致性约束。对照:FC `sts.py:54,59 @ 5927f36` 与 Worker `oss_admin.py:45,50 @ 5927f36` 均从 fragment_id 前缀单一来源推导目录日期。
  >
  > 执行佐证(02-03 对照点 c/d):S-07 实证小程序纯函数自身可产出错位 key(fragmentId@23:59:59 + recordedAt@次日 00:00:01 → `recordings/2026-07-05/20260704T235959_….wav`,双 TZ 同果);S-18 实证 Worker 对等价错位 key 返回 `None`(`poller.py:57 @ 5927f36` 往返等式);S-06 实证同一 UTC 瞬间双 TZ 产出不同 fragment_id 与目录日期(单 TZ 进程内自洽)。
  >
  > **Postel 宽严分析:** 生产者(小程序 preview 链)宽——目录日期与前缀两个独立来源,无一致性约束;消费者(Worker)严——`poller.py:57` 往返等式要求目录日期与前缀日期一致,不一致即静默拒收(None,不入处理队列)。失配方向:宽生产者可产出严消费者静默拒收的 key,且拒收无任何告警面。触发条件:fragmentId 构造时刻与 recordedAt 跨日(近午夜)或跨时区混用双入参;当前上传链因 AC#4(object_key 用 FC 返回值)不经过 preview key,故为潜伏而非活跃。
- **修复建议:** 让 `buildObjectKeyPreview` 的目录日期从 fragmentId 时间前缀单一来源推导(与 FC/Worker 同构),移除 `recordedAt` 独立入参或仅作无 fragmentId 时的缺省;同时把「上传 key 必须使用 FC 返回的 object_key、preview 不参与上传」的 AC#4 约束以单元测试锁定,防止 preview 值未来泄漏进上传链。
- **工作量:** S(单文件 `apps/miniprogram/utils/audio.js` + 调用点与测试)
- **关联发现:** F-CON-03(同一 key 族的小程序声部分叉);关联线索: HYP-13;矩阵组① 行 4;02-03 样本 S-06/S-07/S-18(对照点 c/d);黄金样本配方覆盖
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-CON-03: key→fragment_id 第四处反推 `fragmentIdFromObjectKey` 无任何校验

- **维度:** 契约一致性 (CON)
- **严重度:** MEDIUM — 影响:非法/错位/非 .wav key 一律照单全收返回前缀子串,与 Worker `fragment_id_from_key` 对同一输入返回 None 的行为分叉——以该反推结果做列表展示/去重键时,可对 Worker 永不处理的对象呈现"正常"条目,掩盖数据滞留;可能性:当前队列内 object key 全部来自 FC 签发(合法域内),无现实触发;契约形态变更或异常 key 进入队列数据即触发
- **证据:** `apps/miniprogram/utils/upload_queue.js:38-44 @ 5927f36`(矩阵反向引用:组① 行 5「key → fragment_id 反推」小程序格 diverge)
  > ```javascript
  > function fragmentIdFromObjectKey(objectKey) {
  >   const s = String(objectKey || '')
  >   const slash = s.lastIndexOf('/')
  >   const name = slash === -1 ? s : s.slice(slash + 1)
  >   const dot = name.lastIndexOf('.')
  >   return dot === -1 ? name : name.slice(0, dot)
  > }
  > ```
  > 纯字符串切割:取最后一个 `/` 后、最后一个 `.` 前,无格式/日期/扩展名/往返校验。对照:Worker `poller.py:47-61 @ 5927f36` 的 `fragment_id_from_key` 以 `endswith(".wav")`(:53)+ 往返等式 `object_key_for(id) == key`(:57)双重校验。
  >
  > 执行佐证(02-03 对照点 b/c):S-14(`.m4a` key)与 S-18(目录≠前缀 key)——Worker 均返回 `None`,JS 第四处均照单全收返回前缀 id(双 TZ 同果)。
  >
  > **Postel 宽严分析:** 本条是同一契约的两个消费者宽严分叉——消费者甲(Worker)严:双重校验非法即 None;消费者乙(小程序第四处)宽:零校验照单全收。失配方向:同一 key 在两个消费者产生不同解析结果(None vs 前缀子串),小程序端因此可能对 Worker 视角不存在的片段维持正常状态展示。触发条件:任何非 FC 签发形态的 key 进入小程序队列数据(当前链路上 key 全部来自 FC,合法域内两消费者行为一致)。
- **修复建议:** `fragmentIdFromObjectKey` 增加与 `FRAGMENT_ID_RE` 一致的形状校验并要求 `.wav` 扩展名,非法输入返回 null 由调用方走异常分支;或按 `upload_queue.js:37 @ 5927f36` 注释既定方向("US-015 落地正式 fragment_id 后替换"),直接消费队列项已持久化的 fragmentId 字段,消除反推需求。
- **工作量:** S(单文件 `apps/miniprogram/utils/upload_queue.js` + 测试)
- **关联发现:** F-CON-02;关联线索: HYP-13;矩阵组① 行 5;D14-6(第四处重复实现债务,移交 Phase 3 CODE 维度);02-03 样本 S-14/S-18(对照点 b/c);黄金样本配方覆盖
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-CON-04: verify-upload 不校验 `x-oss-meta-sha256`,上传完整性确认只覆盖 size/etag

- **维度:** 契约一致性 (CON)
- **严重度:** LOW — 影响:同大小内容损坏的对象可通过 verify-upload 判 verified(假阳性);Worker 下载后 sha256 比对可兜底发现,但处置是删 `.part` 下轮重下——对象本体损坏时将反复重下无告警,片段处理停滞;可能性:需绕过 OSS 传输层完整性保障(HTTPS + 服务端 CRC)产生同长度内容损坏,现实概率极低,且 `head.py` docstring 自证为 tech-spec §4.2 文档化设计取舍
- **证据:** `apps/fc/shared/fc_shared/head.py:9-10,24-31 @ 5927f36`(矩阵反向引用:组① 行 13「x-oss-meta-sha256」FC 格 absent)
  > "HeadObject 只能校验对象存在性与 ``Content-Length``(无法校验 sha256,见 §4.2 注),故响应只区分「不存在 / 大小不一致 / 一致」三态。" — `ObjectHead` dataclass 仅 `exists / content_length / etag / last_modified` 四字段,HeadObject 响应可携带的 `x-oss-meta-sha256` 未被读取。
  >
  > 对照:生产端小程序上传时写入该 meta(`audio.js:168 @ 5927f36`);Worker 下载后执行 sha256 比对(`poller.py:272-283 @ 5927f36`,不一致删 `.part` 重下)。
  >
  > **Postel 宽严分析:** 生产者(小程序)严——主动提供完整性信息(sha256 meta);消费者(FC verify-upload)宽——丢弃该信息,只校验 size/etag。失配方向:生产者提供的完整性凭据被链路中段消费者忽略,完整性闭环被推迟到 Worker 下载后,而 verify-upload 的"verified"语义因此弱于其字面承诺(仅 size 一致)。触发条件:对象内容与 sha256 不符但 Content-Length 一致时,verify-upload 返回假阳性 verified。
- **修复建议:** 若修复里程碑要闭环:verify-upload 请求增加 `expected_sha256` 字段,`verify_upload_result` 读取 HeadObject 返回的 `x-oss-meta-sha256` 比对,不符返回新 reason(如 `SHA256_MISMATCH`)——需同步 FC(head.py/handler)与小程序(verify.js/queue_runtime.js)两处,跨组件属 L;若维持 §4.2 取舍(可辩护:OSS 传输层已有完整性保障),建议至少在 Worker 的 sha256 失配重下路径加失败计数与告警日志,消除"反复重下无告警"的停滞盲区(M,Worker 单组件多文件)。
- **工作量:** L(闭环方案跨 FC + 小程序;保守告警方案 M)
- **关联发现:** 关联线索: HYP-13;HYP-03(sha256 跨语言双实现关联线索,D14-1 移交 Phase 3);矩阵组① 行 13
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-CON-05: 7 个 FC 错误码字面量在小程序实现代码零出现,统一经 `body.error` 通用透传

- **维度:** 契约一致性 (CON)
- **严重度:** INFO — 影响:小程序按 statusCode 段分支(200 / ≥500 / 其余 4xx),每个错误码的客户端行为等同(透传展示码值),当前输入域内无任何行为分叉;可能性:仅当未来需要按码差异化处置(如 SIZE_EXCEEDED 提示压缩、INVALID_CODE 强制重登录)时该缺席才显性化
- **证据:** `apps/miniprogram/utils/uploader.js:32-50 @ 5927f36`(矩阵反向引用:组② 行 35-41「7 个错误码字符串」小程序格 absent ×7——本条单条覆盖 7 格,同一根因)
  > ```javascript
  > // FC 用 body.error 返回稳定错误码(INVALID_CODE / OPENID_NOT_ALLOWED / SIZE_EXCEEDED 等)。
  > const errorCode = data.error ? String(data.error) : 'HTTP_' + Number(statusCode || 0)
  > return { ok: false, errorCode: errorCode }
  > ```
  > `classifyFcResponse` 按 `statusCode === 200` 与否二分(:34),`classifyVerifyResponse`(`verify.js:28-51 @ 5927f36`)按 200/≥500/其余 4xx 三段;7 个错误码字面量(定义端 `errors.py:13-19 @ 5927f36`)在小程序实现代码零出现(`uploader.js:47` 为注释非代码)。
  >
  > **Postel 宽严分析:** 生产者(FC)严——稳定错误码 + 固定 `error` 字段包络(`errors.py:38 @ 5927f36`);消费者(小程序)宽——只读 `error` 一个键并透传,不识别具体码值。失配方向:无行为失配——宽消费者对全部码等同处理恰是 Postel「宽收」的容错姿态,FC 新增/更名错误码不会破坏客户端。触发条件:无(当前域内行为无分叉),故归类良性而非覆盖洞:错误码契约对客户端是"可用信息"而非"必须分支的义务",通用透传已满足展示与日志需求。
- **修复建议:** 无需修复即可上线。若修复里程碑引入按码交互(重登录/压缩提示等),建议以 `fc_shared/errors.py` 为单一真值源同步生成 JS 常量,避免第四份字面量漂移;注意 CLAUDE.md 声称的"uploader.js branches on the same strings"与实态不符,已作为 Phase 4 DOC 维度移交线索(矩阵组② 行 35-41 行下注)。
- **工作量:** S(如需引入按码分支:uploader.js/verify.js 常量与分支 + 测试)
- **关联发现:** 关联线索: HYP-13;Phase 4 DOC 移交(CLAUDE.md 错误码分支声明失实);D14-3(联调工具第二份错误码字面定义,移交 Phase 3)
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft

### F-CON-06: 上传大小上限 50 MB 无小程序侧镜像常量或上传前预检

- **维度:** 契约一致性 (CON)
- **严重度:** LOW — 影响:超限文件在 issue-credential 即被 400 SIZE_EXCEEDED 显式拒绝(4xx 立即失败,不重试),用户可见但手动重试永不成功,manual_retry 循环空耗操作;失败面显式非静默;可能性:600 s 分片阈值下小程序常见录音码率难以逼近 50 MB,录音格式/码率/分片阈值任一变更后单片段逼近上限即触发
- **证据:** `apps/fc/shared/fc_shared/env.py:41 @ 5927f36` + `sts.py:91-99 @ 5927f36`(矩阵反向引用:组③ 行 46「上传大小上限 50 MB」小程序格 absent)
  > `DEFAULT_MAX_UPLOAD_BYTES = 52428800`(可被 env `MAX_UPLOAD_BYTES` 覆盖);`check_size` 超限抛 400 SIZE_EXCEEDED(附 limit_bytes/actual_bytes)。小程序侧 grep 裁决(矩阵行 46 行下注):`git grep -nE '52428800|MAX_UPLOAD' 5927f36 -- apps/miniprogram/` 零大小预检常量命中——上限语义仅经 SIZE_EXCEEDED 错误码事后感知,而该码在小程序又无分支消费(F-CON-05)。
  >
  > **Postel 宽严分析:** 消费者(FC)严——`check_size` 硬上限 400 拒绝;生产者(小程序)宽——无预检,任意大小先发起签发请求。失配方向:宽生产者可产出严消费者必拒的请求,拒绝发生在链路中段而非源头,用户得不到"文件过大"的可行动提示。触发条件:单片段 `size_bytes > MAX_UPLOAD_BYTES`(默认 52428800)。同类边界:组② 行 18/28 的 `size=0` 回退(`uploader.js:63 @ 5927f36` / `verify.js:59-60 @ 5927f36` 的 `|| 0`)与 FC `parse_size` 的 `size <= 0 → 400 INVALID_REQUEST`(`sts.py:86-87 @ 5927f36`)构成同方向宽严失配——manifest 缺失时生产者发出消费者必拒的值(该两行为 agree 格,Postel 注记并入本条)。
- **修复建议:** 小程序 `config.js` 增加 `MAX_UPLOAD_BYTES` 镜像常量(与 FC 默认值一致,注明 FC env 可覆盖的语义与同步义务),`uploadFragment` 在 requestSts 前预检 `size_bytes`,超限给出明确不可重试文案;顺带收紧 `size=0` 回退——manifest 缺失时直接置 upload_failed 而非发出必拒请求。
- **工作量:** S(config.js + uploader.js/verify.js 预检 + 测试)
- **关联发现:** F-CON-05(超限时用户感知依赖错误码透传);关联线索: HYP-13;矩阵组③ 行 46、组② 行 18/28 size=0 边界注记
- **上线判定:** (Phase 5 填,留空)
- **状态:** draft
