"""Linux 版入口：启动监控/守护线程 + FastAPI Web UI。

用法：
    python main.py                 # 前台运行
    nohup python main.py &         # 后台运行（推荐用 systemd，见 README）

浏览器访问 http://<服务器IP>:6657 即可（端口可在 Web UI「设置」里改）。
旧的终端菜单与独立推送进程已移除，所有交互都在 Web UI 完成。
"""
import sys
import threading

import uvicorn

from config import ConfigManager
from monitor import LiveMonitor
from webui.app import create_app


def main():
    cfg = ConfigManager()
    monitor = LiveMonitor(cfg)
    monitor.start()

    host = cfg.global_settings.get("webui_host", "0.0.0.0")
    port = int(cfg.global_settings.get("webui_port", 6657))

    app = create_app(monitor)
    print(f"🦜 Web UI: http://127.0.0.1:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
