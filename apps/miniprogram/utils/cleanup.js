// SoniScope · 本地缓存自动清理模块
//
// 负责：
// - 自动清理 verified:true 且 verified_at >= 48 小时的本地记录和缓存
// - verified:false、待人工重传、待人工 verify 的文件永不自动删除
// - 手动删除记录（含未 verify 通过的二次确认逻辑）

var constants = require('./constants.js');
var logger = require('./logger.js');

// ── Public API ────────────────────────────────────────────────────

/**
 * 自动清理已 verify 通过且超过 48 小时的本地缓存记录。
 *
 * 清理策略：
 *  - 只删除 verified:true 的记录
 *  - 必须 verified_at 距当前时间 >= 48 小时
 *  - 未 verify 通过（manual_retry、manual_verify 等）永不自动删除
 *
 * 应在以下时机调用:
 *  - app.onLaunch（启动时扫描）
 *  - 每条 verify 成功后
 *
 * @returns {number} 本次清理的条数
 */
function runAutoCleanup() {
  try {
    var list = _loadUploadList();
    if (list.length === 0) return 0;

    var now = Date.now();
    var retentionMs = constants.AUDIO_RETENTION_MS; // 48 小时（毫秒）
    var removed = 0;
    var kept = [];

    for (var i = 0; i < list.length; i++) {
      var record = list[i];

      // AC6: 只自动清理 VERIFIED 记录
      if (record.status !== constants.UPLOAD_STATUS.VERIFIED) {
        kept.push(record);
        continue;
      }

      // 必须有 verifiedAt 时间戳
      if (!record.verifiedAt) {
        kept.push(record);
        continue;
      }

      // AC5: verified_at >= 48 小时才可清理
      var verifiedTime = new Date(record.verifiedAt).getTime();
      if (isNaN(verifiedTime) || now - verifiedTime < retentionMs) {
        kept.push(record);
        continue;
      }

      // 可安全清理：记录已 verify 通过且超过 48 小时
      logger.info('[Cleanup] auto-cleaning verified record (48h+):',
        record.fragmentId,
        'verified_at:', record.verifiedAt);

      // 尝试清理本地临时文件（如仍存在）
      _tryRemoveFile(record.tempFilePath);

      removed++;
    }

    if (removed > 0) {
      _saveUploadList(kept);
      logger.info('[Cleanup] auto-cleaned', removed,
        'verified record(s),', kept.length, 'remaining');
    }

    return removed;
  } catch (e) {
    logger.error('[Cleanup] auto-cleanup error:', e);
    return 0;
  }
}

/**
 * 手动删除一条上传记录。
 *
 * AC7: 对未 verify 通过的记录，调用方应先用 wx.showModal 做二次确认
 * （文案："该录音尚未成功上传到云端，删除后无法恢复，确定删除？"）
 *
 * @param {string} fragmentId - 要删除的 fragment_id
 * @returns {{ success: boolean, wasVerified: boolean }} 删除结果
 */
function deleteRecordById(fragmentId) {
  try {
    var list = _loadUploadList();
    var targetIndex = -1;
    var wasVerified = false;

    for (var i = 0; i < list.length; i++) {
      if (list[i].fragmentId === fragmentId) {
        targetIndex = i;
        wasVerified = list[i].status === constants.UPLOAD_STATUS.VERIFIED;
        break;
      }
    }

    if (targetIndex < 0) {
      logger.warn('[Cleanup] deleteRecordById: record not found:', fragmentId);
      return { success: false, wasVerified: false };
    }

    var record = list[targetIndex];

    // 尝试清理本地临时文件
    _tryRemoveFile(record.tempFilePath);

    list.splice(targetIndex, 1);
    _saveUploadList(list);

    logger.info('[Cleanup] manually deleted record:', fragmentId,
      'was_verified:', wasVerified);

    return { success: true, wasVerified: wasVerified };
  } catch (e) {
    logger.error('[Cleanup] deleteRecordById error:', e);
    return { success: false, wasVerified: false };
  }
}

// ── Internal helpers ──────────────────────────────────────────────

/**
 * 尝试删除本地临时文件，文件不存在也不报错。
 */
function _tryRemoveFile(filePath) {
  if (!filePath) return;
  try {
    var fs = wx.getFileSystemManager();
    // 检查文件是否存在后再删除
    fs.access({
      path: filePath,
      success: function () {
        fs.unlink({
          filePath: filePath,
          success: function () {
            logger.info('[Cleanup] removed temp file:', filePath);
          },
          fail: function (err) {
            logger.warn('[Cleanup] failed to unlink temp file:', filePath, err);
          }
        });
      },
      fail: function () {
        // File doesn't exist — nothing to do
      }
    });
  } catch (e) {
    // access API 可能在某些版本不可用，忽略
  }
}

function _loadUploadList() {
  try {
    return wx.getStorageSync('upload_list') || [];
  } catch (e) {
    return [];
  }
}

function _saveUploadList(list) {
  try {
    wx.setStorageSync('upload_list', list);
  } catch (e) {
    logger.error('[Cleanup] failed to save upload list:', e);
  }
}

// ── Exports ───────────────────────────────────────────────────────

module.exports = {
  runAutoCleanup: runAutoCleanup,
  deleteRecordById: deleteRecordById,
  // Exported for testing
  _loadUploadList: _loadUploadList,
  _saveUploadList: _saveUploadList,
  _tryRemoveFile: _tryRemoveFile,
};
