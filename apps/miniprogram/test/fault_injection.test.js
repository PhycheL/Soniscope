// US-020 单元测试：开发者故障注入菜单。
// 纯逻辑（fault_injection）直接断言；dev 菜单页与 uploads 页请求适配器用 node Page harness +
// mock wx 端到端验证三个开关的效果与 ENV 门控。

const test = require('node:test')
const assert = require('node:assert')
const path = require('node:path')

const fi = require('../utils/fault_injection')

const DEV_PAGE = path.resolve(__dirname, '../pages/dev/dev.js')
const UPLOADS_PAGE = path.resolve(__dirname, '../pages/uploads/uploads.js')
const CONFIG = path.resolve(__dirname, '../config.js')

const QUEUE_KEY = 'soniscope:upload_queue'
const FAULT_KEY = 'soniscope:fault_injection'

// ── 纯逻辑 ────────────────────────────────────────────────────────────────────
test('isDevEnv：production 为 false，其余为 true（AC#1）', function () {
  assert.strictEqual(fi.isDevEnv('production'), false)
  assert.strictEqual(fi.isDevEnv('development'), true)
  assert.strictEqual(fi.isDevEnv('staging'), true)
  assert.strictEqual(fi.isDevEnv(undefined), true)
})

test('三个开关名与 tech-spec §6.1 一致', function () {
  assert.strictEqual(fi.FAULT_FC_URL_BROKEN, 'mock-fc-url-broken')
  assert.strictEqual(fi.FAULT_NETWORK_OFFLINE, 'mock-network-offline')
  assert.strictEqual(fi.FAULT_VERIFY_FAIL, 'mock-verify-fail')
  assert.deepStrictEqual(fi.FAULT_NAMES, [
    'mock-fc-url-broken',
    'mock-network-offline',
    'mock-verify-fail',
  ])
})

test('normalizeFaults：默认全关、未知键丢弃、布尔化', function () {
  assert.deepStrictEqual(fi.normalizeFaults(null), {
    'mock-fc-url-broken': false,
    'mock-network-offline': false,
    'mock-verify-fail': false,
  })
  const norm = fi.normalizeFaults({ 'mock-fc-url-broken': 1, unknown: true })
  assert.strictEqual(norm['mock-fc-url-broken'], true)
  assert.strictEqual(norm['mock-network-offline'], false)
  assert.ok(!('unknown' in norm))
})

test('isEnabled / setFault / toggleFault：不可变更新', function () {
  let faults = fi.normalizeFaults({})
  assert.strictEqual(fi.isEnabled(faults, 'mock-fc-url-broken'), false)
  const set = fi.setFault(faults, 'mock-verify-fail', true)
  assert.strictEqual(fi.isEnabled(set, 'mock-verify-fail'), true)
  assert.strictEqual(fi.isEnabled(faults, 'mock-verify-fail'), false, '原对象不被修改')
  const toggled = fi.toggleFault(set, 'mock-verify-fail')
  assert.strictEqual(fi.isEnabled(toggled, 'mock-verify-fail'), false)
  // 未知开关不产生副作用。
  assert.deepStrictEqual(fi.toggleFault(faults, 'nope'), fi.normalizeFaults({}))
})

test('buildSwitchViews：含 name/label/hint/enabled', function () {
  const views = fi.buildSwitchViews({ 'mock-network-offline': true })
  assert.strictEqual(views.length, 3)
  const offline = views.find((v) => v.name === 'mock-network-offline')
  assert.strictEqual(offline.enabled, true)
  assert.ok(offline.label && offline.hint)
  assert.strictEqual(views.find((v) => v.name === 'mock-fc-url-broken').enabled, false)
})

test('loadFaults：dev 读 storage，production 永远全关（AC#1 门控）', function () {
  const store = { [FAULT_KEY]: { 'mock-fc-url-broken': true } }
  const deps = (env) => ({
    env: env,
    getStorage: (k) => store[k],
    setStorage: (k, v) => {
      store[k] = v
    },
  })
  assert.strictEqual(fi.loadFaults(deps('development'))['mock-fc-url-broken'], true)
  assert.strictEqual(fi.loadFaults(deps('production'))['mock-fc-url-broken'], false)
})

