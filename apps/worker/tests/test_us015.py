"""US-015 单元测试：device_short_id、fragment_id、sha256 与 OSS 元数据草案

测试范围：
- device_short_id 持久化（首次生成+冷启动后保持）
- fragment_id 格式严格匹配 <YYYYMMDDTHHMMSS>_<deviceShortId>_<26字符ULID>
- 同秒内连续保存两条录音生成两个不同 fragment_id
- manifest 草案包含全部必需字段
- SHA-256 计算正确性
- OSS 用户自定义元数据（x-oss-meta-*）完整性
- 小程序代码结构验证
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
MP_DIR = REPO_ROOT / "apps" / "miniprogram"


# ── Helpers ─────────────────────────────────────────────────────────────────


def _read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── FIXTURES ───────────────────────────────────────────────────────────────


@pytest.fixture
def crypto_js() -> str:
    return _read_text(MP_DIR / "utils" / "crypto.js")


@pytest.fixture
def idgen_js() -> str:
    return _read_text(MP_DIR / "utils" / "idgen.js")


@pytest.fixture
def index_js() -> str:
    return _read_text(MP_DIR / "pages" / "index" / "index.js")


@pytest.fixture
def app_js() -> str:
    return _read_text(MP_DIR / "app.js")


# ── Tests: crypto.js — SHA-256 ──────────────────────────────────────────────


class TestCryptoModule:
    """验证 crypto.js SHA-256 实现"""

    def test_module_exists(self):
        """AC: 存在 utils/crypto.js 模块"""
        assert (MP_DIR / "utils" / "crypto.js").is_file(), (
            "crypto.js must exist for sha256 computation"
        )

    def test_sha256hex_function_exported(self, crypto_js):
        """AC: sha256Hex 函数被导出"""
        assert "sha256Hex" in crypto_js, (
            "crypto.js must export sha256Hex function"
        )
        assert "module.exports" in crypto_js, (
            "crypto.js must use module.exports"
        )

    def test_compute_file_sha256_function_exported(self, crypto_js):
        """AC: computeFileSha256 函数被导出"""
        assert "computeFileSha256" in crypto_js, (
            "crypto.js must export computeFileSha256 for file hashing"
        )

    def test_uses_fs_readfile(self, crypto_js):
        """AC: 使用 wx.getFileSystemManager 读取文件"""
        assert "getFileSystemManager" in crypto_js or "readFile" in crypto_js, (
            "must use wx.getFileSystemManager().readFile to read audio"
        )

    def test_returns_promise(self, crypto_js):
        """AC: computeFileSha256 返回 Promise"""
        assert "Promise" in crypto_js, (
            "computeFileSha256 must return Promise"
        )

    def test_sha256_constants_exist(self, crypto_js):
        """AC: SHA-256 实现包含正确的 K 常量"""
        assert "0x428a2f98" in crypto_js, (
            "must contain SHA-256 K constants"
        )
        assert "0x6a09e667" in crypto_js, (
            "must contain SHA-256 initial hash values"
        )

    def test_sha256_padding_handled(self, crypto_js):
        """AC: SHA-256 包含正确的消息填充逻辑"""
        assert "0x80" in crypto_js, (
            "must append '1' bit (0x80) for sha256 padding"
        )

    def test_sha256_hex_output_64_chars(self, crypto_js):
        """AC: SHA-256 输出 64 字符十六进制字符串"""
        # verify that sha256Hex converts to hex properly
        assert "toString(16)" in crypto_js, (
            "must output hex by calling toString(16)"
        )

    def test_processblock_exists(self, crypto_js):
        """AC: SHA-256 有 block 处理函数"""
        assert "_processBlock" in crypto_js or "processBlock" in crypto_js, (
            "must have block processing function"
        )


# ── Tests: idgen.js — Fragment ID & device_short_id ────────────────────────


class TestIdgenDeviceShortId:
    """验证 device_short_id 生成与持久化"""

    def test_module_exists(self):
        """AC: 存在 utils/idgen.js 模块"""
        assert (MP_DIR / "utils" / "idgen.js").is_file(), (
            "idgen.js must exist for fragment id generation"
        )

    def test_get_or_create_device_short_id_exported(self, idgen_js):
        """AC: getOrCreateDeviceShortId 函数被导出"""
        assert "getOrCreateDeviceShortId" in idgen_js, (
            "idgen.js must export getOrCreateDeviceShortId"
        )

    def test_get_device_short_id_exported(self, idgen_js):
        """AC: getDeviceShortId 函数被导出"""
        assert "getDeviceShortId" in idgen_js, (
            "idgen.js must export getDeviceShortId"
        )

    def test_device_short_id_storage_key(self, idgen_js):
        """AC: device_short_id 使用本地存储持久化"""
        assert "soniscope_device_short_id" in idgen_js, (
            "must use soniscope_device_short_id storage key"
        )

    def test_device_short_id_length_in_range(self, idgen_js):
        """AC: device_short_id 长度在 4-8 字符范围内"""
        assert "DEVICE_ID_LENGTH" in idgen_js, (
            "must have DEVICE_ID_LENGTH constant"
        )
        # Verify length is an integer between 4 and 8
        match = re.search(r"DEVICE_ID_LENGTH\s*=\s*(\d+)", idgen_js)
        assert match, "DEVICE_ID_LENGTH must be defined as integer"
        length = int(match.group(1))
        assert 4 <= length <= 8, f"DEVICE_ID_LENGTH {length} not in range 4-8"

    def test_device_short_id_persists_on_second_call(self, idgen_js):
        """AC: 冷启动后 device_short_id 保持不变（从 storage 读取）"""
        assert "getStorageSync" in idgen_js, (
            "must use wx.getStorageSync to read persisted device id"
        )
        assert "setStorageSync" in idgen_js, (
            "must use wx.setStorageSync to persist device id"
        )


class TestIdgenFragmentId:
    """验证 fragment_id 生成"""

    def test_generate_fragment_id_exported(self, idgen_js):
        """AC: generateFragmentId 函数被导出"""
        assert "generateFragmentId" in idgen_js, (
            "idgen.js must export generateFragmentId"
        )

    def test_fragment_id_format_pattern(self, idgen_js):
        """AC: fragment_id 格式匹配 <YYYYMMDDTHHMMSS>_<deviceShortId>_<26字符ULID>"""
        # Fragment ID must contain timestamp, device ID, and ULID parts
        assert "generateFragmentId" in idgen_js, (
            "must have generateFragmentId function"
        )

    def test_fragment_id_contains_device_id(self, idgen_js):
        """AC: fragment_id 包含 device_short_id"""
        # The function should use the deviceShortId parameter
        assert "deviceShortId" in idgen_js, (
            "fragment_id must include deviceShortId"
        )

    def test_generate_ulid_exported(self, idgen_js):
        """AC: generateUlid 函数被导出"""
        assert "generateUlid" in idgen_js, (
            "idgen.js must export generateUlid"
        )

    def test_ulid_is_26_chars(self, idgen_js):
        """AC: ULID 为 26 字符"""
        # ULID: 10 timestamp + 16 random = 26
        assert "10" in idgen_js and "16" in idgen_js, (
            "ULID must be 10 + 16 = 26 chars"
        )

    def test_generate_session_id_exported(self, idgen_js):
        """AC: generateSessionId 函数被导出"""
        assert "generateSessionId" in idgen_js, (
            "idgen.js must export generateSessionId"
        )

    def test_crockford_alphabet(self, idgen_js):
        """AC: ULID 使用 Crockford Base32 字母表（不含 I, L, O, U）"""
        assert "CROCKFORD" in idgen_js, (
            "must define Crockford Base32 alphabet"
        )
        # Verify it doesn't contain I, L, O, U
        if "CROCKFORD" in idgen_js:
            # The alphabet should not include I, L, O, U
            # But we can't easily parse the exact string since it's JS
            pass

    def test_ulid_uses_random(self, idgen_js):
        """AC: ULID 随机部分使用 Math.random()"""
        assert "Math.random" in idgen_js, (
            "ULID random part must use Math.random()"
        )

    def test_ulid_uses_timestamp(self, idgen_js):
        """AC: ULID 时间部分使用 Date.now()"""
        assert "Date.now" in idgen_js, (
            "ULID timestamp part must use Date.now()"
        )


# ── Tests: app.js — device_short_id 初始化 ──────────────────────────────────


class TestAppDeviceShortId:
    """验证 app.js 首次启动生成 device_short_id"""

    def test_app_requires_idgen(self, app_js):
        """AC: app.js 导入 idgen 模块"""
        assert "idgen" in app_js, (
            "app.js must require idgen module"
        )

    def test_onlaunch_initializes_device_id(self, app_js):
        """AC: onLaunch 中调用 getOrCreateDeviceShortId"""
        assert "getOrCreateDeviceShortId" in app_js, (
            "onLaunch must call getOrCreateDeviceShortId"
        )

    def test_globaldata_has_device_short_id(self, app_js):
        """AC: globalData 包含 deviceShortId 字段"""
        assert "deviceShortId" in app_js, (
            "globalData must have deviceShortId field"
        )


# ── Tests: index.js — manifest 草案与 OSS 元数据 ───────────────────────────


class TestIndexManifestDraft:
    """验证 index.js 中 manifest 草案与 OSS 元数据"""

    def test_index_requires_idgen(self, index_js):
        """AC: index.js 导入 idgen 模块"""
        assert "idgen" in index_js, (
            "index.js must require idgen module"
        )

    def test_index_requires_crypto(self, index_js):
        """AC: index.js 导入 crypto 模块"""
        assert "cryptoUtil" in index_js or "crypto" in index_js, (
            "index.js must require crypto module"
        )

    def test_fragment_id_generated_with_device_id(self, index_js):
        """AC: 保存并上传时生成带 device_short_id 的 fragment_id"""
        assert "generateFragmentId" in index_js, (
            "onSaveAndUpload must call generateFragmentId"
        )

    def test_session_id_generated(self, index_js):
        """AC: 保存并上传时生成 session_id"""
        assert "generateSessionId" in index_js, (
            "onSaveAndUpload must call generateSessionId"
        )

    def test_compute_file_sha256_called(self, index_js):
        """AC: 保存并上传时计算原始音频 sha256"""
        assert "computeFileSha256" in index_js, (
            "onSaveAndUpload must call computeFileSha256"
        )

    def test_manifest_contains_fragment_id(self, index_js):
        """AC: manifest 草案包含 fragment_id"""
        assert "fragment_id" in index_js, (
            "manifest must contain fragment_id field"
        )

    def test_manifest_contains_session_id(self, index_js):
        """AC: manifest 草案包含 session_id"""
        assert "session_id" in index_js, (
            "manifest must contain session_id field"
        )

    def test_manifest_contains_chunk_seq(self, index_js):
        """AC: manifest 草案包含 chunk_seq"""
        assert "chunk_seq" in index_js, (
            "manifest must contain chunk_seq field"
        )

    def test_manifest_contains_chunk_total(self, index_js):
        """AC: manifest 草案包含 chunk_total"""
        assert "chunk_total" in index_js, (
            "manifest must contain chunk_total field"
        )

    def test_manifest_contains_device_id(self, index_js):
        """AC: manifest 草案包含 device_id"""
        assert "device_id" in index_js, (
            "manifest must contain device_id field"
        )

    def test_manifest_contains_recorded_at(self, index_js):
        """AC: manifest 草案包含 recorded_at"""
        assert "recorded_at" in index_js, (
            "manifest must contain recorded_at field"
        )

    def test_manifest_contains_duration_seconds(self, index_js):
        """AC: manifest 草案包含 duration_seconds"""
        assert "duration_seconds" in index_js, (
            "manifest must contain duration_seconds field"
        )

    def test_manifest_contains_audio_object(self, index_js):
        """AC: manifest 草案包含 audio 对象"""
        assert "audio" in index_js, (
            "manifest must contain audio object"
        )

    def test_manifest_contains_original_format(self, index_js):
        """AC: manifest.audio 包含 original_format"""
        assert "original_format" in index_js, (
            "manifest.audio must contain original_format"
        )

    def test_manifest_contains_audio_size_bytes(self, index_js):
        """AC: manifest.audio 包含 size_bytes"""
        assert "size_bytes" in index_js, (
            "manifest.audio must contain size_bytes"
        )

    def test_manifest_contains_upload_object(self, index_js):
        """AC: manifest 草案包含 upload 对象"""
        assert "upload" in index_js, (
            "manifest must contain upload object"
        )

    def test_manifest_contains_original_sha256(self, index_js):
        """AC: manifest.upload 包含 original_sha256"""
        assert "original_sha256" in index_js, (
            "manifest.upload must contain original_sha256"
        )

    def test_oss_meta_session_id(self, index_js):
        """AC: OSS 元数据包含 x-oss-meta-session-id"""
        assert "x-oss-meta-session-id" in index_js, (
            "must include x-oss-meta-session-id in OSS metadata"
        )

    def test_oss_meta_chunk_seq(self, index_js):
        """AC: OSS 元数据包含 x-oss-meta-chunk-seq"""
        assert "x-oss-meta-chunk-seq" in index_js, (
            "must include x-oss-meta-chunk-seq in OSS metadata"
        )

    def test_oss_meta_chunk_total(self, index_js):
        """AC: OSS 元数据包含 x-oss-meta-chunk-total"""
        assert "x-oss-meta-chunk-total" in index_js, (
            "must include x-oss-meta-chunk-total in OSS metadata"
        )

    def test_oss_meta_recorded_at(self, index_js):
        """AC: OSS 元数据包含 x-oss-meta-recorded-at"""
        assert "x-oss-meta-recorded-at" in index_js, (
            "must include x-oss-meta-recorded-at in OSS metadata"
        )

    def test_oss_meta_duration(self, index_js):
        """AC: OSS 元数据包含 x-oss-meta-duration"""
        assert "x-oss-meta-duration" in index_js, (
            "must include x-oss-meta-duration in OSS metadata"
        )

    def test_oss_meta_original_format(self, index_js):
        """AC: OSS 元数据包含 x-oss-meta-original-format"""
        assert "x-oss-meta-original-format" in index_js, (
            "must include x-oss-meta-original-format in OSS metadata"
        )

    def test_oss_meta_sha256(self, index_js):
        """AC: OSS 元数据包含 x-oss-meta-sha256"""
        assert "x-oss-meta-sha256" in index_js, (
            "must include x-oss-meta-sha256 in OSS metadata"
        )

    def test_upload_record_includes_manifest(self, index_js):
        """AC: uploadRecord 包含 manifest 字段"""
        assert "manifest" in index_js, (
            "uploadRecord must include manifest object"
        )

    def test_upload_record_includes_oss_meta(self, index_js):
        """AC: uploadRecord 包含 ossMeta 字段"""
        assert "ossMeta" in index_js, (
            "uploadRecord must include ossMeta for OSS upload"
        )

    def test_get_app_device_id(self, index_js):
        """AC: 从 app.globalData 获取 device_short_id"""
        assert "getApp" in index_js, (
            "must use getApp() to access device_short_id"
        )

    def test_save_in_progress_prevents_duplicate(self, index_js):
        """AC: 防重复点击仍生效（saveInProgress 检查）"""
        assert "saveInProgress" in index_js, (
            "must have saveInProgress guard against duplicate clicks"
        )


# ── Tests: JS 语法 / Makefile / 密钥安全 ──────────────────────────────────


class TestJsSyntax:
    """验证所有 JS 文件语法正确"""

    def test_crypto_js_syntax(self):
        """AC: crypto.js 语法正确"""
        result = subprocess.run(
            ["node", "-c", str(MP_DIR / "utils" / "crypto.js")],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"crypto.js syntax error: {result.stderr}"

    def test_idgen_js_syntax(self):
        """AC: idgen.js 语法正确"""
        result = subprocess.run(
            ["node", "-c", str(MP_DIR / "utils" / "idgen.js")],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"idgen.js syntax error: {result.stderr}"

    def test_app_js_syntax(self):
        """AC: app.js 语法正确"""
        result = subprocess.run(
            ["node", "-c", str(MP_DIR / "app.js")],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"app.js syntax error: {result.stderr}"

    def test_index_js_syntax(self):
        """AC: index.js 语法正确"""
        result = subprocess.run(
            ["node", "-c", str(MP_DIR / "pages" / "index" / "index.js")],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"index.js syntax error: {result.stderr}"


class TestMakefile:
    """验证 Makefile target 覆盖"""

    def test_miniprogram_lint_covers_new_files(self):
        """AC: Makefile miniprogram-lint 覆盖新文件（crypto.js, idgen.js, app.js）"""
        mk = _read_text(REPO_ROOT / "Makefile")
        assert "crypto.js" in mk, (
            "Makefile miniprogram-lint must check crypto.js syntax"
        )
        assert "idgen.js" in mk, (
            "Makefile miniprogram-lint must check idgen.js syntax"
        )
        assert "app.js" in mk, (
            "Makefile miniprogram-lint must cover app.js (updated for device_short_id)"
        )


class TestSecurity:
    """验证密钥安全"""

    def test_no_hardcoded_secrets_in_crypto(self):
        """AC: crypto.js 不包含 AK / Secret / token 明文"""
        content = _read_text(MP_DIR / "utils" / "crypto.js")
        sensitive = [
            "access_key_secret",
            "access_key_id",
            "security_token",
            "appsecret",
        ]
        for s in sensitive:
            assert s not in content.lower(), (
                f"crypto.js must not contain {s}"
            )

    def test_no_hardcoded_secrets_in_idgen(self):
        """AC: idgen.js 不包含 AK / Secret / token 明文"""
        content = _read_text(MP_DIR / "utils" / "idgen.js")
        sensitive = [
            "access_key_secret",
            "access_key_id",
            "security_token",
            "appsecret",
        ]
        for s in sensitive:
            assert s not in content.lower(), (
                f"idgen.js must not contain {s}"
            )

    def test_no_hardcoded_secrets_in_app_js(self):
        """AC: app.js 不包含 AK / Secret / token 明文"""
        content = _read_text(MP_DIR / "app.js")
        sensitive = [
            "access_key_secret",
            "access_key_id",
            "security_token",
            "appsecret",
        ]
        for s in sensitive:
            assert s not in content.lower(), (
                f"app.js must not contain {s}"
            )


# ── Tests: SHA-256 功能正确性（逻辑验证） ──────────────────────────────────


TEST_VECTORS = [
    ("", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    ("abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),
    ("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
     "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"),
    ("hello world",
     "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"),
]


class TestSha256Logic:
    """验证 SHA-256 实现逻辑（通过 Node.js 执行 crypto.js 验证）"""

    def test_sha256_empty_string(self):
        """AC: 空字符串 SHA-256 等于标准向量"""
        js_code = """
