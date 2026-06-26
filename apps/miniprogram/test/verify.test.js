// US-018 单元测试：上传后 verify 回执、48 小时本地保留与手动删除二次确认。
// 纯逻辑 verify / retention 用注入 deps 验证；上传列表页用 node Page harness + mock wx 端到端验证。

const test = require('node:test')
const assert = require('node:assert')
const path = require('node:path')

const verify = require('../utils/verify')
const retention = require('../utils/retention')

const UPLOADS_PAGE = path.resolve(__dirname, '../pages/uploads/uploads.js')

const HOUR_MS = 60 * 60 * 1000

function makeItem() {
  return {
    fragmentId: '20260627T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE',
    status: 'pending_verify',
    statusText: '待 verify',
    tempFilePath: 'wxfile://tmp/rec.mp3',
    manifest: { audio: { size_bytes: 4096 } },
  }
}

// ── 纯逻辑：classifyVerifyResponse ────────────────────────────────────────────
test('classifyVerifyResponse：200 verified:true → verified（AC#2）', function () {
  const r = verify.classifyVerifyResponse(200, { verified: true, etag: 'E', size: 4096 })
  assert.strictEqual(r.kind, 'verified')
  assert.strictEqual(r.size, 4096)
})

test('classifyVerifyResponse：200 verified:false → unverified + reason（AC#3）', function () {
  const a = verify.classifyVerifyResponse(200, { verified: false, reason: 'OBJECT_NOT_FOUND' })
  assert.strictEqual(a.kind, 'unverified')
  assert.strictEqual(a.reason, 'OBJECT_NOT_FOUND')
  const b = verify.classifyVerifyResponse(200, {
    verified: false,
    reason: 'SIZE_MISMATCH',
    actual_size: 100,
  })
  assert.strictEqual(b.reason, 'SIZE_MISMATCH')
  assert.strictEqual(b.actualSize, 100)
})

test('classifyVerifyResponse：5xx → retryable，4xx → fatal（AC#4 / AGENTS）', function () {
  assert.strictEqual(verify.classifyVerifyResponse(503, {}).kind, 'retryable')
  assert.strictEqual(verify.classifyVerifyResponse(500, {}).kind, 'retryable')
  const f = verify.classifyVerifyResponse(401, { error: 'INVALID_CODE' })
  assert.strictEqual(f.kind, 'fatal')
  assert.strictEqual(f.errorCode, 'INVALID_CODE')
})

test('verify 退避延时为 5s/15s/45s 最多 3 次', function () {
  assert.deepStrictEqual(verify.VERIFY_RETRY_DELAYS_MS, [5000, 15000, 45000])
  assert.strictEqual(verify.MAX_VERIFY_RETRIES, 3)
})

// ── verifyFragment：注入 deps ─────────────────────────────────────────────────
function baseDeps(overrides) {
  const statuses = []
  const deps = {
    now: () => 1000,
    login: async () => 'wx-code-1',
    requestVerify: async () => ({ statusCode: 200, data: { verified: true, etag: 'E', size: 4096 } }),
    wait: async () => {},
    onStatus: (s, extra) => statuses.push(Object.assign({ status: s }, extra)),
  }
  return { deps: Object.assign(deps, overrides || {}), statuses: statuses }
}

test('verifyFragment：verified:true → verified + verifiedAt（AC#2）', async function () {
  const { deps, statuses } = baseDeps({ now: () => 123456 })
  const res = await verify.verifyFragment(makeItem(), deps)
  assert.strictEqual(res.status, 'verified')
  assert.strictEqual(res.verifiedAt, 123456)
  assert.strictEqual(statuses[statuses.length - 1].status, 'verified')
  assert.strictEqual(statuses[statuses.length - 1].verifiedAt, 123456)
})

test('verifyFragment：OBJECT_NOT_FOUND → 待人工重传 + reason（AC#3）', async function () {
  const { deps } = baseDeps({
    requestVerify: async () => ({ statusCode: 200, data: { verified: false, reason: 'OBJECT_NOT_FOUND' } }),
  })
  const res = await verify.verifyFragment(makeItem(), deps)
  assert.strictEqual(res.status, 'manual_retry')
  assert.strictEqual(res.reason, 'OBJECT_NOT_FOUND')
})

