#!/usr/bin/env python3
"""生成主页用的蓝鲸 SVG：baby blue 梦幻简洁版（大场景 + 单独鲸鱼图标）。"""
import random
from pathlib import Path

OUT = Path(__file__).parent / "assets"

BODY = (
    "M 20,143 "
    "C 20,117 31,101 53,93 "
    "C 86,80 124,74 172,74 "
    "C 242,74 322,90 374,110 "
    "C 386,115 394,118 400,120 "
    "C 424,104 450,82 478,70 "
    "C 500,60 513,65 508,82 "
    "C 504,96 494,103 486,107 "
    "C 471,117 459,127 451,134 "
    "C 468,143 483,157 495,172 "
    "C 507,187 501,203 486,198 "
    "C 474,193 466,184 458,175 "
    "C 441,165 419,155 400,147 "
    "C 458,183 428,158 400,147 "
    "C 392,145 386,145 380,147 "
    "C 320,172 244,190 182,190 "
    "C 122,190 60,178 34,165 "
    "C 24,159 20,151 20,143 Z"
)
FLIPPER = "M 88,174 C 110,202 130,220 152,228 C 174,236 190,228 179,213 C 164,194 148,177 142,161 Z"
DORSAL = "M 326,112 C 334,92 350,82 366,90 C 360,100 352,110 348,122 Z"
BACK_LIGHT = "M 20,143 C 20,117 31,101 53,93 C 86,80 124,74 172,74 C 242,74 322,90 374,110 C 386,115 394,118 400,120"
GROOVES = [
    "M 46,158 C 84,176 126,186 168,188",
    "M 72,168 C 108,182 148,190 190,191",
    "M 100,178 C 134,188 170,194 212,194",
]
DOTS = [(150, 78, 2.4), (206, 74, 3.2), (262, 76, 2.2), (316, 84, 3.0), (362, 98, 2.0)]


def build_whale(uid, aura=False):
    tw_css, dots = "", ""
    for i, (x, y, r) in enumerate(DOTS):
        dur, delay = 3.0 + (i % 3) * 0.8, -(i * 0.4)
        tw_css += f".tw{i}{{animation:twk {dur:.1f}s ease-in-out {delay:.1f}s infinite}}"
        dots += f'<circle class="tw{i}" cx="{x}" cy="{y}" r="{r}" fill="#E8FAFF" opacity=".9"/>'
    grooves = "".join(
        f'<path d="{d}" fill="none" stroke="#F0F9FF" stroke-opacity=".45" stroke-width="2.4" stroke-linecap="round"/>'
        for d in GROOVES
    )
    aura_el = f'<ellipse cx="284" cy="156" rx="286" ry="124" fill="url(#{uid}-aura)"/>' if aura else ""
    shadow = (
        f'<ellipse cx="290" cy="292" rx="250" ry="20" fill="#4A90D9" opacity=".16" filter="url(#{uid}-blur)"/>'
        if aura else ""
    )
    return f"""
  <defs>
    <linearGradient id="{uid}-body" x1="0" y1="0" x2="0.12" y2="1">
      <stop offset="0" stop-color="#63B8FF"/>
      <stop offset="0.45" stop-color="#2E86E0"/>
      <stop offset="1" stop-color="#14538F"/>
    </linearGradient>
    <linearGradient id="{uid}-fin" x1="0" y1="0" x2="0.35" y2="1">
      <stop offset="0" stop-color="#4C9FE8"/>
      <stop offset="1" stop-color="#1B5EA8"/>
    </linearGradient>
    <radialGradient id="{uid}-aura">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity=".75"/>
      <stop offset="0.55" stop-color="#D6EEFF" stop-opacity=".45"/>
      <stop offset="1" stop-color="#D6EEFF" stop-opacity="0"/>
    </radialGradient>
    <filter id="{uid}-blur" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="9"/>
    </filter>
    <filter id="{uid}-soft" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="3"/>
    </filter>
    <clipPath id="{uid}-clip"><path d="{BODY}"/></clipPath>
  </defs>
  {aura_el}
  {shadow}
  <g>
    <path d="{FLIPPER}" fill="url(#{uid}-fin)" stroke="#0E3E72" stroke-opacity=".22" stroke-width="2"/>
    <path d="{DORSAL}" fill="url(#{uid}-fin)" stroke="#0E3E72" stroke-opacity=".22" stroke-width="2"/>
    <path d="{BODY}" fill="url(#{uid}-body)"/>
    <g clip-path="url(#{uid}-clip)">
      <ellipse cx="240" cy="240" rx="250" ry="78" fill="#DCEFFF" opacity=".55"/>
      <ellipse cx="130" cy="92" rx="140" ry="30" fill="#BFE6FF" opacity=".45" filter="url(#{uid}-blur)"/>
      {grooves}
    </g>
    <path d="{BACK_LIGHT}" fill="none" stroke="#EAF9FF" stroke-opacity=".8" stroke-width="3.4" stroke-linecap="round" filter="url(#{uid}-soft)"/>
    <path d="{BODY}" fill="none" stroke="#0E3E72" stroke-opacity=".3" stroke-width="2.2"/>
    <path d="M 24,150 C 60,160 100,164 138,160" fill="none" stroke="#0E3E72" stroke-opacity=".38" stroke-width="3" stroke-linecap="round"/>
    <circle cx="86" cy="124" r="7.5" fill="#0B2A4E"/>
    <circle cx="83.5" cy="121.5" r="2.6" fill="#F2FBFF" opacity=".95"/>
    {dots}
  </g>
  <style>
    {tw_css}
    @keyframes twk{{0%,100%{{opacity:.4}}50%{{opacity:1}}}}
  </style>"""


