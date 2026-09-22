"""抖音 / B站 平台 API：开播检测、直播流直链解析、画质映射、画质 Cookie 注入。

直链解析逻辑移植自 Windows 版 MonitorAndRecorder.py：
  - 页面 RENDER_DATA 解析（Win 8285 _fetch_stream_urls_via_requests）
  - enter 接口（Win 8429 _fetch_enter_interface + 8508 _parse_stream_urls）
  - 画质 Cookie 注入（Win 5604 modify_cookie_with_quality）
  - B站主播信息 4 接口兜底链（Win 5275 fetch_bili_user_info）
全部为纯 requests 实现，无浏览器依赖。
"""
import json
import random
import re
from urllib.parse import unquote

import requests

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36 EdgA/130.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
]


def random_ua():
    return random.choice(UA_LIST)


# 画质档位 → enter 接口键 / Cookie 注入值（Win 8202 _get_quality_suffix / 8529 quality_key_map）
QUALITY_KEY_MAP = {
    "蓝光": "FULL_HD1",
    "超清": "HD1",
    "高清": "SD1",
    "标清": "SD2",
}
# 原画走 stream_data.data.origin.main.flv，Cookie 注入值用 or4
QUALITY_COOKIE_CODE = {
    "原画": "or4",
    "蓝光": "uhd",
    "超清": "hd",
    "高清": "ld",
    "标清": "sd",
}
QUALITY_SUFFIX = {"原画": ("or4", "max"), "蓝光": ("uhd",), "超清": ("hd",), "高清": ("ld",), "标清": ("sd",)}


def inject_quality_cookie(cookie_str, quality):
    """在原始 Cookie 上注入画质参数（复刻 Win 5604，请求时动态注入、不落盘）"""
    cookie_dict = {}
    if cookie_str:
        for pair in cookie_str.split(";"):
            pair = pair.strip()
            if "=" in pair:
                key, value = pair.split("=", 1)
                cookie_dict[key.strip()] = value.strip()
    code = QUALITY_COOKIE_CODE.get(quality, "or4")
    cookie_dict["live_local_quality"] = code
    cookie_dict["webcast_local_quality"] = code
    return "; ".join(f"{k}={v}" for k, v in cookie_dict.items())


def _clean_url(url):
    return url.replace("\\u0026", "&").rstrip("\\")


