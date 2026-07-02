// 界面重设计单测：历史弹层卡片装饰（relativeDay / dotKindFor / decorateHistoryCards）
// 与上传队列运行时（queue_runtime）编排。纯逻辑 + 注入 mock wx，随 node --test 纳入质量门。

const test = require('node:test')
const assert = require('node:assert')

const view = require('../utils/uploads_view')
const { createQueueRuntime } = require('../utils/queue_runtime')
const uploadQueue = require('../utils/upload_queue')
const { STATUS_TEXT } = require('../utils/upload_queue')

const DAY_MS = 24 * 60 * 60 * 1000

function item(fragmentId, status, manifest, extra) {
  return Object.assign(
    {
      fragmentId: fragmentId,
      status: status,
      statusText: STATUS_TEXT[status] || status,
      durationSeconds: (manifest && manifest.duration_seconds) || 0,
      manifest: manifest || {},
    },
    extra || {},
  )
}

// ── relativeDay ──────────────────────────────────────────────────────────────
test('relativeDay：同日 → 今天，前一日 → 昨天，更早 → M-D', function () {
  const now = new Date('2026-07-02T14:00:00').getTime()
  assert.strictEqual(view.relativeDay(new Date('2026-07-02T09:00:00').getTime(), now), '今天')
  assert.strictEqual(view.relativeDay(new Date('2026-07-01T23:00:00').getTime(), now), '昨天')
  assert.strictEqual(view.relativeDay(new Date('2026-06-28T10:00:00').getTime(), now), '6-28')
  assert.strictEqual(view.relativeDay(null, now), '')
})

// ── dotKindFor ───────────────────────────────────────────────────────────────
test('dotKindFor：失败态 → fail，verified → ok，其余 → up', function () {
  assert.strictEqual(view.dotKindFor('upload_failed'), 'fail')
  assert.strictEqual(view.dotKindFor('manual_retry'), 'fail')
  assert.strictEqual(view.dotKindFor('manual_verify'), 'fail')
  assert.strictEqual(view.dotKindFor('verified'), 'ok')
  assert.strictEqual(view.dotKindFor('queued'), 'up')
  assert.strictEqual(view.dotKindFor('uploading'), 'up')
  assert.strictEqual(view.dotKindFor('pending_verify'), 'up')
})

// ── decorateHistoryCards ─────────────────────────────────────────────────────
test('decorateHistoryCards：单卡补 title/subText/dotKind（含相对时间）', function () {
  const now = new Date('2026-07-02T14:00:00').getTime()
  const recorded = new Date('2026-07-02T13:59:00').getTime()
  const queue = [item('f1', 'verified', { recorded_at: new Date(recorded).toISOString(), duration_seconds: 11 })]
  const cards = view.decorateHistoryCards(view.buildCards(queue), now)
  assert.strictEqual(cards[0].type, 'single')
  assert.strictEqual(cards[0].dotKind, 'ok')
  assert.strictEqual(cards[0].title, '录音')
  assert.ok(cards[0].subText.indexOf('今天') === 0, 'subText 应以相对时间开头: ' + cards[0].subText)
})

test('decorateHistoryCards：失败单卡显示错误码', function () {
  const queue = [item('f1', 'upload_failed', {}, { errorCode: 'OSS_UPLOAD_FAILED' })]
  const cards = view.decorateHistoryCards(view.buildCards(queue), Date.now())
  assert.strictEqual(cards[0].dotKind, 'fail')
  assert.ok(cards[0].subText.indexOf('OSS_UPLOAD_FAILED') !== -1, cards[0].subText)
})

test('decorateHistoryCards：session 折叠卡补聚合副标题与 dotKind', function () {
  const queue = [
    item('c1', 'verified', { session_id: 's1', chunk_seq: 1, duration_seconds: 600 }),
    item('c2', 'upload_failed', { session_id: 's1', chunk_seq: 2, duration_seconds: 600 }),
  ]
  const cards = view.decorateHistoryCards(view.buildCards(queue), Date.now())
  assert.strictEqual(cards[0].type, 'session')
  assert.strictEqual(cards[0].dotKind, 'fail')
  assert.strictEqual(cards[0].title, '长录音 · 2 段')
  assert.ok(cards[0].subText.indexOf('失败') !== -1, cards[0].subText)
})

// ── queue_runtime ────────────────────────────────────────────────────────────
function makeFaultInjection() {
  return {
    FAULT_FC_URL_BROKEN: 'mock-fc-url-broken',
    FAULT_NETWORK_OFFLINE: 'mock-network-offline',
    FAULT_VERIFY_FAIL: 'mock-verify-fail',
    isDevEnv: function () { return false },
    isEnabled: function () { return false },
    loadFaults: function () { return {} },
  }
}

