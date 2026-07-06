# 阿里云 OSS / FC 3.0 / RAM 使用经验手册

> 提炼自 SoniScope 项目对阿里云 OSS/FC/RAM 的实际使用,整理日期 2026-07-06。本文是面向未来项目的经验手册(playbook),按"决策 / 模式 / 踩坑"组织;文中的 SoniScope 文件路径与数字均为案例引用(格式 `path:line`),可在该仓库中独立复核。

## 一、引言

**经验来源。** SoniScope 是一条个人级录音转写流水线:WeChat 小程序录音直传 OSS(STS 临时凭证)→ Aliyun FC 3.0 函数做唯一可信网关(签发单 object key STS、校验上传)→ OSS 私有桶作为唯一数据契约 → 本地 Python Worker 轮询下载、ffmpeg 标准化、NLS 云端 ASR 转写。项目从零把这套架构跑到了部署上线阶段,期间在 OSS、FC 3.0、RAM/STS 三个服务上积累了大量决策、可复用模式与真金白银换来的踩坑记录。

**适用范围。** 本手册假定的读者是"下一个要用阿里云 OSS/FC/RAM 的项目",且满足:

- 个人或小团队规模,按量付费,不追求企业级多账号治理;
- 技术栈为 Python(服务端/Worker)+ 微信小程序 JS(客户端)双栈,或其中之一;
- 需要"客户端直传对象存储 + 无服务器函数做轻网关"这类经典组合。

**阅读方式。** 第二部分是贯穿三个服务的通用模式(先读);三、四、五部分分别是 OSS、FC 3.0、RAM/STS 的专篇;第六部分是跨领域踩坑速查表(排障时先查这里);第七部分是可直接搬运的资产索引。

## 二、总纲:贯穿三个服务的通用模式

### 2.1 纯逻辑 + Protocol 注入 + lazy import(最值得复用的顶层模式)

全仓一致的三层分法:

1. **纯逻辑函数零 IO**(key 推导、policy 构造、元数据映射、签名计算),直接被 mypy strict + pytest / node --test 覆盖;
2. **云调用收敛到 Protocol 接口**(`OssSource` / `StsIssuer` / `FcApi` / `NlsBackend`),单测注入 Fake 实现(如内存 dict 的 `FakeSource`,带调用计数与可注入错误),全程不触网;
3. **Real 实现 lazy import 云 SDK**,使"无凭证 / 无 SDK"的 CI 环境优雅 SKIP(真实入口缺 config/SDK/凭证时 exit 0 + SKIP 文案,CI 不红)。

案例:OSS 侧 `poller.py`(`OssSource`/`RealOssSource`);部署侧 `fc_deploy.py:6-14,106-119`(`FcApi` Protocol,单测注入 `FakeFcApi`);STS 侧 `sts.py:117-176`(`StsIssuer` Protocol + `get_issuer()`,单测 monkeypatch 注入假实现)。小程序 JS 侧是同一模式的镜像:所有 wx API(`wx.login`/`wx.request`/`wx.uploadFile`/定时器)经 `deps` 对象注入,纯函数可在 node 单测里跑。

这个模式对阿里云尤其重要:阿里云 Python SDK 家族(`alibabacloud_*` / `aliyunsdkcore`)体积大、版本行为差异多、部分无类型标注——lazy import + `ignore_missing_imports` 让它们完全不进入类型检查与单测路径。

### 2.2 runbook 是真实云资源的单一真实来源

控制台里点出来的资源(bucket 名、region、函数 URL、RAM 账号/角色、环境变量清单、运行规格)必须落成 runbook 文档,并明确文档权威链(产品 PRD → 技术 spec → runbook → agent 约定)。代码中的真实云常量以 runbook 为准,而不是反过来——**阿里云分配的值(哪怕拼写错误)是 canonical 的**,详见 §4.7 的 `issue-cedential` 案例。

### 2.3 最小权限:一职能一子账号 + 两级收窄

原则:每个"职能"一个 RAM 子账号,权限边界互不重叠;临时凭证走"角色策略限前缀、AssumeRole 会话 policy 收到单资源"的两级收窄。部署账号与运行时账号绝不复用。完整切分表与 policy 模板见第五部分。

### 2.4 防御性脱敏:黑名单 + 子串兜底,比"约定不打印"可靠

秘密防泄漏不能靠"大家约定不打印",要在出口处结构性拦截。SoniScope 的四道防线:

1. **`MaskedSecret(SecretStr)`**(Pydantic v2):配置里所有密钥的类型;>8 字符只显示前后 4 位,≤8 全打码,覆写 `_display`;明文只能显式 `.get_secret_value()` 取出。`config.py:22-48`。本手册后文各处提到"密钥经 MaskedSecret"均指此实现,不再重复展开。
2. **结构化日志自动脱敏**:`log_event(event, **fields)` 渲染 `event=... k=v` 单行(字段按名排序、None 省略、`print(flush=True)` 供 FC stdout 采集);脱敏双保险 = 显式敏感字段名集合 + 子串兜底(`secret/token/appkey/api_key/session_key/password`),字段名先归一化(小写、`-`→`_`)。openid 只记 sha256 前 16 位(`hash_openid`)。`audit.py:14-45,48-62,35-37`。
3. **备份只记名不记值**:部署前备份线上函数时,环境变量只写排序后的**变量名**清单(`<name>.env-names.txt`),绝不写值。`fc_deploy.py:359-371`。
4. **静态扫描兜底**:对客户端源码全量扫描硬编码长期 AK(阿里云长期 AK ID 均以 `LTAI` 开头,正则 `\bLTAI[0-9A-Za-z]{6,}\b`)与密钥赋值字面量,测试夹具目录豁免。`miniprogram_lint.py:42-46,121-128,187-191`。

