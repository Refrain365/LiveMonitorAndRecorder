import json
import os
import logging

class ConfigManager:
    def __init__(self):
        # 1. 强制设定配置目录为 config 文件夹
        self.config_dir = 'config'
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 2. 定义新文件路径
        self.cookie_file = os.path.join(self.config_dir, 'cookie.json')
        self.bili_file = os.path.join(self.config_dir, 'bilibili.json')
        self.douyin_file = os.path.join(self.config_dir, 'douyin.json')

        # 3. 加载配置 (如果没有则生成新的)
        self.cookie_data = self._load_cookie_config()
        self.bili_list = self._load_list_config(self.bili_file)
        self.douyin_list = self._load_list_config(self.douyin_file)

    def _load_cookie_config(self):
        """加载 Cookie 和 全局设置"""
        default_config = {
            "cookies": {
                "bilibili": "",
                "douyin": ""
            },
            "global_settings": {
                "check_interval": 60,
                "record_quality": "best",
                "save_folder": "Recordings"
            }
        }
        
        # 如果文件不存在，保存默认配置到 config/cookie.json
        if not os.path.exists(self.cookie_file):
            self._save_json(self.cookie_file, default_config)
            return default_config
        
        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # 补全可能缺失的字段
                for k, v in default_config.items():
                    if k not in loaded:
                        loaded[k] = v
                return loaded
        except:
            return default_config

    def _load_list_config(self, filepath):
        """加载主播列表"""
        if not os.path.exists(filepath):
            self._save_json(filepath, [])
            return []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def _save_json(self, filepath, data):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"保存配置文件 {filepath} 失败: {e}")

    # --- 公开方法 ---

    def save_cookie_settings(self):
        self._save_json(self.cookie_file, self.cookie_data)

    def save_streamers(self):
        self._save_json(self.bili_file, self.bili_list)
        self._save_json(self.douyin_file, self.douyin_list)

    def add_streamer(self, name, url, platform, auto_record=False):
        new_streamer = {
            "name": name,
            "url": url,
            "platform": platform,
            "auto_record": auto_record,
            "last_status": False,
            "enabled": True
        }
        
        if platform == 'bilibili':
            self.bili_list.append(new_streamer)
        else:
            self.douyin_list.append(new_streamer)
            
        self.save_streamers()

    def get_streamers(self, target='all'):
        if target == 'bilibili':
            return self.bili_list
        elif target == 'douyin':
            return self.douyin_list
        else:
            return self.bili_list + self.douyin_list
