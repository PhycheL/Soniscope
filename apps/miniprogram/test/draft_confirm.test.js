// US-014 单元测试：草稿确认态（试听 / 暂停 / 重录 / 删除 / 保存并上传）。
// 覆盖：试听创建 innerAudioContext 并播放、暂停、重录清理并重新录音、删除清理不入队、
// 保存并上传冻结草稿并落盘队列、重复点击不生成重复 Fragment、上传队列纯函数去重。
//
// 小程序 Page 依赖全局 wx / Page，无构建工具时用 node 内置 test runner + 手写 mock 验证。
// 通过 make test（pytest）的 test_miniprogram_js.py 以子进程 `node --test` 纳入统一质量门。

const test = require('node:test')
const assert = require('node:assert')
const path = require('node:path')

const uploadQueue = require('../utils/upload_queue')

const INDEX_PAGE = path.resolve(__dirname, '../pages/index/index.js')

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

// innerAudioContext mock：记录 src / play / pause / stop / destroy 调用。
function makeAudio() {
  const audio = {
    src: '',
    calls: { play: 0, pause: 0, stop: 0, destroy: 0 },
    handlers: {},
    onEnded: function (cb) { audio.handlers.ended = cb },
    onError: function (cb) { audio.handlers.error = cb },
    play: function () { audio.calls.play += 1 },
    pause: function () { audio.calls.pause += 1 },
    stop: function () { audio.calls.stop += 1 },
    destroy: function () { audio.calls.destroy += 1 },
  }
  return audio
}

