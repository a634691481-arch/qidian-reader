"""起点（阅文）微信扫码登录 · 微信开放平台原生流程，纯协议无浏览器。

二维码内容就是微信官方确认页：
    https://open.weixin.qq.com/connect/confirm?uuid=<uuid>

流程：
  1. GET open.weixin.qq.com/connect/qrconnect?appid=..&redirect_uri=ptlogin.yuewen.com/login/weixin
     -> HTML 里取 uuid
  2. 本地生成二维码（qrcode 库），内容如上
  3. 长轮询 long.open.weixin.qq.com/connect/l/qrconnect?uuid=..
     -> wx_errcode 408 待扫 / 404 已扫 / 405 已确认(带 wx_code) / 402 过期
  4. 用 wx_code 打 redirect_uri 换 alk，再走 passport.qidian.com/login/redirect 换起点登录态
"""
from __future__ import annotations

import base64
import io
import json
import re
import time
import uuid as _uuid
from urllib.parse import quote

import qrcode
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36")

APPID = "wx3b20af53872b38eb"
REDIRECT = "https://ptlogin.yuewen.com/login/weixin"
RETURN_URL = "https://www.qidian.com/loginSuccess?surl=https%3A%2F%2Fwww.qidian.com%2F"
CONFIRM = "https://open.weixin.qq.com/connect/confirm?uuid="

QRCONNECT = "https://open.weixin.qq.com/connect/qrconnect"
LONGPOLL = "https://long.open.weixin.qq.com/connect/l/qrconnect"
WEIXIN_WRAP = "https://ptlogin.yuewen.com/login/weixinlogin"
WEIXIN_CALLBACK = "https://ptlogin.yuewen.com/login/weixincallback"

BASE_PARAMS = {
    "appId": 10,
    "areaId": 1,
    "source": "",
    "returnurl": RETURN_URL,
    "target": "iframe",
    "ticket": 1,
    "autotime": 30,
    "jumpdm": "yuewen",
    "ajaxdm": "yuewen",
    "auto": 1,
}


