#!/usr/bin/env bash
# ============================================================
# LiveMonitorAndRecorder Linux 一键安装脚本
# 仅安装本项目 Linux 版所需内容（依赖 + 可选 systemd 服务），
# 不会改动仓库其他部分；仅支持 Linux 环境执行。
# 支持：Ubuntu / Debian（apt）、CentOS / RHEL / Fedora（dnf/yum）
#
# 用法（推荐：一条命令直接跑）：
#   curl -fsSL https://raw.githubusercontent.com/Refrain365/LiveMonitorAndRecorder/main/Linux/install.sh | bash
#   加参数用 bash -s -- 传递：   .../install.sh | bash -s -- --systemd
#   环境变量直接给 bash：        .../install.sh | LMR_BRANCH=feat/linux-support bash
#                                .../install.sh | LMR_MIRROR=https://ghproxy.cc/ bash
#
#   也可先下载再执行（在完整项目目录、含 main.py 时会跳过下载直接安装）：
#     curl -fsSL .../Linux/install.sh -o install.sh && bash install.sh [--systemd]
#   自举说明：检测到脚本同目录缺少项目文件时，会自动把仓库 Linux/ 目录内容
#   下载到 ./LiveMonitorAndRecorder/ 再继续安装。
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WITH_SYSTEMD=0
if [ "${1:-}" = "--systemd" ]; then
  WITH_SYSTEMD=1
fi

TMP_DIRS=""
trap 'if [ -n "$TMP_DIRS" ]; then rm -rf $TMP_DIRS; fi' EXIT

log()  { printf '\033[1;32m[✔]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[✘]\033[0m %s\n' "$*" >&2; }

# 仅限 Linux：Windows（Git Bash/MSYS/Cygwin）与 macOS 直接拒绝
case "$(uname -s)" in
  Linux) ;;
  *)
    err "本脚本仅支持 Linux（当前系统: $(uname -s)）。Windows 请使用 Windows/ 目录版本。"
    exit 1
    ;;
esac

# 需要提权的操作统一走这里（root 直跑 / 普通用户走 sudo）
if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
else
  SUDO="sudo"
fi
as_root() {
  if [ -n "$SUDO" ]; then
    sudo "$@"
  else
    "$@"
  fi
}

# ---------- 1. 识别系统与包管理器 ----------
PKG="unknown"
if command -v apt-get >/dev/null 2>&1; then
  PKG="apt-get"
elif command -v dnf >/dev/null 2>&1; then
  PKG="dnf"
elif command -v yum >/dev/null 2>&1; then
  PKG="yum"
fi