配套测试纪律:单测断言 repr/summary 输出中不含明文密钥;live 测试断言"拒绝响应不含任何凭证字段"(见 §5.5)。

## 三、OSS 篇

### 3.1 Python SDK(alibabacloud-oss-v2)client 构造

可直接复用的构造代码(`verify_prep.py:632-651`):

```python
import alibabacloud_oss_v2 as oss

cfg = oss.config.load_default()
cfg.credentials_provider = oss.credentials.StaticCredentialsProvider(
    access_key_id=ak_id, access_key_secret=ak_secret)  # STS 凭证时多传 security_token
cfg.region = "cn-beijing"
cfg.endpoint = endpoint
client = oss.Client(cfg)
```

两个坑:

- **region 与 endpoint 都要设**,只设其一在不同 SDK 版本下行为不一致;
- **`get_bucket_info` 返回的 region 带 `oss-` 前缀**(如 `oss-cn-beijing`),与配置里的裸 region(`cn-beijing`)比对前需 `.replace("oss-", "")` 归一化。

### 3.2 API 清单与分页 list

常用请求对象:`ListObjectsV2Request`(分页列举)、`HeadObjectRequest`(存在性/大小)、`GetObjectRequest + get_object_to_file`(下载)、`GetObjectRequest + presign(expires=timedelta)`(签名 URL)、`GetBucketInfoRequest`(校验 bucket/region/ACL);`PutObjectRequest`/`DeleteObjectRequest` 仅测试代码使用。

**分页 list 是易漏点**(`poller.py:417-438`):`while True` + `continuation_token` 循环,直到 `is_truncated` 为 False;**token 为空也 break(双保险)**,防 SDK 字段缺失导致死循环;响应字段访问全部用 `getattr(obj, "key", "")` 防御式取值,不假定 SDK 版本间字段齐全。

### 3.3 presign 签名 URL 与自动续签("长任务 + 短时效签名 URL"模式)

场景:给 NLS 这类异步云服务递交一个 presign URL 让它自行拉取音频。presign 有效期 3600s,但 NLS 异步排队,轮询可能超时——SoniScope 的做法是设 `RESIGN_THRESHOLD_SECONDS`:轮询超过 **50 分钟**就重新签发 URL 并**重新提交任务**(仅换 URL 不够,任务里存的是旧 URL),否则 NLS 拉取时 URL 已过期。`nls.py:49-50,314-326,409-435`。

任何"把签名 URL 交给第三方异步消费"的场景都要预设这个续签+重提循环。

附 NLS 联动经验:两种 upload_mode——`oss-url`(首选,presign 让 NLS 自行拉取)/`direct`(降级,本地直传 FlashRecognizer);filetrans 提交参数 `version:"4.0"`、`enable_words:False`、`enable_sample_rate_adaptive:True`;**NLS Token 服务仅在 `cn-shanghai`**,与 OSS 所在 region(本项目 cn-beijing)不同,极易配错(见 §6 总表)。

### 3.4 错误码提取:多路兜底(跨 SDK 版本防御)

阿里云 SDK 各版本异常对象的错误码字段名不统一。可靠做法(`head.py:79-93,127-130`):

- 遍历多候选属性:`code / error_code / Code / status_code / StatusCode`;
- 递归 `unwrap()` 内层异常;
- 都取不到时退化为异常文本字符串匹配。

**HeadObject 对象不存在时 SDK 抛异常而非返回空**——必须 catch 后判 `NoSuchKey / NoSuchObject / 404` 才能区分"对象不存在"与"真错误"。

### 3.5 小程序端 V4 签名 PostObject 直传(最难复用,重点)

微信小程序无 `crypto`、无 `btoa`,且 `wx.uploadFile` 只能发 POST multipart——所以直传 OSS 只能走 **PostObject 协议 + OSS4-HMAC-SHA256 表单签名**,全部签名逻辑用纯函数实现、注入 `now` 可确定性单测。

完整 6 步(`oss_sign.js`):

1. **时间戳全 UTC**:`YYYYMMDD`(date)/ `YYYYMMDDTHHMMSSZ`(ISO8601 basic)/ policy expiration 用 RFC3339 且毫秒置 0。
2. **credential 字符串**:`accessKeyId/date/region/oss/aliyun_v4_request`。
3. **派生签名密钥 HMAC 链**:`HMAC('aliyun_v4'+secret, date) → HMAC(·, region) → HMAC(·, 'oss') → HMAC(·, 'aliyun_v4_request')`。
4. **policy conditions 逐项列全**:bucket、`['eq','$key',objectKey]`(精确等于服务端返回的 key)、`x-oss-signature-version`、`x-oss-credential`、`x-oss-date`、`x-oss-security-token`、`success_action_status:'200'`、以及**全部 `x-oss-meta-*` 元数据逐条加入**(防篡改)。
5. **签名对象是 base64 后的 policy**:`signature = HMAC_hex(signingKey, base64(JSON.stringify(policy)))`——签 base64 串,不是 JSON 原文。
6. **formData 字段清单**:`key / policy / x-oss-signature-version / x-oss-credential / x-oss-date / x-oss-security-token / x-oss-signature / success_action_status` + 全部元数据字段,直接喂 `wx.uploadFile`。