test('verifyFragment：SIZE_MISMATCH → 待人工重传 + reason（AC#3）', async function () {
  const { deps } = baseDeps({
    requestVerify: async () => ({ statusCode: 200, data: { verified: false, reason: 'SIZE_MISMATCH' } }),
  })
  const res = await verify.verifyFragment(makeItem(), deps)
  assert.strictEqual(res.status, 'manual_retry')
  assert.strictEqual(res.reason, 'SIZE_MISMATCH')
})

test('verifyFragment：5xx 退避重试 3 次后待人工 verify（AC#4）', async function () {
  let calls = 0
  const waits = []
  const { deps } = baseDeps({
    requestVerify: async () => { calls += 1; return { statusCode: 503, data: {} } },
    wait: async (ms) => { waits.push(ms) },
  })
  const res = await verify.verifyFragment(makeItem(), deps)
  assert.strictEqual(res.status, 'manual_verify')
  assert.strictEqual(res.errorCode, 'VERIFY_FAILED')
  assert.strictEqual(calls, 4, '初次 + 3 次重试')
  assert.deepStrictEqual(waits, [5000, 15000, 45000])
})

test('verifyFragment：网络错误（requestVerify 抛异常）也走退避重试（AC#4）', async function () {
  let calls = 0
  const { deps } = baseDeps({
    requestVerify: async () => { calls += 1; throw new Error('network') },
    wait: async () => {},
  })
  const res = await verify.verifyFragment(makeItem(), deps)
  assert.strictEqual(res.status, 'manual_verify')
  assert.strictEqual(calls, 4)
})

test('verifyFragment：第 3 次重试成功 → verified', async function () {
  let calls = 0
  const { deps } = baseDeps({
    requestVerify: async () => {
      calls += 1
      return calls < 3
        ? { statusCode: 500, data: {} }
        : { statusCode: 200, data: { verified: true, size: 4096 } }
    },
    wait: async () => {},
  })
  const res = await verify.verifyFragment(makeItem(), deps)
  assert.strictEqual(res.status, 'verified')
})

test('verifyFragment：4xx 立即待人工 verify，不重试', async function () {
  let calls = 0
  const { deps } = baseDeps({
    requestVerify: async () => { calls += 1; return { statusCode: 401, data: { error: 'INVALID_CODE' } } },
  })
  const res = await verify.verifyFragment(makeItem(), deps)
  assert.strictEqual(res.status, 'manual_verify')
  assert.strictEqual(res.errorCode, 'INVALID_CODE')
  assert.strictEqual(calls, 1, '4xx 不重试')
})

// ── 纯逻辑：retention（48 小时保留 / 永不自动删 / 删除确认）─────────────────────
test('canAutoDelete：verified 且 >= 48h → 可删（AC#5）', function () {
  const item = { status: 'verified', verifiedAt: 0 }
  assert.strictEqual(retention.canAutoDelete(item, 48 * HOUR_MS), true)
  assert.strictEqual(retention.canAutoDelete(item, 49 * HOUR_MS), true)
})

test('canAutoDelete：verified 但 < 48h → 不删（AC#5）', function () {
  const item = { status: 'verified', verifiedAt: 0 }
  assert.strictEqual(retention.canAutoDelete(item, 47 * HOUR_MS), false)
})

test('canAutoDelete：未 verified 即使超过 7 天也不删（AC#6）', function () {
  const eightDays = 8 * 24 * HOUR_MS
  assert.strictEqual(retention.canAutoDelete({ status: 'manual_retry', verifiedAt: 0 }, eightDays), false)
  assert.strictEqual(retention.canAutoDelete({ status: 'manual_verify', verifiedAt: 0 }, eightDays), false)
  assert.strictEqual(retention.canAutoDelete({ status: 'pending_verify' }, eightDays), false)
})

