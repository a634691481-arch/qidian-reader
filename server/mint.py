"""w_tsfp 纯 Python 铸造：V8 嵌入引擎跑 probev3.js，无 Node、无浏览器、无网络。

原理：起点风控 token 由 probev3.js（腾讯 Chaos VM）在页面里算出后写 document.cookie。
本模块用 py_mini_racer(V8) 提供最小宿主环境（cookie/navigator/canvas/localStorage/定时器），
执行同一份脚本，拦截 cookie 写入拿到 w_tsfp。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from py_mini_racer import MiniRacer

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probev3.js"

_SHIM = r"""
var __cookies = {};
var __timers = [];
var __tick = 0;

function __now(){ return Date.now(); }

var document = {
  get cookie(){ return Object.keys(__cookies).map(function(k){return k+'='+__cookies[k];}).join('; '); },
  set cookie(v){
    var s = String(v).split(';')[0];
    var i = s.indexOf('=');
    if (i > 0) { __cookies[s.slice(0,i).trim()] = s.slice(i+1).trim(); }
  },
  readyState: 'complete',
  referrer: 'https://www.qidian.com/',
  domain: 'www.qidian.com',
  URL: 'https://www.qidian.com/chapter/1048541850/894700866/',
  location: { href: 'https://www.qidian.com/chapter/1048541850/894700866/', protocol: 'https:', host: 'www.qidian.com', hostname: 'www.qidian.com', pathname: '/chapter/1048541850/894700866/', search: '', hash: '' },
  documentElement: { clientWidth: 1920, clientHeight: 960, style: {} },
  body: { clientWidth: 1920, clientHeight: 860, appendChild: function(){}, removeChild: function(){}, style: {} },
  head: { appendChild: function(){}, removeChild: function(){} },
  createElement: function(tag){
    return {
      tagName: String(tag).toUpperCase(),
      style: {}, dataset: {}, children: [],
      setAttribute: function(){}, getAttribute: function(){ return null; },
      appendChild: function(){}, removeChild: function(){}, addEventListener: function(){},
      getContext: function(){ return __ctx(); },
      toDataURL: function(){ return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='; },
      width: 300, height: 150
    };
  },
  getElementsByTagName: function(){ return []; },
  getElementById: function(){ return null; },
  querySelector: function(){ return null; },
  querySelectorAll: function(){ return []; },
  addEventListener: function(t, fn){ if (typeof fn === 'function') __listeners.push([String(t), fn]); },
  removeEventListener: function(){},
  hasFocus: function(){ return true; }
};

function __ctx(){
  var c = {};
  c.canvas = { width: 300, height: 150 };
  c.fillRect = function(){}; c.fillText = function(){}; c.strokeText = function(){};
  c.beginPath = function(){}; c.arc = function(){}; c.closePath = function(){}; c.fill = function(){}; c.stroke = function(){};
  c.moveTo = function(){}; c.lineTo = function(){}; c.bezierCurveTo = function(){}; c.quadraticCurveTo = function(){};
  c.save = function(){}; c.restore = function(){}; c.translate = function(){}; c.rotate = function(){}; c.scale = function(){};
  c.measureText = function(t){ return { width: String(t).length * 8, actualBoundingBoxAscent: 8 }; };
  c.getImageData = function(x, y, w, h){ return { data: new Uint8ClampedArray(Math.max(4, (w|0)*(h|0)*4)), width: w, height: h }; };
  c.createLinearGradient = function(){ return { addColorStop: function(){} }; };
  c.createRadialGradient = function(){ return { addColorStop: function(){} }; };
  c.putImageData = function(){}; c.drawImage = function(){}; c.clip = function(){};
  c.getParameter = function(k){ return ({37443:'WebKit', 7936:'WebKit WebGL', 7937:'WebGL 1.0', 7938:'WebGL GLSL ES 1.0'})[k] || 'WebKit'; };
  c.getExtension = function(){ return {}; };
  c.getSupportedExtensions = function(){ return ['WEBGL_debug_renderer_info']; };
  c.getShaderPrecisionFormat = function(){ return { precision: 23, rangeMin: 127, rangeMax: 127 }; };
  return c;
}

var navigator = {
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
  platform: 'Win32', vendor: 'Google Inc.', language: 'zh-CN', languages: ['zh-CN','zh'],
  hardwareConcurrency: 8, deviceMemory: 8, maxTouchPoints: 0, webdriver: false,
  cookieEnabled: true, onLine: true, doNotTrack: null,
  plugins: { length: 5 }, mimeTypes: { length: 2 },
  permissions: { query: function(){ return { state: 'prompt' }; } }
};

var screen = { width: 1920, height: 1080, availWidth: 1920, availHeight: 1040, colorDepth: 24, pixelDepth: 24 };
var location = document.location;
var localStorage = {
  _d: {},
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(this._d, k) ? this._d[k] : null; },
  setItem: function(k, v){ this._d[k] = String(v); },
  removeItem: function(k){ delete this._d[k]; },
  clear: function(){ this._d = {}; },
  key: function(i){ return Object.keys(this._d)[i] || null; },
  get length(){ return Object.keys(this._d).length; }
};
var sessionStorage = localStorage;
var performance = { now: function(){ return __now() - 1; }, timing: { navigationStart: __now() - 100 }, navigation: { type: 0 } };
var crypto = {
  getRandomValues: function(a){ for (var i=0;i<a.length;i++){ a[i] = (Math.random()*256)|0; } return a; }
};
var setTimeout = function(fn, ms){ if (typeof fn === 'function') __timers.push(fn); return ++__cb; };
var setInterval = function(fn, ms){
  if (typeof fn === 'function' && String(fn).indexOf('debugger') < 0) __timers.push(fn);
  return ++__cb;
};
var clearTimeout = function(){};
var clearInterval = function(){};
var requestAnimationFrame = function(fn){ if (typeof fn === 'function') __timers.push(function(){ fn(__now()); }); return ++__cb; };
var __listeners = [];
var addEventListener = function(t, fn){ if (typeof fn === 'function') __listeners.push([String(t), fn]); };
var removeEventListener = function(){};
var fetch = function(){ return { then: function(){ return this; }, catch: function(){ return this; } }; };
var XMLHttpRequest = function(){
  this.open = function(){}; this.send = function(){}; this.setRequestHeader = function(){};
  this.addEventListener = function(){}; this.readyState = 0; this.status = 0;
};

