// 开发者故障注入菜单（US-020）：仅非 production 可见，运行时切换三个故障开关，
// 无需修改源码或重新编译小程序（AC#1/#5）。开关效果由 uploads 页的请求适配器读取生效。

const config = require('../../config')
const { createLogger } = require('../../utils/logger')
const faultInjection = require('../../utils/fault_injection')

const logger = createLogger('dev')

Page({
  data: {
    // production 时为 false，模板只展示「生产环境不可用」兜底文案（AC#1）。
    devEnv: false,
    switches: [],
  },

  onLoad() {
    if (!faultInjection.isDevEnv(config.ENV)) {
      // production：菜单不可用（双重兜底，正常入口在 production 下不可见）。
      this.setData({ devEnv: false, switches: [] })
      return
    }
    this.setData({ devEnv: true })
    this._refresh()
  },

  onShow() {
    if (faultInjection.isDevEnv(config.ENV)) {
      this._refresh()
    }
  },

  _refresh() {
    this.setData({ switches: faultInjection.buildSwitchViews(this._load()) })
  },

  _load() {
    return faultInjection.loadFaults(this._storageDeps())
  },

  _storageDeps() {
    return {
      env: config.ENV,
      getStorage: (k) => wx.getStorageSync(k),
      setStorage: (k, v) => wx.setStorageSync(k, v),
    }
  },

  // 运行时切换某个开关（AC#5：无需改源码 / 重新编译）。
  onToggleSwitch(e) {
    const name = e && e.currentTarget && e.currentTarget.dataset.name
    if (!name || !faultInjection.isDevEnv(config.ENV)) {
      return
    }
    const next = faultInjection.toggleFault(this._load(), name)
    faultInjection.saveFaults(this._storageDeps(), next)
    logger.info('fault injection toggled', { name: name, enabled: !!next[name] })
    this._refresh()
  },
})
