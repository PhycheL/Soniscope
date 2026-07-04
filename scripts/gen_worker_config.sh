#!/usr/bin/env bash
#
# 生成 Worker 运行时配置 config.yaml（US-001 手册 H-2 块）。
#
# 数据来源：实时读取 docs/runbook/cloud-setup.md，把其中已登记的非敏感值
# （OSS endpoint/bucket、NLS AppKey、region、模型名等）抽取出来自动填入。
# 只有 runbook 里没有的值（按红线，明文 AK/Secret 只在 1Password，不进 runbook）
# 才留 __FILL_ME__ 占位符给你手工填写：
#   - oss.access_key_id / oss.access_key_secret    （§2.2 soniscope-local-reader 只读 AK）
#   - transcriber.access_key_id / access_key_secret（§2.3 soniscope-asr AK）
#
# 同时负责 H 块要求的相关操作：
#   - 写到 SONISCOPE_HOME 指定的目录（可来自环境变量或仓库根目录 .env），与代码仓库分离
#   - 生成后立即 chmod 600（红线 §3）
#   - 不覆盖已填好的配置（除非 --force）
#
# 用法：
#   scripts/gen_worker_config.sh                 # 读 runbook 生成（已存在则拒绝覆盖）
#   scripts/gen_worker_config.sh --force         # 强制重新生成
#   scripts/gen_worker_config.sh --check         # 校验现有 config.yaml（权限 + 待填字段）
#   scripts/gen_worker_config.sh --runbook PATH  # 指定 runbook 路径（默认仓库内 cloud-setup.md）
#   scripts/gen_worker_config.sh -h              # 帮助
#
set -euo pipefail

FILL='__FILL_ME__'   # --check 据此判断哪些字段尚未填写

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNBOOK_DEFAULT="$REPO_ROOT/docs/runbook/cloud-setup.md"
ENV_FILE="$REPO_ROOT/.env"

log()  { printf '[gen-config] %s\n' "$*"; }
warn() { printf '[gen-config] ⚠ %s\n' "$*" >&2; }
die()  { printf '[gen-config] 错误：%s\n' "$*" >&2; exit 1; }

usage() {
  sed -n '3,23p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

resolve_home() {
  # 目录来源优先级；结果写入全局 HOME_DIR / HOME_SRC：
  #   1) 环境变量 $SONISCOPE_HOME
  #   2) 仓库根目录 .env 中的 SONISCOPE_HOME
  local home src
  if [ -n "${SONISCOPE_HOME:-}" ]; then
    home="$SONISCOPE_HOME"; src="环境变量 SONISCOPE_HOME"
  else
    home="$(dotenv_soniscope_home)"
    [ -n "$home" ] || die "未设置 SONISCOPE_HOME。请 export SONISCOPE_HOME=/path/to/SoniScope，或在仓库根目录 .env 写入 SONISCOPE_HOME=/path/to/SoniScope。"
    src=".env"
  fi
  case "$home" in "~"|"~/"*) home="${HOME}${home#\~}";; esac
  HOME_DIR="$home"
  HOME_SRC="$src"
}