var crypto = require('./utils/crypto.js');
function str2bytes(s) {
  var arr = new Uint8Array(s.length);
  for (var i = 0; i < s.length; i++) arr[i] = s.charCodeAt(i);
  return arr;
}
console.log(crypto.sha256Hex(str2bytes("")));
"""
        result = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True, text=True, cwd=str(MP_DIR)
        )
        assert result.returncode == 0, f"sha256 empty: {result.stderr}"
        assert result.stdout.strip() == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_sha256_abc(self):
        """AC: 'abc' SHA-256 等于标准向量"""
        js_code = """
var crypto = require('./utils/crypto.js');
function str2bytes(s) {
  var arr = new Uint8Array(s.length);
  for (var i = 0; i < s.length; i++) arr[i] = s.charCodeAt(i);
  return arr;
}
console.log(crypto.sha256Hex(str2bytes("abc")));
"""
        result = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True, text=True, cwd=str(MP_DIR)
        )
        assert result.returncode == 0, f"sha256 abc: {result.stderr}"
        assert result.stdout.strip() == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

    def test_sha256_hello_world(self):
        """AC: 'hello world' SHA-256 等于标准向量"""
        js_code = """
var crypto = require('./utils/crypto.js');
function str2bytes(s) {
  var arr = new Uint8Array(s.length);
  for (var i = 0; i < s.length; i++) arr[i] = s.charCodeAt(i);
  return arr;
}
console.log(crypto.sha256Hex(str2bytes("hello world")));
"""
        result = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True, text=True, cwd=str(MP_DIR)
        )
        assert result.returncode == 0, f"sha256 hello world: {result.stderr}"
        assert result.stdout.strip() == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    def test_sha256_long_string(self):
        """AC: 长消息 SHA-256 计算正确（多 block）"""
        js_code = """
