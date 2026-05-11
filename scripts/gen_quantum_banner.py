#!/usr/bin/env python3
"""Generate quantum ASCII face animation SVG banner for all README files."""
import math, random, textwrap

COLS = 52
ROWS = 13
W = 910
H = 234
CW = W / COLS
CH = H / ROWS

FACE_CHARS  = ['0','1','ψ','Ω','∞','⊕','◉','⚡','#','@','*']
BG_CHARS    = ['0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F']
EYE_CHARS   = ['◉','⊕','@','0','O','Ω','*','#']
MOUTH_CHARS = ['~','=','-','_','∽','≈','—','⌇']

def face_mask(cx, cy, rx=6, ry=5):
    pts = {}
    # head outline
    for a in range(0, 360, 9):
        r = math.radians(a)
        x = round(cx + rx * math.cos(r))
        y = round(cy + ry * 0.75 * math.sin(r))
        if 0 <= x < COLS and 0 <= y < ROWS:
            pts[(x,y)] = 'outline'
    # eyes
    for ex, ey in [(cx-2, cy-2), (cx+2, cy-2)]:
        for dx in range(-1,2):
            for dy in range(-1,2):
                if dx*dx + dy*dy <= 1 and 0 <= ex+dx < COLS and 0 <= ey+dy < ROWS:
                    pts[(ex+dx, ey+dy)] = 'eye'
    # nose
    for d in [(0,0),(0,1),(-1,2),(1,2)]:
        x,y = cx+d[0], cy+d[1]
        if 0 <= x < COLS and 0 <= y < ROWS:
            pts[(x,y)] = 'nose'
    # smile
    for mx in range(-3, 4):
        my = round(abs(mx) * 0.5)
        x, y = cx+mx, cy+3-my
        if 0 <= x < COLS and 0 <= y < ROWS:
            pts[(x,y)] = 'mouth'
    return pts

# Three faces across the banner
all_faces = {}
for fcx in [11, 26, 41]:
    all_faces.update(face_mask(fcx, 6))

# Assign character sets and colors per position
def get_chars(kind, seed):
    r = random.Random(seed)
    if kind == 'eye':
        pool = EYE_CHARS
        color = '#ff00ff'
    elif kind == 'mouth':
        pool = MOUTH_CHARS
        color = '#ffd700'
    elif kind in ('outline','nose'):
        pool = FACE_CHARS
        color = '#00f0ff'
    else:
        pool = BG_CHARS
        color = r.choice(['#004444','#003333','#002222','#001a1a','#005555'])
    chars = [r.choice(pool) for _ in range(8)]
    return chars, color

random.seed(42)
cells = {}
for row in range(ROWS):
    for col in range(COLS):
        key = (col, row)
        kind = all_faces.get(key, 'bg')
        chars, color = get_chars(kind, col * 100 + row)
        dur = round(random.uniform(0.3, 0.7) if kind == 'bg'
                    else random.uniform(0.6, 1.4), 2)
        delay = round(random.uniform(0, dur), 3)
        cells[key] = {'chars': chars, 'color': color, 'dur': dur, 'delay': delay, 'kind': kind}

# Build CSS keyframes per cell — group by same (dur, delay) to reduce CSS size
# Instead: inline animation via animationDelay on each text group
lines = []
lines.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&amp;display=swap');
  .c {{ font-family: "Share Tech Mono", "Courier New", monospace; font-size: 15px; }}
  .c0 {{ animation: s0 var(--d) var(--o) infinite step-start; }}
  .c1 {{ animation: s1 var(--d) var(--o) infinite step-start; }}
  .c2 {{ animation: s2 var(--d) var(--o) infinite step-start; }}
  .c3 {{ animation: s3 var(--d) var(--o) infinite step-start; }}
  .c4 {{ animation: s4 var(--d) var(--o) infinite step-start; }}
  .c5 {{ animation: s5 var(--d) var(--o) infinite step-start; }}
  .c6 {{ animation: s6 var(--d) var(--o) infinite step-start; }}
  .c7 {{ animation: s7 var(--d) var(--o) infinite step-start; }}
  @keyframes s0 {{ 0%{{opacity:1}} 12.5%{{opacity:0}} 100%{{opacity:0}} }}
  @keyframes s1 {{ 0%{{opacity:0}} 12.5%{{opacity:1}} 25%{{opacity:0}} 100%{{opacity:0}} }}
  @keyframes s2 {{ 0%{{opacity:0}} 25%{{opacity:1}} 37.5%{{opacity:0}} 100%{{opacity:0}} }}
  @keyframes s3 {{ 0%{{opacity:0}} 37.5%{{opacity:1}} 50%{{opacity:0}} 100%{{opacity:0}} }}
  @keyframes s4 {{ 0%{{opacity:0}} 50%{{opacity:1}} 62.5%{{opacity:0}} 100%{{opacity:0}} }}
  @keyframes s5 {{ 0%{{opacity:0}} 62.5%{{opacity:1}} 75%{{opacity:0}} 100%{{opacity:0}} }}
  @keyframes s6 {{ 0%{{opacity:0}} 75%{{opacity:1}} 87.5%{{opacity:0}} 100%{{opacity:0}} }}
  @keyframes s7 {{ 0%{{opacity:0}} 87.5%{{opacity:1}} 100%{{opacity:0}} }}
</style>
</defs>
<rect width="{W}" height="{H}" fill="#0a0a0f"/>''')

for row in range(ROWS):
    for col in range(COLS):
        cell = cells[(col,row)]
        x = col * CW + CW * 0.1
        y = row * CH + CH * 0.85
        d = cell['dur']
        o = cell['delay']
        color = cell['color']
        for i, ch in enumerate(cell['chars']):
            ch_safe = ch.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            lines.append(
                f'<text class="c c{i}" x="{x:.1f}" y="{y:.1f}" fill="{color}" '
                f'style="--d:{d}s;--o:{o}s">{ch_safe}</text>'
            )

lines.append('</svg>')
svg = '\n'.join(lines)

out = '/mnt/shanebrain-raid/pulsar-sentinel/quantum-banner.svg'
with open(out, 'w') as f:
    f.write(svg)
print(f"Written {len(svg):,} bytes → {out}")
print(f"Cells: {COLS*ROWS}, Elements: {COLS*ROWS*8}")
