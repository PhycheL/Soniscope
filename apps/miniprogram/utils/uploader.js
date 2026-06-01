// SoniScope · 上传队列与 STS 直传引擎
//
// 负责：
// - 管理上传列表的八种状态流转
// - wx.login → FC /issue-credential 获取单文件 STS
// - wx.uploadFile 直传 OSS（附带全部 7 个 x-oss-meta-* 请求头）
// - /verify-upload 签收回执
// - 指数退避重试（5s/15s/45s，最多 3 次）
// - 离线感知：网络不可用时停留在 queued，恢复后自动继续

var constants = require('./constants.js');
var logger = require('./logger.js');

// ── Module-level state ────────────────────────────────────────────

var _uploadingActive = false;  // 是否有上传任务正在执行
var _networkAvailable = true;  // 当前网络状态

// ── Public API ────────────────────────────────────────────────────

/**
 * Initialize the upload engine.
 *
 * Registers a network-status listener so uploads automatically resume
 * when the device comes back online.
 */
function initUploader() {
  wx.onNetworkStatusChange(function (res) {
    var prev = _networkAvailable;
    _networkAvailable = res.isConnected;
    logger.info('[Uploader] network status changed: connected=', res.isConnected,
      'type=', res.networkType);

    if (!prev && res.isConnected) {
      // Network came back — try to process the queue
      logger.info('[Uploader] network restored, resuming uploads');
      processUploadQueue();
    }
  });

  // Initial network check
  wx.getNetworkType({
    success: function (res) {
      _networkAvailable = res.networkType !== 'none';
      logger.info('[Uploader] initial network: connected=', _networkAvailable,
        'type=', res.networkType);
      if (_networkAvailable) {
        processUploadQueue();
      }
    },
    fail: function () {
      _networkAvailable = true; // assume online if we can't determine
    }
  });
}

/**
 * Process the upload queue: find all QUEUED records and start uploading.
 *
 * Uploads are processed sequentially (one at a time) to avoid overwhelming
 * the wx.uploadFile concurrency limit.
 */
function processUploadQueue() {
  if (_uploadingActive) {
    logger.info('[Uploader] upload already in progress, will retry after current completes');
    return;
  }

  if (!_networkAvailable) {
    logger.info('[Uploader] offline, deferring uploads');
    return;
  }

  var list = _loadUploadList();
  var queued = [];

  // Find all queued items
  for (var i = 0; i < list.length; i++) {
    if (list[i].status === constants.UPLOAD_STATUS.QUEUED ||
        list[i].status === constants.UPLOAD_STATUS.MANUAL_RETRY) {
      queued.push(i);
    }
  }

  if (queued.length === 0) {
    logger.info('[Uploader] no queued items to upload');
    return;
  }

  logger.info('[Uploader] found', queued.length, 'queued item(s), starting upload');
  _uploadingActive = true;

  // Process first queued item; the chain continues in _uploadOne
  _uploadOne(list, queued[0]);
}

/**
 * Trigger upload for a specific record (e.g., manual retry from the UI).
 *
 * @param {string} fragmentId
 */
function triggerManualRetry(fragmentId) {
  var list = _loadUploadList();

  for (var i = 0; i < list.length; i++) {
    if (list[i].fragmentId === fragmentId) {
      // Reset retry count and set status to queued
      list[i].retryCount = 0;
      list[i].status = constants.UPLOAD_STATUS.QUEUED;
      list[i].statusText = constants.UPLOAD_STATUS_CN[list[i].status];
      _saveUploadList(list);
      logger.info('[Uploader] manual retry triggered for', fragmentId);

      // Update any active page's data
      _notifyPages(list);
      break;
    }
  }

  // Try to upload
  processUploadQueue();
}

// ── Internal: single-record upload pipeline ───────────────────────

/**
 * Upload one record from the list.
 *
 * Steps:
 *  1. wx.login → get code
 *  2. POST FC /issue-credential → get STS
 *  3. wx.uploadFile → OSS (STS auth + x-oss-meta-* headers)
 *  4. POST FC /verify-upload → verify receipt
 *
 * @param {Array} list  — full upload list
 * @param {number} index — index of the record to upload
 */