def _png_data_url(text: str, box: int = 8, border: int = 2) -> str:
    qr = qrcode.QRCode(version=None, box_size=box, border=border)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class QRSession:
    def __init__(self) -> None:
        self.sid = _uuid.uuid4().hex[:12]
        self.http = requests.Session()
        self.http.headers.update({"User-Agent": UA})
        self.uuid = ""
        self.oauth_state = _uuid.uuid4().hex[:16]
        self.image = ""
        self.content = ""
        self.status = "pending"   # pending | scanned | confirmed | expired | error
        self.msg = ""
        self.created = time.time()
        self.cookie = ""
        self.user = {}
        self.polls = 0
        self.wx_code = ""
        self.debug = {}
        self.sources = []

    # ---------------- 1. 取 uuid + 出二维码 ----------------
    def start(self) -> dict:
        """走阅文 weixinlogin 包装页：一次拿到 uuid，并拿到同会话 cookie"""
        try:
            r = self.http.get(
                WEIXIN_WRAP,
                params=BASE_PARAMS,
                headers={"Referer": "https://passport.yuewen.com/"},
                timeout=20,
            )
            m = (re.search(r"l/qrconnect\?uuid=([\w-]{6,})", r.text)
                 or re.search(r"/connect/qrcode/([\w-]{6,})", r.text))
            if not m:
                raise RuntimeError("未取到 uuid（weixinlogin 结构变化）")
            self.uuid = m.group(1)
            self.content = CONFIRM + self.uuid
            self.image = _png_data_url(self.content)
            self.status = "pending"
            self.msg = "请用微信扫一扫"
        except Exception as e:  # noqa: BLE001
            self.status = "error"
            self.msg = str(e)[:160]
        return self.state()

    # ---------------- 2. 长轮询 ----------------
    def poll(self) -> dict:
        if self.status in ("confirmed", "expired", "error") or not self.uuid:
            return self.state()
        try:
            r = self.http.get(
                LONGPOLL,
                params={"uuid": self.uuid, "_": int(time.time() * 1000)},
                headers={"Referer": CONFIRM + self.uuid},
                timeout=30,
            )
            body = r.text
        except Exception as e:  # noqa: BLE001
            self.msg = "轮询异常：" + str(e)[:80]
            return self.state()

        self.polls += 1
        code = re.search(r"wx_errcode\s*=\s*(\d+)", body)
        wxcode = re.search(r"wx_code\s*=\s*'([^']*)'", body)
        err = code.group(1) if code else ""

        if err == "405":
            self.wx_code = wxcode.group(1) if wxcode else ""
            self._finish()
        elif err == "404":
            self.status = "scanned"
            self.msg = "已扫码，请在手机点「确认登录」"
        elif err == "402":
            self.status = "expired"
            self.msg = "二维码已过期，请刷新"
        elif err == "403":
            self.status = "expired"
            self.msg = "已取消登录"
        else:
            self.status = "pending"
            self.msg = "请用微信扫一扫"
        return self.state()

    # ---------------- 3. 换登录态 ----------------
    @staticmethod
    def _unescape_js(s: str) -> str:
        rep = (
            ("\\u0026", "&"),
            ("\\u003d", "="),
            ("\\u003f", "?"),
            ("\\u002f", "/"),
            ("\\/", "/"),
            ("&amp;", "&"),
        )
        for k, v in rep:
            s = s.replace(k, v)
        return s

    @staticmethod
    def _set_params(html: str) -> dict:
        """从页面里抠出 LoginV1.setParams({...}) 的 JSON"""
        m = re.search(r"setParams\(\s*(\{[\s\S]*?\})\s*\)\s*;", html)
        if not m:
            return {}
        try:
            return json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            return {}

    def _apply(self, p: dict) -> dict:
        """把 setParams 里的身份字段落成 cookie，返回命中的字段"""
        d = p.get("data") if isinstance(p.get("data"), dict) else p
        hit = {}
        pairs = (
            ("ywGuid", "ywguid"),
            ("ywKey", "ywkey"),
            ("ywOpenId", "ywopenid"),
            ("alk", "alk"),
        )
        for src, ck in pairs:
            v = d.get(src) or p.get(src)
            if v:
                hit[ck] = v
                for dom in (".qidian.com", ".yuewen.com"):
                    self.http.cookies.set(ck, v, domain=dom, path="/")
        return hit

    def _finish(self) -> None:
        if not self.wx_code:
            self.status = "expired"
            self.msg = "微信未返回 code"
            return

        cb = (
            "%s?returnurl=%s&ajaxdm=yuewen&appid=10&areaid=1&auto=1&autotime=30"
            "&ish5=&jumpdm=yuewen&popup=&target=iframe&ticket=1&code=%s&state=STATE"
        ) % (WEIXIN_CALLBACK, quote(RETURN_URL, safe=""), quote(self.wx_code, safe=""))

        body = ""
        try:
            body = self.http.get(cb, timeout=25, allow_redirects=True).text or ""
        except Exception:  # noqa: BLE001
            pass

        try:
            with open("data/last-callback.html", "w", encoding="utf-8") as f:
                f.write(body)
        except Exception:  # noqa: BLE001
            pass

        p = self._set_params(body)
        hit = self._apply(p)
        self.debug = {"cb": {"code": p.get("code"), "ticket": bool(p.get("ticket")), "hit": list(hit.keys())}}

        # 回调页可能是 JS 跳转，抓出其中的跳转地址并跟进
        follows = re.findall(r"https://passport\.qidian\.com/login/redirect\?[^\"'\s<>\\]+", body)
        if not follows:
            follows = re.findall(r"location\.(?:href|replace)\s*[=(]\s*[\"']([^\"']+)[\"']", body)

        # 回调页真实结构：var data = {... "callbackData":{"302url":"..."} ...}
        raw = self._unescape_js(body)
        urls = re.findall(r'"302url"\s*:\s*"(https:[^"]+)"', raw)
        urls += re.findall(r'"sublogin[^"]*"', raw)  # 占位，忽略
        for u in urls[:3]:
            if not u.startswith("http"):
                continue
            try:
                r3 = self.http.get(u, timeout=25, allow_redirects=True)
                self._apply(self._set_params(r3.text or ""))
                self.sources.append(u[:80])
            except Exception:  # noqa: BLE001
                pass

        # 页面里若有非空 ywOpenId，直接落 cookie
        oid = re.findall(r'"ywOpenId"\s*:\s*"([0-9A-Fa-f]{16,})"', raw)
        if oid:
            self._apply({"ywOpenId": oid[0]})

        ticket = p.get("ticket") or ""
        guid = p.get("ywGuid") or ""
        openid = p.get("ywOpenId") or ""
        if ticket:
            follows.insert(
                0,
                "https://www.qidian.com/loginSuccess?surl=https%%3A%%2F%%2Fwww.qidian.com%%2F&ticket=%s&ywguid=%s&ywOpenId=%s"
                % (quote(str(ticket), safe=""), quote(str(guid), safe=""), quote(str(openid), safe="")),
            )
        for u in follows[:4]:
            try:
                r2 = self.http.get(u, timeout=25, allow_redirects=True)
                self._apply(self._set_params(r2.text or ""))
            except Exception:  # noqa: BLE001
                pass

        self._to_qidian()

        jar = {c.name: c.value for c in self.http.cookies}
        self.user = {"ywopenid": jar.get("ywopenid", ""), "alk": bool(jar.get("alk"))}
        self.cookie = "; ".join("%s=%s" % (k, v) for k, v in jar.items() if v)
        if jar.get("ywopenid"):
            self.status = "confirmed"
            self.msg = "登录成功"
        else:
            self.status = "error"
            names = ",".join(jar.keys()) or "空"
            self.msg = "已确认，但未换到登录态（cookies: %s / cb hit: %s）" % (names[:60], ",".join(hit) or "无")

    def _to_qidian(self) -> None:
        """把 yuewen 侧的 alk 换成 qidian 登录态"""
        jar = {c.name: c.value for c in self.http.cookies}
        base = "https://passport.qidian.com/login/redirect?returnurl=" + quote(RETURN_URL, safe="")
        urls = [base]
        if jar.get("alk"):
            urls.append(
                base
                + "&alk=" + quote(jar["alk"], safe="")
                + "&ywopenid=" + quote(jar.get("ywopenid", ""), safe="")
            )
        for u in urls:
            try:
                self.http.get(u, timeout=25, allow_redirects=True)
            except Exception:  # noqa: BLE001
                pass
        try:
            self.http.get("https://www.qidian.com/", timeout=20)
        except Exception:  # noqa: BLE001
            pass

    def state(self, with_image: bool = False) -> dict:
        s = {
            "sid": self.sid,
            "status": self.status,
            "msg": self.msg,
            "polls": self.polls,
            "age": int(time.time() - self.created),
            "hasCookie": bool(self.cookie),
            "user": self.user,
            "content": self.content,
            "debug": self.debug,
        }
        if with_image:
            s["image"] = self.image
        return s


SESSIONS: dict[str, QRSession] = {}


def gc(max_age: int = 300) -> None:
    now = time.time()
    for k, v in list(SESSIONS.items()):
        if now - v.created > max_age:
            SESSIONS.pop(k, None)


# ---------------- 会话注册表（供 IPC / HTTP 两个适配层共用） ----------------
def start() -> dict:
    """新建扫码会话，返回二维码 dataURL 与 sid"""
    gc()
    sess = QRSession()
    state = sess.start()
    SESSIONS[sess.sid] = sess
    return {"ok": state["status"] != "error", "image": sess.image, **state}


def poll(sid: str) -> dict:
    """轮询扫码状态；确认成功后落盘 cookie 并作废已铸令牌"""
    import store
    import tsfp as token_mod

    sess = SESSIONS.get(sid)
    if not sess:
        return {"ok": False, "status": "expired", "msg": "会话不存在或已过期"}

    state = sess.poll()
    if state["status"] == "confirmed" and sess.cookie:
        store.write(sess.cookie)
        token_mod.MINTER.invalidate()
        state.update({"cookieLen": len(sess.cookie), "loggedIn": True})
    return {"ok": True, **state}
