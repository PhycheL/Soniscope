"""Worker 启动恢复扫描与统一原子写入工具（US-023，tech-spec §3.5 / §3.6）。

Worker 每次启动时按 §3.6 分三段扫描运行时目录，清理中间态残留，避免半成品文件：

1. **inbox/**（下载/转码中断）：删除 ``<id>.part``（下次重下）与 ``<id>.wav.tmp``
   （转码中断，下次重下重转码）。
2. **tmp/**（转写中断）：删除 ``<id>.transcript.json.tmp``，对应 fragment 将在第三段
   被识别为「转写未完」。
3. **fragments/**：有 ``.done`` 跳过；无 ``.done`` 但有 ``audio.wav`` → 转写未完
   （待重新转写）；无 ``audio.wav`` 的空目录可安全忽略/删除。

并提供统一**原子写入协议**工具（§3.5「先临时文件 → 同文件系统原子 rename → 最后写
``.done``」）：``manifest.json`` / ``transcript.json`` / ``transcript.txt`` 均先写临时文件再
原子 ``os.replace``；``.done`` 最后创建且为 0 字节空文件。其中 ``transcript.json`` 的临时文件
刻意写在 ``tmp/<id>.transcript.json.tmp``，使转写中断时第二段扫描能据此清理。

沿用既有「纯逻辑（无 IO，可直接单测）+ IO 用可注入 callable」分层：``finalize_fragment``
默认不依赖任何具体转写器，调用方（make test / US-027 完整流水线）注入转写结果，
单测全程不触系统工具与云端。
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from soniscope_worker.oss_admin import OssAdminError, object_key_for
from soniscope_worker.paths import fragments_dir, inbox_dir, tmp_dir

AUDIO_FILENAME = "audio.wav"
MANIFEST_FILENAME = "manifest.json"
TRANSCRIPT_JSON_FILENAME = "transcript.json"
TRANSCRIPT_TXT_FILENAME = "transcript.txt"
DONE_MARKER = ".done"

PART_SUFFIX = ".part"
WAV_TMP_SUFFIX = ".wav.tmp"
TRANSCRIPT_TMP_SUFFIX = ".transcript.json.tmp"


# ── 统一原子写入工具（§3.5 三段式协议）────────────────────────────────────
def atomic_write_text(dest: Path, text: str) -> None:
    """原子写文本：先写同目录临时文件，再 ``os.replace`` 到 ``dest``（同文件系统）。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f"{dest.name}.", suffix=".tmp", dir=str(dest.parent)
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def atomic_write_json(dest: Path, obj: Any) -> None:
    """原子写 JSON（``manifest.json`` 等），UTF-8、缩进 2、保留中文。"""
    atomic_write_text(dest, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def transcript_tmp_path(tmp_root: Path, fragment_id: str) -> Path:
    """转写中间态文件 ``tmp/<fragment_id>.transcript.json.tmp``（中断恢复信号）。"""
    return tmp_root / f"{fragment_id}{TRANSCRIPT_TMP_SUFFIX}"


def write_transcript_json(
    fragment_dir: Path, fragment_id: str, obj: Any, *, tmp_root: Path
) -> Path:
    """原子写 ``transcript.json``：先写 ``tmp/<id>.transcript.json.tmp`` 再 rename。

    临时文件刻意放 ``tmp/``（与 ``fragments/`` 同文件系统），使转写中断时残留的
    ``.transcript.json.tmp`` 能被启动恢复扫描第二段清理（§3.5/§3.6）。
    """
    tmp_root.mkdir(parents=True, exist_ok=True)
    fragment_dir.mkdir(parents=True, exist_ok=True)
    tmp = transcript_tmp_path(tmp_root, fragment_id)
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dest = fragment_dir / TRANSCRIPT_JSON_FILENAME
    os.replace(tmp, dest)
    return dest


def transcript_txt_from_segments(segments: Sequence[Any]) -> str:
    """从 ``transcript.json`` 的 ``segments[].text`` 按顺序拼接派生 ``transcript.txt``。"""
    parts: list[str] = []
    for seg in segments:
        text = ""
        if isinstance(seg, dict):
            text = str(seg.get("text", "") or "")
        parts.append(text)
    return "".join(parts)


def create_done_marker(fragment_dir: Path) -> Path:
    """最后一步创建 ``.done`` 完成标记，**0 字节空文件**（§3.5）。"""
    fragment_dir.mkdir(parents=True, exist_ok=True)
    done = fragment_dir / DONE_MARKER
    with open(done, "wb"):
        pass  # 0 字节
    return done


# ── 转写落盘收尾（transcript.json → transcript.txt → .done）────────────────
@dataclass(frozen=True)
class FinalizeResult:
    """转写收尾产物路径。"""

    fragment_id: str
    transcript_json: Path
    transcript_txt: Path
    done_marker: Path


def finalize_fragment(
    fragment_dir: Path,
    fragment_id: str,
    transcript: dict[str, Any],
    *,
    tmp_root: Path,
    log: Callable[[str], None] = lambda _msg: None,
) -> FinalizeResult:
    """把转写结果按三段式协议原子落盘并最后创建 ``.done``（US-023 收尾工具）。

    顺序严格为：① 原子写 ``transcript.json``（经 ``tmp/<id>.transcript.json.tmp``）；
    ② 原子写 ``transcript.txt``（由 segments 派生）；③ 最后创建 0 字节 ``.done``。
    任一步失败都不会创建 ``.done``，故崩溃/中断永不产生半成品完成态。

    转写内容由调用方提供（make test 注入 stub、US-027 注入真实 Transcriber 结果），
    本函数不依赖任何具体转写器实现。
    """
    tj = write_transcript_json(fragment_dir, fragment_id, transcript, tmp_root=tmp_root)
    segments = transcript.get("segments", [])
    txt = transcript_txt_from_segments(segments if isinstance(segments, list) else [])
    tt = fragment_dir / TRANSCRIPT_TXT_FILENAME
    atomic_write_text(tt, txt)
    done = create_done_marker(fragment_dir)  # 最后创建
    log(f"[recover] {fragment_id} 转写落盘完成：transcript.json/txt + .done")
    return FinalizeResult(
        fragment_id=fragment_id, transcript_json=tj, transcript_txt=tt, done_marker=done
    )


# ── 启动恢复扫描（§3.6 三段）────────────────────────────────────────────────
@dataclass(frozen=True)
class FragmentState:
    """fragments/ 扫描中单个 fragment 目录的判定。"""

    fragment_id: str
    date: str
    path: Path
    status: str  # done / pending / empty


@dataclass(frozen=True)
class RecoveryReport:
    """一次启动恢复扫描的结果汇总。"""

    removed_parts: list[str] = field(default_factory=list)
    removed_wav_tmps: list[str] = field(default_factory=list)
    removed_transcript_tmps: list[str] = field(default_factory=list)
    done: list[FragmentState] = field(default_factory=list)
    pending: list[FragmentState] = field(default_factory=list)
    empty: list[FragmentState] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"清理 .part {len(self.removed_parts)}、.wav.tmp {len(self.removed_wav_tmps)}、"
            f".transcript.json.tmp {len(self.removed_transcript_tmps)}；"
            f"fragments 已完成 {len(self.done)}、转写未完 {len(self.pending)}、"
            f"空目录 {len(self.empty)}"
        )


