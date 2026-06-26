// 首页：录音开始/停止 + mm:ss 计时 + 停止后生成保留原始格式的本地草稿（US-012）。
// 录音中断保护与草稿恢复提示（US-013）：锁屏 / 来电 / 切后台等中断时自动停止录音并落盘草稿，
// 回到前台后提示保留 / 丢弃 / 继续新录。
//
// 前端不转码（ADR-1）：录音请求 mp3（体积小、兼容性好），但 original_format 以微信实际产出的
// 临时文件为准；OSS object key 预览始终用 .wav 目标扩展名，仅表示 Worker 标准化目标。

const { createLogger } = require('../../utils/logger')
const {
  formatDuration,
  buildDraftManifest,
  buildFragmentId,
  buildUploadManifestDraft,
  buildOssMetadata,
} = require('../../utils/audio')
const {
  INTERRUPT_DRAFT_STORAGE_KEY,
  buildInterruptedDraft,
  buildRecoveryPrompt,
} = require('../../utils/draft')
const {
  UPLOAD_QUEUE_STORAGE_KEY,
  buildQueuedFragment,
  appendQueuedFragment,
} = require('../../utils/upload_queue')
const { ensureDeviceShortId } = require('../../utils/device')
const { monotonicFactory } = require('../../utils/ulid')
const { sha256Hex } = require('../../utils/sha256')

const logger = createLogger('index')

// 录音请求格式（tech-spec §5.1：可优先请求 mp3）。
const RECORD_FORMAT = 'mp3'
// 单次录音最长时长（毫秒）；长录音自动分片在 US-016 实现，本期与分片阈值对齐。
const MAX_RECORD_DURATION_MS = 600000

