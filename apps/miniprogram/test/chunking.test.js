// US-016 单元测试：长录音自动分片与 session 聚合元数据。
// 覆盖（AC#6）：session_id 分配、chunk_seq 递增、chunk_total 回填、边界时长。
//
// 纯函数（utils/chunking）直接验证；Page 集成（录音开始分配 session、到达阈值自动分片、
// 最终停止聚合并整段入队）用与 ids.test.js / draft_confirm.test.js 一致的手写 wx / Page mock。
// 通过 make test（pytest）的 test_miniprogram_js.py 以子进程 `node --test` 纳入统一质量门。

const test = require('node:test')
const assert = require('node:assert')
const crypto = require('node:crypto')
const path = require('node:path')

const chunking = require('../utils/chunking')
const audio = require('../utils/audio')
const uploadQueue = require('../utils/upload_queue')

const INDEX_PAGE = path.resolve(__dirname, '../pages/index/index.js')

// ---- 纯函数 ----

test('shouldRotateChunk 在 600s 阈值分界（AC#2/#5）', function () {
  assert.strictEqual(chunking.CHUNK_MAX_DURATION_SECONDS, 600)
  assert.strictEqual(chunking.shouldRotateChunk(599), false)
  assert.strictEqual(chunking.shouldRotateChunk(600), true, '到达阈值即应分片')
  assert.strictEqual(chunking.shouldRotateChunk(604), true)
  // 计时器每秒触发一次判断：在 600s 触发 → 单片实际时长约 600~601s，恒 ≤ 605s（AC#5）。
})

test('createRecordingSession 分配 session_id，addChunk 的 chunk_seq 从 1 递增（AC#1/#3）', function () {
  const s = chunking.createRecordingSession('01HZX3K8MN5PQR9TFB7AYWVCDE')
  assert.strictEqual(s.sessionId, '01HZX3K8MN5PQR9TFB7AYWVCDE')
  assert.strictEqual(chunking.chunkCount(s), 0)
  const c1 = chunking.addChunk(s, { tempFilePath: 'a' })
  const c2 = chunking.addChunk(s, { tempFilePath: 'b' })
  const c3 = chunking.addChunk(s, { tempFilePath: 'c' })
  assert.strictEqual(c1.chunk_seq, 1)
  assert.strictEqual(c2.chunk_seq, 2)
  assert.strictEqual(c3.chunk_seq, 3)
  assert.strictEqual(chunking.chunkCount(s), 3)
})

test('resolveChunkTotal：单片为 null，多片为片数（AC#4）', function () {
  assert.strictEqual(chunking.resolveChunkTotal(0), null)
  assert.strictEqual(chunking.resolveChunkTotal(1), null, '未分片单条录音 chunk_total 为 null')
  assert.strictEqual(chunking.resolveChunkTotal(2), 2)
  assert.strictEqual(chunking.resolveChunkTotal(3), 3)
})

test('backfillChunkTotal 把片数回填到所有分片 manifest（AC#4）', function () {
  const manifests = [{ chunk_seq: 1 }, { chunk_seq: 2 }, { chunk_seq: 3 }]
  const total = chunking.backfillChunkTotal(manifests)
  assert.strictEqual(total, 3)
  manifests.forEach(function (m) {
    assert.strictEqual(m.chunk_total, 3, '每片 chunk_total 应回填为 3')
  })
  // 单片回填 null。
  const one = [{ chunk_seq: 1 }]
  assert.strictEqual(chunking.backfillChunkTotal(one), null)
  assert.strictEqual(one[0].chunk_total, null)
})

// ---- Page 集成：录音开始分配 session → 自动分片 → 最终停止聚合入队 ----

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
      return { unlink: function () {}, readFileSync: function () { return fileBytes } }
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

function setup() {
  const recorder = makeRecorder()
  const storage = {}
  const wx = makeWx(recorder, storage, new Uint8Array(crypto.randomBytes(256)))
  const config = loadPageConfig(wx)
  const inst = Object.assign({}, config)
  inst.data = JSON.parse(JSON.stringify(config.data))
  inst.setData = function (patch) { Object.assign(inst.data, patch) }
  inst.onLoad()
  return { inst: inst, recorder: recorder, storage: storage }
}

// 模拟一次分片边界：计时器到阈值 → stop 当前片 → onStop 落片并自动 start 下一片。
function rotateChunk(ctx, res) {
  ctx.inst._maybeRotateChunk(chunking.CHUNK_MAX_DURATION_SECONDS)
  ctx.recorder.handlers.stop(res)
}

test('录音开始即分配 session_id，且自动分片共享该值（AC#1）', function () {
  const ctx = setup()
  ctx.inst.onTapRecord() // 开始录音
  const sessionId = ctx.inst._session.sessionId
  assert.ok(sessionId && sessionId.length === 26, '录音开始应分配 26 字符 session_id：' + sessionId)
  rotateChunk(ctx, { tempFilePath: 'wxfile://tmp/c1.mp3', duration: 600000, fileSize: 1000 })
  assert.strictEqual(ctx.inst._session.sessionId, sessionId, '分片后 session_id 不变')
  ctx.inst.onUnload()
})