# ----------1.5 项目自举：单独下载本脚本时，自动拉取 Linux 版内容 ----------
# 判据：脚本同目录没有 main.py → 不是完整项目目录。
# 内容取自仓库 Linux/ 目录，落地目录固定命名为 LiveMonitorAndRecorder。
if [ ! -f "$SCRIPT_DIR/main.py" ]; then
  if ! command -v curl >/dev/null 2>&1; then
    log "安装 curl 以便下载项目文件 ..."
    case "$PKG" in
      apt-get) as_root apt-get update -y && as_root apt-get install -y curl ;;
      dnf)     as_root dnf install -y curl ;;
      yum)     as_root yum install -y curl ;;
      *) err "缺少 curl 且无法通过包管理器安装"; exit 1 ;;
    esac
  fi
  # ---- GitHub 加速源 ----
  # 用法均为「镜像前缀 + 完整 GitHub URL」（ghproxy 形态），例如：
  #   https://ghproxy.cc/https://github.com/Refrain365/LiveMonitorAndRecorder/archive/refs/heads/main.tar.gz
  # 第一项空字符串 = 直连 GitHub（推荐，能连通时通常最快）
  GITHUB_SOURCES=(
    ""
    "https://github.chenc.dev/"
    "https://ghproxy.cfd/"
    "https://github.tbedu.top/"
    "https://ghproxy.cc/"
    "https://gh.monlor.com/"
    "https://cdn.akaere.online/"
    "https://gh.idayer.com/"
    "https://gh.llkk.cc/"
    "https://ghpxy.hwinzniej.top/"
    "https://github-proxy.memory-echoes.cn/"
    "https://git.yylx.win/"
    "https://gitproxy.mrhjx.cn/"
    "https://gh.fhjhy.top/"
    "https://gp.zkitefly.eu.org/"
    "https://gh-proxy.com/"
    "https://ghfile.geekertao.top/"
    "https://j.1lin.dpdns.org/"
    "https://ghproxy.imciel.com/"
    "https://github-proxy.teach-english.tech/"
    "https://gh.927223.xyz/"
    "https://github.ednovas.xyz/"
    "https://ghf.xn--eqrr82bzpe.top/"
    "https://gh.dpik.top/"
    "https://gh.jasonzeng.dev/"
    "https://gh.xxooo.cf/"
    "https://gh.bugdey.us.kg/"
    "https://ghm.078465.xyz/"
    "https://j.1win.ggff.net/"
    "https://tvv.tw/"
    "https://gitproxy.127731.xyz/"
    "https://gh.inkchills.cn/"
    "https://ghproxy.cxkpro.top/"
    "https://gh.sixyin.com/"
    "https://github.geekery.cn/"
    "https://git.669966.xyz/"
    "https://gh.5050net.cn/"
    "https://gh.felicity.ac.cn/"
    "https://github.dpik.top/"
    "https://ghp.keleyaa.com/"
    "https://gh.wsmdn.dpdns.org/"
    "https://ghproxy.monkeyray.net/"
    "https://fastgit.cc/"
    "https://gh.catmak.name/"
    "https://gh.noki.icu/"
  )

  if [ -n "${LMR_BRANCH:-}" ]; then
    LMR_BRANCHES="$LMR_BRANCH"
  else
    # 合并前用 feat 分支兜底，合并后 main 即可
    LMR_BRANCHES="main feat/linux-support"
  fi
  BOOT_TMP="$(mktemp -d)"
  TMP_DIRS="$TMP_DIRS $BOOT_TMP"
  TARGET="$SCRIPT_DIR/LiveMonitorAndRecorder"

  # 首字节延迟探测：range 请求第1个字节，4 秒超时，成功输出耗时（秒）
  probe_ttfb() {
    local out
    out=$(curl -fL -sS -r0-0 --max-time 4 -o /dev/null \
      -w '%{http_code} %{time_total}' "$1$2" 2>/dev/null) || return 1
    case "$out" in
      200\ * | 206\ *) printf '%s' "$out" | awk '{print $2}' ;;
      *) return 1 ;;
    esac
  }

  # 并行探测全部候选，选首字节最快者。
  # 设置 LMR_MIRROR=https://xxx/ 可强制指定镜像、跳过测速。
  select_fastest_prefix() {
    if [ -n "${LMR_MIRROR:-}" ]; then
      printf '%s' "$LMR_MIRROR"
      return 0
    fi
    local dir i p t best="" bestt=999999
    dir="$(mktemp -d)"
    i=0
    for p in "${GITHUB_SOURCES[@]}"; do
      ( t=$(probe_ttfb "$p" "$1") && printf '%s' "$t" >"$dir/$i" ) &
      i=$((i + 1))
    done
    wait || true
    i=0
    for p in "${GITHUB_SOURCES[@]}"; do
      if [ -f "$dir/$i" ]; then
        t="$(cat "$dir/$i")"
        if awk -v a="$t" -v b="$bestt" 'BEGIN { exit !(a < b) }'; then
          bestt="$t"
          best="$p"
        fi
      fi
      i=$((i + 1))
    done
    rm -rf "$dir"
    # 全部探测失败时返回哨兵值，避免与“直连最快（空前缀）”混淆
    if [ "$bestt" = "999999" ]; then
      printf '%s' "__NONE__"
    else
      printf '%s' "$best"
    fi
  }

  FIRST_BR="${LMR_BRANCHES%% *}"
  PROBE_URL="https://github.com/Refrain365/LiveMonitorAndRecorder/archive/refs/heads/${FIRST_BR}.tar.gz"
  if [ -z "${LMR_MIRROR:-}" ]; then
    log "测速选择最快下载源（${#GITHUB_SOURCES[@]} 个候选，含直连）..."
  fi
  BEST_PREFIX="$(select_fastest_prefix "$PROBE_URL")"
  if [ -n "${LMR_MIRROR:-}" ]; then
    log "使用指定镜像: $LMR_MIRROR"
  elif [ "$BEST_PREFIX" = "__NONE__" ]; then
    warn "所有源测速均失败，将按列表顺序逐个尝试"
    BEST_PREFIX=""
  elif [ -z "$BEST_PREFIX" ]; then
    log "最快源: 直连 GitHub"
  else
    log "最快镜像: $BEST_PREFIX"
  fi

  # 下载顺序：最快者在前，其余候选依次兜底
  DL_ORDER=("$BEST_PREFIX")
  for p in "${GITHUB_SOURCES[@]}"; do
    if [ "$p" != "$BEST_PREFIX" ]; then
      DL_ORDER+=("$p")
    fi
  done

  DOWNLOADED=0
  for br in $LMR_BRANCHES; do
    # ?cb=时间戳：绕过镜像对 archive 的旧缓存（GitHub 忽略该参数，直连不受影响）
    FULL_URL="https://github.com/Refrain365/LiveMonitorAndRecorder/archive/refs/heads/${br}.tar.gz?cb=$(date +%s)"
    for prefix in "${DL_ORDER[@]}"; do
      log "下载分支 ${br}（源: ${prefix:-直连 GitHub}）..."
      if curl -fL --retry 1 --connect-timeout 8 --max-time 600 \
          -o "$BOOT_TMP/lmr.tar.gz" "${prefix}${FULL_URL}"; then
        rm -rf "$BOOT_TMP/x"
        mkdir -p "$BOOT_TMP/x"
        if tar -xzf "$BOOT_TMP/lmr.tar.gz" -C "$BOOT_TMP/x" 2>/dev/null; then
          SRC="$(find "$BOOT_TMP/x" -maxdepth 3 -type d -name Linux | head -1)"
          if [ -n "$SRC" ] && [ -f "$SRC/main.py" ]; then
            mkdir -p "$TARGET"
            cp -a "$SRC"/. "$TARGET"/
            DOWNLOADED=1
            break
          fi
        fi
      fi
      warn "该源下载失败，尝试下一个源 ..."
    done
    if [ "$DOWNLOADED" -eq 1 ]; then
      break
    fi
  done
  if [ "$DOWNLOADED" -ne 1 ]; then
    err "项目内容下载失败（全部源均不可用）。可手动克隆："
    err "  git clone https://github.com/Refrain365/LiveMonitorAndRecorder.git LiveMonitorAndRecorder"
    err "  然后执行 LiveMonitorAndRecorder/Linux/install.sh"
    exit 1
  fi
  log "已下载到: $TARGET（目录名 LiveMonitorAndRecorder）"
  rm -rf "$BOOT_TMP"
  if [ ! -f "$TARGET/main.py" ]; then
    err "下载内容异常（缺少 main.py），请稍后重试或手动克隆："
    err "  git clone https://github.com/Refrain365/LiveMonitorAndRecorder.git LiveMonitorAndRecorder"
    exit 1
  fi
  # 直接切换工作目录，继续执行本脚本剩余步骤：
  # 不依赖压缩包内是否包含 install.sh（镜像可能缓存合并前的旧包），
  # --systemd 等参数与 LMR_* 环境变量在本进程内天然保留。
  SCRIPT_DIR="$TARGET"
  cd "$SCRIPT_DIR" || { err "无法进入项目目录: $SCRIPT_DIR"; exit 1; }
  log "已切换到项目目录，继续安装 ..."
