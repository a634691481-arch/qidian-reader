"""滑块验证码纯算：缺口定位 + 人类轨迹生成。零浏览器依赖。

用法：
    python slider.py <bg.png> <slice.png>      # 输出偏移
    python slider.py --selftest                # 合成样本自测
"""
from __future__ import annotations

import math
import random
import sys

import cv2
import numpy as np


# ---------------------------------------------------------------- 图像解码
def _decode(buf: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(buf, np.uint8), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("图像解码失败")
    return img


def _gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


# ---------------------------------------------------------------- 缺口定位
def locate(bg_img, sl_img) -> dict:
    """返回 {'x':缺口左边缘, 'y':..., 'score':..., 'w':.., 'h':..}

    腾讯 TCaptcha 的 slice 是抠出的小图（带 alpha），bg 是带缺口的完整图。
    定位 = 用 slice 的 alpha 掩码在 bg 上做边缘匹配。
    """
    bg = _decode(bg_img) if isinstance(bg_img, (bytes, bytearray)) else bg_img
    sl = _decode(sl_img) if isinstance(sl_img, (bytes, bytearray)) else sl_img

    if sl.ndim == 3 and sl.shape[2] == 4:
        mask = sl[:, :, 3]
        tpl_color = sl[:, :, :3]
    else:
        tpl_color = sl if sl.ndim == 3 else cv2.cvtColor(sl, cv2.COLOR_GRAY2BGR)
        g0 = _gray(tpl_color)
        mask = ((g0 < 248) | (g0 > 8)).astype(np.uint8) * 255

    ys, xs = np.where(mask > 16)
    if xs.size < 30:
        raise ValueError("slice 掩码为空")
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    tpl_color = tpl_color[y0:y1, x0:x1]
    mask = mask[y0:y1, x0:x1]

    gb = _gray(bg)
    tb = _gray(tpl_color)
    bh, bw = gb.shape[:2]
    th, tw = tb.shape[:2]

    # 尺寸不一致时按比例缩放模板
    if th > bh or tw > bw:
        k = min(bh / th, bw / tw) * 0.92
        nw, nh = max(1, int(tw * k)), max(1, int(th * k))
        tb = cv2.resize(tb, (nw, nh), interpolation=cv2.INTER_AREA)
        mask = cv2.resize(mask, (nw, nh), interpolation=cv2.INTER_NEAREST)
        tw, th = nw, nh

    fb, ft = gb.astype(np.float32), tb.astype(np.float32)
    candidates = []

    # A. 灰度 CCOEFF（对缺口变暗/线性光照不敏感，实测最稳）
    r = cv2.matchTemplate(fb, ft, cv2.TM_CCOEFF_NORMED)
    _, mv, _, ml = cv2.minMaxLoc(r)
    candidates.append((float(mv), ml[0], ml[1], "gray-ccoeff"))

    # B. 带 alpha 掩码的 CCORR
    try:
        m8 = (mask > 16).astype(np.float32)
        if m8.sum() > 0:
            r2 = cv2.matchTemplate(fb, ft, cv2.TM_CCORR_NORMED, mask=m8)
            r2 = np.nan_to_num(r2, nan=-1.0, posinf=-1.0, neginf=-1.0)
            _, mv2, _, ml2 = cv2.minMaxLoc(r2)
            candidates.append((float(mv2) * 0.7, ml2[0], ml2[1], "gray-masked"))
    except cv2.error:
        pass

    score, x, y, how = max(candidates, key=lambda c: c[0])
    return {
        "x": int(x),
        "y": int(y),
        "score": round(float(score), 4),
        "how": how,
        "w": int(tw),
        "h": int(th),
        "bg": [int(bw), int(bh)],
        "slice_pad": [x0, y0],
    }


def locate_scaled(bg_img, sl_img, display_w: int | None = None) -> dict:
    """腾讯前端按显示宽度缩放，提交的答案需换算回显示坐标。"""
    r = locate(bg_img, sl_img)
    if display_w:
        r["x_display"] = int(round(r["x"] * display_w / r["bg"][0]))
    return r


# ---------------------------------------------------------------- 轨迹生成
def track(distance: float, rng: random.Random | None = None) -> list[list[int]]:
    """拟人化拖动轨迹 [[x, y, t_ms], ...]，末点 x == round(distance)。"""
    rng = rng or random.Random()
    d = max(1.0, float(distance))
    total = int(rng.uniform(650, 1100) + d * rng.uniform(0.55, 0.95))
    step_ms = 16

    pts: list[list[int]] = []
    x = 0.0
    v = 0.0
    t = 0
    # 贝塞尔式缓动 + 抖动，最后 15% 减速并微回弹
    easy = d / max(1.0, total / step_ms)
    phase_back = int(total / step_ms * 0.86)
    i = 0
    while t < total and x < d:
        i += 1
        if i < phase_back:
            a = rng.uniform(0.055, 0.11) if i < 8 else rng.uniform(0.02, 0.05)
            v = min(v + a * step_ms, easy * rng.uniform(1.1, 1.9))
        else:
            v = max(v * rng.uniform(0.55, 0.78), easy * 0.12)
        x += v
        if x > d:
            x = d
        y = int(round(math.sin(i / 7.0) * rng.uniform(0.4, 1.6) + rng.uniform(-1, 1)))
        pts.append([int(round(x)), y, t])
        t += step_ms
    if not pts or pts[-1][0] != int(round(d)):
        pts.append([int(round(d)), 0, t])
    # 末端回弹 1-2 像素
    if rng.random() < 0.5 and len(pts) > 3:
        pts.append([max(0, int(round(d)) - rng.randint(1, 2)), 0, t + step_ms])
        pts.append([int(round(d)), 0, t + step_ms * 2])
    return pts


def answer_json(distance: float) -> str:
    """腾讯 TCaptcha slide 答案体。"""
    import json

    return json.dumps({"x": int(round(distance)), "y": 0}, separators=(",", ":"))


# ---------------------------------------------------------------- 自测
def _selftest() -> int:
    rng = np.random.default_rng(7)
    bg = rng.integers(30, 235, (160, 320, 3), dtype=np.uint8)
    bg = cv2.GaussianBlur(bg, (5, 5), 0)
    cv2.circle(bg, (200, 90), 40, (240, 200, 60), -1)
    cv2.rectangle(bg, (40, 40), (120, 120), (60, 200, 220), -1)

    gx, gy, gw, gh = 173, 52, 56, 56
    piece = bg[gy : gy + gh, gx : gx + gw].copy()
    sl = cv2.cvtColor(piece, cv2.COLOR_BGR2BGRA)
    alpha = np.zeros((gh, gw), np.uint8)
    cv2.rectangle(alpha, (0, 0), (gw - 1, gh - 1), 255, -1)
    cv2.circle(alpha, (gw // 2, 0), 9, 255, -1)
    sl[:, :, 3] = alpha
    bg_marked = bg.copy()
    bg_marked[gy : gy + gh, gx : gx + gw] = (bg[gy : gy + gh, gx : gx + gw] * 0.45).astype(np.uint8)

    ok, b1 = cv2.imencode(".png", bg_marked)
    ok2, b2 = cv2.imencode(".png", sl)
    r = locate(b1.tobytes(), b2.tobytes())
    print("expect x=%d  got x=%d  score=%.4f" % (gx, r["x"], r["score"]))
    tr = track(r["x"])
    print("track points=%d  last=%s" % (len(tr), tr[-1]))
    return 0 if abs(r["x"] - gx) <= 2 else 1


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        raise SystemExit(_selftest())
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(2)
    import json

    with open(sys.argv[1], "rb") as f:
        b = f.read()
    with open(sys.argv[2], "rb") as f:
        s = f.read()
    print(json.dumps(locate(b, s), ensure_ascii=False))


def solve_urls(bg_url: str, slice_url: str) -> dict:
    """下载两张图 -> 缺口定位 -> 拟人轨迹 -> 答案体"""
    if not (bg_url and slice_url):
        return {"ok": False, "error": "需要 bg 与 slice 两个图片 URL"}
    try:
        import net

        bg, _ = net.fetch_bytes(bg_url)
        sl, _ = net.fetch_bytes(slice_url)
        result = locate(bg, sl)
        track_pts = track(result["x"])
        return {
            "ok": True,
            **result,
            "track": track_pts,
            "points": len(track_pts),
            "duration": track_pts[-1][2] if track_pts else 0,
            "answer": answer_json(result["x"]),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}
