#!/usr/bin/env python3
"""生成主页的头图 / 页脚：蓝色星空波浪横幅（自仓 SVG，不依赖 Vercel）。

要点：
  1. 蓝色夜空：深蓝 → 靛蓝 → 天青，配星点与星芒（和原画《星空·鲸鱼的梦》同一蓝系）
  2. 底部/顶部叠三层波浪，颜色从深到亮；每层横向大幅来回 + 一点上下起伏，
     三层节奏互质，看起来像海面在涌，而不是慢慢平移
  3. 头图带 "Hi, I'm Xche 👋"（SVG 文字，用系统字体渲染）
  4. `--frames`：把动画在关键帧时刻定格成静态 SVG，交给 rsvg-convert 检查画面
"""
import math
import random
import sys
from pathlib import Path

OUT = Path(__file__).parent / "assets"
DBG = Path(__file__).parent / ".dbg" / "wave_frames"
GIF = Path(__file__).parent / ".dbg" / "wave_gif"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,'PingFang SC','Microsoft YaHei',sans-serif"

# ------------------------------------------------------------------ 三层浪
# (class, y 占画布高度的比例, 正弦振幅, 相位, 渐变 id, 不透明度)
LAYERS = [
    ("wv1", 0.66, 16, 0.0, "w1", ".95"),
    ("wv2", 0.76, 13, 1.3, "w2", ".92"),
    ("wv3", 0.88, 10, 2.6, "w3", ".9"),
]

# 每层浪的运动：(时间比例, dx, dy)，dur 秒，delay 用负值错开相位。
# 幅度按「一眼看得出来」定：横向来回 80~140px（画布宽 1000），再叠几像素上下起伏，
# 三层周期 12 / 9.4 / 7.6 秒互不整除，合起来很久不重复同一个画面。
MOTION = [
    dict(cls="wv1", kf="drift1", dur=12.0, delay=0.0,
         frames=[(0, 0, 0), (.25, -80, -8), (.5, -38, 6), (.75, 58, -5), (1, 0, 0)]),
    dict(cls="wv2", kf="drift2", dur=9.4, delay=-2.4,
         frames=[(0, 0, 0), (.25, 52, -6), (.5, 68, 7), (.75, -44, -2), (1, 0, 0)]),
    dict(cls="wv3", kf="drift3", dur=7.6, delay=-1.1,
         frames=[(0, 0, 0), (.25, -46, 6), (.5, -8, -6), (.75, 34, 4), (1, 0, 0)]),
]
MARGIN = 110  # x 采样左右余量：盖住最大横移 80px，动画到两端也不露天空色竖条
DEPTH = 70    # 填充往下多画这么多：上下起伏时画面底边同样不会露天空色