test('canAutoDelete：已清理（localDeleted）或缺 verifiedAt → 不删', function () {
  assert.strictEqual(
    retention.canAutoDelete({ status: 'verified', verifiedAt: 0, localDeleted: true }, 99 * HOUR_MS),
    false,
  )
  assert.strictEqual(retention.canAutoDelete({ status: 'verified' }, 99 * HOUR_MS), false)
})

test('selectAutoDeletable：只选 verified 且超 48h 的项', function () {
  const queue = [
    { fragmentId: 'a', status: 'verified', verifiedAt: 0 },
    { fragmentId: 'b', status: 'verified', verifiedAt: 47 * HOUR_MS },
    { fragmentId: 'c', status: 'manual_retry', verifiedAt: 0 },
  ]
  const out = retention.selectAutoDeletable(queue, 48 * HOUR_MS)
  assert.deepStrictEqual(out.map((it) => it.fragmentId), ['a'])
})

test('needsDeleteConfirmation：非 verified 需确认，verified 直接删（AC#7）', function () {
  assert.strictEqual(retention.needsDeleteConfirmation({ status: 'manual_retry' }), true)
  assert.strictEqual(retention.needsDeleteConfirmation({ status: 'pending_verify' }), true)
  assert.strictEqual(retention.needsDeleteConfirmation({ status: 'verified' }), false)
})

