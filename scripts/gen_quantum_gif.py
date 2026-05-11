#!/usr/bin/env python3
"""
Quantum ASCII Face Animation — infinite loop GIF banner
Characters shift at quantum speed forming faces from pure noise.
No locks. No limits. 8-bit → quantum.
"""
from PIL import Image, ImageDraw, ImageFont
import random, math, os

W, H = 860, 180
COLS, ROWS = 43, 9
CW, CH = W // COLS, H // ROWS
FRAMES = 24
FRAME_MS = 80

# Character pools
NOISE  = list('0123456789ABCDEF')
FACE   = list('0123456789#@ψΩ∞⊕◉⚡*&%$!')
EYE    = list('◉⊕@0OΩ*#8')
MOUTH  = list('~=-_∽≈—')

BG     = (10, 10, 15)
CYAN   = (0, 240, 255)
MAGENTA= (255, 0, 255)
GOLD   = (255, 215, 0)
DIM    = (0, 60, 70)
DIMM   = (0, 40, 50)
DIMMM  = (0, 25, 35)

def face_cells(cx, cy, rx=6, ry=4):
    result = {}
    for a in range(0, 360, 10):
        r = math.radians(a)
        x = round(cx + rx * math.cos(r))
        y = round(cy + ry * 0.75 * math.sin(r))
        if 0 <= x < COLS and 0 <= y < ROWS:
            result[(x,y)] = ('outline', CYAN)
    for ex, ey, label in [(cx-2, cy-2, 'eye'), (cx+2, cy-2, 'eye')]:
        for dx in range(-1,2):
            for dy in range(-1,2):
                if dx*dx + dy*dy <= 1:
                    xx, yy = ex+dx, ey+dy
                    if 0 <= xx < COLS and 0 <= yy < ROWS:
                        result[(xx,yy)] = ('eye', MAGENTA)
    for d in [(0,0),(0,1),(-1,2),(1,2)]:
        xx, yy = cx+d[0], cy+d[1]
        if 0 <= xx < COLS and 0 <= yy < ROWS:
            result[(xx,yy)] = ('nose', CYAN)
    for mx in range(-3, 4):
        my = round(abs(mx)*0.5)
        xx, yy = cx+mx, cy+3-my
        if 0 <= xx < COLS and 0 <= yy < ROWS:
            result[(xx,yy)] = ('mouth', GOLD)
    return result

# Build face map — 3 faces
faces = {}
for fcx in [8, 22, 36]:
    faces.update(face_cells(fcx, 4))

# Per-cell config
rng = random.Random(42)
cells = {}
for row in range(ROWS):
    for col in range(COLS):
        key = (col, row)
        info = faces.get(key)
        if info:
            kind, color = info
            pool = EYE if kind == 'eye' else (MOUTH if kind == 'mouth' else FACE)
            speed = rng.randint(1, 2)
        else:
            kind, color = 'bg', rng.choice([DIM, DIMM, DIMMM])
            pool = NOISE
            speed = rng.randint(1, 4)
        phase = rng.randint(0, len(pool)-1)
        cells[key] = {'pool': pool, 'color': color, 'speed': speed, 'phase': phase, 'kind': kind}

# Try to load a monospace font, fall back gracefully
FONT_SIZE = 16
try:
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf', FONT_SIZE)
except:
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf', FONT_SIZE)
    except:
        font = ImageFont.load_default()

frames = []
for f in range(FRAMES):
    img = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)

    for row in range(ROWS):
        for col in range(COLS):
            cell = cells[(col, row)]
            idx = (cell['phase'] + f * cell['speed']) % len(cell['pool'])
            ch = cell['pool'][idx]
            x = col * CW + 2
            y = row * CH + 1
            color = cell['color']
            # Pulse face cells on beat
            if cell['kind'] != 'bg' and f % 6 < 3:
                r2 = tuple(min(255, int(c * 1.3)) for c in color)
            else:
                r2 = color
            draw.text((x, y), ch, font=font, fill=r2)

    # Scan line overlay (subtle)
    for sy in range(0, H, 4):
        draw.line([(0, sy), (W, sy)], fill=(0, 0, 0, 30) if hasattr(draw, 'alpha') else (8, 8, 12))

    frames.append(img)

out = '/mnt/shanebrain-raid/pulsar-sentinel/quantum-banner.gif'
frames[0].save(
    out,
    save_all=True,
    append_images=frames[1:],
    loop=0,
    duration=FRAME_MS,
    optimize=False
)
size = os.path.getsize(out)
print(f"Generated {FRAMES} frames → {out}  ({size/1024:.0f} KB)")