function makeWx(storage, scenario) {
  scenario = scenario || {}
  return {
    getStorageSync: function (k) {
      return Object.prototype.hasOwnProperty.call(storage, k) ? storage[k] : ''
    },
    setStorageSync: function (k, v) { storage[k] = v },
    getNetworkType: function (opt) { opt.success({ networkType: scenario.network || 'wifi' }) },
    login: function (opt) { opt.success({ code: 'c1' }) },
    request: function (opt) { opt.success({ statusCode: scenario.fcStatus || 200, data: scenario.fcData }) },
    uploadFile: function (opt) {
      opt.success({ statusCode: scenario.ossStatus || 200, data: '' })
      return { onProgressUpdate: function () {} }
    },
    getFileSystemManager: function () {
      return { unlink: function (o) { if (o && o.success) { o.success() } } }
    },
    showModal: function (opt) { if (opt && opt.success) { opt.success({ confirm: true }) } },
  }
}

const FULL_CRED = {
  access_key_id: 'STS.id',
  access_key_secret: 'secret',
  security_token: 'token',
  expiration: '2026-07-02T11:00:00Z',
  bucket: 'soniscope-audio',
  endpoint: 'oss-cn-beijing.aliyuncs.com',
  object_key: 'recordings/2026-07-02/20260702T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE.wav',
}

function config() {
  return {
    ENV: 'development',
    OSS_REGION: 'cn-beijing',
    OSS_UPLOAD_URL: 'https://soniscope-audio.oss-cn-beijing.aliyuncs.com',
    FC_ISSUE_CREDENTIAL_URL: 'https://fc-issue.example',
    FC_VERIFY_UPLOAD_URL: 'https://fc-verify.example',
  }
}

function noopLogger() {
  return { info: function () {}, warn: function () {}, error: function () {} }
}

function queuedItem() {
  return {
    fragmentId: '20260702T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE',
    status: uploadQueue.STATUS_QUEUED,
    statusText: STATUS_TEXT[uploadQueue.STATUS_QUEUED],
    tempFilePath: 'wxfile://tmp/rec.mp3',
    manifest: { audio: { size_bytes: 4096 } },
    ossMetadata: { 'x-oss-meta-sha256': 'abc' },
  }
}

test('queue_runtime.drive：queued → OSS 2xx → verified 落盘并回调渲染', async function () {
  const storage = {}
  storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY] = [queuedItem()]
  const wx = makeWx(storage, { fcData: FULL_CRED, verifyData: { verified: true, size: 4096 } })
  // verify 走 request：需返回 verified；上面 request 用 fcData，这里覆盖为 verify 场景。
  wx.request = function (opt) {
    if (opt.url.indexOf('verify') !== -1) {
      opt.success({ statusCode: 200, data: { verified: true, etag: 'E', size: 4096 } })
    } else {
      opt.success({ statusCode: 200, data: FULL_CRED })
    }
  }
  let rendered = 0
  const rt = createQueueRuntime({
    wx: wx, config: config(), logger: noopLogger(), faultInjection: makeFaultInjection(),
    onChange: function () { rendered += 1 },
  })
  await rt.drive()
  const q = storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY]
  assert.strictEqual(q[0].status, uploadQueue.STATUS_VERIFIED)
  assert.ok(rendered > 0, 'onChange 应被回调驱动渲染')
})

test('queue_runtime：缺 getNetworkType（如测试环境）时视为离线，不触发上传', async function () {
  const storage = {}
  storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY] = [queuedItem()]
  const wx = makeWx(storage, {})
  delete wx.getNetworkType
  const rt = createQueueRuntime({
    wx: wx, config: config(), logger: noopLogger(), faultInjection: makeFaultInjection(),
  })
  await rt.drive()
  // 仍为 queued（未上传）。
  assert.strictEqual(storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY][0].status, uploadQueue.STATUS_QUEUED)
})

test('queue_runtime.manualRetry：重置状态并重跑上传', async function () {
  const storage = {}
  const failed = Object.assign(queuedItem(), { status: uploadQueue.STATUS_UPLOAD_FAILED, errorCode: 'X' })
  storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY] = [failed]
  const wx = makeWx(storage, {})
  wx.request = function (opt) {
    if (opt.url.indexOf('verify') !== -1) {
      opt.success({ statusCode: 200, data: { verified: true, size: 4096 } })
    } else {
      opt.success({ statusCode: 200, data: FULL_CRED })
    }
  }
  const rt = createQueueRuntime({
    wx: wx, config: config(), logger: noopLogger(), faultInjection: makeFaultInjection(),
  })
  await rt.manualRetry(failed.fragmentId)
  assert.strictEqual(storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY][0].status, uploadQueue.STATUS_VERIFIED)
})

test('queue_runtime.remove：删除项并回调渲染', function () {
  const storage = {}
  storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY] = [Object.assign(queuedItem(), { status: uploadQueue.STATUS_VERIFIED })]
  const wx = makeWx(storage, {})
  let rendered = 0
  const rt = createQueueRuntime({
    wx: wx, config: config(), logger: noopLogger(), faultInjection: makeFaultInjection(),
    onChange: function () { rendered += 1 },
  })
  rt.remove('20260702T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE')
  assert.strictEqual(storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY].length, 0)
  assert.ok(rendered > 0)
})
