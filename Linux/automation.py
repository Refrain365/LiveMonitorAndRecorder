"""自动化任务：把自定义脚本绑定到主播的开播 / 下播事件。

逻辑移植自 Windows 版 _check_automation（Win 12469）+ _execute_auto_tasks（单工作
线程串行执行，任务级去重）。触发点在 monitor 的状态变化处调用 check_automation。
"""
import logging
import os
import queue
import subprocess
import sys
import threading

logger = logging.getLogger("monitor")


class AutomationRunner:
    def __init__(self, config_manager):
        self.cfg = config_manager
        self._queue = queue.Queue()
        self._running_keys = set()
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True, name="automation-worker")
        self._worker.start()

    def _worker_loop(self):
        while True:
            try:
                script, key = self._queue.get()
                if key in self._running_keys:
                    continue
                with self._lock:
                    self._running_keys.add(key)
                try:
                    self._run_script(script, key)
                finally:
                    with self._lock:
                        self._running_keys.discard(key)
            except Exception as e:
                logger.error(f"[自动化] 任务队列异常: {e}")

    def _run_script(self, script, key):
        if not script or not os.path.exists(script):
            logger.warning(f"[自动化] 脚本不存在: {script}")
            return
        try:
            if script.endswith(".py"):
                cmd = [sys.executable, script]
            elif script.endswith(".sh"):
                cmd = ["bash", script]
            else:
                logger.warning(f"[自动化] 不支持的脚本类型: {script}（仅支持 .py / .sh）")
                return
            logger.info(f"[自动化] 触发脚本: {script}")
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        except Exception as e:
            logger.error(f"[自动化] 脚本执行失败 {script}: {e}")

    def check_automation(self, streamer, trigger):
        """主播状态变化时调用。trigger: "直播中" / "未开播"（复刻 Win 12469 的匹配规则）"""
        for auto in self.cfg.automations:
            if auto.get("streamer") != streamer.get("name"):
                continue
            if auto.get("trigger") != trigger:
                continue
            # 平台隔离校验：automation 记录了平台时需一致
            if auto.get("platform") and auto.get("platform") != streamer.get("platform"):
                continue
            script = auto.get("script", "")
            key = f"{script}:{streamer.get('name')}:{trigger}"
            self._queue.put((script, key))