def _remove_by_suffix(root: Path, suffix: str) -> list[str]:
    """删除 ``root`` 下所有以 ``suffix`` 结尾的文件，返回被删文件名（排序稳定）。"""
    if not root.exists():
        return []
    removed: list[str] = []
    for p in sorted(root.iterdir()):
        if p.is_file() and p.name.endswith(suffix):
            try:
                p.unlink()
                removed.append(p.name)
            except OSError:  # pragma: no cover - 并发删除等罕见情况
                continue
    return removed


def recover_inbox(inbox_root: Path) -> tuple[list[str], list[str]]:
    """第一段：清理 inbox 残留 ``*.part`` 与 ``*.wav.tmp``（下次重下/重转码，§3.6）。

    返回 ``(removed_parts, removed_wav_tmps)``。注意先清 ``.wav.tmp`` 再清 ``.part``：
    ``.wav.tmp`` 以 ``.part`` 之外的后缀结尾，两者互不重叠，顺序无副作用。
    """
    wav_tmps = _remove_by_suffix(inbox_root, WAV_TMP_SUFFIX)
    parts = _remove_by_suffix(inbox_root, PART_SUFFIX)
    return parts, wav_tmps


def recover_tmp(tmp_root: Path) -> list[str]:
    """第二段：清理 tmp 残留 ``*.transcript.json.tmp``（转写中断，§3.6）。"""
    return _remove_by_suffix(tmp_root, TRANSCRIPT_TMP_SUFFIX)


