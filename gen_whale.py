#!/usr/bin/env python3
"""生成主页用的蓝鲸 SVG：临摹《星空·鲸鱼的梦》（丙烯底 + 油画细节）。

对照原图的要点：
  1. 竖构图 3:4，鲸鱼横贯画面中部，头朝右、尾在左上，胸鳍斜向下摆
  2. 天空是"发光的天青蓝"：顶部深藏青星空 → 中部亮蓝辉光 → 底部云海
  3. 座头鲸：背深到近黑，腹部/喉部大片白并带长条腹褶，胸鳍长而带白边
  4. 笔触：长条软笔触画云，鲸鱼身上顺形体走的长条笔触，画布颗粒
"""
import math
import random
from pathlib import Path

OUT = Path(__file__).parent / "assets"
W, H = 900, 1200
W_X0, W_YC, W_LEN = 66.0, 146.0, 400.0
BEND_R = 900.0


# ------------------------------------------------------------------ 形体工具
def catmull_path(points, closed=True):
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


def bend_pt(x, y, R=BEND_R):
    th = (x - W_X0) / R
    dy = y - W_YC
    return (
        W_X0 + R * math.sin(th) - dy * math.sin(th),
        W_YC + R - R * math.cos(th) + dy * math.cos(th),
        th,
    )


def bend(pts):
    return [(bx, by) for bx, by, _ in (bend_pt(x, y) for x, y in pts)]


def _profile(t, peak_t, amp, floor):
    k = math.log(0.5) / math.log(peak_t)
    return floor + amp * math.sin(math.pi * (t ** k)) ** 0.9


def _body_points(steps=22):
    top, bot = [], []
    for i in range(steps + 1):
        t = i / steps
        x = W_X0 + W_LEN * t
        top.append((x, W_YC - _profile(t, 0.28, 32, 8)))
        bot.append((x, W_YC + _profile(t, 0.40, 28, 9)))
    return top + list(reversed(bot))


_BODY = _body_points()
_RAW = {
    "body": _BODY,
    "fluke": [
        (466, 132), (516, 96), (546, 84), (560, 94),
        (536, 120), (512, 136), (534, 158), (556, 180),
        (548, 196), (504, 178), (466, 156),
    ],
    "fin": [
        (140, 172), (188, 198), (240, 226), (292, 248),
        (304, 236), (262, 212), (212, 188), (168, 166),
    ],
    "fin2": [
        (154, 166), (202, 190), (252, 216), (300, 236),
        (310, 225), (272, 202), (224, 180), (180, 160),
    ],
    "dorsal": [(362, 122), (374, 104), (394, 106), (384, 122)],
    "back_light": _BODY[1:21],
    "fluke_light": [(470, 134), (516, 98), (546, 86), (556, 96)],
    "fin_light": [(144, 174), (192, 200), (244, 228), (290, 244)],
    "belly_line": _BODY[24:34],
    "jaw": [(72, 158), (110, 166), (156, 170), (204, 170)],
    "pleats": [
        [(100, 172), (136, 182), (176, 189), (216, 191)],
        [(108, 178), (144, 188), (184, 194), (224, 195)],
        [(118, 184), (152, 192), (192, 197), (232, 198)],
        [(130, 188), (164, 196), (202, 200), (242, 200)],
    ],
}
_EYE_RAW = (150, 141)


