// 上传编排（US-017）：静默登录 → 获取单文件 STS → OSS 直传，含 FC 错误处理、
// OSS 指数退避重试与状态机迁移。设计沿用 codebase「纯逻辑 + IO 注入」分层：
//
// * 纯逻辑（classifyFcResponse / 退避延时 / 状态判定）无 IO，直接 node 单测；
// * 一切 IO（wx.login / wx.request / wx.uploadFile / 等待）收敛到注入的 deps，
//   Page 提供真实 wx 适配器，测试注入 mock，不触网；
// * 绝不打印 access_key_secret / security_token（仅记录非敏感的 object_key / 状态 / 错误码）。

const {
  STATUS_UPLOADING,
  STATUS_PENDING_VERIFY,
  STATUS_MANUAL_RETRY,
} = require('./upload_queue')
const { buildPostObjectForm } = require('./oss_sign')

// FC issue-credential 成功响应必备的 7 个字段（tech-spec §4.1，与 fc_live.CREDENTIAL_FIELDS 一致）。
const CREDENTIAL_FIELDS = [
  'access_key_id',
  'access_key_secret',
  'security_token',
  'expiration',
  'bucket',
  'endpoint',
  'object_key',
]

// OSS 非 2xx / 网络错误的指数退避延时（AGENTS 错误处理：5s → 15s → 45s，最多 3 次）。
const RETRY_DELAYS_MS = [5000, 15000, 45000]
const MAX_UPLOAD_RETRIES = RETRY_DELAYS_MS.length

// 判定 FC 响应：200 + 7 字段齐全 → 凭证；否则取稳定错误码（AC#3）。
function classifyFcResponse(statusCode, body) {
  const data = body || {}
  if (Number(statusCode) === 200) {
    const missing = CREDENTIAL_FIELDS.filter(function (f) {
      return !String(data[f] == null ? '' : data[f]).trim()
    })
    if (!missing.length) {
      const credential = {}
      CREDENTIAL_FIELDS.forEach(function (f) {
        credential[f] = data[f]
      })
      return { ok: true, credential: credential }
    }
    return { ok: false, errorCode: 'INCOMPLETE_CREDENTIAL' }
  }
  // FC 用 body.error 返回稳定错误码（INVALID_CODE / OPENID_NOT_ALLOWED / SIZE_EXCEEDED 等）。
  const errorCode = data.error ? String(data.error) : 'HTTP_' + Number(statusCode || 0)
  return { ok: false, errorCode: errorCode }
}

function isOssSuccess(statusCode) {
  const code = Number(statusCode)
  return code >= 200 && code < 300
}

// 上传单条 Fragment（AC#1-#7）。返回最终状态补丁 { status, errorCode? }。
// deps：login() / requestSts(code, fragmentId, size) / uploadFile({url,name,filePath,formData,onProgress})
//       / wait(ms) / now() / region / uploadUrl / onStatus(status, extra) / onProgress(percent) / logger。
async function uploadFragment(item, deps) {
  const logger = deps.logger || { info: function () {}, warn: function () {}, error: function () {} }
  const fragmentId = item.fragmentId
  const size = (item.manifest && item.manifest.audio && item.manifest.audio.size_bytes) || 0

  const setStatus = function (status, extra) {
    if (deps.onStatus) {
      deps.onStatus(status, extra || {})
    }
  }

  // AC#1：网络可用进入上传中。
  setStatus(STATUS_UPLOADING, { progress: 0 })

  // AC#2：静默登录拿 code → POST issue-credential 拿单文件 STS。
  let code
  try {
    code = await deps.login()
  } catch (e) {
    setStatus(STATUS_MANUAL_RETRY, { errorCode: 'LOGIN_FAILED' })
    logger.warn('upload login failed', { fragmentId: fragmentId })
    return { status: STATUS_MANUAL_RETRY, errorCode: 'LOGIN_FAILED' }
  }

  let fcResp
  try {
    fcResp = await deps.requestSts(code, fragmentId, size)
  } catch (e) {
    // FC 网络错误：按 4xx 同等立即失败处理（AC#3 范畴，待人工重传）。
    setStatus(STATUS_MANUAL_RETRY, { errorCode: 'FC_UNREACHABLE' })
    logger.warn('upload fc unreachable', { fragmentId: fragmentId })
    return { status: STATUS_MANUAL_RETRY, errorCode: 'FC_UNREACHABLE' }
  }

  const cls = classifyFcResponse(fcResp.statusCode, fcResp.data)
  if (!cls.ok) {
    // AC#3：FC 返回非 200 → 待人工重传，并记录错误码。
    setStatus(STATUS_MANUAL_RETRY, { errorCode: cls.errorCode })
    logger.warn('upload fc rejected', { fragmentId: fragmentId, errorCode: cls.errorCode })
    return { status: STATUS_MANUAL_RETRY, errorCode: cls.errorCode }
  }

  // AC#4：object_key 用 FC 返回值，不由前端拼接覆盖。AC#5：附带全部 x-oss-meta-* 元数据。
  const form = buildPostObjectForm({
    credential: cls.credential,
    ossMetadata: item.ossMetadata || {},
    now: deps.now ? deps.now() : new Date(),
    region: deps.region,
    uploadUrl: deps.uploadUrl,
  })
  logger.info('sts issued, uploading to oss', {
    fragmentId: fragmentId,
    object_key: cls.credential.object_key,
  })

  // AC#6：OSS 非 2xx / 网络错误按 5s/15s/45s 退避，最多 3 次；AC#7：进度回调 + 2xx→待 verify。
  for (let attempt = 0; attempt <= MAX_UPLOAD_RETRIES; attempt++) {
    let ossResp = null
    let failed = false
    try {
      ossResp = await deps.uploadFile({
        url: form.url,
        name: form.name,
        filePath: item.tempFilePath,
        formData: form.formData,
        onProgress: function (percent) {
          if (deps.onProgress) {
            deps.onProgress(percent)
          }
        },
      })
    } catch (e) {
      failed = true
    }
    if (!failed && ossResp && isOssSuccess(ossResp.statusCode)) {
      setStatus(STATUS_PENDING_VERIFY, { progress: 100 })
      logger.info('oss upload ok, pending verify', { fragmentId: fragmentId })
      return { status: STATUS_PENDING_VERIFY }
    }
    if (attempt < MAX_UPLOAD_RETRIES) {
      logger.warn('oss upload failed, will retry', {
        fragmentId: fragmentId,
        attempt: attempt + 1,
        statusCode: ossResp ? ossResp.statusCode : 'network-error',
      })
      if (deps.wait) {
        await deps.wait(RETRY_DELAYS_MS[attempt])
      }
    }
  }

  // 重试 3 次仍失败 → 待人工重传（AC#6）。
  setStatus(STATUS_MANUAL_RETRY, { errorCode: 'OSS_UPLOAD_FAILED' })
  logger.error('oss upload exhausted retries', { fragmentId: fragmentId })
  return { status: STATUS_MANUAL_RETRY, errorCode: 'OSS_UPLOAD_FAILED' }
}

module.exports = {
  CREDENTIAL_FIELDS: CREDENTIAL_FIELDS,
  RETRY_DELAYS_MS: RETRY_DELAYS_MS,
  MAX_UPLOAD_RETRIES: MAX_UPLOAD_RETRIES,
  classifyFcResponse: classifyFcResponse,
  isOssSuccess: isOssSuccess,
  uploadFragment: uploadFragment,
}
