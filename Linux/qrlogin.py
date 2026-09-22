"""B站扫码登录：生成二维码 + 轮询状态 + 提取登录 Cookie。

接口（bilibili passport 开放接口，无签名，纯 requests）：
  1. GET https://passport.bilibili.com/x/passport-login/web/qrcode/generate
     → {code: 0, data: {url, qrcode_key}}     url 即二维码内容
  2. GET https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key=...
     → data.code: 86101 未扫码 / 86090 已扫码待确认 / 86038 过期 /
        0 成功（登录参数可能在 data.url 查询串、也可能只在响应头 Set-Cookie，两者都要收）
"""
from urllib.parse import urlparse, parse_qs

import requests

GENERATE_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}

# 登录态关键四键（固定输出顺序）
KEEP_KEYS = ("SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5")


def qr_generate():
    """申请登录二维码。返回 {"qrcode_key": ..., "url": ...}；失败抛异常。"""
    r = requests.get(GENERATE_URL, headers=_HEADERS, timeout=10).json()
    if r.get("code") != 0 or not r.get("data", {}).get("qrcode_key"):
        raise RuntimeError(f"申请二维码失败: {r}")
    return r["data"]


def extract_cookie(cross_domain_url):
    """从跨域 URL 查询串提取登录参数（保留原始接口行为，供单测/兜底）。"""
    params = parse_qs(urlparse(cross_domain_url or "").query)
    return "; ".join(f"{k}={params[k][0]}" for k in KEEP_KEYS if params.get(k))


def _jar_pick(jar, key):
    """从 Cookie 罐取值。跨域跳转后同名 Cookie 可能存在于多个域
    （passport.bilibili.com / biligame.com 等），requests 的 jar[name]
    遇重名会抛 CookieConflictError，这里手动挑选：优先 bilibili 主域，否则取第一个。"""
    matches = [c for c in jar if c.name == key]
    if not matches:
        return None
    for c in matches:
        if "bilibili" in (c.domain or ""):
            return c.value
    return matches[0].value


def _merge_cookie(url, jar):
    """URL 查询参数与 Set-Cookie 响应头合并，按固定键序输出。

    实测新版 poll 成功时登录参数可能只从响应头下发，两处都要收集；
    同时跟随跨域跳转，把中间各站 Set-Cookie 的登录参数也收进 jar。
    返回 (cookie字符串, 来源诊断信息)。
    """
    values, source = {}, {}
    params = parse_qs(urlparse(url or "").query)
    for k in KEEP_KEYS:
        if params.get(k):
            values[k] = params[k][0]
            source[k] = "url"
    for k in KEEP_KEYS:
        if k not in values:
            v = _jar_pick(jar, k)
            if v:
                values[k] = v
                source[k] = "set-cookie"
    cookie = "; ".join(f"{k}={values[k]}" for k in KEEP_KEYS if k in values)
    return cookie, source


def qr_poll(qrcode_key):
    """轮询扫码状态。

    返回 {"status": waiting|scanned|success|expired|error,
          "message": ..., "cookie": ..., "source": 来源诊断}
    success 时 cookie 为可直接使用的 Cookie 字符串（可能为空=提取失败）。
    """
    session = requests.Session()
    try:
        resp = session.get(POLL_URL, params={"qrcode_key": qrcode_key},
                           headers=_HEADERS, timeout=10, allow_redirects=True)
        r = resp.json()
    except Exception as e:
        return {"status": "error", "message": f"网络错误: {e}", "cookie": "", "source": {}}
    code = r.get("data", {}).get("code") if isinstance(r.get("data"), dict) else None
    if code == 86101:
        return {"status": "waiting", "message": "等待扫码", "cookie": "", "source": {}}
    if code == 86090:
        return {"status": "scanned", "message": "已扫码，请在手机上确认", "cookie": "", "source": {}}
    if code == 86038:
        return {"status": "expired", "message": "二维码已过期，请重新生成", "cookie": "", "source": {}}
    if code == 0:
        url = r["data"].get("url", "") if isinstance(r.get("data"), dict) else ""
        # 跟随跨域跳转，收集中间各站下发的 Set-Cookie（不抛错）
        if url:
            try:
                session.get(url, headers=_HEADERS, timeout=10, allow_redirects=True)
            except Exception:
                pass
        try:
            cookie, source = _merge_cookie(url, session.cookies)
        except Exception as e:
            cookie, source = "", {"merge_error": str(e)}
        return {"status": "success",
                "message": "登录成功" if cookie else "扫码确认成功，但未提取到 Cookie",
                "cookie": cookie, "source": source}
    return {"status": "error",
            "message": r.get("data", {}).get("message") or f"未知状态码 {code}",
            "cookie": "", "source": {}}


def verify_cookie(cookie):
    """用 nav 接口验证 Cookie 是否为登录态。返回 (is_login, 昵称)。"""
    try:
        r = requests.get(NAV_URL, headers={**_HEADERS, "Cookie": cookie}, timeout=10).json()
        d = r.get("data") or {}
        return bool(d.get("isLogin")), d.get("uname") or ""
    except Exception:
        return False, ""
