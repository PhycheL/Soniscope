// US-015 单元测试：device_short_id 持久化、fragment_id 正则、同秒唯一性、
// manifest 草案字段完整性、原始音频 sha256 正确性，以及 OSS 用户自定义元数据。
//
// 纯函数（device / ulid / sha256 / audio）直接验证；Page 集成（保存并上传生成 fragment_id +
// sha256 + manifest）用与 draft_confirm.test.js 一致的手写 wx / Page mock 验证。
// 通过 make test（pytest）的 test_miniprogram_js.py 以子进程 `node --test` 纳入统一质量门。

const test = require('node:test')
const assert = require('node:assert')
const crypto = require('node:crypto')
const path = require('node:path')

const device = require('../utils/device')
const ulidMod = require('../utils/ulid')
const { sha256Hex } = require('../utils/sha256')
const audio = require('../utils/audio')
const uploadQueue = require('../utils/upload_queue')

const INDEX_PAGE = path.resolve(__dirname, '../pages/index/index.js')

// ---- device_short_id（AC#1）----

test('device_short_id 首次生成 4-8 字符并持久化，冷启动不变（AC#1）', function () {
  const store = {}
  const storage = {
    getStorageSync: function (k) {
      return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : ''
    },
    setStorageSync: function (k, v) { store[k] = v },
  }
  const id1 = device.ensureDeviceShortId(storage)
  assert.ok(/^[A-Za-z0-9]{4,8}$/.test(id1), 'device_short_id 应为 4-8 字母数字')
  assert.strictEqual(store[device.DEVICE_SHORT_ID_STORAGE_KEY], id1, '应持久化到 storage')
  // 冷启动：用同一 storage 再次取，值不变。
  const id2 = device.ensureDeviceShortId(storage)
  assert.strictEqual(id2, id1, '冷启动后 device_short_id 保持不变')
})

test('device_short_id 已存非法值时重新生成合法值', function () {
  const store = {}
  store[device.DEVICE_SHORT_ID_STORAGE_KEY] = 'bad id!!!'
  const storage = {
    getStorageSync: function (k) { return store[k] },
    setStorageSync: function (k, v) { store[k] = v },
  }
  const id = device.ensureDeviceShortId(storage)
  assert.ok(device.isValidDeviceShortId(id))
  assert.notStrictEqual(id, 'bad id!!!')
})

test('generateDeviceShortId 注入 rng 确定性生成', function () {
  const id = device.generateDeviceShortId(function () { return 0 })
  assert.strictEqual(id, 'aaaaaa', 'rng=0 应生成首字符重复的合法短 ID')
  assert.ok(device.isValidDeviceShortId(id))
})

// ---- ULID + fragment_id（AC#2/#3）----

test('ulid 生成 26 字符 Crockford base32', function () {
  const u = ulidMod.ulid(1700000000000, function () { return 0 })
  assert.strictEqual(u.length, 26)
  assert.ok(/^[0-9A-Z]{26}$/.test(u))
})

test('fragment_id 格式严格匹配 FRAGMENT_ID_RE（AC#2）', function () {
  const next = ulidMod.monotonicFactory(function () { return 0.5 })
  const recordedAt = new Date(2026, 5, 27, 12, 0, 0)
  const fid = audio.buildFragmentId(recordedAt, 'dev01a', next(1700000000000))
  assert.ok(audio.FRAGMENT_ID_RE.test(fid), 'fragment_id 应匹配 <ts>_<device>_<ULID>：' + fid)
})

test('同一毫秒内连续生成两个不同 fragment_id（AC#3）', function () {
  const next = ulidMod.monotonicFactory(function () { return 0.5 })
  const recordedAt = new Date(2026, 5, 27, 12, 0, 0)
  const t = 1700000000000
  const f1 = audio.buildFragmentId(recordedAt, 'dev01a', next(t))
  const f2 = audio.buildFragmentId(recordedAt, 'dev01a', next(t)) // 同一毫秒 → 单调递增随机段
  assert.notStrictEqual(f1, f2, '同秒/同毫秒应生成不同 fragment_id')
  assert.ok(audio.FRAGMENT_ID_RE.test(f1) && audio.FRAGMENT_ID_RE.test(f2))
})

// ---- manifest 草案字段完整性（AC#4）+ OSS 元数据（AC#6）----

