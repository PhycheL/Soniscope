// US-019 单元测试：上传列表页八种状态、离线积压提示与长录音折叠展示。
// 纯逻辑 uploads_view 直接验证；上传列表页用 node Page harness + mock wx 验证手动重传与渲染。

const test = require('node:test')
const assert = require('node:assert')
const path = require('node:path')

const view = require('../utils/uploads_view')
const { STATUS_TEXT } = require('../utils/upload_queue')

const UPLOADS_PAGE = path.resolve(__dirname, '../pages/uploads/uploads.js')
const HOUR_MS = 60 * 60 * 1000

const FULL_CRED = {
  access_key_id: 'STS.id',
  access_key_secret: 'secret',
  security_token: 'token',
  expiration: '2026-06-27T11:00:00Z',
  bucket: 'soniscope-audio',
  endpoint: 'oss-cn-beijing.aliyuncs.com',
  object_key: 'recordings/2026-06-27/20260627T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE.wav',
}

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

// ── AC#1/#9：八种状态中文文案 ────────────────────────────────────────────────
test('八种状态中文文案齐全（AC#1/#9）', function () {
  assert.strictEqual(STATUS_TEXT.draft, '草稿')
  assert.strictEqual(STATUS_TEXT.queued, '待上传')
  assert.strictEqual(STATUS_TEXT.uploading, '上传中')
  assert.strictEqual(STATUS_TEXT.pending_verify, '待 verify')
  assert.strictEqual(STATUS_TEXT.verified, '上传成功')
  assert.strictEqual(STATUS_TEXT.upload_failed, '上传失败')
  assert.strictEqual(STATUS_TEXT.manual_retry, '待人工重传')
  assert.strictEqual(STATUS_TEXT.manual_verify, '待人工 verify')
})

// ── 状态归类 ─────────────────────────────────────────────────────────────────
test('canManualRetry：仅 upload_failed / manual_retry（AC#2/#3）', function () {
  assert.strictEqual(view.canManualRetry('upload_failed'), true)
  assert.strictEqual(view.canManualRetry('manual_retry'), true)
  assert.strictEqual(view.canManualRetry('manual_verify'), false)
  assert.strictEqual(view.canManualRetry('queued'), false)
  assert.strictEqual(view.canManualRetry('verified'), false)
})

test('canReVerify：pending_verify / manual_verify / verified', function () {
  assert.strictEqual(view.canReVerify('pending_verify'), true)
  assert.strictEqual(view.canReVerify('manual_verify'), true)
  assert.strictEqual(view.canReVerify('verified'), true)
  assert.strictEqual(view.canReVerify('queued'), false)
})

test('isFailed / isBacklog 归类正确', function () {
  assert.strictEqual(view.isFailed(item('a', 'manual_retry')), true)
  assert.strictEqual(view.isFailed(item('a', 'verified')), false)
  assert.strictEqual(view.isBacklog(item('a', 'queued')), true)
  assert.strictEqual(view.isBacklog(item('a', 'manual_verify')), true)
  assert.strictEqual(view.isBacklog(item('a', 'uploading')), false)
  assert.strictEqual(view.isBacklog(item('a', 'verified')), false)
})

// ── AC#4：顶部积压提示 ───────────────────────────────────────────────────────
test('countBacklog：按单 chunk 计数待上传/失败/待人工重传/待人工 verify（AC#4）', function () {
  const queue = [
    item('a', 'queued'),
    item('b', 'upload_failed'),
    item('c', 'manual_retry'),
    item('d', 'manual_verify'),
    item('e', 'uploading'),
    item('f', 'verified'),
    item('g', 'pending_verify'),
  ]
  assert.strictEqual(view.countBacklog(queue), 4)
})

test('hoursBetween：向下取整、不为负', function () {
  assert.strictEqual(view.hoursBetween(0, 3 * HOUR_MS + 30 * 60 * 1000), 3)
  assert.strictEqual(view.hoursBetween(5 * HOUR_MS, 0), 0)
  assert.strictEqual(view.hoursBetween(null, 99 * HOUR_MS), 0)
})