function _uploadOne(list, index) {
  if (index >= list.length) {
    // No more items to process
    _uploadingActive = false;
    return;
  }

  var record = list[index];
  if (!record || !record.fragmentId) {
    _uploadingActive = false;
    return;
  }

  logger.info('[Uploader] starting upload for', record.fragmentId,
    'chunk', record.chunkSeq + '/' + record.chunkTotal);

  _updateRecordStatus(list, index, constants.UPLOAD_STATUS.UPLOADING);
  _notifyPages(list);

  // ── Step 1: wx.login → get code ──
  _wxLogin(function (codeErr, code) {
    if (codeErr) {
      logger.error('[Uploader] wx.login failed:', codeErr);
      _handleUploadFailure(list, index, 'INVALID_CODE');
      return;
    }

    // ── Step 2: POST FC /issue-credential → get STS ──
    _fetchSts(record, code, function (stsErr, stsResult) {
      if (stsErr) {
        logger.error('[Uploader] STS fetch failed:', stsErr);
        _handleUploadFailure(list, index, stsErr.errorCode || 'STS_FAILED');
        return;
      }

      // ── Step 3: wx.uploadFile → OSS (with retry) ──
      _ossUploadWithRetry(record, stsResult, 0, function (ossErr) {
        if (ossErr) {
          logger.error('[Uploader] OSS upload failed:', ossErr);
          _handleUploadFailure(list, index, 'OSS_UPLOAD_FAILED');
          return;
        }

        // ── Step 4: POST FC /verify-upload ──
        _verifyUploadWithRetry(record, code, 0, function (verifyErr) {
          if (verifyErr) {
            logger.error('[Uploader] verify failed:', verifyErr);
            _handleVerifyFailure(list, index, verifyErr.reason || 'VERIFY_FAILED');
            _continueNext(list, index);
            return;
          }

          // ── All steps passed! ──
          logger.info('[Uploader] upload + verify complete for', record.fragmentId);
          _updateRecordStatus(list, index, constants.UPLOAD_STATUS.VERIFIED, {
            verifiedAt: new Date().toISOString()
          });
          _notifyPages(list);
          _continueNext(list, index);
        });
      });
    });
  });
}

/**
 * Continue to the next queued item after current one is done.
 */
function _continueNext(list, currentIndex) {
  // Find the next queued/manual_retry item
  for (var i = currentIndex + 1; i < list.length; i++) {
    if (list[i].status === constants.UPLOAD_STATUS.QUEUED ||
        list[i].status === constants.UPLOAD_STATUS.MANUAL_RETRY) {
      _uploadOne(list, i);
      return;
    }
  }

  // No more queued items
  _uploadingActive = false;
}

// ── wx.login wrapper ──────────────────────────────────────────────

function _wxLogin(callback) {
  wx.login({
    success: function (res) {
      if (res.code) {
        callback(null, res.code);
      } else {
        callback(new Error('wx.login returned no code'));
      }
    },
    fail: function (err) {
      callback(err);
    }
  });
}

// ── FC /issue-credential ──────────────────────────────────────────

function _fetchSts(record, code, callback) {
  var data = {
    code: code,
    fragment_id: record.fragmentId,
    size: record.size || record.audio.size_bytes || 0
  };

  logger.info('[Uploader] fetching STS for', record.fragmentId, 'size:', data.size);

  wx.request({
    url: constants.FC_ISSUE_CREDENTIAL_URL,
    method: 'POST',
    header: { 'Content-Type': 'application/json' },
    data: data,
    success: function (res) {
      if (res.statusCode === 200 && res.data && res.data.access_key_id) {
        logger.info('[Uploader] STS received for', record.fragmentId);
        callback(null, res.data);
      } else {
        var errMsg = (res.data && res.data.error) || 'UNKNOWN';
        var detail = (res.data && res.data.detail) || '';
        logger.error('[Uploader] STS fetch returned non-200:', res.statusCode, errMsg, detail);
        callback({ errorCode: errMsg, detail: detail });
      }
    },
    fail: function (err) {
      logger.error('[Uploader] STS fetch network error:', err);
      callback({ errorCode: 'NETWORK_ERROR', detail: err.errMsg || '' });
    }
  });
}

