// SoniScope 微信小程序 · 日观声记
// 本期 MVP：极薄前端 — 只做采集、草稿、上传、状态展示
// 不做业务鉴权、不保存长期密钥

var logger = require('./utils/logger.js');

App({
  onLaunch: function () {
    logger.info('[App] onLaunch');

    // 初始化本地存储检查
    this._checkStorage();
  },

  onShow: function () {
    logger.info('[App] onShow');
  },

  onHide: function () {
    logger.info('[App] onHide');
  },

  onError: function (msg) {
    logger.error('[App] onError:', msg);
  },

  _checkStorage: function () {
    try {
      var info = wx.getStorageInfoSync();
      logger.info('[App] Storage info — currentSize:', info.currentSize, 'limitSize:', info.limitSize);
    } catch (e) {
      logger.warn('[App] Storage check failed:', e);
    }
  },

  globalData: {
    // 本期 MVP 全局数据
  }
});
