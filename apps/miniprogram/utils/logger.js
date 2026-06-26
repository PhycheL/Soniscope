// 基础日志工具：自动脱敏长期 AK、AppSecret、STS access_key_secret、security_token 等敏感字段。
//
// 安全红线（AGENTS.md）：明文 AK / Secret / Token / AppSecret 不得完整打印到日志。
// 业务侧凭证一律以对象字段传入（如 { access_key_secret, security_token }），
// log() 在打印前对敏感键做前后 4 位脱敏，避免明文进入 vConsole / 控制台。

// 敏感字段名匹配（覆盖 STS 凭证、长期 AK、微信密钥等）。
const SENSITIVE_KEY_RE =
  /(access[_-]?key[_-]?secret|access[_-]?key[_-]?id|app[_-]?secret|appsecret|security[_-]?token|session[_-]?key|api[_-]?key|secret|token|password)/i

function maskValue(value) {
  const s = String(value)
  if (s.length <= 8) {
    return '****'
  }
  return s.slice(0, 4) + '****' + s.slice(-4)
}

// 递归脱敏：对象按敏感键名打码，数组逐项处理，标量原样返回。
function redact(input) {
  if (Array.isArray(input)) {
    return input.map(redact)
  }
  if (input && typeof input === 'object') {
    const out = {}
    for (const key of Object.keys(input)) {
      out[key] = SENSITIVE_KEY_RE.test(key) ? maskValue(input[key]) : redact(input[key])
    }
    return out
  }
  return input
}

function createLogger(scope) {
  const prefix = '[soniscope:' + scope + ']'
  const emit = function (level, args) {
    const safe = args.map(function (a) {
      return a && typeof a === 'object' ? redact(a) : a
    })
    // eslint-disable-next-line no-console
    console[level](prefix, ...safe)
  }
  return {
    info: function () {
      emit('log', Array.prototype.slice.call(arguments))
    },
    warn: function () {
      emit('warn', Array.prototype.slice.call(arguments))
    },
    error: function () {
      emit('error', Array.prototype.slice.call(arguments))
    },
  }
}

module.exports = {
  createLogger: createLogger,
  redact: redact,
  maskValue: maskValue,
}
