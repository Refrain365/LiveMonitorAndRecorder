import requests
import time
import logging
import subprocess
import os
import shutil
import signal
import sys
from datetime import datetime
from config import ConfigManager

class LiveMonitor:
    def __init__(self, config_manager):
        self.cfg = config_manager
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        if not shutil.which("ffmpeg"):
            logging.warning("⚠️ 未检测到 ffmpeg，将只保存 .ts 格式，无法自动转为 .mp4！")

    def _clean_url(self, url):
        if "?" in url:
            return url.split("?")[0]
        return url

    def check_bilibili(self, url):
        try:
            clean_url = self._clean_url(url)
            room_id = clean_url.split("/")[-1]
            api_url = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}"
            
            b_cookie = self.cfg.cookie_data['cookies'].get('bilibili', '')
            headers = self.headers.copy()
            if b_cookie:
                headers['Cookie'] = b_cookie

            res = requests.get(api_url, headers=headers, timeout=10)
            data = res.json()
            if data['code'] == 0:
                is_live = data['data']['live_status'] == 1
                return is_live
        except Exception as e:
            logging.error(f"B站检测出错: {e}")
        return False

    def check_douyin(self, url):
        try:
            clean_url = self._clean_url(url)
            cmd = ["streamlink", clean_url, "--json"]
            dy_cookie = self.cfg.cookie_data['cookies'].get('douyin', '')
            if dy_cookie:
                cmd.extend(["--http-header", f"Cookie={dy_cookie}"])

            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
            if result.returncode == 0:
                return True
        except Exception:
            pass
        return False

    def start_recording(self, streamer):
        name = streamer['name']
        url = self._clean_url(streamer['url']) 
        platform = streamer.get('platform', 'douyin')
        
        root_dir = self.cfg.cookie_data['global_settings'].get('save_folder', 'Recordings')
        save_dir = os.path.join(os.getcwd(), root_dir, platform, name)
        os.makedirs(save_dir, exist_ok=True)
        
        time_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        ts_path = os.path.join(save_dir, f"{time_str}.ts")
        mp4_path = os.path.join(save_dir, f"{time_str}.mp4")
        
        logging.info(f"🚀 启动录制: {name} -> {ts_path}")
        
        cookie_arg = ""
        cookie_val = self.cfg.cookie_data['cookies'].get(platform, '')
        if cookie_val:
            cookie_arg = f"--http-header \"Cookie={cookie_val}\""

        shell_cmd = (
            f"streamlink \"{url}\" best -o \"{ts_path}\" --force {cookie_arg} "
            f"&& ffmpeg -i \"{ts_path}\" -c copy \"{mp4_path}\" -loglevel error -y "
            f"&& rm \"{ts_path}\""
        )
        subprocess.Popen(shell_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def run_check_loop(self, mode='all'):
        """
        mode: 'all', 'bilibili', 'douyin'
        """
        # === 优化点 3: 信号处理，捕获停止指令 ===
        def signal_handler(sig, frame):
            logging.info(f"🛑 收到停止信号 ({sig})，监控服务正在安全退出...")
            sys.exit(0)
        
        # 注册信号：当收到 SIGTERM (pkill发出的) 或 SIGINT (Ctrl+C) 时，执行 signal_handler
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        logging.info("==========================================")
        logging.info(f"🟢 监控服务启动 | 模式: [{mode}]")
        logging.info("==========================================")
        
        while True:
            self.cfg = ConfigManager()
            interval = self.cfg.cookie_data['global_settings'].get('check_interval', 60)
            
            streamers = self.cfg.get_streamers(mode)
            
            for s in streamers:
                if not s.get('enabled', True): continue

                is_live = False
                clean_url = self._clean_url(s['url'])
                platform = s.get('platform', 'douyin')

                if platform == 'bilibili':
                    is_live = self.check_bilibili(clean_url)
                else:
                    is_live = self.check_douyin(clean_url)
                
                if is_live:
                    if not s['last_status']:
                        logging.info(f"✅ 开播: {s['name']} ({platform})")
                        if s.get('auto_record', False):
                            self.start_recording(s)
                        
                        s['last_status'] = True
                        self.cfg.save_streamers()
                else:
                    if s['last_status']:
                        logging.info(f"❌ 下播: {s['name']}")
                        s['last_status'] = False
                        self.cfg.save_streamers()

            time.sleep(interval)
