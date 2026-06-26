// US-017 单元测试：上传编排（静默登录 → STS → OSS 直传，含 FC 错误、退避重试、状态机）。
// 纯逻辑 uploader 用注入 deps 验证；上传列表页用 node Page harness + mock wx 端到端验证。

const test = require('node:test')
const assert = require('node:assert')
const path = require('node:path')

const uploader = require('../utils/uploader')
const uploadQueue = require('../utils/upload_queue')

const UPLOADS_PAGE = path.resolve(__dirname, '../pages/uploads/uploads.js')

const FULL_CRED = {
  access_key_id: 'STS.id',
  access_key_secret: 'secret',
  security_token: 'token',
  expiration: '2026-06-27T11:00:00Z',
  bucket: 'soniscope-audio',
  endpoint: 'oss-cn-beijing.aliyuncs.com',
  object_key: 'recordings/2026-06-27/20260627T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE.wav',
}

function makeItem() {
  return {
    fragmentId: '20260627T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE',
    status: 'queued',
    tempFilePath: 'wxfile://tmp/rec.mp3',
    manifest: { audio: { size_bytes: 4096 } },
    ossMetadata: { 'x-oss-meta-sha256': 'abc' },
  }
}

// ── 纯逻辑：classifyFcResponse ────────────────────────────────────────────────
test('classifyFcResponse：200 + 7 字段齐全 → ok + credential', function () {
  const r = uploader.classifyFcResponse(200, FULL_CRED)
  assert.strictEqual(r.ok, true)
  assert.strictEqual(r.credential.object_key, FULL_CRED.object_key)
})

test('classifyFcResponse：200 但缺字段 → 不 ok', function () {
  const r = uploader.classifyFcResponse(200, { access_key_id: 'x' })
  assert.strictEqual(r.ok, false)
  assert.strictEqual(r.errorCode, 'INCOMPLETE_CREDENTIAL')
})

test('classifyFcResponse：非 200 取 body.error 稳定错误码（AC#3）', function () {
  assert.strictEqual(uploader.classifyFcResponse(403, { error: 'OPENID_NOT_ALLOWED' }).errorCode,
    'OPENID_NOT_ALLOWED')
  assert.strictEqual(uploader.classifyFcResponse(400, { error: 'SIZE_EXCEEDED' }).errorCode,
    'SIZE_EXCEEDED')
  assert.strictEqual(uploader.classifyFcResponse(500, {}).errorCode, 'HTTP_500')
})

test('退避延时为 5s/15s/45s 最多 3 次（AGENTS 错误处理）', function () {
  assert.deepStrictEqual(uploader.RETRY_DELAYS_MS, [5000, 15000, 45000])
  assert.strictEqual(uploader.MAX_UPLOAD_RETRIES, 3)
})

// ── uploadFragment：happy / FC reject / OSS retry / login fail ────────────────
function baseDeps(overrides) {
  const statuses = []
  const progress = []
  const deps = {
    region: 'cn-beijing',
    uploadUrl: 'https://soniscope-audio.oss-cn-beijing.aliyuncs.com',
    now: () => new Date(Date.UTC(2026, 5, 27, 10, 15, 0)),
    login: async () => 'wx-code-1',
    requestSts: async () => ({ statusCode: 200, data: FULL_CRED }),
    uploadFile: async (opts) => {
      if (opts.onProgress) opts.onProgress(100)
      return { statusCode: 200, data: '' }
    },
    wait: async () => {},
    onStatus: (s, extra) => statuses.push(Object.assign({ status: s }, extra)),
    onProgress: (p) => progress.push(p),
  }
  return { deps: Object.assign(deps, overrides || {}), statuses: statuses, progress: progress }
}

test('uploadFragment happy：uploading → pending_verify，进度回调（AC#1/#7）', async function () {
  const { deps, statuses, progress } = baseDeps()
  const res = await uploader.uploadFragment(makeItem(), deps)
  assert.strictEqual(res.status, uploadQueue.STATUS_PENDING_VERIFY)
  assert.strictEqual(statuses[0].status, uploadQueue.STATUS_UPLOADING)
  assert.strictEqual(statuses[statuses.length - 1].status, uploadQueue.STATUS_PENDING_VERIFY)
  assert.ok(progress.includes(100))
})

test('uploadFragment：FC 非 200 → 待人工重传 + 记录错误码（AC#3，不重试）', async function () {
  let ossCalls = 0
  const { deps } = baseDeps({
    requestSts: async () => ({ statusCode: 403, data: { error: 'OPENID_NOT_ALLOWED' } }),
    uploadFile: async () => { ossCalls += 1; return { statusCode: 200 } },
  })
  const res = await uploader.uploadFragment(makeItem(), deps)
  assert.strictEqual(res.status, uploadQueue.STATUS_MANUAL_RETRY)
  assert.strictEqual(res.errorCode, 'OPENID_NOT_ALLOWED')
  assert.strictEqual(ossCalls, 0, 'FC 失败不应触发 OSS 上传')
})