// ── OSS Direct Upload (with retries) ──────────────────────────────

function _ossUploadWithRetry(record, stsResult, attempt, callback) {
  if (attempt >= constants.UPLOAD_MAX_RETRIES) {
    logger.error('[Uploader] OSS upload exhausted retries for', record.fragmentId);
    callback(new Error('OSS_UPLOAD_MAX_RETRIES'));
    return;
  }

  if (attempt > 0) {
    var delay = constants.UPLOAD_RETRY_INTERVALS[attempt - 1] || 45000;
    logger.info('[Uploader] retrying OSS upload in', delay + 'ms',
      '(attempt', (attempt + 1) + '/' + constants.UPLOAD_MAX_RETRIES + ')');
    setTimeout(function () {
      _doOssUpload(record, stsResult, attempt, callback);
    }, delay);
  } else {
    _doOssUpload(record, stsResult, attempt, callback);
  }
}

function _doOssUpload(record, stsResult, attempt, callback) {
  var objectKey = stsResult.object_key;
  var uploadUrl = constants.OSS_UPLOAD_DOMAIN + '/' + objectKey;

  logger.info('[Uploader] uploading to OSS:', uploadUrl,
    'object_key:', objectKey);

  // Build form data for OSS PostObject
  // OSS STS upload requires: OSSAccessKeyId, Signature, policy, key, success_action_status
  // But with wx.uploadFile, we use the PUT method style via the filePath + header signature

  // For wx.uploadFile direct PUT to OSS with STS:
  // We need to use OSS's PostObject (multipart form upload) or signed PUT
  //
  // The practical approach for WeChat mini-programs: use OSS STS PostObject
  // with the form fields approach.
  //
  // wx.uploadFile sends a multipart form POST request.
  // OSS PostObject accepts multipart form POST with:
  // - OSSAccessKeyId
  // - Signature
  // - policy (base64-encoded JSON)
  // - key
  // - success_action_status
  // - x-oss-meta-* headers
  // - file (the actual file field)

  var formData = _buildOssFormData(stsResult, record);

  // Set the OSS host as the file upload name (wx.uploadFile uses 'name' for OSS's file field)
  // Actually, wx.uploadFile's `name` parameter is the form field name for the file.
  // OSS PostObject expects the file in the 'file' field.

  // For OSS direct upload with STS via wx.uploadFile,
  // we use PostObject (POST with multipart form)
  var uploadTask = wx.uploadFile({
    url: constants.OSS_UPLOAD_DOMAIN,
    filePath: record.tempFilePath,
    name: 'file',
    formData: formData,
    header: {
      // OSS PostObject doesn't require special headers beyond the form fields
      'Content-Type': 'multipart/form-data'
    },
    success: function (res) {
      logger.info('[Uploader] OSS HTTP', res.statusCode, 'for', record.fragmentId);

      if (res.statusCode >= 200 && res.statusCode < 300) {
        logger.info('[Uploader] OSS upload success for', record.fragmentId);
        callback(null);
      } else if (res.statusCode >= 400 && res.statusCode < 500) {
        // 4xx — don't retry
        logger.error('[Uploader] OSS 4xx error, not retrying:', res.statusCode);
        callback(new Error('OSS_4XX_ERROR'));
      } else {
        // 5xx — retry
        logger.error('[Uploader] OSS upload failed HTTP', res.statusCode, ', retrying...');
        _ossUploadWithRetry(record, stsResult, attempt + 1, callback);
      }
    },
    fail: function (err) {
      logger.error('[Uploader] OSS upload network error:', err);
      _ossUploadWithRetry(record, stsResult, attempt + 1, callback);
    }
  });

  // Track upload progress
  uploadTask.onProgressUpdate(function (progress) {
    // Update progress in the upload list
    var list = _loadUploadList();
    for (var i = 0; i < list.length; i++) {
      if (list[i].fragmentId === record.fragmentId) {
        list[i].uploadProgress = progress.progress;
        _saveUploadList(list);
        _notifyPages(list);
        break;
      }
    }
  });
}