**密码学原语纯 JS 自实现**(`hmac.js` + `sha256.js`):HMAC(key 超 64 字节先哈希、ipad/opad 0x36/0x5c)+ 手写 base64;可在 node 单测里对照 `node:crypto` 跑校验向量。整套可原样搬运到任何无 crypto 环境的 JS 运行时。

**上传编排**(`uploader.js`):OSS 非 2xx / 网络错误按 5s→15s→45s 退避重试最多 3 次,耗尽转 `OSS_UPLOAD_FAILED` 人工处理;凭证使用侧的安全细节(security_token 三处出现、object_key 必须用服务端返回值)见 §5.4。

### 3.6 数据契约:object key 与 x-oss-meta-*

当 OSS 对象是多端之间的**唯一数据契约**时,契约细节值得工程化对待:

- **object key 规则集中且可往返校验**。本项目 key 规则 `recordings/<YYYY-MM-DD>/<fragment_id>.wav` 在 4 处独立实现(FC 签发端 `sts.py`、Worker 运维端 `oss_admin.py`、小程序预览端 `audio.js`、Worker 反推端 `poller.py`),正则完全一致,跨语言必须保持同步——这是刻意重复(跨包不共享代码),靠 spec 文档做规格锚点。
- **round-trip 校验模式(值得复用)**:反向解析 `fragment_id_from_key` 先切出 id,再用正向构造 `object_key_for(id) == key` 做往返校验——一次正向构造覆盖所有反向校验(格式、日期合法性、目录一致性);非法 key 归入 ignored_keys 不阻塞轮询。`poller.py:47-66`。
- **`x-oss-meta-*` 元数据 7 字段契约**:session-id / chunk-seq / chunk-total / recorded-at / duration / original-format / sha256,写入时全部 `String()` 化。
- **踩坑(null↔"0" 映射)**:非分片录音的 chunk_total 在客户端 manifest 里是 null,写 OSS meta 时映射为 `"0"`,Worker 读回把 `<=0` 映射回 None——跨系统契约中 null 语义的显式映射必须双向写清楚,否则两端各自"合理默认"就漂移了。
- **读回容错**:`normalize_metadata` 去 `x-oss-meta-` 前缀 + 小写归一(兼容 SDK 已去前缀/未去前缀两种形态);数值解析用容错的 `_as_int/_as_float`(失败返回 None 不抛异常)。

### 3.7 结构性防删除(把"不能删"变成可测试的约束)

"业务代码绝不删 OSS 对象"这类红线,靠 code review 记不住,要结构化:

1. **Protocol 只暴露 list/head/download**,接口层面排除删除能力;单测用 `hasattr` 断言 Real 实现没有 delete 方法——红线变成会红的测试。`poller.py:215-231`、`test_poller.py:425-426`。
2. **删除能力只存在于独立运维模块**(仅测试用途),且三重门禁:警告提示 + 必须 `--yes` 或环境变量 `SONISCOPE_ALLOW_OSS_DELETE=1` 显式确认。
3. **静态扫描兜底**:retention 校验命令静态扫描源码,只匹配**真实调用形态**(`.delete_object(` / `DeleteObjectRequest`),避免把 docstring 里"绝不调用 DeleteObject"的说明文字误判违规;白名单豁免仅限测试模块;日志扫描用宽松 token。`ops.py:39-55,223-237`。

### 3.8 配置与成本(花钱买来的数字)

- Bucket 私有 ACL;公网 endpoint `oss-cn-beijing.aliyuncs.com`,内网 `oss-cn-beijing-internal.aliyuncs.com`。
- 小程序 `wx.uploadFile` 的目标域名必须加入小程序后台合法域名白名单(如 `https://<bucket>.oss-cn-beijing.aliyuncs.com`)。
- 测试音频不进 git:存 OSS `sample/` 前缀,本地脚本按需拉取。
- **成本**:OSS 标准存储约 **0.12 元/GB/月**(1.6GB≈0.19 元/月);上传流入免费;**同地域内网下载免费**(跨 region 或走公网收费)——因此 **OSS / FC / Worker(计算侧)的 region 必须一致**,这是省钱也是架构约束;NLS ASR 约 **2.5 元/小时,无免费额度**——转写量是这套流水线的主要成本项,幂等性设计(避免重复转写)直接省钱。

## 四、FC 3.0 篇

### 4.1 FC 3.0 无 service 层:两个直接影响

FC 3.0 取消了 2.0 的服务(service)层级,函数是顶级实体:

