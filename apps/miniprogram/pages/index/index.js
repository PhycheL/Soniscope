// 首页：录音开始/停止 + mm:ss 计时 + 停止后生成保留原始格式的本地草稿（US-012）。
//
// 前端不转码（ADR-1）：录音请求 mp3（体积小、兼容性好），但 original_format 以微信实际产出的
// 临时文件为准；OSS object key 预览始终用 .wav 目标扩展名，仅表示 Worker 标准化目标。

const { createLogger } = require('../../utils/logger')
const { formatDuration, buildDraftManifest } = require('../../utils/audio')

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
  },

  onLoad() {
    this.recorder = wx.getRecorderManager()
    this.startedAt = 0
    this.timer = null
    this._bindRecorder()
    logger.info('index page loaded')
  },

  onUnload() {
    this._clearTimer()
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
    this.setData({ recording: true, durationText: '00:00', draft: null })
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
    const recordedAt = new Date(this.startedAt || Date.now())
    // 保留微信实际产出的本地临时音频文件路径与格式，前端不做任何转码。
    const draft = buildDraftManifest({
      recordedAt: recordedAt,
      tempFilePath: res && res.tempFilePath,
      requestedFormat: RECORD_FORMAT,
      durationMs: res && res.duration,
      fileSize: res && res.fileSize,
    })
    this.setData({
      recording: false,
      durationText: formatDuration(draft.duration_seconds),
      draft: draft,
    })
    // AC#5/#7/#8：草稿记录 audio.original_format，并在控制台 / vConsole 打印 original_format。
    logger.info('recording stopped', {
      original_format: draft.audio.original_format,
      duration_seconds: draft.duration_seconds,
      temp_file_path: draft.temp_file_path,
      object_key_preview: draft.object_key_preview,
    })
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