test('saveFaults：production 忽略写入（AC#1 门控）', function () {
  const store = {}
  const deps = (env) => ({
    env: env,
    getStorage: (k) => store[k],
    setStorage: (k, v) => {
      store[k] = v
    },
  })
  fi.saveFaults(deps('production'), { 'mock-verify-fail': true })
  assert.ok(!(FAULT_KEY in store), 'production 不应落盘')
  fi.saveFaults(deps('development'), { 'mock-verify-fail': true })
  assert.strictEqual(store[FAULT_KEY]['mock-verify-fail'], true)
})

// ── Page harness ──────────────────────────────────────────────────────────────
function makeWx(storage) {
  return {
    _navigated: [],
    getStorageSync: (k) =>
      Object.prototype.hasOwnProperty.call(storage, k) ? storage[k] : '',
    setStorageSync: (k, v) => {
      storage[k] = v
    },
    getNetworkType: (opt) => opt.success({ networkType: 'wifi' }),
    login: (opt) => opt.success({ code: 'c1' }),
    navigateTo: function (opt) {
      this._navigated.push(opt.url)
    },
    request: function (opt) {
      if (String(opt.url).indexOf('verify-upload') !== -1) {
        opt.success({ statusCode: 200, data: { verified: true, etag: 'E', size: 4096 } })
      } else {
        // 默认返回完整 STS 凭证（7 字段）。
        opt.success({
          statusCode: 200,
          data: {
            access_key_id: 'AK',
            access_key_secret: 'SK',
            security_token: 'TK',
            expiration: '2026-06-27T10:00:00Z',
            bucket: 'soniscope-audio',
            endpoint: 'oss-cn-beijing.aliyuncs.com',
            object_key: 'recordings/2026-06-27/' + opt.data.fragment_id + '.wav',
          },
        })
      }
    },
    uploadFile: function (opt) {
      opt.success({ statusCode: 200, data: '' })
      return { onProgressUpdate: function () {} }
    },
    getFileSystemManager: function () {
      return { unlink: function (o) { if (o.success) o.success() } }
    },
  }
}

function loadPage(file, wx) {
  global.wx = wx
  let captured = null
  global.Page = function (opts) {
    captured = opts
  }
  delete require.cache[file]
  require(file)
  const inst = Object.assign({}, captured)
  inst.data = JSON.parse(JSON.stringify(captured.data))
  inst.setData = function (patch) {
    Object.assign(inst.data, patch)
  }
  return inst
}

function queuedItem() {
  return {
    fragmentId: '20260627T101500_dev01_01HZX3K8MN5PQR9TFB7AYWVCDE',
    status: 'queued',
    statusText: '待上传（离线排队）',
    tempFilePath: 'wxfile://tmp/rec.mp3',
    manifest: { audio: { size_bytes: 4096 } },
    ossMetadata: {},
  }
}

function pendingVerifyItem() {
  return Object.assign(queuedItem(), { status: 'pending_verify', statusText: '待 verify' })
}

// ── dev 菜单页 ────────────────────────────────────────────────────────────────
test('dev 页：dev 环境渲染三个开关并可运行时切换持久化（AC#5）', function () {
  const storage = {}
  const wx = makeWx(storage)
  const inst = loadPage(DEV_PAGE, wx)
  inst.onLoad()
  assert.strictEqual(inst.data.devEnv, true)
  assert.strictEqual(inst.data.switches.length, 3)
  inst.onToggleSwitch({ currentTarget: { dataset: { name: 'mock-fc-url-broken' } } })
  // 落盘且视图反映。
  assert.strictEqual(storage[FAULT_KEY]['mock-fc-url-broken'], true)
  assert.strictEqual(
    inst.data.switches.find((s) => s.name === 'mock-fc-url-broken').enabled,
    true,
  )
  // 再切回关闭。
  inst.onToggleSwitch({ currentTarget: { dataset: { name: 'mock-fc-url-broken' } } })
  assert.strictEqual(storage[FAULT_KEY]['mock-fc-url-broken'], false)
})

