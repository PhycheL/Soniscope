// SoniScope · 开发者故障注入模块
//
// 仅在非 production 环境使用。
// 提供三个运行时可切换的故障注入开关：
//   - mockFcUrlBroken    → /issue-credential 和 /verify-upload 请求全部强制失败
//   - mockNetworkOffline  → 模拟离线，即使真实网络可用也让上传进入离线排队
//   - mockVerifyFail      → /verify-upload 永远返回 verified:false
//
// 开关持久化到本地 storage（soniscope_dev_flags），无需修改源码即可运行时切换。
// production 构建中本模块不会被导入（dev menu 入口不可见）。

var constants = require('./constants.js');

var STORAGE_KEY = 'soniscope_dev_flags';

// ── 默认值 ──────────────────────────────────────────────────────────

var DEFAULT_FLAGS = {
  mockFcUrlBroken: false,
  mockNetworkOffline: false,
  mockVerifyFail: false,
};

// ── 内部 helpers ─────────────────────────────────────────────────────

function _loadFlags() {
  try {
    var stored = wx.getStorageSync(STORAGE_KEY);
    if (stored && typeof stored === 'object') {
      // Merge stored flags into defaults (only known keys)
      var merged = {};
      var keys = Object.keys(DEFAULT_FLAGS);
      for (var i = 0; i < keys.length; i++) {
        var k = keys[i];
        merged[k] = (stored[k] !== undefined) ? stored[k] : DEFAULT_FLAGS[k];
      }
      return merged;
    }
  } catch (e) {
    // ignore
  }
  var defaults = {};
  var dk = Object.keys(DEFAULT_FLAGS);
  for (var j = 0; j < dk.length; j++) {
    defaults[dk[j]] = DEFAULT_FLAGS[dk[j]];
  }
  return defaults;
}

function _saveFlags(flags) {
  try {
    wx.setStorageSync(STORAGE_KEY, flags);
  } catch (e) {
    // ignore
  }
}

// ── Public API ──────────────────────────────────────────────────────

/**
 * Read a single fault injection flag.
 *
 * @param {string} name — one of 'mockFcUrlBroken', 'mockNetworkOffline', 'mockVerifyFail'
 * @returns {boolean}
 */
function getFlag(name) {
  if (constants.IS_PRODUCTION) {
    return false; // 生产环境永远不注入故障
  }
  var flags = _loadFlags();
  return !!flags[name];
}

/**
 * Set a single fault injection flag and persist.
 *
 * @param {string} name
 * @param {boolean} value
 */
function setFlag(name, value) {
  var flags = _loadFlags();
  flags[name] = !!value;
  _saveFlags(flags);
}

/**
 * Toggle a single fault injection flag (flip boolean).
 *
 * @param {string} name
 * @returns {boolean} the new value
 */
function toggleFlag(name) {
  var flags = _loadFlags();
  flags[name] = !flags[name];
  _saveFlags(flags);
  return flags[name];
}

/**
 * Get all flags as a plain object.
 *
 * @returns {{ mockFcUrlBroken: boolean, mockNetworkOffline: boolean, mockVerifyFail: boolean }}
 */
function getAllFlags() {
  return _loadFlags();
}

/**
 * Reset all flags to defaults (all false).
 */
function resetAllFlags() {
  _saveFlags(Object.assign({}, DEFAULT_FLAGS));
}

/**
 * Check if any fault injection flag is active.
 *
 * @returns {boolean}
 */
function isAnyFlagActive() {
  var flags = _loadFlags();
  return flags.mockFcUrlBroken || flags.mockNetworkOffline || flags.mockVerifyFail;
}

module.exports = {
  getFlag: getFlag,
  setFlag: setFlag,
  toggleFlag: toggleFlag,
  getAllFlags: getAllFlags,
  resetAllFlags: resetAllFlags,
  isAnyFlagActive: isAnyFlagActive,
  STORAGE_KEY: STORAGE_KEY,
};
