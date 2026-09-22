# 🐧 LiveMonitorAndRecorder · Linux 版

直播监控与录制助手的**服务器版**：FastAPI 网页界面 + FFmpeg / Streamlink 引擎，
面向长期挂机、无人值守场景。监控检测、直链解析、断流重连、通知体系等核心逻辑与
Windows 版对齐；界面与交互为独立实现的 Web UI（不是 Tkinter 的移植）。

## ✨ 功能特性

**监控与提醒**

- 抖音 / 哔哩哔哩 多主播开播监控，状态变化即时推送（WxPusher、企业微信机器人）
- 通知组：主播归组、每组独立配置推送渠道；勿扰时段（支持跨天）内屏蔽通知
- 监控速度 1~5 档 + 定时调速；休眠时段暂停监控（已开始的录制不受影响）

**录制**

- 抖音录播 V2：requests 解析直播直链（页面 RENDER_DATA → enter 接口 → 正则兜底），
  ffmpeg 边录边存；后台 2 秒守护轮询，断流自动重连（冷却 6 秒 / 最多 5 次 / 30 秒窗口）
- 五档画质：原画 / 蓝光 / 超清 / 高清 / 标清；录播 Cookie 按画质自动注入参数，一份通用
- B站 streamlink 录制：房间没有所选画质档位时自动回退最高可用档，不会因档位名录不上
- 下播后 ffmpeg `-c copy` 无损封装 MP4（不重编码）；可配置是否保留原始 FLV/TS，
  产物大小差超过容差（默认 25MB）时自动保留原文件待检查
- 归档固定按 UTC+8：`Recordings/<平台>/<主播>/<日期>/<时分秒>.mp4`，
  同一天多次直播的文件进同一个日期目录

**Web UI（浏览器操作，无需命令行）**

- 仪表盘：主播状态卡片、直播标题、手动开始/停止录制、运行日志实时滚动
- 主播管理：抖音直播间链接 / 主页链接自动归一（纯抖音号受接口限制会明确提示），
  B站直播间链接与 UID 互转，昵称自动获取；保存有「没有改动 / 保存成功 / 保存失败」明确反馈
- 录播文件：按 平台/主播/日期 树形浏览，显示文件大小，下载支持断点续传（HTTP Range）
- B站扫码登录：页面生成二维码，手机 App 扫码确认后 Cookie 自动验证、保存并回填
- 通知 / Cookie / 设置 三页集中管理全部配置
- 可选访问口令保护；界面适配竖屏与窄窗口

**自动化**

- 自定义 .py / .sh 脚本绑定到主播的开播（直播中）/ 下播（未开播）事件，单线程串行执行

## 📦 安装

Linux一键安装脚本

```bash
curl -fsSL https://raw.githubusercontent.com/Refrain365/LiveMonitorAndRecorder/main/Linux/install.sh -o install.sh
bash install.sh
```

仅安装 Linux 版：脚本会把仓库 `Linux/` 目录的内容下载到 **`./LiveMonitorAndRecorder/`**，
并依次完成：Python3 检查（低于 3.8 会警告）→ ffmpeg（Ubuntu 走 apt；CentOS 系
自动下载静态编译版到 `/usr/local/bin`）→ 创建 `.venv` 虚拟环境并安装全部 Python
依赖 → 自动校验 → 注册全局命令 `live` → 打印启动方式。

- 下载前会**自动测速选择最快源**：直连 GitHub +44 个社区镜像（ghproxy 前缀形态）
  并行探测首字节延迟，最快者优先、失败自动按序切换；也可强制指定：
  `LMR_MIRROR=https://ghproxy.cc/ bash install.sh`
- 下载分支默认依次尝试 `main`、`feat/linux-support`（PR 合并前用后者兜底）；
  可用环境变量指定：`LMR_BRANCH=feat/linux-support bash install.sh`

同时创建 systemd 常驻服务（可选，参数会随引导脚本自动传递到下载后的目录）：

```bash
bash install.sh --systemd
```

### 手动安装（不使用脚本时）

```bash
# Ubuntu / Debian
sudo apt install ffmpeg python3 python3-venv
# CentOS / RHEL：官方源没有 ffmpeg，先自行装好 ffmpeg 再继续
python3 -m venv .venv
.venv/bin/pip install -r requirement.txt
```

### 依赖说明

| 依赖 | 用途 | 来源 |
|---|---|---|
| Python ≥ 3.8 | 主程序 | 系统包管理器 |
| FFmpeg | 抖音直录与 MP4 无损封装 | install.sh 自动安装 |
| Streamlink | B站录制引擎 | pip（requirement.txt） |
| FastAPI / Uvicorn | Web UI 服务 | pip |
| requests / qrcode | 平台接口调用与扫码登录 | pip |

## 🚀 运行

