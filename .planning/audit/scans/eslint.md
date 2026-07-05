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

核实方法:每条命中经 `git show 5927f36:<path>` 提取命中行及上下文人工判断。判据遵守 CHARTER 双语言适配声明与 RESEARCH Anti-Pattern:命中是否"确认"以仓库既有惯例为基准,不以外部 JS lint 标准作质量判据;纯风格类一律误报。行序与上方输出一致。

| # | 命中(path:line @ 5927f36) | 规则/模式 | 销号 | 理由/去向 |
|---|---------------------------|-----------|------|-----------|
| 1 | apps/miniprogram/pages/index/index.js:379 | no-unused-vars('e') | 误报 | catch(e) 形参未用系仓库既有惯例(基础库 3.5.5 时代写法,未用 ES2019 可选 catch 绑定),非质量信号;计入 HYP-15 量化底数(见尾部小结) |
| 2 | apps/miniprogram/pages/index/index.js:425 | no-unused-vars('e') | 误报 | 同 #1 |
| 3 | apps/miniprogram/pages/index/index.js:552 | no-unused-vars('e') | 误报 | 同 #1 |
| 4 | apps/miniprogram/pages/index/index.js:602 | no-unused-vars('e') | 误报 | 同 #1 |
| 5 | apps/miniprogram/pages/index/index.js:656 | no-unused-vars('e') | 误报 | 同 #1 |
| 6 | apps/miniprogram/pages/index/index.js:688 | no-unused-vars('e') | 误报 | 同 #1 |
| 7 | apps/miniprogram/pages/uploads/uploads.js:100 | no-unused-vars('e') | 误报 | 同 #1 |
| 8 | apps/miniprogram/pages/uploads/uploads.js:174 | no-unused-vars('e') | 误报 | 同 #1 |
| 9 | apps/miniprogram/pages/uploads/uploads.js:311 | no-unused-vars('e') | 误报 | 同 #1 |
| 10 | apps/miniprogram/utils/audio.js:160 | eqeqeq | 误报 | `manifest.chunk_total == null` 为故意宽松判空(同时捕获 undefined),仓库既有惯例写法 |
| 11 | apps/miniprogram/utils/device.js:39 | no-unused-vars('e') | 误报 | 同 #1 |
| 12 | apps/miniprogram/utils/device.js:48 | no-unused-vars('e') | 误报 | 同 #1 |
| 13 | apps/miniprogram/utils/fault_injection.js:89 | no-unused-vars('e') | 误报 | 同 #1 |
| 14 | apps/miniprogram/utils/fault_injection.js:103 | no-unused-vars('e') | 误报 | 同 #1 |
| 15 | apps/miniprogram/utils/logger.js:40 | unused eslint-disable directive | 误报 | 仓库无 ESLint,`// eslint-disable-next-line no-console` 为遗留防御性注释,无行为影响;该注释存在本身作为 HYP-15 旁证记入尾部小结 |
| 16 | apps/miniprogram/utils/queue_runtime.js:47 | no-unused-vars('e') | 误报 | 同 #1 |
| 17 | apps/miniprogram/utils/queue_runtime.js:77 | no-unused-vars('e') | 误报 | 同 #1 |
| 18 | apps/miniprogram/utils/queue_runtime.js:240 | no-unused-vars('e') | 误报 | 同 #1 |
| 19 | apps/miniprogram/utils/retention.js:26 | eqeqeq | 误报 | `item.verifiedAt == null` 故意宽松判空,同 #10 |
| 20 | apps/miniprogram/utils/uploader.js:36 | eqeqeq | 误报 | `data[f] == null` 故意宽松判空(凭证字段缺省检测),同 #10 |
| 21 | apps/miniprogram/utils/uploader.js:78 | no-unused-vars('e') | 误报 | 同 #1 |
| 22 | apps/miniprogram/utils/uploader.js:87 | no-unused-vars('e') | 误报 | 同 #1 |
| 23 | apps/miniprogram/utils/uploader.js:131 | no-unused-vars('e') | 误报 | 同 #1 |
| 24 | apps/miniprogram/utils/uploads_view.js:86 | eqeqeq | 误报 | `ms == null` 故意宽松判空(recordedAtMs 可返回 null),同 #10 |
| 25 | apps/miniprogram/utils/uploads_view.js:89 | eqeqeq | 误报 | `earliest == null` 初值判空,同 #10 |
| 26 | apps/miniprogram/utils/uploads_view.js:98 | eqeqeq | 误报 | `fromMs == null` 判空,同 #10 |
| 27 | apps/miniprogram/utils/uploads_view.js:223 | eqeqeq | 误报 | `ms == null` 判空(后接 Number.isFinite 复核),同 #10 |
| 28 | apps/miniprogram/utils/verify.js:72 | no-unused-vars('e') | 误报 | 同 #1 |
| 29 | apps/miniprogram/utils/verify.js:88 | no-unused-vars('e') | 误报 | 同 #1 |

**对账等式:** 确认 0 + 误报 29 + 移交 0 = 命中总数 29 ✓

**移交说明:** 本档无移交项。

## HYP-15 量化小结(供 03-05 审 miniprogram_lint.py 引用)

ESLint 相对仓内自定义门禁 miniprogram_lint 的增量检出面(非测试 JS 全量,即 HYP-15 漏报面量化底数):**0 error / 29 warning**。主导规则分布:

- `no-unused-vars` ×21——全部为 catch(e) 形参未用,仓库惯例写法,无一真实缺陷;
- `eqeqeq` ×7——全部为 `== null` 故意宽松判空惯用式,无一跨类型误比较;
- `unused eslint-disable directive` ×1——logger.js:40 遗留防御性注释,旁证开发时曾预期 ESLint 存在而仓库实际未配置。

结论要点:本次配方下 ESLint 增量命中经逐条核实**零真实缺陷**——miniprogram_lint 未检出这 29 处并不构成漏报实害;但 ESLint 检出面(未用变量/宽松相等/坠落分支/重复键等语义类规则)与 miniprogram_lint 现有规则面(合法域名、硬编码密钥、四文件约定)完全不重叠,HYP-15 的"规则覆盖面狭窄"半句由此获得量化参照。03-05 深挖时据此判断 miniprogram_lint 覆盖面是否需立发现。
