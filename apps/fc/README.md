# apps/fc —— 阿里云 FC 3.0 顶级 Web 函数源码

本目录存放两个 FC 3.0 顶级 Web 函数（**无 service 层级**）的源码：

| 代码目录（snake_case） | 云端函数名（kebab-case） | 公网 URL |
|---|---|---|
| `issue_credential/` | `issue-credential` | `https://issue-cedential-ottfirocds.cn-beijing.fcapp.run` |
| `verify_upload/`    | `verify-upload`    | `https://verify-upload-nnjpaoamhw.cn-beijing.fcapp.run` |

> `issue-cedential`（少一个 `r`）是阿里云分配的真实 URL，**不要"修正"拼写**。

## 部署 / 运维（顶层 Makefile 唯一入口）

```bash
make deploy-fc FUNCTION=issue-credential   # 打包 + 备份 + 部署单个函数
make deploy-fc FUNCTION=verify-upload
make deploy-fc                             # 不传 FUNCTION 时部署两个函数
make rollback-fc FUNCTION=issue-credential # 从最新备份回滚
make fc-logs FUNCTION=verify-upload        # 拉取近 1 小时日志
```

部署逻辑见 `apps/worker/src/soniscope_worker/fc_deploy.py`（纯逻辑可单测，云端 IO
lazy import `alibabacloud-fc20230330`，仅部署脚本使用、不随函数代码打包）。

- 打包产物：`build/fc/<function_name>/`（暂存目录）+ `build/fc/<function_name>.zip`
- Custom Runtime 入口：`apps/fc/shared/app.py` 会被复制到每个函数包根目录，匹配云端启动命令 `python3 app.py`
- 部署前备份：`build/fc/backup/<YYYYMMDD-HHMMSS>/<function_name>.zip`（仅记录环境变量名，不记录值）
- 部署日志：`build/fc/logs/deploy-<YYYYMMDD-HHMMSS>.log`
- 部署只更新**代码包**，不改环境变量 / 触发器 / 运行时规格 / 公网 URL

## 现状（US-005）

本期仅建立目录约定与可部署骨架；`handler.py` 为占位 WSGI 处理器，真实业务逻辑在
US-006 / US-007（issue-credential）与 US-006 / US-009（verify-upload）实现。