- **URL 形态变化**:从 2.0 的 `/2016-08-15/proxy/<svc>/<fn>/` 变为 `https://<url-id>.<region>.fcapp.run/`,每函数一个独立子域名;
- **没有服务级共享环境变量**:多个函数共享的配置(本项目两函数共 10 个环境变量)必须**每个函数各填一遍**,控制台改配置时两边都要改。`docs/runbook/cloud-setup.md:60-62`、`docs/runbook/fc-deploy.md:299`。

### 4.2 Custom Runtime + 约 35 行零依赖 WSGI 适配层

选择 Custom Runtime + Web 函数,启动命令 `python3 app.py`,**部署包根目录必须含 `app.py`**。适配层全部用 stdlib(`apps/fc/shared/app.py`,约 35 行):

- `ThreadingWSGIServer(ThreadingMixIn, WSGIServer)` + `daemon_threads = True`,用 `wsgiref.simple_server.make_server`(`app.py:17-18,29`);
- **端口 fallback 链**:`FC_SERVER_PORT` → `PORT` → `9000`(`app.py:21-23`);
- 监听 `0.0.0.0`,`serve_forever()`,启动打印带 `flush=True`(FC 经 stdout 采集日志)(`app.py:27-31`);
- 请求委派给函数本地的 `handler.handler`(`from handler import handler as application`,`app.py:14`)。

**GET 作存活探针**:handler 里 `method != "POST"` 直接返回 `200 {"function":..., "status":"ok"}`,供部署后 curl 验活;业务只走 POST。`issue_credential/handler.py:36-40`。

个人级项目用这套 stdlib 方案代替 Flask/FastAPI 的收益:部署包里零 web 框架依赖、冷启动轻、没有框架版本维护负担。

### 4.3 共享库 vendor 进 zip,而非 pip 安装

FC 没有便捷的跨函数共享层(Layer),多函数共享代码的实用解法:**部署打包时把共享包整棵复制进每个函数 zip 的根目录**(`SHARED_PARENT=("apps","fc","shared")`,`_vendor_shared()` 复制 `fc_shared` 树,部署后可直接 `import fc_shared`)。`fc_deploy.py:48-50,197-204`。`app.py` 同样复制进包根,缺失即报错。`fc_deploy.py:207-212`。

函数组织:每函数一目录(`handler.py` + `requirements.txt`),依赖极简、按函数拆分(签发函数只装 STS SDK,校验函数只装 OSS SDK)。共享包按域分模块(`auth / env / audit / errors / http / sts / head / wechat`),`__init__.py` 统一 re-export。

**衍生坑**:多个函数的入口都叫 `handler.py`(约定统一)→ mypy 模块名冲突 → 解法是 handler.py 只受 ruff 检查、排除出 mypy,而把全部实质逻辑放进 mypy strict 覆盖的共享包,handler 只留薄薄的编排层。`pyproject.toml:30-32,50`。

### 4.4 部署工程化(备份→打包→更新→验活→回滚全流程)

值得整套照抄的部署脚本设计(`fc_deploy.py`,云 IO 收敛到 `FcApi` Protocol,见 §2.1):

- **打包(`package_function`)**:清空 staging → 复制源码(排除 `__pycache__`/`.pyc`)→ vendor 共享包 → 复制 app.py → 读 requirements.txt 用 `uv pip install --target <staging>` 把依赖装进包内 → **确定性 zip(按路径排序)+ sha256**(可比对两次构建是否一致)。`fc_deploy.py:157-233,640-657`。
- **管理 SDK(`alibabacloud-fc20230330`,lazy import,只进部署工具、绝不打进函数包)**:endpoint 拼接 `f"{ACCOUNT_ID}.{REGION}.fc.aliyuncs.com"`(`fc_deploy.py:599-601`);备份用 `get_function_code` 拿 URL 再 `urllib` 下载(`fc_deploy.py:603-623`);**只更新代码**——`update_function` 只传 `InputCodeLocation(zip_file=base64...)`,不碰环境变量/触发器/运行规格,函数创建与触发器配置留给一次性人工准备(`fc_deploy.py:659-674`);缺 SDK 抛错并给安装指引(`fc_deploy.py:593-598`)。
- **备份**:部署前下载线上代码 zip + 环境变量名清单(只记名不记值,见 §2.4);"备份跳过"只有首次部署(线上无代码)才允许,线上已有代码时备份失败要警惕。`fc_deploy.py:382-384`。
- **编排(`deploy_one`)**:备份(best-effort)→ 打包 → update_code → curl 验活,**验活只认 HTTP 2xx**。`fc_deploy.py:374-415`。
- **回滚**:备份按时间戳目录存放,`find_latest_backup` 取最新 zip → `update_code` 恢复。`fc_deploy.py:236-247,418-453`。
- **部署凭证注入**:`ALIYUN_DEPLOY_AK_ID/SECRET` 从仓库根 `.env` 读取(支持 `export ` 前缀、引号、`utf-8-sig`),shell 环境变量优先,绝不进 git。`fc_deploy.py:52,299-328`。
- **错误信息脱敏**:`_redact_error_text` 把已知 secret 值替换为 `***REDACTED***`,再用正则 `\b(?:LTAI|STS\.)[0-9A-Za-z]{8,}\b` 兜底;`_exception_summary` 只提取 `code/status_code/request_id/message` 并截断 300 字符——SDK 异常原文可能内嵌凭证,不能整段进日志。`fc_deploy.py:53-59,331-355`。
- **失败判据**:`412` / `CAExited` 视为部署失败(常见于启动命令错误或包结构不对)。`tech-spec.md:584`、`test_fc_deploy.py:214`。
- 产物路径约定:`build/fc/<name>/`(staging)、`build/fc/<name>.zip`、`build/fc/backup/<ts>/`、`build/fc/logs/deploy-<ts>.log`。

