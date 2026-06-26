// 录音辅助纯函数：时长格式化、原始格式探测、OSS object key 预览、草稿 manifest 构造。
//
// 前端不做音频转码（tech-spec §5.1 / ADR-1）：
//   - audio.original_format 记录微信实际产出的原始格式；临时路径扩展名不可靠时回退到录音请求格式。
//   - OSS object key 始终用 .wav 目标扩展名（OSS_OBJECT_KEY_EXT），表示 Worker 侧最终标准化目标，
//     不代表前端已转码。
//
// 本模块为纯函数（不依赖 wx 运行时），便于 node --check 静态校验与后续单元测试复用。

const { OSS_OBJECT_KEY_EXT } = require('../config')

// 已知音频容器/编码扩展名（tech-spec §3.2 列举 wav/mp3/aac/m4a/amr 等）。
const KNOWN_FORMATS = ['wav', 'mp3', 'aac', 'm4a', 'amr', 'pcm', 'silk', 'ogg']

function pad2(n) {
  return n < 10 ? '0' + n : String(n)
}

// 秒数 → mm:ss（用于录音计时与草稿时长展示）。
function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.floor(Number(totalSeconds) || 0))
  const mm = Math.floor(s / 60)
  const ss = s % 60
  return pad2(mm) + ':' + pad2(ss)
}

// 从文件路径取扩展名（小写，无点）。
function extensionOf(path) {
  const s = String(path || '')
  const slash = s.lastIndexOf('/')
  const name = slash === -1 ? s : s.slice(slash + 1)
  const dot = name.lastIndexOf('.')
  if (dot <= 0) {
    return ''
  }
  return name.slice(dot + 1).toLowerCase()
}

// 探测原始音频格式：优先临时文件扩展名；扩展名缺失/不可识别时回退到录音请求格式。
function detectOriginalFormat(tempFilePath, requestedFormat) {
  const ext = extensionOf(tempFilePath)
  if (ext && KNOWN_FORMATS.indexOf(ext) !== -1) {
    return ext
  }
  const req = String(requestedFormat || '').toLowerCase()
  if (req && KNOWN_FORMATS.indexOf(req) !== -1) {
    return req
  }
  return ext || req || 'unknown'
}

function localDateParts(date) {
  return {
    y: String(date.getFullYear()),
    m: pad2(date.getMonth() + 1),
    d: pad2(date.getDate()),
    hh: pad2(date.getHours()),
    mm: pad2(date.getMinutes()),
    ss: pad2(date.getSeconds()),
  }
}

// object key 日期分段 <YYYY-MM-DD>（本地时区）。
function objectKeyDate(date) {
  const p = localDateParts(date)
  return p.y + '-' + p.m + '-' + p.d
}

// fragment_id 时间前缀 <YYYYMMDDTHHMMSS>（本地时区，tech-spec §3.1）。
function fragmentTimestamp(date) {
  const p = localDateParts(date)
  return p.y + p.m + p.d + 'T' + p.hh + p.mm + p.ss
}

// ISO 8601 带本地时区偏移（如 2026-05-26T14:48:00+08:00）。
function toIso(date) {
  const offsetMinutes = -date.getTimezoneOffset()
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const abs = Math.abs(offsetMinutes)
  const p = localDateParts(date)
  return (
    p.y + '-' + p.m + '-' + p.d + 'T' + p.hh + ':' + p.mm + ':' + p.ss +
    sign + pad2(Math.floor(abs / 60)) + ':' + pad2(abs % 60)
  )
}

// US-012 仅做 object key 预览：fragment_id 的 deviceShortId + ULID 在 US-015 正式生成并持久化，
// 这里用 pending 占位，仅用于草稿确认前预览目标 object key 形态，不会发送给 FC / OSS。
function previewFragmentId(recordedAt) {
  return fragmentTimestamp(recordedAt) + '_pending_pending'
}

// fragment_id 正则（与 FC fc_shared/sts.py 的 _FRAGMENT_ID_RE 保持一致）：
// <YYYYMMDDTHHMMSS>_<deviceShortId 4-8>_<ULID 26>。
const FRAGMENT_ID_RE =
  /^\d{4}\d{2}\d{2}T\d{6}_[A-Za-z0-9]{4,8}_[0-9A-Za-z]{26}$/