/**
 * Build OSS PostObject form data from STS result.
 *
 * Uses the OSS STS PostObject approach:
 * - policy = base64-encoded JSON specifying expiration and conditions
 * - signature = HMAC-SHA1 of policy with STS access_key_secret
 * - OSSAccessKeyId = STS access_key_id
 * - x-oss-security-token = STS security_token
 */
function _buildOssFormData(stsResult, record) {
  var now = new Date();
  var expiration = new Date(now.getTime() + 900 * 1000); // 15 minutes

  // Use the OSS meta from the record
  var meta = record.ossMeta || {};

  // Build OSS PostObject policy
  var conditions = [
    { bucket: stsResult.bucket },
    { key: stsResult.object_key },
    { success_action_status: '200' },
    // Content-length range: 1 byte to 100 MB
    ['content-length-range', 1, 104857600]
  ];

  // Add conditions for each x-oss-meta-* header
  var metaKeys = Object.keys(meta);
  for (var mi = 0; mi < metaKeys.length; mi++) {
    conditions.push({ key: metaKeys[mi], value: String(meta[metaKeys[mi]]) });
  }

  var policyDoc = {
    expiration: expiration.toISOString(),
    conditions: conditions
  };

  var policyJson = JSON.stringify(policyDoc);
  var policyBase64 = _base64Encode(policyJson);
  var signature = _hmacSha1Base64(policyBase64, stsResult.access_key_secret);

  var formData = {
    OSSAccessKeyId: stsResult.access_key_id,
    Signature: signature,
    policy: policyBase64,
    key: stsResult.object_key,
    success_action_status: '200',
    'x-oss-security-token': stsResult.security_token,
  };

  // Add all x-oss-meta-* headers as form fields
  for (var mj = 0; mj < metaKeys.length; mj++) {
    formData[metaKeys[mj]] = String(meta[metaKeys[mj]]);
  }

  return formData;
}

/**
 * Base64 encode a UTF-8 string (for policy encoding).
 *
 * Uses wx.arrayBufferToBase64 for reliability across platforms.
 */
function _base64Encode(str) {
  // Simple base64 encode for policy (no btoa in WeChat mini-program)
  // We use the wx.arrayBufferToBase64 approach
  var utf8Bytes = _stringToUtf8Bytes(str);
  return _bytesToBase64(utf8Bytes);
}

function _stringToUtf8Bytes(str) {
  var bytes = [];
  for (var i = 0; i < str.length; i++) {
    var code = str.charCodeAt(i);
    if (code < 0x80) {
      bytes.push(code);
    } else if (code < 0x800) {
      bytes.push(0xc0 | (code >> 6), 0x80 | (code & 0x3f));
    } else if (code < 0x10000) {
      bytes.push(0xe0 | (code >> 12), 0x80 | ((code >> 6) & 0x3f), 0x80 | (code & 0x3f));
    } else {
      bytes.push(0xf0 | (code >> 18), 0x80 | ((code >> 12) & 0x3f),
                 0x80 | ((code >> 6) & 0x3f), 0x80 | (code & 0x3f));
    }
  }
  return bytes;
}

var _B64_ALPHABET = [
  'A','B','C','D','E','F','G','H','I','J','K','L','M',
  'N','O','P','Q','R','S','T','U','V','W','X','Y','Z',
  'a','b','c','d','e','f','g','h','i','j','k','l','m',
  'n','o','p','q','r','s','t','u','v','w','x','y','z',
  '0','1','2','3','4','5','6','7','8','9','+','/'
].join('');

