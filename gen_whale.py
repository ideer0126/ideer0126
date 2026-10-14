#!/usr/bin/env python3
"""生成主页用的蓝鲸 SVG：莫奈睡莲池 + 跃出水面的座头鲸。

要点：
  1. 鲸鱼形体用参数化曲线生成，再沿圆弧"折弯"成跃起姿态（不是简单旋转）
  2. 全身/水面/倒影都是碎笔触（同色同宽并进一条 path，体积小）
  3. 莫奈睡莲池配色：水面色阶亮起来，蓝→青→薰衣草，配粉白睡莲与荷叶
  4. feTurbulence 位移让笔触带手抖感，加画布颗粒与柔和暗角
"""
import math
import random
from pathlib import Path

OUT = Path(__file__).parent / "assets"

W_X0, W_YC, W_LEN = 66.0, 146.0, 400.0
BEND_R = 900.0          # 折弯半径：越小跃得越弯
WATER_Y = 252           # 画面里的水线


# ------------------------------------------------------------------ 形体工具
def catmull_path(points, closed=True):
    """Catmull-Rom 转三次贝塞尔。"""
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
    """把身体中轴弯成圆弧：头在上、尾在下，形成跃起的弧线。"""
    th = (x - W_X0) / R
    dy = y - W_YC
    return (
        W_X0 + R * math.sin(th) + dy * math.sin(th),
        W_YC + R - R * math.cos(th) - dy * math.cos(th),
        th,
    )


def bend(pts, R=BEND_R):
    return [(bx, by) for bx, by, _ in (bend_pt(x, y, R) for x, y in pts)]


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
    """返回某一姿态下的全部路径 + 关键点。"""
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
    g["eye_tilt"] = math.degrees(eth) if bent else 0.0
    xs = [p[0] for p in g["body"]] + [p[0] for p in g["fluke"]] + [p[0] for p in g["fin"]]
    ys = [p[1] for p in g["body"]] + [p[1] for p in g["fluke"]] + [p[1] for p in g["fin"]]
    g["bbox"] = (min(xs), min(ys), max(xs), max(ys))
    return g


G_BREACH = geometry(True)
G_STRAIGHT = geometry(False)


# ------------------------------------------------------------------ 笔触工具
def dab(x, y, length, angle, bow):
    a = math.radians(angle)
    x0, y0 = x - math.cos(a) * length / 2, y - math.sin(a) * length / 2
    x1, y1 = x + math.cos(a) * length / 2, y + math.sin(a) * length / 2
    mx = (x0 + x1) / 2 - math.sin(a) * bow
    my = (y0 + y1) / 2 + math.cos(a) * bow
    return f"M{x0:.0f},{y0:.0f}Q{mx:.0f},{my:.0f} {x1:.0f},{y1:.0f}"


def dab_layer(rnd, color, opacity, width, count, xr, yr, lo, hi, tilt=6, bow=8, tf=None):
    parts = []
    for _ in range(count):
        x, y = rnd.uniform(*xr), rnd.uniform(*yr)
        ln, an = rnd.uniform(lo, hi), rnd.uniform(-tilt, tilt)
        if tf:
            x, y, an = tf(x, y, an)
        parts.append(dab(x, y, ln, an, rnd.uniform(-bow, bow)))
    return (
        f'<path d="{" ".join(parts)}" fill="none" stroke="{color}" stroke-opacity="{opacity}" '
        f'stroke-width="{width}" stroke-linecap="round"/>'
    )