test('buildBanner：有积压 → 显示「未上传 N 条，距离最早录音已 X 小时」（AC#4）', function () {
  const now = Date.parse('2026-06-27T12:00:00Z')
  const queue = [
    item('a', 'queued', { recorded_at: '2026-06-27T09:00:00Z' }),
    item('b', 'manual_retry', { recorded_at: '2026-06-27T10:00:00Z' }),
    item('c', 'verified', { recorded_at: '2026-06-27T05:00:00Z' }),
  ]
  const banner = view.buildBanner(queue, now)
  assert.strictEqual(banner.visible, true)
  assert.strictEqual(banner.count, 2)
  assert.strictEqual(banner.hours, 3, '最早积压 09:00 距 12:00 为 3 小时（verified 05:00 不计）')
  assert.strictEqual(banner.text, '未上传 2 条，距离最早录音已 3 小时')
})

test('buildBanner：无积压 → 不显示（AC#4）', function () {
  const queue = [item('a', 'verified'), item('b', 'pending_verify')]
  const banner = view.buildBanner(queue, Date.now())
  assert.strictEqual(banner.visible, false)
  assert.strictEqual(banner.count, 0)
})

// ── AC#6/#7/#8：长录音折叠卡片 ───────────────────────────────────────────────
test('buildCards：单条录音 → single 卡片', function () {
  const queue = [item('a', 'queued', { session_id: 's1', chunk_seq: 1 })]
  const cards = view.buildCards(queue)
  assert.strictEqual(cards.length, 1)
  assert.strictEqual(cards[0].type, 'single')
  assert.strictEqual(cards[0].fragmentId, 'a')
})

test('buildCards：同 session 多 chunk → 折叠 session 卡片，按 chunk_seq 排序（AC#6/#8）', function () {
  const queue = [
    item('c2', 'verified', { session_id: 's1', chunk_seq: 2, duration_seconds: 600 }),
    item('c1', 'verified', { session_id: 's1', chunk_seq: 1, duration_seconds: 600 }),
    item('c3', 'verified', { session_id: 's1', chunk_seq: 3, duration_seconds: 300 }),
  ]
  const cards = view.buildCards(queue)
  assert.strictEqual(cards.length, 1)
  const card = cards[0]
  assert.strictEqual(card.type, 'session')
  assert.strictEqual(card.chunkCount, 3)
  assert.deepStrictEqual(
    card.chunks.map((c) => c.chunkSeq),
    [1, 2, 3],
    '按 chunk_seq 升序',
  )
  assert.strictEqual(card.summaryText, '25:00 · 3 段', '总时长 1500s → 25:00 · 3 段（AC#6）')
})

test('buildCards：全部 chunk verified → 聚合「已完成」（AC#7）', function () {
  const queue = [
    item('c1', 'verified', { session_id: 's1', chunk_seq: 1 }),
    item('c2', 'verified', { session_id: 's1', chunk_seq: 2 }),
  ]
  const card = view.buildCards(queue)[0]
  assert.strictEqual(card.aggregateKind, 'done')
  assert.strictEqual(card.aggregateText, '已完成')
})

test('buildCards：任一 chunk 失败 → 聚合「X / N 失败」（AC#7）', function () {
  const queue = [
    item('c1', 'verified', { session_id: 's1', chunk_seq: 1 }),
    item('c2', 'manual_retry', { session_id: 's1', chunk_seq: 2 }),
    item('c3', 'verified', { session_id: 's1', chunk_seq: 3 }),
  ]
  const card = view.buildCards(queue)[0]
  assert.strictEqual(card.aggregateKind, 'failed')
  assert.strictEqual(card.aggregateText, '1 / 3 失败')
})

test('buildCards：进行中 → 聚合「M / N 已完成」', function () {
  const queue = [
    item('c1', 'verified', { session_id: 's1', chunk_seq: 1 }),
    item('c2', 'uploading', { session_id: 's1', chunk_seq: 2 }),
  ]
  const card = view.buildCards(queue)[0]
  assert.strictEqual(card.aggregateKind, 'progress')
  assert.strictEqual(card.aggregateText, '1 / 2 已完成')
})

test('buildCards：不同 session 各自成卡，保持首次出现顺序', function () {
  const queue = [
    item('a', 'queued', { session_id: 's1', chunk_seq: 1 }),
    item('b1', 'queued', { session_id: 's2', chunk_seq: 1 }),
    item('b2', 'queued', { session_id: 's2', chunk_seq: 2 }),
    item('c', 'queued', {}),
  ]
  const cards = view.buildCards(queue)
  assert.deepStrictEqual(
    cards.map((c) => c.type),
    ['single', 'session', 'single'],
  )
})

