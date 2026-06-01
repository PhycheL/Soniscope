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

  // ── 重新 verify（verified 记录重新检查 OSS） ────────

  onReVerify: function (e) {
    var fragmentId = e.currentTarget.dataset.fragmentId;
    logger.info('[UploadList] re-verify triggered for', fragmentId);
    uploader.triggerReVerify(fragmentId);
    var that = this;
    setTimeout(function () {
      that._loadUploadList();
    }, 500);
  },

  // ── 删除记录 ────────────────────────────────────────

  onDeleteRecord: function (e) {
    var fragmentId = e.currentTarget.dataset.fragmentId;
    var status = e.currentTarget.dataset.status;

    logger.info('[UploadList] delete triggered for', fragmentId, 'status:', status);

    // AC7: 未 verify 通过的记录删除需要二次确认
    var isVerified = status === constants.UPLOAD_STATUS.VERIFIED;
    var that = this;

    if (isVerified) {
      // Verified records: simple confirmation
      wx.showModal({
        title: '删除记录',
        content: '确定从列表中删除此上传记录吗？云端 OSS 对象不会受影响。',
        success: function (res) {
          if (res.confirm) {
            _doDelete(that, fragmentId);
          }
        },
      });
    } else {
      // AC7: Non-verified records: double confirmation
      wx.showModal({
        title: '⚠️ 警告',
        content: '该录音尚未成功上传到云端，删除后无法恢复，确定删除？',
        confirmText: '确定删除',
        confirmColor: '#f5222d',
        success: function (res) {
          if (res.confirm) {
            // 二次确认
            wx.showModal({
              title: '再次确认',
              content: '删除后音频将永久丢失，确认删除？',
              confirmText: '确认删除',
              confirmColor: '#f5222d',
              success: function (res2) {
                if (res2.confirm) {
                  _doDelete(that, fragmentId);
                }
              },
            });
          }
        },
      });
    }

    function _doDelete(page, fid) {
      var result = uploader.deleteRecord(fid);
      if (result.success) {
        wx.showToast({ title: '记录已删除', icon: 'success', duration: 1500 });
        page._loadUploadList();
      } else {
        wx.showToast({ title: '删除失败', icon: 'none', duration: 1500 });
      }
    }
  },
});