# -------------------------------------------------------------------- 鲸鱼
def build_whale(uid, g, aura=False, shine=1.0, bent=True):
    rnd = random.Random(2026)
    x0, y0, x1, y1 = g["bbox"]
    if bent:
        def tf(x, y, a):
            bx, by, th = bend_pt(x, y)
            return bx, by, a + math.degrees(th)
    else:
        tf = None
    skin = []
    for color, op, w, n, yr in [
        ("#0A2038", 0.5, 9, 30, (162, 212)),
        ("#123A5C", 0.45, 10, 34, (132, 205)),
        ("#1B5580", 0.4, 8, 34, (106, 185)),
        ("#2A7BA4", 0.36, 6, 30, (90, 160)),
        ("#4FA3C4", 0.24, 5, 20, (80, 140)),
        ("#86C8DC", 0.19, 4, 12, (74, 126)),
        ("#2A2E5E", 0.22, 7, 14, (130, 205)),
        ("#B8845E", 0.12, 4, 7, (100, 175)),
    ]:
        skin.append(dab_layer(rnd, color, op * shine, w, n, (70, 545), yr, 14, 52, 8, 7, tf=tf))
    skin = "\n        ".join(skin)
    fin_dabs = dab_layer(rnd, "#0A2440", 0.5, 7, 14, (165, 315), (192, 252), 14, 40, 10, 6, tf=tf)
    fin_dabs2 = dab_layer(rnd, "#2C6E96", 0.4, 5, 12, (165, 315), (190, 248), 12, 34, 10, 5, tf=tf)

    def crest_paths():
        out = []
        for i in range(14):
            cx = 78 + i * 22
            cy = 122 - i * 1.5 + rnd.uniform(-4, 4)
            ln = rnd.uniform(10, 26)
            bow = rnd.uniform(-3, 3)
            if bent:
                bx, by, th = bend_pt(cx, cy)
                first = dab(bx, by, ln, math.degrees(th) - 8, bow)
            else:
                first = dab(cx, cy, ln, rnd.uniform(-14, 4), bow)
            out.append(
                f'<path d="{first}" fill="none" stroke="#CFEFFB" '
                f'stroke-opacity="{rnd.uniform(0.16, 0.4) * shine:.2f}" '
                f'stroke-width="{rnd.uniform(1.6, 3.4):.1f}" stroke-linecap="round"/>'
            )
        return "".join(out)

    crest = crest_paths()
    pleats = "".join(
        f'<path d="{d}" fill="none" stroke="#9FD2E4" stroke-opacity=".13" stroke-width="2" stroke-linecap="round"/>'
        for d in g["paths"]["pleats"]
    )
    aura_el = (
        f'<ellipse cx="{(x0 + x1) / 2:.0f}" cy="{(y0 + y1) / 2:.0f}" '
        f'rx="{(x1 - x0) * 0.62:.0f}" ry="{(y1 - y0) * 0.8:.0f}" fill="url(#{uid}-aura)"/>'
        if aura
        else ""
    )
    eye_x, eye_y = g["eye"]
    return f"""
  <defs>
    <linearGradient id="{uid}-skin" gradientUnits="userSpaceOnUse" x1="{x0 + (x1 - x0) * 0.06:.0f}" y1="{y0:.0f}" x2="{x0 + (x1 - x0) * 0.44:.0f}" y2="{y1:.0f}">
      <stop offset="0" stop-color="#8CCBF0"/>
      <stop offset="0.2" stop-color="#2E7BA6"/>
      <stop offset="0.48" stop-color="#1B5480"/>
      <stop offset="0.76" stop-color="#123A5C"/>
      <stop offset="1" stop-color="#0E2F4C"/>
    </linearGradient>
    <linearGradient id="{uid}-fin" gradientUnits="userSpaceOnUse" x1="{x0 + 60:.0f}" y1="{y0 + 80:.0f}" x2="{x0 + 220:.0f}" y2="{y1:.0f}">
      <stop offset="0" stop-color="#3B87A8"/>
      <stop offset="1" stop-color="#123A5C"/>
    </linearGradient>
    <radialGradient id="{uid}-aura">
      <stop offset="0" stop-color="#BFF2FB" stop-opacity=".4"/>
      <stop offset="0.55" stop-color="#5FB6D8" stop-opacity=".18"/>
      <stop offset="1" stop-color="#2E7CA0" stop-opacity="0"/>
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
    <clipPath id="{uid}-clip"><path d="{g['paths']['body']}"/><path d="{g['paths']['fluke']}"/><path d="{g['paths']['fin']}"/></clipPath>
  </defs>
  {aura_el}
  <g filter="url(#{uid}-paint)">
    <g filter="url(#{uid}-soft)" opacity=".7">
      <path d="{g['paths']['body']}" fill="none" stroke="#020B16" stroke-width="14"/>
      <path d="{g['paths']['fluke']}" fill="none" stroke="#020B16" stroke-width="12"/>
    </g>
    <path d="{g['paths']['fin']}" fill="url(#{uid}-fin)"/>
    <path d="{g['paths']['dorsal']}" fill="url(#{uid}-fin)"/>
    <path d="{g['paths']['body']}" fill="url(#{uid}-skin)"/>
    <path d="{g['paths']['fluke']}" fill="url(#{uid}-skin)"/>
    <g clip-path="url(#{uid}-clip)">
      {fin_dabs}
      {fin_dabs2}
      <path d="{g['paths']['fin_light']}" fill="none" stroke="#BFE8F5" stroke-opacity=".3" stroke-width="6" stroke-linecap="round" filter="url(#{uid}-soft)"/>
      <g filter="url(#{uid}-brush)">
        {skin}
      </g>
      <path d="{g['paths']['back_light']}" fill="none" stroke="#E2F8FF" stroke-opacity=".62" stroke-width="6" stroke-linecap="round" filter="url(#{uid}-soft)"/>
      <path d="{g['paths']['fluke_light']}" fill="none" stroke="#CBEDFA" stroke-opacity=".5" stroke-width="4.5" stroke-linecap="round" filter="url(#{uid}-soft)"/>
      <g filter="url(#{uid}-soft)">{crest}</g>
      {pleats}
      <path d="{g['paths']['body']}" fill="none" stroke="#061529" stroke-opacity=".4" stroke-width="12" filter="url(#{uid}-blur)"/>
      <path d="{g['paths']['fluke']}" fill="none" stroke="#061529" stroke-opacity=".4" stroke-width="10" filter="url(#{uid}-blur)"/>
      <path d="{g['paths']['crease']}" fill="none" stroke="#061529" stroke-opacity=".35" stroke-width="7" stroke-linecap="round" filter="url(#{uid}-soft)"/>
    </g>
    <circle cx="{eye_x - 11:.1f}" cy="{eye_y - 5:.1f}" r="11" fill="#9AD4E8" opacity=".2" filter="url(#{uid}-soft)"/>
    <circle cx="{eye_x:.1f}" cy="{eye_y:.1f}" r="6.4" fill="#04121F"/>
    <circle cx="{eye_x - 1.7:.1f}" cy="{eye_y - 1.7:.1f}" r="1.7" fill="#DCF6FF" opacity=".85"/>
  </g>
  <style>
    @keyframes twk{{0%,100%{{opacity:.3}}50%{{opacity:.9}}}}
  </style>"""