fi

OS_NAME="unknown"
if [ -r /etc/os-release ]; then
  OS_NAME="$(. /etc/os-release && echo "${PRETTY_NAME:-unknown}")"
fi
echo "=== LiveMonitorAndRecorder 一键安装 ==="
log "系统: $OS_NAME | 包管理器: $PKG"

# ---------- 2. Python3 ----------
if ! command -v python3 >/dev/null 2>&1; then
  log "安装 python3 ..."
  case "$PKG" in
    apt-get)
      as_root apt-get update -y
      as_root apt-get install -y python3 python3-pip python3-venv curl
      ;;
    dnf)
      as_root dnf install -y python3 python3-pip curl
      ;;
    yum)
      as_root yum install -y python3 python3-pip curl
      ;;
    *)
      err "未检测到 apt/dnf/yum，请先手动安装 python3（需3.8+）"
      exit 1
      ;;
  esac
fi
PY_VER="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
log "Python: $PY_VER ($(command -v python3))"
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)'; then
  warn "Python $PY_VER 低于3.8，部分依赖可能装不上，建议升级 Python"
fi

# ---------- 3. ffmpeg ----------
if command -v ffmpeg >/dev/null 2>&1; then
  log "ffmpeg 已安装: $(ffmpeg -version 2>/dev/null | head -1)"
