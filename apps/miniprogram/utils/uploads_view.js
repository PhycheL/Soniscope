// 上传列表页视图模型（US-019）：把扁平的上传队列渲染为
//   - 八种状态中文文案（AC#1/#9）；
//   - 顶部「未上传 N 条，距离最早录音已 X 小时」离线积压提示（AC#4）；
//   - 同一 session_id 多个 chunk 折叠为一张长录音卡片（AC#6/#7/#8）。
//
// 本模块只放可静态校验 / 可单测的纯函数；Page（uploads）负责 wx storage IO、
// setData 渲染与上传 / verify / 重传编排。
//
// 数据来源：队列项形如 { fragmentId, status, statusText, durationSeconds,
//   progress, errorCode, reason, verifiedAt, localDeleted, tempFilePath,
//   manifest: { session_id, chunk_seq, chunk_total, recorded_at, ... } }。

const {
  STATUS_QUEUED,
  STATUS_PENDING_VERIFY,
  STATUS_VERIFIED,
  STATUS_UPLOAD_FAILED,
  STATUS_MANUAL_RETRY,
  STATUS_MANUAL_VERIFY,
  statusText,
} = require('./upload_queue')
const { formatDuration } = require('./audio')

// 计入「未上传积压」的状态（AC#4：待上传 / 上传失败 / 待人工重传 / 待人工 verify，按单 chunk 计数）。
const BACKLOG_STATUSES = [
  STATUS_QUEUED,
  STATUS_UPLOAD_FAILED,
  STATUS_MANUAL_RETRY,
  STATUS_MANUAL_VERIFY,
]

// 失败 / 需人工干预的状态（AC#2 红色标记、AC#7 折叠卡片「X / N 失败」）。
const FAILED_STATUSES = [STATUS_UPLOAD_FAILED, STATUS_MANUAL_RETRY, STATUS_MANUAL_VERIFY]

// 可点击「手动重传」的状态（AC#2/#3：上传失败 / 待人工重传 → 重置重试计数后重跑 STS+OSS+verify）。
const MANUAL_RETRY_STATUSES = [STATUS_UPLOAD_FAILED, STATUS_MANUAL_RETRY]

// 可点击「重新 verify」的状态（US-018：待 verify / 待人工 verify；verified 也允许手动复验）。
const RE_VERIFY_STATUSES = [STATUS_PENDING_VERIFY, STATUS_MANUAL_VERIFY, STATUS_VERIFIED]

function inSet(set, status) {
  return set.indexOf(String(status || '')) !== -1
}

function isBacklog(item) {
  return !!item && inSet(BACKLOG_STATUSES, item.status)
}

function isFailed(item) {
  return !!item && inSet(FAILED_STATUSES, item.status)
}

function canManualRetry(status) {
  return inSet(MANUAL_RETRY_STATUSES, status)
}

function canReVerify(status) {
  return inSet(RE_VERIFY_STATUSES, status)
}

// 队列项录制时间（毫秒）。优先 manifest.recorded_at（ISO 字符串），无法解析时返回 null。
function recordedAtMs(item) {
  const iso = item && item.manifest && item.manifest.recorded_at
  if (!iso) {
    return null
  }
  const ms = Date.parse(String(iso))
  return Number.isFinite(ms) ? ms : null
}

// AC#4：未上传积压条数（按单个 chunk 计数）。
function countBacklog(queue) {
  const list = Array.isArray(queue) ? queue : []
  return list.filter(isBacklog).length
}

// 最早一条积压记录的录制时间（毫秒）；无积压或无可解析时间时返回 null。
function earliestBacklogMs(queue) {
  const list = Array.isArray(queue) ? queue : []
  let earliest = null
  list.forEach(function (it) {
    if (!isBacklog(it)) {
      return
    }
    const ms = recordedAtMs(it)
    if (ms == null) {
      return
    }
    if (earliest == null || ms < earliest) {
      earliest = ms
    }
  })
  return earliest
}

// 两个时间戳之间的整小时数（向下取整，不为负）。
function hoursBetween(fromMs, nowMs) {
  if (fromMs == null) {
    return 0
  }
  const diff = Number(nowMs) - Number(fromMs)
  if (!Number.isFinite(diff) || diff <= 0) {
    return 0
  }
  return Math.floor(diff / (60 * 60 * 1000))
}

