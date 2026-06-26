// US-013 单元测试：录音中断保护与草稿恢复（AC#7）。
// 覆盖：中断回调注册、中断时停止录音、本地落盘、重复中断去重。
//
// 小程序 Page 依赖全局 wx / Page，无构建工具时用 node 内置 test runner + 手写 mock 验证。
// 通过 make test（pytest）的 test_miniprogram_js.py 以子进程 `node --test` 纳入统一质量门。

const test = require('node:test')
const assert = require('node:assert')
const path = require('node:path')

const draft = require('../utils/draft')

const INDEX_PAGE = path.resolve(__dirname, '../pages/index/index.js')

// 录音管理器 mock：记录回调注册与 start/stop 调用，可手动触发 onStop。
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
    // 真机上 stop() 异步回调 onStop；测试里由用例显式触发 fireStop 以控制时序。
    stop: function () { calls.stop += 1 },
  }
}

function makeWx(recorder, storage, unlinks) {
  return {
    getRecorderManager: function () { return recorder },
    setStorageSync: function (k, v) { storage[k] = v },
    getStorageSync: function (k) { return Object.prototype.hasOwnProperty.call(storage, k) ? storage[k] : '' },
    removeStorageSync: function (k) { delete storage[k] },
    getFileSystemManager: function () {
      return { unlink: function (opt) { unlinks.push(opt.filePath) } }
    },
    showToast: function () {},
    switchTab: function () {},
  }
}

// 载入 index.js 并捕获传给全局 Page 的配置对象（每次清缓存以重新执行）。
function loadPageConfig(wx) {
  global.wx = wx
  let captured = null
  global.Page = function (opts) { captured = opts }
  delete require.cache[INDEX_PAGE]
  require(INDEX_PAGE)
  return captured
}

// 用捕获的 Page 配置构造一个实例（深拷贝 data，setData 做浅合并）。
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
  const wx = makeWx(recorder, storage, unlinks)
  const inst = instantiate(loadPageConfig(wx))
  inst.onLoad()
  return { inst: inst, recorder: recorder, storage: storage, unlinks: unlinks }
}

function startRecording(inst) {
  inst.onTapRecord() // 未录音 → 开始录音
}

function fireStop(ctx, res) {
  ctx.recorder.handlers.stop(res || { tempFilePath: 'wxfile://tmp/rec.mp3', duration: 4200, fileSize: 12345 })
}

test('onLoad 注册中断回调（AC#1）', function () {
  const ctx = setup()
  assert.strictEqual(typeof ctx.recorder.handlers.interruptionBegin, 'function')
  assert.strictEqual(typeof ctx.recorder.handlers.interruptionEnd, 'function')
  assert.strictEqual(typeof ctx.recorder.handlers.stop, 'function')
})

test('中断触发时自动停止录音（AC#2）', function () {
  const ctx = setup()
  startRecording(ctx.inst)
  assert.strictEqual(ctx.inst.data.recording, true)
  ctx.recorder.handlers.interruptionBegin()
  assert.strictEqual(ctx.recorder.calls.stop, 1, '中断应触发 recorder.stop()')
})

test('中断后草稿本地落盘且标记被中断保存、含录制时长（AC#2/#3）', function () {
  const ctx = setup()
  startRecording(ctx.inst)
  ctx.recorder.handlers.interruptionBegin()
  fireStop(ctx, { tempFilePath: 'wxfile://tmp/rec.mp3', duration: 4200, fileSize: 12345 })

  const saved = ctx.storage[draft.INTERRUPT_DRAFT_STORAGE_KEY]
  assert.ok(saved, '中断草稿应已落盘到 storage')
  assert.strictEqual(saved.status, draft.STATUS_DRAFT_INTERRUPTED)
  assert.strictEqual(saved.status_label, draft.STATUS_LABEL_DRAFT_INTERRUPTED)
  assert.strictEqual(saved.interrupted, true)
  assert.strictEqual(saved.duration_seconds, 4.2, '草稿应包含录制时长')
  assert.strictEqual(ctx.inst.data.recording, false)
})

