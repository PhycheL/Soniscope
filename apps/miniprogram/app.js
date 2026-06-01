// SoniScope 微信小程序 · 日观声记
// 本期 MVP：极薄前端 — 只做采集、草稿、上传、状态展示
// 不做业务鉴权、不保存长期密钥

var logger = require('./utils/logger.js');
var idgen = require('./utils/idgen.js');
var uploader = require('./utils/uploader.js');

App({
  onLaunch: function () {
    logger.info('[App] onLaunch');

    // 初始化本地存储检查
    this._checkStorage();

    // 首次启动生成 device_short_id 并持久化
    var deviceId = idgen.getOrCreateDeviceShortId();
    this.globalData.deviceShortId = deviceId;
    logger.info('[App] device_short_id ensured:', deviceId);

    // 初始化上传引擎（注册网络状态监听，自动处理离线排队→恢复上传）
    uploader.initUploader();
  },

  onShow: function () {
    logger.info('[App] onShow');
    // 确保 device_short_id 在 globalData 中可用(覆盖冷启动后 onLaunch 已完成的情形)
    if (!this.globalData.deviceShortId) {
      var idgen = require('./utils/idgen.js');
      this.globalData.deviceShortId = idgen.getOrCreateDeviceShortId();
    }
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
    deviceShortId: '' // 首次启动由 onLaunch 初始化
  }
});
