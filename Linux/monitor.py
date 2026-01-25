import requests
import time
import logging
import subprocess
import os
import signal
import sys
import re
from datetime import datetime
from config import ConfigManager

class LiveMonitor:
    def __init__(self, config_manager):
        self.cfg = config_manager
        self.last_disk_alert = 0

    def _clean_url(self, url):
        return url.split("?")[0] if "?" in url else url

    def _safe_filename(self, name):
        name = name.strip()
        name = re.sub(r'[\\/:*?"<>|]', '_', name)
        return name[:50]

    def trigger_push(self, title, content):
        token = self.cfg.cookie_data['notification'].get('wxpusher_app_token')
        uids = self.cfg.cookie_data['notification'].get('wxpusher_uids')
        if token and uids:
            cmd = f"import requests; requests.post('https://wxpusher.zjiecode.com/api/send/message', json={{'appToken': '{token}', 'content': '{content}', 'summary': '{title}', 'uids': {uids}, 'contentType': 1}})"
            subprocess.Popen([sys.executable, "-c", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def start_recording(self, streamer, title="直播中"):
        name, platform = streamer['name'], streamer.get('platform', 'douyin')
        url, quality = self._clean_url(streamer['url']), streamer.get('quality', 'best')
        split_gb = self.cfg.cookie_data['global_settings'].get('split_size', 0)
        split_arg = f"--max-file-size {int(split_gb * 1024)}M" if split_gb > 0 else ""
        save_folder = self.cfg.cookie_data['global_settings'].get('save_folder', 'Recordings')
        save_dir = os.path.join(os.getcwd(), save_folder, platform, name)
        os.makedirs(save_dir, exist_ok=True)
        t_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename_base = f"{t_str}_{self._safe_filename(title)}"
        ts_path, mp4_path = os.path.join(save_dir, f"{filename_base}.ts"), os.path.join(save_dir, f"{filename_base}.mp4")
        cookie_val = self.cfg.cookie_data['cookies'].get(platform, '')
        cookie_arg = f"--http-header \"Cookie={cookie_val}\"" if cookie_val else ""
        
        # 优化：RECORDING_TARGET 标识放在最前面，方便 ps 过滤
        shell_cmd = (
            f"streamlink \"{url}\" {quality} -o \"{ts_path}\" --force {cookie_arg} {split_arg} "
            f"--title \"REC_ID:{url}\" " 
            f"&& ffmpeg -i \"{ts_path}\" -c copy \"{mp4_path}\" -loglevel error -y && rm \"{ts_path}\""
        )
        subprocess.Popen(shell_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info(f"🚀 Record Start: {name}")

    def run_check_loop(self, mode='all'):
        signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
        while True:
            self.cfg = ConfigManager()
            for s in self.cfg.get_streamers(mode):
                url, platform = self._clean_url(s['url']), s.get('platform', 'douyin')
                is_live, title = False, "直播间"
                try:
                    if platform == 'bilibili':
                        res = requests.get(f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={url.split('/')[-1]}", timeout=10).json()
                        if res['code'] == 0: is_live, title = (res['data']['live_status'] == 1), res['data']['title']
                    else:
                        is_live = subprocess.run(["streamlink", url, "--json"], stdout=subprocess.PIPE, timeout=20).returncode == 0
                except: pass

                if is_live:
                    is_rec = os.system(f"ps aux | grep streamlink | grep 'REC_ID:{url}' | grep -v grep > /dev/null") == 0
                    if not s['last_status']:
                        self.trigger_push("🔴 开播提醒", f"主播【{s['name']}】已开播")
                        self.start_recording(s, title)
                        s['last_status'] = True; self.cfg.save_streamers()
                    elif not is_rec:
                        self.start_recording(s, title)
                else:
                    if s['last_status']: s['last_status'] = False; self.cfg.save_streamers()
            time.sleep(self.cfg.cookie_data['global_settings'].get('check_interval', 60))