// US-015 正式 fragment_id：<本地时间前缀>_<deviceShortId>_<ULID>（ULID 由调用方生成，保证唯一）。
function buildFragmentId(recordedAt, deviceShortId, ulidStr) {
  return fragmentTimestamp(recordedAt) + '_' + deviceShortId + '_' + ulidStr
}

// object key 预览：recordings/<YYYY-MM-DD>/<fragment_id>.wav（始终 .wav 目标扩展名）。
function buildObjectKeyPreview(fragmentId, recordedAt) {
  return 'recordings/' + objectKeyDate(recordedAt) + '/' + fragmentId + OSS_OBJECT_KEY_EXT
}

// 构造 US-012 范围内的草稿 manifest（部分字段）。
// 本 story 仅落地 audio.original_format / duration / 临时路径 / object key 预览；
// session_id / chunk_seq / chunk_total / sha256 等完整字段在 US-015 补齐。
function buildDraftManifest(opts) {
  const recordedAt = opts.recordedAt
  const originalFormat = detectOriginalFormat(opts.tempFilePath, opts.requestedFormat)
  const fragmentId = previewFragmentId(recordedAt)
  return {
    recorded_at: toIso(recordedAt),
    duration_seconds: Math.round((Number(opts.durationMs) || 0) / 100) / 10,
    temp_file_path: String(opts.tempFilePath || ''),
    audio: {
      original_format: originalFormat,
      size_bytes: Number(opts.fileSize) || 0,
    },
    object_key_preview: buildObjectKeyPreview(fragmentId, recordedAt),
  }
}

// US-015 上传前 manifest 草案：在草稿确认（保存并上传）时补齐正式 fragment_id / session_id /
// chunk_seq / chunk_total / upload.original_sha256，供 OSS 直传与 Worker HeadObject 读回（tech-spec §3.3）。
// chunk_total：非分片单条录音为 null（manifest 语义；OSS meta 侧映射为 0，见 buildOssMetadata）。
function buildUploadManifestDraft(opts) {
  const recordedAt = opts.recordedAt
  const fragmentId = opts.fragmentId
  const chunkTotal =
    opts.chunkTotal === undefined || opts.chunkTotal === null ? null : opts.chunkTotal
  return {
    fragment_id: fragmentId,
    session_id: String(opts.sessionId || ''),
    chunk_seq: Number(opts.chunkSeq) || 1,
    chunk_total: chunkTotal,
    device_id: String(opts.deviceShortId || ''),
    recorded_at: toIso(recordedAt),
    duration_seconds: Number(opts.durationSeconds) || 0,
    audio: {
      original_format: opts.originalFormat || 'unknown',
      size_bytes: Number(opts.sizeBytes) || 0,
    },
    upload: {
      original_sha256: String(opts.originalSha256 || ''),
    },
    object_key: buildObjectKeyPreview(fragmentId, recordedAt),
    temp_file_path: String(opts.tempFilePath || ''),
  }
}

// US-015 AC#6：从 manifest 草案派生 OSS 用户自定义元数据（tech-spec §3.2）。
// 非分片 chunk_total 在 OSS meta 中写 0（manifest 内为 null）。
function buildOssMetadata(manifest) {
  const audio = (manifest && manifest.audio) || {}
  const upload = (manifest && manifest.upload) || {}
  const chunkTotal = manifest.chunk_total == null ? 0 : manifest.chunk_total
  return {
    'x-oss-meta-session-id': String(manifest.session_id || ''),
    'x-oss-meta-chunk-seq': String(manifest.chunk_seq),
    'x-oss-meta-chunk-total': String(chunkTotal),
    'x-oss-meta-recorded-at': String(manifest.recorded_at || ''),
    'x-oss-meta-duration': String(manifest.duration_seconds),
    'x-oss-meta-original-format': String(audio.original_format || ''),
    'x-oss-meta-sha256': String(upload.original_sha256 || ''),
  }
}

module.exports = {
  FRAGMENT_ID_RE: FRAGMENT_ID_RE,
  formatDuration: formatDuration,
  extensionOf: extensionOf,
  detectOriginalFormat: detectOriginalFormat,
  objectKeyDate: objectKeyDate,
  fragmentTimestamp: fragmentTimestamp,
  toIso: toIso,
  buildObjectKeyPreview: buildObjectKeyPreview,
  buildFragmentId: buildFragmentId,
  buildDraftManifest: buildDraftManifest,
  buildUploadManifestDraft: buildUploadManifestDraft,
  buildOssMetadata: buildOssMetadata,
}
