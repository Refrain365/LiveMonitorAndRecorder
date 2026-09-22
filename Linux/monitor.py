"""监控与录制核心。

移植自 Windows 版：
  - 监控循环与状态变化触发（Win 11522 _monitor_loop / 8051 _on_streamer_live_status_changed）
  - 2 秒守护轮询（Win 7777 _douyin_record_refresh_loop）
  - 断流重连状态机：冷却 6s / 最多 5 次 / 30s 窗口，仅"自发断开"重连，
    用户手动停止不重连，下播重置计数（Win 7854 _guard_douyin_record）
  - 下播后 ffmpeg -c copy 无损封装 MP4，转码不完整判定（大小差 > 容差不删原文件，
    Win 3731/3841 转码模板 SIZE_TOLERANCE_MB=25）
  - 监控速度模型（Win 10294 _compute_monitor_timings / 10438 定时调速）
  - 休眠时段暂停监控、录制不受影响（Win 10430）

引擎差异（已确认的选型）：抖音不走 aria2，requests 解析直链后由 ffmpeg 直录 FLV；
B站保留 streamlink。
"""
import logging
import logging.handlers
import os
import random
import re
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

import requests

from automation import AutomationRunner
from config import ConfigManager
from douyin_api import (check_bilibili_live, check_douyin_live_streamer,
                        fetch_stream_urls_for_streamer, random_ua)
from notifier import is_in_sleep_period, send_notifications

logger = logging.getLogger("monitor")

SPEED_MULTIPLIER = {1: 1.0, 2: 1.5, 3: 2.0, 4: 3.0, 5: 4.0}
# 重连状态机参数（复刻 Windows）
RECONNECT_COOLDOWN = 6          # 秒
RECONNECT_MAX_ATTEMPTS = 5
RECONNECT_WINDOW = 30           # 自首次重连起的窗口（秒）
GUARD_INTERVAL = 2              # 守护线程轮询间隔（"2秒响应"的核心）
SIZE_TOLERANCE_MB = 25          # MP4 比 FLV 小超过此值视为转码不完整


TZ_CN = timezone(timedelta(hours=8))  # 录制目录按 UTC+8 归档
PLATFORM_DIRS = {"douyin": "抖音", "bilibili": "哔哩哔哩"}


def _now_cn():
    return datetime.now(TZ_CN)


def _safe_filename(name):
    name = name.strip()
    return re.sub(r'[\\/:*?"<>|]', "_", name)[:50]


class RingBufferHandler(logging.Handler):
    """内存日志环，供 Web UI 实时查看"""

    def __init__(self, capacity=400):
        super().__init__()
        self.buffer = deque(maxlen=capacity)

    def emit(self, record):
        try:
            self.buffer.append(self.format(record))
        except Exception:
            pass


class RecordTask:
    """一个主播的一次录制会话（跨断流重连持续存在，直到下播收尾）"""

    def __init__(self, streamer):
        self.streamer = streamer
        self.platform = streamer.get("platform", "douyin")
        self.quality = streamer.get("quality", "原画")
        self.process = None          # ffmpeg / streamlink 子进程
        self.state = "抓流中"        # 抓流中 / 录制中 / 等待重连 / 转码中 / 失败
        self.user_stopped = False
        self.reconnect_attempts = 0
        self.first_reconnect_time = None
        self.next_retry_time = 0.0
        self.started_at = None       # ffmpeg 实际开录时间
        self.output_base = ""        # 无扩展名输出路径
        self.raw_ext = ".flv"        # 抖音=flv，B站=ts
        self.stream_url = ""
        self.is_hls = False
        self.error = ""

    @property
    def is_alive(self):
        return self.process is not None and self.process.poll() is None


