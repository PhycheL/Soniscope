// 上传队列运行时（渲染无关）：封装「静默登录 → STS → OSS 直传 → verify」编排、
// 48h 本地缓存自动清理、手动重传 / 重新 verify / 删除，供录音页历史弹层复用。
//
// 设计：所有 wx IO 通过注入的 wx 适配器完成；纯逻辑仍复用 utils/uploader、utils/verify、
// utils/retention、utils/uploads_view、utils/upload_queue。与 pages/uploads/uploads.js 的
// 内联编排保持一致（uploads 页为既有单测的参照实现，故其控制器不改；本模块承载录音页历史弹层）。
//
// 用法：const rt = createQueueRuntime({ wx, config, logger, faultInjection, onChange })
//   rt.autoCleanup(); rt.load(); await rt.drive();
// onChange(queue) 在队列变更时回调，页面据此重渲染。

const {
  UPLOAD_QUEUE_STORAGE_KEY,
  STATUS_QUEUED,
  STATUS_PENDING_VERIFY,
  updateQueueItem,
} = require('./upload_queue')
const { uploadFragment } = require('./uploader')
const { verifyFragment } = require('./verify')
const {
  selectAutoDeletable,
  needsDeleteConfirmation,
  DELETE_CONFIRM_MESSAGE,
} = require('./retention')

