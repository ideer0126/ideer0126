#!/usr/bin/env python3
"""生成主页用的蓝鲸 SVG：星空油画里的座头鲸（不用 PNG，全部由代码画出来）。

要点：
  1. 鲸鱼形体用参数化曲线生成 + 沿圆弧折弯，Catmull-Rom 平滑
  2. 鲸鱼身体是"星空双曝"：体内嵌银河星云与星点，边缘一圈星光
  3. 背景深色星空：银河带 + 星云笔触 + 星点/星芒 + 云海，全是碎笔触堆出的油画感
  4. feTurbulence 位移让笔触与轮廓手抖，加画布颗粒与暗角
"""
import math
import random
from pathlib import Path

OUT = Path(__file__).parent / "assets"
W, H = 1000, 430
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
        top.append((x, W_YC - _profile(t, 0.30, 64, 12)))
        bot.append((x, W_YC + _profile(t, 0.40, 56, 14)))
    return top + list(reversed(bot))


_RAW = {
    "body": _body_points(),
    "fluke": [
        (466, 132), (516, 96), (546, 84), (560, 94),
        (536, 120), (512, 136), (534, 158), (556, 180),
        (548, 196), (504, 178), (466, 156),
    ],
    "fin": [
        (152, 190), (206, 216), (262, 242), (312, 256),
        (322, 247), (292, 230), (240, 206), (186, 184),
    ],
    "dorsal": [(368, 106), (382, 86), (404, 88), (392, 106)],
    "back_light": _body_points()[1:21],
    "fluke_light": [(470, 134), (516, 98), (546, 86), (556, 96)],
    "fin_light": [(158, 192), (208, 218), (264, 244), (308, 254)],
    "pleats": [
        [(104, 186), (148, 198), (200, 204), (254, 203)],
        [(122, 194), (164, 204), (212, 208), (264, 207)],
        [(144, 202), (182, 209), (224, 212), (268, 210)],
    ],
    "crease": [(512, 136), (528, 150), (546, 164), (556, 180)],
}
_EYE_RAW = (150, 141)


def geometry(bent):
    f = (lambda pts: bend(pts)) if bent else (lambda pts: list(pts))
    g = {k: f(v) for k, v in _RAW.items() if k != "pleats"}
    g["pleats"] = [f(p) for p in _RAW["pleats"]]
    g["paths"] = {
        "body": catmull_path(g["body"]),
        "fluke": catmull_path(g["fluke"]),
        "fin": catmull_path(g["fin"]),
        "dorsal": catmull_path(g["dorsal"]),
        "back_light": catmull_path(g["back_light"], closed=False),
        "fluke_light": catmull_path(g["fluke_light"], closed=False),
        "fin_light": catmull_path(g["fin_light"], closed=False),
        "crease": catmull_path(g["crease"], closed=False),
        "pleats": [catmull_path(p, closed=False) for p in g["pleats"]],
    }
    if bent:
        ex, ey, eth = bend_pt(*_EYE_RAW)
    else:
        ex, ey, eth = _EYE_RAW[0], _EYE_RAW[1], 0.0
    g["eye"] = (ex, ey)
    xs = [p[0] for p in g["body"]] + [p[0] for p in g["fluke"]] + [p[0] for p in g["fin"]]
    ys = [p[1] for p in g["body"]] + [p[1] for p in g["fluke"]] + [p[1] for p in g["fin"]]
    g["bbox"] = (min(xs), min(ys), max(xs), max(ys))
    return g


G = geometry(True)


# ------------------------------------------------------------------ 笔触工具
def dab(x, y, length, angle, bow=6):
    a = math.radians(angle)
    x0, y0 = x - math.cos(a) * length / 2, y - math.sin(a) * length / 2
    x1, y1 = x + math.cos(a) * length / 2, y + math.sin(a) * length / 2
    mx = (x0 + x1) / 2 - math.sin(a) * bow
    my = (y0 + y1) / 2 + math.cos(a) * bow
    return f"M{x0:.0f},{y0:.0f}Q{mx:.0f},{my:.0f} {x1:.0f},{y1:.0f}"


def dab_layer(rnd, color, opacity, width, count, xr, yr, lo, hi, tilt=6, bow=8, cap="butt"):
    d = " ".join(
        dab(rnd.uniform(*xr), rnd.uniform(*yr), rnd.uniform(lo, hi),
            rnd.uniform(-tilt, tilt), rnd.uniform(-bow, bow))
        for _ in range(count)
    )
    return (
        f'<path d="{d}" fill="none" stroke="{color}" stroke-opacity="{opacity}" '
        f'stroke-width="{width}" stroke-linecap="{cap}"/>'
    )


