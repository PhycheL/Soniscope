## Context

小程序当前在草稿确认态使用 `wx.createInnerAudioContext()` 做本地试听。iOS 真机日志显示，用户多次点击试听、暂停、重录/删除草稿后切后台，会在 `onHide` 之后收到多条 `operateAudio:fail jsapi has no permission ... runningState=background` 错误。

现状代码把音频上下文挂在首页实例上，但 `onAudition()` 每次调用都会注册新的 `onEnded` / `onError` 回调；`_stopAudition()` 只 stop，不解绑或销毁上下文；重录/删除/保存成功退出草稿态时也没有统一释放上下文。结果是试听回调可以越过草稿生命周期继续存在，iOS 后台权限更严格时会暴露为控制台错误。Android 行为可能更宽松，但这不是可依赖的产品语义。

后续 iOS 真机日志又显示试听已触发 `onCanplay` 和 `onPlay` 但用户仍听不到声音。该现象说明播放请求已进入微信音频播放态，剩余主要差异在 iOS 设备静音开关策略：草稿试听属于用户主动播放的预览动作，不应被系统静音开关静默吞掉，因此需要在试听前显式配置 inner audio 的 `obeyMuteSwitch: false`。

本变更只处理小程序前端试听生命周期。OSS/FC/Worker 数据链路不变。

## Goals / Non-Goals

**Goals:**

- 保持一个小程序代码库和一套业务状态机，iOS 与 Android 共享录音、草稿、上传、verify 流程。
- 让试听生命周期在重复试听、暂停、重录、删除、保存并上传、切后台、页面卸载路径上都可幂等清理。
- 避免重复注册音频事件监听器，避免预期的后台权限错误被当作业务错误反复打到控制台。
- 确保 iOS 真机草稿试听在 `onPlay` 已触发时实际可听，不被设备静音开关静默吞掉。
- 补充自动测试和真机验收清单，覆盖此前遗漏的 iOS/Android 试听后切后台路径。

**Non-Goals:**

- 不实现后台音频播放。
- 不新增 `requiredBackgroundModes: ["audio"]` 或类似后台音频权限。
- 不拆成 iOS 页面和 Android 页面两套实现。
- 不改 FC API、OSS object key/metadata、Worker 文件状态机或 ASR 流程。

## Decisions

1. **单实现优先，平台分支只做最小防护**

   录音、草稿、上传和 verify 流程继续由同一套页面逻辑驱动。平台差异只允许出现在音频清理或错误分类的小范围 helper 内，例如识别 iOS 后台态的预期 `operateAudio` 权限错误并降级处理。备选方案是维护 iOS/Android 两套页面或两套状态机，但这会让核心“不丢、不重”的上传链路出现双倍测试面。

2. **音频上下文由明确生命周期 helper 统一管理**

   首页引入清晰的内部协议：开始试听前确保旧上下文已停止并释放，创建新上下文后只注册一次 `onEnded` / `onError`；退出草稿态、切后台、页面卸载时调用同一个 release helper。这样比在每个按钮 handler 内零散 stop 更容易验证，也能避免多次点击试听造成监听器累积。

3. **后台路径以释放为主，不申请后台音频能力**

   SoniScope 的试听是草稿确认辅助动作，不是后台播放功能。`onHide` 时应该停止并释放试听资源，而不是让音频继续运行。申请后台音频能力会扩大产品语义，增加审核和用户感知风险。

4. **iOS 静音开关只作为播放选项处理**

   试听是用户显式点击后的前台预览，不是通知音或后台播放。实现上只在试听 helper 内调用 `wx.setInnerAudioOption({ obeyMuteSwitch: false })`，并保留上下文级兼容赋值；不引入 iOS 页面分支，也不影响录音、上传或 Worker 协议。

5. **测试覆盖行为契约而不模拟微信原生内核**

   自动测试侧重点是防止代码再次退化：禁止在 `onAudition()` 中反复注册监听器、要求所有草稿退出路径调用统一 release helper、要求 `onHide` / `onUnload` 释放音频上下文。微信 iOS 原生权限行为仍需真机 checklist 验证。

## Risks / Trade-offs

- [Risk] 每次试听前重建音频上下文可能比复用上下文略重。→ Mitigation: 草稿试听是低频操作，稳定性优先；如后续需要优化，可保留“单上下文、单次绑定”的实现，但必须保持可证明不重复绑定。
- [Risk] 微信基础库对 `offError` / `offEnded` 支持存在版本差异。→ Mitigation: release helper 以 `stop()` + `destroy()` 为核心，不依赖 off 系列 API；如使用 off API，必须有兼容 guard。
- [Risk] iOS 仍可能在极端时序下产生 native 异步错误。→ Mitigation: 对已释放/后台后的预期音频错误降级为 debug/info，不弹 toast，不影响草稿和上传状态；真机验收确认控制台无 error 级别噪声。

## Migration Plan

1. 修改首页试听 helper，统一创建、停止、销毁和状态复位。
2. 试听开始前配置 inner audio，使 iOS 前台草稿预览不服从设备静音开关。
3. 将重录、删除、保存成功、`onHide`、`onUnload` 全部接入同一个 release helper。
4. 补充静态/单元测试，锁定“监听器不重复注册”、“iOS 静音开关配置”和“所有退出路径释放上下文”。
5. 更新 MVP checklist，加入 iOS 与 Android 的试听生命周期 smoke test。
6. 验证：`make miniprogram-lint`、聚焦测试、`make test`；最后由用户在 iOS 和 Android 真机执行 checklist。

## Open Questions

- 是否当前只有 iOS 设备可测。如果 Android 设备暂时不可用，本 change 仍应把 Android 真机项写入 checklist，并把未执行结果明确标记为待验证。