// ── 上传列表页集成（Page harness + mock wx）──────────────────────────────────
function makeWx(storage, scenario) {
  const sc = scenario || {}
  return {
    _unlinked: [],
    getStorageSync: (k) =>
      Object.prototype.hasOwnProperty.call(storage, k) ? storage[k] : '',
    setStorageSync: (k, v) => { storage[k] = v },
    getNetworkType: (opt) => opt.success({ networkType: sc.network || 'wifi' }),
    login: (opt) => opt.success({ code: 'c1' }),
    request: function (opt) {
      if (String(opt.url).indexOf('verify-upload') !== -1) {
        opt.success({ statusCode: sc.verifyStatus || 200, data: sc.verifyData || { verified: true, etag: 'E', size: 4096 } })
      } else {
        opt.success({ statusCode: sc.fcStatus || 200, data: sc.fcData || FULL_CRED })
      }
    },
    uploadFile: function (opt) {
      opt.success({ statusCode: sc.ossStatus || 200, data: '' })
      return { onProgressUpdate: function () {} }
    },
    getFileSystemManager: function () {
      const self = this
      return { unlink: function (o) { self._unlinked.push(o.filePath); if (o.success) o.success() } }
    },
    showModal: function (opt) { opt.success({ confirm: true }) },
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

function failedItem() {
  return {
    fragmentId: '20260627T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE',
    status: 'manual_retry',
    statusText: '待人工重传',
    errorCode: 'OSS_UPLOAD_FAILED',
    tempFilePath: 'wxfile://tmp/rec.mp3',
    manifest: { audio: { size_bytes: 4096 }, recorded_at: '2026-06-27T10:00:00Z' },
    ossMetadata: { 'x-oss-meta-sha256': 'abc' },
  }
}

test('uploads 页：手动重传重置错误码并重跑 STS+OSS+verify → 上传成功（AC#2/#3）', async function () {
  const storage = { 'soniscope:upload_queue': [failedItem()] }
  const wx = makeWx(storage, {})
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  await inst.onTapManualRetry({ currentTarget: { dataset: { fid: failedItem().fragmentId } } })
  const persisted = storage['soniscope:upload_queue'][0]
  assert.strictEqual(persisted.status, 'verified', '重传后完整跑到 verified')
  assert.strictEqual(persisted.errorCode || '', '', '错误码已重置')
})

test('uploads 页：onShow 渲染折叠卡片与积压 banner（AC#4/#6）', function () {
  const queue = [
    {
      fragmentId: 'c1',
      status: 'queued',
      manifest: { session_id: 's1', chunk_seq: 1, duration_seconds: 600, recorded_at: '2026-06-27T10:00:00Z' },
      durationSeconds: 600,
    },
    {
      fragmentId: 'c2',
      status: 'queued',
      manifest: { session_id: 's1', chunk_seq: 2, duration_seconds: 600, recorded_at: '2026-06-27T10:10:00Z' },
      durationSeconds: 600,
    },
  ]
  const storage = { 'soniscope:upload_queue': queue }
  const wx = makeWx(storage, { network: 'none' }) // 离线：不触发上传，仅验证渲染
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  inst._loadQueue()
  assert.strictEqual(inst.data.cards.length, 1)
  assert.strictEqual(inst.data.cards[0].type, 'session')
  assert.strictEqual(inst.data.cards[0].chunkCount, 2)
  assert.strictEqual(inst.data.banner.visible, true)
  assert.strictEqual(inst.data.banner.count, 2)
})

test('uploads 页：onToggleSession 切换展开状态（AC#8）', function () {
  const storage = { 'soniscope:upload_queue': [] }
  const wx = makeWx(storage, {})
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  inst.onToggleSession({ currentTarget: { dataset: { sid: 's1' } } })
  assert.strictEqual(inst.data.expanded.s1, true)
  inst.onToggleSession({ currentTarget: { dataset: { sid: 's1' } } })
  assert.strictEqual(inst.data.expanded.s1, false)
})