def star_layer(rnd, color, count, xr, yr, sw, op):
    """星点用极短线段 + 圆头笔帽画：几百颗星只占一条 path。"""
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


# ------------------------------------------------------------ 星空鲸鱼本体
def build_whale(uid):
    rnd = random.Random(2026)
    x0, y0, x1, y1 = G["bbox"]
    # 厚涂色块：一块块颜料拍上去，方向和形体一致（不再靠渐变糊出来）
    impasto = []
    for color, op, w, n, y0, y1 in [
        ("#0A1730", 0.44, 11, 40, 150, 205),
        ("#132445", 0.42, 10, 42, 118, 200),
        ("#1E3A66", 0.38, 9, 40, 100, 180),
        ("#2A5288", 0.32, 8, 36, 88, 160),
        ("#3E6FA8", 0.27, 7, 30, 80, 145),
        ("#6E5AA8", 0.22, 6, 22, 95, 175),
        ("#9AB6E0", 0.17, 5, 18, 80, 132),
        ("#0A1230", 0.4, 12, 26, 160, 210),
    ]:
        seg = []
        for _ in range(n):
            bx, by, bth = bend_pt(rnd.uniform(70, 540), rnd.uniform(y0, y1))
            seg.append(dab(bx, by, rnd.uniform(26, 86), math.degrees(bth) + rnd.uniform(-10, 10), rnd.uniform(-7, 7)))
        impasto.append(
            f'<path d="{" ".join(seg)}" fill="none" stroke="{color}" stroke-opacity="{op}" '
            f'stroke-width="{w}" stroke-linecap="butt"/>'
        )
    impasto = "\n        ".join(impasto)
    inner_glow = "\n        ".join(
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{col}" opacity="{op}" filter="url(#{uid}-blur)"/>'
        for cx, cy, rx, ry, col, op in [
            (230, 146, 150, 52, "#4A3F8F", 0.34),
            (350, 136, 120, 44, "#2A4A8C", 0.3),
        ]
    )
    def swirl(n):
        """沿身体里的一条银河带撒星：中间密、两端散。"""
        pts = []
        for _ in range(n):
            t = rnd.uniform(0, 1)
            x = 80 + 450 * t
            y = 150 - 26 * math.sin(math.pi * t) + rnd.gauss(0, 16 + 22 * abs(t - 0.5))
            pts.append(f"M{x:.0f},{y:.0f}h0.01")
        return " ".join(pts)

    inner_stars = "\n        ".join(
        f'<path d="{swirl(int(count * 0.62)) + " " + " ".join(f"M{rnd.uniform(70, 545):.0f},{rnd.uniform(70, 210):.0f}h0.01" for _ in range(int(count * 0.38)))}" '
        f'fill="none" stroke="{color}" stroke-opacity="{op}" stroke-linecap="round" stroke-width="{sw}"/>'
        for color, count, sw, op in [
            ("#FFFFFF", 80, 1.9, ".9"), ("#DCEAFF", 100, 1.3, ".8"),
            ("#FFF0CC", 46, 1.6, ".75"), ("#A9C4FF", 70, 1.0, ".6"),
        ]
    )
    big = "".join(
        sparkle(x, y, s, f"ws{i}", round(rnd.uniform(2.6, 4.4), 1), -round(rnd.uniform(0, 3), 1))
        for i, (x, y, s) in enumerate([(150, 118, 7), (250, 100, 5.5), (350, 118, 6.5), (215, 168, 5), (430, 140, 5.5)])
    )
    pleats = "".join(
        f'<path d="{d}" fill="none" stroke="#9FD2E4" stroke-opacity=".1" stroke-width="2" stroke-linecap="round"/>'
        for d in G["paths"]["pleats"]
    )
    # 边缘光拆成一截截短笔，像一笔笔点上去的高光
    rim_segs, rim_segs2 = [], []
    pts = G["back_light"]
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        ang = math.degrees(math.atan2(by - ay, bx - ax))
        rim_segs.append(dab((ax + bx) / 2, (ay + by) / 2 - 1, math.hypot(bx - ax, by - ay) * 1.25, ang, rnd.uniform(-2, 2)))
    fpts = G["fluke_light"]
    for i in range(len(fpts) - 1):
        (ax, ay), (bx, by) = fpts[i], fpts[i + 1]
        ang = math.degrees(math.atan2(by - ay, bx - ax))
        rim_segs2.append(dab((ax + bx) / 2, (ay + by) / 2 - 1, math.hypot(bx - ax, by - ay) * 1.3, ang, rnd.uniform(-2, 2)))
    rim = (f'<path d="{" ".join(rim_segs)}" fill="none" stroke="#EAF6FF" stroke-opacity=".8" '
           f'stroke-width="5.5" stroke-linecap="butt" filter="url(#{uid}-soft)"/>')
    rim2 = (f'<path d="{" ".join(rim_segs2)}" fill="none" stroke="#D6EEFF" stroke-opacity=".55" '
            f'stroke-width="4" stroke-linecap="butt" filter="url(#{uid}-soft)"/>')
    eye_x, eye_y = G["eye"]
    return f"""
  <defs>
    <linearGradient id="{uid}-skin" gradientUnits="userSpaceOnUse" x1="{x0 + (x1 - x0) * 0.05:.0f}" y1="{y0:.0f}" x2="{x0 + (x1 - x0) * 0.5:.0f}" y2="{y1:.0f}">
      <stop offset="0" stop-color="#3E72B0"/>
      <stop offset="0.24" stop-color="#22406F"/>
      <stop offset="0.55" stop-color="#132445"/>
      <stop offset="0.82" stop-color="#0B1530"/>
      <stop offset="1" stop-color="#050A16"/>
    </linearGradient>
    <linearGradient id="{uid}-fin" gradientUnits="userSpaceOnUse" x1="{x0 + 60:.0f}" y1="{y0 + 80:.0f}" x2="{x0 + 230:.0f}" y2="{y1:.0f}">
      <stop offset="0" stop-color="#2C5C96"/>
      <stop offset="1" stop-color="#0A1730"/>
    </linearGradient>
    <radialGradient id="{uid}-aura">
      <stop offset="0" stop-color="#BFE4FF" stop-opacity=".3"/>
      <stop offset="0.5" stop-color="#5B7FD8" stop-opacity=".16"/>
      <stop offset="1" stop-color="#2A3A7C" stop-opacity="0"/>
    </radialGradient>
    <filter id="{uid}-blur" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="11"/>
    </filter>
    <filter id="{uid}-soft" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="3.6"/>
    </filter>
    <filter id="{uid}-brush" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="0.3"/>
    </filter>
    <filter id="{uid}-paint" x="-10%" y="-10%" width="120%" height="120%">
      <feTurbulence type="fractalNoise" baseFrequency="0.013 0.02" numOctaves="3" seed="7" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="7" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <clipPath id="{uid}-clip">
      <path d="{G['paths']['body']}"/><path d="{G['paths']['fluke']}"/><path d="{G['paths']['fin']}"/>
    </clipPath>
  </defs>
  <ellipse cx="{(x0 + x1) / 2:.0f}" cy="{(y0 + y1) / 2:.0f}" rx="{(x1 - x0) * 0.66:.0f}" ry="{(y1 - y0) * 0.86:.0f}" fill="url(#{uid}-aura)"/>
  <g filter="url(#{uid}-paint)">
    <g filter="url(#{uid}-soft)" opacity=".85">
      <path d="{G['paths']['body']}" fill="none" stroke="#03060F" stroke-width="16"/>
      <path d="{G['paths']['fluke']}" fill="none" stroke="#03060F" stroke-width="13"/>
    </g>
    <path d="{G['paths']['fin']}" fill="url(#{uid}-fin)"/>
    <path d="{G['paths']['dorsal']}" fill="url(#{uid}-fin)"/>
    <path d="{G['paths']['body']}" fill="url(#{uid}-skin)"/>
    <path d="{G['paths']['fluke']}" fill="url(#{uid}-skin)"/>
    <g clip-path="url(#{uid}-clip)">
      <g filter="url(#{uid}-brush)">
        {inner_glow}
      </g>
      {impasto}
      {inner_stars}
      {big}
      <path d="{G['paths']['fin_light']}" fill="none" stroke="#CFE9FF" stroke-opacity=".22" stroke-width="5" stroke-linecap="round" filter="url(#{uid}-soft)"/>
      {rim}
      {rim2}
      {pleats}
      <path d="{G['paths']['body']}" fill="none" stroke="#03060F" stroke-opacity=".5" stroke-width="13" filter="url(#{uid}-blur)"/>
      <path d="{G['paths']['fluke']}" fill="none" stroke="#03060F" stroke-opacity=".45" stroke-width="10" filter="url(#{uid}-blur)"/>
      <path d="{G['paths']['crease']}" fill="none" stroke="#03060F" stroke-opacity=".4" stroke-width="7" stroke-linecap="round" filter="url(#{uid}-soft)"/>
    </g>
    <circle cx="{eye_x - 11:.1f}" cy="{eye_y - 5:.1f}" r="11" fill="#9AD4E8" opacity=".16" filter="url(#{uid}-soft)"/>
    <circle cx="{eye_x:.1f}" cy="{eye_y:.1f}" r="6.4" fill="#02060F"/>
    <circle cx="{eye_x - 1.8:.1f}" cy="{eye_y - 1.8:.1f}" r="1.9" fill="#EAF6FF" opacity=".95"/>
  </g>
  <style>
    @keyframes twk{{0%,100%{{opacity:.28}}50%{{opacity:.95}}}}
  </style>"""


# ------------------------------------------------------------- 星空油画场景
def scene_svg():
    rnd = random.Random(1899)
    sky_impasto = "\n      ".join(
        dab_layer(rnd, color, op, w, n, xr, yr, lo, hi, tilt, 10, cap="butt")
        for color, op, w, n, xr, yr, lo, hi, tilt in [
            ("#080D22", 0.5, 26, 70, (-40, 1040), (0, 430), 46, 120, 14),
            ("#0D1330", 0.46, 22, 70, (-40, 1040), (0, 430), 42, 110, 15),
            ("#151C44", 0.42, 18, 66, (-30, 1030), (0, 430), 38, 100, 16),
            ("#1E2460", 0.36, 14, 62, (0, 1000), (20, 430), 34, 92, 18),
            ("#2A2E7C", 0.3, 11, 54, (60, 960), (40, 400), 30, 84, 20),
            ("#3A3F92", 0.24, 9, 42, (120, 920), (60, 380), 26, 74, 22),
            ("#4A4AA8", 0.18, 7, 30, (180, 880), (80, 340), 22, 62, 24),
            ("#6E5AA8", 0.14, 5, 20, (220, 860), (60, 300), 18, 54, 26),
        ]
    )
    nebula = "\n      ".join(
        dab_layer(rnd, color, op, w, n, xr, yr, 30, 120, tilt, 14)
        for color, op, w, n, xr, yr, tilt in [
            ("#1A2050", 0.4, 26, 34, (-40, 1040), (0, 430), 18),
            ("#2A2E6E", 0.32, 20, 30, (60, 940), (0, 380), 20),
            ("#453A8C", 0.24, 15, 26, (120, 900), (20, 330), 22),
            ("#6E3A63", 0.16, 12, 18, (200, 860), (0, 260), 24),
            ("#1E5F6B", 0.18, 13, 20, (60, 700), (120, 430), 16),
            ("#0A1230", 0.4, 34, 24, (-40, 1040), (150, 430), 14),
        ]
    )
    stars = "\n      ".join(
        star_layer(rnd, color, count, (-20, 1020), (0, 430), sw, op)
        for color, count, sw, op in [
            ("#FFFFFF", 150, 1.6, ".85"), ("#DCEAFF", 190, 1.1, ".7"),
            ("#FFF3D6", 70, 1.4, ".7"), ("#A9C4FF", 150, 0.9, ".55"),
        ]
    )
    # 银河带：沿对角线再撒一层密星
    stars += "\n      " + "\n      ".join(
        f'<path d="{" ".join(f"M{280 + i * 5.4 + rnd.uniform(-70, 70):.0f},{400 - i * 2.2 + rnd.uniform(-90, 90):.0f}h0.01" for i in range(count))}" '
        f'fill="none" stroke="{color}" stroke-opacity="{op}" stroke-linecap="round" stroke-width="{sw}"/>'
        for color, count, sw, op in [("#FFFFFF", 120, 1.5, ".8"), ("#CBDCFF", 160, 1.0, ".6")]
    )
    sparkles = "".join(
        sparkle(x, y, s, f"sp{i}", round(rnd.uniform(3.0, 5.6), 1), -round(rnd.uniform(0, 3.4), 1), c, o)
        for i, (x, y, s, c, o) in enumerate([
            (150, 96, 10, "#FFFFFF", ".85"), (392, 58, 7, "#DCEAFF", ".8"),
            (704, 108, 8.5, "#FFF3D6", ".8"), (884, 220, 6, "#FFFFFF", ".7"),
            (238, 330, 7, "#CBDCFF", ".7"), (800, 44, 5.5, "#FFFFFF", ".7"),
        ])
    )
    clouds = "\n      ".join(
        dab_layer(rnd, color, op, w, n, (-40, 1040), yr, 40, 150, 5, 16)
        for color, op, w, n, yr in [
            ("#0B1734", 0.35, 30, 26, (330, 430)),
            ("#16264E", 0.28, 22, 24, (340, 430)),
            ("#2A3A7C", 0.2, 16, 18, (355, 430)),
            ("#4A5AA0", 0.14, 11, 12, (370, 430)),
        ]
    )
    trail = "".join(
        f'<circle cx="{700 + i * 26 + rnd.uniform(-8, 8):.0f}" cy="{296 - i * 20 + rnd.uniform(-10, 10):.0f}" '
        f'r="{rnd.uniform(0.8, 2.4):.1f}" fill="#EAF6FF" opacity="{rnd.uniform(0.2, 0.7):.2f}"/>'
        for i in range(20)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="星空油画：银河里的蓝色座头鲸">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0.18" y2="1">
      <stop offset="0" stop-color="#03050E"/>
      <stop offset="0.34" stop-color="#060B1E"/>
      <stop offset="0.68" stop-color="#0A1330"/>
      <stop offset="1" stop-color="#101B44"/>
    </linearGradient>
    <radialGradient id="milky" cx="0.34" cy="0.72" r="0.72">
      <stop offset="0" stop-color="#7E8FD8" stop-opacity=".15"/>
      <stop offset="0.45" stop-color="#4A4A9E" stop-opacity=".08"/>
      <stop offset="1" stop-color="#0A1330" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="moon">
      <stop offset="0" stop-color="#EAF4FF" stop-opacity=".36"/>
      <stop offset="0.4" stop-color="#8FA8E8" stop-opacity=".18"/>
      <stop offset="1" stop-color="#2A3A7C" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="vig" cx="0.5" cy="0.46" r="0.82">
      <stop offset="0.5" stop-color="#000000" stop-opacity="0"/>
      <stop offset="0.82" stop-color="#000205" stop-opacity=".45"/>
      <stop offset="1" stop-color="#000000" stop-opacity=".85"/>
    </radialGradient>
    <filter id="wobble" x="-6%" y="-6%" width="112%" height="112%">
      <feTurbulence type="fractalNoise" baseFrequency="0.016 0.026" numOctaves="4" seed="5" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="9" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="slightblur" x="-6%" y="-6%" width="112%" height="112%">
      <feGaussianBlur stdDeviation="0.35"/>
    </filter>
    <filter id="softlight" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="24"/>
    </filter>
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" seed="9"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>
    <filter id="canvas" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.01 0.4" numOctaves="2" seed="3"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>
    <clipPath id="frame"><rect x="0" y="0" width="{W}" height="{H}" rx="26"/></clipPath>
  </defs>

  <rect x="0" y="0" width="{W}" height="{H}" rx="26" fill="url(#sky)"/>

  <g clip-path="url(#frame)">
    <g filter="url(#slightblur)">
      <g filter="url(#wobble)">
        {sky_impasto}
        {nebula}
      </g>
    </g>
    <ellipse cx="340" cy="300" rx="520" ry="240" fill="url(#milky)"/>
    <ellipse cx="836" cy="92" rx="180" ry="150" fill="url(#moon)"/>

    <g filter="url(#slightblur)">
      {stars}
    </g>
    {sparkles}
    {trail}

    <g transform="translate(258,26) scale(0.86)">
      <g class="bob">
        <g transform="rotate(-7,308,198)">
          {build_whale('w')}
        </g>
      </g>
    </g>

    <g filter="url(#softlight)">
      {clouds}
    </g>

    <rect x="0" y="0" width="{W}" height="{H}" filter="url(#canvas)" opacity=".06"/>
    <rect x="0" y="0" width="{W}" height="{H}" filter="url(#grain)" opacity=".1"/>
    <rect x="0" y="0" width="{W}" height="{H}" fill="url(#vig)"/>
  </g>
  <rect x="0.75" y="0.75" width="{W - 1}.5" height="{H - 1}.5" rx="25.5" fill="none" stroke="#4A5AA0" stroke-opacity=".35" stroke-width="1.5"/>

  <style>
    @keyframes bob{{0%,100%{{transform:translateY(0) rotate(0deg)}}50%{{transform:translateY(-16px) rotate(-1.4deg)}}}}
    .bob{{animation:bob 11s ease-in-out infinite}}
    @keyframes twk{{0%,100%{{opacity:.28}}50%{{opacity:.95}}}}
  </style>
</svg>
"""


OUT.mkdir(exist_ok=True)
(OUT / "starry-whale.svg").write_text(scene_svg(), encoding="utf-8")
print("written:", *((p.name, p.stat().st_size) for p in sorted(OUT.glob("*.svg"))))