test('25 分钟长录音切成 3 片：chunk_seq 1/2/3、共享 session、chunk_total=3 回填并入队（AC#2/#3/#4/#7）', function () {
  const ctx = setup()
  ctx.inst.onTapRecord() // 开始录音（chunk 1）
  const sessionId = ctx.inst._session.sessionId
  // 两次分片边界（10 分钟 + 10 分钟），随后用户停止收尾第 3 片（约 5 分钟）。
  rotateChunk(ctx, { tempFilePath: 'wxfile://tmp/c1.mp3', duration: 600000, fileSize: 1000 })
  rotateChunk(ctx, { tempFilePath: 'wxfile://tmp/c2.mp3', duration: 600000, fileSize: 1000 })
  assert.strictEqual(ctx.inst.data.recording, true, '分片间仍处录音态')
  assert.strictEqual(chunking.chunkCount(ctx.inst._session), 2, '已落地两片')
  // 用户最终停止 → 第 3 片落地，构造长录音聚合草稿。
  ctx.inst.onTapRecord()
  ctx.recorder.handlers.stop({ tempFilePath: 'wxfile://tmp/c3.mp3', duration: 300000, fileSize: 500 })

  const draft = ctx.inst.data.draft
  assert.ok(draft && draft.is_long, '应为长录音聚合草稿')
  assert.strictEqual(draft.chunk_total, 3)
  assert.strictEqual(draft.session_id, sessionId)
  // 总时长 ≈ 10 + 10 + 5 = 25 分钟（1500 秒）。
  assert.strictEqual(draft.duration_seconds, 1500)

  // 单片时长均 ≤ 605 秒（AC#5）。
  ctx.inst._session.chunks.forEach(function (c) {
    assert.ok(c.durationMs / 1000 <= 605, '单片时长不超过 605 秒：' + c.durationMs)
  })

  // 确认后整段入队：3 条 Fragment，独立 fragment_id、共享 session、chunk_seq 1/2/3、chunk_total 3。
  ctx.inst.onTapSaveUpload()
  const queue = ctx.storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY]
  assert.ok(Array.isArray(queue) && queue.length === 3, '应入队 3 条 Fragment')
  const ids = {}
  queue.forEach(function (item, i) {
    assert.ok(audio.FRAGMENT_ID_RE.test(item.fragmentId), 'fragmentId 应合法：' + item.fragmentId)
    ids[item.fragmentId] = true
    assert.strictEqual(item.manifest.session_id, sessionId, '共享 session_id')
    assert.strictEqual(item.manifest.chunk_seq, i + 1, 'chunk_seq 1/2/3')
    assert.strictEqual(item.manifest.chunk_total, 3, 'chunk_total 回填为 3')
    assert.strictEqual(item.ossMetadata['x-oss-meta-chunk-total'], '3')
    assert.strictEqual(item.ossMetadata['x-oss-meta-session-id'], sessionId)
  })
  assert.strictEqual(Object.keys(ids).length, 3, '3 个 fragment_id 互不相同')
  assert.strictEqual(ctx.inst.data.draft.frozen, true, '保存后草稿冻结')
  // 重复点击不再追加。
  ctx.inst.onTapSaveUpload()
  assert.strictEqual(ctx.storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY].length, 3)
})

test('未达阈值的单条录音不分片：chunk_total 为 null（非分片语义）', function () {
  const ctx = setup()
  ctx.inst.onTapRecord() // 开始
  ctx.inst.onTapRecord() // 停止（未触发任何分片）
  ctx.recorder.handlers.stop({ tempFilePath: 'wxfile://tmp/s.mp3', duration: 5000, fileSize: 4096 })
  const draft = ctx.inst.data.draft
  assert.ok(draft, '应进入单草稿确认态')
  assert.strictEqual(!!draft.is_long, false, '单条录音不是长录音聚合草稿')
  ctx.inst.onTapSaveUpload()
  const item = ctx.storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY][0]
  assert.strictEqual(item.manifest.chunk_total, null, '非分片 chunk_total 为 null')
  assert.strictEqual(item.manifest.chunk_seq, 1)
  assert.strictEqual(item.ossMetadata['x-oss-meta-chunk-total'], '0', '非分片 OSS meta chunk-total 为 0')
})

test('长录音重录清理该 session 下所有分片临时文件', function () {
  const recorder = makeRecorder()
  const storage = {}
  const unlinks = []
  const wx = makeWx(recorder, storage, new Uint8Array(crypto.randomBytes(64)))
  wx.getFileSystemManager = function () {
    return { unlink: function (opt) { unlinks.push(opt.filePath) }, readFileSync: function () { return new Uint8Array(8) } }
  }
  const config = loadPageConfig(wx)
  const inst = Object.assign({}, config)
  inst.data = JSON.parse(JSON.stringify(config.data))
  inst.setData = function (patch) { Object.assign(inst.data, patch) }
  inst.onLoad()
  const ctx = { inst: inst, recorder: recorder, storage: storage }

  inst.onTapRecord()
  rotateChunk(ctx, { tempFilePath: 'wxfile://tmp/c1.mp3', duration: 600000, fileSize: 1000 })
  inst.onTapRecord()
  recorder.handlers.stop({ tempFilePath: 'wxfile://tmp/c2.mp3', duration: 300000, fileSize: 500 })
  inst.onDeleteDraft()
  assert.deepStrictEqual(unlinks.sort(), ['wxfile://tmp/c1.mp3', 'wxfile://tmp/c2.mp3'])
  assert.strictEqual(inst.data.draft, null)
})