test('连续两次中断不重复生成草稿（AC#6 去重）', function () {
  const ctx = setup()
  startRecording(ctx.inst)
  ctx.recorder.handlers.interruptionBegin()
  ctx.recorder.handlers.interruptionBegin() // 第二次中断应被去重忽略
  assert.strictEqual(ctx.recorder.calls.stop, 1, '同一次录音仅 stop 一次')

  fireStop(ctx)
  // onStop 后若再来中断（已非录音态），也不应再 stop / 落盘新草稿
  ctx.recorder.handlers.interruptionBegin()
  assert.strictEqual(ctx.recorder.calls.stop, 1)
  assert.ok(ctx.storage[draft.INTERRUPT_DRAFT_STORAGE_KEY], '仅保留同一份中断草稿')
})

test('切后台（onHide）作为等价中断保存草稿（AC#1）', function () {
  const ctx = setup()
  startRecording(ctx.inst)
  ctx.inst.onHide()
  assert.strictEqual(ctx.recorder.calls.stop, 1)
  fireStop(ctx)
  const saved = ctx.storage[draft.INTERRUPT_DRAFT_STORAGE_KEY]
  assert.ok(saved)
  assert.strictEqual(saved.interrupt_reason, 'background')
})

test('未录音时中断回调为空操作', function () {
  const ctx = setup()
  ctx.recorder.handlers.interruptionBegin() // 未开始录音
  assert.strictEqual(ctx.recorder.calls.stop, 0)
  assert.strictEqual(ctx.storage[draft.INTERRUPT_DRAFT_STORAGE_KEY], undefined)
})

test('回到前台展示恢复提示（AC#4）', function () {
  const ctx = setup()
  startRecording(ctx.inst)
  ctx.inst.onHide()
  fireStop(ctx)
  ctx.inst.data.recovery = null // 清掉落盘时即时弹出的提示，模拟回前台重新触发
  ctx.inst.onShow()
  assert.ok(ctx.inst.data.recovery, 'onShow 应展示恢复提示')
  assert.strictEqual(ctx.inst.data.recovery.message, draft.RECOVERY_MESSAGE)
})

test('保留 / 丢弃 / 继续新录三个动作产生对应状态迁移（AC#5）', function () {
  // 保留：草稿保留、提示关闭、清掉中断槽位
  let ctx = setup()
  startRecording(ctx.inst)
  ctx.recorder.handlers.interruptionBegin()
  fireStop(ctx)
  ctx.inst.onKeepDraft()
  assert.strictEqual(ctx.inst.data.recovery, null)
  assert.ok(ctx.inst.data.draft, '保留后草稿仍在')
  assert.strictEqual(ctx.storage[draft.INTERRUPT_DRAFT_STORAGE_KEY], undefined)

  // 丢弃：清理草稿文件与记录
  ctx = setup()
  startRecording(ctx.inst)
  ctx.recorder.handlers.interruptionBegin()
  fireStop(ctx, { tempFilePath: 'wxfile://tmp/rec.mp3', duration: 3000, fileSize: 999 })
  ctx.inst.onDiscardDraft()
  assert.strictEqual(ctx.inst.data.recovery, null)
  assert.strictEqual(ctx.inst.data.draft, null)
  assert.deepStrictEqual(ctx.unlinks, ['wxfile://tmp/rec.mp3'])
  assert.strictEqual(ctx.storage[draft.INTERRUPT_DRAFT_STORAGE_KEY], undefined)

  // 继续新录：清理旧草稿并重新开始录音
  ctx = setup()
  startRecording(ctx.inst)
  ctx.recorder.handlers.interruptionBegin()
  fireStop(ctx)
  const startsBefore = ctx.recorder.calls.start
  ctx.inst.onRestartRecording()
  assert.strictEqual(ctx.inst.data.recovery, null)
  assert.strictEqual(ctx.inst.data.recording, true, '继续新录应重新进入录音态')
  assert.strictEqual(ctx.recorder.calls.start, startsBefore + 1)
  ctx.inst.onUnload() // 清理新录音启动的计时器，避免 node 事件循环挂起
})

test('dedupeInterruptedDraft 单槽位只保留最后状态（AC#6）', function () {
  const a = { status: draft.STATUS_DRAFT_INTERRUPTED, duration_seconds: 1 }
  const b = { status: draft.STATUS_DRAFT_INTERRUPTED, duration_seconds: 2 }
  assert.strictEqual(draft.dedupeInterruptedDraft(a, b), b)
  assert.strictEqual(draft.dedupeInterruptedDraft(a, null), a)
  assert.strictEqual(draft.dedupeInterruptedDraft(null, null), null)
})