安装脚本已注册全局命令，**在任意目录执行 `live` 即可启动录播程序**：

```bash
live
```

等价于进入项目目录运行 `.venv/bin/python main.py`（引导脚本落点 `LiveMonitorAndRecorder/`，
克隆仓库落点 `LiveMonitorAndRecorder/Linux/`；手动安装可自行创建
`/usr/local/bin/live` 启动器或直接进目录运行）。

浏览器访问 `http://<服务器IP>:6657`。所有配置都在网页里完成；首次启动生成
`config/config.json`，旧版（终端菜单时代）的三份配置文件会自动迁移合并。

### systemd 常驻（推荐）

`bash install.sh --systemd` 会自动完成以下全部步骤，也可以手动创建：

```ini
# /etc/systemd/system/livemonitor.service
# 注意：WorkingDirectory 按实际布局调整——完整克隆为 .../LiveMonitorAndRecorder/Linux，
#       引导脚本下载为 .../LiveMonitorAndRecorder（bash install.sh --systemd 会自动取对路径）
[Unit]
Description=LiveMonitorAndRecorder Linux
After=network.target

[Service]
WorkingDirectory=/opt/LiveMonitorAndRecorder/Linux
ExecStart=/opt/LiveMonitorAndRecorder/Linux/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now livemonitor
systemctl status livemonitor     # 查看状态
systemctl restart livemonitor    # 改配置后重启
```

## 🍪 首次使用（三步）

1. **配 Cookie**：「Cookie」页粘贴抖音 Cookie（监控、录播两栏贴同一份即可）；
   B站点「生成B站登录二维码」，手机扫码后 Cookie 自动保存
2. **加主播**：「主播管理」页填链接——抖音填直播间链接或主页链接，
   B站填 UID 或直播间链接，昵称留空自动获取
3. **开录制**：主播卡片点「开启自动录制」——开播即录、断流续录、下播自动封装 MP4

## 📁 目录结构

```
Linux/
├── main.py            # 入口：监控/守护线程 + Web 服务
├── config.py          # 配置管理（config/config.json，旧配置自动迁移）
├── douyin_api.py      # 抖音/B站接口：开播检测、直链解析、画质映射、输入归一
├── monitor.py         # 监控循环 + 录制 + 守护重连 + MP4 封装
├── notifier.py        # WxPusher / 企业微信、通知组、勿扰与休眠时段
├── automation.py      # 开播/下播事件脚本执行
├── qrlogin.py         # B站扫码登录
├── install.sh         # 一键安装（Ubuntu / CentOS）
├── requirement.txt    # Python 依赖清单
├── webui/             # FastAPI 路由 + 静态单页前端
├── config/config.json # 运行配置（含 Cookie，已被 .gitignore 排除）
├── logs/              # 按天滚动日志
└── Recordings/        # 录播产出
    └── 抖音|哔哩哔哩/<主播名>/<YYYY-MM-DD(UTC+8)>/<HH-MM-SS>.mp4
```

## 🪟 与 Windows 版的差异

| | Windows | Linux |
|---|---|---|
| 界面 | Tkinter 桌面 GUI | Web UI（浏览器访问，适配竖屏） |
| 抖音下载引擎 | aria2（FLV 后转码） | ffmpeg 直录（无 aria2 依赖） |
| Cookie 获取 | selenium 自动采集 | 网页粘贴 + B站扫码登录 |
| B站 | 仅监控提醒 | 监控提醒 + streamlink 录制 |
| 自动化脚本 | .py / .bat | .py / .sh |

开播检测、直链解析、画质档位、断流重连参数、通知体系等核心逻辑两边一致。

## ❓ 常见问题

| 现象 | 解决方法 |
|---|---|
| 明明在播却显示「未开播」 | 抖音监控 Cookie 失效，重新粘贴；B站重新扫码登录 |
| 开播了但没录到（日志报未获取直链） | 抖音录播 Cookie 失效，重新粘贴 |
| 添加抖音号提示无法解析 | 抖音接口限制，改用直播间链接（开播时）或主页链接 |
| B站录制没按所选画质档 | 该房间无此档位时自动回退最高可用档，属正常行为 |
| 收不到微信通知 | 依次检查：推送渠道开关 → 主播所在通知组 → 是否处于勿扰时段 |
| 服务器占用高 | 「设置」把监控速度调至 3~5 档，或配置定时调速 |
| Web 端口被占用 | 「设置」修改 `webui_port` 后重启程序 |
| 开机自启 / 进程挂了自动拉起 | `bash install.sh --systemd`，或按上文手动创建服务 |
| 修改了保存目录 | 只影响新录制；旧文件需手动移动到新目录 |

## 📜 声明

本项目仅供学习交流，请勿用于商业用途。开源免费，**请勿倒卖**。
