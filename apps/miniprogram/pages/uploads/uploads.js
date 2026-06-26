// 上传列表页（骨架）。八种状态展示、离线提示、长录音折叠在 US-019 实现。

const { createLogger } = require('../../utils/logger')

const logger = createLogger('uploads')

Page({
  data: {
    items: [],
  },
  onLoad() {
    logger.info('uploads page loaded')
  },
})
