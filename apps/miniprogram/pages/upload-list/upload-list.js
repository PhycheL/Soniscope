// 日观声记 · 上传列表页

var logger = require('../../utils/logger.js');
var constants = require('../../utils/constants.js');
var uploader = require('../../utils/uploader.js');

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
    // 从 local storage 加载上传记录
    try {
      var list = wx.getStorageSync('upload_list') || [];
      // 映射中文状态文案和进度信息
      list = list.map(function (item) {
        item.statusText = constants.UPLOAD_STATUS_CN[item.status] || item.status;
        // 进度百分比（uploading 状态时显示）
        if (item.status === 'uploading' && typeof item.uploadProgress !== 'undefined') {
          item.progressText = item.uploadProgress + '%';
        } else {
          item.progressText = '';
        }
        return item;
      });
      this.setData({ uploadList: list });
      logger.info('[UploadList] loaded', list.length, 'records');
    } catch (e) {
      logger.error('[UploadList] load failed:', e);
    }
  },

  // ── 手动重传 ────────────────────────────────────────

  onManualRetry: function (e) {
    var fragmentId = e.currentTarget.dataset.fragmentId;
    logger.info('[UploadList] manual retry triggered for', fragmentId);
    uploader.triggerManualRetry(fragmentId);
    // Reload list after a short delay to show updated status
    var that = this;
    setTimeout(function () {
      that._loadUploadList();
    }, 500);
  },
});