test('buildUploadManifestDraft 含 AC#4 全部字段', function () {
  const m = audio.buildUploadManifestDraft({
    recordedAt: new Date(2026, 5, 27, 12, 0, 0),
    deviceShortId: 'dev01a',
    fragmentId: '20260627T120000_dev01a_01HZX3K8MN5PQR9TFB7AYWVCDE',
    sessionId: '01HZX3K8MN5PQR9TFB7AYWVCDE',
    chunkSeq: 1,
    chunkTotal: null,
    durationSeconds: 5.2,
    originalFormat: 'mp3',
    sizeBytes: 4096,
    originalSha256: 'a'.repeat(64),
    tempFilePath: 'wxfile://tmp/rec.mp3',
  })
  assert.strictEqual(m.session_id, '01HZX3K8MN5PQR9TFB7AYWVCDE')
  assert.strictEqual(m.chunk_seq, 1)
  assert.strictEqual(m.chunk_total, null, '非分片 chunk_total 为 null')
  assert.strictEqual(m.device_id, 'dev01a')
  assert.ok(m.recorded_at && /T.*[+-]\d{2}:\d{2}$/.test(m.recorded_at), 'recorded_at 带时区')
  assert.strictEqual(m.duration_seconds, 5.2)
  assert.strictEqual(m.audio.original_format, 'mp3')
  assert.strictEqual(m.audio.size_bytes, 4096)
  assert.strictEqual(m.upload.original_sha256, 'a'.repeat(64))
  assert.strictEqual(
    m.object_key,
    'recordings/2026-06-27/20260627T120000_dev01a_01HZX3K8MN5PQR9TFB7AYWVCDE.wav'
  )
})

test('buildOssMetadata 含全部 x-oss-meta-*，非分片 chunk-total 为 0（AC#6）', function () {
  const m = audio.buildUploadManifestDraft({
    recordedAt: new Date(2026, 5, 27, 12, 0, 0),
    deviceShortId: 'dev01a',
    fragmentId: '20260627T120000_dev01a_01HZX3K8MN5PQR9TFB7AYWVCDE',
    sessionId: '01HZX3K8MN5PQR9TFB7AYWVCDE',
    chunkSeq: 1,
    chunkTotal: null,
    durationSeconds: 5.2,
    originalFormat: 'mp3',
    sizeBytes: 4096,
    originalSha256: 'b'.repeat(64),
    tempFilePath: 'wxfile://tmp/rec.mp3',
  })
  const meta = audio.buildOssMetadata(m)
  assert.strictEqual(meta['x-oss-meta-session-id'], '01HZX3K8MN5PQR9TFB7AYWVCDE')
  assert.strictEqual(meta['x-oss-meta-chunk-seq'], '1')
  assert.strictEqual(meta['x-oss-meta-chunk-total'], '0', '非分片 OSS meta chunk-total 为 0')
  assert.ok(meta['x-oss-meta-recorded-at'])
  assert.strictEqual(meta['x-oss-meta-duration'], '5.2')
  assert.strictEqual(meta['x-oss-meta-original-format'], 'mp3')
  assert.strictEqual(meta['x-oss-meta-sha256'], 'b'.repeat(64))
})

// ---- sha256 正确性（AC#5）----

test('sha256Hex 空输入与已知向量正确', function () {
  assert.strictEqual(
    sha256Hex(new Uint8Array(0)),
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
  )
  assert.strictEqual(
    sha256Hex('abc'),
    'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
  )
})

test('sha256Hex 与 node crypto 对照（随机字节，AC#5）', function () {
  for (let n = 0; n < 5; n++) {
    const bytes = crypto.randomBytes(100 + n * 137)
    const expected = crypto.createHash('sha256').update(bytes).digest('hex')
    // 传 ArrayBuffer 与 Uint8Array 两种形态都应一致。
    const u8 = new Uint8Array(bytes)
    assert.strictEqual(sha256Hex(u8), expected, 'Uint8Array 输入')
    assert.strictEqual(
      sha256Hex(u8.buffer.slice(u8.byteOffset, u8.byteOffset + u8.byteLength)),
      expected,
      'ArrayBuffer 输入'
    )
  }
})

// ---- Page 集成：保存并上传生成 fragment_id + sha256 + manifest（AC#2/#3/#4/#5/#8）----

function makeRecorder() {
  const handlers = {}
  const calls = { start: 0, stop: 0 }
  return {
    handlers: handlers,
    calls: calls,
    onStart: function (cb) { handlers.start = cb },
    onStop: function (cb) { handlers.stop = cb },
    onError: function (cb) { handlers.error = cb },
    onInterruptionBegin: function (cb) { handlers.interruptionBegin = cb },
    onInterruptionEnd: function (cb) { handlers.interruptionEnd = cb },
    start: function () { calls.start += 1 },
    stop: function () { calls.stop += 1 },
  }
}