else
  case "$PKG" in
    apt-get)
      # Ubuntu/Debian 官方源自带
      log "通过 apt 安装 ffmpeg ..."
      as_root apt-get update -y
      as_root apt-get install -y ffmpeg xz-utils
      ;;
    *)
      # CentOS/RHEL 系官方源没有 ffmpeg：
      # 不折腾 EPEL/RPM Fusion 源（各小版本差异大、易踩坑），
      # 直接下载通用静态编译版到 /usr/local/bin，任何发行版都能用。
      # 多源故障切换：GitHub BtbN 构建（国内可达性较好）优先，johnvansickle 兜底。
      case "$(uname -m)" in
        x86_64)                 FFARCH="amd64"; BTBN="linux64" ;;
        aarch64 | arm64)        FFARCH="arm64"; BTBN="linuxarm64" ;;
        *) err "不支持的 CPU 架构: $(uname -m)"; exit 1 ;;
      esac
      if ! command -v curl >/dev/null 2>&1; then
        err "缺少 curl，无法下载 ffmpeg 静态版"
        exit 1
      fi
      TMP="$(mktemp -d)"
      TMP_DIRS="$TMP_DIRS $TMP"
      FF_URLS="
https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-${BTBN}-gpl.tar.xz
https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-${FFARCH}-static.tar.xz
"
      DOWNLOADED=0
      for ff_url in $FF_URLS; do
        log "下载 ffmpeg 静态编译版: $ff_url"
        if curl -fL --retry 2 --connect-timeout 15 -o "$TMP/ffmpeg.tar.xz" "$ff_url"; then
          DOWNLOADED=1
          break
        fi
        warn "该源下载失败，尝试下一个 ..."
      done
      if [ "$DOWNLOADED" -ne 1 ]; then
        err "所有 ffmpeg 下载源均失败，请手动安装 ffmpeg 后重试"
        exit 1
      fi
      tar -xJf "$TMP/ffmpeg.tar.xz" -C "$TMP"
      FF_BIN="$(find "$TMP" -maxdepth 4 -type f -name ffmpeg | head -1)"
      if [ -z "$FF_BIN" ]; then
        err "ffmpeg 静态包解压异常"
        exit 1
      fi
      as_root install -m 755 "$(dirname "$FF_BIN")/ffmpeg" "$(dirname "$FF_BIN")/ffprobe" /usr/local/bin/
      ;;
  esac
  command -v ffmpeg >/dev/null 2>&1 || { err "ffmpeg 安装失败"; exit 1; }
  log "ffmpeg: $(ffmpeg -version 2>/dev/null | head -1)"
