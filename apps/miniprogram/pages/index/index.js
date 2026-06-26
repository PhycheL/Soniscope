// 首页：录音入口（骨架）。完整录音开始/停止与计时在 US-012 实现。

const { createLogger } = require('../../utils/logger')

const logger = createLogger('index')

Page({
  data: {
    recording: false,
    durationText: '00:00',
  },
  onLoad() {
    logger.info('index page loaded')
  },
  // 录音按钮占位：真实录音逻辑在 US-012 接入 wx.getRecorderManager()。
  onTapRecord() {
    logger.info('record button tapped (skeleton)')
  },
  goUploads() {
    wx.switchTab({ url: '/pages/uploads/uploads' })
  },
})
