// 小程序合法域名与运行配置（单一真实来源）。
//
// 这些 URL 与 docs/runbook/cloud-setup.md §3-4 登记的真实云资源一致，
// 同时必须在「微信公众平台 → 开发管理 → 服务器域名」中按下列清单配置：
//   - request 合法域名：FC_ISSUE_CREDENTIAL_URL、FC_VERIFY_UPLOAD_URL
//   - uploadFile 合法域名：OSS_UPLOAD_URL
//
// 注意：issue-cedential 子域名确实少一个 r，是阿里云分配的真实 URL，不要“修正”拼写。

const FC_ISSUE_CREDENTIAL_URL = 'https://issue-cedential-ottfirocds.cn-beijing.fcapp.run'
const FC_VERIFY_UPLOAD_URL = 'https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run'
const OSS_UPLOAD_URL = 'https://soniscope-audio.oss-cn-beijing.aliyuncs.com'

// request 合法域名（两条，FC 3.0 每函数子域名独立，白名单不支持通配符）
const REQUEST_LEGAL_DOMAINS = [FC_ISSUE_CREDENTIAL_URL, FC_VERIFY_UPLOAD_URL]
// uploadFile 合法域名
const UPLOAD_LEGAL_DOMAINS = [OSS_UPLOAD_URL]

// 长录音分片阈值（tech-spec §3.1：CHUNK_MAX_DURATION_SECONDS = 600，本期作为前端常量管理）
const CHUNK_MAX_DURATION_SECONDS = 600

// OSS object key 目标扩展名（即使原始格式非 wav，object key 始终用 .wav，表示 Worker 侧标准化目标）
const OSS_OBJECT_KEY_EXT = '.wav'

// 运行环境：production 构建不显示开发者菜单 / 故障注入（US-020）
const ENV = 'development'

module.exports = {
  FC_ISSUE_CREDENTIAL_URL,
  FC_VERIFY_UPLOAD_URL,
  OSS_UPLOAD_URL,
  REQUEST_LEGAL_DOMAINS,
  UPLOAD_LEGAL_DOMAINS,
  CHUNK_MAX_DURATION_SECONDS,
  OSS_OBJECT_KEY_EXT,
  ENV,
}
