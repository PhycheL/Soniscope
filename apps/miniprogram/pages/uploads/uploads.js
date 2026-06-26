// 上传列表页：US-014 起读取本地上传队列并展示「待上传 / 上传中」记录。
// 八种状态全量展示、离线提示、长录音折叠在 US-019 实现。

const { createLogger } = require('../../utils/logger')
const { UPLOAD_QUEUE_STORAGE_KEY } = require('../../utils/upload_queue')

const logger = createLogger('uploads')

Page({
  data: {
    items: [],
  },
  onLoad() {
    logger.info('uploads page loaded')
  },
  // 每次切到本页（含从录音页「保存并上传」后切 tab）刷新队列。
  onShow() {
    this._loadQueue()
  },
  _loadQueue() {
    let queue = []
    try {
      queue = wx.getStorageSync(UPLOAD_QUEUE_STORAGE_KEY) || []
    } catch (e) {
      queue = []
    }
    this.setData({ items: queue })
  },
})