function _bytesToBase64(bytes) {
  var result = '';
  for (var i = 0; i < bytes.length; i += 3) {
    var b1 = bytes[i];
    var b2 = i + 1 < bytes.length ? bytes[i + 1] : 0;
    var b3 = i + 2 < bytes.length ? bytes[i + 2] : 0;
    result += _B64_ALPHABET[b1 >> 2];
    result += _B64_ALPHABET[((b1 & 3) << 4) | (b2 >> 4)];
    if (i + 1 < bytes.length) {
      result += _B64_ALPHABET[((b2 & 15) << 2) | (b3 >> 6)];
    } else {
      result += '=';
    }
    if (i + 2 < bytes.length) {
      result += _B64_ALPHABET[b3 & 63];
    } else {
      result += '=';
    }
  }
  return result;
}

/**
 * Simple HMAC-SHA1 implementation for OSS PostObject signature.
 *
 * Since wx.arrayBufferToBase64 is available, we use it in a best-effort way.
 * If crypto API is unavailable, fall back to a simplified approach.
 */
function _hmacSha1Base64(data, key) {
  // In WeChat mini programs, we can't use browser crypto APIs directly.
  // For OSS PostObject, the STS temporary credential uses the secret to sign the policy.
  //
  // We use wx.arrayBufferToBase64 with a SHA-1-like computation.
  // However, WeChat doesn't expose HMAC-SHA1 directly.
  //
  // ALTERNATIVE: OSS supports "Signature" computed by client using the STS
  // access_key_secret with HMAC-SHA1 of the base64 policy.
  //
  // Since wx.request can handle HMAC for us (OSS SDK), but we're doing direct POST,
  // we implement HMAC-SHA1 using the standard algorithm.

  // ... HMAC-SHA1 implementation ...
  // For the MVP, since we're doing direct form POST to OSS and WeChat
  // doesn't have crypto.subtle, we implement HMAC-SHA1 in pure JS.

  return _hmacSha1Base64Impl(data, key);
}

function _hmacSha1Base64Impl(data, key) {
  // HMAC-SHA1 = SHA1((key ^ opad) || SHA1((key ^ ipad) || message))
  var blockSize = 64;

  var keyBytes = _stringToBytes(key);

  // If key is longer than block size, hash it
  if (keyBytes.length > blockSize) {
    keyBytes = _sha1Bytes(keyBytes);
  }

  // Pad to block size
  while (keyBytes.length < blockSize) {
    keyBytes.push(0);
  }

  var ipad = [];
  var opad = [];
  for (var i = 0; i < blockSize; i++) {
    ipad.push(keyBytes[i] ^ 0x36);
    opad.push(keyBytes[i] ^ 0x5c);
  }

  var msgBytes = _stringToBytes(data);
  var innerHash = _sha1Bytes(ipad.concat(msgBytes));
  var outerHash = _sha1Bytes(opad.concat(innerHash));

  return _bytesToBase64(outerHash);
}

function _stringToBytes(str) {
  var bytes = [];
  for (var i = 0; i < str.length; i++) {
    var code = str.charCodeAt(i);
    if (code < 0x80) {
      bytes.push(code);
    } else {
      // Encode multi-byte UTF-8
      bytes = bytes.concat(_stringToUtf8Bytes(str.charAt(i)));
    }
  }
  return bytes;
}

/**
 * Pure JS SHA-1 implementation for HMAC.
 */