def sparkle(x, y, s, cls, dur, delay, color="#FFFFFF"):
    return (
        f'<path class="{cls}" d="M {x},{y - s} Q {x + s * 0.22},{y - s * 0.22} {x + s},{y} '
        f'Q {x + s * 0.22},{y + s * 0.22} {x},{y + s} Q {x - s * 0.22},{y + s * 0.22} {x - s},{y} '
        f'Q {x - s * 0.22},{y - s * 0.22} {x},{y - s} Z" fill="{color}"/>'
        f"<style>.{cls}{{animation:twk {dur}s ease-in-out {delay}s infinite}}</style>"
    )


def scene_svg():
    rnd = random.Random(126)
    bokeh = []
    for i in range(4):
        x, y = round(rnd.uniform(90, 910), 1), round(rnd.uniform(70, 280), 1)
        r = round(rnd.uniform(42, 86), 1)
        o = round(rnd.uniform(0.16, 0.3), 2)
        dur, delay = round(rnd.uniform(9, 15), 1), -round(rnd.uniform(0, 9), 1)
        dy = round(rnd.uniform(-16, 16), 1)
        bokeh.append(
            f'<circle class="k{i}" cx="{x}" cy="{y}" r="{r}" fill="#FFFFFF" opacity="{o}" filter="url(#kblur)"/>'
            f"<style>.k{i}{{animation:float {dur}s ease-in-out {delay}s infinite}}"
            f"@keyframes float{{0%,100%{{transform:translate(0,0)}}50%{{transform:translate(14px,{dy}px)}}}}</style>"
        )
    sparks = "".join(
        sparkle(x, y, s, f"sp{i}", round(rnd.uniform(3.2, 5.5), 1), -round(rnd.uniform(0, 3), 1))
        for i, (x, y, s) in enumerate(
            [(180, 92, 7), (300, 252, 5), (470, 74, 6), (640, 112, 5.5), (792, 226, 6.5),
             (868, 96, 5), (120, 238, 5.5), (560, 292, 4.5)]
        )
    )
    bubbles = []
    for i in range(4):
        x = round(rnd.uniform(340, 700), 1)
        r = round(rnd.uniform(3.5, 6.5), 1)
        dur, delay = round(rnd.uniform(12, 18), 1), -round(rnd.uniform(0, 12), 1)
        bubbles.append(
            f'<circle class="bb{i}" cx="{x}" cy="292" r="{r}" fill="none" stroke="#FFFFFF" stroke-opacity=".75" stroke-width="1.8"/>'
            f"<style>.bb{i}{{animation:rise {dur}s linear {delay}s infinite}}"
            f"@keyframes rise{{0%{{transform:translate(0,0);opacity:0}}15%{{opacity:.85}}"
            f"100%{{transform:translate(10px,-218px);opacity:0}}}}</style>"
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 340" width="1000" height="340" role="img" aria-label="baby blue 梦境里的蓝色鲸鱼">
  <defs>
    <linearGradient id="dream" x1="0" y1="0" x2="0.2" y2="1">
      <stop offset="0" stop-color="#F6FCFF"/>
      <stop offset="0.38" stop-color="#DEEFFF"/>
      <stop offset="0.76" stop-color="#C2E3FC"/>
      <stop offset="1" stop-color="#A2D2F5"/>
    </linearGradient>
    <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity=".6"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>
    <filter id="kblur" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="22"/>
    </filter>
  </defs>

  <rect x="0" y="0" width="1000" height="340" rx="26" fill="url(#dream)"/>

  <g class="beams">
    <path d="M 250,0 L 430,0 L 300,340 L 130,340 Z" fill="url(#beam)" opacity=".5"/>
    <path d="M 610,0 L 730,0 L 700,340 L 560,340 Z" fill="url(#beam)" opacity=".38"/>
  </g>

  {''.join(bokeh)}

  <path d="M 0,30 C 150,14 300,46 450,30 C 600,14 750,46 900,30 C 950,25 980,30 1000,28" fill="none" stroke="#FFFFFF" stroke-opacity=".85" stroke-width="2.6" class="line"/>

  {sparks}

  <g transform="translate(186,6) scale(1.15)">
    <g class="bob">{build_whale('w', aura=True)}</g>
  </g>

  {''.join(bubbles)}

  <style>
    @keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-14px)}}}}
    .bob{{animation:bob 8s ease-in-out infinite}}
    @keyframes twk{{0%,100%{{opacity:.35}}50%{{opacity:1}}}}
    @keyframes sway{{0%,100%{{transform:translateX(0)}}50%{{transform:translateX(20px)}}}}
    .line{{animation:sway 18s ease-in-out infinite}}
    @keyframes beams{{0%,100%{{opacity:.65}}50%{{opacity:1}}}}
    .beams{{animation:beams 14s ease-in-out infinite}}
  </style>
</svg>
"""


def solo_svg():
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="6 56 522 196" width="522" height="196" role="img" aria-label="蓝色鲸鱼">
  <g class="bob">{build_whale('s', aura=True)}</g>
  <style>
    @keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-10px)}}}}
    .bob{{animation:bob 7s ease-in-out infinite}}
    @keyframes twk{{0%,100%{{opacity:.35}}50%{{opacity:1}}}}
  </style>
</svg>
"""


OUT.mkdir(exist_ok=True)
(OUT / "blue-whale-scene.svg").write_text(scene_svg(), encoding="utf-8")
(OUT / "blue-whale.svg").write_text(solo_svg(), encoding="utf-8")
print("written:", *(p.name for p in sorted(OUT.glob("*.svg"))))