def stars(rnd, count, w, y0, y1, color, sw, op, layers=6):
    """星点分层：每层整体闪烁，几百颗也只占几条 path。"""
    out = []
    per = max(1, count // layers)
    for i in range(layers):
        pts = " ".join(
            f"M{rnd.uniform(-10, w + 10):.0f},{rnd.uniform(y0, y1):.0f}h0.01" for _ in range(per)
        )
        dur, delay = round(rnd.uniform(2.6, 5.4), 1), -round(rnd.uniform(0, 3), 1)
        out.append(
            f'<path class="st{i}" d="{pts}" fill="none" stroke="{color}" stroke-opacity="{op}" '
            f'stroke-linecap="round" stroke-width="{sw}"/>'
            f"<style>.st{i}{{animation:twk {dur}s ease-in-out {delay}s infinite}}</style>"
        )
    return "\n    ".join(out)


def sparkle(x, y, s, cls, dur, delay, color="#FFFFFF", op=".9"):
    return (
        f'<path class="{cls}" d="M {x},{y - s} Q {x + s * 0.2},{y - s * 0.2} {x + s},{y} '
        f'Q {x + s * 0.2},{y + s * 0.2} {x},{y + s} Q {x - s * 0.2},{y + s * 0.2} {x - s},{y} '
        f'Q {x - s * 0.2},{y - s * 0.2} {x},{y - s} Z" fill="{color}" opacity="{op}"/>'
        f"<style>.{cls}{{animation:twk {dur}s ease-in-out {delay}s infinite}}</style>"
    )


def wave_path(y, amp, phase, bottom, w=1000, crest_only=False, step=25):
    """一条横贯画面的波浪：正弦采样 + Catmull-Rom 转三次贝塞尔。

    - 三次贝塞尔保证采样点处切线连续，浪脊是平滑正弦，不会出现扇贝状棱角
      （旧版用 Q + 控制点固定下移 amp*0.4，上坡下坡一视同仁，每个采样点都是个折角）
    - x 采样范围左右各留 MARGIN，覆盖 drift 动画的 translateX(±80px)
      （旧版 x 只到 990，右边缘会露出 10~36px 的天空色竖条）
    """
    x_lo, x_hi = -MARGIN, w + MARGIN
    n = math.ceil((x_hi - x_lo) / step)
    pts = []
    for k in range(n + 1):
        x = x_lo + k * step
        pts.append((x, y + amp * math.sin((x / w) * math.pi * 2.2 + phase) - amp * 0.25))
    d = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        d.append(
            f"C{p1[0] + (p2[0] - p0[0]) / 6:.1f},{p1[1] + (p2[1] - p0[1]) / 6:.1f} "
            f"{p2[0] - (p3[0] - p1[0]) / 6:.1f},{p2[1] - (p3[1] - p1[1]) / 6:.1f} "
            f"{p2[0]:.1f},{p2[1]:.1f}"
        )
    if not crest_only:
        d.append(f"L{pts[-1][0]:.1f},{bottom}L{pts[0][0]:.1f},{bottom}Z")
    return " ".join(d)


def ease_in_out(f):
    """CSS ease-in-out = cubic-bezier(.42,0,.58,1)：解出该进度对应的动画进度。

    定格检查要跟浏览器看到的画面一致，所以这里不能直接用线性插值。
    """
    lo, hi = 0.0, 1.0
    for _ in range(24):
        mid = (lo + hi) / 2
        x = 3 * (1 - mid) ** 2 * mid * 0.42 + 3 * (1 - mid) * mid ** 2 * 0.58 + mid ** 3
        if x < f:
            lo = mid
        else:
            hi = mid
    t = (lo + hi) / 2
    return 3 * (1 - t) * t ** 2 + t ** 3


def baked(m, t):
    """定格模式：算出 t 秒时这一层的静态 transform（播放时不跑动画）。"""
    k = ((t - m["delay"]) % m["dur"]) / m["dur"]
    for (t0, dx0, dy0), (t1, dx1, dy1) in zip(m["frames"], m["frames"][1:]):
        if t0 <= k <= t1:
            f = 0 if t1 == t0 else ease_in_out((k - t0) / (t1 - t0))
            return f'transform="translate({dx0 + (dx1 - dx0) * f:.1f},{dy0 + (dy1 - dy0) * f:.1f})"'
    dx, dy = m["frames"][-1][1:]
    return f'transform="translate({dx:.1f},{dy:.1f})"'


def layer(i, inner, t=None):
    """一层浪的外壳：正常模式挂 class 交给 CSS 动画，定格模式直接写死 transform。"""
    m = MOTION[i]
    if t is None:
        return f'<g class="{m["cls"]}">{inner}</g>'
    return f'<g {baked(m, t)}>{inner}</g>'


def motion_css():
    """把 MOTION 翻译成 @keyframes + 类选择器（保证动画和定格用的是同一组数字）。"""
    out = []
    for m in MOTION:
        steps = "".join(
            f"{k * 100:g}%{{transform:translate({dx:g}px,{dy:g}px)}}"
            for k, dx, dy in m["frames"]
        )
        out.append(f"@keyframes {m['kf']}{{{steps}}}")
        out.append(
            f".{m['cls']}{{animation:{m['kf']} {m['dur']:g}s ease-in-out "
            f"{m['delay']:g}s infinite}}"
        )
    return "\n    ".join(out)


def banner(kind, t=None):
    """kind: 'header' 波浪在底部；'footer' 波浪在顶部。t 不为 None 时定格该时刻。"""
    rnd = random.Random(7 if kind == "header" else 11)
    W = 1000
    H = 220 if kind == "header" else 150
    flip = f'transform="translate(0,{H}) scale(1,-1)"' if kind == "footer" else ""

    star_zone = (0, H * 0.72) if kind == "header" else (H * 0.3, H)
    st = "\n    ".join([
        stars(rnd, 90, W, *star_zone, "#FFFFFF", 1.6, ".85"),
        stars(rnd, 110, W, *star_zone, "#DCEAFF", 1.1, ".65"),
        stars(rnd, 70, W, *star_zone, "#A9C4FF", 0.9, ".5"),
    ])
    sparks = "".join(
        sparkle(x, y, s, f"sp{k}", round(rnd.uniform(3.0, 5.2), 1), -round(rnd.uniform(0, 3), 1))
        for k, (x, y, s) in enumerate(
            [(96, H * 0.24, 9), (268, H * 0.15, 6), (452, H * 0.3, 7),
             (664, H * 0.18, 6.5), (836, H * 0.34, 8), (930, H * 0.12, 5)]
        )
    )
    text = ""
    if kind == "header":
        text = f'''
  <text x="{W / 2}" y="{H * 0.47:.0f}" text-anchor="middle" font-family="{FONT}"
        font-size="46" font-weight="600" fill="#0A1E3C" opacity=".45"
        filter="url(#txtblur)">Hi, I&#39;m Xche 👋</text>
  <text x="{W / 2}" y="{H * 0.46:.0f}" text-anchor="middle" font-family="{FONT}"
        font-size="46" font-weight="600" fill="#EAF6FF" letter-spacing="1">Hi, I&#39;m Xche 👋</text>'''

    # 渐变用 userSpaceOnUse：y 坐标跟着每层浪的可见范围走，
    # 这样往下多填 DEPTH 不会把渐变拉长（否则浪的颜色会整体变浅）
    grads = "".join(
        f'''<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="{H * yr - amp * 1.25:.1f}" x2="0" y2="{H}">
      <stop offset="0" stop-color="{c0}"/><stop offset="1" stop-color="{c1}"/>
    </linearGradient>'''
        for (_, yr, amp, _, gid, _), (c0, c1) in zip(
            LAYERS, [("#1B4E86", "#123A6E"), ("#38A0DC", "#1E63A8"), ("#7FCBEE", "#2E86C8")]
        )
    )

    def group(i, inner):
        return f'  <g {flip}>\n    {layer(i, inner, t)}\n  </g>'

    waves = []
    for i, (_, yr, amp, ph, gid, op) in enumerate(LAYERS):
        inner = (f'<path d="{wave_path(H * yr, amp, ph, H + DEPTH)}" '
                 f'fill="url(#{gid})" opacity="{op}"/>')
        waves.append(group(i, inner))
    # 这条亮线描的是第一层浪的浪脊，所以必须跟 wv1 同一个动画同步漂移；
    # 又要压在 wv2 之上，所以单独成组放在最后
    _, yr0, amp0, ph0, _, _ = LAYERS[0]
    waves.append(group(0, f'<path d="{wave_path(H * yr0, amp0, ph0, H, crest_only=True)}" '
                          f'fill="none" stroke="#9FDCF5" stroke-opacity=".4" stroke-width="2.5"/>'))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img"
     aria-label="{'Hi, I am Xche' if kind == 'header' else '蓝色星空波浪'}">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0.18" y2="1">
      <stop offset="0" stop-color="#061229"/>
      <stop offset="0.34" stop-color="#0C2A55"/>
      <stop offset="0.68" stop-color="#164A86"/>
      <stop offset="1" stop-color="#1E63A8"/>
    </linearGradient>
    {grads}
    <filter id="txtblur" x="-20%" y="-40%" width="140%" height="180%">
      <feGaussianBlur stdDeviation="4"/>
    </filter>
    <filter id="glow" x="-20%" y="-60%" width="140%" height="220%">
      <feGaussianBlur stdDeviation="9"/>
    </filter>
  </defs>

  <rect x="0" y="0" width="{W}" height="{H}" fill="url(#sky)"/>
  <g {flip}>
    <ellipse cx="{W * 0.62:.0f}" cy="{H * 0.3:.0f}" rx="330" ry="150" fill="#5FB6E8" opacity=".16" filter="url(#glow)"/>
    {st}
    {sparks}
  </g>
  {text}
{chr(10).join(waves)}

  <style>
    @keyframes twk{{0%,100%{{opacity:.3}}50%{{opacity:.95}}}}
    {motion_css()}
    @media (prefers-reduced-motion: reduce){{*{{animation:none !important}}}}
  </style>
</svg>
"""


def keyframe_times():
    """各层动画的关键帧时刻（去重），用来逐帧定格检查。"""
    ts = set()
    for m in MOTION:
        for k, _, _ in m["frames"]:
            ts.add(round((k * m["dur"] + m["delay"]) % m["dur"], 2))
        for k in (.125, .375, .625, .875):  # 关键帧之间也采样，看中间过程
            ts.add(round((k * m["dur"] + m["delay"]) % m["dur"], 2))
    return sorted(ts)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for kind in ("header", "footer"):
        p = OUT / f"{kind}-wave.svg"
        p.write_text(banner(kind), encoding="utf-8")
        print("written:", p.name, p.stat().st_size, "bytes")
    if "--frames" in sys.argv:
        DBG.mkdir(parents=True, exist_ok=True)
        for f in DBG.glob("*.svg"):
            f.unlink()
        for t in keyframe_times():
            for kind in ("header", "footer"):
                (DBG / f"{kind}_t{t:05.2f}.svg").write_text(banner(kind, t), encoding="utf-8")
        print("frames:", len(keyframe_times()), "x2 ->", DBG)
    if "--gif" in sys.argv:
        # 密集定格：每 0.2 秒一帧、转一圈 12 秒（wv1 的周期），拼成动图肉眼看幅度
        GIF.mkdir(parents=True, exist_ok=True)
        for f in GIF.glob("*.svg"):
            f.unlink()
        n = 60
        for i in range(n):
            (GIF / f"f{i:03d}.svg").write_text(banner("header", i * 0.2), encoding="utf-8")
        print("gif frames:", n, "->", GIF)