function _sha1Bytes(msg) {
  // SHA-1 constants
  var H = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0];

  // Pre-processing
  var msgLenBits = msg.length * 8;
  msg.push(0x80);

  while ((msg.length % 64) !== 56) {
    msg.push(0);
  }

  // Append length as 64-bit big-endian
  for (var i = 7; i >= 4; i--) {
    msg.push(0);
  }
  msg.push((msgLenBits >>> 24) & 0xff);
  msg.push((msgLenBits >>> 16) & 0xff);
  msg.push((msgLenBits >>> 8) & 0xff);
  msg.push(msgLenBits & 0xff);

  // Process each 512-bit block
  for (var blockStart = 0; blockStart < msg.length; blockStart += 64) {
    var W = new Array(80);
    for (var t = 0; t < 16; t++) {
      W[t] = (msg[blockStart + t * 4] << 24) |
             (msg[blockStart + t * 4 + 1] << 16) |
             (msg[blockStart + t * 4 + 2] << 8) |
             msg[blockStart + t * 4 + 3];
    }
    for (var t = 16; t < 80; t++) {
      W[t] = _rotl(W[t - 3] ^ W[t - 8] ^ W[t - 14] ^ W[t - 16], 1);
    }

    var a = H[0], b = H[1], c = H[2], d = H[3], e = H[4];

    for (var t = 0; t < 80; t++) {
      var temp = (_rotl(a, 5) + _sha1F(t, b, c, d) + e + W[t] + _sha1K(t)) | 0;
      e = d;
      d = c;
      c = _rotl(b, 30);
      b = a;
      a = temp;
    }

    H[0] = (H[0] + a) | 0;
    H[1] = (H[1] + b) | 0;
    H[2] = (H[2] + c) | 0;
    H[3] = (H[3] + d) | 0;
    H[4] = (H[4] + e) | 0;
  }

  // Convert to byte array
  var result = [];
  for (var i = 0; i < 5; i++) {
    result.push((H[i] >>> 24) & 0xff);
    result.push((H[i] >>> 16) & 0xff);
    result.push((H[i] >>> 8) & 0xff);
    result.push(H[i] & 0xff);
  }
  return result;
}

function _rotl(x, n) {
  return (x << n) | (x >>> (32 - n));
}

function _sha1F(t, b, c, d) {
  if (t < 20) return (b & c) | (~b & d);
  if (t < 40) return b ^ c ^ d;
  if (t < 60) return (b & c) | (b & d) | (c & d);
  return b ^ c ^ d;
}

function _sha1K(t) {
  if (t < 20) return 0x5A827999;
  if (t < 40) return 0x6ED9EBA1;
  if (t < 60) return 0x8F1BCDCD;
  return 0xCA62C1D6;
}

// ── FC /verify-upload ──────────────────────────────────────────────

function _verifyUploadWithRetry(record, code, attempt, callback) {
  if (attempt >= constants.UPLOAD_MAX_RETRIES) {
    logger.error('[Uploader] verify exhausted retries for', record.fragmentId);
    callback({ reason: 'VERIFY_MAX_RETRIES' });
    return;
  }

  if (attempt > 0) {
    var delay = constants.UPLOAD_RETRY_INTERVALS[attempt - 1] || 45000;
    setTimeout(function () {
      _doVerifyUpload(record, code, attempt, callback);
    }, delay);
  } else {
    _doVerifyUpload(record, code, attempt, callback);
  }
}

function _doVerifyUpload(record, code, attempt, callback) {
  var data = {
    code: code,
    fragment_id: record.fragmentId,
    expected_size: record.size || record.audio.size_bytes || 0
  };

  logger.info('[Uploader] verifying upload for', record.fragmentId);

  wx.request({
    url: constants.FC_VERIFY_UPLOAD_URL,
    method: 'POST',
    header: { 'Content-Type': 'application/json' },
    data: data,
    success: function (res) {
      if (res.statusCode === 200 && res.data) {
        if (res.data.verified === true) {
          logger.info('[Uploader] verify success for', record.fragmentId);
          callback(null);
        } else {
          // verified: false — permanent failure (OBJECT_NOT_FOUND / SIZE_MISMATCH)
          logger.error('[Uploader] verify returned false:', res.data.reason);
          callback({ reason: 'VERIFY_FALSE_' + (res.data.reason || 'UNKNOWN') });
        }
      } else if (res.statusCode >= 500) {
        // 5xx — retry
        logger.error('[Uploader] verify 5xx, retrying...');
        _verifyUploadWithRetry(record, code, attempt + 1, callback);
      } else if (res.statusCode >= 400) {
        // 4xx auth — don't retry
        logger.error('[Uploader] verify 4xx, not retrying');
        callback({ reason: 'VERIFY_4XX' });
      } else {
        logger.error('[Uploader] verify unexpected status:', res.statusCode);
        _verifyUploadWithRetry(record, code, attempt + 1, callback);
      }
    },
    fail: function (err) {
      logger.error('[Uploader] verify network error:', err);
      _verifyUploadWithRetry(record, code, attempt + 1, callback);
    }
  });
}