def geometry():
    """先把形体折弯，再整体左右翻转（头朝右，与原图一致）。

    注意：翻转必须绕同一条轴，否则身体翻过去了、腹褶和胸鳍还留在原地。
    """
    bent = {
        k: ([bend(p) for p in v] if k == "pleats" else bend(v))
        for k, v in _RAW.items()
    }
    xs = [p[0] for p in bent["body"]]
    c = min(xs) + max(xs)

    def m(pts):
        return [(c - x, y) for x, y in pts]

    g = {k: ([m(p) for p in v] if k == "pleats" else m(v)) for k, v in bent.items()}
    g["paths"] = {
        "body": catmull_path(g["body"]),
        "fluke": catmull_path(g["fluke"]),
        "fin": catmull_path(g["fin"]),
        "fin2": catmull_path(g["fin2"]),
        "dorsal": catmull_path(g["dorsal"]),
        "back_light": catmull_path(g["back_light"], closed=False),
        "fluke_light": catmull_path(g["fluke_light"], closed=False),
        "fin_light": catmull_path(g["fin_light"], closed=False),
        "belly_line": catmull_path(g["belly_line"], closed=False),
        "jaw": catmull_path(g["jaw"], closed=False),
        "pleats": [catmull_path(p, closed=False) for p in g["pleats"]],
    }
    ex, ey, _ = bend_pt(*_EYE_RAW)
    xs = [p[0] for p in g["body"]] + [p[0] for p in g["fluke"]] + [p[0] for p in g["fin"]]
    ys = [p[1] for p in g["body"]] + [p[1] for p in g["fluke"]] + [p[1] for p in g["fin"]]
    g["eye"] = (c - ex, ey)
    g["bbox"] = (min(xs), min(ys), max(xs), max(ys))
    return g


G = geometry()


# ------------------------------------------------------------------ 笔触工具
def dab(x, y, length, angle, bow=6):
    a = math.radians(angle)
    x0, y0 = x - math.cos(a) * length / 2, y - math.sin(a) * length / 2
    x1, y1 = x + math.cos(a) * length / 2, y + math.sin(a) * length / 2
    mx = (x0 + x1) / 2 - math.sin(a) * bow
    my = (y0 + y1) / 2 + math.cos(a) * bow
    return f"M{x0:.0f},{y0:.0f}Q{mx:.0f},{my:.0f} {x1:.0f},{y1:.0f}"


def dab_layer(rnd, color, opacity, width, count, xr, yr, lo, hi, tilt=6, bow=8):
    d = " ".join(
        dab(rnd.uniform(*xr), rnd.uniform(*yr), rnd.uniform(lo, hi),
            rnd.uniform(-tilt, tilt), rnd.uniform(-bow, bow))
        for _ in range(count)
    )
    return (
        f'<path d="{d}" fill="none" stroke="{color}" stroke-opacity="{opacity}" '
        f'stroke-width="{width}" stroke-linecap="butt"/>'
    )


def star_layer(rnd, color, count, xr, yr, sw, op):
    d = " ".join(f"M{rnd.uniform(*xr):.0f},{rnd.uniform(*yr):.0f}h0.01" for _ in range(count))
    return (
        f'<path d="{d}" fill="none" stroke="{color}" stroke-opacity="{op}" '
        f'stroke-linecap="round" stroke-width="{sw}"/>'
    )


def sparkle(x, y, s, cls, dur, delay, color="#FFFFFF", op=".95"):
    return (
        f'<path class="{cls}" d="M {x},{y - s} Q {x + s * 0.2},{y - s * 0.2} {x + s},{y} '
        f'Q {x + s * 0.2},{y + s * 0.2} {x},{y + s} Q {x - s * 0.2},{y + s * 0.2} {x - s},{y} '
        f'Q {x - s * 0.2},{y - s * 0.2} {x},{y - s} Z" fill="{color}" opacity="{op}"/>'
        f"<style>.{cls}{{animation:twk {dur}s ease-in-out {delay}s infinite}}</style>"
    )


