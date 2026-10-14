#!/usr/bin/env python3
"""生成「蓝鲸出没」小节里的三只小蓝鲸动画图标（assets/whale-trio.svg）。

要点：
  1. 三只小蓝鲸相位错开：上下浮 + 左右飘 + 整体轻摆 + 摆尾 + 胸鳍划水
  2. 头顶水柱循环喷发（应援棒一按就喷着水柱亮起来），配一圈淡光晕和一颗小星芒
  3. 只用 SMIL（animate / animateTransform），不碰 CSS transform-origin，
     `<img src=".../whale-trio.svg">` 里也能动，GitHub README 可用
  4. `--frames`：把动画在关键帧时刻定格成静态 SVG，方便逐帧检查画面
     （rsvg-convert / 浏览器截图都不跑动画，只有真浏览器才看得到过程）

用法：
  python3 gen_whale_trio.py            # 生成 assets/whale-trio.svg
  python3 gen_whale_trio.py --frames   # 额外把关键帧定格到 .dbg/whale_frames/
"""
import sys
from pathlib import Path

OUT = Path(__file__).parent / "assets"
DBG = Path(__file__).parent / ".dbg" / "whale_frames"

W, H = 320, 88  # 画布：三只鲸鱼并排，上下留出喷水和摆尾的空间
CENTER_Y = 50   # 鲸鱼身体中线的 y
SPOTS = [58, 162, 266]  # 三只鲸鱼的中心 x

# ------------------------------------------------------------------ 形体
# 局部坐标：原点在身体中心，头朝右，尾在左
# 身形走「细长」路线：长 65 高 30（约 2.2:1），比旧版 59x38 显瘦，也不至于细成带鱼
BODY = [
    (34, -4), (29, -10), (17, -14), (-2, -15), (-17, -11), (-26, -7), (-31, -3),
    (-31, 1), (-26, 4), (-17, 9), (-2, 12), (14, 15), (27, 12), (34, 6),
]
FLUKE = [  # 尾鳍：绕尾根 (-31,0) 摆动（两瓣圆钝，别像鱼尾那样尖）
    (-30, -4), (-33, -9), (-40, -13), (-46, -11), (-45, -7), (-39, -3),
    (-39, 3), (-45, 7), (-46, 11), (-40, 13), (-33, 9), (-30, 4),
]
FIN = [  # 胸鳍：绕肩点 (15,6) 划水，画在身体之上（要比肚皮多垂出来一点，才像鳍）
    (15, 4), (7, 8), (0, 15), (4, 21), (14, 19), (18, 8),
]
BELLY = [  # 浅色肚皮（用身体轮廓裁剪）
    (40, 4), (27, 12), (10, 16), (-6, 14), (-19, 9),
    (-8, 6), (10, 7), (27, 6),
]
BLOWHOLE = (15.0, -14.0)  # 喷水口
JOINTS = {"fluke": (-31.0, 0.0), "fin": (15.0, 6.0), "body": (0.0, 0.0)}


def catmull(points, closed=True):
    """Catmull-Rom 采样点 → 三次贝塞尔路径（和 gen_whale.py 同一套算法）。"""
    n = len(points)

    def pt(i):
        return points[i % n] if closed else points[max(0, min(n - 1, i))]

    d = [f"M{points[0][0]:.1f},{points[0][1]:.1f}"]
    for i in range(n if closed else n - 1):
        p0, p1, p2, p3 = pt(i - 1), pt(i), pt(i + 1), pt(i + 2)
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(
            f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
        )
    return " ".join(d) + ("Z" if closed else "")


def sparkle(x, y, s):
    """四角星芒。"""
    return (
        f'<path d="M {x},{y - s} Q {x + s * 0.22},{y - s * 0.22} {x + s},{y} '
        f'Q {x + s * 0.22},{y + s * 0.22} {x},{y + s} Q {x - s * 0.22},{y + s * 0.22} {x - s},{y} '
        f'Q {x - s * 0.22},{y - s * 0.22} {x},{y - s} Z" fill="#8FD3F2"/>'
    )