function makeWx(recorder, storage, fileBytes) {
  return {
    getRecorderManager: function () { return recorder },
    createInnerAudioContext: function () {
      return { src: '', onEnded: function () {}, onError: function () {},
        play: function () {}, pause: function () {}, stop: function () {}, destroy: function () {} }
    },
    setStorageSync: function (k, v) { storage[k] = v },
    getStorageSync: function (k) {
      return Object.prototype.hasOwnProperty.call(storage, k) ? storage[k] : ''
    },
    removeStorageSync: function (k) { delete storage[k] },
    getFileSystemManager: function () {
      return {
        unlink: function () {},
        readFileSync: function () { return fileBytes },
      }
    },
    showToast: function () {},
    switchTab: function () {},
  }
}

function loadPageConfig(wx) {
  global.wx = wx
  let captured = null
  global.Page = function (opts) { captured = opts }
  delete require.cache[INDEX_PAGE]
  require(INDEX_PAGE)
  return captured
}

function setup(fileBytes) {
  const recorder = makeRecorder()
  const storage = {}
  const wx = makeWx(recorder, storage, fileBytes)
  const config = loadPageConfig(wx)
  const inst = Object.assign({}, config)
  inst.data = JSON.parse(JSON.stringify(config.data))
  inst.setData = function (patch) { Object.assign(inst.data, patch) }
  inst.onLoad()
  return { inst: inst, recorder: recorder, storage: storage }
}

function recordDraft(ctx) {
  ctx.inst.onTapRecord()
  ctx.inst.onTapRecord()
  ctx.recorder.handlers.stop({ tempFilePath: 'wxfile://tmp/rec.mp3', duration: 5000, fileSize: 4096 })
}

test('保存并上传生成正式 fragment_id + sha256 + manifest 草案（AC#2/#4/#5）', function () {
  const bytes = crypto.randomBytes(512)
  const expectedSha = crypto.createHash('sha256').update(bytes).digest('hex')
  const ctx = setup(new Uint8Array(bytes))
  recordDraft(ctx)
  ctx.inst.onTapSaveUpload()
  const queue = ctx.storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY]
  assert.ok(Array.isArray(queue) && queue.length === 1)
  const item = queue[0]
  assert.ok(audio.FRAGMENT_ID_RE.test(item.fragmentId), 'fragmentId 应匹配正则：' + item.fragmentId)
  assert.ok(item.manifest, '队列项应携带 manifest 草案')
  assert.strictEqual(item.manifest.fragment_id, item.fragmentId)
  assert.strictEqual(item.manifest.upload.original_sha256, expectedSha, 'manifest sha256 应等于真实哈希')
  assert.ok(item.ossMetadata, '队列项应携带 OSS 元数据')
  assert.strictEqual(item.ossMetadata['x-oss-meta-sha256'], expectedSha)
  assert.strictEqual(item.ossMetadata['x-oss-meta-chunk-total'], '0')
  assert.strictEqual(ctx.inst.data.draft.frozen, true)
})

test('device_short_id 持久化后页面保存复用同一值（AC#8）', function () {
  const ctx = setup(new Uint8Array(crypto.randomBytes(64)))
  const persisted = ctx.storage[device.DEVICE_SHORT_ID_STORAGE_KEY]
  assert.ok(device.isValidDeviceShortId(persisted), 'onLoad 应已持久化 device_short_id')
  recordDraft(ctx)
  ctx.inst.onTapSaveUpload()
  const item = ctx.storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY][0]
  assert.strictEqual(item.manifest.device_id, persisted, 'fragment 的 device_id 应等于持久化短 ID')
  // fragment_id 的 deviceShortId 段一致。
  assert.strictEqual(item.fragmentId.split('_')[1], persisted)
})

test('同一秒内连续保存两条录音得到两个不同 fragment_id、device_short_id 一致（AC#3/#8）', function () {
  const ctx = setup(new Uint8Array(crypto.randomBytes(64)))
  recordDraft(ctx)
  ctx.inst.onTapSaveUpload()
  const first = ctx.storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY][0].fragmentId
  // 第二条录音（同秒）
  recordDraft(ctx)
  ctx.inst.onTapSaveUpload()
  const queue = ctx.storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY]
  assert.strictEqual(queue.length, 2, '应有两条不同 Fragment')
  const second = queue[1].fragmentId
  assert.notStrictEqual(first, second, '同秒两条 fragment_id 不同')
  assert.strictEqual(
    first.split('_')[1],
    second.split('_')[1],
    'device_short_id 段一致'
  )
})