### 4.5 鉴权设计:anonymous 触发器 + 应用内 allowlist

**决策:HTTP 触发器用 anonymous(禁用阿里云 sig 签名认证),业务鉴权全部在应用内做**(`docs/runbook/cloud-setup.md:74`)。理由:客户端是微信小程序,天然有 `wx.login` code → openid 的身份体系,叠加阿里云签名反而要在客户端藏签名密钥。

**三步走鉴权(`auth.authorize_request`)**:读 JSON body → 必填字段校验 → 微信 `jscode2session` 换 openid → 比对 `OPENID_ALLOWLIST`。错误路径映射稳定错误码:非法 body → `400 INVALID_REQUEST`;code 换取失败 → `401 INVALID_CODE`;不在白名单 → `403 OPENID_NOT_ALLOWED`。`fc_shared/auth.py:39-52`。微信侧任何失败统一 401,响应绝不回显 code/secret/session_key,fetch 可注入以便单测。`fc_shared/wechat.py:44-52`。

**稳定错误码是跨语言契约**:`INVALID_CODE / OPENID_NOT_ALLOWED / INVALID_REQUEST / SIZE_EXCEEDED / SERVER_MISCONFIGURED / STS_ISSUE_FAILED / HEAD_OBJECT_FAILED` + 200 业务 reason `OBJECT_NOT_FOUND / SIZE_MISMATCH`——Python 端定义为字符串常量,小程序 JS 按相同字符串分支,两侧都有测试锚定。`fc_shared/errors.py:13-43`。

**环境变量管理(`env.py`)**:共享必填 6 个(`OSS_BUCKET/OSS_REGION/OSS_ENDPOINT/WX_APPID/WX_APP_SECRET/OPENID_ALLOWLIST`),每函数再加自己专属的(互不加载对方的);`MAX_UPLOAD_BYTES` 可选默认 50MB。**缺必填变量时一次性列出所有缺失变量名(绝不打印值)**→ `500 SERVER_MISCONFIGURED`,运维一眼看全要补什么。`env.py:16-41,88-107`。

**决策:不用 FC 执行角色,显式读环境变量 AK**(`docs/runbook/fc-deploy.md:357-366`)。取舍:执行角色更"正统"但增加一层角色配置与调试成本;个人项目用子账号 AK 走环境变量,配合 §5 的最小权限切分与脱敏纪律,足够且可控。

**上传校验的三态映射**(verify-upload 函数,`head.py:34-99`):HeadObject 只能校验存在性 + Content-Length(**无法校验 sha256**,PostObject 响应也拿不到内容摘要)——所以 verify 结果设计为三态:verified / `OBJECT_NOT_FOUND` / `SIZE_MISMATCH`,内容级校验留给下游消费者(Worker 下载后比对元数据里的 sha256)。404 判定依赖 §3.4 的多路兜底。

### 4.6 OSS 事件触发器要点(设计已定,未上线前的预研结论)

若用 OSS 事件触发 FC(如 `oss:ObjectCreated:*`,前缀/后缀过滤,异步调用):

- **触发器投递的是事件 JSON,不是普通 HTTP 请求**——handler 需从 body 解析 `events[].oss.object.key`;WSGI 形态无需改。
- **至少一次投递 → 函数必须幂等**:以"产物已存在"作为完成标记 + HeadObject 幂等检查,避免重复处理与重复计费。
- 配置**失败 Destination** 便于观测投递失败。
- 部署脚本只更新代码,新函数创建 + 触发器 + 环境变量走一次性人工准备(与 §4.4 的"只更新代码"原则一致)。
- 长任务函数放宽超时(如 900s)但保持小内存(纯 API 调用无本地计算时 512MB 足够)。

### 4.7 踩坑:阿里云分配的 url-id 是 canonical 的(`issue-cedential` 案例)

FC 3.0 给每个函数分配的子域名 url-id 一旦生成就是事实标准。SoniScope 的 issue-credential 函数被阿里云分配的子域名是 `issue-cedential-...`——**少了一个 r,是阿里云系统生成时的拼写错误,但绝对不能在代码里"修复"它**:改成"正确"拼写会指向一个不存在的 host。对策:在所有出现该 URL 的地方(客户端配置、部署脚本、lint 规则)加注释警告"故意拼错,勿修",并把它写进 agent/协作者约定,防止任何一次"顺手修复"。`apps/fc/README.md:10`、`fc_deploy.py:33-34`。

推而广之:**真实云资源的一切标识符(url-id、bucket 名、角色 ARN)以云端实际值为准,进 runbook,代码只引用**——见 §2.2。

## 五、RAM/STS 篇

### 5.1 核心模型:三层凭证隔离 + STS 精确到单资源

