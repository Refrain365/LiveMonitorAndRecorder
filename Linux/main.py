"""Linux 版入口：启动监控/守护线程 + FastAPI Web UI。

用法：
    live                          # install.sh 注册的全局命令
    .venv/bin/python main.py      # 或直接运行

启动时会打印本机 / 内网 / 外网三个访问地址（端口可在 Web UI「设置」里改）。
旧的终端菜单与独立推送进程已移除，所有交互都在 Web UI 完成。
"""
import re
import socket

import requests
import uvicorn

from config import ConfigManager
from monitor import LiveMonitor
from webui.app import create_app


def _lan_ip():
    """探测本机内网 IP：UDP 选路法（不真正发包），失败退回 hostname 解析。"""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("223.5.5.5", 53))  # UDP connect 只用于选路取本端地址
        ip = sock.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    finally:
        if sock is not None:
            sock.close()
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return ""


def _is_public_ip(ip):
    """排除回环/私有/链路本地地址，保证外网地址是真的公网 IP。"""
    if ip.startswith(("10.", "127.", "192.168.", "169.254.")):
        return False
    if ip.startswith("172."):
        try:
            if 16 <= int(ip.split(".")[1]) <= 31:
                return False
        except (ValueError, IndexError):
            return False
    return True


def _public_ip():
    """请求多个公网 IP 回显服务，返回首个有效公网 IPv4；全部失败返回空。"""
    sources = (
        "https://api.ipify.org",
        "https://ip.3322.net",
        "https://myip.ipip.net",
    )
    for url in sources:
        try:
            text = requests.get(url, timeout=2).text
            m = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", text)
            if m and _is_public_ip(m.group(1)):
                return m.group(1)
        except Exception:
            continue
    return ""


def main():
    cfg = ConfigManager()
    monitor = LiveMonitor(cfg)
    monitor.start()

    host = cfg.global_settings.get("webui_host", "0.0.0.0")
    port = int(cfg.global_settings.get("webui_port", 6657))

    app = create_app(monitor)
    lan = _lan_ip()
    pub = _public_ip()
    # flush：确保重定向到文件/systemd journal 时地址也能立即显示
    print(f"🦜 Web UI（本机）: http://127.0.0.1:{port}", flush=True)
    print(f"🦜 Web UI（内网）: {f'http://{lan}:{port}' if lan else '未获取到'}", flush=True)
    if pub:
        print(f"🦜 Web UI（外网）: http://{pub}:{port}", flush=True)
    else:
        print(f"🦜 Web UI（外网）: 未获取到（请自行使用 公网IP:{port} 访问）", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
