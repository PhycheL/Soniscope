// HMAC-SHA256 + base64（US-017）：OSS V4 PostObject 表单签名所需的密码学原语。
//
// 复用 utils/sha256.js 的纯 JS SHA-256 内核（sha256Bytes / toBytes），无外部依赖，
// 可在 node 单测中对照 node:crypto 校验向量；微信小程序运行时同样可用（纯 JS）。
//
// 本模块为纯函数（不依赖 wx 运行时）。

const { sha256Bytes, bytesToHex, toBytes } = require('./sha256')

const BLOCK_SIZE = 64 // SHA-256 分组字节数

// HMAC-SHA256：key / msg 接受 字符串 / ArrayBuffer / TypedArray / number[]，返回 32 字节 Uint8Array。
function hmacSha256(key, msg) {
  let k = toBytes(key)
  // key 超过分组长度先哈希；不足分组长度右侧补 0。
  if (k.length > BLOCK_SIZE) {
    k = sha256Bytes(k)
  }
  const keyBlock = new Uint8Array(BLOCK_SIZE)
  keyBlock.set(k)
  const ipad = new Uint8Array(BLOCK_SIZE)
  const opad = new Uint8Array(BLOCK_SIZE)
  for (let i = 0; i < BLOCK_SIZE; i++) {
    ipad[i] = keyBlock[i] ^ 0x36
    opad[i] = keyBlock[i] ^ 0x5c
  }
  const msgBytes = toBytes(msg)
  const inner = new Uint8Array(BLOCK_SIZE + msgBytes.length)
  inner.set(ipad)
  inner.set(msgBytes, BLOCK_SIZE)
  const innerHash = sha256Bytes(inner)
  const outer = new Uint8Array(BLOCK_SIZE + innerHash.length)
  outer.set(opad)
  outer.set(innerHash, BLOCK_SIZE)
  return sha256Bytes(outer)
}

function hmacSha256Hex(key, msg) {
  return bytesToHex(hmacSha256(key, msg))
}

const B64_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

// 标准 base64 编码（输入接受 字符串 / 字节）。微信小程序无 btoa，故纯实现。
function base64Encode(input) {
  const bytes = toBytes(input)
  let out = ''
  for (let i = 0; i < bytes.length; i += 3) {
    const b0 = bytes[i]
    const b1 = i + 1 < bytes.length ? bytes[i + 1] : 0
    const b2 = i + 2 < bytes.length ? bytes[i + 2] : 0
    out += B64_ALPHABET[b0 >> 2]
    out += B64_ALPHABET[((b0 & 0x03) << 4) | (b1 >> 4)]
    out += i + 1 < bytes.length ? B64_ALPHABET[((b1 & 0x0f) << 2) | (b2 >> 6)] : '='
    out += i + 2 < bytes.length ? B64_ALPHABET[b2 & 0x3f] : '='
  }
  return out
}

module.exports = {
  hmacSha256: hmacSha256,
  hmacSha256Hex: hmacSha256Hex,
  base64Encode: base64Encode,
}