var __B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
function btoa(input){
  var s = String(input), out = '', i = 0;
  for (; i + 2 < s.length; i += 3) {
    var c1 = s.charCodeAt(i) & 255, c2 = s.charCodeAt(i+1) & 255, c3 = s.charCodeAt(i+2) & 255;
    out += __B64.charAt(c1 >> 2) + __B64.charAt(((c1 & 3) << 4) | (c2 >> 4))
         + __B64.charAt(((c2 & 15) << 2) | (c3 >> 6)) + __B64.charAt(c3 & 63);
  }
  var rest = s.length - i;
  if (rest === 1) {
    var a = s.charCodeAt(i) & 255;
    out += __B64.charAt(a >> 2) + __B64.charAt((a & 3) << 4) + '==';
  } else if (rest === 2) {
    var a2 = s.charCodeAt(i) & 255, b2 = s.charCodeAt(i+1) & 255;
    out += __B64.charAt(a2 >> 2) + __B64.charAt(((a2 & 3) << 4) | (b2 >> 4))
         + __B64.charAt((b2 & 15) << 2) + '=';
  }
  return out;
}
function atob(input){
  var s = String(input).replace(/[^A-Za-z0-9+/]/g, ''), out = '', i = 0;
  for (; i + 3 < s.length; i += 4) {
    var n = (__B64.indexOf(s.charAt(i)) << 18) | (__B64.indexOf(s.charAt(i+1)) << 12)
          | (__B64.indexOf(s.charAt(i+2)) << 6) | __B64.indexOf(s.charAt(i+3));
    out += String.fromCharCode((n >> 16) & 255, (n >> 8) & 255, n & 255);
  }
  return out;
}

var process = undefined;
var globalThis = this;
var window = this;
var self = this;
var top = this;
var parent = this;
var __cb = 0;
"""

_RUN = r"""
function __fire(name){
  var n = 0, keep = [];
  for (var i = 0; i < __listeners.length; i++) {
    var t = __listeners[i][0], fn = __listeners[i][1];
    if (t === name || t === 'load' || t === 'DOMContentLoaded') { try { fn({ type: t }); n++; } catch (e) {} }
    else keep.push(__listeners[i]);
  }
  __listeners = keep;
  return n;
}

function __flushTimers(limit){
  var n = 0;
  while (__timers.length && n < limit) {
    var fn = __timers.shift();
    try { fn(); } catch (e) {}
    n++;
  }
  return n;
}
"""


class Minter:
    """一次 V8 上下文可反复铸造；脚本只加载一次。"""

    def __init__(self, probe_path: Path | None = None) -> None:
        self.src = (probe_path or PROBE).read_text(encoding="utf-8")
        self.ctx = MiniRacer()
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        self.ctx.eval(_SHIM)
        self.ctx.eval(_RUN)
        self.ctx.eval(self.src)
        self._loaded = True

    def mint(self, seed: str = "", timeout_s: float = 8.0) -> str:
        self._load()
        # 重置上次铸造残留：probev3 每次重 eval 会重新注册 listeners，
        # 不清空会随铸造次数线性叠加（越铸越慢 + Chaos VM 状态漂移）
        self.ctx.eval("__cookies = {}; __timers = []; __listeners = []; __cb = 0;")
        # 灌入底座 cookie（不含 w_tsfp）；json.dumps 保证值安全转成 JS 字面量
        # （Python repr 的 \x.. 转义 JS 不认，含引号/反斜杠时甚至能注入代码）
        for kv in seed.split(";"):
            i = kv.find("=")
            if i <= 0:
                continue
            k, v = kv[:i].strip(), kv[i + 1:].strip()
            if not k or k == "w_tsfp":
                continue
            self.ctx.eval("__cookies[%s] = %s;" % (json.dumps(k), json.dumps(v)))

        self.ctx.eval(self.src)
        for ev in ("DOMContentLoaded", "load", "readystatechange"):
            try:
                self.ctx.eval("__fire(%r);" % ev)
            except Exception:  # noqa: BLE001
                pass
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            self.ctx.eval("__flushTimers(50);")
            tok = self.ctx.eval("__cookies['w_tsfp'] || ''")
            if tok:
                return str(tok)
            if not self.ctx.eval("__timers.length"):
                time.sleep(0.02)
        return ""


_MINTERS: dict[str, Minter] = {}


def mint_token(seed: str = "") -> str:
    """线程内复用一个 V8 实例"""
    import threading

    key = str(threading.get_ident())
    m = _MINTERS.get(key)
    if m is None:
        m = _MINTERS[key] = Minter()
    return m.mint(seed)


if __name__ == "__main__":
    import sys

    seed = Path(sys.argv[1]).read_text(encoding="utf-8") if len(sys.argv) > 1 else ""
    t0 = time.time()
    tok = mint_token(seed)
    print("len=%d  %.0fms" % (len(tok), (time.time() - t0) * 1000))
    print(tok)