test('uploadFragment：OSS 持续失败按退避重试 3 次后待人工重传（AC#6）', async function () {
  let attempts = 0
  const waits = []
  const { deps } = baseDeps({
    uploadFile: async () => { attempts += 1; return { statusCode: 503 } },
    wait: async (ms) => { waits.push(ms) },
  })
  const res = await uploader.uploadFragment(makeItem(), deps)
  assert.strictEqual(res.status, uploadQueue.STATUS_MANUAL_RETRY)
  assert.strictEqual(res.errorCode, 'OSS_UPLOAD_FAILED')
  assert.strictEqual(attempts, 4, '初次 + 3 次重试')
  assert.deepStrictEqual(waits, [5000, 15000, 45000])
})

test('uploadFragment：OSS 第 3 次重试成功 → 待 verify', async function () {
  let attempts = 0
  const { deps } = baseDeps({
    uploadFile: async () => {
      attempts += 1
      return attempts < 3 ? { statusCode: 500 } : { statusCode: 200 }
    },
    wait: async () => {},
  })
  const res = await uploader.uploadFragment(makeItem(), deps)
  assert.strictEqual(res.status, uploadQueue.STATUS_PENDING_VERIFY)
})

test('uploadFragment：网络错误（uploadFile 抛异常）也走退避重试', async function () {
  let attempts = 0
  const { deps } = baseDeps({
    uploadFile: async () => { attempts += 1; throw new Error('network') },
    wait: async () => {},
  })
  const res = await uploader.uploadFragment(makeItem(), deps)
  assert.strictEqual(res.status, uploadQueue.STATUS_MANUAL_RETRY)
  assert.strictEqual(attempts, 4)
})

test('uploadFragment：login 失败 → 待人工重传', async function () {
  const { deps } = baseDeps({ login: async () => { throw new Error('login') } })
  const res = await uploader.uploadFragment(makeItem(), deps)
  assert.strictEqual(res.status, uploadQueue.STATUS_MANUAL_RETRY)
  assert.strictEqual(res.errorCode, 'LOGIN_FAILED')
})

// ── 上传列表页集成（Page harness + mock wx）──────────────────────────────────
function makeWxUploads(storage, scenario) {
  return {
    getStorageSync: (k) =>
      Object.prototype.hasOwnProperty.call(storage, k) ? storage[k] : '',
    setStorageSync: (k, v) => { storage[k] = v },
    getNetworkType: (opt) => opt.success({ networkType: scenario.network || 'wifi' }),
    login: (opt) =>
      scenario.loginFail ? opt.fail(new Error('login')) : opt.success({ code: 'c1' }),
    request: (opt) => opt.success({ statusCode: scenario.fcStatus || 200, data: scenario.fcData }),
    uploadFile: (opt) => {
      opt.success({ statusCode: scenario.ossStatus || 200, data: '' })
      return { onProgressUpdate: function () {} }
    },
  }
}

function loadUploadsPage(wx) {
  global.wx = wx
  let captured = null
  global.Page = function (opts) { captured = opts }
  delete require.cache[UPLOADS_PAGE]
  require(UPLOADS_PAGE)
  const inst = Object.assign({}, captured)
  inst.data = JSON.parse(JSON.stringify(captured.data))
  inst.setData = function (patch) { Object.assign(inst.data, patch) }
  return inst
}

function queuedItem() {
  return {
    fragmentId: '20260627T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE',
    status: 'queued',
    statusText: '待上传',
    tempFilePath: 'wxfile://tmp/rec.mp3',
    manifest: { audio: { size_bytes: 4096 } },
    ossMetadata: { 'x-oss-meta-sha256': 'abc' },
  }
}

test('uploads 页 onShow：queued → 待 verify 并落盘（AC#1/#7）', async function () {
  const storage = { 'soniscope:upload_queue': [queuedItem()] }
  const wx = makeWxUploads(storage, { fcData: FULL_CRED })
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  await inst._processQueue()
  const persisted = storage['soniscope:upload_queue'][0]
  assert.strictEqual(persisted.status, 'pending_verify')
  assert.strictEqual(persisted.statusText, '待 verify')
})

test('uploads 页：FC 403 → 待人工重传 + 记录错误码（AC#3）', async function () {
  const storage = { 'soniscope:upload_queue': [queuedItem()] }
  const wx = makeWxUploads(storage, { fcStatus: 403, fcData: { error: 'OPENID_NOT_ALLOWED' } })
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  await inst._processQueue()
  const persisted = storage['soniscope:upload_queue'][0]
  assert.strictEqual(persisted.status, 'manual_retry')
  assert.strictEqual(persisted.statusText, '待人工重传')
  assert.strictEqual(persisted.errorCode, 'OPENID_NOT_ALLOWED')
})

test('uploads 页：离线时跳过上传，保持 queued', async function () {
  const storage = { 'soniscope:upload_queue': [queuedItem()] }
  const wx = makeWxUploads(storage, { network: 'none', fcData: FULL_CRED })
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  await inst._processQueue()
  assert.strictEqual(storage['soniscope:upload_queue'][0].status, 'queued')
})

test('updateQueueItem：按 fragmentId 更新并同步 statusText', function () {
  const q = [queuedItem()]
  const next = uploadQueue.updateQueueItem(q, q[0].fragmentId, { status: 'uploading', progress: 30 })
  assert.strictEqual(next[0].status, 'uploading')
  assert.strictEqual(next[0].statusText, '上传中')
  assert.strictEqual(next[0].progress, 30)
  // 不可变：原数组未被修改。
  assert.strictEqual(q[0].status, 'queued')
})
