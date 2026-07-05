# 扫描档案:ruff 扩展规则集

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

per D-05(临时扩展分析器)/ D-07(命令+版本+输出存档)。扫描对象为 scratchpad 基线导出副本(导出路径见 COVERAGE.md 头部备注);命令逐字取 03-RESEARCH.md Code Examples #3 实测配方(`--isolated` 隔离仓内 pyproject 配置;`--ignore PLC0415,TRY003,S101` 为定稿降噪参数,Pitfall 2——PLC0415 撞项目故意懒导入模式,不得改动规则集)。输出中的导出前缀已统一改写为仓库相对路径,便于 `path:line @ 5927f36` 引用。命中 ≠ 发现:逐条人工核实后销号,03-02 填。

**工具版本:** ruff 0.15.20(仓内 uv.lock 锁定版,经 `uv run ruff --version` 实测;pyproject 声明 `>=0.4`——版本差本身是 TOOL 维度观察点)

## 扫描:worker src + fc + scripts 两文件,扩展规则集

```bash
# $EXPORT = scratchpad 基线导出根(仓库外)
uv run ruff check --isolated --target-version py311 \
  --select S,BLE,TRY,DTZ,ARG,ERA,SIM,RET,PLC,PLE,PLW \
  --ignore PLC0415,TRY003,S101 \
  "$EXPORT/apps/worker/src" "$EXPORT/apps/fc" \
  "$EXPORT/scripts/test_asr.py" "$EXPORT/scripts/fetch_test_fixtures.py"
```

**命中计数:69**(exit=1;RESEARCH 实测参考值 69 ✓)。规则分布:ARG001 ×24、ARG002 ×13、S105 ×7、TRY300 ×6、S106 ×6、S607 ×2、S603 ×2、PLW0108 ×2、DTZ011 ×2、TRY301 ×1、SIM105 ×1、S110 ×1、S104 ×1、DTZ005 ×1。命中文件分布注记:`apps/fc/tests/` 35 条(配方路径 `$EXPORT/apps/fc` 含 tests/,RESEARCH 配方原样;测试质量归 Phase 4,销号时可按"移交/误报"处置)、worker src 32 条、`apps/fc/shared/app.py` 1 条(S104,HYP-12 关联)、`scripts/fetch_test_fixtures.py` 1 条;35 + 32 + 1 + 1 = 69 ✓。

**完整输出(路径已改写为仓库相对):**

