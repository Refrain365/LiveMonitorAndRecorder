"""FastAPI Web UI 后端：REST API + 静态页面托管。

口令保护：config 里 global_settings.webui_password 非空时启用，
登录成功后发 HttpOnly token cookie。
"""
import os
import re
import secrets
import sys
from pathlib import Path
from urllib.parse import quote as _urlquote

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(monitor):
    app = FastAPI(title="LiveMonitorAndRecorder Linux")
    app.state.monitor = monitor
    _tokens = set()

    cfg = monitor.cfg

    # ---------- 鉴权 ----------

    def auth(request: Request):
        password = cfg.global_settings.get("webui_password", "")
        if not password:
            return
        token = request.cookies.get("lm_token", "")
        if token not in _tokens:
            raise HTTPException(status_code=401, detail="未登录")

    class LoginBody(BaseModel):
        password: str = ""

    @app.post("/api/login")
    def login(body: LoginBody, response: Response):
        password = cfg.global_settings.get("webui_password", "")
        if not password:
            return {"ok": True, "auth_required": False}
        if not secrets.compare_digest(body.password, password):
            raise HTTPException(status_code=401, detail="口令错误")
        token = secrets.token_hex(24)
        _tokens.add(token)
        response.set_cookie("lm_token", token, httponly=True, samesite="lax")
        return {"ok": True, "auth_required": True}

    @app.post("/api/logout")
    def logout(request: Request, response: Response):
        token = request.cookies.get("lm_token", "")
        _tokens.discard(token)
        response.delete_cookie("lm_token")
        return {"ok": True}

    @app.get("/api/auth_required")
    def auth_required():
        return {"required": bool(cfg.global_settings.get("webui_password", ""))}

    # ---------- 状态 / 日志 ----------

    @app.get("/api/status", dependencies=[Depends(auth)])
    def status():
        return monitor.get_status()

    @app.get("/api/logs", dependencies=[Depends(auth)])
    def logs(lines: int = 200):
        return {"lines": monitor.get_log_tail(min(max(lines, 10), 400))}

    # ---------- 主播管理 ----------

    class StreamerBody(BaseModel):
        name: str = ""
        platform: str  # bilibili / douyin
        url: str = ""
        quality: str = "原画"
        record_enabled: bool = False
        monitor_enabled: bool = True
        group: str = ""

    @app.get("/api/streamers", dependencies=[Depends(auth)])
    def list_streamers():
        return {"streamers": cfg.get_streamers()}

    @app.post("/api/streamers", dependencies=[Depends(auth)])
    def add_streamer(body: StreamerBody):
        if body.platform not in ("bilibili", "douyin"):
            raise HTTPException(status_code=400, detail="平台必须是 bilibili 或 douyin")
        name, url = body.name.strip(), body.url.strip()
        if not url:
            raise HTTPException(status_code=400, detail="链接不能为空")
        extra = {}
        if body.platform == "bilibili":
            from douyin_api import resolve_bilibili_streamer
            try:
                resolved = resolve_bilibili_streamer(url)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            # 存规范的直播间链接（房间号），UID 单独保存
            url = f"https://live.bilibili.com/{resolved['room_id']}"
            extra = {"uid": resolved.get("uid", "")}
            if not name:
                name = resolved.get("name", "")
            if not name:
                raise HTTPException(status_code=400, detail="自动获取昵称失败，请手填")
        else:
            from douyin_api import resolve_douyin_streamer
            try:
                resolved = resolve_douyin_streamer(url, cfg.cookies.get("douyin_monitor", ""))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            extra = resolved
            if not name:
                name = resolved.get("name", "")
            if not name:
                raise HTTPException(status_code=400, detail="自动获取昵称失败，请手填")
        if cfg.add_streamer(name, url, body.platform, body.quality or "原画", extra=extra):
            if body.record_enabled or body.group or not body.monitor_enabled:
                cfg.update_streamer(name, {"record_enabled": body.record_enabled,
                                           "monitor_enabled": body.monitor_enabled,
                                           "group": body.group})
            return {"ok": True, "name": name}
        raise HTTPException(status_code=400, detail="该主播已存在")

    @app.put("/api/streamers/{name}", dependencies=[Depends(auth)])
    def update_streamer(name: str, body: StreamerBody):
        s = cfg.find_streamer(name)
        if not s:
            raise HTTPException(status_code=404, detail="主播不存在")
        updates = {"quality": body.quality,
                   "record_enabled": body.record_enabled,
                   "monitor_enabled": body.monitor_enabled, "group": body.group}
        if body.url.strip() and body.url.strip() != s.get("url"):
            updates["url"] = body.url.strip()
            # 换了链接 → 重新归一
            if s.get("platform") == "douyin":
                from douyin_api import resolve_douyin_streamer
                try:
                    resolved = resolve_douyin_streamer(body.url.strip(), cfg.cookies.get("douyin_monitor", ""))
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
                for k in ("sec_uid", "unique_id", "last_web_rid"):
                    if resolved.get(k):
                        updates[k] = resolved[k]
            elif s.get("platform") == "bilibili":
                from douyin_api import resolve_bilibili_streamer
                try:
                    resolved = resolve_bilibili_streamer(body.url.strip())
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
                updates["url"] = f"https://live.bilibili.com/{resolved['room_id']}"
                if resolved.get("uid"):
                    updates["uid"] = resolved["uid"]
        if not cfg.update_streamer(name, updates):
            raise HTTPException(status_code=400, detail="更新失败")
        return {"ok": True}

    @app.delete("/api/streamers/{name}", dependencies=[Depends(auth)])
    def delete_streamer(name: str):
        monitor.stop_recording(name)
        if not cfg.remove_streamer(name):
            raise HTTPException(status_code=404, detail="主播不存在")
        return {"ok": True}

    @app.post("/api/streamers/{name}/record_start", dependencies=[Depends(auth)])
    def record_start(name: str):
        s = cfg.find_streamer(name)
        if not s:
            raise HTTPException(status_code=404, detail="主播不存在")
        # 手动开始录制是一次性操作，与「自动录制」开关相互独立，不改开关状态
        monitor.start_recording(s)
        return {"ok": True}

    @app.post("/api/streamers/{name}/record_stop", dependencies=[Depends(auth)])
    def record_stop(name: str):
        if not monitor.stop_recording(name):
            raise HTTPException(status_code=404, detail="当前没有录制任务")
        return {"ok": True}

    # ---------- 设置（含 Cookie、通知、自动化） ----------

    @app.get("/api/settings", dependencies=[Depends(auth)])
    def get_settings():
        data = dict(cfg.data)
        # 口令不回传明文
        data["global_settings"] = {k: v for k, v in data["global_settings"].items() if k != "webui_password"}
        data["global_settings"]["has_password"] = bool(cfg.global_settings.get("webui_password", ""))
        return data

    class SettingsBody(BaseModel):
        class Config:
            extra = "allow"

    @app.post("/api/settings", dependencies=[Depends(auth)])
    def save_settings(body: dict):
        if "cookies" in body:
            cfg.data["cookies"] = body["cookies"]
        if "notification" in body:
            cfg.data["notification"] = body["notification"]
        if "global_settings" in body:
            gs = body["global_settings"]
            # 前端不回传口令字段；单独的 change_password 接口负责改口令
            gs.pop("webui_password", None)
            gs.pop("has_password", None)
            cfg.data["global_settings"].update(gs)
        if "automations" in body:
            cfg.data["automations"] = body["automations"]
        cfg.save()
        return {"ok": True}

    class PasswordBody(BaseModel):
        old_password: str = ""
        new_password: str = ""

    @app.post("/api/password", dependencies=[Depends(auth)])
    def change_password(body: PasswordBody):
        old = cfg.global_settings.get("webui_password", "")
        if old and not secrets.compare_digest(body.old_password, old):
            raise HTTPException(status_code=401, detail="旧口令错误")
        cfg.global_settings["webui_password"] = body.new_password.strip()
        cfg.save()
        return {"ok": True}

    # ---------- 测试推送 ----------

    @app.post("/api/test_notify", dependencies=[Depends(auth)])
    def test_notify():
        from notifier import send_notifications
        send_notifications(cfg.data, "🧪 测试推送", "这是一条来自 Linux 版的测试消息")
        return {"ok": True}

    # ---------- B站扫码登录 ----------

    import base64
    import io as _io
    import qrcode as _qrcode

    _qr_sessions = {}  # sid -> qrcode_key

    @app.post("/api/qrlogin/start", dependencies=[Depends(auth)])
    def qrlogin_start():
        import qrlogin
        try:
            data = qrlogin.qr_generate()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"申请二维码失败: {e}")
        sid = secrets.token_hex(8)
        _qr_sessions[sid] = data["qrcode_key"]
        # 会话只保留最近 10 个，防泄漏
        for old in list(_qr_sessions)[:-10]:
            _qr_sessions.pop(old, None)
        img = _qrcode.make(data["url"])
        buf = _io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {"sid": sid, "qr": f"data:image/png;base64,{b64}"}

    @app.get("/api/qrlogin/status", dependencies=[Depends(auth)])
    def qrlogin_status(sid: str):
        import qrlogin
        from monitor import logger
        key = _qr_sessions.get(sid)
        if not key:
            raise HTTPException(status_code=404, detail="会话不存在或已失效，请重新生成二维码")
        try:
            r = qrlogin.qr_poll(key)
            if r["status"] == "success":
                # 先完成验证与保存，最后才清会话（中途异常不丢会话）
                resp = {"status": "error", "saved": False, "message": ""}
                if r.get("cookie"):
                    is_login, uname = qrlogin.verify_cookie(r["cookie"])
                    if is_login:
                        cfg.data["cookies"]["bilibili"] = r["cookie"]
                        cfg.save()
                        logger.info(f"📱 B站扫码登录成功（{uname}），Cookie 已保存，来源: {r.get('source')}")
                        resp = {"status": "success", "saved": True,
                                "message": f"登录成功（{uname}），Cookie 已自动保存"}
                    else:
                        logger.warning(f"[扫码] Cookie 提取成功但 nav 验证未登录: {r.get('source')}")
                        resp = {"status": "error", "saved": False,
                                "message": "取到的 Cookie 验证未通过（未登录态），请重试"}
                else:
                    logger.warning(f"[扫码] 成功但未提取到 Cookie: {r.get('source')}")
                    resp = {"status": "error", "saved": False,
                            "message": "扫码确认成功，但未提取到 Cookie，请重试"}
                _qr_sessions.pop(sid, None)
                return resp
            if r["status"] in ("expired", "error"):
                _qr_sessions.pop(sid, None)
            return {"status": r["status"], "saved": False, "message": r["message"]}
        except Exception as e:
            # 任何异常都不让前端 500：如实报错，保留会话供下轮重试
            logger.error(f"[扫码] 状态查询异常: {e}")
            return {"status": "error", "saved": False, "message": f"服务端异常: {e}"}

    # ---------- 录播文件管理 ----------

    @app.get("/api/files", dependencies=[Depends(auth)])
    def list_files():
        """按保存目录格式返回录播树：平台 → 主播 → 日期 → 文件（含大小）。"""
        from monitor import PLATFORM_DIRS
        folder = cfg.global_settings.get("save_folder", "Recordings")
        root = os.path.abspath(folder)
        platforms = []
        for key, label in PLATFORM_DIRS.items():
            pdir = os.path.join(root, label)
            entry = {"key": key, "label": label, "count": 0, "size": 0, "streamers": []}
            if os.path.isdir(pdir):
                for sname in sorted(os.listdir(pdir)):
                    sdir = os.path.join(pdir, sname)
                    if not os.path.isdir(sdir):
                        continue
                    s_entry = {"name": sname, "count": 0, "size": 0, "days": []}
                    for dname in sorted(os.listdir(sdir), reverse=True):
                        dpath = os.path.join(sdir, dname)
                        if not os.path.isdir(dpath):
                            continue
                        d_entry = {"date": dname, "count": 0, "size": 0, "files": []}
                        for fname in sorted(os.listdir(dpath), reverse=True):
                            fpath = os.path.join(dpath, fname)
                            if not os.path.isfile(fpath):
                                continue
                            try:
                                sz = os.path.getsize(fpath)
                                mt = int(os.path.getmtime(fpath))
                            except OSError:
                                continue
                            rel = f"{label}/{sname}/{dname}/{fname}"
                            d_entry["files"].append({"name": fname, "size": sz, "mtime": mt, "path": rel})
                            d_entry["count"] += 1
                            d_entry["size"] += sz
                        if d_entry["files"]:
                            s_entry["days"].append(d_entry)
                            s_entry["count"] += d_entry["count"]
                            s_entry["size"] += d_entry["size"]
                    if s_entry["days"]:
                        entry["streamers"].append(s_entry)
                        entry["count"] += s_entry["count"]
                        entry["size"] += s_entry["size"]
            platforms.append(entry)
        return {"root": folder, "platforms": platforms}

    @app.get("/api/files/download", dependencies=[Depends(auth)])
    def download_file(path: str, request: Request):
        """下载录播文件，支持 HTTP Range（断点续传，206/416 语义完整）。"""
        folder = cfg.global_settings.get("save_folder", "Recordings")
        root = os.path.abspath(folder)
        full = os.path.realpath(os.path.join(root, path))
        if not (full == root or full.startswith(root + os.sep)):
            raise HTTPException(status_code=400, detail="非法路径")
        if not os.path.isfile(full):
            raise HTTPException(status_code=404, detail="文件不存在")
        size = os.path.getsize(full)
        fname = os.path.basename(full)
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"attachment; filename*=UTF-8''{_urlquote(fname)}",
        }
        start, end, status = 0, size - 1, 200
        rng = (request.headers.get("range") or "").strip()
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if not m:
                return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
            s_str, e_str = m.group(1), m.group(2)
            if s_str:
                start = int(s_str)
                end = int(e_str) if e_str else size - 1
            elif e_str:  # 后缀范围 bytes=-N
                start, end = max(0, size - int(e_str)), size - 1
            else:
                return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
            if start >= size or start > end:
                return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
            end = min(end, size - 1)
            status = 206
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        length = end - start + 1

        def body():
            with open(full, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(body(), status_code=status,
                                 media_type="application/octet-stream",
                                 headers={**headers, "Content-Length": str(length)})

    # ---------- 静态页面 ----------

    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    @app.exception_handler(HTTPException)
    async def http_exc_handler(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return app