一句话:**客户端永不持有长期 AK,只拿服务端签发的、限定单个 object key、有效期 ≤900 秒的 STS 临时凭证;服务端(FC)用专职子账号长期 AK 内部 AssumeRole;后端消费者(Worker)用只读子账号 AK 且配置文件 chmod 600。** 配套"越权/过期反例测试"和"泄漏检测断言"做红线验证(§5.5)。

### 5.2 子账号切分:一职能一子账号

SoniScope 的切分表(`docs/runbook/cloud-setup.md:24-55`,主账号 UID `1633875501759333`):

| 主体 | 名称 | 权限边界 | 用途 |
|---|---|---|---|
| 子账号 | `soniscope-fc` | `AliyunSTSAssumeRoleAccess` + 自定义策略(`oss:GetObject` 仅限 `soniscope-audio/recordings/*`) | FC 运行时:AssumeRole + HeadObject |
| 子账号 | `soniscope-local-reader` | 自定义 bucket 只读策略 | Worker 只读下载 |
| 子账号 | `soniscope-asr` | `AliyunNLSFullAccess` | NLS 转写调用 |
| 子账号 | `soniscope-fc-deploy` | 最小策略 `fc:GetFunction/GetFunctionCode/UpdateFunction` | 本地部署脚本改函数代码 |
| 角色 | `soniscope-uploader-role` | 策略限 PutObject 于 `recordings/*`;**信任主体精确到 `user/soniscope-fc`** | 被 AssumeRole 后叠加 inline policy 收窄到单 key |

切分逻辑(可直接套用):

- **信任链闭环**:角色的信任主体精确到单个子账号——其他任何子账号的 AK 泄漏,也无法 AssumeRole 拿到上传能力。
- **两级收窄("角色宽 + 会话窄")**:角色自身策略限定前缀(`recordings/*`),AssumeRole 时再传 inline session policy 收窄到**单个 object key**——生效权限是两者交集,经典最小权限模式。
- **读写分离**:后端消费者(Worker)独立只读子账号,结构上拿不到 PutObject/AssumeRole 能力。
- **部署账号与运行时账号绝不复用**:`soniscope-fc-deploy`(本地 .env,能改函数代码)≠ `soniscope-fc`(FC 环境变量,运行时签 STS/HeadObject)——两者权限集完全不同,复用意味着任一侧泄漏即双杀。runbook 用整节篇幅强调不要复用。`docs/runbook/fc-deploy.md:25-209`。
- **删除权限全局不发**(任何主体都没有 DeleteObject),配合 §3.7 的结构性防删除。

**踩坑**:角色的"最大会话时长"(配 1h)必须 ≥ AssumeRole 请求的 `duration_seconds`(900s)——**请求值才是真正生效的上限**,角色侧有意留余量即可。

### 5.3 单 object key 的 STS 签发(服务端)

Policy 模板精确到单 key、无任何通配符(`sts.py:62-73`):

```python
"Resource": [f"acs:oss:*:*:{bucket}/{object_key}"]  # 单条、无 *
"Action": ["oss:PutObject"]                          # 仅 PutObject
```

配套纪律:

- **object_key 由服务端从业务 ID 严格推导**(正则 + datetime 日期合法性校验),非法直接 400——防路径穿越把 policy 撑大。`sts.py:29-59`。
- `duration_seconds = 900`(这也是 AssumeRole 允许的最短值);`role_session_name` ≤64 字符。`sts.py:24-27`。
- SDK 用法(`alibabacloud-sts20150401` + `tea-openapi`,lazy import):endpoint `sts.{region}.aliyuncs.com`;`AssumeRoleRequest(role_arn, role_session_name, duration_seconds, policy=json.dumps(...))`——**policy 以 JSON 字符串传入**;响应提取 `access_key_id / access_key_secret / security_token / expiration` 四字段。`sts.py:133-171`。
- handler 红线:长期 AK 只从环境变量读、只传给 assume_role,**绝不进响应或日志**;签发失败统一 500,日志只记 `type(exc).__name__`。`issue_credential/handler.py:71-93`。
- policy 构造函数在签发端与反例测试端**刻意重复实现**(不跨包共享,避免函数包依赖 Worker 包),靠 tech-spec 条目做规格锚点——与 §3.6 的 key 规则同理。
- 架构决策案例(ADR-8):上传元数据选 `x-oss-meta-*` 而非独立 sidecar 对象,理由是"不破坏单文件 STS 安全模型"——`oss:PutObject` 天然允许同请求携带 meta,无需放宽 policy 到第二个 key。**安全约束反向驱动架构决策**的好例子。

### 5.4 STS 凭证在客户端的正确用法(V4 PostObject 侧)

签名步骤本身见 §3.5;凭证安全相关的三条铁律:

1. **security_token 出现在三处,缺一不可**:① policy conditions `{'x-oss-security-token': token}`;② 表单字段 `x-oss-security-token`;③ 签名密钥由 access_key_secret 派生(token 本身不进 HMAC 链,但因写入被签名的 policy 而受完整性保护)。少任何一处 OSS 直接拒签。`oss_sign.js:75-105`。
2. **object_key 必须用服务端返回值,客户端不许自行拼接**——否则"单 key STS"形同虚设(客户端拼一个别的 key,policy 对不上直接失败,但如果客户端拼接逻辑与服务端一致则安全模型退化为约定)。`uploader.js:102`。
3. **凭证完整性前置检查**:7 字段(`access_key_id / access_key_secret / security_token / expiration / bucket / endpoint / object_key`)齐全非空才开始上传,否则报 `INCOMPLETE_CREDENTIAL`——把"服务端半残响应"挡在签名之前。`uploader.js:17-50`。