// ── Failure handlers ──────────────────────────────────────────────

function _handleUploadFailure(list, index, errorCode) {
  var record = list[index];
  record.retryCount = (record.retryCount || 0) + 1;

  logger.info('[Uploader] upload failure, retryCount=', record.retryCount,
    '/', constants.UPLOAD_MAX_RETRIES);

  if (record.retryCount < constants.UPLOAD_MAX_RETRIES) {
    // Will be retried on next processUploadQueue call
    _updateRecordStatus(list, index, constants.UPLOAD_STATUS.QUEUED);
    record.errorCode = errorCode;
  } else {
    // Exhausted retries → manual retry
    _updateRecordStatus(list, index, constants.UPLOAD_STATUS.MANUAL_RETRY);
    record.errorCode = errorCode;
    logger.error('[Uploader] retries exhausted for', record.fragmentId, '→ manual_retry');
  }

  _notifyPages(list);
}

function _handleVerifyFailure(list, index, reason) {
  var record = list[index];

  // verified:false (OBJECT_NOT_FOUND / SIZE_MISMATCH) → manual_retry
  // verify 调用失败 ×3 → manual_verify
  if (reason === 'VERIFY_FALSE_OBJECT_NOT_FOUND' || reason === 'VERIFY_FALSE_SIZE_MISMATCH') {
    _updateRecordStatus(list, index, constants.UPLOAD_STATUS.MANUAL_RETRY);
  } else {
    _updateRecordStatus(list, index, constants.UPLOAD_STATUS.MANUAL_VERIFY);
  }

  record.verifyReason = reason;
  _notifyPages(list);
}

// ── List management helpers ────────────────────────────────────────

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
    logger.error('[Uploader] failed to save upload list:', e);
  }
}

function _updateRecordStatus(list, index, status, extra) {
  if (index < 0 || index >= list.length) return;

  var record = list[index];
  record.status = status;
  record.statusText = constants.UPLOAD_STATUS_CN[status] || status;

  if (extra) {
    for (var key in extra) {
      if (extra.hasOwnProperty(key)) {
        record[key] = extra[key];
      }
    }
  }

  _saveUploadList(list);
}

function _notifyPages(list) {
  // Notify upload-list page if it's active
  var pages = getCurrentPages();
  for (var i = 0; i < pages.length; i++) {
    if (pages[i].route === 'pages/upload-list/upload-list') {
      // Map to status text and set
      var mapped = list.map(function (item) {
        item.statusText = constants.UPLOAD_STATUS_CN[item.status] || item.status;
        return item;
      });
      pages[i].setData({ uploadList: mapped });
    }
  }
}

// ── Exports ───────────────────────────────────────────────────────

module.exports = {
  initUploader: initUploader,
  processUploadQueue: processUploadQueue,
  triggerManualRetry: triggerManualRetry,

  // Exported for testing
  _loadUploadList: _loadUploadList,
  _saveUploadList: _saveUploadList,
  _updateRecordStatus: _updateRecordStatus,
  _buildOssFormData: _buildOssFormData,
  _base64Encode: _base64Encode,
  _hmacSha1Base64: _hmacSha1Base64,
  _sha1Bytes: _sha1Bytes,
  _stringToUtf8Bytes: _stringToUtf8Bytes,
  _bytesToBase64: _bytesToBase64,
  _wxLogin: _wxLogin,
  _fetchSts: _fetchSts,
  _ossUploadWithRetry: _ossUploadWithRetry,
  _verifyUploadWithRetry: _verifyUploadWithRetry,
  _handleUploadFailure: _handleUploadFailure,
  _handleVerifyFailure: _handleVerifyFailure,
  _continueNext: _continueNext,
};