fi

# ---------- 4. 虚拟环境 + Python 依赖 ----------
cd "$SCRIPT_DIR"
if [ ! -x .venv/bin/python ]; then
  log "创建虚拟环境 .venv ..."
  if ! python3 -m venv .venv; then
    warn "venv 创建失败，尝试补装组件后重试 ..."
    case "$PKG" in
      apt-get) as_root apt-get install -y python3-venv || true ;;
      *)       warn "RHEL 系 venv 通常随 python3 自带，若持续失败请检查 python3 版本" ;;
    esac
    rm -rf .venv
    python3 -m venv .venv || { err "虚拟环境创建失败，请检查 python3-venv/virtualenv"; exit 1; }
  fi
fi
log "安装 Python 依赖（fastapi / streamlink / qrcode 等）..."
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirement.txt

# ---------- 5. 安装校验 ----------
log "校验安装结果..."
.venv/bin/python -c "import fastapi, uvicorn, requests, qrcode, streamlink; print('  Python 依赖: OK')"
echo "  ffmpeg:     $(ffmpeg -version 2>/dev/null | head -1)"
echo "  streamlink: $(.venv/bin/streamlink --version 2>/dev/null | head -1)"

# ---------- 6. 注册全局命令 live：任意目录执行即启动录播程序 ----------
LIVE_CMD="/usr/local/bin/live"
if [ -e "$LIVE_CMD" ] && ! grep -q "LiveMonitorAndRecorder 启动器" "$LIVE_CMD" 2>/dev/null; then
  warn "/usr/local/bin/live 已被其他程序占用，跳过注册（如需本功能请先删除该文件再重装）"
else
  if as_root tee "$LIVE_CMD" >/dev/null <<EOF
#!/bin/sh
# LiveMonitorAndRecorder 启动器（install.sh 自动生成）
cd "$SCRIPT_DIR" || exit 1
exec ./.venv/bin/python main.py "\$@"
EOF
  then
    if as_root chmod +x "$LIVE_CMD"; then
      log "已注册全局命令: live（任意目录执行即可启动录播程序）"
    else
      warn "live 命令执行权限设置失败（不影响其他功能）"
    fi
  else
    warn "全局命令 live 注册失败（不影响其他功能）"
  fi
fi

# ---------- 7. 可选：systemd 常驻服务 ----------
if [ "$WITH_SYSTEMD" -eq 1 ]; then
  command -v systemctl >/dev/null 2>&1 || { err "当前环境没有 systemd，跳过服务创建"; exit 1; }
  UNIT="/etc/systemd/system/livemonitor.service"
  log "写入 systemd 服务: $UNIT"
  as_root tee "$UNIT" >/dev/null <<EOF
[Unit]
Description=LiveMonitorAndRecorder Linux
After=network.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
  as_root systemctl daemon-reload
  as_root systemctl enable --now livemonitor
  sleep 2
  as_root systemctl --no-pager -l status livemonitor | head -8 || true
fi

echo ""
log "安装完成！启动方式："
echo ""
echo "    live                # 任意目录全局命令（已注册到 $LIVE_CMD）"
echo ""
echo "  或进入项目目录运行："
echo "    cd $SCRIPT_DIR"
echo "    .venv/bin/python main.py"
echo ""
echo "  然后浏览器访问  http://<服务器IP>:6657"
if [ "$WITH_SYSTEMD" -eq 1 ]; then
  echo ""
  echo "  systemd 服务：systemctl status livemonitor / systemctl restart livemonitor"
fi
echo ""
