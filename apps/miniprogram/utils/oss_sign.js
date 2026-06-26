// OSS V4 PostObject 表单签名（US-017）：小程序用 FC 签发的单文件 STS 凭证，
// 通过 wx.uploadFile（POST multipart/form-data）直传音频到 OSS。
//
// wx.uploadFile 只能发 POST 表单，故走 OSS「PostObject」表单上传协议（不是 PUT），
// 用 OSS4-HMAC-SHA256 对 base64(policy) 签名。签名算法见阿里云 OSS V4 Post 文档。
//
// 本模块为纯函数：注入 now（Date）即可确定性产出，便于 node 单测对照。
// 绝不在此打印 access_key_secret / security_token（调用方用脱敏 logger 记录非敏感字段）。

const { hmacSha256, hmacSha256Hex, base64Encode } = require('./hmac')

const SIGNATURE_VERSION = 'OSS4-HMAC-SHA256'
const SERVICE = 'oss'
const REQUEST_TYPE = 'aliyun_v4_request'
// 表单 policy 有效期（秒）：与 STS 有效期同量级即可，签名本身受 STS 过期约束。
const DEFAULT_POLICY_EXPIRE_SECONDS = 900

// UTC <YYYYMMDD>
function utcDate(now) {
  const y = now.getUTCFullYear()
  const m = String(now.getUTCMonth() + 1).padStart(2, '0')
  const d = String(now.getUTCDate()).padStart(2, '0')
  return '' + y + m + d
}

// UTC ISO8601 basic：<YYYYMMDDTHHMMSSZ>
function utcDateTime(now) {
  const hh = String(now.getUTCHours()).padStart(2, '0')
  const mm = String(now.getUTCMinutes()).padStart(2, '0')
  const ss = String(now.getUTCSeconds()).padStart(2, '0')
  return utcDate(now) + 'T' + hh + mm + ss + 'Z'
}

// RFC3339 expiration（policy.expiration），UTC，毫秒置 0。
function expirationIso(now, expireSeconds) {
  const exp = new Date(now.getTime() + expireSeconds * 1000)
  return exp.toISOString().replace(/\.\d{3}Z$/, 'Z')
}

// V4 派生签名密钥：HMAC 链（aliyun_v4+secret → date → region → service → request）。
function deriveSigningKey(secret, date, region) {
  const k1 = hmacSha256('aliyun_v4' + secret, date)
  const k2 = hmacSha256(k1, region)
  const k3 = hmacSha256(k2, SERVICE)
  return hmacSha256(k3, REQUEST_TYPE)
}

// 构造 wx.uploadFile 所需的 PostObject 表单字段与签名。
//
// credential：FC issue-credential 返回的 STS 凭证 + object_key（{ access_key_id,
//   access_key_secret, security_token, bucket, endpoint, object_key }）。
//   object_key 必须用 FC 返回值，不由前端自行拼接覆盖（AC#4）。
// ossMetadata：x-oss-meta-* 元数据（buildOssMetadata 产出，AC#5）。
// 返回 { url, name, formData }：直接喂给 wx.uploadFile。
function buildPostObjectForm(opts) {
  const credential = opts.credential || {}
  const ossMetadata = opts.ossMetadata || {}
  const now = opts.now || new Date()
  const region = opts.region || 'cn-beijing'
  const uploadUrl = opts.uploadUrl || ''
  const expireSeconds = opts.expireSeconds || DEFAULT_POLICY_EXPIRE_SECONDS

  const accessKeyId = String(credential.access_key_id || '')
  const accessKeySecret = String(credential.access_key_secret || '')
  const securityToken = String(credential.security_token || '')
  const objectKey = String(credential.object_key || '')
  const bucket = String(credential.bucket || '')

  const date = utcDate(now)
  const dateTime = utcDateTime(now)
  const credentialString =
    accessKeyId + '/' + date + '/' + region + '/' + SERVICE + '/' + REQUEST_TYPE

  // policy 条件：精确约束 key、签名版本、凭证、时间、安全令牌、成功状态码与全部元数据。
  const conditions = [
    { bucket: bucket },
    ['eq', '$key', objectKey],
    { 'x-oss-signature-version': SIGNATURE_VERSION },
    { 'x-oss-credential': credentialString },
    { 'x-oss-date': dateTime },
    { 'x-oss-security-token': securityToken },
    { success_action_status: '200' },
  ]
  const metaKeys = Object.keys(ossMetadata).sort()
  metaKeys.forEach(function (k) {
    const cond = {}
    cond[k] = String(ossMetadata[k])
    conditions.push(cond)
  })

  const policy = { expiration: expirationIso(now, expireSeconds), conditions: conditions }
  const base64Policy = base64Encode(JSON.stringify(policy))
  const signingKey = deriveSigningKey(accessKeySecret, date, region)
  const signature = hmacSha256Hex(signingKey, base64Policy)

  const formData = {
    key: objectKey,
    policy: base64Policy,
    'x-oss-signature-version': SIGNATURE_VERSION,
    'x-oss-credential': credentialString,
    'x-oss-date': dateTime,
    'x-oss-security-token': securityToken,
    'x-oss-signature': signature,
    success_action_status: '200',
  }
  metaKeys.forEach(function (k) {
    formData[k] = String(ossMetadata[k])
  })

  return { url: uploadUrl, name: 'file', formData: formData }
}

module.exports = {
  SIGNATURE_VERSION: SIGNATURE_VERSION,
  DEFAULT_POLICY_EXPIRE_SECONDS: DEFAULT_POLICY_EXPIRE_SECONDS,
  utcDate: utcDate,
  utcDateTime: utcDateTime,
  expirationIso: expirationIso,
  deriveSigningKey: deriveSigningKey,
  buildPostObjectForm: buildPostObjectForm,
}
