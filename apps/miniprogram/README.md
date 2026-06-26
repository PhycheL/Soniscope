# 日观声记 SoniScope 微信小程序

极薄前端：录音 → 草稿确认 → 静默登录拿 STS → 直传 OSS → verify → 上传列表。
业务鉴权、签发、校验都在云端 FC；小程序源码中**绝不**出现长期 AccessKey / AppSecret / 业务密钥。

## 用微信开发者工具打开

1. 微信开发者工具 → 导入项目 → 目录选择本目录 `apps/miniprogram/`。
2. AppID 已登记为 `wx3f973c7297728b0c`（见 `project.config.json`）。
3. 编译后模拟器进入「录音」首页与「上传列表」两个页面。

## 服务器合法域名（微信公众平台 → 开发管理 → 服务器域名）

单一真实来源为 `config.js`，需在公众平台后台配置一致：

| 类型 | 域名 |
|---|---|
| request | `https://issue-cedential-ottfirocds.cn-beijing.fcapp.run` |
| request | `https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run` |
| uploadFile | `https://soniscope-audio.oss-cn-beijing.aliyuncs.com` |

> `issue-cedential` 子域名确实少一个 `r`，是阿里云分配的真实 URL，不要“修正”拼写。

## 静态检查

```bash
make lint   # ruff（Python）+ 小程序源码静态检查（lint-miniprogram）
```

`lint-miniprogram` 校验：JSON 配置可解析、AppID 正确、合法域名齐全且未被错误修正、
页面文件完整、源码中无硬编码密钥。

## 后续 story

录音/草稿/上传/状态机等在 US-012 ~ US-020 逐步实现；本 story（US-011）只交付骨架与环境配置。