def classify_fragment_dir(date: str, frag_dir: Path) -> FragmentState | None:
    """判定单个 ``fragments/<date>/<id>/`` 目录状态（§3.6 第三段，纯逻辑）。

    - 有 ``.done`` → ``done``（跳过）；
    - 无 ``.done`` 但有 ``audio.wav`` → ``pending``（转写未完，待重转写）；
    - 无 ``audio.wav`` → ``empty``（空目录，可安全忽略/删除）。

    目录名不是合法 fragment_id 时返回 ``None``（忽略，不纳入恢复）。
    """
    fragment_id = frag_dir.name
    try:
        if object_key_for(fragment_id).split("/")[1] != date:
            return None
    except OssAdminError:
        return None
    if (frag_dir / DONE_MARKER).exists():
        status = "done"
    elif (frag_dir / AUDIO_FILENAME).is_file():
        status = "pending"
    else:
        status = "empty"
    return FragmentState(fragment_id=fragment_id, date=date, path=frag_dir, status=status)


def scan_fragments(fragments_root: Path) -> list[FragmentState]:
    """第三段：遍历 ``fragments/<date>/<id>/`` 并判定每个目录状态（§3.6）。"""
    states: list[FragmentState] = []
    if not fragments_root.exists():
        return states
    for date_dir in sorted(fragments_root.iterdir()):
        if not date_dir.is_dir():
            continue
        for frag_dir in sorted(date_dir.iterdir()):
            if not frag_dir.is_dir():
                continue
            state = classify_fragment_dir(date_dir.name, frag_dir)
            if state is not None:
                states.append(state)
    return states


def recover(
    *,
    inbox_root: Path,
    tmp_root: Path,
    fragments_root: Path,
    remove_empty_dirs: bool = False,
    log: Callable[[str], None] = lambda _msg: None,
) -> RecoveryReport:
    """执行启动三段恢复扫描（§3.6），返回汇总报告。

    清理 inbox/tmp 中间态残留并对 fragments 分类。``remove_empty_dirs=True`` 时删除
    确认为空（无 ``audio.wav``）的 fragment 目录；默认只忽略（等下次 OSS 轮询下载）。
    """
    parts, wav_tmps = recover_inbox(inbox_root)
    transcript_tmps = recover_tmp(tmp_root)
    states = scan_fragments(fragments_root)
    done = [s for s in states if s.status == "done"]
    pending = [s for s in states if s.status == "pending"]
    empty = [s for s in states if s.status == "empty"]

    if remove_empty_dirs:
        for s in empty:
            try:
                s.path.rmdir()
            except OSError:  # pragma: no cover - 目录非空等罕见情况
                continue

    report = RecoveryReport(
        removed_parts=parts,
        removed_wav_tmps=wav_tmps,
        removed_transcript_tmps=transcript_tmps,
        done=done,
        pending=pending,
        empty=empty,
    )
    if parts:
        log(f"[recover] 清理 inbox 残留 .part：{', '.join(parts)}")
    if wav_tmps:
        log(f"[recover] 清理 inbox 残留 .wav.tmp：{', '.join(wav_tmps)}")
    if transcript_tmps:
        log(f"[recover] 清理 tmp 残留 .transcript.json.tmp：{', '.join(transcript_tmps)}")
    log(f"[recover] {report.summary()}")
    return report


