import time
import requests
import logging
import signal
import sys
import os
from datetime import datetime
from config import ConfigManager

# 独立日志：notifier_daemon.log
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', filename='notifier_daemon.log', filemode='a')

class PushDaemon:
    def __init__(self):
        self.cfg = ConfigManager()

    def send_msg(self, title, content):
        notif = self.cfg.cookie_data.get('notification', {})
        token = notif.get('wxpusher_app_token')
        uids = notif.get('wxpusher_uids')
        if not token or not uids: return

        api_url = "https://wxpusher.zjiecode.com/api/send/message"
        data = {
            "appToken": token,
            "content": f"{content}\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "summary": title,
            "contentType": 1,
            "uids": uids
        }
        try:
            res = requests.post(api_url, json=data, timeout=10).json()
            if res.get('code') == 1000:
                logging.info(f"成功推送: {title}")
        except Exception as e:
            logging.error(f"推送失败: {e}")

    def run(self):
        def sig_handler(s, f):
            logging.info("🛑 推送后台关闭")
            sys.exit(0)
        signal.signal(signal.SIGTERM, sig_handler)
        logging.info("🟢 推送后台服务已启动...")
        
        while True:
            # 保持进程常驻，Notifier 也可以增加定时自检逻辑
            time.sleep(60)

if __name__ == "__main__":
    PushDaemon().run()
