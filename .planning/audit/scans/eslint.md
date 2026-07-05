# 扫描档案:ESLint 临时配方(小程序 JS)

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

per D-05(JS 侧无仓内配置临时 ESLint,顺带量化 HYP-15 漏报面)/ D-07(命令+版本+输出存档)。配置文件 `eslint.config.mjs` 写在 scratchpad 基线导出根目录(仓库外,满足 D-05 零仓库写入;配置内容逐字取 03-RESEARCH.md Code Examples #5 注释中的平面配置);`cd` 到导出根运行,扫描路径限定非测试 JS(`apps/miniprogram/{utils,pages}/**/*.js` + `app.js` + `config.js`),不含 test/(Pitfall 3,测试 JS 归 Phase 4)。输出中的导出前缀已统一改写为仓库相对路径。包合法性已经 03-01 Task 2 人工批准。**注意(反 Anti-Pattern):ESLint 结果只是线索与 HYP-15 漏报面量化底数,不是小程序 JS 的质量判据**(CHARTER 双语言适配声明:以仓库既有惯例为基准)。

**工具版本:** eslint 9.39.4(经 `npx --yes eslint@9 --version` 实测)/ node v22.18.0 / npm 10.9.3

## 配置文件(scratchpad 导出根 `eslint.config.mjs`,逐字存档)

```js
export default [{ files:["**/*.js"],
  languageOptions:{ ecmaVersion:2020, sourceType:"commonjs",
    globals:{ wx:"readonly",App:"readonly",Page:"readonly",Component:"readonly",
      getApp:"readonly",getCurrentPages:"readonly",module:"writable",require:"readonly",
      exports:"writable",console:"readonly",setTimeout:"readonly",clearTimeout:"readonly",
      setInterval:"readonly",clearInterval:"readonly",globalThis:"readonly" } },
  rules:{ "no-undef":"error","no-unused-vars":"warn","no-shadow":"warn","eqeqeq":"warn",
    "no-fallthrough":"error","no-unreachable":"error","no-dupe-keys":"error",
    "no-redeclare":"error","no-empty":"warn","no-prototype-builtins":"warn",
    "consistent-return":"warn","no-var":"off" } }];
```

## 扫描:小程序非测试 JS 全量

```bash
cd "$EXPORT" && npx --yes eslint@9 --no-config-lookup -c eslint.config.mjs \
  "apps/miniprogram/utils/**/*.js" "apps/miniprogram/pages/**/*.js" \
  "apps/miniprogram/app.js" "apps/miniprogram/config.js"
```

**命中计数:29 问题(0 error / 29 warning)**。与 RESEARCH 探针的 43 问题差异说明:探针含 test/ 目录(13 个 error 全为测试文件 Node 全局误报,Pitfall 3);本次按定稿配方限定非测试路径,error 归零,warning 面即 HYP-15 漏报面的量化底数。

```
apps/miniprogram/pages/index/index.js
  379:14  warning  'e' is defined but never used  no-unused-vars
  425:14  warning  'e' is defined but never used  no-unused-vars
  552:14  warning  'e' is defined but never used  no-unused-vars
  602:14  warning  'e' is defined but never used  no-unused-vars
  656:16  warning  'e' is defined but never used  no-unused-vars
  688:14  warning  'e' is defined but never used  no-unused-vars

apps/miniprogram/pages/uploads/uploads.js
  100:14  warning  'e' is defined but never used  no-unused-vars
  174:16  warning  'e' is defined but never used  no-unused-vars
  311:14  warning  'e' is defined but never used  no-unused-vars

apps/miniprogram/utils/audio.js
  160:43  warning  Expected '===' and instead saw '=='  eqeqeq

apps/miniprogram/utils/device.js
  39:12  warning  'e' is defined but never used  no-unused-vars
  48:12  warning  'e' is defined but never used  no-unused-vars

apps/miniprogram/utils/fault_injection.js
   89:12  warning  'e' is defined but never used  no-unused-vars
  103:12  warning  'e' is defined but never used  no-unused-vars

apps/miniprogram/utils/logger.js
  40:5  warning  Unused eslint-disable directive (no problems were reported from 'no-console')

apps/miniprogram/utils/queue_runtime.js
   47:14  warning  'e' is defined but never used  no-unused-vars
   77:16  warning  'e' is defined but never used  no-unused-vars
  240:14  warning  'e' is defined but never used  no-unused-vars

apps/miniprogram/utils/retention.js
  26:23  warning  Expected '===' and instead saw '=='  eqeqeq

apps/miniprogram/utils/uploader.js
   36:30  warning  Expected '===' and instead saw '=='  eqeqeq
   78:12  warning  'e' is defined but never used        no-unused-vars
   87:12  warning  'e' is defined but never used        no-unused-vars
  131:14  warning  'e' is defined but never used        no-unused-vars

apps/miniprogram/utils/uploads_view.js
   86:12  warning  Expected '===' and instead saw '=='  eqeqeq
   89:18  warning  Expected '===' and instead saw '=='  eqeqeq
   98:14  warning  Expected '===' and instead saw '=='  eqeqeq
  223:10  warning  Expected '===' and instead saw '=='  eqeqeq

apps/miniprogram/utils/verify.js
  72:14  warning  'e' is defined but never used  no-unused-vars
  88:14  warning  'e' is defined but never used  no-unused-vars

✖ 29 problems (0 errors, 29 warnings)
  0 errors and 1 warning potentially fixable with the `--fix` option.
```

## 三态销号表(03-02 填)

| # | 命中(path:line @ 5927f36) | 规则/模式 | 销号 | 理由/去向 |
|---|---------------------------|-----------|------|-----------|
