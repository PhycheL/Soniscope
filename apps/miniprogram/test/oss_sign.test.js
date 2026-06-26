// US-017 单元测试：HMAC-SHA256 / base64 与 OSS V4 PostObject 表单签名。
// 用 node:crypto 作为独立对照，校验纯 JS 实现（无外部依赖）与 OSS V4 签名链路正确性。

const test = require('node:test')
const assert = require('node:assert')
const crypto = require('node:crypto')

const { hmacSha256Hex, base64Encode } = require('../utils/hmac')
const { sha256Bytes } = require('../utils/sha256')
const oss = require('../utils/oss_sign')

test('HMAC-SHA256 与 node:crypto 一致（标准向量）', function () {
  const got = hmacSha256Hex('key', 'The quick brown fox jumps over the lazy dog')
  assert.strictEqual(got, 'f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8')
})

test('HMAC-SHA256 对随机字节与 node:crypto 一致', function () {
  const key = crypto.randomBytes(40)
  const msg = crypto.randomBytes(200)
  const expected = crypto.createHmac('sha256', key).update(msg).digest('hex')
  assert.strictEqual(hmacSha256Hex(key, msg), expected)
})

test('sha256Bytes 与 node:crypto 一致', function () {
  const data = crypto.randomBytes(123)
  const got = Buffer.from(sha256Bytes(data)).toString('hex')
  assert.strictEqual(got, crypto.createHash('sha256').update(data).digest('hex'))
})

test('base64Encode 标准向量与 padding', function () {
  assert.strictEqual(base64Encode('Man'), 'TWFu')
  assert.strictEqual(base64Encode('Ma'), 'TWE=')
  assert.strictEqual(base64Encode('M'), 'TQ==')
  assert.strictEqual(base64Encode('日观声记'), Buffer.from('日观声记', 'utf8').toString('base64'))
})

const CRED = {
  access_key_id: 'STS.AkId123',
  access_key_secret: 'sts-secret-do-not-log',
  security_token: 'security-token-xyz',
  bucket: 'soniscope-audio',
  endpoint: 'oss-cn-beijing.aliyuncs.com',
  object_key: 'recordings/2026-06-27/20260627T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE.wav',
}
const META = {
  'x-oss-meta-session-id': '01HZX3K8MN5PQR9TFB7AYWVCDE',
  'x-oss-meta-chunk-seq': '1',
  'x-oss-meta-chunk-total': '0',
  'x-oss-meta-sha256': 'abc123',
}
const NOW = new Date(Date.UTC(2026, 5, 27, 10, 15, 0))

test('buildPostObjectForm 表单字段齐全且 key 用 FC 返回值（AC#4/#5）', function () {
  const form = oss.buildPostObjectForm({
    credential: CRED,
    ossMetadata: META,
    now: NOW,
    region: 'cn-beijing',
    uploadUrl: 'https://soniscope-audio.oss-cn-beijing.aliyuncs.com',
  })
  assert.strictEqual(form.url, 'https://soniscope-audio.oss-cn-beijing.aliyuncs.com')
  assert.strictEqual(form.name, 'file')
  const fd = form.formData
  // object_key 必须等于 FC 返回值，不被前端覆盖（AC#4）。
  assert.strictEqual(fd.key, CRED.object_key)
  assert.strictEqual(fd['x-oss-signature-version'], 'OSS4-HMAC-SHA256')
  assert.strictEqual(fd['x-oss-credential'], 'STS.AkId123/20260627/cn-beijing/oss/aliyun_v4_request')
  assert.strictEqual(fd['x-oss-date'], '20260627T101500Z')
  assert.strictEqual(fd['x-oss-security-token'], CRED.security_token)
  assert.strictEqual(fd.success_action_status, '200')
  assert.ok(fd.policy && fd['x-oss-signature'])
  // 全部 x-oss-meta-* 元数据进入表单（AC#5）。
  Object.keys(META).forEach(function (k) {
    assert.strictEqual(fd[k], META[k])
  })
})

test('buildPostObjectForm 签名与独立 OSS V4 计算一致', function () {
  const form = oss.buildPostObjectForm({
    credential: CRED,
    ossMetadata: META,
    now: NOW,
    region: 'cn-beijing',
  })
  // 独立用 node:crypto 重算 OSS V4 签名链。
  const date = '20260627'
  const region = 'cn-beijing'
  const hmac = function (key, msg) {
    return crypto.createHmac('sha256', key).update(msg).digest()
  }
  const k1 = hmac('aliyun_v4' + CRED.access_key_secret, date)
  const k2 = hmac(k1, region)
  const k3 = hmac(k2, 'oss')
  const signingKey = hmac(k3, 'aliyun_v4_request')
  const expected = crypto.createHmac('sha256', signingKey).update(form.formData.policy).digest('hex')
  assert.strictEqual(form.formData['x-oss-signature'], expected)
})

test('policy base64 解码后含 key/bucket/security-token 条件', function () {
  const form = oss.buildPostObjectForm({ credential: CRED, ossMetadata: META, now: NOW })
  const policy = JSON.parse(Buffer.from(form.formData.policy, 'base64').toString('utf8'))
  assert.ok(Array.isArray(policy.conditions))
  const flat = JSON.stringify(policy.conditions)
  assert.ok(flat.includes(CRED.object_key))
  assert.ok(flat.includes('soniscope-audio'))
  assert.ok(flat.includes('OSS4-HMAC-SHA256'))
  assert.ok(typeof policy.expiration === 'string' && policy.expiration.endsWith('Z'))
})