# -------------------------------------------------------------------- 鲸鱼
def build_whale(uid):
    rnd = random.Random(2026)
    x0, y0, x1, y1 = G["bbox"]
    skin = []
    for color, op, w, n, ya, yb in [
        ("#081226", 0.55, 15, 30, 112, 168),
        ("#0E2444", 0.5, 13, 30, 118, 176),
        ("#1B4576", 0.42, 11, 28, 122, 172),
        ("#2E6FA8", 0.34, 9, 22, 126, 166),
        ("#4A93C8", 0.26, 7, 16, 124, 158),
        ("#8FC8E8", 0.2, 5, 10, 118, 146),
        ("#DCEAF4", 0.55, 12, 30, 162, 192),
        ("#C3DCEA", 0.5, 9, 24, 168, 196),
        ("#EAF4FA", 0.42, 6, 16, 172, 194),
        ("#12294A", 0.42, 11, 18, 150, 186),
    ]:
        seg = []
        for _ in range(n):
            bx, by, bth = bend_pt(rnd.uniform(70, 540), rnd.uniform(ya, yb))
            seg.append(dab(bx, by, rnd.uniform(40, 130), math.degrees(bth) + rnd.uniform(-2.5, 2.5), rnd.uniform(-5, 5)))
        skin.append(
            f'<path d="{" ".join(seg)}" fill="none" stroke="{color}" stroke-opacity="{op}" '
            f'stroke-width="{w}" stroke-linecap="butt"/>'
        )
    skin = "\n        ".join(skin)
    pleats = "".join(
        f'<path d="{d}" fill="none" stroke="#12314F" stroke-opacity=".4" stroke-width="2.8" stroke-linecap="butt"/>'
        f'<path d="{d}" fill="none" stroke="#F6FBFF" stroke-opacity=".45" stroke-width="2" stroke-linecap="butt" transform="translate(0,-4.5)"/>'
        for d in G["paths"]["pleats"]
    )
    rim, rim2 = [], []
    bpts = G["back_light"]
    for i in range(len(bpts) - 1):
        (ax, ay), (bx, by) = bpts[i], bpts[i + 1]
        ang = math.degrees(math.atan2(by - ay, bx - ax))
        rim.append(dab((ax + bx) / 2, (ay + by) / 2 - 2, math.hypot(bx - ax, by - ay) * 1.2, ang, rnd.uniform(-2, 2)))
    fpts = G["fluke_light"]
    for i in range(len(fpts) - 1):
        (ax, ay), (bx, by) = fpts[i], fpts[i + 1]
        ang = math.degrees(math.atan2(by - ay, bx - ax))
        rim2.append(dab((ax + bx) / 2, (ay + by) / 2 - 2, math.hypot(bx - ax, by - ay) * 1.25, ang, rnd.uniform(-2, 2)))
    eye_x, eye_y = G["eye"]
    return f"""
  <defs>
    <linearGradient id="{uid}-skin" gradientUnits="userSpaceOnUse" x1="0" y1="102" x2="0" y2="200">
      <stop offset="0" stop-color="#0C1A34"/>
      <stop offset="0.34" stop-color="#0A1730"/>
      <stop offset="0.6" stop-color="#164066"/>
      <stop offset="0.74" stop-color="#8FB6D2"/>
      <stop offset="0.86" stop-color="#D8E8F2"/>
      <stop offset="1" stop-color="#F2F8FC"/>
    </linearGradient>
    <linearGradient id="{uid}-fluke" gradientUnits="userSpaceOnUse" x1="0" y1="90" x2="0" y2="200">
      <stop offset="0" stop-color="#0C1E3A"/>
      <stop offset="0.6" stop-color="#16385F"/>
      <stop offset="1" stop-color="#8FB4D0"/>
    </linearGradient>
    <linearGradient id="{uid}-fin" gradientUnits="userSpaceOnUse" x1="{x0:.0f}" y1="{y0 + 90:.0f}" x2="{x0 + 250:.0f}" y2="{y1:.0f}">
      <stop offset="0" stop-color="#0C1E3A"/>
      <stop offset="0.34" stop-color="#2A5480"/>
      <stop offset="1" stop-color="#E2EEF6"/>
    </linearGradient>
    <filter id="{uid}-blur" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="10"/>
    </filter>
    <filter id="{uid}-soft" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="3"/>
    </filter>
    <filter id="{uid}-paint" x="-8%" y="-8%" width="116%" height="116%">
      <feTurbulence type="fractalNoise" baseFrequency="0.012 0.019" numOctaves="3" seed="7" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="8" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <clipPath id="{uid}-clip">
      <path d="{G['paths']['body']}"/><path d="{G['paths']['fluke']}"/><path d="{G['paths']['fin']}"/>
    </clipPath>
  </defs>
  <g filter="url(#{uid}-paint)">
    <path d="{G['paths']['fin2']}" fill="#0B1B36" opacity=".92"/>
    <path d="{G['paths']['fin']}" fill="url(#{uid}-fin)"/>
    <path d="{G['paths']['fin']}" fill="none" stroke="#081226" stroke-opacity=".6" stroke-width="2.4"/>
    <path d="{G['paths']['dorsal']}" fill="#0C1A34"/>
    <path d="{G['paths']['body']}" fill="url(#{uid}-skin)"/>
    <path d="{G['paths']['fluke']}" fill="url(#{uid}-fluke)"/>
    <g clip-path="url(#{uid}-clip)">
      {skin}
      {pleats}
      <path d="{G['paths']['jaw']}" fill="none" stroke="#061224" stroke-opacity=".55" stroke-width="3" stroke-linecap="butt"/>
      <ellipse cx="392" cy="176" rx="150" ry="50" fill="#0A1830" opacity=".8" filter="url(#{uid}-blur)"/>
      <ellipse cx="310" cy="172" rx="96" ry="40" fill="#102A4C" opacity=".55" filter="url(#{uid}-blur)"/>
      <ellipse cx="440" cy="168" rx="110" ry="44" fill="#0A1830" opacity=".7" filter="url(#{uid}-blur)"/>
      <ellipse cx="492" cy="162" rx="86" ry="40" fill="#0A1830" opacity=".82" filter="url(#{uid}-blur)"/>
      <ellipse cx="540" cy="154" rx="70" ry="36" fill="#0A1830" opacity=".85" filter="url(#{uid}-blur)"/>
      <path d="{G['paths']['belly_line']}" fill="none" stroke="#0B1B36" stroke-opacity=".5" stroke-width="16" filter="url(#{uid}-blur)" transform="translate(0,-8)"/>
      <path d="{G['paths']['belly_line']}" fill="none" stroke="#F2F8FC" stroke-opacity=".5" stroke-width="5" filter="url(#{uid}-soft)"/>
      <path d="{' '.join(rim)}" fill="none" stroke="#DCF0FA" stroke-opacity=".7" stroke-width="4.5" stroke-linecap="butt" filter="url(#{uid}-soft)"/>
      <path d="{' '.join(rim2)}" fill="none" stroke="#CFE8F6" stroke-opacity=".5" stroke-width="3.6" stroke-linecap="butt" filter="url(#{uid}-soft)"/>
      <path d="{G['paths']['body']}" fill="none" stroke="#050C1A" stroke-opacity=".45" stroke-width="14" filter="url(#{uid}-blur)"/>
      <path d="{G['paths']['fluke']}" fill="none" stroke="#050C1A" stroke-opacity=".4" stroke-width="10" filter="url(#{uid}-blur)"/>
    </g>
    <circle cx="{eye_x:.1f}" cy="{eye_y:.1f}" r="5" fill="#02060F"/>
    <circle cx="{eye_x + 1.6:.1f}" cy="{eye_y - 1.6:.1f}" r="1.6" fill="#EAF4FA" opacity=".9"/>
  </g>
  <style>
    @keyframes twk{{0%,100%{{opacity:.28}}50%{{opacity:.95}}}}
  </style>"""