# ------------------------------------------------------------- 荷叶 / 睡莲
def lily_pad(cx, cy, r, notch_deg, pad_color="#2C5A48"):
    a1, a2 = math.radians(notch_deg + 30), math.radians(notch_deg - 30)
    return (
        f'<path d="M{cx + r * math.cos(a1):.1f},{cy + r * 0.62 * math.sin(a1):.1f} '
        f'A{r:.1f},{r * 0.62:.1f} 0 1 1 {cx + r * math.cos(a2):.1f},{cy + r * 0.62 * math.sin(a2):.1f} '
        f'L{cx:.1f},{cy:.1f} Z" fill="{pad_color}" fill-opacity=".62" '
        f'stroke="#9CCBA8" stroke-opacity=".16" stroke-width="1"/>'
    )


# ------------------------------------------------------- 莫奈睡莲池 + 跃起
WHALE_SCALE = 0.72
WHALE_ROT = 20          # 让身体更陡，像跃起而不是下沉
_ROT_C = (308.0, 198.0)  # 绕身体中心旋转


def place_pt(x, y):
    """把（未变换的）鲸鱼坐标换算到画面坐标，用于对齐水花与倒影。"""
    a = math.radians(WHALE_ROT)
    dx, dy = x - _ROT_C[0], y - _ROT_C[1]
    rx = dx * math.cos(a) - dy * math.sin(a) + _ROT_C[0]
    ry = dx * math.sin(a) + dy * math.cos(a) + _ROT_C[1]
    return rx * WHALE_SCALE + _TX, ry * WHALE_SCALE + _TY


