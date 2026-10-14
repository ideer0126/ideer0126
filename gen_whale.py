#!/usr/bin/env python3
"""生成主页用的蓝鲸 SVG：莫奈印象派油画风（大场景 + 单独鲸鱼图标）。

做法：
  1. 鲸鱼重画成座头鲸（长胸鳍、宽尾鳍、圆钝头），形体先单独验证
  2. 全部用"碎笔触"堆出来（同色同宽的分组塞进一条 path，体积小）
  3. 颜色是深色莫奈：深蓝紫水面 + 青绿/紫罗兰碎笔 + 少量玫瑰与暖金反光
  4. feTurbulence + feDisplacementMap 让笔触与轮廓"手抖"，像画笔而不是矢量
  5. 画布颗粒 + 暗角
"""
import math
import random
from pathlib import Path

OUT = Path(__file__).parent / "assets"

# ------------------------------------------------------- 座头鲸形体（朝左）
def catmull_path(points, closed=True):
    """Catmull-Rom 转三次贝塞尔：给定关键点，输出平滑闭合曲线。"""
    n = len(points)

    def pt(i):
        return points[i % n] if closed else points[max(0, min(n - 1, i))]

    d = [f"M{points[0][0]:.1f},{points[0][1]:.1f}"]
    for i in (range(n) if closed else range(n - 1)):
        p0, p1, p2, p3 = pt(i - 1), pt(i), pt(i + 1), pt(i + 2)
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    if closed:
        d.append("Z")
    return " ".join(d)


W_X0, W_YC, W_LEN = 66.0, 146.0, 400.0


def _profile(t, peak_t, amp, floor):
    """0..1 上的平滑隆起：两端收到 floor，在 peak_t 处最高。"""
    k = math.log(0.5) / math.log(peak_t)
    return floor + amp * math.sin(math.pi * (t ** k)) ** 0.9


def _body_points(steps=22):
    top, bot = [], []
    for i in range(steps + 1):
        t = i / steps
        x = W_X0 + W_LEN * t
        top.append((x, W_YC - _profile(t, 0.30, 64, 12)))
        bot.append((x, W_YC + _profile(t, 0.40, 56, 14)))
    return top + list(reversed(bot))


BODY_PTS = _body_points()
# 尾鳍：两片厚实的叶 + 中间缺口
FLUKE_PTS = [
    (466, 132), (516, 96), (546, 84), (560, 94),
    (536, 120), (512, 136), (534, 158), (556, 180),
    (548, 196), (504, 178), (466, 156),
]
# 长胸鳍（座头鲸标志）
FIN_PTS = [
    (152, 190), (206, 216), (262, 242), (312, 256),
    (322, 247), (292, 230), (240, 206), (186, 184),
]
FIN_LIGHT = catmull_path([(158, 192), (208, 218), (264, 244), (308, 254)], closed=False)
# 小背鳍
DORSAL_PTS = [(368, 106), (382, 86), (404, 88), (392, 106)]

BODY = catmull_path(BODY_PTS)
FLUKE = catmull_path(FLUKE_PTS)
FLIPPER = catmull_path(FIN_PTS)
DORSAL = catmull_path(DORSAL_PTS)
BACK_LIGHT = catmull_path(BODY_PTS[1:21], closed=False)
FLUKE_LIGHT = catmull_path([(470, 134), (516, 98), (546, 86), (556, 96)], closed=False)
PLEATS = [
    "M 104,186 C 148,198 200,204 254,203",
    "M 122,194 C 164,204 212,208 264,207",
    "M 144,202 C 182,209 224,212 268,210",
]
MOUTH = ""
EYE = (150, 141)