另外 policy 有效期与 STS 有效期取同量级(900s),conditions 里 `['eq','$key',objectKey]` 精确等于 + 全部元数据逐条锁死(见 §3.5 第 4 步)。

### 5.5 安全验证:反例测试 + 泄漏检测断言

最小权限不是配完就完,要有**自动化反例测试**证明"越权确实被拒":

- **单 key 越权反例**(`sts_escape.py`):签发单 key STS → 推导同目录另一个 key → PutObject → **断言 AccessDenied**。双签发路径:有微信 code 走真实 FC;否则用部署凭证 AssumeRole 构造等价测试凭证。无凭证时整体 SKIP、exit 0(见 §2.1)。
- **五类越权/过期反例**(`fc_live.py`):put_other_key / get_object / list_objects / delete_object / expired_put(过期用例等待凭证到期 + 15s buffer)+ 鉴权反例(伪造 code→401、白名单外→403、超大 size→400)。
- **verify 端四场景**(`verify_upload_live.py`):verified:true / OBJECT_NOT_FOUND / SIZE_MISMATCH / 伪造 code,附 P95 时延断言(1s)。
- **凭证泄漏检测断言(最值得复用的模式)**:拒绝类响应(401/403/400)里若出现**任何一个凭证字段**(access_key_id 等)→ 直接判 FAIL"疑似泄漏";鉴权失败响应若含 `etag/size/last_modified/actual_size` 或 `verified=true` → 判信息泄漏。把"错误路径不泄密"从 review 项变成断言。`fc_live.py:153-156`、`verify_upload_live.py:96-101`。
- **反例聚合门禁**(`verify_prep.py`):越权 PutObject / ListObjects / GetObject / 过期 PutObject 四例**全部被拒**才 pass;错误码按 `OSS_DENIED_CODES` / `OSS_EXPIRED_CODES` 分类表判定(错误码提取仍走 §3.4 的多路兜底)。

**踩坑**:`wx.login` 的 code 是一次性的,每调一次 FC 消耗一个——跑多条反例需要预先攒多个 code。

可量化的安全指标(验收用):客户端产物中长期 AK 检索 0 命中;STS 有效期 ≤15 分钟;单 key 越权反例 100% 被拒;未授权 openid 100% 403。(凭证自动轮换可有意推迟,编号留缺口以示"没忘,是缓做"。)

### 5.6 凭证管理纪律

- 配置内所有密钥经 `MaskedSecret`(展开见 §2.4);Worker 侧 `config.yaml` 必须 **chmod 600**,校验脚本检查权限并给修复提示。
- FC 侧全走环境变量,两函数各自独立的必填变量集,互不加载对方专属变量(§4.5)。
- 部署期凭证放本地 `.env`,绝不进 git(§4.4)。
- 客户端源码持续扫描硬编码 AK(LTAI 前缀模式,展开见 §2.4 第 4 条)。
- 日志/备份/错误信息的出口脱敏见 §2.4、§4.4。

## 六、跨领域踩坑总表

排障与新项目启动时先查这张表;"详见"列指向本手册中该坑的完整展开(展开只在一处)。