_bx0, _by0, _bx1, _by1 = G_BREACH["bbox"]
_corners = [(x, y) for x in (_bx0, _bx1) for y in (_by0, _by1)]
_raw = []
for _x, _y in _corners:
    _a = math.radians(WHALE_ROT)
    _dx, _dy = _x - _ROT_C[0], _y - _ROT_C[1]
    _raw.append(((_dx * math.cos(_a) - _dy * math.sin(_a) + _ROT_C[0]) * WHALE_SCALE,
                 (_dx * math.sin(_a) + _dy * math.cos(_a) + _ROT_C[1]) * WHALE_SCALE))
_TX = 566.0 - (min(p[0] for p in _raw) + max(p[0] for p in _raw)) / 2
_TY = (WATER_Y + 46) - max(p[1] for p in _raw)
# 出水点：尾柄穿过水线的位置
_cands = [place_pt(x, y) for x, y in G_BREACH["body"] + G_BREACH["fluke"] if x > 380]
_near = min(_cands, key=lambda p: abs(p[1] - WATER_Y))
EXIT_X, EXIT_Y = _near[0], WATER_Y


def scene_svg():
    rnd = random.Random(1899)
    H = 430
    above = []
    for color, op, w, n, yr, tilt in [
        ("#071C2A", 0.5, 24, 40, (0, 120), 8),
        ("#0B2A2E", 0.42, 20, 34, (0, 150), 10),
        ("#123A3A", 0.32, 16, 28, (10, 170), 10),
        ("#0E3048", 0.4, 22, 34, (60, 230), 6),
        ("#16456B", 0.34, 18, 32, (80, 250), 5),
        ("#2A6E97", 0.26, 12, 26, (120, 258), 4),
    ]:
        above.append(dab_layer(rnd, color, op, w, n, (-30, 1030), yr, 22, 84, tilt, 9))
    above = "\n      ".join(above)

    water = []
    for color, op, w, n, yr, tilt in [
        ("#123A5C", 0.4, 22, 34, (WATER_Y, H), 3),
        ("#1B4A72", 0.4, 20, 42, (WATER_Y, H), 3),
        ("#23648C", 0.36, 17, 42, (WATER_Y, H - 10), 3),
        ("#2E7CA0", 0.34, 14, 42, (WATER_Y, H - 20), 4),
        ("#3E93B0", 0.3, 12, 38, (WATER_Y, H - 40), 4),
        ("#5FB0C6", 0.26, 10, 34, (WATER_Y, H - 70), 5),
        ("#7FCBDA", 0.22, 8, 28, (WATER_Y, H - 100), 5),
        ("#9FDCE8", 0.18, 6, 22, (WATER_Y, H - 130), 6),
        ("#6F86C0", 0.18, 9, 24, (WATER_Y + 10, H), 4),
        ("#8FA8D8", 0.15, 7, 20, (WATER_Y, H - 30), 6),
        ("#5F9E8A", 0.14, 8, 18, (WATER_Y + 20, H), 5),
        ("#7FB08A", 0.11, 6, 12, (WATER_Y + 30, H - 10), 7),
        ("#E0B0C0", 0.15, 5, 12, (WATER_Y + 30, H - 20), 8),
        ("#F0D8E0", 0.12, 4, 9, (WATER_Y + 40, H - 40), 8),
        ("#F2E6CE", 0.1, 4, 7, (WATER_Y + 40, H - 60), 9),
    ]:
        water.append(dab_layer(rnd, color, op, w, n, (-30, 1030), yr, 20, 76, tilt, 8))
    water = "\n      ".join(water)

    reflect = dab_layer(rnd, "#DCF2F8", 0.22, 4, 38, (-20, 1020), (WATER_Y - 8, WATER_Y + 50), 26, 96, 2, 5)
    reflect2 = dab_layer(rnd, "#A8DCE8", 0.15, 6, 24, (-20, 1020), (WATER_Y + 20, WATER_Y + 96), 20, 70, 3, 5)

    pads = "".join(
        lily_pad(px, py, pr, rnd.uniform(0, 360), rnd.choice(["#2C5A48", "#356049", "#264F42", "#3E6B52"]))
        for px, py, pr in [
            (104, 374, 20), (246, 414, 26), (368, 386, 17), (498, 420, 22),
            (628, 378, 19), (772, 412, 24), (896, 358, 17), (176, 332, 13),
            (856, 314, 12), (58, 418, 15), (704, 318, 11), (430, 320, 10),
        ]
    )
    pad_light = "".join(
        f'<ellipse cx="{px + rnd.uniform(-pr * 0.5, pr * 0.5):.0f}" cy="{py + rnd.uniform(-pr * 0.35, pr * 0.35):.0f}" '
        f'rx="{rnd.uniform(4, pr * 0.5):.1f}" ry="{rnd.uniform(2, pr * 0.26):.1f}" fill="#8FC8A0" '
        f'opacity="{rnd.uniform(0.16, 0.4):.2f}"/>'
        for px, py, pr in [(104, 374, 20), (246, 414, 26), (498, 420, 22), (772, 412, 24), (628, 378, 19)]
    )
    # 睡莲：小簇花点，别长成"眼睛"
    blooms = ""
    for cx, cy in [(120, 356), (258, 396), (512, 402), (788, 394), (882, 342), (668, 360), (352, 368)]:
        for dx, dy, r, c, o in [
            (0, 0, 5.4, "#F7DEE6", 0.85), (7, 4, 3.8, "#FFF4F7", 0.8),
            (-6, 5, 3.4, "#EBBECD", 0.75), (3, -6, 2.8, "#FFF9FB", 0.75),
            (-4, -3, 2.2, "#F3D6A9", 0.7),
        ]:
            blooms += f'<circle cx="{cx + dx:.0f}" cy="{cy + dy:.0f}" r="{r}" fill="{c}" opacity="{o}"/>'

    # 出水口的水花 / 涟漪 / 顺身而下的水流
    rnd2 = random.Random(77)
    spray = "".join(
        f'<ellipse cx="{EXIT_X + math.cos(a) * rr:.0f}" cy="{EXIT_Y - 6 - math.sin(abs(a)) * rr * 0.85:.0f}" '
        f'rx="{sr * 1.5:.1f}" ry="{sr * 0.55:.1f}" fill="#F4FCFF" opacity="{op:.2f}" '
        f'transform="rotate({math.degrees(a) * 0.35:.0f},{EXIT_X + math.cos(a) * rr:.0f},{EXIT_Y - 6:.0f})"/>'
        for a, rr, sr, op in (
            (rnd2.uniform(-0.35, math.pi + 0.35), rnd2.uniform(30, 190),
             rnd2.uniform(4, 11), rnd2.uniform(0.3, 0.8))
            for _ in range(40)
        )
    )
    foam = "".join(
        f'<ellipse cx="{EXIT_X + rnd2.uniform(-130, 130):.0f}" cy="{EXIT_Y + rnd2.uniform(-6, 16):.0f}" '
        f'rx="{rnd2.uniform(14, 46):.1f}" ry="{rnd2.uniform(4, 11):.1f}" fill="#EAF9FF" '
        f'opacity="{rnd2.uniform(0.2, 0.5):.2f}"/>'
        for _ in range(18)
    )
    droplets = "".join(
        f'<ellipse cx="{EXIT_X + rnd2.uniform(-150, 80):.0f}" cy="{EXIT_Y - rnd2.uniform(8, 160):.0f}" '
        f'rx="{rnd2.uniform(1.2, 3):.1f}" ry="{rnd2.uniform(2, 4.6):.1f}" fill="#DCF2F8" '
        f'opacity="{rnd2.uniform(0.25, 0.6):.2f}"/>'
        for _ in range(22)
    ) + "".join(
        f'<ellipse cx="{EXIT_X + rnd2.uniform(-160, 60):.0f}" cy="{EXIT_Y - rnd2.uniform(30, 190):.0f}" '
        f'rx="{rnd2.uniform(1.4, 2.6):.1f}" ry="{rnd2.uniform(7, 18):.1f}" fill="#EAF8FF" '
        f'opacity="{rnd2.uniform(0.18, 0.4):.2f}" transform="rotate(-58,{EXIT_X:.0f},{EXIT_Y:.0f})"/>'
        for _ in range(9)
    )
    ripples = "".join(
        f'<ellipse cx="{EXIT_X:.0f}" cy="{EXIT_Y + 6 + i * 11:.0f}" rx="{120 + i * 70}" ry="{15 + i * 8}" '
        f'fill="none" stroke="#DCF2F8" stroke-opacity="{0.34 - i * 0.07:.2f}" stroke-width="{2.6 - i * 0.3:.1f}"/>'
        for i in range(3)
    )
    # 身上淌下来的水（竖直向下，跟重力走）
    drips = "".join(
        f'<rect x="{place_pt(x, y)[0] - rnd2.uniform(1.2, 2.4):.0f}" y="{place_pt(x, y)[1]:.0f}" '
        f'width="{rnd2.uniform(2.4, 4.4):.1f}" height="{rnd2.uniform(14, 44):.0f}" rx="1.8" '
        f'fill="#DCF2F8" opacity="{rnd2.uniform(0.25, 0.6):.2f}"/>'
        for x, y in [(120, 172), (170, 190), (230, 192), (290, 186), (170, 140), (240, 120), (320, 170), (110, 150)]
    )
    motes = "".join(
        f'<circle cx="{rnd.uniform(40, 960):.0f}" cy="{rnd.uniform(20, 250):.0f}" r="{rnd.uniform(1.1, 2.8):.1f}" '
        f'fill="#EAF8FF" opacity="{rnd.uniform(0.15, 0.45):.2f}"/>'
        for _ in range(22)
    )
    whale_tf = f"translate({_TX:.1f},{_TY:.1f}) scale({WHALE_SCALE})"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {H}" width="1000" height="{H}" role="img" aria-label="莫奈睡莲池上跃出水面的蓝色座头鲸">
  <defs>
    <linearGradient id="air" x1="0" y1="0" x2="0.15" y2="1">
      <stop offset="0" stop-color="#071B2C"/>
      <stop offset="0.42" stop-color="#0F3350"/>
      <stop offset="0.78" stop-color="#1B4A6E"/>
      <stop offset="1" stop-color="#2A6E8E"/>
    </linearGradient>
    <linearGradient id="pond" x1="0" y1="0" x2="0.1" y2="1">
      <stop offset="0" stop-color="#3E8FB0"/>
      <stop offset="0.22" stop-color="#2A6E97"/>
      <stop offset="0.6" stop-color="#1B4A72"/>
      <stop offset="1" stop-color="#0E2F4C"/>
    </linearGradient>
    <linearGradient id="mergeline" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2A6E97" stop-opacity="0"/>
      <stop offset="0.5" stop-color="#4FA8C8" stop-opacity=".5"/>
      <stop offset="1" stop-color="#2A6E97" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="vig" cx="0.5" cy="0.48" r="0.8">
      <stop offset="0.52" stop-color="#000000" stop-opacity="0"/>
      <stop offset="0.82" stop-color="#01060C" stop-opacity=".34"/>
      <stop offset="1" stop-color="#000308" stop-opacity=".7"/>
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
    <filter id="refl" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="5"/>
    </filter>
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" seed="9"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>
    <filter id="canvas" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.01 0.4" numOctaves="2" seed="3"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>
    <clipPath id="frame"><rect x="0" y="0" width="1000" height="{H}" rx="26"/></clipPath>
    <clipPath id="pondclip"><rect x="0" y="{WATER_Y}" width="1000" height="{H - WATER_Y}"/></clipPath>
  </defs>

  <rect x="0" y="0" width="1000" height="{H}" rx="26" fill="url(#air)"/>
  <rect x="0" y="{WATER_Y}" width="1000" height="{H - WATER_Y}" fill="url(#pond)"/>

  <g clip-path="url(#frame)">
    <g filter="url(#slightblur)">
      <g filter="url(#wobble)">
        {above}
      </g>
      <g filter="url(#wobble)">
        {water}
      </g>
    </g>

    <rect x="0" y="{WATER_Y - 26}" width="1000" height="52" fill="url(#mergeline)"/>

    <g filter="url(#wobble)">
      {reflect}
      {reflect2}
    </g>

    {motes}

    <g clip-path="url(#pondclip)">
      <g transform="translate({_TX:.1f},{2 * WATER_Y - _TY:.1f}) scale({WHALE_SCALE},{-WHALE_SCALE * 0.5:.3f})" opacity=".2" filter="url(#refl)">
        <path d="{G_BREACH['paths']['body']}" fill="#0A2A48"/>
        <path d="{G_BREACH['paths']['fluke']}" fill="#0A2A48"/>
      </g>
    </g>

    <g transform="{whale_tf}">
      <g class="bob">
        <g transform="rotate({WHALE_ROT},{_ROT_C[0]:.0f},{_ROT_C[1]:.0f})">
          {build_whale('w', G_BREACH, aura=True, bent=True)}
        </g>
      </g>
    </g>

    <rect x="0" y="{WATER_Y}" width="1000" height="{H - WATER_Y}" fill="url(#pond)" opacity=".3"/>

    {drips}
    <g filter="url(#softlight)" opacity=".9">{foam}</g>
    <g filter="url(#slightblur)" opacity=".92">{spray}</g>
    {droplets}
    <g filter="url(#slightblur)">
      {ripples}
    </g>

    {pads}
    <g filter="url(#slightblur)" opacity=".5">
      {pad_light}
    </g>
    {blooms}

    <rect x="0" y="0" width="1000" height="{H}" filter="url(#canvas)" opacity=".04"/>
    <rect x="0" y="0" width="1000" height="{H}" filter="url(#grain)" opacity=".07"/>
    <rect x="0" y="0" width="1000" height="{H}" fill="url(#vig)"/>
  </g>
  <rect x="0.75" y="0.75" width="998.5" height="{H - 1}.5" rx="25.5" fill="none" stroke="#4FA8C8" stroke-opacity=".32" stroke-width="1.5"/>

  <style>
    @keyframes bob{{0%,100%{{transform:translateY(0) rotate(0deg)}}50%{{transform:translateY(-13px) rotate(-1.2deg)}}}}
    .bob{{animation:bob 9s ease-in-out infinite}}
    @keyframes twk{{0%,100%{{opacity:.3}}50%{{opacity:.9}}}}
  </style>
</svg>
"""


def solo_svg():
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="30 62 552 186" width="552" height="186" role="img" aria-label="莫奈风格的蓝色座头鲸">
  <g class="bob">{build_whale('s', G_STRAIGHT, bent=False, shine=1.15)}</g>
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
print("breach bbox:", tuple(round(v) for v in G_BREACH["bbox"]))
