// 长录音自动分片纯逻辑（US-016）。
//
// 超过分片阈值（CHUNK_MAX_DURATION_SECONDS = 600s，tech-spec §3.1）的录音自动切成多个 Fragment：
//   - 整段录音共享一个 session_id（录音开始时分配，AC#1）；
//   - 每个分片独立 fragment_id，chunk_seq 从 1 递增（AC#3）；
//   - 用户最终停止后把 chunk_total 回填到该 session 下所有分片 manifest 草案（AC#4）；
//   - 单分片（未触发分片）chunk_total 为 null（非分片单条录音语义，与 US-015 一致）。
//
// 本模块只放可静态校验 / 可单测的纯函数（不依赖 wx 运行时）；
// Page（pages/index/index.js）持有会话实例，在 wx 录音回调与计时器中驱动分片。

const { CHUNK_MAX_DURATION_SECONDS } = require('../config')

// 是否到达分片边界：当前分片已录时长（秒）达到阈值即应自动 stop 当前片并 start 下一片（AC#2/#5）。
// 计时器每秒触发一次本判断；阈值为 600s，配合 stop→start 的极小间隙，单分片实际时长 ≤ 605s。
function shouldRotateChunk(chunkElapsedSeconds) {
  return Number(chunkElapsedSeconds) >= CHUNK_MAX_DURATION_SECONDS
}

// 创建一个录音会话：sessionId 在录音开始时分配，所有自动分片共享（AC#1）。
function createRecordingSession(sessionId) {
  return { sessionId: String(sessionId || ''), chunks: [] }
}

// 追加一个分片采集记录（tempFilePath / durationMs / recordedAt 等原始数据），
// 分配 chunk_seq（从 1 递增，AC#3）并返回带 chunk_seq 的记录。
function addChunk(session, record) {
  const seq = session.chunks.length + 1
  const entry = Object.assign({}, record, { chunk_seq: seq })
  session.chunks.push(entry)
  return entry
}

// 当前已累计分片数。
function chunkCount(session) {
  return session && Array.isArray(session.chunks) ? session.chunks.length : 0
}

// chunk_total 解析：发生过自动分片（>= 2 片）时为片数；单片（未分片）为 null。
function resolveChunkTotal(count) {
  return Number(count) > 1 ? Number(count) : null
}

// 把 chunk_total 回填到该 session 下所有 chunk manifest 草案（AC#4），返回回填值。
// 单片时回填 null（非分片语义）；多片时回填片数。
function backfillChunkTotal(manifests) {
  const list = Array.isArray(manifests) ? manifests : []
  const total = resolveChunkTotal(list.length)
  list.forEach(function (m) {
    if (m) {
      m.chunk_total = total
    }
  })
  return total
}

module.exports = {
  CHUNK_MAX_DURATION_SECONDS: CHUNK_MAX_DURATION_SECONDS,
  shouldRotateChunk: shouldRotateChunk,
  createRecordingSession: createRecordingSession,
  addChunk: addChunk,
  chunkCount: chunkCount,
  resolveChunkTotal: resolveChunkTotal,
  backfillChunkTotal: backfillChunkTotal,
}