test('dev 页：production 环境菜单不可用、开关不可切换（AC#1）', function () {
  const config = require(CONFIG)
  const original = config.ENV
  config.ENV = 'production'
  try {
    const storage = {}
    const wx = makeWx(storage)
    const inst = loadPage(DEV_PAGE, wx)
    inst.onLoad()
    assert.strictEqual(inst.data.devEnv, false)
    assert.deepStrictEqual(inst.data.switches, [])
    inst.onToggleSwitch({ currentTarget: { dataset: { name: 'mock-fc-url-broken' } } })
    assert.ok(!(FAULT_KEY in storage), 'production 切换不落盘')
  } finally {
    config.ENV = original
    delete require.cache[CONFIG]
  }
})

// ── uploads 页：三个开关的效果 ────────────────────────────────────────────────
test('uploads 页：devMenuVisible 在 dev 环境为 true（AC#1 入口）', function () {
  const wx = makeWx({ [QUEUE_KEY]: [] })
  const inst = loadPage(UPLOADS_PAGE, wx)
  inst.onLoad()
  assert.strictEqual(inst.data.devMenuVisible, true)
  inst.onTapDevMenu()
  assert.deepStrictEqual(wx._navigated, ['/pages/dev/dev'])
})

test('uploads 页：mock-network-offline → queued 项保持待上传（AC#3）', async function () {
  const storage = { [QUEUE_KEY]: [queuedItem()], [FAULT_KEY]: { 'mock-network-offline': true } }
  const wx = makeWx(storage)
  const inst = loadPage(UPLOADS_PAGE, wx)
  inst.onLoad()
  await inst._processQueue()
  assert.strictEqual(storage[QUEUE_KEY][0].status, 'queued', '离线时不应上传')
})

test('uploads 页：关闭离线开关后自动上传（AC#3 恢复）', async function () {
  const storage = { [QUEUE_KEY]: [queuedItem()] }
  const wx = makeWx(storage)
  const inst = loadPage(UPLOADS_PAGE, wx)
  inst.onLoad()
  await inst._processQueue()
  assert.strictEqual(storage[QUEUE_KEY][0].status, 'pending_verify', '在线应上传成功进入待 verify')
})

test('uploads 页：mock-fc-url-broken → 上传进入待人工重传（AC#2）', async function () {
  const storage = { [QUEUE_KEY]: [queuedItem()], [FAULT_KEY]: { 'mock-fc-url-broken': true } }
  const wx = makeWx(storage)
  const inst = loadPage(UPLOADS_PAGE, wx)
  inst.onLoad()
  await inst._processQueue()
  const item = storage[QUEUE_KEY][0]
  assert.strictEqual(item.status, 'manual_retry')
  assert.strictEqual(item.statusText, '待人工重传')
})

test('uploads 页：关闭 fc-broken 后手动重传成功（AC#6 恢复）', async function () {
  const storage = {
    [QUEUE_KEY]: [Object.assign(queuedItem(), { status: 'manual_retry', errorCode: 'FC_UNREACHABLE' })],
  }
  const wx = makeWx(storage)
  const inst = loadPage(UPLOADS_PAGE, wx)
  inst.onLoad()
  await inst.onTapManualRetry({
    currentTarget: { dataset: { fid: queuedItem().fragmentId } },
  })
  assert.strictEqual(storage[QUEUE_KEY][0].status, 'verified')
})

test('uploads 页：mock-verify-fail → verify 返回 verified:false（AC#4）', async function () {
  const storage = { [QUEUE_KEY]: [pendingVerifyItem()], [FAULT_KEY]: { 'mock-verify-fail': true } }
  const wx = makeWx(storage)
  const inst = loadPage(UPLOADS_PAGE, wx)
  inst.onLoad()
  await inst._processVerifyQueue()
  const item = storage[QUEUE_KEY][0]
  assert.strictEqual(item.status, 'manual_retry', 'verified:false 业务原因 → 待人工重传')
  assert.strictEqual(item.reason, 'OBJECT_NOT_FOUND')
})