# ------------------------------------------------------------------ 动画
# 每条动画：frames = [(时间比例, 数值元组), ...]，dur 秒，begin 可负（相位错开）
MOTION = {
    # 上下浮：慢，带一点下潜
    "bob":   dict(kind="translate", frames=[(0, (0, 2)), (.28, (0, -6)), (.55, (0, 0)),
                                            (.8, (0, 4)), (1, (0, 2))], dur=4.4, splines=True),
    # 左右飘：更慢，制造"游动"的错位感
    "sway":  dict(kind="translate", frames=[(0, (0, 0)), (.5, (5, 0)), (1, (0, 0))],
                  dur=6.8, splines=True),
    # 整体轻摆（绕身体中心）
    "tilt":  dict(kind="rotate", joint="body",
                  frames=[(0, (-2.5,)), (.5, (2.5,)), (1, (-2.5,))], dur=4.4, splines=True),
    # 摆尾
    "fluke": dict(kind="rotate", joint="fluke",
                  frames=[(0, (-14,)), (.5, (11,)), (1, (-14,))], dur=1.9, splines=True),
    # 胸鳍划水
    "fin":   dict(kind="rotate", joint="fin",
                  frames=[(0, (0,)), (.5, (-16,)), (1, (0,))], dur=1.9, splines=True),
}
# 每只鲸鱼的节奏偏移（秒）：错开相位，别像三个复制品
PHASE = [
    {"bob": 0.0, "sway": 0.0, "tilt": 0.0, "fluke": 0.0, "fin": -0.3, "spout": -1.1},
    {"bob": -1.5, "sway": -2.3, "tilt": -1.2, "fluke": -0.7, "fin": -1.0, "spout": -0.9},
    {"bob": -2.9, "sway": -4.1, "tilt": -2.4, "fluke": -1.3, "fin": -1.6, "spout": -1.7},
]
SPOUT_DUR = 2.6  # 一轮喷水
SPOUT = [  # (起点, 终点, 半径) —— 水珠呈扇形往上冲
    ((16, -14), (16, -35), 2.3),
    ((11, -13), (5, -30), 1.7),
    ((21, -13), (27, -30), 1.7),
]
SPARKLE = (41, -17, 3.8)  # 星芒：鼻尖前上方


def smil(kind, frames, dur, begin, joint=None):
    """把 frames 翻译成 SMIL 动画元素。"""
    t = ";".join(f"{k:g}" for k, _ in frames)
    if kind == "translate":
        vals = ";".join(f"{v[0]:g},{v[1]:g}" for _, v in frames)
    else:
        cx, cy = JOINTS[joint]
        vals = ";".join(f"{v[0]:g} {cx:g} {cy:g}" for _, v in frames)
    splines = ("".join("0.42 0 0.58 1 " for _ in range(len(frames) - 1))).strip()
    extra = f' calcMode="spline" keySplines="{splines}"' if len(frames) > 2 else ""
    return (
        f'<animateTransform attributeName="transform" type="{kind}" '
        f'values="{vals}" keyTimes="{t}" dur="{dur}s" begin="{begin:g}s" '
        f'repeatCount="indefinite"{extra}/>'
    )


def bake(anim, t, begin):
    """定格模式：算出 t 秒时的静态 transform。"""
    dur = anim["dur"]
    k = ((t - begin) % dur) / dur
    frames = anim["frames"]
    for (t0, v0), (t1, v1) in zip(frames, frames[1:]):
        if t0 <= k <= t1:
            f = 0 if t1 == t0 else (k - t0) / (t1 - t0)  # 定格用线性就够看位置了
            v = tuple(a + (b - a) * f for a, b in zip(v0, v1))
            break
    else:
        v = frames[-1][1]
    if anim["kind"] == "translate":
        return f"translate({v[0]:.1f},{v[1]:.1f})"
    cx, cy = JOINTS[anim["joint"]]
    return f"rotate({v[0]:.1f},{cx:g},{cy:g})"


def layer(name, inner, ph, t=None):
    """一层变换：正常模式吐 SMIL，定格模式吐静态 transform。"""
    anim = MOTION[name]
    begin = ph[name]
    if t is None:
        return (f"<g>{smil(anim['kind'], anim['frames'], anim['dur'], begin, anim.get('joint'))}\n"
                f"{inner}</g>")
    return f'<g transform="{bake(anim, t, begin)}">\n{inner}</g>'


