// 上传队列纯逻辑（US-014：草稿确认态点击「保存并上传」→ 草稿冻结并晋升为「待上传」队列项）。
//
// 本 story 只把已确认的草稿落盘成一条上传队列记录，让上传列表页出现「待上传 / 上传中」记录；
// 真正的 fragment_id 生成（US-015）、静默登录 / STS / OSS 直传（US-017）、verify（US-018）后续补齐。
// 本模块只放可静态校验 / 可单测的纯函数；Page（index / uploads）只做 wx storage IO 与渲染。

// 上传状态（tech-spec §6.7 八状态）。US-014 落地前两态；US-017 增加上传中→待 verify
// 与失败→待人工重传；八态全量渲染 / 折叠在 US-019。
const STATUS_QUEUED = 'queued'
const STATUS_UPLOADING = 'uploading'
const STATUS_PENDING_VERIFY = 'pending_verify'
const STATUS_VERIFIED = 'verified'
const STATUS_UPLOAD_FAILED = 'upload_failed'
const STATUS_MANUAL_RETRY = 'manual_retry'
const STATUS_MANUAL_VERIFY = 'manual_verify'

const STATUS_TEXT = {
  draft: '草稿',
  queued: '待上传',
  uploading: '上传中',
  pending_verify: '待 verify',
  verified: '上传成功',
  upload_failed: '上传失败',
  manual_retry: '待人工重传',
  manual_verify: '待人工 verify',
}

// 上传队列本地落盘 key（uploads 页读取渲染）。
const UPLOAD_QUEUE_STORAGE_KEY = 'soniscope:upload_queue'

function statusText(status) {
  return STATUS_TEXT[status] || String(status || '')
}

// 从 object key 预览（recordings/<date>/<id>.wav）反推 fragmentId（去目录、去扩展名）。
// US-014 复用草稿的 object key 预览作为列表展示 / 去重键；US-015 落地正式 fragment_id 后替换。
function fragmentIdFromObjectKey(objectKey) {
  const s = String(objectKey || '')
  const slash = s.lastIndexOf('/')
  const name = slash === -1 ? s : s.slice(slash + 1)
  const dot = name.lastIndexOf('.')
  return dot === -1 ? name : name.slice(0, dot)
}

// 从已确认（冻结）的草稿构造上传队列项。
// US-015：传入 manifest（含正式 fragment_id / object_key / sha256）与 ossMetadata 时，
// 队列项使用正式 fragment_id 与 object key，并携带 manifest 草案 + OSS 元数据供 US-017 直传使用；
// 不传时退回 US-014 行为（从 object key 预览反推 fragmentId）。
function buildQueuedFragment(draft, manifest, ossMetadata) {
  const m = manifest || null
  const audio = (draft && draft.audio) || {}
  const objectKey = (m && m.object_key) || (draft && draft.object_key_preview) || ''
  const fragmentId = (m && m.fragment_id) || fragmentIdFromObjectKey(objectKey)
  const item = {
    fragmentId: fragmentId,
    status: STATUS_QUEUED,
    statusText: statusText(STATUS_QUEUED),
    durationSeconds: (draft && draft.duration_seconds) || 0,
    originalFormat:
      audio.original_format || (m && m.audio && m.audio.original_format) || 'unknown',
    objectKeyPreview: objectKey,
    tempFilePath: (draft && draft.temp_file_path) || '',
  }
  if (m) {
    item.manifest = m
  }
  if (ossMetadata) {
    item.ossMetadata = ossMetadata
  }
  return item
}

// 追加到队列；同一 fragmentId 已存在则不重复追加（AC#5：不允许重复点击生成重复 Fragment）。
function appendQueuedFragment(queue, item) {
  const list = Array.isArray(queue) ? queue.slice() : []
  for (let i = 0; i < list.length; i++) {
    if (list[i] && list[i].fragmentId === item.fragmentId) {
      return list
    }
  }
  list.push(item)
  return list
}

// 更新队列中指定 fragmentId 项的字段（US-017 上传状态机：status / progress / errorCode 等）。
// patch 中的 status 会自动同步 statusText。返回新数组（不可变更新）。
function updateQueueItem(queue, fragmentId, patch) {
  const list = Array.isArray(queue) ? queue.slice() : []
  for (let i = 0; i < list.length; i++) {
    if (list[i] && list[i].fragmentId === fragmentId) {
      const next = Object.assign({}, list[i], patch)
      if (patch && patch.status) {
        next.statusText = statusText(patch.status)
      }
      list[i] = next
      return list
    }
  }
  return list
}

module.exports = {
  STATUS_QUEUED: STATUS_QUEUED,
  STATUS_UPLOADING: STATUS_UPLOADING,
  STATUS_PENDING_VERIFY: STATUS_PENDING_VERIFY,
  STATUS_VERIFIED: STATUS_VERIFIED,
  STATUS_UPLOAD_FAILED: STATUS_UPLOAD_FAILED,
  STATUS_MANUAL_RETRY: STATUS_MANUAL_RETRY,
  STATUS_MANUAL_VERIFY: STATUS_MANUAL_VERIFY,
  STATUS_TEXT: STATUS_TEXT,
  UPLOAD_QUEUE_STORAGE_KEY: UPLOAD_QUEUE_STORAGE_KEY,
  statusText: statusText,
  fragmentIdFromObjectKey: fragmentIdFromObjectKey,
  buildQueuedFragment: buildQueuedFragment,
  appendQueuedFragment: appendQueuedFragment,
  updateQueueItem: updateQueueItem,
}