# ------------------------------------------------------------------ 场景
WHALE_SCALE = 1.62
WHALE_ROT = 9.0
_ROT_C = ((G["bbox"][0] + G["bbox"][2]) / 2, (G["bbox"][1] + G["bbox"][3]) / 2)


def place_pt(x, y):
    a = math.radians(WHALE_ROT)
    dx, dy = x - _ROT_C[0], y - _ROT_C[1]
    rx = dx * math.cos(a) - dy * math.sin(a) + _ROT_C[0]
    ry = dx * math.sin(a) + dy * math.cos(a) + _ROT_C[1]
    return rx * WHALE_SCALE + _TX, ry * WHALE_SCALE + _TY


_bx0, _by0, _bx1, _by1 = G["bbox"]
_r = []
for _x, _y in [(x, y) for x in (_bx0, _bx1) for y in (_by0, _by1)]:
    _a = math.radians(WHALE_ROT)
    _dx, _dy = _x - _ROT_C[0], _y - _ROT_C[1]
    _r.append(((_dx * math.cos(_a) - _dy * math.sin(_a) + _ROT_C[0]) * WHALE_SCALE,
               (_dx * math.sin(_a) + _dy * math.cos(_a) + _ROT_C[1]) * WHALE_SCALE))
_TX = W * 0.5 - (min(p[0] for p in _r) + max(p[0] for p in _r)) / 2
_TY = H * 0.44 - (min(p[1] for p in _r) + max(p[1] for p in _r)) / 2


