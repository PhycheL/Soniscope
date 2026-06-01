// 日观声记 · 上传列表页
// US-019: 八种状态展示、离线积压提醒、长录音折叠展示

var logger = require('../../utils/logger.js');
var constants = require('../../utils/constants.js');
var uploader = require('../../utils/uploader.js');

Page({
  data: {
    sessionCards: [],       // 长录音聚合卡片（chunkTotal > 1）
    individualRecords: [],  // 单 chunk 或非 session 记录
    showBanner: false,      // 顶部未上传提醒横幅
    pendingCount: 0,        // 未上传数量
    hoursSinceEarliest: '',  // 距离最早录音的小时数
    totalRecords: 0,        // 总记录数
  },

  onLoad: function () {
    logger.info('[UploadList] onLoad');
    this._loadUploadList();
  },

  onShow: function () {
    logger.info('[UploadList] onShow');
    this._loadUploadList();
  },

  // ── 数据加载与分组 ─────────────────────────────────────────

  _loadUploadList: function () {
    try {
      var rawList = wx.getStorageSync('upload_list') || [];

      // ── 按 sessionId 分组 ────────────────────────────────
      var sessionMap = {};
      var individualRecords = [];

      for (var i = 0; i < rawList.length; i++) {
        var item = rawList[i];
        // AC6: 同一 session_id 且有多个 chunk 的记录聚合为长录音卡片
        if (item.sessionId && item.chunkTotal > 1) {
          var sid = item.sessionId;
          if (!sessionMap[sid]) {
            sessionMap[sid] = [];
          }
          sessionMap[sid].push(item);
        } else {
          individualRecords.push(item);
        }
      }

      // ── 构建 session 聚合卡片 ────────────────────────────
      var sessionCards = [];
      var sessionIds = Object.keys(sessionMap);

      for (var si = 0; si < sessionIds.length; si++) {
        var sid = sessionIds[si];
        var chunks = sessionMap[sid];

        // 按 chunkSeq 排序
        chunks.sort(function (a, b) {
          return (a.chunkSeq || 0) - (b.chunkSeq || 0);
        });

        var totalDuration = 0;
        var allVerified = true;
        var failedCount = 0;

        for (var ci = 0; ci < chunks.length; ci++) {
          totalDuration += (chunks[ci].duration || 0);
          chunks[ci].statusText = constants.UPLOAD_STATUS_CN[chunks[ci].status] || chunks[ci].status;

          if (chunks[ci].status !== constants.UPLOAD_STATUS.VERIFIED) {
            allVerified = false;
          }
          // AC7: 统计失败/需关注的 chunk
          if (chunks[ci].status === constants.UPLOAD_STATUS.MANUAL_RETRY ||
              chunks[ci].status === constants.UPLOAD_STATUS.MANUAL_VERIFY ||
              chunks[ci].status === constants.UPLOAD_STATUS.UPLOAD_FAILED) {
            failedCount++;
          }
        }

        sessionCards.push({
          sessionId: sid,
          chunks: chunks,
          totalDuration: totalDuration,
          totalDurationDisplay: _formatDuration(totalDuration),
          chunkCount: chunks.length,
          allVerified: allVerified,
          failedCount: failedCount,
          expanded: false,  // 默认折叠
        });
      }

      // ── 构建单条记录展示 ─────────────────────────────────
      for (var ir = 0; ir < individualRecords.length; ir++) {
        var rec = individualRecords[ir];
        rec.statusText = constants.UPLOAD_STATUS_CN[rec.status] || rec.status;
        if (rec.status === 'uploading' && typeof rec.uploadProgress !== 'undefined') {
          rec.progressText = rec.uploadProgress + '%';
        } else {
          rec.progressText = '';
        }
      }

      // ── 计算顶部横幅（AC4） ──────────────────────────────
      var pendingCount = 0;
      var earliestTime = null;

      for (var br = 0; br < rawList.length; br++) {
        var rec = rawList[br];
        var st = rec.status;

        // AC4: 统计所有未完成/需关注的上传记录
        if (st === constants.UPLOAD_STATUS.QUEUED ||
            st === constants.UPLOAD_STATUS.UPLOADING ||
            st === constants.UPLOAD_STATUS.UPLOAD_FAILED ||
            st === constants.UPLOAD_STATUS.MANUAL_RETRY ||
            st === constants.UPLOAD_STATUS.MANUAL_VERIFY ||
            st === constants.UPLOAD_STATUS.PENDING_VERIFY) {
          pendingCount++;
        }

        if (rec.recordedAt) {
          var t = new Date(rec.recordedAt).getTime();
          if (!isNaN(t) && (earliestTime === null || t < earliestTime)) {
            earliestTime = t;
          }
        }
      }

      var hoursSinceEarliest = '';
      if (earliestTime !== null) {
        var diffMs = Date.now() - earliestTime;
        var diffHours = Math.max(0, Math.floor(diffMs / (1000 * 60 * 60)));
        hoursSinceEarliest = String(diffHours);
      }

      this.setData({
        sessionCards: sessionCards,
        individualRecords: individualRecords,
        showBanner: pendingCount > 0,
        pendingCount: pendingCount,
        hoursSinceEarliest: hoursSinceEarliest,
        totalRecords: rawList.length,
      });

      logger.info('[UploadList] loaded', rawList.length, 'records,',
        sessionCards.length, 'session cards,', pendingCount, 'pending');
    } catch (e) {
      logger.error('[UploadList] load failed:', e);
    }
  },

  // ── 长录音卡片折叠/展开（AC6/AC8） ──────────────────────

  onToggleSession: function (e) {
    var sessionId = e.currentTarget.dataset.sessionId;
    var cards = this.data.sessionCards;
    for (var i = 0; i < cards.length; i++) {
      if (cards[i].sessionId === sessionId) {
        cards[i].expanded = !cards[i].expanded;
        break;
      }
    }
    this.setData({ sessionCards: cards });
  },

  // ── 手动重传（单条记录） ─────────────────────────────────

  onManualRetry: function (e) {
    var fragmentId = e.currentTarget.dataset.fragmentId;
    logger.info('[UploadList] manual retry triggered for', fragmentId);
    uploader.triggerManualRetry(fragmentId);
    var that = this;
    setTimeout(function () {
      that._loadUploadList();
    }, 500);
  },

  // ── session 内单个 chunk 手动重传（AC8） ─────────────────

  onRetryChunk: function (e) {
    var fragmentId = e.currentTarget.dataset.fragmentId;
    logger.info('[UploadList] chunk retry triggered for', fragmentId);
    uploader.triggerManualRetry(fragmentId);
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

  // ── 删除记录 ────────────────────────────────────────────

  onDeleteRecord: function (e) {
    var fragmentId = e.currentTarget.dataset.fragmentId;
    var status = e.currentTarget.dataset.status;

    logger.info('[UploadList] delete triggered for', fragmentId, 'status:', status);

    // AC7: 未 verify 通过的记录删除需要二次确认
    var isVerified = status === constants.UPLOAD_STATUS.VERIFIED;
    var that = this;

    if (isVerified) {
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
      wx.showModal({
        title: '⚠️ 警告',
        content: '该录音尚未成功上传到云端，删除后无法恢复，确定删除？',
        confirmText: '确定删除',
        confirmColor: '#f5222d',
        success: function (res) {
          if (res.confirm) {
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

// ── 工具函数 ──────────────────────────────────────────────────

function _formatDuration(totalSeconds) {
  var m = Math.floor(totalSeconds / 60);
  var s = totalSeconds % 60;
  return (m < 10 ? '0' + m : m) + ':' + (s < 10 ? '0' + s : s);
}