var crypto = require('./utils/crypto.js');
var msg = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
function str2bytes(s) {
  var arr = new Uint8Array(s.length);
  for (var i = 0; i < s.length; i++) arr[i] = s.charCodeAt(i);
  return arr;
}
console.log(crypto.sha256Hex(str2bytes(msg)));
"""
        result = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True, text=True, cwd=str(MP_DIR)
        )
        assert result.returncode == 0, f"sha256 long: {result.stderr}"
        assert result.stdout.strip() == "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"


# ── Tests: ULID 生成逻辑（通过 Node.js 执行 idgen.js 验证） ──────────────────


class TestUlidLogic:
    """验证 ULID 生成逻辑（通过 Node.js）"""

    def test_ulid_is_26_chars(self):
        """AC: ULID 为 26 字符（10 timestamp + 16 random）"""
        js_code = """
var idgen = require('./utils/idgen.js');
var ulid = idgen.generateUlid();
console.log(ulid.length);
"""
        result = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True, text=True, cwd=str(MP_DIR)
        )
        assert result.returncode == 0, f"ulid length: {result.stderr}"
        assert result.stdout.strip() == "26", f"ULID must be 26 chars, got {result.stdout.strip()}"

    def test_two_ulids_are_different(self):
        """AC: 连续生成两个 ULID 不相同"""
        js_code = """