// ── 上传列表页集成（Page harness + mock wx）──────────────────────────────────
function makeWx(storage, scenario) {
  const sc = scenario || {}
  return {
    _unlinked: [],
    _modalShown: 0,
    getStorageSync: (k) =>
      Object.prototype.hasOwnProperty.call(storage, k) ? storage[k] : '',
    setStorageSync: (k, v) => { storage[k] = v },
    getNetworkType: (opt) => opt.success({ networkType: sc.network || 'wifi' }),
    login: (opt) => opt.success({ code: 'c1' }),
    request: function (opt) {
      // 路由 verify-upload 请求；其余（issue-credential）走 STS 分支。
      if (String(opt.url).indexOf('verify-upload') !== -1) {
        opt.success({ statusCode: sc.verifyStatus || 200, data: sc.verifyData })
      } else {
        opt.success({ statusCode: sc.fcStatus || 200, data: sc.fcData })
      }
    },
    uploadFile: function (opt) {
      opt.success({ statusCode: sc.ossStatus || 200, data: '' })
      return { onProgressUpdate: function () {} }
    },
    getFileSystemManager: function () {
      const wx = this
      return {
        unlink: function (opt) {
          wx._unlinked.push(opt.filePath)
          if (opt.success) opt.success()
        },
      }
    },
    showModal: function (opt) {
      this._modalShown += 1
      opt.success({ confirm: !!(scenario && scenario.confirmDelete) })
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

function pendingVerifyItem() {
  return {
    fragmentId: '20260627T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE',
    status: 'pending_verify',
    statusText: '待 verify',
    tempFilePath: 'wxfile://tmp/rec.mp3',
    manifest: { audio: { size_bytes: 4096 } },
  }
}

test('uploads 页：pending_verify → 上传成功（verified）并落盘（AC#1/#2）', async function () {
  const storage = { 'soniscope:upload_queue': [pendingVerifyItem()] }
  const wx = makeWx(storage, { verifyData: { verified: true, etag: 'E', size: 4096 } })
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  await inst._processVerifyQueue()
  const persisted = storage['soniscope:upload_queue'][0]
  assert.strictEqual(persisted.status, 'verified')
  assert.strictEqual(persisted.statusText, '上传成功')
  assert.ok(persisted.verifiedAt > 0, '应写入 verified_at')
})

test('uploads 页：重新 verify 删对象后 → 待人工重传 + OBJECT_NOT_FOUND（AC#9）', async function () {
  const storage = { 'soniscope:upload_queue': [pendingVerifyItem()] }
  const wx = makeWx(storage, { verifyData: { verified: false, reason: 'OBJECT_NOT_FOUND' } })
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  await inst.onTapReVerify({ currentTarget: { dataset: { fid: pendingVerifyItem().fragmentId } } })
  const persisted = storage['soniscope:upload_queue'][0]
  assert.strictEqual(persisted.status, 'manual_retry')
  assert.strictEqual(persisted.statusText, '待人工重传')
  assert.strictEqual(persisted.reason, 'OBJECT_NOT_FOUND')
})

test('uploads 页 _autoCleanup：verified >= 48h 删本地缓存、保留记录（AC#5）', function () {
  const old = Object.assign(pendingVerifyItem(), {
    status: 'verified',
    statusText: '上传成功',
    verifiedAt: 1, // 远早于现在，必然超过 48h
  })
  const storage = { 'soniscope:upload_queue': [old] }
  const wx = makeWx(storage, {})
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  inst._autoCleanup()
  assert.deepStrictEqual(wx._unlinked, ['wxfile://tmp/rec.mp3'], '应 unlink 本地文件')
  const persisted = storage['soniscope:upload_queue'][0]
  assert.strictEqual(persisted.localDeleted, true, '标记本地已清理')
  assert.strictEqual(persisted.status, 'verified', '队列记录保留')
})

test('uploads 页 _autoCleanup：verified < 48h 不删（AC#5/#6）', function () {
  const recent = Object.assign(pendingVerifyItem(), {
    status: 'verified',
    statusText: '上传成功',
    verifiedAt: Date.now(),
  })
  const storage = { 'soniscope:upload_queue': [recent] }
  const wx = makeWx(storage, {})
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  inst._autoCleanup()
  assert.deepStrictEqual(wx._unlinked, [])
  assert.ok(!storage['soniscope:upload_queue'][0].localDeleted)
})

test('uploads 页 _autoCleanup：未 verified 即使超 7 天也不删（AC#6）', function () {
  const stale = Object.assign(pendingVerifyItem(), { status: 'manual_retry', verifiedAt: 1 })
  const storage = { 'soniscope:upload_queue': [stale] }
  const wx = makeWx(storage, {})
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  inst._autoCleanup()
  assert.deepStrictEqual(wx._unlinked, [])
})

test('uploads 页：手动删除未 verified → 二次确认，确认后删除（AC#7）', function () {
  const item = Object.assign(pendingVerifyItem(), { status: 'manual_retry' })
  const storage = { 'soniscope:upload_queue': [item] }
  const wx = makeWx(storage, { confirmDelete: true })
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  inst.onTapDelete({ currentTarget: { dataset: { fid: item.fragmentId } } })
  assert.strictEqual(wx._modalShown, 1, '应弹出二次确认')
  assert.strictEqual(storage['soniscope:upload_queue'].length, 0, '确认后删除记录')
  assert.ok(wx._unlinked.indexOf('wxfile://tmp/rec.mp3') !== -1)
})

test('uploads 页：手动删除二次确认取消 → 不删除（AC#7）', function () {
  const item = Object.assign(pendingVerifyItem(), { status: 'manual_retry' })
  const storage = { 'soniscope:upload_queue': [item] }
  const wx = makeWx(storage, { confirmDelete: false })
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  inst.onTapDelete({ currentTarget: { dataset: { fid: item.fragmentId } } })
  assert.strictEqual(wx._modalShown, 1)
  assert.strictEqual(storage['soniscope:upload_queue'].length, 1, '取消后保留记录')
})

test('uploads 页：手动删除 verified 记录 → 无需确认直接删', function () {
  const item = Object.assign(pendingVerifyItem(), { status: 'verified', verifiedAt: Date.now() })
  const storage = { 'soniscope:upload_queue': [item] }
  const wx = makeWx(storage, {})
  const inst = loadUploadsPage(wx)
  inst.onLoad()
  inst.onTapDelete({ currentTarget: { dataset: { fid: item.fragmentId } } })
  assert.strictEqual(wx._modalShown, 0, 'verified 不弹确认')
  assert.strictEqual(storage['soniscope:upload_queue'].length, 0)
})