# ------------------------------------------------------------ 笔触基础函数
def dab(x, y, length, angle, bow):
    a = math.radians(angle)
    x0, y0 = x - math.cos(a) * length / 2, y - math.sin(a) * length / 2
    x1, y1 = x + math.cos(a) * length / 2, y + math.sin(a) * length / 2
    mx = (x0 + x1) / 2 - math.sin(a) * bow
    my = (y0 + y1) / 2 + math.cos(a) * bow
    return f"M{x0:.0f},{y0:.0f}Q{mx:.0f},{my:.0f} {x1:.0f},{y1:.0f}"


def dab_layer(rnd, color, opacity, width, count, xr, yr, lo, hi, tilt=6, bow=8):
    d = " ".join(
        dab(
            rnd.uniform(*xr),
            rnd.uniform(*yr),
            rnd.uniform(lo, hi),
            rnd.uniform(-tilt, tilt),
            rnd.uniform(-bow, bow),
        )
        for _ in range(count)
    )
    return (
        f'<path d="{d}" fill="none" stroke="{color}" stroke-opacity="{opacity}" '
        f'stroke-width="{width}" stroke-linecap="round"/>'
    )


# ------------------------------------------------------------------- 鲸鱼
def build_whale(uid, aura=False, shadow=False, shine=1.0):
    rnd = random.Random(2026)
    # 皮肤：碎笔触分层，亮部偏青蓝，暗部偏靛紫，偶尔一点暖光
    skin = []
    for color, op, w, n, yr in [
        ("#0A2038", 0.5, 9, 30, (160, 212)),
        ("#123A5C", 0.45, 10, 34, (130, 205)),
        ("#1B5580", 0.4, 8, 34, (105, 185)),
        ("#2A7BA4", 0.36, 6, 30, (90, 160)),
        ("#4FA3C4", 0.24, 5, 20, (80, 140)),
        ("#86C8DC", 0.19, 4, 12, (74, 126)),
        ("#2A2E5E", 0.22, 7, 14, (130, 205)),
        ("#B8845E", 0.12, 4, 7, (100, 175)),
    ]:
        skin.append(dab_layer(rnd, color, op * shine, w, n, (70, 545), yr, 14, 52, 8, 7))
    skin = "\n        ".join(skin)
    fin_dabs = dab_layer(rnd, "#0A2440", 0.5, 7, 14, (165, 315), (192, 252), 14, 40, 10, 6)
    fin_dabs2 = dab_layer(rnd, "#2C6E96", 0.4, 5, 12, (165, 315), (190, 248), 12, 34, 10, 5)
    # 背脊上的高光碎笔
    crest = "".join(
        f'<path d="{dab(78 + i * 22, 122 - i * 1.5 + rnd.uniform(-4, 4), rnd.uniform(10, 26), rnd.uniform(-14, 4), rnd.uniform(-3, 3))}" '
        f'fill="none" stroke="#CFEFFB" stroke-opacity="{rnd.uniform(0.16, 0.4) * shine:.2f}" '
        f'stroke-width="{rnd.uniform(1.6, 3.4):.1f}" stroke-linecap="round"/>'
        for i in range(14)
    )
    pleats = "".join(
        f'<path d="{d}" fill="none" stroke="#9FD2E4" stroke-opacity=".13" stroke-width="2" stroke-linecap="round"/>'
        for d in PLEATS
    )
    aura_el = (
        f'<ellipse cx="300" cy="140" rx="300" ry="130" fill="url(#{uid}-aura)"/>' if aura else ""
    )
    shadow_el = (
        f'<ellipse cx="300" cy="272" rx="250" ry="18" fill="#01060D" opacity=".4" filter="url(#{uid}-blur)"/>'
        if shadow
        else ""
    )
    return f"""
  <defs>
    <linearGradient id="{uid}-skin" gradientUnits="userSpaceOnUse" x1="110" y1="74" x2="500" y2="215">
      <stop offset="0" stop-color="#7CC2E8"/>
      <stop offset="0.2" stop-color="#2E7BA6"/>
      <stop offset="0.48" stop-color="#1B5480"/>
      <stop offset="0.76" stop-color="#123A5C"/>
      <stop offset="1" stop-color="#0E2F4C"/>
    </linearGradient>
    <linearGradient id="{uid}-fin" gradientUnits="userSpaceOnUse" x1="150" y1="180" x2="300" y2="256">
      <stop offset="0" stop-color="#3B87A8"/>
      <stop offset="1" stop-color="#123A5C"/>
    </linearGradient>
    <radialGradient id="{uid}-aura">
      <stop offset="0" stop-color="#9FEEF8" stop-opacity=".42"/>
      <stop offset="0.55" stop-color="#3E92B8" stop-opacity=".2"/>
      <stop offset="1" stop-color="#123A63" stop-opacity="0"/>
    </radialGradient>
    <filter id="{uid}-blur" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="10"/>
    </filter>
    <filter id="{uid}-soft" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="3.6"/>
    </filter>
    <filter id="{uid}-brush" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="1.1"/>
    </filter>
    <filter id="{uid}-paint" x="-10%" y="-10%" width="120%" height="120%">
      <feTurbulence type="fractalNoise" baseFrequency="0.013 0.02" numOctaves="3" seed="7" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="7" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <clipPath id="{uid}-clip"><path d="{BODY}"/><path d="{FLUKE}"/></clipPath>
    <clipPath id="{uid}-finclip"><path d="{FLIPPER}"/></clipPath>
  </defs>
  {aura_el}
  {shadow_el}
  <g filter="url(#{uid}-paint)">
    <g filter="url(#{uid}-soft)" opacity=".75">
      <path d="{BODY}" fill="none" stroke="#020B16" stroke-width="14"/>
      <path d="{FLUKE}" fill="none" stroke="#020B16" stroke-width="12"/>
    </g>
    <path d="{FLIPPER}" fill="url(#{uid}-fin)"/>
    <g clip-path="url(#{uid}-finclip)">
      <path d="{FIN_LIGHT}" fill="none" stroke="#BFE8F5" stroke-opacity=".3" stroke-width="6" stroke-linecap="round" filter="url(#{uid}-soft)"/>
      {fin_dabs}
      {fin_dabs2}
    </g>
    <path d="{DORSAL}" fill="url(#{uid}-fin)"/>
    <path d="{BODY}" fill="url(#{uid}-skin)"/>
    <path d="{FLUKE}" fill="url(#{uid}-skin)"/>
    <g clip-path="url(#{uid}-clip)">
      <ellipse cx="300" cy="212" rx="230" ry="46" fill="#6FB0D2" opacity=".18" filter="url(#{uid}-blur)"/>
      <g filter="url(#{uid}-brush)">
        {skin}
      </g>
      <path d="{BACK_LIGHT}" fill="none" stroke="#DCF5FF" stroke-opacity=".62" stroke-width="6" stroke-linecap="round" filter="url(#{uid}-soft)"/>
      <path d="{FLUKE_LIGHT}" fill="none" stroke="#CBEDFA" stroke-opacity=".5" stroke-width="4.5" stroke-linecap="round" filter="url(#{uid}-soft)"/>
      <g filter="url(#{uid}-soft)">{crest}</g>
      {pleats}

      <path d="{BODY}" fill="none" stroke="#061529" stroke-opacity=".4" stroke-width="12" filter="url(#{uid}-blur)"/>
      <path d="{FLUKE}" fill="none" stroke="#061529" stroke-opacity=".4" stroke-width="10" filter="url(#{uid}-blur)"/>
      <path d="M 512,136 C 528,150 546,164 556,180" fill="none" stroke="#061529" stroke-opacity=".35" stroke-width="7" stroke-linecap="round" filter="url(#{uid}-soft)"/>
    </g>
    <circle cx="{EYE[0]}" cy="{EYE[1]}" r="11" fill="#9AD4E8" opacity=".2" filter="url(#{uid}-soft)"/>
    <circle cx="{EYE[0]}" cy="{EYE[1]}" r="6.4" fill="#04121F"/>
    <circle cx="{EYE[0]-1.7}" cy="{EYE[1]-1.7}" r="1.7" fill="#DCF6FF" opacity=".85"/>
  </g>
  <style>
    @keyframes twk{{0%,100%{{opacity:.3}}50%{{opacity:.9}}}}
  </style>"""