def scene_svg():
    rnd = random.Random(111)
    clouds = "\n      ".join(
        dab_layer(rnd, color, op, round(w * 0.8), n, (-60, 960), yr, lo, hi, tilt, 16)
        for color, op, w, n, yr, lo, hi, tilt in [
            ("#101E3C", 0.5, 40, 26, (20, 300), 120, 320, 10),
            ("#16264E", 0.42, 32, 24, (40, 340), 110, 280, 12),
            ("#1E3A6A", 0.34, 26, 22, (120, 420), 100, 240, 14),
            ("#2E6FA8", 0.26, 20, 20, (240, 560), 90, 220, 16),
            ("#4FA0D4", 0.22, 16, 18, (300, 620), 80, 200, 18),
            ("#8FCBEE", 0.18, 12, 14, (340, 640), 70, 170, 20),
            ("#BFE4F8", 0.14, 9, 10, (380, 660), 60, 150, 22),
            ("#0B3A72", 0.36, 46, 24, (620, 1150), 160, 380, 8),
            ("#0A2E60", 0.4, 54, 22, (700, 1200), 180, 420, 6),
            ("#1C63A8", 0.26, 30, 20, (860, 1200), 140, 320, 7),
            ("#3E8FD0", 0.2, 20, 16, (900, 1200), 120, 280, 8),
            ("#7FC4EE", 0.14, 14, 12, (940, 1200), 100, 240, 9),
        ]
    )
    stars = "\n      ".join(
        star_layer(rnd, color, count, (-20, 920), yr, sw, op)
        for color, count, sw, op, yr in [
            ("#FFFFFF", 210, 1.7, ".85", (0, 520)),
            ("#DCEAFF", 180, 1.2, ".7", (0, 560)),
            ("#A9C4FF", 140, 1.0, ".55", (0, 620)),
            ("#FFFFFF", 90, 1.4, ".6", (560, 900)),
            ("#CFE4FF", 70, 1.0, ".45", (860, 1200)),
        ]
    )
    sparkles = "".join(
        sparkle(x, y, s, f"sp{i}", round(rnd.uniform(3.0, 5.4), 1), -round(rnd.uniform(0, 3.2), 1), c, o)
        for i, (x, y, s, c, o) in enumerate([
            (74, 400, 11, "#FFFFFF", ".95"), (318, 516, 9, "#EAF4FA", ".9"),
            (786, 668, 8.5, "#FFFFFF", ".9"), (150, 236, 7, "#DCEAFF", ".8"),
            (628, 300, 7, "#FFFFFF", ".8"), (836, 430, 6, "#CFE4FF", ".7"),
            (420, 742, 6, "#EAF4FA", ".65"), (238, 900, 5.5, "#FFFFFF", ".6"),
        ])
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="星空油画：鲸鱼的梦">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0.12" y2="1">
      <stop offset="0" stop-color="#060B1A"/>
      <stop offset="0.16" stop-color="#0A1631"/>
      <stop offset="0.32" stop-color="#16406F"/>
      <stop offset="0.46" stop-color="#2268A8"/>
      <stop offset="0.58" stop-color="#2E7FC0"/>
      <stop offset="0.72" stop-color="#0E4A8C"/>
      <stop offset="0.88" stop-color="#0C4482"/>
      <stop offset="1" stop-color="#0E3568"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#8FD0F6" stop-opacity=".62"/>
      <stop offset="0.45" stop-color="#3E93D8" stop-opacity=".26"/>
      <stop offset="1" stop-color="#1B4D84" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glow2" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#BFE8FA" stop-opacity=".38"/>
      <stop offset="1" stop-color="#3E93D8" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="vig" cx="0.5" cy="0.44" r="0.78">
      <stop offset="0.5" stop-color="#000000" stop-opacity="0"/>
      <stop offset="0.82" stop-color="#00030A" stop-opacity=".34"/>
      <stop offset="1" stop-color="#000206" stop-opacity=".72"/>
    </radialGradient>
    <filter id="wobble" x="-6%" y="-6%" width="112%" height="112%">
      <feTurbulence type="fractalNoise" baseFrequency="0.012 0.02" numOctaves="4" seed="5" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="13" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="cloudsoft" x="-10%" y="-10%" width="120%" height="120%">
      <feGaussianBlur stdDeviation="11"/>
    </filter>
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="3" seed="9"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>
    <filter id="canvas" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.008 0.36" numOctaves="2" seed="3"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>
    <clipPath id="frame"><rect x="0" y="0" width="{W}" height="{H}" rx="14"/></clipPath>
  </defs>

  <rect x="0" y="0" width="{W}" height="{H}" rx="14" fill="url(#sky)"/>

  <g clip-path="url(#frame)">
    <ellipse cx="{W * 0.54:.0f}" cy="{H * 0.43:.0f}" rx="560" ry="420" fill="url(#glow)"/>
    <ellipse cx="{W * 0.66:.0f}" cy="{H * 0.42:.0f}" rx="300" ry="220" fill="url(#glow2)"/>

    <g filter="url(#wobble)">
      {clouds}
    </g>

    <g filter="url(#cloudsoft)" opacity=".62">
      {dab_layer(rnd, "#C8EAFB", 0.34, 24, 18, (-40, 940), (330, 640), 130, 320, 18, 22)}
      {dab_layer(rnd, "#6FB8E4", 0.3, 34, 16, (-40, 940), (280, 620), 150, 360, 16, 22)}
      {dab_layer(rnd, "#EAF6FE", 0.22, 15, 12, (200, 900), (360, 600), 110, 260, 20, 18)}
    </g>

    <g>{stars}</g>
    {sparkles}

    <g transform="translate({_TX:.1f},{_TY:.1f}) scale({WHALE_SCALE})">
      <g class="bob">
        <g transform="rotate({WHALE_ROT},{_ROT_C[0]:.1f},{_ROT_C[1]:.1f})">
          {build_whale('w')}
        </g>
      </g>
    </g>

    <g filter="url(#cloudsoft)" opacity=".5">
      {dab_layer(rnd, "#0A2E60", 0.4, 40, 14, (-60, 960), (900, 1200), 160, 360, 6, 20)}
      {dab_layer(rnd, "#8FCBEE", 0.16, 16, 12, (-40, 940), (960, 1200), 120, 280, 8, 18)}
    </g>

    <rect x="0" y="0" width="{W}" height="{H}" filter="url(#canvas)" opacity=".06"/>
    <rect x="0" y="0" width="{W}" height="{H}" filter="url(#grain)" opacity=".1"/>
    <rect x="0" y="0" width="{W}" height="{H}" fill="url(#vig)"/>
  </g>

  <style>
    @keyframes bob{{0%,100%{{transform:translateY(0) rotate(0deg)}}50%{{transform:translateY(-18px) rotate(-0.8deg)}}}}
    .bob{{animation:bob 12s ease-in-out infinite}}
    @keyframes twk{{0%,100%{{opacity:.28}}50%{{opacity:.95}}}}
  </style>
</svg>
"""


OUT.mkdir(exist_ok=True)
(OUT / "starry-whale.svg").write_text(scene_svg(), encoding="utf-8")
print("written:", *((p.name, p.stat().st_size) for p in sorted(OUT.glob("*.svg"))))
