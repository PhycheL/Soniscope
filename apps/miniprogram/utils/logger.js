// SoniScope · 安全日志工具
//
// 关键原则（来自 AGENTS.md）：
// - 绝不打印长期 AK、AppSecret、STS access_key_secret 或 security_token 明文
// - FC 日志不记录完整 openid（只记录哈希）
// - 日志可记录 fragment_id、结果、耗时

var constants = require('./constants.js');

// 敏感字段名列表（不区分大小写匹配）
var SENSITIVE_FIELD_NAMES = [
  'access_key_secret',
  'accesskey_secret',
  'access_key_id',
  'security_token',
  'appsecret',
  'secret',
  'signature',
  'password',
  'token',
];

var logLevel = constants.IS_PRODUCTION ? 3 : 0; // 0=DEBUG, 1=INFO, 2=WARN, 3=ERROR

function _isSensitiveValue(key, value) {
  if (!key || !value || typeof value !== 'string') return false;
  var keyLower = key.toLowerCase();
  for (var i = 0; i < SENSITIVE_FIELD_NAMES.length; i++) {
    if (keyLower.indexOf(SENSITIVE_FIELD_NAMES[i]) !== -1) {
      return true;
    }
  }
  return false;
}

function _maskValue(value) {
  if (!value || typeof value !== 'string' || value.length <= 8) {
    return '***';
  }
  return value.substring(0, 4) + '****' + value.substring(value.length - 4);
}

function _safeStringify(obj) {
  if (!obj) return String(obj);
  if (typeof obj !== 'object') return String(obj);

  try {
    var safe = {};
    var keys = Object.keys(obj);
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i];
      var v = obj[k];
      if (_isSensitiveValue(k, v)) {
        safe[k] = _maskValue(v);
      } else {
        safe[k] = v;
      }
    }
    return JSON.stringify(safe);
  } catch (e) {
    return '[unserializable]';
  }
}

function debug() {
  if (logLevel <= 0) {
    console.log('[DEBUG]', _formatArgs(arguments));
  }
}

function info() {
  if (logLevel <= 1) {
    console.log('[INFO]', _formatArgs(arguments));
  }
}

function warn() {
  if (logLevel <= 2) {
    console.warn('[WARN]', _formatArgs(arguments));
  }
}

function error() {
  if (logLevel <= 3) {
    console.error('[ERROR]', _formatArgs(arguments));
  }
}

function _formatArgs(args) {
  var parts = [];
  for (var i = 0; i < args.length; i++) {
    var arg = args[i];
    if (typeof arg === 'string') {
      parts.push(arg);
    } else if (typeof arg === 'object') {
      parts.push(_safeStringify(arg));
    } else {
      parts.push(String(arg));
    }
  }
  return parts.join(' ');
}

module.exports = {
  debug: debug,
  info: info,
  warn: warn,
  error: error,
};