def recover_runtime(
    log: Callable[[str], None] = print, *, remove_empty_dirs: bool = False
) -> RecoveryReport:
    """对真实 ``$SONISCOPE_HOME`` 运行时目录执行启动恢复扫描（Worker 启动调用）。"""
    return recover(
        inbox_root=inbox_dir(),
        tmp_root=tmp_dir(),
        fragments_root=fragments_dir(),
        remove_empty_dirs=remove_empty_dirs,
        log=log,
    )


# ── make test-crash-recovery：自包含验证恢复 + 重新转写补齐 ──────────────────
_CRASH_FID = "20260527T130000_devc01_01HZX3K8MN5PQR9TFB7AYWVCDE"


def _stub_transcript(fragment_id: str) -> dict[str, Any]:
    """make test 用的确定性占位转写结果（真实 NLS 转写器在 US-026）。"""
    return {
        "segments": [
            {"start": 0.0, "end": 1.0, "text": "恢复"},
            {"start": 1.0, "end": 2.0, "text": "重转写"},
        ],
        "language": "zh",
        "model": "stub",
        "params_version": "test",
        "provider": "stub",
    }


def run_test_crash_recovery() -> tuple[list[str], int]:
    """make test-crash-recovery：自包含模拟「转写中 kill -9」后重启恢复（AC#7）。

    在临时运行时目录里构造：一个 ``audio.wav`` 已就绪但 ``transcript.json`` / ``.done`` 缺失
    的 fragment（转写中断），外加 inbox 残留 ``.part`` / ``.wav.tmp`` 与 tmp 残留
    ``.transcript.json.tmp``。执行 :func:`recover` 后断言中间态被清理、该 fragment 被判为
    ``pending``，再用 :func:`finalize_fragment` 重新转写补齐 ``transcript.json`` 与 ``.done``。
    不触云端、不触系统工具（转写结果为确定性 stub，真实 NLS 在 US-026）。
    """
    lines: list[str] = []
    fid = _CRASH_FID
    try:
        date = object_key_for(fid).split("/")[1]
    except OssAdminError as exc:  # pragma: no cover - 固定常量合法
        lines.append(f"FAIL — 内部 fragment_id 非法：{exc}")
        return lines, 1

    with tempfile.TemporaryDirectory(prefix="soniscope-crash-recovery-") as tmpdir:
        base = Path(tmpdir)
        inbox = base / "inbox"
        tmp = base / "tmp"
        fragments = base / "fragments"
        frag_dir = fragments / date / fid
        for d in (inbox, tmp, frag_dir):
            d.mkdir(parents=True, exist_ok=True)

        # 转写中断现场：audio.wav + manifest.json 就绪，但无 transcript.json / .done。
        (frag_dir / AUDIO_FILENAME).write_bytes(b"RIFF....WAVEfake-audio")
        atomic_write_json(frag_dir / MANIFEST_FILENAME, {"fragment_id": fid})
        # 中间态残留（崩溃留下）。
        (inbox / f"{fid}{PART_SUFFIX}").write_bytes(b"partial-download")
        (inbox / f"{fid}{WAV_TMP_SUFFIX}").write_bytes(b"partial-transcode")
        transcript_tmp_path(tmp, fid).write_text("{partial", encoding="utf-8")

        report = recover(
            inbox_root=inbox, tmp_root=tmp, fragments_root=fragments, log=lines.append
        )

        problems: list[str] = []
        if (inbox / f"{fid}{PART_SUFFIX}").exists():
            problems.append(".part 残留未被清理")
        if (inbox / f"{fid}{WAV_TMP_SUFFIX}").exists():
            problems.append(".wav.tmp 残留未被清理")
        if transcript_tmp_path(tmp, fid).exists():
            problems.append(".transcript.json.tmp 残留未被清理")
        pending_ids = [s.fragment_id for s in report.pending]
        if fid not in pending_ids:
            problems.append(f"该 fragment 未被识别为转写未完（pending={pending_ids}）")

        if not problems:
            # 重启后重新转写补齐 transcript.json + .done（AC#7）。
            finalize_fragment(frag_dir, fid, _stub_transcript(fid), tmp_root=tmp, log=lines.append)
            if not (frag_dir / TRANSCRIPT_JSON_FILENAME).is_file():
                problems.append("重转写后 transcript.json 仍缺失")
            if not (frag_dir / TRANSCRIPT_TXT_FILENAME).is_file():
                problems.append("重转写后 transcript.txt 仍缺失")
            done = frag_dir / DONE_MARKER
            if not done.is_file():
                problems.append("重转写后 .done 仍缺失")
            elif done.stat().st_size != 0:
                problems.append(".done 不是 0 字节空文件")
            if transcript_tmp_path(tmp, fid).exists():
                problems.append("transcript.json 落盘后 .transcript.json.tmp 临时文件未清理")

        if problems:
            lines.extend(f"FAIL — {p}" for p in problems)
            return lines, 1

    lines.append("✅ 崩溃恢复校验通过（清理 tmp 残留 + 重新转写补齐 transcript.json 与 .done）")
    return lines, 0