dotenv_soniscope_home() {
  [ -f "$ENV_FILE" ] || return 0
  awk '
    function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    /^[ \t]*(#|$)/ { next }
    {
      line = $0
      sub(/^[ \t]*export[ \t]+/, "", line)
      if (line ~ /^[ \t]*SONISCOPE_HOME[ \t]*=/) {
        sub(/^[^=]*=/, "", line)
        line = trim(line)
        if ((substr(line, 1, 1) == "\"" && substr(line, length(line), 1) == "\"") ||
            (substr(line, 1, 1) == "\047" && substr(line, length(line), 1) == "\047")) {
          line = substr(line, 2, length(line) - 2)
        }
        print line
        exit
      }
    }
  ' "$ENV_FILE"
}

# ---- 从 runbook 抽取「首个匹配行里的第一个反引号包裹值」 ----
# 用法：rb_value <grep-ERE-用于定位行>
rb_value() {
  grep -m1 -E "$1" "$RUNBOOK" 2>/dev/null \
    | grep -oE '`[^`]+`' | head -1 | tr -d '`' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

# ---- YAML 标量：占位符保持裸值（供 --check 识别），真实值加引号 ----
yval() {
  if [ "$1" = "$FILL" ]; then printf '%s' "$FILL"; else printf '"%s"' "$1"; fi
}

# ---- 抽取 + 缺失则降级为占位符并记账 ----
PENDING_NOTES=()
need() { # need <显示名> <runbook值>
  local name="$1" val="$2"
  if [ -z "$val" ]; then
    PENDING_NOTES+=("$name（runbook 未登记）")
    printf '%s' "$FILL"
  else
    printf '%s' "$val"
  fi
}

write_template() {
  local dst="$1"

  [ -f "$RUNBOOK" ] || die "找不到 runbook：$RUNBOOK（用 --runbook 指定路径）"
  log "读取 runbook：$RUNBOOK"

  # 从 runbook 抽取非敏感值
  local oss_endpoint oss_bucket asr_appkey asr_region asr_model
  oss_endpoint="$(need 'oss.endpoint' "$(rb_value '^-[[:space:]]*Endpoint')")"
  oss_bucket="$(need 'oss.bucket'     "$(rb_value 'Bucket 名')")"
  asr_appkey="$(need 'transcriber.appkey' "$(rb_value 'AppKey')")"
  asr_region="$(rb_value 'API endpoint')"
  asr_model="$(rb_value '模型名')"

  # api_endpoint：runbook 只记 region，按 NLS 录音文件转写固定格式推导
  local asr_endpoint
  if [ -n "$asr_region" ]; then
    asr_endpoint="filetrans.${asr_region}.aliyuncs.com"
  else
    asr_endpoint="$(need 'transcriber.api_endpoint' '')"
  fi
  [ -n "$asr_model" ] || asr_model="$(need 'transcriber.model' '')"

  # 凭证：红线规定不进 runbook，恒为手工填写
  PENDING_NOTES+=('oss.access_key_id / access_key_secret（§2.2 1Password）')
  PENDING_NOTES+=('transcriber.access_key_id / access_key_secret（§2.3 1Password）')

  cat > "$dst" <<EOF
# SoniScope Worker 运行时配置（US-001 手册 H-2）
# 由 scripts/gen_worker_config.sh 读取 docs/runbook/cloud-setup.md 生成。
# 非敏感值已自动填入；标记为 ${FILL} 的字段需手工替换为真实凭证。
# 本文件含明文 AK，红线：绝不进 git；权限必须 chmod 600。

oss:
  endpoint: $(yval "$oss_endpoint")
  bucket: $(yval "$oss_bucket")
  access_key_id: $(yval "$FILL")        # §2.2 soniscope-local-reader 的 AK ID（1Password）
  access_key_secret: $(yval "$FILL")    # §2.2 soniscope-local-reader 的 AK Secret

poll:
  interval_seconds: 60

transcriber:
  name: cloud-speech
  provider: aliyun-nls
  model: $(yval "$asr_model")    # 来自 runbook §5.2 模型名/版本
  params_version: v1
  api_endpoint: $(yval "$asr_endpoint")   # 由 runbook §5.2 region 推导（NLS 录音文件转写）
  appkey: $(yval "$asr_appkey")    # runbook §5.2 NLS 项目 AppKey（非 AccessKey）
  access_key_id: $(yval "$FILL")        # §2.3 soniscope-asr 的 AK ID（1Password）
  access_key_secret: $(yval "$FILL")    # §2.3 soniscope-asr 的 AK Secret
  local:
    enabled: false   # 本期不部署本地 Whisper
EOF
}

do_check() {
  local dst="$1"
  [ -f "$dst" ] || die "找不到配置文件：${dst} （先不带参数运行本脚本生成模板）"

  local rc=0 perm
  perm="$(stat -f '%Lp' "$dst" 2>/dev/null || stat -c '%a' "$dst" 2>/dev/null || echo '???')"
  if [ "$perm" = "600" ]; then
    log "权限：$perm ✓"
  else
    warn "权限：${perm}（应为 600）。修复：chmod 600 \"${dst}\""
    rc=1
  fi

  local pending
  pending="$(grep -nE ":[[:space:]]*${FILL}" "$dst" || true)"
  if [ -n "$pending" ]; then
    warn "以下字段尚未填写："
    printf '%s\n' "$pending" | sed 's/^/         /' >&2
    rc=1
  else
    log "占位符：全部已填 ✓"
  fi

  local filled
  filled="$(grep -E '^[[:space:]]*[a-z_]+:[[:space:]]+[^[:space:]#]' "$dst" \
            | grep -v "$FILL" | wc -l | tr -d ' ')"
  log "已填(非占位)叶子字段数：$filled"

  [ "$rc" -eq 0 ] && log "校验通过：$dst" || die "校验未通过，见上方提示。"
}

main() {
  local mode="gen" force=0
  RUNBOOK="$RUNBOOK_DEFAULT"
  while [ $# -gt 0 ]; do
    case "$1" in
      --check)      mode="check";;
      --force|-f)   force=1;;
      --runbook)    shift; RUNBOOK="${1:-}"; [ -n "$RUNBOOK" ] || die "--runbook 需要路径参数";;
      -h|--help)    usage 0;;
      *)            die "未知参数：$1（-h 查看用法）";;
    esac
    shift
  done

  local home dst
  resolve_home
  home="$HOME_DIR"
  dst="$home/config.yaml"
  log "工作目录        = ${home}（来源：${HOME_SRC}）"
  log "目标文件        = $dst"

  case "$dst" in
    "$REPO_ROOT"/*) warn "目标位于代码仓库内（${REPO_ROOT}）——红线要求运行时配置与 repo 分离，请设置 SONISCOPE_HOME 指向 repo 之外的目录。";;
  esac

  if [ "$mode" = "check" ]; then
    do_check "$dst"
    return
  fi

  [ -d "$home" ] || die "工作目录不存在：${home}。请先手动创建/挂载该目录，并通过 SONISCOPE_HOME 指向它。"
  [ -w "$home" ] || die "工作目录不可写：${home}。请检查目录权限。"

  if [ -f "$dst" ] && [ "$force" -ne 1 ]; then
    die "$dst 已存在。如确认要覆盖（会清掉已填凭证），请加 --force；只想校验请用 --check。"
  fi

  write_template "$dst"
  chmod 600 "$dst"

  log "已生成并 chmod 600。"
  log "权限确认：$(ls -la "$dst")"
  echo
  if [ "${#PENDING_NOTES[@]}" -gt 0 ]; then
    log "仍需手工填写（runbook 中没有的值）："
    local n
    for n in "${PENDING_NOTES[@]}"; do log "  - $n"; done
    echo
  fi
  log "下一步：编辑 ${dst} 替换 ${FILL} 字段，再运行 scripts/gen_worker_config.sh --check 验证"
}

main "$@"