function createQueueRuntime(opts) {
  const wx = opts.wx
  const config = opts.config
  const logger = opts.logger
  const faultInjection = opts.faultInjection
  const onChange = typeof opts.onChange === 'function' ? opts.onChange : function () {}

  let processing = false
  let verifying = false

  function faults() {
    return faultInjection.loadFaults({
      env: config.ENV,
      getStorage: function (k) { return wx.getStorageSync(k) },
      setStorage: function (k, v) { wx.setStorageSync(k, v) },
    })
  }

  function readQueue() {
    try {
      return wx.getStorageSync(UPLOAD_QUEUE_STORAGE_KEY) || []
    } catch (e) {
      return []
    }
  }

  function writeQueue(queue) {
    wx.setStorageSync(UPLOAD_QUEUE_STORAGE_KEY, queue)
    onChange(queue)
  }

  function patchItem(fragmentId, patch) {
    writeQueue(updateQueueItem(readQueue(), fragmentId, patch))
  }

  // 网络可用性判断；缺失 getNetworkType（如测试环境）时保守视为离线，避免误触网络调用。
  function isOnline() {
    if (faultInjection.isEnabled(faults(), faultInjection.FAULT_NETWORK_OFFLINE)) {
      return Promise.resolve(false)
    }
    if (!wx || typeof wx.getNetworkType !== 'function') {
      return Promise.resolve(false)
    }
    return new Promise(function (resolve) {
      try {
        wx.getNetworkType({
          success: function (res) {
            resolve(!!(res && res.networkType && res.networkType !== 'none'))
          },
          fail: function () { resolve(true) },
        })
      } catch (e) {
        resolve(false)
      }
    })
  }

  function wxLogin() {
    return new Promise(function (resolve, reject) {
      wx.login({
        success: function (res) {
          return res && res.code ? resolve(res.code) : reject(new Error('NO_CODE'))
        },
        fail: function (err) { reject(err) },
      })
    })
  }

  function wxRequestSts(code, fragmentId, size) {
    if (faultInjection.isEnabled(faults(), faultInjection.FAULT_FC_URL_BROKEN)) {
      return Promise.reject(new Error('MOCK_FC_URL_BROKEN'))
    }
    return new Promise(function (resolve, reject) {
      wx.request({
        url: config.FC_ISSUE_CREDENTIAL_URL,
        method: 'POST',
        header: { 'content-type': 'application/json' },
        data: { code: code, fragment_id: fragmentId, size: size },
        success: function (res) { resolve({ statusCode: res.statusCode, data: res.data }) },
        fail: function (err) { reject(err) },
      })
    })
  }

  function wxRequestVerify(code, fragmentId, expectedSize) {
    const f = faults()
    if (faultInjection.isEnabled(f, faultInjection.FAULT_FC_URL_BROKEN)) {
      return Promise.reject(new Error('MOCK_FC_URL_BROKEN'))
    }
    if (faultInjection.isEnabled(f, faultInjection.FAULT_VERIFY_FAIL)) {
      return Promise.resolve({ statusCode: 200, data: { verified: false, reason: 'OBJECT_NOT_FOUND' } })
    }
    return new Promise(function (resolve, reject) {
      wx.request({
        url: config.FC_VERIFY_UPLOAD_URL,
        method: 'POST',
        header: { 'content-type': 'application/json' },
        data: { code: code, fragment_id: fragmentId, expected_size: expectedSize },
        success: function (res) { resolve({ statusCode: res.statusCode, data: res.data }) },
        fail: function (err) { reject(err) },
      })
    })
  }

  function wxUploadFile(o) {
    return new Promise(function (resolve, reject) {
      const task = wx.uploadFile({
        url: o.url,
        filePath: o.filePath,
        name: o.name,
        formData: o.formData,
        success: function (res) { resolve({ statusCode: res.statusCode, data: res.data }) },
        fail: function (err) { reject(err) },
      })
      if (task && task.onProgressUpdate && o.onProgress) {
        task.onProgressUpdate(function (p) { o.onProgress(p.progress) })
      }
    })
  }

  function uploadOne(fragmentId) {
    const item = readQueue().find(function (it) { return it && it.fragmentId === fragmentId })
    if (!item) {
      return Promise.resolve()
    }
    const deps = {
      logger: logger,
      region: config.OSS_REGION,
      uploadUrl: config.OSS_UPLOAD_URL,
      now: function () { return new Date() },
      login: wxLogin,
      requestSts: wxRequestSts,
      uploadFile: wxUploadFile,
      wait: function (ms) { return new Promise(function (r) { setTimeout(r, ms) }) },
      onStatus: function (status, extra) {
        patchItem(fragmentId, Object.assign({ status: status }, extra))
      },
      onProgress: function (percent) { patchItem(fragmentId, { progress: percent }) },
    }
    return uploadFragment(item, deps)
  }

  function verifyOne(fragmentId) {
    const item = readQueue().find(function (it) { return it && it.fragmentId === fragmentId })
    if (!item) {
      return Promise.resolve()
    }
    const deps = {
      logger: logger,
      now: function () { return Date.now() },
      login: wxLogin,
      requestVerify: wxRequestVerify,
      wait: function (ms) { return new Promise(function (r) { setTimeout(r, ms) }) },
      onStatus: function (status, extra) {
        patchItem(fragmentId, Object.assign({ status: status }, extra))
      },
    }
    return verifyFragment(item, deps)
  }

  async function processQueue() {
    if (processing) {
      return
    }
    processing = true
    try {
      if (!(await isOnline())) {
        return
      }
      let queue = readQueue()
      for (let i = 0; i < queue.length; i++) {
        const item = queue[i]
        if (!item || item.status !== STATUS_QUEUED) {
          continue
        }
        await uploadOne(item.fragmentId)
        queue = readQueue()
      }
    } finally {
      processing = false
    }
  }

  async function processVerifyQueue() {
    if (verifying) {
      return
    }
    verifying = true
    try {
      if (!(await isOnline())) {
        return
      }
      let queue = readQueue()
      for (let i = 0; i < queue.length; i++) {
        const item = queue[i]
        if (!item || item.status !== STATUS_PENDING_VERIFY) {
          continue
        }
        await verifyOne(item.fragmentId)
        queue = readQueue()
      }
    } finally {
      verifying = false
    }
  }

  // PLACEHOLDER_PUBLIC

  function unlinkFile(filePath) {
    if (!filePath) {
      return
    }
    try {
      wx.getFileSystemManager().unlink({ filePath: filePath, success: function () {}, fail: function () {} })
    } catch (e) {
      // best-effort：临时文件可能已不存在。
    }
  }

  // 自动清理本地缓存（verified 且距今 >= 48h）：只删本地文件，保留队列记录与 OSS 对象。
  function autoCleanup() {
    const deletable = selectAutoDeletable(readQueue(), Date.now())
    if (!deletable.length) {
      return
    }
    deletable.forEach(function (it) {
      unlinkFile(it.tempFilePath)
      const next = updateQueueItem(readQueue(), it.fragmentId, { localDeleted: true })
      wx.setStorageSync(UPLOAD_QUEUE_STORAGE_KEY, next)
      logger.info('local cache auto-cleaned (verified >= 48h)', { fragmentId: it.fragmentId })
    })
    onChange(readQueue())
  }

  // 依次上传 queued 项，再驱动 pending_verify 项 verify。
  async function drive() {
    await processQueue()
    await processVerifyQueue()
  }

  // 手动重传：重置该 Fragment 重试计数（状态回 queued、清错误码），重跑 STS+OSS+verify。
  async function manualRetry(fragmentId) {
    if (!fragmentId) {
      return
    }
    patchItem(fragmentId, { status: STATUS_QUEUED, errorCode: '', reason: '', progress: 0 })
    logger.info('manual retry requested', { fragmentId: fragmentId })
    await uploadOne(fragmentId)
    const after = readQueue().find(function (it) { return it && it.fragmentId === fragmentId })
    if (after && after.status === STATUS_PENDING_VERIFY) {
      await verifyOne(fragmentId)
    }
    onChange(readQueue())
  }

  // 手动重新 verify。
  async function reVerify(fragmentId) {
    if (!fragmentId) {
      return
    }
    await verifyOne(fragmentId)
    onChange(readQueue())
  }

  // 手动删除（未 verified 需二次确认；verified 可直接删）。
  function remove(fragmentId) {
    if (!fragmentId) {
      return
    }
    const item = readQueue().find(function (it) { return it && it.fragmentId === fragmentId })
    if (!item) {
      return
    }
    function doRemove() {
      unlinkFile(item.tempFilePath)
      writeQueue(readQueue().filter(function (it) { return !(it && it.fragmentId === fragmentId) }))
    }
    if (needsDeleteConfirmation(item) && wx && typeof wx.showModal === 'function') {
      wx.showModal({
        title: '确认删除',
        content: DELETE_CONFIRM_MESSAGE,
        success: function (res) { if (res && res.confirm) { doRemove() } },
      })
      return
    }
    doRemove()
  }

  return {
    readQueue: readQueue,
    autoCleanup: autoCleanup,
    drive: drive,
    manualRetry: manualRetry,
    reVerify: reVerify,
    remove: remove,
  }
}

module.exports = { createQueueRuntime: createQueueRuntime }
