// 上传后 verify 回执（US-018）：OSS 直传收到 2xx 后立即 POST verify-upload 得到最终签收回执。
// 沿用 codebase「纯逻辑 + IO 注入」分层：
//
// * classifyVerifyResponse 纯函数，直接 node 单测；
// * verifyFragment 编排，一切 IO（login / requestVerify / wait / now）由注入的 deps 提供，
//   Page 提供真实 wx 适配器，测试注入 mock，不触网；
// * 绝不打印敏感字段（仅记录 fragmentId / 状态 / reason / 错误码）。

const {
  STATUS_VERIFIED,
  STATUS_MANUAL_RETRY,
  STATUS_MANUAL_VERIFY,
} = require('./upload_queue')

// verify 网络错误 / 5xx 的指数退避延时（AGENTS 错误处理：5s → 15s → 45s，最多 3 次）。
const VERIFY_RETRY_DELAYS_MS = [5000, 15000, 45000]
const MAX_VERIFY_RETRIES = VERIFY_RETRY_DELAYS_MS.length

// verified:false 的两类业务原因（tech-spec §4.2，FC verify-upload 200 响应体字段）。
const REASON_OBJECT_NOT_FOUND = 'OBJECT_NOT_FOUND'
const REASON_SIZE_MISMATCH = 'SIZE_MISMATCH'

// 判定 verify 响应分类：
//   verified  → 200 且 verified:true（AC#2）
//   unverified→ 200 且 verified:false，携带 reason（AC#3 OBJECT_NOT_FOUND / SIZE_MISMATCH）
//   retryable → 5xx / 网络错误（AC#4 退避重试）
//   fatal     → 4xx 鉴权 / 参数错误（AGENTS：立即失败不重试）
function classifyVerifyResponse(statusCode, body) {
  const code = Number(statusCode)
  const data = body || {}
  if (code === 200) {
    if (data.verified === true) {
      return {
        kind: 'verified',
        etag: data.etag,
        size: data.size,
        lastModified: data.last_modified,
      }
    }
    return {
      kind: 'unverified',
      reason: data.reason ? String(data.reason) : 'UNKNOWN',
      actualSize: data.actual_size,
    }
  }
  if (code >= 500) {
    return { kind: 'retryable', errorCode: 'HTTP_' + code }
  }
  const errorCode = data.error ? String(data.error) : 'HTTP_' + (code || 0)
  return { kind: 'fatal', errorCode: errorCode }
}

// verify 单条 Fragment（AC#1-#4）。返回最终状态补丁 { status, reason?/errorCode?/verifiedAt? }。
// deps：login() / requestVerify(code, fragmentId, expectedSize) / wait(ms) / now() /
//       onStatus(status, extra) / logger。
async function verifyFragment(item, deps) {
  const logger = deps.logger || { info() {}, warn() {}, error() {} }
  const fragmentId = item.fragmentId
  const expectedSize =
    (item.manifest && item.manifest.audio && item.manifest.audio.size_bytes) || 0
  const setStatus = function (status, extra) {
    if (deps.onStatus) {
      deps.onStatus(status, extra || {})
    }
  }

  for (let attempt = 0; attempt <= MAX_VERIFY_RETRIES; attempt++) {
    // AC#1：携带 code、fragment_id、expected_size 调 verify-upload。code 一次性，每次重试重新登录。
    let code
    try {
      code = await deps.login()
    } catch (e) {
      if (attempt < MAX_VERIFY_RETRIES) {
        if (deps.wait) {
          await deps.wait(VERIFY_RETRY_DELAYS_MS[attempt])
        }
        continue
      }
      setStatus(STATUS_MANUAL_VERIFY, { errorCode: 'LOGIN_FAILED' })
      logger.warn('verify login failed', { fragmentId: fragmentId })
      return { status: STATUS_MANUAL_VERIFY, errorCode: 'LOGIN_FAILED' }
    }

    let resp = null
    let networkError = false
    try {
      resp = await deps.requestVerify(code, fragmentId, expectedSize)
    } catch (e) {
      networkError = true
    }

    if (!networkError && resp) {
      const cls = classifyVerifyResponse(resp.statusCode, resp.data)
      if (cls.kind === 'verified') {
        // AC#2：写入 verified_at，状态切换为上传成功（verified）。
        const verifiedAt = deps.now ? deps.now() : Date.now()
        setStatus(STATUS_VERIFIED, { verifiedAt: verifiedAt, reason: '', errorCode: '' })
        logger.info('verify ok', { fragmentId: fragmentId })
        return { status: STATUS_VERIFIED, verifiedAt: verifiedAt }
      }
      if (cls.kind === 'unverified') {
        // AC#3：OBJECT_NOT_FOUND / SIZE_MISMATCH → 待人工重传并展示 reason。
        setStatus(STATUS_MANUAL_RETRY, { reason: cls.reason })
        logger.warn('verify unverified', { fragmentId: fragmentId, reason: cls.reason })
        return { status: STATUS_MANUAL_RETRY, reason: cls.reason }
      }
      if (cls.kind === 'fatal') {
        // 4xx：上传已成功，仅 verify 鉴权 / 参数失败 → 待人工 verify（不重试）。
        setStatus(STATUS_MANUAL_VERIFY, { errorCode: cls.errorCode })
        logger.warn('verify fatal', { fragmentId: fragmentId, errorCode: cls.errorCode })
        return { status: STATUS_MANUAL_VERIFY, errorCode: cls.errorCode }
      }
      // retryable：落入下方退避。
    }

    // AC#4：网络错误 / 5xx → 退避重试。
    if (attempt < MAX_VERIFY_RETRIES) {
      logger.warn('verify retry', { fragmentId: fragmentId, attempt: attempt + 1 })
      if (deps.wait) {
        await deps.wait(VERIFY_RETRY_DELAYS_MS[attempt])
      }
    }
  }

  // 重试 3 次仍失败 → 待人工 verify（AC#4）。
  setStatus(STATUS_MANUAL_VERIFY, { errorCode: 'VERIFY_FAILED' })
  logger.error('verify exhausted retries', { fragmentId: fragmentId })
  return { status: STATUS_MANUAL_VERIFY, errorCode: 'VERIFY_FAILED' }
}

module.exports = {
  VERIFY_RETRY_DELAYS_MS: VERIFY_RETRY_DELAYS_MS,
  MAX_VERIFY_RETRIES: MAX_VERIFY_RETRIES,
  REASON_OBJECT_NOT_FOUND: REASON_OBJECT_NOT_FOUND,
  REASON_SIZE_MISMATCH: REASON_SIZE_MISMATCH,
  classifyVerifyResponse: classifyVerifyResponse,
  verifyFragment: verifyFragment,
}
