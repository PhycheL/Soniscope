// 纯 JS SHA-256（US-015）：前端对原始音频字节计算 sha256，写入 upload.original_sha256
// 并准备为 x-oss-meta-sha256（tech-spec §3.2 / §3.3）。
//
// 微信小程序内可用 wasm-crypto 优化大文件主线程卡顿（AGENTS.md 技术栈建议），本期先用纯 JS
// 实现，保证可在 node 单测中对照 crypto 校验正确性、且无外部依赖；wasm 化属后续性能优化。
//
// 本模块为纯函数（不依赖 wx 运行时），输入接受 ArrayBuffer / TypedArray / number[] / 字符串。

const K = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]

function rotr(x, n) {
  return (x >>> n) | (x << (32 - n))
}

function toHex8(x) {
  return (x >>> 0).toString(16).padStart(8, '0')
}

// 把多种输入统一成 Uint8Array（字符串按 UTF-8 编码）。
function toBytes(input) {
  if (input instanceof ArrayBuffer) {
    return new Uint8Array(input)
  }
  if (ArrayBuffer.isView(input)) {
    return new Uint8Array(input.buffer, input.byteOffset, input.byteLength)
  }
  if (Array.isArray(input)) {
    return Uint8Array.from(input)
  }
  if (typeof input === 'string') {
    const out = []
    for (let i = 0; i < input.length; i++) {
      let c = input.charCodeAt(i)
      if (c < 0x80) {
        out.push(c)
      } else if (c < 0x800) {
        out.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f))
      } else if (c >= 0xd800 && c <= 0xdbff && i + 1 < input.length) {
        const c2 = input.charCodeAt(++i)
        c = 0x10000 + ((c & 0x3ff) << 10) + (c2 & 0x3ff)
        out.push(
          0xf0 | (c >> 18),
          0x80 | ((c >> 12) & 0x3f),
          0x80 | ((c >> 6) & 0x3f),
          0x80 | (c & 0x3f)
        )
      } else {
        out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f))
      }
    }
    return Uint8Array.from(out)
  }
  throw new TypeError('sha256: unsupported input type')
}

// 计算 SHA-256，返回小写 hex 字符串（64 字符）。
function sha256Hex(input) {
  const bytes = toBytes(input)
  const h = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ]
  const len = bytes.length
  const bitLen = len * 8
  const withOne = len + 1
  const k = (56 - (withOne % 64) + 64) % 64
  const totalLen = withOne + k + 8
  const msg = new Uint8Array(totalLen)
  msg.set(bytes)
  msg[len] = 0x80
  const hi = Math.floor(bitLen / 0x100000000)
  const lo = bitLen >>> 0
  msg[totalLen - 8] = (hi >>> 24) & 0xff
  msg[totalLen - 7] = (hi >>> 16) & 0xff
  msg[totalLen - 6] = (hi >>> 8) & 0xff
  msg[totalLen - 5] = hi & 0xff
  msg[totalLen - 4] = (lo >>> 24) & 0xff
  msg[totalLen - 3] = (lo >>> 16) & 0xff
  msg[totalLen - 2] = (lo >>> 8) & 0xff
  msg[totalLen - 1] = lo & 0xff

  const w = new Array(64)
  for (let i = 0; i < totalLen; i += 64) {
    for (let t = 0; t < 16; t++) {
      const j = i + t * 4
      w[t] = (msg[j] << 24) | (msg[j + 1] << 16) | (msg[j + 2] << 8) | msg[j + 3]
    }
    for (let t = 16; t < 64; t++) {
      const s0 = rotr(w[t - 15], 7) ^ rotr(w[t - 15], 18) ^ (w[t - 15] >>> 3)
      const s1 = rotr(w[t - 2], 17) ^ rotr(w[t - 2], 19) ^ (w[t - 2] >>> 10)
      w[t] = (w[t - 16] + s0 + w[t - 7] + s1) | 0
    }
    let a = h[0]
    let b = h[1]
    let c = h[2]
    let d = h[3]
    let e = h[4]
    let f = h[5]
    let g = h[6]
    let hh = h[7]
    for (let t = 0; t < 64; t++) {
      const bigS1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
      const ch = (e & f) ^ (~e & g)
      const temp1 = (hh + bigS1 + ch + K[t] + w[t]) | 0
      const bigS0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
      const maj = (a & b) ^ (a & c) ^ (b & c)
      const temp2 = (bigS0 + maj) | 0
      hh = g
      g = f
      f = e
      e = (d + temp1) | 0
      d = c
      c = b
      b = a
      a = (temp1 + temp2) | 0
    }
    h[0] = (h[0] + a) | 0
    h[1] = (h[1] + b) | 0
    h[2] = (h[2] + c) | 0
    h[3] = (h[3] + d) | 0
    h[4] = (h[4] + e) | 0
    h[5] = (h[5] + f) | 0
    h[6] = (h[6] + g) | 0
    h[7] = (h[7] + hh) | 0
  }
  return h.map(toHex8).join('')
}

module.exports = {
  sha256Hex: sha256Hex,
}
