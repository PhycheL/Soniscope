// 日观声记 SoniScope 小程序入口。
// 极薄前端：只做采集、草稿、本地缓存、上传、状态展示；不保存长期密钥、不做业务鉴权。

const config = require('./config')
const { createLogger } = require('./utils/logger')

const logger = createLogger('app')

App({
  globalData: {
    env: config.ENV,
  },
  onLaunch() {
    logger.info('app launched', { env: config.ENV })
  },
  onError(err) {
    logger.error('app error', err)
  },
})