class LiveMonitor:
    def __init__(self, config_manager: ConfigManager):
        self.cfg = config_manager
        self.automation = AutomationRunner(config_manager)
        self.tasks = {}              # 主播名 -> RecordTask
        self.postprocessing = []     # [{name, thread}] 转码收尾线程
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self.started_at = datetime.now()
        self.log_ring = RingBufferHandler()
        self._setup_logging()

    # ---------- 日志 ----------

    def _setup_logging(self):
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        ring = self.log_ring
        ring.setFormatter(fmt)
        root.handlers.clear()
        root.addHandler(ring)
        # 按天分割日志文件（复刻 Windows enable_daily_log_split 行为）
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        fh = logging.handlers.TimedRotatingFileHandler(
            os.path.join(log_dir, "monitor.log"), when="midnight", backupCount=30, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)

    def get_log_tail(self, lines=200):
        buf = list(self.log_ring.buffer)
        return buf[-lines:]

    # ---------- 监控速度模型（复刻 Win 10294/10438） ----------

    def get_current_speed_level(self):
        level = self.cfg.global_settings.get("monitor_speed_level", 1)
        for p in self.cfg.global_settings.get("scheduled_speed_periods", []) or []:
            try:
                now = datetime.now()
                cur = now.hour * 60 + now.minute
                sh, sm = map(int, p["start"].split(":"))
                eh, em = map(int, p["end"].split(":"))
                s, e = sh * 60 + sm, eh * 60 + em
                if (s <= e and s <= cur <= e) or (s > e and (cur >= s or cur <= e)):
                    level = int(p.get("level", level))
            except Exception:
                pass
        return level

    def compute_monitor_timings(self, stream_count):
        mult = SPEED_MULTIPLIER.get(self.get_current_speed_level(), 1.0)
        every_sleep = max(3.5, 4 + 0.5 * min(stream_count, 10)) * mult
        total_cycle = max(5, stream_count * 3) * mult / 2
        return every_sleep, total_cycle

    # ---------- 进程生命周期 ----------

    def start(self):
        threading.Thread(target=self.monitor_loop, daemon=True, name="monitor").start()
        threading.Thread(target=self.guard_loop, daemon=True, name="guard").start()
        logger.info("🟢 监控与守护线程已启动")

    def shutdown(self):
        self._stop_event.set()

    # ---------- 监控主循环 ----------

    def monitor_loop(self):
        while not self._stop_event.is_set():
            try:
                if is_in_sleep_period(self.cfg.data):
                    self._sleep_chunk(60)
                    continue
                streamers = [s for s in self.cfg.get_streamers() if s.get("monitor_enabled", True)]
                every_sleep, total_cycle = self.compute_monitor_timings(len(streamers))
                status_changed = False
                for s in streamers:
                    if self._stop_event.is_set():
                        break
                    prev = s.get("last_status", False)
                    if s.get("platform") == "bilibili":
                        room_id = self._bili_room_id(s)
                        is_live, title = check_bilibili_live(room_id)
                        if is_live is None:
                            continue  # 请求失败保持旧状态
                        s["_title"] = title
                    else:
                        rid_before = s.get("last_web_rid")
                        is_live = check_douyin_live_streamer(s, self.cfg.cookies.get("douyin_monitor", ""))
                        if s.get("last_web_rid") != rid_before:
                            status_changed = True  # 房间号更新了（重开直播），需要持久化
                        if is_live is None:
                            continue
                    if is_live and not prev:
                        logger.info(f"🔴 {s['name']} 开播")
                        status_changed = True
                        s["last_status"] = True
                        send_notifications(self.cfg.data, "🔴 开播提醒",
                                           f"主播【{s['name']}】已开播", streamer=s)
                        self.automation.check_automation(s, "直播中")
                        if s.get("record_enabled", False):
                            self.start_recording(s)
                    elif not is_live and prev:
                        logger.info(f"⚪ {s['name']} 下播")
                        status_changed = True
                        s["last_status"] = False
                        self.automation.check_automation(s, "未开播")
                    # 直播中但任务已终结（如重连放弃后主播仍播）→ 重新拉起录制
                    if is_live and s.get("record_enabled") and not self._has_active_task(s["name"]):
                        self.start_recording(s)
                    self._sleep_chunk(random.uniform(1.0, 3.0) if s.get("platform") == "bilibili" else every_sleep)
                if status_changed:
                    self.cfg.save_streamer_status()
                self._sleep_chunk(total_cycle)
            except Exception as e:
                logger.error(f"[监控] 循环异常: {e}")
                self._sleep_chunk(10)

    @staticmethod
    def _sleep_chunk(seconds):
        """长睡眠按 1~2.5s 分片，便于及时响应停止（复刻 Windows 分片方式）"""
        end = time.time() + max(0, seconds)
        while time.time() < end:
            time.sleep(min(2.5, max(0.2, end - time.time())))

    @staticmethod
    def _bili_room_id(streamer):
        url = str(streamer.get("url", "")).strip()
        m = re.search(r'(?:live\.bilibili\.com/)?(\d+)', url.split("?")[0])
        return m.group(1) if m else url

    def _has_active_task(self, name):
        with self._lock:
            t = self.tasks.get(name)
            # 失败态不算活跃（但失败态主播下播时才清理，避免无限重启）
            return t is not None and t.state not in ("失败",)

    # ---------- 录制 ----------

    def _save_dir(self, streamer):
        """保存目录：<save_folder>/<抖音|哔哩哔哩>/<主播名>/<YYYY-MM-DD(UTC+8)>/
        同一天多次直播的录制文件都归档到同一个日期文件夹。"""
        folder = self.cfg.global_settings.get("save_folder", "Recordings")
        platform_dir = PLATFORM_DIRS.get(streamer.get("platform"), streamer.get("platform", "抖音"))
        day = _now_cn().strftime("%Y-%m-%d")
        path = os.path.join(folder, platform_dir, _safe_filename(streamer["name"]), day)
        os.makedirs(path, exist_ok=True)
        return path

    def start_recording(self, streamer):
        with self._lock:
            if streamer["name"] in self.tasks:
                return
            self.tasks[streamer["name"]] = RecordTask(streamer)
        logger.info(f"🚀 开始录制: {streamer['name']}（{streamer.get('quality', '原画')}）")

    def stop_recording(self, name):
        """Web UI 手动停止：标记 user_stopped，守护线程负责收尾（不重连）"""
        with self._lock:
            t = self.tasks.get(name)
        if not t:
            return False
        t.user_stopped = True
        if t.is_alive:
            try:
                t.process.terminate()
            except Exception:
                pass
        logger.info(f"⏹ 手动停止录制: {name}")
        return True

    def _build_douyin_cmd(self, task, streamer):
        cookie = self.cfg.cookies.get("douyin_record", "")
        from douyin_api import inject_quality_cookie
        cookie = inject_quality_cookie(cookie, task.quality)
        headers = f"Referer: https://live.douyin.com/{streamer.get('url', '')}\r\nCookie: {cookie}\r\n"
        cmd = ["ffmpeg", "-loglevel", "error", "-y",
               "-user_agent", random_ua(),
               "-headers", headers]
        if task.is_hls:
            cmd += ["-protocol_whitelist", "file,http,https,tcp,tls"]
        cmd += ["-i", task.stream_url,
                "-c", "copy", "-f", "flv",
                task.output_base + ".flv"]
        return cmd

    def _build_bili_cmd(self, task, streamer):
        url = streamer.get("url", "").split("?")[0]
        quality = streamer.get("quality", "原画")
        # B站画质沿用 streamlink 档位；房间实际档位名不固定（有的只有 hls/worst/best），
        # 用逗号回退列表：找不到具体分辨率时自动退到 best，避免进程秒退
        sl_quality = {
            "原画": "best",
            "蓝光": "best",
            "超清": "1080p,best",
            "高清": "720p,best",
            "标清": "480p,best",
        }.get(quality, "best")
        cmd = ["streamlink", "--force", url, sl_quality, "-o", task.output_base + ".ts"]
        cookie = self.cfg.cookies.get("bilibili", "")
        if cookie:
            cmd += ["--http-header", f"Cookie={cookie}"]
        split_gb = self.cfg.global_settings.get("split_size", 0)
        if split_gb:
            cmd += ["--max-file-size", str(int(split_gb * 1024)) + "M"]
        return cmd

    def _launch_process(self, task, streamer):
        """抓直链（抖音）并启动录制进程。成功返回 True。"""
        if task.platform == "douyin":
            res = fetch_stream_urls_for_streamer(
                streamer,
                self.cfg.cookies.get("douyin_monitor", ""),
                self.cfg.cookies.get("douyin_record", ""),
                task.quality)
            if not res["url"]:
                task.error = "未获取到直播流直链"
                return False
            task.stream_url = res["url"]
            task.is_hls = res["is_hls"]
            task.output_base = os.path.join(self._save_dir(streamer), _now_cn().strftime("%H-%M-%S"))
            task.raw_ext = ".flv"
            cmd = self._build_douyin_cmd(task, streamer)
        else:
            task.output_base = os.path.join(self._save_dir(streamer), _now_cn().strftime("%H-%M-%S"))
            task.raw_ext = ".ts"
            cmd = self._build_bili_cmd(task, streamer)
        try:
            task.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                            start_new_session=True)
            task.state = "录制中"
            task.started_at = _now_cn()
            task.error = ""
            return True
        except FileNotFoundError as e:
            task.error = f"找不到可执行程序（请确认 ffmpeg/streamlink 已安装）: {e}"
            logger.error(f"[录制] {task.error}")
            return False

    # ---------- 守护线程（2 秒轮询，复刻 Win 7777/7854） ----------

    def guard_loop(self):
        while not self._stop_event.is_set():
            time.sleep(GUARD_INTERVAL)
            try:
                with self._lock:
                    tasks = dict(self.tasks)
                for name, task in list(tasks.items()):
                    self._guard_task(name, task)
                self._collect_finished_postprocessing()
            except Exception as e:
                logger.error(f"[守护] 轮询异常: {e}")

    def _guard_task(self, name, task):
        if task.state == "转码中":
            return
        # 用户手动停止：杀进程收尾
        if task.user_stopped:
            if task.is_alive:
                try:
                    task.process.kill()
                except Exception:
                    pass
                return  # 等下一轮确认进程退出
            self._finalize(name, task)
            return

        if task.is_alive:
            return  # 正常录制中

        # 进程不在运行：区分「还没起进程」与「已退出」
        streamer = task.streamer
        # 续录/重连只看主播是否仍在播；「自动录制」开关只决定是否自动开始新会话
        still_live = bool(streamer.get("last_status", False))

        if task.process is None or task.state in ("抓流中", "等待重连", "失败"):
            now = time.time()
            if now < task.next_retry_time:
                task.state = "等待重连" if task.reconnect_attempts else "抓流中"
                return
            if task.reconnect_attempts >= RECONNECT_MAX_ATTEMPTS:
                # 30s 窗口内重试耗尽 → 放弃守护，等下播清理（复刻 Windows 行为）
                if task.state != "失败":
                    logger.warning(f"[守护] {name} 重连 {RECONNECT_MAX_ATTEMPTS} 次失败，放弃（等下播后重置）")
                    task.state = "失败"
                return
            if task.first_reconnect_time and now - task.first_reconnect_time > RECONNECT_WINDOW:
                if task.state != "失败":
                    logger.warning(f"[守护] {name} 超出 {RECONNECT_WINDOW}s 重连窗口，放弃")
                    task.state = "失败"
                return
            if task.reconnect_attempts == 0:
                task.first_reconnect_time = now
            task.reconnect_attempts += 1
            task.next_retry_time = now + RECONNECT_COOLDOWN
            task.state = "抓流中"
            if not still_live:
                # 主播已下播：不再重试，直接收尾
                self._finalize(name, task)
                return
            logger.info(f"[守护] {name} 第 {task.reconnect_attempts}/{RECONNECT_MAX_ATTEMPTS} 次尝试抓流开录")
            if self._launch_process(task, streamer):
                task.reconnect_attempts = 0
                task.first_reconnect_time = None
            else:
                logger.warning(f"[守护] {name} 抓流失败: {task.error}")
            return

        # 进程已退出且非手动停止
        if still_live:
            # 自发断开且主播仍在播 → 走重连（冷却 6s）
            logger.warning(f"[守护] {name} 录制进程意外退出（疑似断流），准备重连")
            task.process = None
            task.state = "等待重连"
            task.next_retry_time = time.time() + RECONNECT_COOLDOWN
            if task.first_reconnect_time is None:
                task.first_reconnect_time = time.time()
        else:
            self._finalize(name, task)

    # ---------- 收尾：无损封装 MP4（复刻 Win 转码模板） ----------

    def _finalize(self, name, task):
        task.state = "转码中"
        raw_path = task.output_base + task.raw_ext if task.output_base else ""
        thread = threading.Thread(target=self._postprocess, args=(name, task, raw_path),
                                  daemon=True, name=f"post-{name}")
        self.postprocessing.append({"name": name, "thread": thread})
        thread.start()

    def _collect_finished_postprocessing(self):
        for item in list(self.postprocessing):
            if not item["thread"].is_alive():
                self.postprocessing.remove(item)
                with self._lock:
                    self.tasks.pop(item["name"], None)

    def _postprocess(self, name, task, raw_path):
        try:
            if not raw_path or not os.path.exists(raw_path):
                with self._lock:
                    self.tasks.pop(name, None)
                return
            mp4_path = raw_path + ".mp4"
            if os.path.exists(mp4_path):
                os.remove(mp4_path)
            r = subprocess.run(["ffmpeg", "-i", raw_path, "-c", "copy", mp4_path, "-y", "-loglevel", "error"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if r.returncode == 0 and os.path.exists(mp4_path):
                raw_mb = os.path.getsize(raw_path) / 1024 / 1024
                mp4_mb = os.path.getsize(mp4_path) / 1024 / 1024
                keep = self.cfg.global_settings.get("keep_flv", False)
                if not keep and abs(raw_mb - mp4_mb) <= self.cfg.global_settings.get("size_tolerance_mb", SIZE_TOLERANCE_MB):
                    os.remove(raw_path)
                    logger.info(f"📦 {name} 封装完成: {os.path.basename(mp4_path)}（原文件已删除）")
                elif not keep:
                    logger.warning(f"📦 {name} 封装完成但大小差过大（{raw_mb:.0f}MB → {mp4_mb:.0f}MB），保留原文件待检查")
                else:
                    logger.info(f"📦 {name} 封装完成: {os.path.basename(mp4_path)}（保留原文件）")
            else:
                logger.error(f"[转码] {name} MP4 封装失败，保留原始文件")
        except Exception as e:
            logger.error(f"[转码] {name} 收尾异常: {e}")
        finally:
            streamer = task.streamer
            if not streamer.get("last_status", False):
                with self._lock:
                    self.tasks.pop(name, None)

    # ---------- 状态输出（供 Web UI） ----------

    def get_status(self):
        result = []
        with self._lock:
            for s in self.cfg.get_streamers():
                task = self.tasks.get(s["name"])
                item = {
                    "name": s["name"],
                    "platform": s.get("platform"),
                    "url": s.get("url"),
                    "quality": s.get("quality"),
                    "monitor_enabled": s.get("monitor_enabled", True),
                    "record_enabled": s.get("record_enabled", False),
                    "group": s.get("group", ""),
                    "live": bool(s.get("last_status", False)),
                    "title": s.get("_title", ""),
                    "recording": bool(task and task.is_alive),
                    "record_state": task.state if task else "",
                    "record_error": task.error if task else "",
                    "record_started_at": task.started_at.strftime("%Y-%m-%d %H:%M:%S") if task and task.started_at else "",
                    "postprocessing": bool(task and task.state == "转码中"),
                }
                result.append(item)
        return {
            "started_at": self.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "speed_level": self.get_current_speed_level(),
            "sleeping": is_in_sleep_period(self.cfg.data),
            "streamers": result,
        }


if __name__ == "__main__":
    # 独立运行（无 Web UI，供调试）
    m = LiveMonitor(ConfigManager())
    m.start()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