# ----------------------------------------------------------------- 莫奈水面
def scene_svg():
    rnd = random.Random(1899)
    water = []
    # 深水底色上的碎笔：蓝 → 青 → 紫罗兰，偶尔一抹玫瑰/暖金
    for color, op, w, n, yr, tilt in [
        ("#0C2A45", 0.5, 22, 60, (0, 340), 4),
        ("#123A5C", 0.42, 18, 58, (0, 330), 5),
        ("#1A4E73", 0.34, 15, 52, (0, 300), 5),
        ("#23648C", 0.28, 12, 46, (0, 260), 6),
        ("#2E7CA0", 0.22, 10, 38, (0, 220), 7),
        ("#3F93B0", 0.17, 8, 30, (0, 180), 8),
        ("#5FB0C6", 0.13, 6, 22, (0, 140), 9),
        ("#7FCBDA", 0.1, 5, 16, (0, 110), 10),
        ("#333A6E", 0.16, 9, 26, (40, 340), 6),
        ("#1E5F66", 0.13, 7, 20, (60, 300), 8),
        ("#C79AA6", 0.07, 5, 10, (20, 200), 9),
        ("#D8B98A", 0.06, 4, 8, (30, 170), 10),
        ("#020A14", 0.4, 30, 26, (170, 340), 3),
    ]:
        water.append(dab_layer(rnd, color, op, w, n, (-30, 1030), yr, 18, 78, tilt, 9))
    water = "\n      ".join(water)
    # 水面反光：横向拉长的亮笔（莫奈的水面碎光）
    shimmer = dab_layer(rnd, "#CBEDF4", 0.16, 4, 40, (-20, 1020), (6, 96), 22, 90, 2, 5)
    shimmer2 = dab_layer(rnd, "#9FDCE8", 0.12, 6, 26, (-20, 1020), (10, 130), 18, 70, 3, 5)
    motes = "".join(
        f'<circle cx="{rnd.uniform(60, 940):.0f}" cy="{rnd.uniform(20, 250):.0f}" r="{rnd.uniform(1.1, 2.8):.1f}" '
        f'fill="#CFEFF8" opacity="{rnd.uniform(0.1, 0.3):.2f}"/>'
        for _ in range(18)
    )
    bubbles = "".join(
        f'<circle class="bb{i}" cx="{rnd.uniform(340, 720):.0f}" cy="300" r="{rnd.uniform(3, 6):.1f}" '
        f'fill="none" stroke="#9FDCEB" stroke-opacity=".35" stroke-width="1.5"/>'
        f"<style>.bb{i}{{animation:rise {rnd.uniform(14, 20):.1f}s linear {-rnd.uniform(0, 14):.1f}s infinite}}"
        f"@keyframes rise{{0%{{transform:translate(0,0);opacity:0}}18%{{opacity:.55}}"
        f"100%{{transform:translate({rnd.uniform(-16, 16):.0f}px,-200px);opacity:0}}}}</style>"
        for i in range(4)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 340" width="1000" height="340" role="img" aria-label="莫奈风格的深色水面上，一头蓝色座头鲸">
  <defs>
    <linearGradient id="sea" x1="0" y1="0" x2="0.2" y2="1">
      <stop offset="0" stop-color="#10314B"/>
      <stop offset="0.32" stop-color="#0D2B48"/>
      <stop offset="0.7" stop-color="#081B32"/>
      <stop offset="1" stop-color="#020A14"/>
    </linearGradient>
    <radialGradient id="bloom">
      <stop offset="0" stop-color="#A8ECF7" stop-opacity=".2"/>
      <stop offset="0.5" stop-color="#3E92B8" stop-opacity=".09"/>
      <stop offset="1" stop-color="#0B2C46" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="shade">
      <stop offset="0" stop-color="#01060E" stop-opacity=".62"/>
      <stop offset="0.6" stop-color="#020A16" stop-opacity=".3"/>
      <stop offset="1" stop-color="#020A16" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="vig" cx="0.5" cy="0.46" r="0.78">
      <stop offset="0.4" stop-color="#000000" stop-opacity="0"/>
      <stop offset="0.76" stop-color="#01060C" stop-opacity=".48"/>
      <stop offset="1" stop-color="#000308" stop-opacity=".9"/>
    </radialGradient>
    <filter id="wobble" x="-6%" y="-6%" width="112%" height="112%">
      <feTurbulence type="fractalNoise" baseFrequency="0.014 0.022" numOctaves="4" seed="5" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="15" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="slightblur" x="-6%" y="-6%" width="112%" height="112%">
      <feGaussianBlur stdDeviation="0.8"/>
    </filter>
    <filter id="softlight" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="20"/>
    </filter>
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" seed="9"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>
    <filter id="canvas" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.01 0.4" numOctaves="2" seed="3"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>
    <clipPath id="frame"><rect x="0" y="0" width="1000" height="340" rx="26"/></clipPath>
  </defs>

  <rect x="0" y="0" width="1000" height="340" rx="26" fill="url(#sea)"/>

  <g clip-path="url(#frame)">
    <g filter="url(#slightblur)">
      <g filter="url(#wobble)">
        {water}
      </g>
    </g>

    <g filter="url(#softlight)">
      <ellipse cx="500" cy="180" rx="420" ry="180" fill="url(#shade)"/>
    </g>
    <g filter="url(#softlight)">
      <ellipse cx="520" cy="160" rx="360" ry="160" fill="url(#bloom)"/>
    </g>

    <g filter="url(#wobble)">
      {shimmer}
      {shimmer2}
    </g>

    {motes}

    <g transform="translate(196,34) scale(0.95)">
      <g class="bob">{build_whale('w', aura=True, shadow=True)}</g>
    </g>

    {bubbles}

    <rect x="0" y="0" width="1000" height="340" filter="url(#canvas)" opacity=".04"/>
    <rect x="0" y="0" width="1000" height="340" filter="url(#grain)" opacity=".07"/>
    <rect x="0" y="0" width="1000" height="340" fill="url(#vig)"/>
  </g>
  <rect x="0.75" y="0.75" width="998.5" height="338.5" rx="25.5" fill="none" stroke="#2E7C9C" stroke-opacity=".32" stroke-width="1.5"/>

  <style>
    @keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-14px)}}}}
    .bob{{animation:bob 10s ease-in-out infinite}}
    @keyframes twk{{0%,100%{{opacity:.3}}50%{{opacity:.9}}}}
  </style>
</svg>
"""


def solo_svg():
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="30 60 560 190" width="560" height="190" role="img" aria-label="莫奈风格的蓝色座头鲸">
  <g class="bob">{build_whale('s', aura=False, shadow=False, shine=1.15)}</g>
  <style>
    @keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-11px)}}}}
    .bob{{animation:bob 9s ease-in-out infinite}}
    @keyframes twk{{0%,100%{{opacity:.3}}50%{{opacity:.9}}}}
  </style>
</svg>
"""


OUT.mkdir(exist_ok=True)
(OUT / "blue-whale-scene.svg").write_text(scene_svg(), encoding="utf-8")
(OUT / "blue-whale.svg").write_text(solo_svg(), encoding="utf-8")
print("written:", *((p.name, p.stat().st_size) for p in sorted(OUT.glob("*.svg"))))