```
S104 Possible binding to all interfaces
  --> apps/fc/shared/app.py:27:12
   |
26 | def main() -> None:
27 |     host = "0.0.0.0"
   |            ^^^^^^^^^
28 |     port = _port()
29 |     with make_server(host, port, application, server_class=ThreadingWSGIServer) as server:
   |

ARG002 Unused method argument: `headers`
  --> apps/fc/tests/test_custom_runtime_app.py:18:37
   |
16 |         self.status = ""
17 |
18 |     def __call__(self, status: str, headers: list[tuple[str, str]]) -> Any:
   |                                     ^^^^^^^
19 |         self.status = status
20 |         return None
   |

ARG002 Unused method argument: `headers`
  --> apps/fc/tests/test_fc_handlers.py:54:37
   |
52 |         self.status = ""
53 |
54 |     def __call__(self, status: str, headers: list[tuple[str, str]]) -> Any:
   |                                     ^^^^^^^
55 |         self.status = status
56 |         return None
   |

ARG001 Unused function argument: `function`
  --> apps/fc/tests/test_fc_handlers.py:76:36
   |
75 | @pytest.mark.parametrize(("function", "source_dir", "_field"), HANDLERS)
76 | def test_handler_imports_fc_shared(function: str, source_dir: str, _field: str) -> None:
   |                                    ^^^^^^^^
77 |     mod = _load_handler(source_dir)
78 |     assert mod.fc_shared is fc_shared
   |

ARG001 Unused function argument: `function`
  --> apps/fc/tests/test_fc_handlers.py:93:5
   |
91 | @pytest.mark.parametrize(("function", "source_dir", "field"), HANDLERS)
92 | def test_handler_missing_env_is_500(
93 |     function: str, source_dir: str, field: str, monkeypatch: pytest.MonkeyPatch
   |     ^^^^^^^^
94 | ) -> None:
95 |     for key in REQUIRED_ENV:
   |

ARG001 Unused function argument: `function`
   --> apps/fc/tests/test_fc_handlers.py:107:5
    |
105 | @pytest.mark.parametrize(("function", "source_dir", "field"), HANDLERS)
106 | def test_handler_invalid_body_is_400(
107 |     function: str, source_dir: str, field: str, monkeypatch: pytest.MonkeyPatch
    |     ^^^^^^^^
108 | ) -> None:
109 |     for key, val in REQUIRED_ENV.items():
    |

ARG001 Unused function argument: `field`
   --> apps/fc/tests/test_fc_handlers.py:107:37
    |
105 | @pytest.mark.parametrize(("function", "source_dir", "field"), HANDLERS)
106 | def test_handler_invalid_body_is_400(
107 |     function: str, source_dir: str, field: str, monkeypatch: pytest.MonkeyPatch
    |                                     ^^^^^
108 | ) -> None:
109 |     for key, val in REQUIRED_ENV.items():
    |

ARG001 Unused function argument: `function`
   --> apps/fc/tests/test_fc_handlers.py:119:5
    |
117 | @pytest.mark.parametrize(("function", "source_dir", "field"), HANDLERS)
118 | def test_handler_not_in_allowlist_is_403(
119 |     function: str, source_dir: str, field: str, monkeypatch: pytest.MonkeyPatch
    |     ^^^^^^^^
120 | ) -> None:
121 |     env = {**REQUIRED_ENV, "OPENID_ALLOWLIST": "someone-else"}
    |

ARG001 Unused function argument: `code`
   --> apps/fc/tests/test_fc_handlers.py:125:29
    |
123 |         monkeypatch.setenv(key, val)
124 |
125 |     def fake_code_to_openid(code: str, appid: str, secret: str, **_kw: Any) -> str:
    |                             ^^^^
126 |         return "OID-allowed"
    |

ARG001 Unused function argument: `appid`
   --> apps/fc/tests/test_fc_handlers.py:125:40
    |
123 |         monkeypatch.setenv(key, val)
124 |
125 |     def fake_code_to_openid(code: str, appid: str, secret: str, **_kw: Any) -> str:
    |                                        ^^^^^
126 |         return "OID-allowed"
    |

ARG001 Unused function argument: `secret`
   --> apps/fc/tests/test_fc_handlers.py:125:52
    |
123 |         monkeypatch.setenv(key, val)
124 |
125 |     def fake_code_to_openid(code: str, appid: str, secret: str, **_kw: Any) -> str:
    |                                                    ^^^^^^
126 |         return "OID-allowed"
    |

S106 Possible hardcoded password assigned to argument: "access_key_secret"
   --> apps/fc/tests/test_fc_shared.py:207:9
    |
205 |         code="SECRET-CODE",
206 |         session_key="SECRET-SK",
207 |         access_key_secret="SECRET-AK",
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
208 |         security_token="SECRET-TOKEN",
209 |         decision="AUTHORIZED",
    |

S106 Possible hardcoded password assigned to argument: "security_token"
   --> apps/fc/tests/test_fc_shared.py:208:9
    |
206 |         session_key="SECRET-SK",
207 |         access_key_secret="SECRET-AK",
208 |         security_token="SECRET-TOKEN",
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
209 |         decision="AUTHORIZED",
210 |         elapsed_ms=12.3,
    |

S105 Possible hardcoded password assigned to: "ak_secret"
  --> apps/fc/tests/test_head.py:69:29
   |
67 |     env = fc_shared.load_verify_env({"ALIYUN_AK_ID": "id", "ALIYUN_AK_SECRET": "sec"})
68 |     assert env.ak_id == "id"
69 |     assert env.ak_secret == "sec"
   |                             ^^^^^
   |

ARG002 Unused method argument: `headers`
  --> apps/fc/tests/test_issue_credential.py:52:37
   |
50 |         self.status = ""
51 |
52 |     def __call__(self, status: str, headers: list[tuple[str, str]]) -> Any:
   |                                     ^^^^^^^
53 |         self.status = status
54 |         return None
   |

S106 Possible hardcoded password assigned to argument: "access_key_secret"
  --> apps/fc/tests/test_issue_credential.py:81:13
   |
79 |         return fc_shared.StsCredential(
80 |             access_key_id="STS.fakeid",
81 |             access_key_secret="fake-secret",
   |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
82 |             security_token="fake-token",
83 |             expiration="2026-05-26T15:03:00Z",
   |

S106 Possible hardcoded password assigned to argument: "security_token"
  --> apps/fc/tests/test_issue_credential.py:82:13
   |
80 |             access_key_id="STS.fakeid",
81 |             access_key_secret="fake-secret",
82 |             security_token="fake-token",
   |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
83 |             expiration="2026-05-26T15:03:00Z",
84 |         )
   |

ARG001 Unused function argument: `code`
  --> apps/fc/tests/test_issue_credential.py:88:14
   |
87 | def _allow_openid(monkeypatch: pytest.MonkeyPatch) -> None:
88 |     def fake(code: str, appid: str, secret: str, **_kw: Any) -> str:
   |              ^^^^
89 |         return "OID-allowed"
   |

ARG001 Unused function argument: `appid`
  --> apps/fc/tests/test_issue_credential.py:88:25
   |
87 | def _allow_openid(monkeypatch: pytest.MonkeyPatch) -> None:
88 |     def fake(code: str, appid: str, secret: str, **_kw: Any) -> str:
   |                         ^^^^^
89 |         return "OID-allowed"
   |

ARG001 Unused function argument: `secret`
  --> apps/fc/tests/test_issue_credential.py:88:37
   |
87 | def _allow_openid(monkeypatch: pytest.MonkeyPatch) -> None:
88 |     def fake(code: str, appid: str, secret: str, **_kw: Any) -> str:
   |                                     ^^^^^^
89 |         return "OID-allowed"
   |

PLW0108 Lambda may be unnecessary; consider inlining inner function
   --> apps/fc/tests/test_issue_credential.py:159:54
    |
157 |     _set_full_env(monkeypatch)
158 |     _allow_openid(monkeypatch)
159 |     monkeypatch.setattr(fc_shared.sts, "get_issuer", lambda: _FakeIssuer())
    |                                                      ^^^^^^^^^^^^^^^^^^^^^
160 |     mod = _load_handler()
161 |     body = json.dumps({"code": "c", "fragment_id": "bogus", "size": 100}).encode()
    |
help: Inline function call

ARG001 Unused function argument: `code`
   --> apps/fc/tests/test_issue_credential.py:186:16
    |
184 |     _set_full_env(monkeypatch)
185 |
186 |     def reject(code: str, appid: str, secret: str, **_kw: Any) -> str:
    |                ^^^^
187 |         raise fc_shared.FcHttpError(401, fc_shared.INVALID_CODE, message="bad code")
    |

ARG001 Unused function argument: `appid`
   --> apps/fc/tests/test_issue_credential.py:186:27
    |
184 |     _set_full_env(monkeypatch)
185 |
186 |     def reject(code: str, appid: str, secret: str, **_kw: Any) -> str:
    |                           ^^^^^
187 |         raise fc_shared.FcHttpError(401, fc_shared.INVALID_CODE, message="bad code")
    |

ARG001 Unused function argument: `secret`
   --> apps/fc/tests/test_issue_credential.py:186:39
    |
184 |     _set_full_env(monkeypatch)
185 |
186 |     def reject(code: str, appid: str, secret: str, **_kw: Any) -> str:
    |                                       ^^^^^^
187 |         raise fc_shared.FcHttpError(401, fc_shared.INVALID_CODE, message="bad code")
    |

ARG002 Unused method argument: `kwargs`
   --> apps/fc/tests/test_issue_credential.py:220:33
    |
219 |     class _Boom:
220 |         def assume_role(self, **kwargs: Any) -> fc_shared.StsCredential:
    |                                 ^^^^^^
221 |             raise RuntimeError("ak-secret leaked-here")  # 异常文本含敏感词
    |

PLW0108 Lambda may be unnecessary; consider inlining inner function
   --> apps/fc/tests/test_issue_credential.py:223:54
    |
221 |             raise RuntimeError("ak-secret leaked-here")  # 异常文本含敏感词
222 |
223 |     monkeypatch.setattr(fc_shared.sts, "get_issuer", lambda: _Boom())
    |                                                      ^^^^^^^^^^^^^^^
224 |     mod = _load_handler()
225 |     body = json.dumps({"code": "c", "fragment_id": FRAGMENT_ID, "size": 100}).encode()
    |
help: Inline function call

S106 Possible hardcoded password assigned to argument: "access_key_secret"
  --> apps/fc/tests/test_sts.py:96:9
   |
94 |     cred = sts.StsCredential(
95 |         access_key_id="STS.id",
96 |         access_key_secret="sec",
   |         ^^^^^^^^^^^^^^^^^^^^^^^
97 |         security_token="tok",
98 |         expiration="2026-05-26T15:03:00Z",
   |

S106 Possible hardcoded password assigned to argument: "security_token"
  --> apps/fc/tests/test_sts.py:97:9
   |
95 |         access_key_id="STS.id",
96 |         access_key_secret="sec",
97 |         security_token="tok",
   |         ^^^^^^^^^^^^^^^^^^^^
98 |         expiration="2026-05-26T15:03:00Z",
99 |     )
   |

S105 Possible hardcoded password assigned to: "ak_secret"
   --> apps/fc/tests/test_sts.py:153:29
    |
151 |     # ak_secret 字段名含 "secret"，audit 层会脱敏；这里确认 env 本身只承载值不打印。
152 |     env = fc_env.load_sts_env(_STS_ENV)
153 |     assert env.ak_secret == "ak-secret"
    |                             ^^^^^^^^^^^
154 |     assert fc_shared.is_sensitive("ALIYUN_AK_SECRET")
    |

ARG002 Unused method argument: `headers`
  --> apps/fc/tests/test_verify_upload.py:49:37
   |
47 |         self.status = ""
48 |
49 |     def __call__(self, status: str, headers: list[tuple[str, str]]) -> Any:
   |                                     ^^^^^^^
50 |         self.status = status
51 |         return None
   |

ARG001 Unused function argument: `code`
  --> apps/fc/tests/test_verify_upload.py:85:14
   |
84 | def _allow_openid(monkeypatch: pytest.MonkeyPatch) -> None:
85 |     def fake(code: str, appid: str, secret: str, **_kw: Any) -> str:
   |              ^^^^
86 |         return "OID-allowed"
   |

ARG001 Unused function argument: `appid`
  --> apps/fc/tests/test_verify_upload.py:85:25
   |
84 | def _allow_openid(monkeypatch: pytest.MonkeyPatch) -> None:
85 |     def fake(code: str, appid: str, secret: str, **_kw: Any) -> str:
   |                         ^^^^^
86 |         return "OID-allowed"
   |

ARG001 Unused function argument: `secret`
  --> apps/fc/tests/test_verify_upload.py:85:37
   |
84 | def _allow_openid(monkeypatch: pytest.MonkeyPatch) -> None:
85 |     def fake(code: str, appid: str, secret: str, **_kw: Any) -> str:
   |                                     ^^^^^^
86 |         return "OID-allowed"
   |

ARG001 Unused function argument: `code`
   --> apps/fc/tests/test_verify_upload.py:179:16
    |
177 |     _set_full_env(monkeypatch)
178 |
179 |     def reject(code: str, appid: str, secret: str, **_kw: Any) -> str:
    |                ^^^^
180 |         raise fc_shared.FcHttpError(401, fc_shared.INVALID_CODE, message="bad code")
    |

ARG001 Unused function argument: `appid`
   --> apps/fc/tests/test_verify_upload.py:179:27
    |
177 |     _set_full_env(monkeypatch)
178 |
179 |     def reject(code: str, appid: str, secret: str, **_kw: Any) -> str:
    |                           ^^^^^
180 |         raise fc_shared.FcHttpError(401, fc_shared.INVALID_CODE, message="bad code")
    |

ARG001 Unused function argument: `secret`
   --> apps/fc/tests/test_verify_upload.py:179:39
    |
177 |     _set_full_env(monkeypatch)
178 |
179 |     def reject(code: str, appid: str, secret: str, **_kw: Any) -> str:
    |                                       ^^^^^^
180 |         raise fc_shared.FcHttpError(401, fc_shared.INVALID_CODE, message="bad code")
    |

S603 `subprocess` call: check for execution of untrusted input
  --> apps/worker/src/soniscope_worker/audio.py:72:9
   |
70 |     """
71 |     try:
72 |         subprocess.run(
   |         ^^^^^^^^^^^^^^
73 |             [
74 |                 "ffmpeg",
   |

S607 Starting a process with a partial executable path
  --> apps/worker/src/soniscope_worker/audio.py:73:13
   |
71 |       try:
72 |           subprocess.run(
73 | /             [
74 | |                 "ffmpeg",
75 | |                 "-y",
76 | |                 "-i",
77 | |                 str(src),
78 | |                 "-vn",
79 | |                 "-ac",
80 | |                 "1",
81 | |                 "-ar",
82 | |                 "16000",
83 | |                 "-c:a",
84 | |                 "pcm_s16le",
85 | |                 # 输出文件名为 ``<id>.wav.tmp``，扩展名 .tmp 无法让 ffmpeg 推断 muxer，
86 | |                 # 必须显式指定 ``-f wav``。
87 | |                 "-f",
88 | |                 "wav",
89 | |                 str(dest),
90 | |             ],
   | |_____________^
91 |               capture_output=True,
92 |               text=True,
   |

TRY300 Consider moving this statement to an `else` block
   --> apps/worker/src/soniscope_worker/audio.py:140:9
    |
138 |     try:
139 |         os.replace(part, dest)
140 |         return dest
    |         ^^^^^^^^^^^
141 |     except OSError:  # pragma: no cover - part 已不存在等罕见情况
142 |         return None
    |

S105 Possible hardcoded password assigned to: "PASS"
  --> apps/worker/src/soniscope_worker/e2e_scenarios.py:62:8
   |
60 | from soniscope_worker.verify_prep import ProbeError
61 |
62 | PASS = "PASS"
   |        ^^^^^^
63 | FAIL = "FAIL"
64 | SKIP = "SKIP"
   |

ARG001 Unused function argument: `timestamp`
   --> apps/worker/src/soniscope_worker/fc_deploy.py:419:50
    |
418 | def rollback_one(
419 |     api: FcApi, build_root: Path, function: str, timestamp: str
    |                                                  ^^^^^^^^^
420 | ) -> DeployRecord:
421 |     """从最新备份恢复单个函数代码。"""
    |

DTZ005 `datetime.datetime.now()` called without a `tz` argument
   --> apps/worker/src/soniscope_worker/fc_deploy.py:463:12
    |
462 | def _now_stamp() -> str:
463 |     return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    |            ^^^^^^^^^^^^^^^^^^^^^^^
    |
help: Pass a `datetime.timezone` object to the `tz` parameter

TRY301 Abstract `raise` to an inner function
   --> apps/worker/src/soniscope_worker/fc_deploy.py:611:17
    |
609 |             url = getattr(getattr(resp, "body", None), "url", None)
610 |             if not url:
611 |                 raise FcApiError(f"线上 {function} 无可下载代码 URL（疑似首次部署）。")
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
612 |         except FcApiError:
613 |             raise
    |

TRY300 Consider moving this statement to an `else` block
   --> apps/worker/src/soniscope_worker/fc_deploy.py:634:13
    |
632 |             if isinstance(env, dict):
633 |                 return [str(k) for k in env]
634 |             return []
    |             ^^^^^^^^^
635 |         except ImportError as exc:  # pragma: no cover
636 |             raise FcApiError("缺少依赖 alibabacloud-fc20230330。") from exc
    |

ARG002 Unused method argument: `hours`
   --> apps/worker/src/soniscope_worker/fc_deploy.py:688:41
    |
686 |             return CurlResult(url=url, reachable=False, status=None, error=str(exc))
687 |
688 |     def fetch_logs(self, function: str, hours: float) -> list[str]:
    |                                         ^^^^^
689 |         # FC 运行时日志接入阿里云 SLS；未配置 project/logstore 时给明确诊断。
690 |         client = self._client()
    |

S105 Possible hardcoded password assigned to: "PASS"
   --> apps/worker/src/soniscope_worker/fc_live.py:121:8
    |
121 | PASS = "PASS"
    |        ^^^^^^
122 | FAIL = "FAIL"
123 | SKIP = "SKIP"
    |

S603 `subprocess` call: check for execution of untrusted input
   --> apps/worker/src/soniscope_worker/fixtures.py:131:16
    |
129 |     """
130 |     try:
131 |         proc = subprocess.run(
    |                ^^^^^^^^^^^^^^
132 |             [
133 |                 "ffprobe",
    |

S607 Starting a process with a partial executable path
   --> apps/worker/src/soniscope_worker/fixtures.py:132:13
    |
130 |       try:
131 |           proc = subprocess.run(
132 | /             [
133 | |                 "ffprobe",
134 | |                 "-v",
135 | |                 "error",
136 | |                 "-print_format",
137 | |                 "json",
138 | |                 "-show_format",
139 | |                 "-show_streams",
140 | |                 str(path),
141 | |             ],
    | |_____________^
142 |               capture_output=True,
143 |               text=True,
    |

ARG001 Unused function argument: `rel_path`
   --> apps/worker/src/soniscope_worker/miniprogram_lint.py:121:28
    |
121 | def scan_hardcoded_secrets(rel_path: str, text: str) -> list[str]:
    |                            ^^^^^^^^
122 |     """返回某文件中疑似硬编码密钥的描述（纯函数，便于单测）。"""
123 |     findings: list[str] = []
    |

DTZ011 `datetime.date.today()` used
   --> apps/worker/src/soniscope_worker/nls.py:251:12
    |
250 | def _today_iso() -> str:
251 |     return datetime.date.today().isoformat()
    |            ^^^^^^^^^^^^^^^^^^^^^
    |
help: Use `datetime.datetime.now(tz=...).date()` instead

ARG002 Unused method argument: `fragment_id`
   --> apps/worker/src/soniscope_worker/pipeline.py:582:15
    |
581 |     def transcribe(
582 |         self, fragment_id: str, audio_path: Path, oss_key: str
    |               ^^^^^^^^^^^
583 |     ) -> TranscriptResult:
584 |         from soniscope_worker.transcriber import Segment
    |

ARG002 Unused method argument: `audio_path`
   --> apps/worker/src/soniscope_worker/pipeline.py:582:33
    |
581 |     def transcribe(
582 |         self, fragment_id: str, audio_path: Path, oss_key: str
    |                                 ^^^^^^^^^^
583 |     ) -> TranscriptResult:
584 |         from soniscope_worker.transcriber import Segment
    |

ARG002 Unused method argument: `oss_key`
   --> apps/worker/src/soniscope_worker/pipeline.py:582:51
    |
581 |     def transcribe(
582 |         self, fragment_id: str, audio_path: Path, oss_key: str
    |                                                   ^^^^^^^
583 |     ) -> TranscriptResult:
584 |         from soniscope_worker.transcriber import Segment
    |

ARG002 Unused method argument: `object_key`
   --> apps/worker/src/soniscope_worker/pipeline.py:625:29
    |
623 |         return [OssListing(key=self._key, size=len(self._body))]
624 |
625 |     def head_metadata(self, object_key: str) -> dict[str, str]:
    |                             ^^^^^^^^^^
626 |         return dict(self._meta)
    |

ARG001 Unused function argument: `fragments_root`
   --> apps/worker/src/soniscope_worker/poller.py:249:61
    |
248 | def process_plan(
249 |     plan: PollPlan, source: OssSource, *, inbox_root: Path, fragments_root: Path
    |                                                             ^^^^^^^^^^^^^^
250 | ) -> ObjectOutcome:
251 |     """下载单个对象到 ``.part`` → 计算 sha256 → 读元数据 → 比对 sha256。
    |

ARG001 Unused function argument: `fragment_id`
   --> apps/worker/src/soniscope_worker/recovery.py:315:22
    |
315 | def _stub_transcript(fragment_id: str) -> dict[str, Any]:
    |                      ^^^^^^^^^^^
316 |     """make test 用的确定性占位转写结果（真实 NLS 转写器在 US-026）。"""
317 |     return {
    |

ARG002 Unused method argument: `fragment_id`
   --> apps/worker/src/soniscope_worker/retranscribe.py:371:26
    |
369 |         self._params = params_version
370 |
371 |     def transcribe(self, fragment_id: str, audio_path: Path, oss_key: str) -> Any:
    |                          ^^^^^^^^^^^
372 |         from soniscope_worker.transcriber import Segment, TranscriptResult
    |

ARG002 Unused method argument: `audio_path`
   --> apps/worker/src/soniscope_worker/retranscribe.py:371:44
    |
369 |         self._params = params_version
370 |
371 |     def transcribe(self, fragment_id: str, audio_path: Path, oss_key: str) -> Any:
    |                                            ^^^^^^^^^^
372 |         from soniscope_worker.transcriber import Segment, TranscriptResult
    |

ARG002 Unused method argument: `oss_key`
   --> apps/worker/src/soniscope_worker/retranscribe.py:371:62
    |
369 |         self._params = params_version
370 |
371 |     def transcribe(self, fragment_id: str, audio_path: Path, oss_key: str) -> Any:
    |                                                              ^^^^^^^
372 |         from soniscope_worker.transcriber import Segment, TranscriptResult
    |

S105 Possible hardcoded password assigned to: "PASS"
  --> apps/worker/src/soniscope_worker/sts_escape.py:45:8
   |
43 | )
44 |
45 | PASS = "PASS"
   |        ^^^^^^
46 | FAIL = "FAIL"
47 | SKIP = "SKIP"
   |

S105 Possible hardcoded password assigned to: "DEPLOY_AK_SECRET_ENV"
  --> apps/worker/src/soniscope_worker/verify_prep.py:64:24
   |
62 | # 部署期凭证环境变量（tech-spec §6.4）；绝不写死到代码 / git，从本地 .env 或 CI secret 注入。
63 | DEPLOY_AK_ID_ENV = "ALIYUN_DEPLOY_AK_ID"
64 | DEPLOY_AK_SECRET_ENV = "ALIYUN_DEPLOY_AK_SECRET"
   |                        ^^^^^^^^^^^^^^^^^^^^^^^^^
65 |
66 | # OSS 测试素材在 Bucket 中的 sample/ 前缀对象（NLS 拉取用，sha256 同 tests/audio/sample-20s.wav）。
   |

TRY300 Consider moving this statement to an `else` block
   --> apps/worker/src/soniscope_worker/verify_prep.py:636:9
    |
634 |         import alibabacloud_oss_v2 as oss
635 |
636 |         return oss
    |         ^^^^^^^^^^
637 |     except ImportError as exc:  # pragma: no cover - 依赖缺失路径
638 |         raise ProbeError(
    |

DTZ011 `datetime.date.today()` used
   --> apps/worker/src/soniscope_worker/verify_prep.py:656:12
    |
654 | # ── STS 越权反例：真实 IO 辅助 ───────────────────────────────────────────────
655 | def _today() -> str:
656 |     return datetime.date.today().isoformat()
    |            ^^^^^^^^^^^^^^^^^^^^^
    |
help: Use `datetime.datetime.now(tz=...).date()` instead

TRY300 Consider moving this statement to an `else` block
   --> apps/worker/src/soniscope_worker/verify_prep.py:675:9
    |
673 |         from alibabacloud_tea_openapi import models as open_api_models
674 |
675 |         return StsClient, sts_models, open_api_models
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
676 |     except ImportError as exc:  # pragma: no cover - 依赖缺失路径
677 |         raise ProbeError(
    |

TRY300 Consider moving this statement to an `else` block
   --> apps/worker/src/soniscope_worker/verify_prep.py:778:9
    |
776 |         from aliyunsdkcore.request import CommonRequest
777 |
778 |         return AcsClient, CommonRequest
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
779 |     except ImportError as exc:  # pragma: no cover - 依赖缺失路径
780 |         raise ProbeError(
    |

S105 Possible hardcoded password assigned to: "PASS"
  --> apps/worker/src/soniscope_worker/verify_upload_live.py:50:8
   |
48 | MISMATCH_EXPECTED_SIZE = 200
49 |
50 | PASS = "PASS"
   |        ^^^^^^
51 | FAIL = "FAIL"
52 | SKIP = "SKIP"
   |

SIM105 Use `contextlib.suppress(Exception)` instead of `try`-`except`-`pass`
   --> apps/worker/src/soniscope_worker/verify_upload_live.py:259:5
    |
257 |   def _try_delete(probes: VerifyLiveProbes, key: str) -> None:
258 |       """best-effort 清理测试对象（删除失败不影响断言结论）。"""
259 | /     try:
260 | |         probes.delete_object(key)
261 | |     except Exception:  # noqa: BLE001 - 清理失败忽略（不影响主断言）
262 | |         pass
    | |____________^
    |
help: Replace `try`-`except`-`pass` with `with contextlib.suppress(Exception): ...`

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> apps/worker/src/soniscope_worker/verify_upload_live.py:261:5
    |
259 |       try:
260 |           probes.delete_object(key)
261 | /     except Exception:  # noqa: BLE001 - 清理失败忽略（不影响主断言）
262 | |         pass
    | |____________^
    |

TRY300 Consider moving this statement to an `else` block
   --> scripts/fetch_test_fixtures.py:124:9
    |
122 |         import alibabacloud_oss_v2 as oss  # type: ignore
123 |
124 |         return oss
    |         ^^^^^^^^^^
125 |     except ImportError:
126 |         _fail(
    |

Found 69 errors.
No fixes available (2 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

## 三态销号表(03-02 填)

| # | 命中(path:line @ 5927f36) | 规则/模式 | 销号 | 理由/去向 |
|---|---------------------------|-----------|------|-----------|
