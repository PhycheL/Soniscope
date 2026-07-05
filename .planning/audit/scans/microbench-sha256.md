# 微基准档案:sha256.js 主线程哈希计时(D-16)

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

本档案是 D-16 允许的本阶段唯一"对象执行"例外——对基线导出的纯函数 `apps/miniprogram/utils/sha256.js` 做 node 计时,佐证 HYP-03(主线程纯 JS 哈希性能疑点)。与 Phase 2 D-06 harness 先例同构:被测代码经 `git archive`/`git show` 从基线导出到会话 scratchpad(仓库外),计时脚本 `bench_sha256.js` 仅存在于 scratchpad,零仓库写入、零云 IO。**结论定位:静态论证为主判据,本档案数值仅作辅助证据——Mac 环境非真机,量级参考**(D-16)。

## 命令与环境

```bash
# 被测对象:基线导出副本(03-01 已导出,内容由基线 SHA 唯一决定)
# $SCRATCH = 会话 scratchpad 目录(仓库外)
git archive 5927f36 apps scripts | tar -x -C "$SCRATCH/baseline-5927f36"
node "$SCRATCH/bench_sha256.js"
```

| 项 | 值 |
|----|----|
| Node.js | v22.18.0 |
| 平台 | darwin/arm64(**Mac 非真机**——微信小程序真机 JS 引擎与低端设备性能显著低于桌面 V8,数值只作量级参考) |
| 被测模块 | `$SCRATCH/baseline-5927f36/apps/miniprogram/utils/sha256.js`(= `apps/miniprogram/utils/sha256.js @ 5927f36`) |
| 脚本位置 | `$SCRATCH/bench_sha256.js`(仓外,不入库) |

## 脚本要点与来源断言

- **来源断言**(仿 Phase 2 harness 先例):脚本首部以 `require.resolve` 校验被测模块绝对路径必须以 scratchpad 目录开头,否则 `exit 1`——结构性保证不会误测工作树/仓库内文件。
- **正确性对照**:计时前先对 1 MiB 随机字节比对 `sha256Hex` 与 node stdlib `crypto.createHash('sha256')` hex 输出,一致才进入计时(本次 ✓)。
- **计时方法**:`process.hrtime.bigint()` 包裹单次 `sha256Hex(buf)` 调用;每档体量多轮计时取**中位数**;体量档取 1 MiB(短录音)、10 MiB(≈10 分钟分片典型体量,主测档)、50 MiB(`MAX_UPLOAD_BYTES` 上限)。
- 输入为 `crypto.randomBytes` 生成的 Buffer(sha256.js `toBytes` 接受 TypedArray 路径,与小程序 `readFileSync` 返回 ArrayBuffer 的处理链同构)。

## 结果(各轮与中位数)

```
correctness: sha256Hex(1MiB) == crypto sha256 hex ✓
node v22.18.0 | platform darwin/arm64
 1 MiB Buffer: rounds=[14.3, 16.6, 13.8, 13.6, 13.6] ms; median=13.8 ms; throughput≈72.7 MB/s
10 MiB Buffer: rounds=[136.7, 137.2, 136.5, 136.4, 136.0] ms; median=136.5 ms; throughput≈73.3 MB/s
50 MiB Buffer: rounds=[684.1, 681.5, 682.7] ms; median=682.7 ms; throughput≈73.2 MB/s
post-bench rss=194 MiB
```

| 体量 | 轮数 | 中位数 | 吞吐 |
|------|------|--------|------|
| 1 MiB | 5 | 13.8 ms | ≈72.7 MB/s |
| 10 MiB(典型分片) | 5 | 136.5 ms | ≈73.3 MB/s |
| 50 MiB(上传上限) | 3 | 682.7 ms | ≈73.2 MB/s |

吞吐随体量线性(算法 O(n),无超线性退化);`hashWords` padding 阶段整段复制输入(`sha256.js:76-77 @ 5927f36`),峰值内存约 2× 音频字节,与静态论证一致。

## 复跑说明(PATTERNS 存档义务)

```bash
# 1) 任选仓库外目录为 $SCRATCH,导出基线副本(内容由 SHA 唯一决定,会话更替可重导)
mkdir -p "$SCRATCH/baseline-5927f36"
git archive 5927f36 apps scripts | tar -x -C "$SCRATCH/baseline-5927f36"
# 2) 在 $SCRATCH 重写 bench_sha256.js(要点见上节:来源断言 + crypto 对照 + hrtime 多轮取中位,
#    体量档 1/10/50 MiB;脚本本体不入库,按要点可完全重建)
# 3) node "$SCRATCH/bench_sha256.js"
```

## 结论(一句)

桌面 Mac(node v22, arm64)上纯 JS 实现对 10 MiB 典型分片单次哈希 ≈137 ms、50 MiB 上限 ≈683 ms(≈73 MB/s,O(n) 线性)——**Mac 环境非真机,量级参考**;真机低端设备 JS 引擎按常识慢一个数量级级别时,10 MiB 主线程同步哈希将进入秒级可感知卡顿区间,方向上支持 HYP-03 的"低端设备 UI 卡顿"担忧,主判据仍以静态论证为准(回填见 HYPOTHESES.md HYP-03)。

---
*微基准档案: 2026-07-05(D-16 唯一执行例外;3 档体量 × 多轮中位数,正确性对照 ✓,脚本仅存 scratchpad 零仓库写入——03-07 收口,Phase 3 产物封版)*
