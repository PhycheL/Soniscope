// SoniScope · SHA-256 纯 JS 实现
// 用于微信小程序计算原始音频 SHA-256
// 避免引入额外依赖，直接在 JS 中完成计算
//
// 限制：正确处理文件大小最大约 500 MB（位长 < 2^32）

// ── SHA-256 常量 K ────────────────────────────────────────────────

var K = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
  0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
  0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
  0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
  0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
  0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
];

// ── Internal helpers ──────────────────────────────────────────────

function _rotr(x, n) {
  return (x >>> n) | (x << (32 - n));
}

function _processBlock(block, H) {
  var W = new Array(64);

  // Message schedule: first 16 words from block
  for (var t = 0; t < 16; t++) {
    W[t] = block[t];
  }
  for (var t = 16; t < 64; t++) {
    var s0 = _rotr(W[t - 15], 7) ^ _rotr(W[t - 15], 18) ^ (W[t - 15] >>> 3);
    var s1 = _rotr(W[t - 2], 17) ^ _rotr(W[t - 2], 19) ^ (W[t - 2] >>> 10);
    W[t] = (W[t - 16] + s0 + W[t - 7] + s1) | 0;
  }

  var a = H[0], b = H[1], c = H[2], d = H[3];
  var e = H[4], f = H[5], g = H[6], h = H[7];

  for (var t = 0; t < 64; t++) {
    var S1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25);
    var ch = (e & f) ^ (~e & g);
    var temp1 = (h + S1 + ch + K[t] + W[t]) | 0;
    var S0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22);
    var maj = (a & b) ^ (a & c) ^ (b & c);
    var temp2 = (S0 + maj) | 0;

    h = g;
    g = f;
    f = e;
    e = (d + temp1) | 0;
    d = c;
    c = b;
    b = a;
    a = (temp1 + temp2) | 0;
  }

  H[0] = (H[0] + a) | 0;
  H[1] = (H[1] + b) | 0;
  H[2] = (H[2] + c) | 0;
  H[3] = (H[3] + d) | 0;
  H[4] = (H[4] + e) | 0;
  H[5] = (H[5] + f) | 0;
  H[6] = (H[6] + g) | 0;
  H[7] = (H[7] + h) | 0;
}

// ── Public API ────────────────────────────────────────────────────

/**
 * Compute SHA-256 hash of a byte array.
 *
 * @param {Uint8Array} bytes
 * @returns {string} hex-encoded 64-character hash
 */
function sha256Hex(bytes) {
  // Initial hash values (first 32 bits of fractional parts of sqrt of first 8 primes)
  var H = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
  ];

  var msgLen = bytes.length;
  var bitLen = msgLen * 8;

  // Padding: append '1' bit (0x80), zero bits, and 64-bit length
  // (msgLen + 1 + padZeros + 8) must be multiple of 64
  var padZeros = (64 - ((msgLen + 9) % 64)) % 64;
  var totalLen = msgLen + 1 + padZeros + 8;

  var padded = new Uint8Array(totalLen);
  padded.set(bytes);
  padded[msgLen] = 0x80; // append '1' bit as 0x80 byte

  // Append 64-bit big-endian message length
  // For files < ~512 MB (bitLen < 2^32), upper 4 bytes are 0
  padded[totalLen - 8] = 0;
  padded[totalLen - 7] = 0;
  padded[totalLen - 6] = 0;
  padded[totalLen - 5] = 0;
  padded[totalLen - 4] = (bitLen >>> 24) & 0xff;
  padded[totalLen - 3] = (bitLen >>> 16) & 0xff;
  padded[totalLen - 2] = (bitLen >>> 8) & 0xff;
  padded[totalLen - 1] = bitLen & 0xff;

  // Process each 512-bit (64-byte) block
  for (var i = 0; i < totalLen; i += 64) {
    var block = new Array(16);
    for (var j = 0; j < 16; j++) {
      var off = i + j * 4;
      block[j] = (padded[off] << 24) | (padded[off + 1] << 16) |
                 (padded[off + 2] << 8) | padded[off + 3];
    }
    _processBlock(block, H);
  }

  // Convert hash words to hex string (zero-padded bytes)
  var hex = '';
  for (var i = 0; i < 8; i++) {
    var w = H[i] >>> 0; // convert to unsigned
    hex += ('0' + ((w >>> 24) & 0xff).toString(16)).slice(-2);
    hex += ('0' + ((w >>> 16) & 0xff).toString(16)).slice(-2);
    hex += ('0' + ((w >>> 8) & 0xff).toString(16)).slice(-2);
    hex += ('0' + (w & 0xff).toString(16)).slice(-2);
  }

  return hex;
}

/**
 * Compute SHA-256 hash of a local file asynchronously.
 *
 * Reads the file with wx.getFileSystemManager, computes SHA-256 on the
 * ArrayBuffer, and returns the hex digest.
 *
 * @param {string} filePath — local temp file path
 * @returns {Promise<string>} hex-encoded SHA-256 digest
 */
function computeFileSha256(filePath) {
  return new Promise(function (resolve, reject) {
    var fs = wx.getFileSystemManager();
    fs.readFile({
      filePath: filePath,
      success: function (res) {
        try {
          var bytes = new Uint8Array(res.data);
          var hash = sha256Hex(bytes);
          resolve(hash);
        } catch (e) {
          reject(e);
        }
      },
      fail: function (err) {
        reject(err);
      }
    });
  });
}

module.exports = {
  sha256Hex: sha256Hex,
  computeFileSha256: computeFileSha256
};
