"""配置管理：单一 config/config.json，含旧版三文件自动迁移。

线程安全：监控线程与 Web 线程都会读写配置，统一走 self._lock。
"""
import json
import os
import threading

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# 旧版（终端菜单时代）的三个配置文件，检测到时自动迁移
LEGACY_COOKIE_FILE = os.path.join(CONFIG_DIR, "cookie.json")
LEGACY_BILI_FILE = os.path.join(CONFIG_DIR, "bilibili.json")
LEGACY_DOUYIN_FILE = os.path.join(CONFIG_DIR, "douyin.json")

QUALITIES = ["原画", "蓝光", "超清", "高清", "标清"]


def _default_config():
    return {
        "streamers": [],
        "cookies": {
            "douyin_monitor": "",
            "douyin_record": "",
            "bilibili": "",
        },
        "notification": {
            "wxpusher_app_token": "",
            "wxpusher_uids": [],
            "wxpusher_enabled": True,
            "wecom_webhook": "",
            "wecom_enabled": False,
            "notification_groups": [],
            "default_notification_group": "默认组",
            "do_not_disturb_periods": [],
        },
        "global_settings": {
            "check_interval": 60,
            "monitor_speed_level": 1,
            "scheduled_speed_periods": [],
            "save_folder": "Recordings",
            "keep_flv": False,
            "size_tolerance_mb": 25,
            "split_size": 0,
            "sleep_periods": [],
            "webui_password": "",
            "webui_host": "0.0.0.0",
            "webui_port": 6657,
        },
        "automations": [],
    }


def _deep_merge(base, loaded):
    """把已加载配置合并进默认结构，缺的键补默认值（不递归覆盖列表）。"""
    for k, v in base.items():
        if k not in loaded:
            loaded[k] = v
        elif isinstance(v, dict) and isinstance(loaded[k], dict):
            _deep_merge(v, loaded[k])
    return loaded


class ConfigManager:
    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self._lock = threading.RLock()
        self._migrate_legacy()
        self.data = self._load()

    # ---------- 读写 ----------

    def _load(self):
        if not os.path.exists(CONFIG_FILE):
            data = _default_config()
            self._save_json(CONFIG_FILE, data)
            return data
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            return _deep_merge(_default_config(), loaded)
        except Exception:
            return _default_config()

    def save(self):
        with self._lock:
            self._save_json(CONFIG_FILE, self.data)

    @staticmethod
    def _save_json(filepath, data):
        tmp = filepath + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            os.replace(tmp, filepath)
        except Exception as e:
            print(f"[配置] 保存失败 {filepath}: {e}")

    # ---------- 旧版迁移 ----------

    def _migrate_legacy(self):
        if not (os.path.exists(LEGACY_COOKIE_FILE)
                or os.path.exists(LEGACY_BILI_FILE)
                or os.path.exists(LEGACY_DOUYIN_FILE)):
            return
        if os.path.exists(CONFIG_FILE):
            return  # 已迁移过
        data = _default_config()
        try:
            if os.path.exists(LEGACY_COOKIE_FILE):
                with open(LEGACY_COOKIE_FILE, "r", encoding="utf-8") as f:
                    old = json.load(f)
                old_cookie = old.get("cookies", {})
                # 旧版抖音 Cookie 监控/录播共用
                data["cookies"]["douyin_monitor"] = old_cookie.get("douyin", "")
                data["cookies"]["douyin_record"] = old_cookie.get("douyin", "")
                data["cookies"]["bilibili"] = old_cookie.get("bilibili", "")
                gs = old.get("global_settings", {})
                for k in ("check_interval", "save_folder", "split_size"):
                    if k in gs:
                        data["global_settings"][k] = gs[k]
                old_notif = old.get("notification", {})
                data["notification"]["wxpusher_app_token"] = old_notif.get("wxpusher_app_token", "")
                data["notification"]["wxpusher_uids"] = old_notif.get("wxpusher_uids", [])
        except Exception:
            pass
        for legacy_file, platform in ((LEGACY_BILI_FILE, "bilibili"), (LEGACY_DOUYIN_FILE, "douyin")):
            try:
                if not os.path.exists(legacy_file):
                    continue
                with open(legacy_file, "r", encoding="utf-8") as f:
                    for s in json.load(f):
                        data["streamers"].append({
                            "name": s.get("name", ""),
                            "platform": s.get("platform", platform),
                            "url": s.get("url", ""),
                            "quality": s.get("quality", "原画"),
                            "monitor_enabled": s.get("enabled", True),
                            "record_enabled": s.get("auto_record", False),
                            "group": data["notification"]["default_notification_group"],
                            "last_status": bool(s.get("last_status", False)),
                        })
            except Exception:
                pass
        self._save_json(CONFIG_FILE, data)
        print("[配置] 检测到旧版配置，已迁移到 config/config.json")

    # ---------- 便捷访问 ----------

    @property
    def cookies(self):
        return self.data["cookies"]

    @property
    def notification(self):
        return self.data["notification"]

    @property
    def global_settings(self):
        return self.data["global_settings"]

    @property
    def automations(self):
        return self.data["automations"]

    def get_streamers(self):
        with self._lock:
            return self.data["streamers"]

    def find_streamer(self, name):
        with self._lock:
            for s in self.data["streamers"]:
                if s["name"] == name:
                    return s
        return None

    def add_streamer(self, name, url, platform, quality="原画", extra=None):
        with self._lock:
            for s in self.data["streamers"]:
                if s["name"] == name and s["platform"] == platform:
                    return False  # 已存在
            new_s = {
                "name": name,
                "platform": platform,
                "url": url,
                "quality": quality,
                "monitor_enabled": True,
                "record_enabled": False,
                "group": self.data["notification"]["default_notification_group"],
                "last_status": False,
                "record_start_time": None,
                "quality_meta": {},
            }
            # 抖音归一字段：sec_uid / unique_id / last_web_rid
            for k, v in (extra or {}).items():
                if k in ("sec_uid", "unique_id", "last_web_rid", "uid") and v:
                    new_s[k] = v
            self.data["streamers"].append(new_s)
            self.save()
            return True

    def remove_streamer(self, name):
        with self._lock:
            before = len(self.data["streamers"])
            self.data["streamers"] = [s for s in self.data["streamers"] if s["name"] != name]
            changed = len(self.data["streamers"]) < before
            if changed:
                self.save()
            return changed

    def update_streamer(self, name, updates):
        with self._lock:
            s = self.find_streamer(name)
            if not s:
                return False
            for k, v in updates.items():
                if k in ("name", "platform"):
                    continue  # 主键不允许直接改
                if k in ("url", "quality", "monitor_enabled", "record_enabled", "group",
                         "sec_uid", "unique_id", "last_web_rid", "uid"):
                    s[k] = v
            self.save()
            return True

    def save_streamer_status(self):
        """只把状态类字段刷盘（监控线程每轮调用）"""
        self.save()
