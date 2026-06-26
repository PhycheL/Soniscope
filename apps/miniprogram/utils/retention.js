// 本地缓存保留策略（US-018 AC#5/#6/#7）：
//
// * AC#5：仅当 verified 且 verified_at 距当前 >= 48 小时，才可自动清理本地音频缓存；
// * AC#6：verified:false / 待人工重传 / 待人工 verify 的文件即使超过 7 天也永不自动删除；
// * AC#7：手动删除未 verify 通过的记录需二次确认。
// OSS 对象永不删除（AGENTS 安全红线）；自动清理只删本地音频缓存、保留队列记录。
//
// 本模块只放纯函数；Page（uploads）负责真实 wx 文件 IO 与 showModal。

const { STATUS_VERIFIED } = require('./upload_queue')

const RETENTION_HOURS = 48
const RETENTION_MS = RETENTION_HOURS * 60 * 60 * 1000

// 手动删除未 verify 通过记录的二次确认文案（PRD / AC#7 措辞）。
const DELETE_CONFIRM_MESSAGE = '该录音尚未成功上传到云端，删除后无法恢复，确定删除？'

// 该项是否可自动清理本地音频缓存（AC#5）：必须 verified、未清理过、且 verified_at 距今 >= 48 小时。
function canAutoDelete(item, nowMs) {
  if (!item || item.status !== STATUS_VERIFIED) {
    return false
  }
  if (item.localDeleted) {
    return false
  }
  if (item.verifiedAt == null || item.verifiedAt === '') {
    return false
  }
  const verifiedAt = Number(item.verifiedAt)
  if (!Number.isFinite(verifiedAt)) {
    return false
  }
  return Number(nowMs) - verifiedAt >= RETENTION_MS
}

// 选出当前可自动清理的项（AC#5/#6：任何未 verified 的记录一律不入选）。
function selectAutoDeletable(queue, nowMs) {
  const list = Array.isArray(queue) ? queue : []
  return list.filter(function (it) {
    return canAutoDelete(it, nowMs)
  })
}

// 手动删除是否需要二次确认（AC#7：未 verify 通过的记录需确认）。
function needsDeleteConfirmation(item) {
  return !item || item.status !== STATUS_VERIFIED
}

module.exports = {
  RETENTION_HOURS: RETENTION_HOURS,
  RETENTION_MS: RETENTION_MS,
  DELETE_CONFIRM_MESSAGE: DELETE_CONFIRM_MESSAGE,
  canAutoDelete: canAutoDelete,
  selectAutoDeletable: selectAutoDeletable,
  needsDeleteConfirmation: needsDeleteConfirmation,
}