function makeWx(recorder, storage, unlinks, audios) {
  return {
    getRecorderManager: function () { return recorder },
    createInnerAudioContext: function () {
      const a = makeAudio()
      audios.push(a)
      return a
    },
    setStorageSync: function (k, v) { storage[k] = v },
    getStorageSync: function (k) {
      return Object.prototype.hasOwnProperty.call(storage, k) ? storage[k] : ''
    },
    removeStorageSync: function (k) { delete storage[k] },
    getFileSystemManager: function () {
      return { unlink: function (opt) { unlinks.push(opt.filePath) } }
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

function instantiate(config) {
  const inst = Object.assign({}, config)
  inst.data = JSON.parse(JSON.stringify(config.data))
  inst.setData = function (patch) { Object.assign(inst.data, patch) }
  return inst
}

function setup() {
  const recorder = makeRecorder()
  const storage = {}
  const unlinks = []
  const audios = []
  const wx = makeWx(recorder, storage, unlinks, audios)
  const inst = instantiate(loadPageConfig(wx))
  inst.onLoad()
  return { inst: inst, recorder: recorder, storage: storage, unlinks: unlinks, audios: audios }
}

// 录一段普通（非中断）草稿，进入草稿确认态。
function recordDraft(ctx, res) {
  ctx.inst.onTapRecord() // 开始录音
  ctx.inst.onTapRecord() // 停止录音 → 触发 recorder.stop()
  ctx.recorder.handlers.stop(
    res || { tempFilePath: 'wxfile://tmp/rec.mp3', duration: 5000, fileSize: 4096 }
  )
}

test('停止后进入草稿确认态，draft 非空且未冻结（AC#1）', function () {
  const ctx = setup()
  recordDraft(ctx)
  assert.ok(ctx.inst.data.draft, '停止后应有草稿')
  assert.strictEqual(ctx.inst.data.recording, false)
  assert.strictEqual(!!ctx.inst.data.draft.frozen, false)
})

test('试听创建 innerAudioContext 并播放，暂停停止播放（AC#2）', function () {
  const ctx = setup()
  recordDraft(ctx)
  ctx.inst.onTapPlay()
  assert.strictEqual(ctx.audios.length, 1, '应创建一个 innerAudioContext')
  assert.strictEqual(ctx.audios[0].src, 'wxfile://tmp/rec.mp3')
  assert.strictEqual(ctx.audios[0].calls.play, 1)
  assert.strictEqual(ctx.inst.data.playing, true)

  ctx.inst.onTapPause()
  assert.strictEqual(ctx.audios[0].calls.pause, 1)
  assert.strictEqual(ctx.inst.data.playing, false)

  ctx.inst.onUnload() // 清理音频
})

test('试听播放结束回调复位 playing（AC#2）', function () {
  const ctx = setup()
  recordDraft(ctx)
  ctx.inst.onTapPlay()
  ctx.audios[0].handlers.ended()
  assert.strictEqual(ctx.inst.data.playing, false)
  ctx.inst.onUnload()
})

test('重录清理草稿本地文件并重新开始录音（AC#3）', function () {
  const ctx = setup()
  recordDraft(ctx, { tempFilePath: 'wxfile://tmp/a.mp3', duration: 5000, fileSize: 4096 })
  const startsBefore = ctx.recorder.calls.start
  ctx.inst.onReRecord()
  assert.deepStrictEqual(ctx.unlinks, ['wxfile://tmp/a.mp3'], '重录应清理草稿临时文件')
  assert.strictEqual(ctx.recorder.calls.start, startsBefore + 1, '重录应重新开始录音')
  assert.strictEqual(ctx.inst.data.recording, true)
  ctx.inst.onUnload() // 清理重新启动的计时器，避免 node 事件循环挂起
})

test('删除清理草稿本地文件与记录，不入上传队列（AC#4）', function () {
  const ctx = setup()
  recordDraft(ctx, { tempFilePath: 'wxfile://tmp/b.mp3', duration: 5000, fileSize: 4096 })
  ctx.inst.onDeleteDraft()
  assert.deepStrictEqual(ctx.unlinks, ['wxfile://tmp/b.mp3'], '删除应清理草稿临时文件')
  assert.strictEqual(ctx.inst.data.draft, null)
  assert.strictEqual(ctx.inst.data.recording, false, '删除不触发录音')
  assert.strictEqual(
    ctx.storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY],
    undefined,
    '删除不生成 Fragment、不入队'
  )
})

test('保存并上传冻结草稿并落盘上传队列（AC#5）', function () {
  const ctx = setup()
  recordDraft(ctx)
  ctx.inst.onTapSaveUpload()
  const queue = ctx.storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY]
  assert.ok(Array.isArray(queue) && queue.length === 1, '上传队列应有一条记录')
  assert.strictEqual(queue[0].status, uploadQueue.STATUS_QUEUED)
  assert.strictEqual(queue[0].statusText, '待上传')
  assert.ok(queue[0].fragmentId, '队列项应有 fragmentId')
  assert.strictEqual(ctx.inst.data.draft.frozen, true, '草稿应被冻结')
})

test('重复点击保存并上传不生成重复 Fragment（AC#5）', function () {
  const ctx = setup()
  recordDraft(ctx)
  ctx.inst.onTapSaveUpload()
  ctx.inst.onTapSaveUpload() // 第二次点击应被冻结守卫拦截
  const queue = ctx.storage[uploadQueue.UPLOAD_QUEUE_STORAGE_KEY]
  assert.strictEqual(queue.length, 1, '重复点击只产生一条队列记录')
})

test('buildQueuedFragment 从草稿构造队列项', function () {
  const draft = {
    duration_seconds: 5.2,
    temp_file_path: 'wxfile://tmp/c.mp3',
    audio: { original_format: 'mp3', size_bytes: 4096 },
    object_key_preview: 'recordings/2026-06-27/20260627T120000_pending_pending.wav',
  }
  const item = uploadQueue.buildQueuedFragment(draft)
  assert.strictEqual(item.fragmentId, '20260627T120000_pending_pending')
  assert.strictEqual(item.status, 'queued')
  assert.strictEqual(item.statusText, '待上传')
  assert.strictEqual(item.originalFormat, 'mp3')
  assert.strictEqual(item.durationSeconds, 5.2)
})

test('appendQueuedFragment 对同一 fragmentId 去重（AC#5）', function () {
  const a = { fragmentId: 'f1', status: 'queued' }
  const b = { fragmentId: 'f1', status: 'queued' }
  const c = { fragmentId: 'f2', status: 'queued' }
  let q = uploadQueue.appendQueuedFragment([], a)
  q = uploadQueue.appendQueuedFragment(q, b)
  assert.strictEqual(q.length, 1, '相同 fragmentId 不重复追加')
  q = uploadQueue.appendQueuedFragment(q, c)
  assert.strictEqual(q.length, 2)
})