def _recursive_find(obj, key):
    """在嵌套 dict/list 里递归搜索指定 key 的值（复刻 Win 8492）"""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _recursive_find(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _recursive_find(v, key)
            if r is not None:
                return r
    return None


def _parse_stream_data(stream_data_str):
    """stream_data 是 JSON 字符串（可能双重编码），解析出 origin.main.flv（Win 8550）"""
    try:
        stream_data = json.loads(stream_data_str)
        if isinstance(stream_data, str):
            stream_data = json.loads(stream_data)
        return _clean_url(stream_data.get("data", {}).get("origin", {}).get("main", {}).get("flv", "") or "")
    except Exception:
        return ""


def _extract_render_data(page_text):
    """策略1a：从页面 RENDER_DATA 提取各画质 FLV（复刻 Win 策略1a）"""
    result = {}
    m = re.search(r'id="RENDER_DATA"[^>]*>([^<]+)<', page_text)
    if not m:
        return result
    raw = m.group(1)
    # Windows 最多 unquote 3 次
    decoded = raw
    for _ in range(3):
        try:
            new = unquote(decoded)
        except Exception:
            break
        if new == decoded:
            break
        decoded = new
    try:
        obj = json.loads(decoded)
    except Exception:
        return result
    flv_pull = _recursive_find(obj, "flv_pull_url")
    if isinstance(flv_pull, dict):
        for quality, key in QUALITY_KEY_MAP.items():
            url = flv_pull.get(key, "")
            if url:
                result[quality] = _clean_url(url)
    stream_data_str = _recursive_find(obj, "stream_data")
    if isinstance(stream_data_str, str) and stream_data_str:
        origin = _parse_stream_data(stream_data_str)
        if origin:
            result["原画"] = origin
    return result


def extract_web_rid(page_text):
    """从页面解析 web_rid（Win 8437）"""
    m = re.search(r'"web_rid"\s*:\s*"(\d+)"', page_text)
    if m:
        return m.group(1)
    m = re.search(r'"room_id"\s*:\s*(\d+)', page_text)
    if m:
        return m.group(1)
    return ""


def _parse_enter_response(resp_body):
    """解析 enter 接口响应，提取各画质 flv 链接（复刻 Win 8508）"""
    result = {}
    try:
        data = json.loads(resp_body) if isinstance(resp_body, str) else resp_body
        data_list = data.get("data", {}).get("data", [])
        if not data_list:
            return result
        room_data = data_list[0]
        stream_url = room_data.get("stream_url", {})
        flv_pull = stream_url.get("flv_pull_url", {})
        for quality, key in QUALITY_KEY_MAP.items():
            url = flv_pull.get(key, "")
            if url:
                result[quality] = _clean_url(url)
        pull_data = stream_url.get("live_core_sdk_data", {}).get("pull_data", {})
        stream_data_str = pull_data.get("stream_data", "")
        if not stream_data_str:
            m = re.search(r'"stream_data"\s*:\s*"((?:[^"\\]|\\.)*)"', resp_body if isinstance(resp_body, str) else json.dumps(data, ensure_ascii=False))
            if m:
                stream_data_str = m.group(1)
        if stream_data_str:
            origin = _parse_stream_data(stream_data_str)
            if origin:
                result["原画"] = origin
        if "原画" not in result:
            m = re.search(r'"origin"\s*:\s*\{[^}]*?"main"\s*:\s*\{[^}]*?"flv"\s*:\s*"(http[^"]+?\.flv[^"]*?)"',
                          resp_body if isinstance(resp_body, str) else json.dumps(data, ensure_ascii=False))
            if m:
                result["原画"] = _clean_url(m.group(1))
        if "原画" not in result:
            hls = stream_url.get("hls_pull_url", "")
            if hls:
                result["原画"] = _clean_url(hls)
    except Exception:
        pass
    return result


def _build_enter_url(web_rid):
    return (
        "https://live.douyin.com/webcast/room/web/enter/"
        f"?aid=6383&app_name=douyin_web&live_id=1&device_platform=web"
        f"&language=zh-CN&enter_from=web_live&cookie_enabled=true"
        f"&browser_language=zh-CN&browser_platform=Win32&browser_name=Edge"
        f"&browser_version=150.0.0.0&web_rid={web_rid}&room_id_str={web_rid}"
        f"&enter_source=&is_need_double_stream=false"
    )


def _request_enter(web_rid, headers):
    """请求 enter 接口，成功返回解析后的 dict，失败返回 None。"""
    try:
        resp = requests.get(_build_enter_url(web_rid), headers=headers, timeout=10)
        resp.encoding = "utf-8"
        data = resp.json()
        if "data" not in data:
            return None
        return data
    except Exception:
        return None


def _room_status_from_enter(data):
    """从 enter 响应提取权威开播状态：room.status 2=直播中，4=未播（实测确认）。
    拿不到权威状态返回 None。"""
    try:
        data_list = data.get("data", {}).get("data", [])
        if data_list and isinstance(data_list[0].get("status"), int):
            return data_list[0]["status"] == 2
    except Exception:
        pass
    return None


def _fetch_enter_interface(page_text, headers):
    """请求 enter 接口获取最新带签名的直链（复刻 Win 8429）。失败返回 {}。"""
    web_rid = extract_web_rid(page_text)
    if not web_rid:
        return {}
    data = _request_enter(web_rid, headers)
    if data is None:
        return {}
    return _parse_enter_response(data)


def _regex_fallback_urls(page_text):
    """策略1b：正则扫全页 FLV 直链，按后缀分档（复刻 Win 策略1b）"""
    result = {}
    for m in re.finditer(r'(https?://[^"\'\\\s]+?\.flv[^"\'\\\s]*)', page_text):
        url = _clean_url(m.group(1))
        if "only_audio=1" in url:
            continue
        for quality, suffixes in QUALITY_SUFFIX.items():
            if quality in result:
                continue
            for suf in suffixes:
                if re.search(rf"_{suf}\.flv", url):
                    result[quality] = url
                    break
    return result


def check_douyin_live(douyin_id, monitor_cookie):
    """抖音开播检测（按房间号）。True/False；None=请求失败（保持旧状态）"""
    data = _request_enter(str(douyin_id), {
        "User-Agent": random_ua(), "Cookie": monitor_cookie or "",
        "Referer": "https://live.douyin.com/"})
    if data is not None:
        status = _room_status_from_enter(data)
        if status is not None:
            return status
    # 兜底：页面正则（老页面形态）
    headers = {"User-Agent": random_ua(), "Cookie": monitor_cookie or "", "Referer": "https://live.douyin.com/"}
    try:
        resp = requests.get(f"https://live.douyin.com/{douyin_id}", headers=headers, timeout=10)
        m = re.search(r'"live_status"\s*:\s*(\d)', resp.text)
        if m:
            return m.group(1) == "1"
        return "直播中" in resp.text
    except Exception:
        return None


# ---------- 多形式输入归一（直播间链接 / 主页链接 / 抖音号） ----------

SEC_UID_RE = r"MS4wLjABAAAA[A-Za-z0-9_-]+"


def classify_douyin_target(raw):
    """把用户输入归类：web_rid（直播间链接/房间号）、sec_uid（主页链接）、
    unique_id（抖音号/@handle）。返回 {"type": ..., "id": ...}。"""
    s = str(raw).strip()
    m = re.search(r'live\.douyin\.com/(\d+)', s)
    if m:
        return {"type": "web_rid", "id": m.group(1)}
    if re.fullmatch(r"\d{6,}", s):
        return {"type": "web_rid", "id": s}
    m = re.search(r'douyin\.com/user/(' + SEC_UID_RE + r")", s)
    if m:
        return {"type": "sec_uid", "id": m.group(1)}
    m = re.search(r'douyin\.com/@([A-Za-z0-9_.-]+)', s)
    if m:
        return {"type": "unique_id", "id": m.group(1)}
    s = s.lstrip("@")
    if re.fullmatch(SEC_UID_RE, s):
        return {"type": "sec_uid", "id": s}
    return {"type": "unique_id", "id": s}


def _share_user_info(sec_uid, monitor_cookie=""):
    """iesdouyin 分享页（SSR）：sec_uid → 昵称 / 抖音号。失败返回 {}。
    实测需要携带 Cookie（哪怕仅 ttwid）才渲染用户数据。"""
    mobile_ua = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                 "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
    try:
        r = requests.get(f"https://www.iesdouyin.com/share/user/{sec_uid}",
                         headers={"User-Agent": mobile_ua, "Cookie": monitor_cookie or ""}, timeout=10)
        r.encoding = "utf-8"
        m = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>', r.text, re.S)
        if not m:
            return {}
        data = json.loads(m.group(1))
        text = json.dumps(data, ensure_ascii=False)
        out = {}
        mm = re.search(r'"nickname"\s*:\s*"([^"]{1,60})"', text)
        if mm:
            out["nickname"] = mm.group(1)
        mm = re.search(r'"unique_id"\s*:\s*"([^"]{1,60})"', text)
        if mm:
            out["unique_id"] = mm.group(1)
        mm = re.search(r'"secUid"\s*:\s*"(' + SEC_UID_RE + r')"', text)
        if mm:
            out["sec_uid"] = mm.group(1)
        return out
    except Exception:
        return {}


def _user_page_web_rid(sec_uid, monitor_cookie):
    """www.douyin.com/user/{sec_uid}（登录态 SSR 直播卡片）→ 当前直播间 web_rid。
    主播未播或页面异常返回 ""。"""
    headers = {"User-Agent": random_ua(), "Cookie": monitor_cookie or "",
               "Referer": "https://www.douyin.com/"}
    try:
        r = requests.get(f"https://www.douyin.com/user/{sec_uid}", headers=headers, timeout=10)
        r.encoding = "utf-8"
        t = r.text
        # PACE 水合数据里的转义形态 \"owner\":{\"web_rid\":\"123\"} 优先
        m = (re.search(r'web_rid\\+"\s*:\s*\\+"(\d{6,})', t)
             or re.search(r'"web_rid"\s*:\s*"(\d{6,})"', t)
             or re.search(r'live\.douyin\.com/(\d{6,})', t))
        return m.group(1) if m else ""
    except Exception:
        return ""


def resolve_douyin_streamer(raw, monitor_cookie):
    """添加主播时把任意输入归一为 {name, sec_uid, unique_id, last_web_rid}。

    - 直播间链接/房间号：enter 接口拿 owner 的 sec_uid + 昵称（需主播在播）
    - 主页链接：URL 自带 sec_uid，分享页补昵称
    - 抖音号/@handle：抖音无公开解析接口，明确报错引导用户改用前两种
    """
    t = classify_douyin_target(raw)
    headers = {"User-Agent": random_ua(), "Cookie": monitor_cookie or "",
               "Referer": "https://live.douyin.com/"}
    if t["type"] == "web_rid":
        data = _request_enter(t["id"], headers)
        room = ((data or {}).get("data", {}) or {}).get("data", [None])
        room = room[0] if room else None
        owner = (room or {}).get("owner", {}) if room else {}
        return {
            "name": owner.get("nickname", ""),
            "sec_uid": owner.get("sec_uid", ""),
            "unique_id": owner.get("unique_id", "") or "",
            "last_web_rid": t["id"],
        }
    if t["type"] == "sec_uid":
        info = _share_user_info(t["id"], monitor_cookie)
        return {
            "name": info.get("nickname", ""),
            "sec_uid": t["id"],
            "unique_id": info.get("unique_id", ""),
            "last_web_rid": "",
        }
    raise ValueError(
        "无法通过抖音号/@handle 直接解析（抖音接口限制）。"
        "请粘贴主播的【直播间链接】（开播时）或【主页链接】（douyin.com/user/...）")


def get_douyin_web_rid(streamer, monitor_cookie):
    """获取主播当前直播间的 web_rid（不保证在播）。

    优先级：URL 中直含房间号 > 上次缓存的 last_web_rid > 用户页实时解析。
    解析到新房间号时会写回 streamer["last_web_rid"]（由调用方负责持久化）。
    找不到返回 ""。
    """
    t = classify_douyin_target(streamer.get("url", ""))
    if t["type"] == "web_rid":
        return t["id"]
    cached = str(streamer.get("last_web_rid", "") or "")
    if cached:
        return cached
    sec_uid = streamer.get("sec_uid", "")
    if not sec_uid and t["type"] == "sec_uid":
        sec_uid = t["id"]
    if not sec_uid:
        return ""
    rid = _user_page_web_rid(sec_uid, monitor_cookie)
    if rid:
        streamer["last_web_rid"] = rid
    return rid


def check_douyin_live_streamer(streamer, monitor_cookie):
    """按主播档案检测开播（支持三种输入形式）。

    流程：现有 web_rid 查 enter 权威状态 → 状态为“未播”时尝试用户页发现新房间号
    （主播重开直播后房间号可能变化）→ 用新房间号复查。
    True/False；None=网络失败（保持旧状态）。
    """
    headers = {"User-Agent": random_ua(), "Cookie": monitor_cookie or "",
               "Referer": "https://live.douyin.com/"}
    rid = ""
    t = classify_douyin_target(streamer.get("url", ""))
    if t["type"] == "web_rid":
        rid = t["id"]
    else:
        rid = str(streamer.get("last_web_rid", "") or "")

    status = None
    if rid:
        data = _request_enter(rid, headers)
        if data is None:
            return None  # 网络失败，保持旧状态
        status = _room_status_from_enter(data)
        if status is True:
            return True

    # 缓存房间未播/无缓存：用户页发现新房间号（主页链接形式的主播重开后房间号会变）
    if t["type"] != "web_rid":
        sec_uid = streamer.get("sec_uid", "") or (t["id"] if t["type"] == "sec_uid" else "")
        if sec_uid:
            new_rid = _user_page_web_rid(sec_uid, monitor_cookie)
            if new_rid and new_rid != rid:
                streamer["last_web_rid"] = new_rid
                data = _request_enter(new_rid, headers)
                if data is not None:
                    st2 = _room_status_from_enter(data)
                    if st2 is not None:
                        return st2
    if status is not None:
        return status
    # 没有任何房间号可用（如纯抖音号形式）→ 视为未播（无法监控，添加时会引导）
    return False


def fetch_stream_urls_by_rid(web_rid, record_cookie, quality="原画"):
    """按 web_rid 抓直链：enter 接口优先，页面解析兜底。"""
    headers = {
        "User-Agent": random_ua(),
        "Referer": f"https://live.douyin.com/{web_rid}",
        "Cookie": inject_quality_cookie(record_cookie, quality),
    }
    all_urls = {}
    data = _request_enter(str(web_rid), headers)
    if data is not None:
        all_urls.update(_parse_enter_response(data))

    if not all_urls:
        # enter 失败：抓页面解析（RENDER_DATA / web_rid→enter / 正则兜底）
        try:
            resp = requests.get(f"https://live.douyin.com/{web_rid}", headers=headers, timeout=10)
            resp.encoding = "utf-8"
            page_text = resp.text
        except Exception:
            return {"url": "", "is_hls": False, "all": {}}
        all_urls.update(_extract_render_data(page_text))
        for q, u in _fetch_enter_interface(page_text, headers).items():
            all_urls.setdefault(q, u)
        for q, u in _regex_fallback_urls(page_text).items():
            all_urls.setdefault(q, u)

    picked = all_urls.get(quality) or all_urls.get("原画") or ""
    is_hls = picked.endswith(".m3u8") or ".m3u8" in picked
    return {"url": picked, "is_hls": is_hls, "all": all_urls}


def fetch_stream_urls_for_streamer(streamer, monitor_cookie, record_cookie, quality="原画"):
    """按主播档案抓直链：先解析当前 web_rid，再走 enter 接口。"""
    rid = get_douyin_web_rid(streamer, monitor_cookie)
    if not rid:
        return {"url": "", "is_hls": False, "all": {}}
    return fetch_stream_urls_by_rid(rid, record_cookie, quality)


def check_bilibili_live(room_id):
    """B站开播检测（Win 11634）。返回 (is_live, title)；请求失败返回 (None, "")"""
    try:
        resp = requests.get(
            f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}",
            headers={"User-Agent": random_ua()}, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            return data["data"]["live_status"] == 1, data["data"].get("title", "直播间")
    except Exception:
        pass
    return None, ""


# ---------- B站多形式输入归一（直播间链接 / UID） ----------

def classify_bilibili_target(raw):
    """区分直播间号（live.bilibili.com/数字）与 UID（space 链接或纯数字）。
    二者是完全不同的数字，不能混用。"""
    s = str(raw).strip()
    m = re.search(r'live\.bilibili\.com/(\d+)', s)
    if m:
        return {"type": "room_id", "id": m.group(1)}
    m = re.search(r'space\.bilibili\.com/(\d+)', s)
    if m:
        return {"type": "uid", "id": m.group(1)}
    if re.fullmatch(r"\d+", s):
        return {"type": "uid", "id": s}
    return {"type": "unknown", "id": s}


def _bili_card_info(uid):
    """用户卡片：昵称 + 可能为空的房间号。失败返回 ("", "")"""
    try:
        r = requests.get(f"https://api.bilibili.com/x/web-interface/card?mid={uid}",
                         headers={"User-Agent": random_ua(), "Referer": "https://www.bilibili.com/"},
                         timeout=8).json()
        if r.get("code") == 0:
            card = r.get("data", {}).get("card", {})
            return card.get("name", ""), str(r.get("data", {}).get("roomid") or "")
    except Exception:
        pass
    return "", ""


def _bili_room_info_old(uid):
    """UID → 直播间号（getRoomInfoOld）。失败返回 "" """
    try:
        r = requests.get(f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={uid}",
                         headers={"User-Agent": random_ua(), "Referer": "https://live.bilibili.com/"},
                         timeout=8).json()
        if r.get("code") == 0 and r.get("data", {}).get("url"):
            m = re.search(r'(\d+)\s*$', str(r["data"]["url"]))
            if m:
                return m.group(1)
    except Exception:
        pass
    return ""


def resolve_bilibili_streamer(raw):
    """添加 B站主播：任意输入归一为 {name, room_id, uid}。

    - 直播间链接/房间号：get_info 反查 UID，card 补昵称
    - UID：card 拿昵称，getRoomInfoOld 拿直播间号（两者是不同的数字，绝不互替）
    """
    t = classify_bilibili_target(raw)
    if t["type"] == "room_id":
        room_id = t["id"]
        uid = ""
        try:
            r = requests.get(f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}",
                             headers={"User-Agent": random_ua()}, timeout=8).json()
            if r.get("code") == 0:
                uid = str(r.get("data", {}).get("uid") or "")
        except Exception:
            pass
        name, _ = _bili_card_info(uid) if uid else ("", "")
        return {"name": name, "room_id": room_id, "uid": uid}
    if t["type"] == "uid":
        uid = t["id"]
        name, room_id = _bili_card_info(uid)
        if not room_id:
            room_id = _bili_room_info_old(uid)
        if not room_id:
            raise ValueError("无法从该 UID 获取直播间号（可能不是主播账号），请直接粘贴直播间链接 live.bilibili.com/房间号")
        return {"name": name, "room_id": room_id, "uid": uid}
    raise ValueError("无法识别的B站输入，请粘贴直播间链接或 UID（纯数字）")


def fetch_bili_user_info(uid):
    """B站主播信息：昵称 + 房间号。查不到房间号时返回空串（绝不拿 UID 冒充房间号）。"""
    uid = str(uid).strip()
    name, room_id = _bili_card_info(uid)
    if not room_id:
        room_id = _bili_room_info_old(uid)
    return name, room_id