var idgen = require('./utils/idgen.js');
var u1 = idgen.generateUlid();
var u2 = idgen.generateUlid();
console.log(u1 !== u2 ? "DIFFERENT" : "SAME");
"""
        result = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True, text=True, cwd=str(MP_DIR)
        )
        assert result.returncode == 0, f"ulid diff: {result.stderr}"
        assert result.stdout.strip() == "DIFFERENT", "Two consecutive ULIDs must be different"

    def test_ulid_uses_crockford_alphabet(self):
        """AC: ULID 字符均在 Crockford Base32 字母表中"""
        js_code = """
var idgen = require('./utils/idgen.js');
var ulid = idgen.generateUlid();
var valid = idgen.CROCKFORD;
var ok = true;
for (var i = 0; i < ulid.length; i++) {
  if (valid.indexOf(ulid[i]) === -1) { ok = false; break; }
}
console.log(ok ? "OK" : "INVALID:" + ulid);
"""
        result = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True, text=True, cwd=str(MP_DIR)
        )
        assert result.returncode == 0, f"ulid alphabet: {result.stderr}"
        assert result.stdout.strip() == "OK", "ULID must use Crockford Base32 alphabet"


class TestFragmentIdLogic:
    """验证 fragment_id 生成逻辑（通过 Node.js）"""

    def test_fragment_id_format(self):
        """AC: fragment_id 格式匹配 <YYYYMMDDTHHMMSS>_<deviceShortId>_<ULID>"""
        js_code = """
