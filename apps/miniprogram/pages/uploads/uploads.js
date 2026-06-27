// 上传列表页：读取本地上传队列并展示记录，自动驱动上传与 verify 流程。
//
// US-014 起渲染「待上传 / 上传中」；US-017 起 onShow 自动处理 queued 项：
//   静默登录 → 获取单文件 STS → OSS 直传，按状态机迁移 uploading → 待 verify / 待人工重传。
// US-018 起 onShow 再驱动 pending_verify 项的 verify 回执（待 verify → 上传成功 /
//   待人工重传 / 待人工 verify），并执行 48 小时本地缓存自动清理与手动删除二次确认。
// US-019 起渲染八种状态中文文案、顶部离线积压提示、长录音折叠卡片，并提供手动重传入口。

const { createLogger } = require('../../utils/logger')
const config = require('../../config')
const {
  UPLOAD_QUEUE_STORAGE_KEY,
  STATUS_QUEUED,
  STATUS_PENDING_VERIFY,
  updateQueueItem,
} = require('../../utils/upload_queue')
const { uploadFragment } = require('../../utils/uploader')
const { verifyFragment } = require('../../utils/verify')
const {
  selectAutoDeletable,
  needsDeleteConfirmation,
  DELETE_CONFIRM_MESSAGE,
} = require('../../utils/retention')
const { buildCards, buildBanner } = require('../../utils/uploads_view')

const logger = createLogger('uploads')

