// SoniScope 微信小程序 · 常量定义
// 本项目不使用 process.env；所有配置集中在此文件。

module.exports = {
  // ── 微信小程序 ──────────────────────────────────────────────
  APP_ID: 'wx3f973c7297728b0c',

  // ── FC 3.0 公网 URL ────────────────────────────────────────
  // 注意：issue-credential 的 FC URL 子域名确实是 issue-cedential（少一个 r）
  // 这是阿里云分配的真实 URL，不要"修正"拼写。
  FC_ISSUE_CREDENTIAL_URL: 'https://issue-cedential-ottfirocds.cn-beijing.fcapp.run',
  FC_VERIFY_UPLOAD_URL: 'https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run',

  // ── OSS 上传 ────────────────────────────────────────────────
  OSS_UPLOAD_DOMAIN: 'https://soniscope-audio.oss-cn-beijing.aliyuncs.com',

  // ── 分片阈值 ────────────────────────────────────────────────
  CHUNK_MAX_DURATION_SECONDS: 600,

  // ── 上传重试 ────────────────────────────────────────────────
  UPLOAD_MAX_RETRIES: 3,
  UPLOAD_RETRY_INTERVALS: [5000, 15000, 45000],

  // ── 本地缓存保留（毫秒） ────────────────────────────────────
  AUDIO_RETENTION_MS: 48 * 60 * 60 * 1000,

  // ── 环境 ────────────────────────────────────────────────────
  // 通过 project.config.json 中的 projectname 区分环境
  // "soniscope"（正式版）vs "soniscope-dev"（开发版）
  IS_PRODUCTION: false,  // 默认非生产；生产发布前改为 true

  // ── 上传状态 ────────────────────────────────────────────────
  UPLOAD_STATUS: {
    DRAFT: 'draft',
    QUEUED: 'queued',
    UPLOADING: 'uploading',
    PENDING_VERIFY: 'pending_verify',
    VERIFIED: 'verified',
    UPLOAD_FAILED: 'upload_failed',
    MANUAL_RETRY: 'manual_retry',
    MANUAL_VERIFY: 'manual_verify',
  },

  // 中文状态文案映射
  UPLOAD_STATUS_CN: {
    draft: '草稿',
    queued: '待上传（离线排队）',
    uploading: '上传中',
    pending_verify: '待 verify',
    verified: '上传成功（verified）',
    upload_failed: '上传失败',
    manual_retry: '待人工重传',
    manual_verify: '待人工 verify',
  },
};
