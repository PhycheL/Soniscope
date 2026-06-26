// ULID 生成（US-015）：26 字符 Crockford base32（10 字符毫秒时间戳 + 16 字符随机/单调）。
//
// 用于 fragment_id 末段与 session_id（tech-spec §3.1）。Crockford base32 字符集是 [0-9A-Z] 的子集，
// 满足 FC 侧 fragment_id 正则 [0-9A-Za-z]{26}。提供单调工厂 monotonicFactory：同一毫秒内连续生成时
// 递增随机段，保证「同一秒内连续保存两条录音」也得到不同 ULID（US-015 AC#3）。
//
// 本模块为纯函数（不依赖 wx 运行时）；时间与随机源均可注入，便于单测确定性验证。

const ENCODING = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
const ENCODING_LEN = ENCODING.length // 32
const TIME_LEN = 10
const RANDOM_LEN = 16

function randomChar(rng) {
  let r = Math.floor(rng() * ENCODING_LEN)
  if (r >= ENCODING_LEN) {
    r = ENCODING_LEN - 1
  }
  return ENCODING.charAt(r)
}

function encodeTime(now, len) {
  let t = now
  let str = ''
  for (let i = len - 1; i >= 0; i--) {
    const mod = t % ENCODING_LEN
    str = ENCODING.charAt(mod) + str
    t = (t - mod) / ENCODING_LEN
  }
  return str
}

function encodeRandom(len, rng) {
  let str = ''
  for (let i = 0; i < len; i++) {
    str += randomChar(rng)
  }
  return str
}

function resolveTime(seedTime) {
  return typeof seedTime === 'number' ? seedTime : Date.now()
}

function resolveRng(rng) {
  return typeof rng === 'function' ? rng : Math.random
}

// 生成一个 ULID（26 字符）。seedTime / rng 可注入用于测试。
function ulid(seedTime, rng) {
  return encodeTime(resolveTime(seedTime), TIME_LEN) + encodeRandom(RANDOM_LEN, resolveRng(rng))
}

// 单调工厂：返回 next(seedTime) -> ULID；时间不前进时递增随机段，保证单调且互不相同。
function monotonicFactory(rng) {
  const r = resolveRng(rng)
  let lastTime = -1
  let lastRandom = ''

  function incrementRandom(str) {
    let index = str.length
    const chars = str.split('')
    while (--index >= 0) {
      const i = ENCODING.indexOf(chars[index])
      if (i === ENCODING_LEN - 1) {
        chars[index] = ENCODING.charAt(0)
        continue
      }
      chars[index] = ENCODING.charAt(i + 1)
      return chars.join('')
    }
    // 极端溢出（实际不可能）：重新随机。
    return encodeRandom(RANDOM_LEN, r)
  }

  return function next(seedTime) {
    const t = resolveTime(seedTime)
    if (t <= lastTime) {
      lastRandom = incrementRandom(lastRandom)
      return encodeTime(lastTime, TIME_LEN) + lastRandom
    }
    lastTime = t
    lastRandom = encodeRandom(RANDOM_LEN, r)
    return encodeTime(t, TIME_LEN) + lastRandom
  }
}

module.exports = {
  ULID_LENGTH: TIME_LEN + RANDOM_LEN,
  ulid: ulid,
  monotonicFactory: monotonicFactory,
}
