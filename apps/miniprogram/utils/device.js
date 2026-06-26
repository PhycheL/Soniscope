// 设备短 ID（US-015 AC#1）：小程序首次启动生成 4-8 字符 device_short_id 并持久化到本地 storage，
// 冷启动后保持不变。该值进入 fragment_id 的 deviceShortId 段与 manifest 的 device_id 字段
// （tech-spec §3.1）。
//
// 纯逻辑（生成 / 校验）与 storage IO 分离：生成函数可注入随机源做确定性单测；
// ensureDeviceShortId 接收一个具备 getStorageSync / setStorageSync 的对象（运行时传 wx）。

const STORAGE_KEY = 'soniscope:device_short_id'
// 字母数字字符集（满足 FC fragment_id 正则 [A-Za-z0-9]{4,8}）。
const ALPHABET = 'abcdefghijklmnopqrstuvwxyz0123456789'
// 固定 6 字符，落在 4-8 区间内。
const SHORT_ID_LEN = 6

const DEVICE_SHORT_ID_RE = /^[A-Za-z0-9]{4,8}$/

function isValidDeviceShortId(value) {
  return typeof value === 'string' && DEVICE_SHORT_ID_RE.test(value)
}

// 生成 device_short_id（纯函数，rng 可注入）。
function generateDeviceShortId(rng) {
  const r = typeof rng === 'function' ? rng : Math.random
  let s = ''
  for (let i = 0; i < SHORT_ID_LEN; i++) {
    let idx = Math.floor(r() * ALPHABET.length)
    if (idx >= ALPHABET.length) {
      idx = ALPHABET.length - 1
    }
    s += ALPHABET.charAt(idx)
  }
  return s
}

// 读取已持久化的 device_short_id；不存在或非法时生成并持久化后返回（幂等，AC#1）。
function ensureDeviceShortId(storage, rng) {
  let existing = ''
  try {
    existing = storage.getStorageSync(STORAGE_KEY)
  } catch (e) {
    existing = ''
  }
  if (isValidDeviceShortId(existing)) {
    return existing
  }
  const id = generateDeviceShortId(rng)
  try {
    storage.setStorageSync(STORAGE_KEY, id)
  } catch (e) {
    // best effort：持久化失败仍返回本次生成值（冷启动会重生成，属降级）。
  }
  return id
}

module.exports = {
  DEVICE_SHORT_ID_STORAGE_KEY: STORAGE_KEY,
  DEVICE_SHORT_ID_RE: DEVICE_SHORT_ID_RE,
  isValidDeviceShortId: isValidDeviceShortId,
  generateDeviceShortId: generateDeviceShortId,
  ensureDeviceShortId: ensureDeviceShortId,
}