Page({
  data: {
    cards: [],
    banner: { visible: false, count: 0, hours: 0, text: '' },
    // 展开的长录音 session_id 集合（AC#8：展开后才显示每个 chunk）。
    expanded: {},
  },

  onLoad() {
    // 同一时刻只跑一个上传 / verify 循环，避免重复 onShow 并发处理。
    this._processing = false
    this._verifying = false
    logger.info('uploads page loaded')
  },

  // 每次切到本页（含从录音页「保存并上传」后切 tab）：清理本地缓存 → 刷新队列 → 上传 → verify。
  onShow() {
    this._autoCleanup()
    this._loadQueue()
    this._driveQueue()
  },

  // 先跑上传（queued → 待 verify），再跑 verify（待 verify → 上传成功 / 待人工…），串行执行。
  async _driveQueue() {
    await this._processQueue()
    await this._processVerifyQueue()
  },

  _loadQueue() {
    this._render(this._readQueue())
  },

  // 把扁平队列渲染为视图模型：折叠卡片（AC#6-#8）+ 顶部积压提示（AC#4）。
  _render(queue) {
    this.setData({
      cards: buildCards(queue),
      banner: buildBanner(queue, Date.now()),
    })
  },

  // AC#8：展开 / 收起某条长录音卡片，显示其各 chunk。
  onToggleSession(e) {
    const sessionId = e && e.currentTarget && e.currentTarget.dataset.sid
    if (!sessionId) {
      return
    }
    const expanded = Object.assign({}, this.data.expanded)
    expanded[sessionId] = !expanded[sessionId]
    this.setData({ expanded: expanded })
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
    this._render(queue)
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

  // 依次处理所有 pending_verify 项（US-018 AC#1：OSS 2xx 后自动 verify）。
  async _processVerifyQueue() {
    if (this._verifying) {
      return
    }
    this._verifying = true
    try {
      const online = await this._isOnline()
      if (!online) {
        logger.info('offline, skip auto verify')
        return
      }
      let queue = this._readQueue()
      for (let i = 0; i < queue.length; i++) {
        const item = queue[i]
        if (!item || item.status !== STATUS_PENDING_VERIFY) {
          continue
        }
        await this._verifyOne(item.fragmentId)
        queue = this._readQueue()
      }
    } finally {
      this._verifying = false
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
      onStatus: (status, extra) =>
        self._patchItem(fragmentId, Object.assign({ status: status }, extra)),
      onProgress: (percent) => self._patchItem(fragmentId, { progress: percent }),
    }
    await uploadFragment(item, deps)
  },

  // verify 单条：构造注入依赖，交给纯逻辑 verify.verifyFragment（AC#1-#4）。
  async _verifyOne(fragmentId) {
    const item = this._readQueue().find((it) => it && it.fragmentId === fragmentId)
    if (!item) {
      return
    }
    const self = this
    const deps = {
      logger: logger,
      now: () => Date.now(),
      login: () => self._wxLogin(),
      requestVerify: (code, fid, size) => self._wxRequestVerify(code, fid, size),
      wait: (ms) => new Promise((r) => setTimeout(r, ms)),
      onStatus: (status, extra) =>
        self._patchItem(fragmentId, Object.assign({ status: status }, extra)),
    }
    await verifyFragment(item, deps)
  },

  // 手动重新 verify（待 verify / 待人工 verify / verified 记录可点击重试 verify）。
  async onTapReVerify(e) {
    const fragmentId = e && e.currentTarget && e.currentTarget.dataset.fid
    if (!fragmentId) {
      return
    }
    await this._verifyOne(fragmentId)
  },

  // 手动重传（US-019 AC#2/#3）：重置该 Fragment / chunk 的重试计数（清错误码、状态回 queued），
  // 重新执行 获取 STS → OSS 上传 → verify 流程；只影响该条，不触碰同 session 其它 chunk（AC#8）。
  async onTapManualRetry(e) {
    const fragmentId = e && e.currentTarget && e.currentTarget.dataset.fid
    if (!fragmentId) {
      return
    }
    this._patchItem(fragmentId, {
      status: STATUS_QUEUED,
      errorCode: '',
      reason: '',
      progress: 0,
    })
    logger.info('manual retry requested', { fragmentId: fragmentId })
    await this._uploadOne(fragmentId)
    const after = this._readQueue().find((it) => it && it.fragmentId === fragmentId)
    if (after && after.status === STATUS_PENDING_VERIFY) {
      await this._verifyOne(fragmentId)
    }
    this._loadQueue()
  },

  // 手动删除（AC#7：未 verify 通过的记录二次确认；verified 记录可直接删除）。
  onTapDelete(e) {
    const fragmentId = e && e.currentTarget && e.currentTarget.dataset.fid
    if (!fragmentId) {
      return
    }
    const item = this._readQueue().find((it) => it && it.fragmentId === fragmentId)
    if (!item) {
      return
    }
    const self = this
    if (needsDeleteConfirmation(item)) {
      wx.showModal({
        title: '确认删除',
        content: DELETE_CONFIRM_MESSAGE,
        success: (res) => {
          if (res && res.confirm) {
            self._deleteItem(fragmentId)
          }
        },
      })
      return
    }
    this._deleteItem(fragmentId)
  },

  _deleteItem(fragmentId) {
    const item = this._readQueue().find((it) => it && it.fragmentId === fragmentId)
    if (item) {
      this._unlinkFile(item.tempFilePath)
    }
    const next = this._readQueue().filter((it) => !(it && it.fragmentId === fragmentId))
    this._writeQueue(next)
  },

  // 自动清理本地音频缓存（AC#5）：只删 verified 且 verified_at 距今 >= 48 小时的本地文件，
  // 保留队列记录与 OSS 对象（AGENTS：OSS 永不删除）。
  _autoCleanup() {
    const deletable = selectAutoDeletable(this._readQueue(), Date.now())
    if (!deletable.length) {
      return
    }
    deletable.forEach((it) => {
      this._unlinkFile(it.tempFilePath)
      const next = updateQueueItem(this._readQueue(), it.fragmentId, { localDeleted: true })
      wx.setStorageSync(UPLOAD_QUEUE_STORAGE_KEY, next)
      logger.info('local cache auto-cleaned (verified >= 48h)', { fragmentId: it.fragmentId })
    })
    this._loadQueue()
  },

  _unlinkFile(filePath) {
    if (!filePath) {
      return
    }
    try {
      wx.getFileSystemManager().unlink({ filePath: filePath, success() {}, fail() {} })
    } catch (e) {
      // best-effort：临时文件可能已不存在。
    }
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

  _wxRequestVerify(code, fragmentId, expectedSize) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: config.FC_VERIFY_UPLOAD_URL,
        method: 'POST',
        header: { 'content-type': 'application/json' },
        data: { code: code, fragment_id: fragmentId, expected_size: expectedSize },
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
