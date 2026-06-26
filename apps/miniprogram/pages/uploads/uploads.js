// 上传列表页：读取本地上传队列并展示记录，自动驱动「待上传」项的上传流程（US-017）。
//
// US-014 起渲染「待上传 / 上传中」；US-017 起 onShow 自动处理 queued 项：
//   静默登录 → 获取单文件 STS → OSS 直传，按状态机迁移 uploading → 待 verify / 待人工重传。
// 八种状态全量展示、离线积压提示、长录音折叠在 US-019；verify 回执在 US-018。

const { createLogger } = require('../../utils/logger')
const config = require('../../config')
const {
  UPLOAD_QUEUE_STORAGE_KEY,
  STATUS_QUEUED,
  updateQueueItem,
} = require('../../utils/upload_queue')
const { uploadFragment } = require('../../utils/uploader')

const logger = createLogger('uploads')

Page({
  data: {
    items: [],
  },

  onLoad() {
    // 同一时刻只跑一个上传循环，避免重复 onShow 并发处理。
    this._processing = false
    logger.info('uploads page loaded')
  },

  // 每次切到本页（含从录音页「保存并上传」后切 tab）刷新队列并尝试上传。
  onShow() {
    this._loadQueue()
    this._processQueue()
  },

  _loadQueue() {
    this.setData({ items: this._readQueue() })
  },

  _readQueue() {
    try {
      return wx.getStorageSync(UPLOAD_QUEUE_STORAGE_KEY) || []
    } catch (e) {
      return []
    }
  },

  _writeQueue(queue) {
    wx.setStorageSync(UPLOAD_QUEUE_STORAGE_KEY, queue)
    this.setData({ items: queue })
  },

  // 依次处理所有 queued 项（US-017 AC#1：网络可用进入上传中）。
  async _processQueue() {
    if (this._processing) {
      return
    }
    this._processing = true
    try {
      // 简单网络可用性判断；离线积压（待上传）与恢复后自动上传在 US-019 完整落地。
      const online = await this._isOnline()
      if (!online) {
        logger.info('offline, skip auto upload')
        return
      }
      let queue = this._readQueue()
      for (let i = 0; i < queue.length; i++) {
        const item = queue[i]
        if (!item || item.status !== STATUS_QUEUED) {
          continue
        }
        await this._uploadOne(item.fragmentId)
        queue = this._readQueue()
      }
    } finally {
      this._processing = false
    }
  },

  _isOnline() {
    return new Promise((resolve) => {
      try {
        wx.getNetworkType({
          success: (res) => resolve(res && res.networkType && res.networkType !== 'none'),
          fail: () => resolve(true),
        })
      } catch (e) {
        resolve(true)
      }
    })
  },

  // 上传单条：构造注入依赖（真实 wx 适配器），交给纯逻辑 uploader.uploadFragment。
  async _uploadOne(fragmentId) {
    const item = this._readQueue().find((it) => it && it.fragmentId === fragmentId)
    if (!item) {
      return
    }
    const self = this
    const deps = {
      logger: logger,
      region: config.OSS_REGION,
      uploadUrl: config.OSS_UPLOAD_URL,
      now: () => new Date(),
      login: () => self._wxLogin(),
      requestSts: (code, fid, size) => self._wxRequestSts(code, fid, size),
      uploadFile: (opts) => self._wxUploadFile(opts),
      wait: (ms) => new Promise((r) => setTimeout(r, ms)),
      // 状态迁移即时落盘，保证中途中断后列表状态可恢复。
      onStatus: (status, extra) => self._patchItem(fragmentId, Object.assign({ status: status }, extra)),
      onProgress: (percent) => self._patchItem(fragmentId, { progress: percent }),
    }
    await uploadFragment(item, deps)
  },

  _patchItem(fragmentId, patch) {
    const queue = updateQueueItem(this._readQueue(), fragmentId, patch)
    this._writeQueue(queue)
  },

  _wxLogin() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (res) => (res && res.code ? resolve(res.code) : reject(new Error('NO_CODE'))),
        fail: (err) => reject(err),
      })
    })
  },

  _wxRequestSts(code, fragmentId, size) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: config.FC_ISSUE_CREDENTIAL_URL,
        method: 'POST',
        header: { 'content-type': 'application/json' },
        data: { code: code, fragment_id: fragmentId, size: size },
        success: (res) => resolve({ statusCode: res.statusCode, data: res.data }),
        fail: (err) => reject(err),
      })
    })
  },

  _wxUploadFile(opts) {
    return new Promise((resolve, reject) => {
      const task = wx.uploadFile({
        url: opts.url,
        filePath: opts.filePath,
        name: opts.name,
        formData: opts.formData,
        success: (res) => resolve({ statusCode: res.statusCode, data: res.data }),
        fail: (err) => reject(err),
      })
      if (task && task.onProgressUpdate && opts.onProgress) {
        task.onProgressUpdate((p) => opts.onProgress(p.progress))
      }
    })
  },
})