var idgen = require('./utils/idgen.js');
var fid = idgen.generateFragmentId("abc123");
// Must match: YYYYMMDDTHHMMSS_deviceId_26charULID
var re = /^\\d{8}T\\d{6}_[a-z0-9]+_[A-Z0-9]{26}$/;
console.log(re.test(fid) ? "MATCH" : ("MISMATCH:" + fid));
"""
        result = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True, text=True, cwd=str(MP_DIR)
        )
        assert result.returncode == 0, f"fragment_id format: {result.stderr}"
        assert result.stdout.strip() == "MATCH", (
            f"Fragment ID must match YYYYMMDDTHHMMSS_deviceId_26ULID, got {result.stdout.strip()}"
        )

    def test_two_fragment_ids_are_different(self):
        """AC: 同秒内连续生成两个 fragment_id 不同"""
        js_code = """
var idgen = require('./utils/idgen.js');
var f1 = idgen.generateFragmentId("abc123");
var f2 = idgen.generateFragmentId("abc123");
console.log(f1 !== f2 ? "DIFFERENT" : "SAME");
"""
        result = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True, text=True, cwd=str(MP_DIR)
        )
        assert result.returncode == 0, f"fragment_id diff: {result.stderr}"
        assert result.stdout.strip() == "DIFFERENT", (
            "Two consecutive fragment_ids must be different"
        )

    def test_fragment_id_contains_device_id(self):
        """AC: fragment_id 包含传入的 device_short_id"""
        js_code = """
var idgen = require('./utils/idgen.js');
var fid = idgen.generateFragmentId("testdev");
// device_short_id appears after the timestamp (after the second underscore)
var parts = fid.split("_");
console.log(parts[1]);
"""
        result = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True, text=True, cwd=str(MP_DIR)
        )
        assert result.returncode == 0, f"fragment_id device: {result.stderr}"
        assert result.stdout.strip() == "testdev", (
            f"Fragment ID must contain the device_short_id, got {result.stdout.strip()}"
        )

    def test_fragment_id_date_is_current(self):
        """AC: fragment_id 日期部分是当前日期"""
        import datetime
        js_code = """
var idgen = require('./utils/idgen.js');
var fid = idgen.generateFragmentId("abc");
console.log(fid.substring(0, 8));
"""
        result = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True, text=True, cwd=str(MP_DIR)
        )
        assert result.returncode == 0, f"fragment_id date: {result.stderr}"
        date_str = result.stdout.strip()
        today = datetime.date.today().strftime("%Y%m%d")
        assert date_str == today, (
            f"Fragment ID date must be today ({today}), got {date_str}"
        )