# ── make simulate-worker-crash：注入崩溃场景（操作真实 $SONISCOPE_HOME）──────
CASE_MISSING_DONE = "missing-done"
CASE_STALE_PART = "stale-part"
SIMULATE_CASES = (CASE_MISSING_DONE, CASE_STALE_PART)


def run_simulate_worker_crash(
    case: str,
    fragment_id: str,
    *,
    inbox_root: Path | None = None,
    fragments_root: Path | None = None,
) -> tuple[list[str], int]:
    """make simulate-worker-crash：注入崩溃场景，重启 Worker 后由恢复扫描修复。

    - ``CASE=missing-done``：删除该 fragment 的 ``.done``（AC#8）。重启后该条无 ``.done``
      但有 ``audio.wav`` → 被判为转写未完 → 重新转写补回 ``.done``。
    - ``CASE=stale-part``：在 inbox 生成残留 ``<id>.part``（AC#9）。重启后恢复扫描第一段
      清理该 ``.part``，下一轮轮询重新下载。

    操作真实 ``$SONISCOPE_HOME``（``inbox_root`` / ``fragments_root`` 可注入便于单测）。
    """
    lines: list[str] = []
    if case not in SIMULATE_CASES:
        lines.append(
            f"FAIL — 未知 CASE={case!r}，支持：{' | '.join(SIMULATE_CASES)}"
        )
        return lines, 1
    if not fragment_id:
        lines.append("FAIL — 必须提供 FRAGMENT_ID=<id>")
        return lines, 1
    try:
        date = object_key_for(fragment_id).split("/")[1]
    except OssAdminError as exc:
        lines.append(f"FAIL — 非法 fragment_id：{exc}")
        return lines, 1

    inbox = inbox_root if inbox_root is not None else inbox_dir()
    fragments = fragments_root if fragments_root is not None else fragments_dir()

    if case == CASE_MISSING_DONE:
        frag_dir = fragments / date / fragment_id
        done = frag_dir / DONE_MARKER
        if not frag_dir.is_dir():
            lines.append(f"FAIL — 找不到 fragment 目录：{frag_dir}（无法模拟 missing-done）")
            return lines, 1
        if done.exists():
            done.unlink()
            lines.append(f"已删除 .done：{done}")
        else:
            lines.append(f"该 fragment 本就没有 .done（{done}）")
        has_audio = (frag_dir / AUDIO_FILENAME).is_file()
        lines.append(
            f"audio.wav {'存在' if has_audio else '缺失'} —— 重启 Worker 后该条将"
            f"{'被识别为转写未完并重新转写补回 .done' if has_audio else '在 OSS 轮询中重新下载'}"
        )
        return lines, 0

    # CASE_STALE_PART
    inbox.mkdir(parents=True, exist_ok=True)
    part = inbox / f"{fragment_id}{PART_SUFFIX}"
    part.write_bytes(b"stale-residual-part")
    lines.append(f"已生成残留 .part：{part}")
    lines.append("重启 Worker 后恢复扫描第一段将清理该 .part，下一轮轮询重新下载")
    return lines, 0
