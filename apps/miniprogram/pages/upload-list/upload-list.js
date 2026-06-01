// 日观声记 · 上传列表页

var logger = require('../../utils/logger.js');
var constants = require('../../utils/constants.js');

Page({
  data: {
    uploadList: [],
  },

  onLoad: function () {
    logger.info('[UploadList] onLoad');
    this._loadUploadList();
  },

  onShow: function () {
    logger.info('[UploadList] onShow');
    this._loadUploadList();
  },

  _loadUploadList: function () {
    // 本期骨架：从 local storage 加载上传记录
    try {
      var list = wx.getStorageSync('upload_list') || [];
      // 映射中文状态文案
      list = list.map(function (item) {
        item.statusText = constants.UPLOAD_STATUS_CN[item.status] || item.status;
        return item;
      });
      this.setData({ uploadList: list });
      logger.info('[UploadList] loaded', list.length, 'records');
    } catch (e) {
      logger.error('[UploadList] load failed:', e);
    }
  },
});
