// 录音中断保护与草稿恢复的纯逻辑（US-013）。
//
// 中断（锁屏、来电、切后台、杀进程）触发时，已录内容必须自动停止并保存为本地草稿；
// 回到前台后提示用户保留 / 丢弃 / 继续新录。本模块只放可静态校验 / 可单测的纯函数，
// Page（pages/index/index.js）只做 wx API 绑定与状态迁移。

const { buildDraftManifest } = require('./audio')

// 中断保存的草稿状态标记（AC#3）。
const STATUS_DRAFT_INTERRUPTED = 'draft_interrupted'
const STATUS_LABEL_DRAFT_INTERRUPTED = '草稿（被中断保存）'

// 本地草稿落盘的单一槽位 key（AC#2/#6：单槽位天然去重，后到的中断状态覆盖前一份）。
const INTERRUPT_DRAFT_STORAGE_KEY = 'soniscope:interrupted_draft'

// 回到前台后的提示文案（AC#4，措辞需与 PRD 一致）。
const RECOVERY_MESSAGE = '上次录音被中断，已自动保存草稿，是否保留 / 丢弃 / 继续新录？'

// 在 buildDraftManifest 基础上叠加中断状态标记，保证草稿包含录制时长（AC#3）。
function buildInterruptedDraft(opts) {
  const base = buildDraftManifest(opts)
  base.status = STATUS_DRAFT_INTERRUPTED
  base.status_label = STATUS_LABEL_DRAFT_INTERRUPTED
  base.interrupted = true
  base.interrupt_reason = String((opts && opts.interruptReason) || 'interruption')
  return base
}

// 构造前台恢复提示数据（供 wxml 渲染保留 / 丢弃 / 继续新录三个按钮）。
function buildRecoveryPrompt(draft) {
  return {
    message: RECOVERY_MESSAGE,
    durationSeconds: (draft && draft.duration_seconds) || 0,
    statusLabel: (draft && draft.status_label) || STATUS_LABEL_DRAFT_INTERRUPTED,
  }
}

// 去重（AC#6）：同一次录音连续多次中断只保留最后状态，不累计成多份草稿。
// 本地始终只有一个草稿槽位，后到的中断草稿覆盖前一份；无 incoming 时保留 existing。
function dedupeInterruptedDraft(existing, incoming) {
  return incoming || existing || null
}

module.exports = {
  STATUS_DRAFT_INTERRUPTED: STATUS_DRAFT_INTERRUPTED,
  STATUS_LABEL_DRAFT_INTERRUPTED: STATUS_LABEL_DRAFT_INTERRUPTED,
  INTERRUPT_DRAFT_STORAGE_KEY: INTERRUPT_DRAFT_STORAGE_KEY,
  RECOVERY_MESSAGE: RECOVERY_MESSAGE,
  buildInterruptedDraft: buildInterruptedDraft,
  buildRecoveryPrompt: buildRecoveryPrompt,
  dedupeInterruptedDraft: dedupeInterruptedDraft,
}