def whale(i, t=None):
    """第 i 只小蓝鲸；t 不为 None 时输出该时刻的定格画面。"""
    ph = PHASE[i]
    x, y = SPOTS[i], CENTER_Y
    uid = f"w{i}"
    body, belly, fluke, fin = (catmull(p) for p in (BODY, BELLY, FLUKE, FIN))
    bx, by = BLOWHOLE
    sx, sy, ss = SPARKLE

    # 水柱：三颗水珠 + 一圈光晕，同一轮喷发里错开出发
    drops = ""
    for k, ((x0, y0), (x1, y1), r) in enumerate(SPOUT):
        d = 0.16 * k  # 同一轮里错开出发
        if t is None:
            rise = smil(
                "translate",
                [(0, (x0, y0)), (.25, (x0 + (x1 - x0) * .45, y0 + (y1 - y0) * .75)),
                 (.55, (x1, y1)), (1, (x1, y1))],
                SPOUT_DUR, ph["spout"] - d,
            )
            fade = (
                f'<animate attributeName="opacity" values="0;1;.85;0;0" '
                f'keyTimes="0;.06;.55;.75;1" dur="{SPOUT_DUR}s" '
                f'begin="{ph["spout"] - d:g}s" repeatCount="indefinite"/>'
            )
            drops += (f'<g>{rise}{fade}<circle cx="{x0:g}" cy="{y0:g}" r="{r}" '
                      f'fill="#CFEFFF"/></g>')
            continue
        # 定格模式：按线性插值把水珠摆到该时刻的位置
        k2 = ((t - (ph["spout"] - d)) % SPOUT_DUR) / SPOUT_DUR
        f = min(1.0, k2 / .55)
        px, py = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        op = 1 if .06 <= k2 <= .55 else (0 if k2 > .72 or k2 < .02 else .5)
        drops += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" fill="#CFEFFF" opacity="{op}"/>'
    if t is None:
        glow = (
            f'<ellipse cx="{bx:g}" cy="{by - 7:g}" rx="8.5" ry="7" fill="#9FDCF5" '
            f'filter="url(#soft)">'
            f'<animate attributeName="opacity" values=".1;.42;.1" keyTimes="0;.18;1" '
            f'dur="{SPOUT_DUR}s" begin="{ph["spout"]:g}s" repeatCount="indefinite"/>'
            f'</ellipse>'
        )
        twinkle = (f'<animate attributeName="opacity" values=".25;.95;.25" '
                   f'keyTimes="0;.5;1" dur="3.2s" begin="{ph["bob"]:g}s" '
                   f'repeatCount="indefinite"/>')
    else:
        glow = (f'<ellipse cx="{bx:g}" cy="{by - 7:g}" rx="8.5" ry="7" fill="#9FDCF5" '
                f'opacity=".26" filter="url(#soft)"/>')
        twinkle = ""
    spark = f'<g opacity=".8">{twinkle}{sparkle(sx, sy, ss)}</g>'

    # 画序：尾鳍在身后 → 身体 → 肚皮 → 胸鳍压在身侧 → 五官 → 水柱
    parts = f"""<g>{layer('fluke', f'<path d="{fluke}" fill="url(#{uid}f)"/>', ph, t)}</g>
<path d="{body}" fill="url(#{uid}b)"/>
<path d="{belly}" fill="#DCF2FF" clip-path="url(#{uid}c)" opacity=".9"/>
<g>{layer('fin', f'<path d="{fin}" fill="url(#{uid}f)" opacity=".95"/>', ph, t)}</g>
<path d="M34,1.5 Q31,7.5 23,6.5" fill="none" stroke="#1B4E86" stroke-opacity=".5"
      stroke-width="1.4" stroke-linecap="round"/>
<circle cx="25" cy="-4.5" r="2.2" fill="#0A1E3C"/>
<circle cx="25.7" cy="-5.3" r="0.8" fill="#FFFFFF"/>
<ellipse cx="30.5" cy="0.5" rx="2.6" ry="1.8" fill="#FFB3C9" opacity=".45"/>
{drops}{glow}{spark}"""

    # 变换栈：外→内 = 位置 → 左右飘 → 上下浮 → 整体轻摆 → 零件
    inner = layer("tilt", parts, ph, t)
    inner = layer("bob", inner, ph, t)
    inner = layer("sway", inner, ph, t)
    return f'<g id="{uid}">\n<g transform="translate({x},{y})">\n{inner}\n</g>\n</g>'


def doc(t=None):
    defs = "".join(
        f'''<linearGradient id="w{i}b" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#8AD6F5"/><stop offset="1" stop-color="#2E86C8"/>
    </linearGradient>
    <linearGradient id="w{i}f" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#5BB8E8"/><stop offset="1" stop-color="#2472B4"/>
    </linearGradient>
    <clipPath id="w{i}c"><path d="{catmull(BODY)}"/></clipPath>'''
        for i in range(len(SPOTS))
    )
    label = "三只喷水的小蓝鲸"
    body = "\n  ".join(whale(i, t) for i in range(len(SPOTS)))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"
     role="img" aria-label="{label}">
  <title>{label}</title>
  <defs>
    <filter id="soft" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="4"/>
    </filter>
    {defs}
  </defs>
  {body}
</svg>
"""


def keyframe_times():
    """所有动画的关键帧时刻（去重），用来逐帧定格检查。"""
    ts = set()
    for i, ph in enumerate(PHASE):
        for name, anim in MOTION.items():
            for k, _ in anim["frames"]:
                ts.add(round((k * anim["dur"] + ph[name]) % anim["dur"], 3))
        for k in (0, .06, .25, .55, .75):
            ts.add(round((k * SPOUT_DUR + ph["spout"]) % SPOUT_DUR, 3))
    return sorted(ts)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    (OUT / "whale-trio.svg").write_text(doc(), encoding="utf-8")
    print("written:", (OUT / "whale-trio.svg").name, (OUT / "whale-trio.svg").stat().st_size, "bytes")
    if "--frames" in sys.argv:
        DBG.mkdir(parents=True, exist_ok=True)
        for t in keyframe_times():
            (DBG / f"t{t:06.2f}.svg").write_text(doc(t), encoding="utf-8")
        print("frames:", len(keyframe_times()), "->", DBG)
