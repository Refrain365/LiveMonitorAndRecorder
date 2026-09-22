"""通知模块：WxPusher / 企业微信机器人、通知组、勿扰时段。

逻辑移植自 Windows 版：
  - WxPusher payload（Win 11661 send_wxpusher_notification）
  - 企业微信 payload（Win 11686）
  - 通知组归组（Win 11708 send_notifications）
  - 勿扰时段跨天判断（Win 10400 _is_in_time_period / 10422 is_in_do_not_disturb_period）
"""
import logging
from datetime import datetime

import requests

logger = logging.getLogger("monitor")


def _is_in_time_period(start, end, now=None):
    """HH:MM 起止时间判断，支持跨天时段（复刻 Win 10400）"""
    try:
        now = now or datetime.now()
        cur = now.hour * 60 + now.minute
        sh, sm = map(int, start.split(":"))
        eh, em = map(int, end.split(":"))
        s, e = sh * 60 + sm, eh * 60 + em
        if s <= e:
            return s <= cur <= e
        return cur >= s or cur <= e  # 跨天，如 23:00-07:00
    except Exception:
        return False


def is_in_do_not_disturb(cfg_data):
    """命中勿扰时段则通知直接屏蔽（复刻 Win 10422）"""
    periods = cfg_data.get("notification", {}).get("do_not_disturb_periods", []) or []
    for p in periods:
        if _is_in_time_period(p.get("start", ""), p.get("end", "")):
            return True
    return False


def is_in_sleep_period(cfg_data):
    """休眠时段：监控循环暂停，录制不受影响（复刻 Win 10430）"""
    periods = cfg_data.get("global_settings", {}).get("sleep_periods", []) or []
    for p in periods:
        if _is_in_time_period(p.get("start", ""), p.get("end", "")):
            return True
    return False


def send_wxpusher(app_token, uids, title, content):
    payload = {
        "appToken": app_token,
        "content": content,
        "summary": title,
        "contentType": 1,
        "uids": uids,
    }
    try:
        resp = requests.post("https://wxpusher.zjiecode.com/api/send/message",
                             json=payload, timeout=10).json()
        if resp.get("code") == 1000:
            logger.info(f"[通知] WxPusher 推送成功: {title}")
        else:
            logger.warning(f"[通知] WxPusher 推送失败: {resp}")
    except Exception as e:
        logger.error(f"[通知] WxPusher 推送异常: {e}")


def send_wecom(webhook_url, title, content):
    payload = {"msgtype": "text", "text": {"content": f"{title}\n\n{content}"}}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10).json()
        if resp.get("errcode") == 0:
            logger.info(f"[通知] 企业微信推送成功: {title}")
        else:
            logger.warning(f"[通知] 企业微信推送失败: {resp}")
    except Exception as e:
        logger.error(f"[通知] 企业微信推送异常: {e}")


def send_notifications(cfg_data, title, content, streamer=None):
    """按通知组归组推送（复刻 Win 11708）：
    全局开关优先于组设置；主播未归组回退默认行为 wxpusher=True, wecom=False。
    """
    notif = cfg_data.get("notification", {})
    if is_in_do_not_disturb(cfg_data):
        logger.info(f"[通知] 当前处于勿扰时段，已屏蔽: {title}")
        return

    groups = notif.get("notification_groups", []) or []
    group = None
    if streamer:
        gname = streamer.get("group", "")
        group = next((g for g in groups if g.get("name") == gname), None)
    if group is None:
        gname = notif.get("default_notification_group", "")
        group = next((g for g in groups if g.get("name") == gname), None)
    if group is None:
        methods = {"wxpusher": True, "wecom": False}
    else:
        methods = group.get("notify_methods", {})

    content_full = f"{content}\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    if methods.get("wxpusher") and notif.get("wxpusher_enabled", True):
        token, uids = notif.get("wxpusher_app_token", ""), notif.get("wxpusher_uids", [])
        if token and uids:
            send_wxpusher(token, uids, title, content_full)
    if methods.get("wecom") and notif.get("wecom_enabled", False):
        webhook = notif.get("wecom_webhook", "")
        if webhook:
            send_wecom(webhook, title, content_full)
