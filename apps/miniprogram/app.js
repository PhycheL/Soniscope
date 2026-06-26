// 日观声记 SoniScope 小程序入口。
// 极薄前端：只做采集、草稿、本地缓存、上传、状态展示；不保存长期密钥、不做业务鉴权。

const config = require('./config')
const { createLogger } = require('./utils/logger')
const { ensureDeviceShortId } = require('./utils/device')

const logger = createLogger('app')

App({
  globalData: {
    env: config.ENV,
  },
  onLaunch() {
    // US-015 AC#1：首次启动生成并持久化 device_short_id（4-8 字符），冷启动保持不变。
    const deviceShortId = ensureDeviceShortId(wx)
    this.globalData.deviceShortId = deviceShortId
    logger.info('app launched', { env: config.ENV, deviceShortId: deviceShortId })
  },
  onError(err) {
    logger.error('app error', err)
  },
})
