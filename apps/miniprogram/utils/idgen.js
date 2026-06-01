// SoniScope · 设备短 ID、ULID 与 Fragment ID 生成

// Crockford Base32 字母表（不含 I, L, O, U）
var CROCKFORD = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';

var DEVICE_ID_STORAGE_KEY = 'soniscope_device_short_id';
var DEVICE_ID_CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789';
var DEVICE_ID_LENGTH = 6; // 6 字符，位于 AC 要求的 4-8 范围内

// ── Internal helpers ──────────────────────────────────────────────

function _pad2(n) {
  n = n | 0;
  return (n < 10 ? '0' : '') + n;
}

function _encodeBase32(value, length) {
  var str = '';
  for (var i = length - 1; i >= 0; i--) {
    str = CROCKFORD[value % 32] + str;
    value = Math.floor(value / 32);
  }
  return str;
}

function _generateUlid() {
  var now = Date.now();
  var timePart = _encodeBase32(now, 10);
  var randomPart = '';
  for (var i = 0; i < 16; i++) {
    randomPart += CROCKFORD[Math.floor(Math.random() * 32)];
  }
  return timePart + randomPart;
}

// ── Public API ────────────────────────────────────────────────────

/**
 * Get or create the persistent device short ID.
 *
 * On first call, generates a random 6-character alphanumeric ID and
 * persists it to wx storage. Subsequent calls return the stored value.
 *
 * @returns {string} 6-character device short ID
 */
function getOrCreateDeviceShortId() {
  var id = '';
  try {
    id = wx.getStorageSync(DEVICE_ID_STORAGE_KEY) || '';
  } catch (e) {
    // ignore — storage may be unavailable during cold start
  }
  if (id) return id;

  // Generate new ID and persist
  id = '';
  for (var i = 0; i < DEVICE_ID_LENGTH; i++) {
    id += DEVICE_ID_CHARS[Math.floor(Math.random() * DEVICE_ID_CHARS.length)];
  }
  try {
    wx.setStorageSync(DEVICE_ID_STORAGE_KEY, id);
  } catch (e) {
    // ignore — very unlikely
  }
  return id;
}

/**
 * Read the persistent device short ID (no creation).
 *
 * @returns {string} device short ID, or empty string if not yet created
 */
function getDeviceShortId() {
  try {
    return wx.getStorageSync(DEVICE_ID_STORAGE_KEY) || '';
  } catch (e) {
    return '';
  }
}

/**
 * Generate a ULID (Universally Unique Lexicographically Sortable Identifier).
 *
 * 26 characters: 10-char Crockford-base32 timestamp + 16-char randomness.
 *
 * @returns {string} 26-character ULID
 */
function generateUlid() {
  return _generateUlid();
}

/**
 * Generate a SoniScope fragment ID.
 *
 * Format: <YYYYMMDDTHHMMSS>_<deviceShortId>_<26-char-ULID>
 *
 * @param {string} deviceShortId — device short ID
 * @returns {string} fragment ID
 */
function generateFragmentId(deviceShortId) {
  var now = new Date();
  var yyyyMMdd = '' + now.getFullYear()
    + _pad2(now.getMonth() + 1)
    + _pad2(now.getDate());
  var HHMMSS = _pad2(now.getHours())
    + _pad2(now.getMinutes())
    + _pad2(now.getSeconds());
  var ts = yyyyMMdd + 'T' + HHMMSS;
  var ulid = _generateUlid();
  var devId = deviceShortId || 'unknown';
  return ts + '_' + devId + '_' + ulid;
}

/**
 * Generate a session ID shared by all chunks of a recording session.
 *
 * @returns {string} 26-character ULID serving as session ID
 */
function generateSessionId() {
  return _generateUlid();
}

module.exports = {
  // Functions
  getOrCreateDeviceShortId: getOrCreateDeviceShortId,
  getDeviceShortId: getDeviceShortId,
  generateUlid: generateUlid,
  generateFragmentId: generateFragmentId,
  generateSessionId: generateSessionId,
  // Constants (exported for testing)
  CROCKFORD: CROCKFORD,
  DEVICE_ID_STORAGE_KEY: DEVICE_ID_STORAGE_KEY,
  DEVICE_ID_LENGTH: DEVICE_ID_LENGTH
};
