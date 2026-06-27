// 开发者故障注入（US-020）：仅非 production 环境可见、可运行时切换的故障注入开关，
// 用于真机构造 FC 失效、网络离线和 verify 失败等异常路径（tech-spec §6.1）。
//
// 设计沿用 codebase「纯逻辑 + IO 注入」分层：
// * 开关名 / 归一化 / 启用判定 / 视图模型为纯函数，直接 node 单测；
// * 存储读写经注入的 storage 适配器，且统一受 ENV 门控——
//   production 环境读永远返回全部关闭、写直接忽略（即便菜单已不可见也安全兜底）。

const FAULT_FC_URL_BROKEN = 'mock-fc-url-broken'
const FAULT_NETWORK_OFFLINE = 'mock-network-offline'
const FAULT_VERIFY_FAIL = 'mock-verify-fail'

// 三个开关的展示信息（tech-spec §6.1 表）。name 即 storage 中的键。
const FAULT_SWITCHES = [
  {
    name: FAULT_FC_URL_BROKEN,
    label: '所有 FC 请求强制失败',
    hint: '验证自动重试后进入待人工重传',
  },
  {
    name: FAULT_NETWORK_OFFLINE,
    label: '模拟网络离线',
    hint: '保存并上传进入待上传（离线排队）',
  },
  {
    name: FAULT_VERIFY_FAIL,
    label: 'verify 永远返回 verified:false',
    hint: '验证待人工 verify / 待人工重传路径',
  },
]

const FAULT_NAMES = FAULT_SWITCHES.map(function (s) {
  return s.name
})
const FAULT_STORAGE_KEY = 'soniscope:fault_injection'

// 非 production 即视为开发环境（AC#1）。
function isDevEnv(env) {
  return env !== 'production'
}

// 把任意来源对象归一化为「每个已知开关 → 布尔」，未知键丢弃。
function normalizeFaults(raw) {
  const out = {}
  FAULT_NAMES.forEach(function (n) {
    out[n] = !!(raw && raw[n])
  })
  return out
}

function isEnabled(faults, name) {
  return !!(faults && faults[name])
}

// 不可变设置某个开关；未知开关名不产生副作用。
function setFault(faults, name, on) {
  const next = normalizeFaults(faults)
  if (FAULT_NAMES.indexOf(name) !== -1) {
    next[name] = !!on
  }
  return next
}

// 不可变翻转某个开关。
function toggleFault(faults, name) {
  const next = normalizeFaults(faults)
  if (FAULT_NAMES.indexOf(name) !== -1) {
    next[name] = !next[name]
  }
  return next
}

// 投影为带 label / hint / enabled 的视图模型（供 dev 菜单渲染）。
function buildSwitchViews(faults) {
  const norm = normalizeFaults(faults)
  return FAULT_SWITCHES.map(function (s) {
    return { name: s.name, label: s.label, hint: s.hint, enabled: norm[s.name] }
  })
}

// 读取开关状态（受 ENV 门控）。deps：{ env, getStorage(key), setStorage(key, val) }。
function loadFaults(deps) {
  if (!isDevEnv(deps.env)) {
    return normalizeFaults({})
  }
  let raw = {}
  try {
    raw = deps.getStorage(FAULT_STORAGE_KEY) || {}
  } catch (e) {
    raw = {}
  }
  return normalizeFaults(raw)
}

// 持久化开关状态（受 ENV 门控）。production 直接忽略写入并返回全关。
function saveFaults(deps, faults) {
  const next = normalizeFaults(faults)
  if (!isDevEnv(deps.env)) {
    return normalizeFaults({})
  }
  try {
    deps.setStorage(FAULT_STORAGE_KEY, next)
  } catch (e) {
    // best-effort：storage 不可用时静默忽略。
  }
  return next
}

module.exports = {
  FAULT_FC_URL_BROKEN: FAULT_FC_URL_BROKEN,
  FAULT_NETWORK_OFFLINE: FAULT_NETWORK_OFFLINE,
  FAULT_VERIFY_FAIL: FAULT_VERIFY_FAIL,
  FAULT_SWITCHES: FAULT_SWITCHES,
  FAULT_NAMES: FAULT_NAMES,
  FAULT_STORAGE_KEY: FAULT_STORAGE_KEY,
  isDevEnv: isDevEnv,
  normalizeFaults: normalizeFaults,
  isEnabled: isEnabled,
  setFault: setFault,
  toggleFault: toggleFault,
  buildSwitchViews: buildSwitchViews,
  loadFaults: loadFaults,
  saveFaults: saveFaults,
}