// AC#4：顶部积压提示。存在待上传 / 上传失败 / 待人工重传 / 待人工 verify 时显示
// 「未上传 N 条，距离最早录音已 X 小时」（N 按单 chunk 计数）。
function buildBanner(queue, nowMs) {
  const count = countBacklog(queue)
  if (count === 0) {
    return { visible: false, count: 0, hours: 0, text: '' }
  }
  const hours = hoursBetween(earliestBacklogMs(queue), nowMs)
  return {
    visible: true,
    count: count,
    hours: hours,
    text: '未上传 ' + count + ' 条，距离最早录音已 ' + hours + ' 小时',
  }
}

// 单条记录 → 视图项（单卡片或折叠卡片内的 chunk 行复用）。
function toChunkView(item) {
  const status = (item && item.status) || ''
  return {
    fragmentId: (item && item.fragmentId) || '',
    chunkSeq: (item && item.manifest && item.manifest.chunk_seq) || 1,
    status: status,
    statusText: (item && item.statusText) || statusText(status),
    durationSeconds: (item && item.durationSeconds) || 0,
    durationText: formatDuration((item && item.durationSeconds) || 0),
    progress: (item && item.progress) || 0,
    errorCode: (item && item.errorCode) || '',
    reason: (item && item.reason) || '',
    localDeleted: !!(item && item.localDeleted),
    isFailed: isFailed(item),
    canManualRetry: canManualRetry(status),
    canReVerify: canReVerify(status),
  }
}

// 长录音聚合状态文案（AC#7）：任一 chunk 失败 → 「X / N 失败」；全部 verified → 「已完成」；
// 其余（进行中）→ 「M / N 已完成」。
function aggregateStatus(chunks) {
  const total = chunks.length
  const failed = chunks.filter(function (c) {
    return c.isFailed
  }).length
  const verified = chunks.filter(function (c) {
    return c.status === STATUS_VERIFIED
  }).length
  if (failed > 0) {
    return { kind: 'failed', text: failed + ' / ' + total + ' 失败' }
  }
  if (verified === total && total > 0) {
    return { kind: 'done', text: '已完成' }
  }
  return { kind: 'progress', text: verified + ' / ' + total + ' 已完成' }
}

// AC#6/#7/#8：把队列按 session_id 折叠为卡片列表。
// 同一 session_id 含 >= 2 个 chunk → 一张折叠长录音卡片；否则按单条记录渲染。
// 保持首次出现顺序。
function buildCards(queue) {
  const list = Array.isArray(queue) ? queue : []
  const groups = []
  const indexBySession = {}
  list.forEach(function (item) {
    if (!item) {
      return
    }
    const sessionId = (item.manifest && item.manifest.session_id) || ''
    // 无 session_id 的项各自成组（不折叠）。
    const key = sessionId ? 's:' + sessionId : null
    if (key && Object.prototype.hasOwnProperty.call(indexBySession, key)) {
      groups[indexBySession[key]].items.push(item)
      return
    }
    const group = { sessionId: sessionId, items: [item] }
    if (key) {
      indexBySession[key] = groups.length
    }
    groups.push(group)
  })

  return groups.map(function (group) {
    if (group.items.length <= 1) {
      const view = toChunkView(group.items[0])
      view.type = 'single'
      return view
    }
    const chunks = group.items
      .map(toChunkView)
      .sort(function (a, b) {
        return Number(a.chunkSeq) - Number(b.chunkSeq)
      })
    const totalDuration = chunks.reduce(function (sum, c) {
      return sum + (Number(c.durationSeconds) || 0)
    }, 0)
    const agg = aggregateStatus(chunks)
    return {
      type: 'session',
      sessionId: group.sessionId,
      chunkCount: chunks.length,
      totalDurationSeconds: totalDuration,
      // AC#6：例如 "25:00 · 3 段"。
      summaryText: formatDuration(totalDuration) + ' · ' + chunks.length + ' 段',
      aggregateKind: agg.kind,
      aggregateText: agg.text,
      chunks: chunks,
    }
  })
}

module.exports = {
  BACKLOG_STATUSES: BACKLOG_STATUSES,
  FAILED_STATUSES: FAILED_STATUSES,
  MANUAL_RETRY_STATUSES: MANUAL_RETRY_STATUSES,
  RE_VERIFY_STATUSES: RE_VERIFY_STATUSES,
  isBacklog: isBacklog,
  isFailed: isFailed,
  canManualRetry: canManualRetry,
  canReVerify: canReVerify,
  recordedAtMs: recordedAtMs,
  countBacklog: countBacklog,
  earliestBacklogMs: earliestBacklogMs,
  hoursBetween: hoursBetween,
  buildBanner: buildBanner,
  toChunkView: toChunkView,
  aggregateStatus: aggregateStatus,
  buildCards: buildCards,
}