Page({
  data: {
    recording: false,
    durationText: '00:00',
    draft: null,
    // 中断恢复提示（US-013 AC#4）：非空时渲染保留 / 丢弃 / 继续新录三个按钮。
    recovery: null,
    // 草稿试听播放状态（US-014 AC#2）：true 时试听按钮显示「暂停」语义。
    playing: false,
  },

  onLoad() {
    this.recorder = wx.getRecorderManager()
    this.startedAt = 0
    this.timer = null
    // 中断去重标志（AC#6）：每次 _startRecording 重置；同一次录音内只处理一次中断。
    this._interruptHandled = false
    // 当前 onStop 是否由中断触发，决定走中断草稿落盘路径还是普通草稿路径。
    this._interrupting = false
    this._interruptReason = ''
    // 草稿试听播放器（懒创建于 onTapPlay，US-014）。
    this._audio = null
    // 单调 ULID 生成器（US-015）：保证同一秒/同一毫秒内连续保存得到不同 fragment_id / session_id。
    this._nextUlid = monotonicFactory()
    this._bindRecorder()
    // 首次启动生成并持久化 device_short_id（US-015 AC#1，幂等）。
    ensureDeviceShortId(wx)
    logger.info('index page loaded')
  },

  // 回到前台（AC#4）：若存在中断保存的草稿，展示恢复提示。
  onShow() {
    this._maybeShowRecovery()
  },

  // 切后台是等价中断（AC#1）：录音中切后台自动停止并保存草稿。
  onHide() {
    this._handleInterruption('background')
  },

  onUnload() {
    this._clearTimer()
    this._destroyAudio()
  },

  _bindRecorder() {
    const self = this
    this.recorder.onStart(function () {
      logger.info('recording started', { format: RECORD_FORMAT })
    })
    this.recorder.onStop(function (res) {
      self._onRecordStop(res)
    })
    this.recorder.onError(function (err) {
      self._onRecordError(err)
    })
    // 录音中断回调注册（AC#1）：锁屏 / 来电等系统中断由此触发。
    this.recorder.onInterruptionBegin(function () {
      self._handleInterruption('interruption')
    })
    this.recorder.onInterruptionEnd(function () {
      logger.info('recorder interruption end')
    })
  },

  // 统一中断处理（AC#2/#6）：录音中触发即自动停止；同一次录音内去重，避免重复落盘。
  _handleInterruption(reason) {
    if (!this.data.recording) {
      return
    }
    if (this._interruptHandled) {
      return
    }
    this._interruptHandled = true
    this._interrupting = true
    this._interruptReason = reason
    this._clearTimer()
    logger.warn('recording interrupted, auto-stop & save draft', { reason: reason })
    // stop() 触发 onStop，res 携带已录到的临时音频文件路径与时长。
    this.recorder.stop()
  },

  onTapRecord() {
    if (this.data.recording) {
      this._stopRecording()
    } else {
      this._startRecording()
    }
  },

  _startRecording() {
    this.startedAt = Date.now()
    this._interruptHandled = false
    this._interrupting = false
    this._destroyAudio()
    this.setData({
      recording: true,
      durationText: '00:00',
      draft: null,
      recovery: null,
      playing: false,
    })
    this._startTimer()
    // start() 会触发录音权限申请；用户拒绝或失败时进入 onError。
    this.recorder.start({
      format: RECORD_FORMAT,
      duration: MAX_RECORD_DURATION_MS,
    })
  },

  _stopRecording() {
    this._clearTimer()
    this.recorder.stop()
  },

  _onRecordStop(res) {
    this._clearTimer()
    const interrupted = this._interrupting
    this._interrupting = false
    const recordedAt = new Date(this.startedAt || Date.now())
    // 中断时 res.duration 可能缺失，回退到计时差，保证草稿包含录制时长（AC#3）。
    const durationMs =
      (res && res.duration) || Math.max(0, Date.now() - (this.startedAt || Date.now()))
    const opts = {
      recordedAt: recordedAt,
      tempFilePath: res && res.tempFilePath,
      requestedFormat: RECORD_FORMAT,
      durationMs: durationMs,
      fileSize: res && res.fileSize,
    }
    if (interrupted) {
      this._saveInterruptedDraft(opts)
      return
    }
    const draft = buildDraftManifest(opts)
    this.setData({
      recording: false,
      durationText: formatDuration(draft.duration_seconds),
      draft: draft,
    })
    // AC#5/#7/#8（US-012）：草稿记录 audio.original_format，并在控制台 / vConsole 打印。
    logger.info('recording stopped', {
      original_format: draft.audio.original_format,
      duration_seconds: draft.duration_seconds,
      temp_file_path: draft.temp_file_path,
      object_key_preview: draft.object_key_preview,
    })
  },

  // 中断草稿本地落盘（AC#2）：单槽位 storage 天然去重（AC#6），后到状态覆盖前一份。
  _saveInterruptedDraft(opts) {
    opts.interruptReason = this._interruptReason
    const draft = buildInterruptedDraft(opts)
    wx.setStorageSync(INTERRUPT_DRAFT_STORAGE_KEY, draft)
    this.setData({
      recording: false,
      durationText: formatDuration(draft.duration_seconds),
      draft: draft,
    })
    logger.warn('interrupted draft saved', {
      status: draft.status,
      duration_seconds: draft.duration_seconds,
      original_format: draft.audio.original_format,
      reason: draft.interrupt_reason,
    })
    // 若此刻仍在前台（如切后台立即返回），直接展示恢复提示。
    this._maybeShowRecovery()
  },

  // 读取中断草稿并展示恢复提示（AC#4）。
  _maybeShowRecovery() {
    let saved = ''
    try {
      saved = wx.getStorageSync(INTERRUPT_DRAFT_STORAGE_KEY)
    } catch (e) {
      saved = ''
    }
    if (!saved) {
      return
    }
    this.setData({ draft: saved, recovery: buildRecoveryPrompt(saved) })
  },

  // 保留（AC#5）：保留草稿，关闭提示，清掉中断槽位（草稿留待 US-014 试听 / 上传）。
  onKeepDraft() {
    this._clearInterruptStorage()
    this.setData({ recovery: null })
    logger.info('interrupted draft kept')
  },

  // 丢弃（AC#5）：清理本地草稿文件与记录，不生成 Fragment。
  onDiscardDraft() {
    this._cleanupDraftFile(this.data.draft)
    this._clearInterruptStorage()
    this.setData({ recovery: null, draft: null, durationText: '00:00' })
    logger.info('interrupted draft discarded')
  },

  // 继续新录（AC#5）：清理旧草稿并立即开始新录音。
  onRestartRecording() {
    this._cleanupDraftFile(this.data.draft)
    this._clearInterruptStorage()
    this.setData({ recovery: null, draft: null })
    logger.info('interrupted draft discarded, restart recording')
    this._startRecording()
  },

  _clearInterruptStorage() {
    try {
      wx.removeStorageSync(INTERRUPT_DRAFT_STORAGE_KEY)
    } catch (e) {
      // best effort
    }
  },

  // ---- US-014 草稿确认态：试听 / 暂停 / 重录 / 删除 / 保存并上传 ----

  // 试听（AC#2）：用 wx.createInnerAudioContext 播放本地草稿临时音频。
  onTapPlay() {
    const draft = this.data.draft
    if (!draft || !draft.temp_file_path) {
      wx.showToast({ title: '无可试听音频', icon: 'none' })
      return
    }
    if (!this._audio) {
      const self = this
      this._audio = wx.createInnerAudioContext()
      this._audio.onEnded(function () {
        self.setData({ playing: false })
      })
      this._audio.onError(function (err) {
        self.setData({ playing: false })
        logger.error('audition error', { errMsg: err && err.errMsg })
      })
    }
    this._audio.src = draft.temp_file_path
    this._audio.play()
    this.setData({ playing: true })
    logger.info('audition play', { temp_file_path: draft.temp_file_path })
  },

  // 暂停（AC#2）：暂停试听播放。
  onTapPause() {
    if (this._audio) {
      this._audio.pause()
    }
    this.setData({ playing: false })
    logger.info('audition pause')
  },

  // 重录（AC#3）：清理当前草稿本地文件与记录，回到录音初始态并立即开始新录音。
  onReRecord() {
    this._destroyAudio()
    this._cleanupDraftFile(this.data.draft)
    this._clearInterruptStorage()
    this.setData({ draft: null, recovery: null })
    logger.info('draft re-record')
    this._startRecording()
  },

  // 删除（AC#4）：清理当前草稿本地文件与记录，不生成 Fragment、不触发上传，回到初始态。
  onDeleteDraft() {
    this._destroyAudio()
    this._cleanupDraftFile(this.data.draft)
    this._clearInterruptStorage()
    this.setData({ draft: null, recovery: null, durationText: '00:00' })
    logger.info('draft deleted')
  },

  // 保存并上传（US-014 AC#5 + US-015）：生成正式 fragment_id / session_id / sha256 与 manifest 草案，
  // 冻结草稿、晋升为「待上传」队列项并落盘；防重复点击生成重复 Fragment。
  onTapSaveUpload() {
    const draft = this.data.draft
    if (!draft || draft.frozen) {
      return
    }
    // US-015 AC#1：取持久化的 device_short_id（冷启动不变）。
    const deviceShortId = ensureDeviceShortId(wx)
    const recordedAt = draft.recorded_at
      ? new Date(draft.recorded_at)
      : new Date(this.startedAt || Date.now())
    // US-016 会把 session_id 提前到录音开始；本期单条录音在保存时生成（chunk_seq=1、chunk_total=null）。
    const sessionId = this._nextUlid()
    // US-015 AC#2/#3：fragment_id = <时间前缀>_<device>_<ULID>；单调 ULID 保证同秒唯一。
    const fragmentId = buildFragmentId(recordedAt, deviceShortId, this._nextUlid())
    // US-015 AC#5：计算原始音频字节 sha256，写入 upload.original_sha256。
    const originalSha256 = this._computeOriginalSha256(draft.temp_file_path)
    const manifest = buildUploadManifestDraft({
      recordedAt: recordedAt,
      deviceShortId: deviceShortId,
      fragmentId: fragmentId,
      sessionId: sessionId,
      chunkSeq: 1,
      chunkTotal: null,
      durationSeconds: draft.duration_seconds,
      originalFormat: draft.audio && draft.audio.original_format,
      sizeBytes: draft.audio && draft.audio.size_bytes,
      originalSha256: originalSha256,
      tempFilePath: draft.temp_file_path,
    })
    // US-015 AC#6：准备 OSS 用户自定义元数据，供 US-017 直传时附带。
    const ossMetadata = buildOssMetadata(manifest)
    const item = buildQueuedFragment(draft, manifest, ossMetadata)
    let queue = []
    try {
      queue = wx.getStorageSync(UPLOAD_QUEUE_STORAGE_KEY) || []
    } catch (e) {
      queue = []
    }
    queue = appendQueuedFragment(queue, item)
    wx.setStorageSync(UPLOAD_QUEUE_STORAGE_KEY, queue)
    // 草稿已晋升 Fragment：清掉中断槽位，冻结当前草稿（禁用确认态按钮）。
    this._clearInterruptStorage()
    this._destroyAudio()
    const frozen = Object.assign({}, draft, { frozen: true, fragment_id: fragmentId })
    this.setData({ draft: frozen })
    // AC#8：vConsole 显示 fragment_id 与 device_short_id（sha256 非密钥，截断便于核对）。
    logger.info('draft saved & queued for upload', {
      fragmentId: fragmentId,
      deviceShortId: deviceShortId,
      sessionId: sessionId,
      sha256Prefix: originalSha256 ? originalSha256.slice(0, 12) : '',
      status: item.status,
    })
    wx.showToast({ title: '已加入上传队列', icon: 'success' })
  },

  // US-015 AC#5：读取本地临时音频字节并计算原始 sha256；读不到时返回空串（不阻断入队）。
  _computeOriginalSha256(tempFilePath) {
    if (!tempFilePath) {
      return ''
    }
    try {
      const fs = wx.getFileSystemManager && wx.getFileSystemManager()
      if (!fs || !fs.readFileSync) {
        return ''
      }
      const buf = fs.readFileSync(tempFilePath)
      return sha256Hex(buf)
    } catch (e) {
      logger.error('compute original sha256 failed', { errMsg: e && e.message })
      return ''
    }
  },

  _destroyAudio() {
    if (this._audio) {
      try {
        if (this._audio.stop) {
          this._audio.stop()
        }
        if (this._audio.destroy) {
          this._audio.destroy()
        }
      } catch (e) {
        // best effort
      }
      this._audio = null
    }
    if (this.data.playing) {
      this.setData({ playing: false })
    }
  },

  _cleanupDraftFile(draft) {
    if (!draft || !draft.temp_file_path) {
      return
    }
    try {
      const fs = wx.getFileSystemManager && wx.getFileSystemManager()
      if (fs && fs.unlink) {
        fs.unlink({ filePath: draft.temp_file_path, fail: function () {} })
      }
    } catch (e) {
      // best effort：临时文件可能已被系统回收。
    }
  },

  _onRecordError(err) {
    this._clearTimer()
    this.setData({ recording: false })
    logger.error('recorder error', { errMsg: err && err.errMsg })
    wx.showToast({ title: '录音失败或未授权', icon: 'none' })
  },

  _startTimer() {
    const self = this
    this._clearTimer()
    this.timer = setInterval(function () {
      const elapsed = Math.floor((Date.now() - self.startedAt) / 1000)
      self.setData({ durationText: formatDuration(elapsed) })
    }, 1000)
  },

  _clearTimer() {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
  },

  goUploads() {
    wx.switchTab({ url: '/pages/uploads/uploads' })
  },
})