| # | 现象 | 原因 | 对策 | 证据 / 详见 |
|---|------|------|------|------|
| 1 | 修正了 FC 子域名的"拼写错误"后 host 不存在 | 阿里云分配的 url-id 本身拼错(`issue-cedential` 少个 r),但它就是真实地址 | 云端分配值是 canonical,注释警告"勿修"+ 写进协作者约定 | `apps/fc/README.md:10`、`fc_deploy.py:33-34`;§4.7 |
| 2 | bucket region 比对总是不等 | `get_bucket_info` 返回的 region 带 `oss-` 前缀 | 比对前 `.replace("oss-","")` 归一化 | `verify_prep.py:632-651`;§3.1 |
| 3 | HeadObject 查"对象是否存在"直接抛异常 | SDK 对 404 抛异常而非返回空 | catch 后判 `NoSuchKey/NoSuchObject/404`,区分不存在与真错误 | `head.py:79-93,127-130`;§3.4 |
| 4 | 非分片数据两端字段语义漂移 | manifest 中 null 的 chunk_total 写 OSS meta 变 `"0"` | null↔"0" 双向映射显式写进契约,读回 `<=0` 归 None | §3.6 |
| 5 | NLS 长任务后期拉取音频失败 | presign URL 3600s 过期,而任务排队轮询可超 50 分钟 | 超阈值重新签发 URL 并**重新提交任务** | `nls.py:49-50,314-326,409-435`;§3.3 |
| 6 | FC 启动报 `can't open file '/code/app.py'` | 部署包没把 app.py 放在包根 | 打包脚本强制复制 app.py 到 zip 根,缺失即失败 | `fc_deploy.py:207-212`、`docs/runbook/fc-deploy.md:606-617`;§4.2/§4.4 |
| 7 | mypy 报模块名冲突 | 多个函数入口同名 `handler.py` | handler 只留薄编排层、排除出 mypy;实质逻辑进共享包受 strict 检查 | `pyproject.toml:30-32,50`;§4.3 |
| 8 | 部署后函数 `412` / `CAExited` | 启动命令或包结构错误 | 一律判部署失败;验活只认 HTTP 2xx | `tech-spec.md:584`、`test_fc_deploy.py:214`;§4.4 |
| 9 | 分不清该用哪个 AK,或一处泄漏全线失守 | 部署账号与运行时账号混用 | 一职能一子账号,部署/运行时权限集分离绝不复用 | `docs/runbook/fc-deploy.md:25-209`;§5.2 |
| 10 | AssumeRole 报 duration 相关错误或有效期不符预期 | 角色最大会话时长 < 请求值;且请求值才是生效上限 | 角色侧配置留余量(如 1h),请求侧按需(900s) | §5.2 |
| 11 | 连跑多个鉴权用例只有第一个成功 | `wx.login` code 一次性,一次 FC 调用消耗一个 | 多反例预先获取多个 code | §5.5 |
| 12 | STS 表单直传被 OSS 拒签 | security_token 没有同时出现在 policy conditions、表单字段、且 secret 参与密钥派生 | 三处齐全,缺一不可 | `oss_sign.js:75-105`;§5.4 |
| 13 | 单 key STS 安全模型形同虚设 | 客户端自行拼接 object_key | object_key 必须用服务端返回值 | `uploader.js:102`;§5.4 |
| 14 | 换个 SDK 版本错误码就取不到 | 异常对象错误码字段名跨版本不统一 | 多候选属性 + 递归 unwrap + 文本兜底 | `head.py:79-93,127-130`;§3.4 |
| 15 | NLS CreateToken 一直失败 | NLS Token 服务仅在 `cn-shanghai`,与业务 region(cn-beijing)不同 | Token 客户端 region 硬编码 cn-shanghai,与 OSS region 解耦 | §3.3 |
| 16 | 文档间用例/故事编号对不上 | 多份文档演进不同步 | 以代码 docstring 中的编号为准,文档冲突反向修文档 | §5.5(实践来源) |

## 七、可复用资产索引

以下文件可从 SoniScope 仓库直接搬运到新项目(路径为该仓库内路径):

| 文件 | 用途 | 搬运注意 |
|------|------|----------|
| `apps/fc/shared/app.py` | FC Custom Runtime 零依赖 WSGI 适配层(§4.2) | 约 35 行 stdlib;确认入口模块名与 `from handler import handler` 约定一致 |
| `apps/fc/shared/fc_shared/audit.py` | 结构化日志 + 黑名单/子串双保险脱敏(§2.4) | 按项目补充敏感字段名集合;`flush=True` 依赖 stdout 采集 |
| `apps/fc/shared/fc_shared/errors.py` | 稳定错误码常量 + 客户端安全的 HTTP 错误载荷(§4.5) | 错误码字符串是跨语言契约,改动需两端同步 + 测试锚定 |
| `apps/fc/shared/fc_shared/sts.py` | 单 object key STS 签发:policy 模板 + key 校验 + StsIssuer Protocol(§5.3) | Resource 模板与 key 正则按业务改;保持"单条无通配符"原则 |
| `apps/fc/shared/fc_shared/env.py` | FC 环境变量声明式加载,缺失一次性列名不列值(§4.5) | 按函数拆必填集,别让函数加载彼此的专属变量 |
| `apps/worker/src/soniscope_worker/fc_deploy.py` | FC 部署工程化全流程:确定性打包/备份/更新/验活/回滚/脱敏(§4.4) | 换掉账号/region/函数名常量;保留"只更新代码"边界 |
| `apps/miniprogram/utils/oss_sign.js` + `hmac.js` + `sha256.js` | OSS V4 PostObject 表单签名整套 + 纯 JS 密码学原语(§3.5) | 注入 now 保持可测;用 node:crypto 校验向量回归 |
| `apps/miniprogram/utils/uploader.js` | 上传编排:凭证完整性检查 + 5s/15s/45s 退避重试(§3.5/§5.4) | 错误码分支与服务端 errors.py 对齐 |
| `apps/worker/src/soniscope_worker/poller.py` | 分页 list 双保险 + key round-trip 校验 + OssSource 只读 Protocol(§3.2/§3.6/§3.7) | Protocol 面保持 list/head/download 三方法,勿加删除 |
| `apps/worker/src/soniscope_worker/miniprogram_lint.py` | 客户端源码硬编码 AK / 密钥字面量静态扫描(§2.4) | LTAI 前缀规则是阿里云特有;其他云换前缀模式 |
| `apps/worker/src/soniscope_worker/sts_escape.py` / `fc_live.py` / `verify_upload_live.py` | 越权/过期反例测试 + 凭证泄漏检测断言(§5.5) | 无凭证 SKIP + exit 0 的门禁语义要保留,CI 才不红 |
| `apps/worker/src/soniscope_worker/config.py`(`MaskedSecret`) | Pydantic v2 密钥掩码类型(§2.4) | 所有密钥字段一律用它,配合 repr 泄漏测试 |
