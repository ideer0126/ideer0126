#!/usr/bin/env python3
"""生成主页的头图 / 页脚：蓝色星空波浪横幅（自仓 SVG，不依赖 Vercel）。

要点：
  1. 蓝色夜空：深蓝 → 靛蓝 → 天青，配星点与星芒（和原画《星空·鲸鱼的梦》同一蓝系）
  2. 底部/顶部叠三层波浪，颜色从深到亮，缓慢左右漂移
  3. 头图带 "Hi, I'm Xche 👋"（SVG 文字，用系统字体渲染）
"""
import math
import random
from pathlib import Path

OUT = Path(__file__).parent / "assets"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,'PingFang SC','Microsoft YaHei',sans-serif"


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


def wave_path(y, amp, phase, bottom, w=1000, crest_only=False):
    """一条横贯画面的波浪：正弦采样 + 平滑折线（够用且体积小）。"""
    pts = []
    for i in range(0, w + 51, 25):
        yy = y + amp * math.sin((i / w) * math.pi * 2.2 + phase) - amp * 0.25
        pts.append((i - 60, yy))
    d = [f"M{pts[0][0]:.0f},{pts[0][1]:.0f}"]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d.append(f"Q{(x0 + x1) / 2:.0f},{(y0 + y1) / 2 - amp * 0.4:.0f} {x1:.0f},{y1:.0f}")
    if not crest_only:
        d.append(f"L{pts[-1][0]:.0f},{bottom}L{pts[0][0]:.0f},{bottom}Z")
    return " ".join(d)


def banner(kind):
    """kind: 'header' 波浪在底部；'footer' 波浪在顶部。"""
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
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img"
     aria-label="{'Hi, I am Xche' if kind == 'header' else '蓝色星空波浪'}">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0.18" y2="1">
      <stop offset="0" stop-color="#061229"/>
      <stop offset="0.34" stop-color="#0C2A55"/>
      <stop offset="0.68" stop-color="#164A86"/>
      <stop offset="1" stop-color="#1E63A8"/>
    </linearGradient>
    <linearGradient id="w1" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1B4E86"/><stop offset="1" stop-color="#123A6E"/>
    </linearGradient>
    <linearGradient id="w2" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#38A0DC"/><stop offset="1" stop-color="#1E63A8"/>
    </linearGradient>
    <linearGradient id="w3" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#7FCBEE"/><stop offset="1" stop-color="#2E86C8"/>
    </linearGradient>
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
  <g {flip}>
    <g class="wv1"><path d="{wave_path(H * 0.66, 14, 0.0, H)}" fill="url(#w1)" opacity=".95"/></g>
  </g>
  <g {flip}>
    <g class="wv2"><path d="{wave_path(H * 0.76, 12, 1.3, H)}" fill="url(#w2)" opacity=".92"/></g>
  </g>
  <g {flip}>
    <g class="wv3"><path d="{wave_path(H * 0.88, 9, 2.6, H)}" fill="url(#w3)" opacity=".9"/></g>
    <path d="{wave_path(H * 0.66, 14, 0.0, H, crest_only=True)}" fill="none" stroke="#9FDCF5" stroke-opacity=".4" stroke-width="2.5"/>
  </g>

  <style>
    @keyframes twk{{0%,100%{{opacity:.3}}50%{{opacity:.95}}}}
    @keyframes drift1{{0%,100%{{transform:translateX(0)}}50%{{transform:translateX(-26px)}}}}
    @keyframes drift2{{0%,100%{{transform:translateX(0)}}50%{{transform:translateX(22px)}}}}
    @keyframes drift3{{0%,100%{{transform:translateX(0)}}50%{{transform:translateX(-16px)}}}}
    .wv1{{animation:drift1 16s ease-in-out infinite}}
    .wv2{{animation:drift2 13s ease-in-out infinite}}
    .wv3{{animation:drift3 10s ease-in-out infinite}}
  </style>
</svg>
"""


OUT.mkdir(exist_ok=True)
(OUT / "header-wave.svg").write_text(banner("header"), encoding="utf-8")
(OUT / "footer-wave.svg").write_text(banner("footer"), encoding="utf-8")
print("written:", *((p.name, p.stat().st_size) for p in sorted(OUT.glob("*wave.svg"))))
