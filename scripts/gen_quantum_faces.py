#!/usr/bin/env python3
"""
Quantum Face Renderer v3 — Ghost in the Machine
Characters cycle as before, BUT each cell's pool now includes
a real face image tile sliced to character size.
Most frames: numbers/symbols. Occasionally: a face appears.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np
import math, os, random

GIF_W, GIF_H = 860, 320
COLS, ROWS = 72, 28
CW = int(GIF_W / COLS)   # px per char cell
CH = int(GIF_H / ROWS)

FRAMES = 24
FRAME_MS = 65

BANDS = [
    (0.00, 0.12, ['█','▓','#','@','M','W','B','0']),
    (0.12, 0.28, ['0','8','9','Q','G','B','%','&']),
    (0.28, 0.44, ['4','6','5','3','E','F','Z','ψ']),
    (0.44, 0.58, ['7','2','J','T','I','1','Ω','0']),
    (0.58, 0.72, ['!','/','-','|','(',')','-','1']),
    (0.72, 0.85, ['.','·',',','\'','^','`','~',':']),
    (0.85, 1.00, [' ',' ','·','\'',' ',' ','·',' ']),
]

BG_COLOR = (8, 8, 14)
FACE_TILE_EVERY = 8   # 1 face tile per N char slots in the pool


def render_face_image(cx_frac, fw, fh, color_scheme='cyan'):
    """Render a face at full GIF resolution, return PIL Image (RGB)."""
    img = Image.new('RGB', (GIF_W, GIF_H), BG_COLOR)
    d = ImageDraw.Draw(img)
    cx = int(cx_frac * GIF_W)
    cy = GIF_H // 2
    hw, hh = fw // 2, fh // 2

    if color_scheme == 'cyan':
        skin_hi  = (0, 220, 200)
        skin_mid = (0, 140, 160)
        skin_lo  = (0, 80, 100)
        eye_col  = (200, 0, 255)
        lip_col  = (255, 80, 200)
        hair_col = (0, 40, 80)
    else:
        skin_hi  = (255, 200, 160)
        skin_mid = (200, 140, 100)
        skin_lo  = (140, 80,  50)
        eye_col  = (30,  30,  60)
        lip_col  = (180, 60,  60)
        hair_col = (40,  25,  10)

    # Head
    d.ellipse([cx-hw, cy-hh, cx+hw, cy+hh], fill=skin_mid)
    # Highlight top
    d.ellipse([cx-hw+12, cy-hh, cx+hw-12, cy-hh//3], fill=skin_hi)
    # Shadow jaw
    d.ellipse([cx-hw+6, cy+hh//3, cx+hw-6, cy+hh+6], fill=skin_lo)
    # Brow ridge highlight
    brow_y = cy - int(hh * 0.25)
    d.ellipse([cx-hw+18, brow_y-10, cx+hw-18, brow_y+5], fill=skin_hi)

    # Hair
    d.ellipse([cx-hw, cy-hh-8, cx+hw, cy-int(hh*0.35)], fill=hair_col)
    # Temples
    for sign in [-1, 1]:
        tx0 = min(cx+sign*(hw-15), cx+sign*hw+sign*5)
        tx1 = max(cx+sign*(hw-15), cx+sign*hw+sign*5)
        d.ellipse([tx0, cy-hh, tx1, cy-hh//3], fill=hair_col)

    # Eyes
    eye_rx = int(fw * 0.09)
    eye_ry = int(fh * 0.07)
    eye_y  = cy - int(hh * 0.17)
    for sign in [-1, 1]:
        ex = cx + sign * int(fw * 0.22)
        # socket shadow
        d.ellipse([ex-eye_rx-5, eye_y-eye_ry-4, ex+eye_rx+5, eye_y+eye_ry+5], fill=skin_lo)
        # white
        d.ellipse([ex-eye_rx, eye_y-eye_ry, ex+eye_rx, eye_y+eye_ry], fill=(220, 220, 240))
        # iris
        ir = max(eye_rx-3, 4)
        d.ellipse([ex-ir, eye_y-ir+2, ex+ir, eye_y+ir+2], fill=eye_col)
        # pupil
        pr = max(ir-4, 2)
        d.ellipse([ex-pr, eye_y-pr+2, ex+pr, eye_y+pr+2], fill=(5, 5, 10))
        # catch light
        cl = max(pr-2, 1)
        d.ellipse([ex-ir//2, eye_y-ir//2, ex-ir//2+cl*2, eye_y-ir//2+cl*2], fill=(240, 240, 255))
        # lashes hint
        for lx in range(ex-eye_rx, ex+eye_rx, 4):
            d.line([(lx, eye_y-eye_ry), (lx+1, eye_y-eye_ry-4)], fill=hair_col, width=1)

    # Eyebrows
    for sign in [-1, 1]:
        bx = cx + sign * int(fw * 0.22)
        d.line([(bx-eye_rx, eye_y-eye_ry-7), (bx+eye_rx, eye_y-eye_ry-10)],
               fill=hair_col, width=3)

    # Nose
    nose_y = cy + int(hh * 0.12)
    nw = int(fw * 0.07)
    d.polygon([
        (cx, cy - int(hh * 0.04)),
        (cx - nw*2, nose_y + 4),
        (cx - nw, nose_y + 12),
        (cx + nw, nose_y + 12),
        (cx + nw*2, nose_y + 4),
    ], fill=skin_lo)
    # Nostrils
    for sign in [-1, 1]:
        nx = cx + sign * nw
        d.ellipse([nx-4, nose_y+6, nx+4, nose_y+14], fill=tuple(max(0,v-30) for v in skin_lo))

    # Lips
    lip_y = cy + int(hh * 0.32)
    lw = int(fw * 0.27)
    # upper
    d.polygon([
        (cx - lw, lip_y),
        (cx - lw//2, lip_y - 9),
        (cx, lip_y - 5),
        (cx + lw//2, lip_y - 9),
        (cx + lw, lip_y),
    ], fill=lip_col)
    # lower
    d.ellipse([cx-lw+4, lip_y, cx+lw-4, lip_y+16], fill=tuple(min(255,v+30) for v in lip_col))
    # lip line
    d.line([(cx-lw, lip_y), (cx+lw, lip_y)], fill=tuple(max(0,v-40) for v in lip_col), width=2)
    # Philtrum
    d.line([(cx, nose_y+12), (cx, lip_y-3)], fill=skin_lo, width=2)

    # Ears
    ear_h = int(hh * 0.30)
    ear_w = int(fw * 0.07)
    ear_y = cy - int(hh * 0.05)
    for sign in [-1, 1]:
        ex = cx + sign * (hw - 2)
        d.ellipse([ex-ear_w, ear_y-ear_h, ex+ear_w, ear_y+ear_h], fill=skin_mid)
        d.ellipse([ex-ear_w+3, ear_y-ear_h+5, ex+ear_w-2, ear_y+ear_h-5], fill=skin_lo)

    # Neck
    nk = int(fw * 0.20)
    d.rectangle([cx-nk, cy+hh-8, cx+nk, GIF_H], fill=skin_mid)
    d.line([(cx-nk, cy+hh-8), (cx-nk, GIF_H)], fill=skin_lo, width=2)
    d.line([(cx+nk, cy+hh-8), (cx+nk, GIF_H)], fill=skin_lo, width=2)

    img = img.filter(ImageFilter.GaussianBlur(radius=1.8))
    return img


def make_brightness(face_img_gray):
    small = face_img_gray.resize((COLS, ROWS), Image.LANCZOS)
    return np.array(small, dtype=np.float32) / 255.0


# --- Render face images (full res) ---
print("Rendering face images...")
FACE_CONFIGS = [
    (0.17, 185, 245, 'cyan'),
    (0.50, 185, 245, 'cyan'),
    (0.83, 185, 245, 'cyan'),
]

face_images = []
for (cx, fw, fh, scheme) in FACE_CONFIGS:
    fi = render_face_image(cx, fw, fh, scheme)
    face_images.append(fi)

# Combined brightness for char-band selection
gray_maps = [fi.convert('L') for fi in face_images]
brightness_maps = [make_brightness(g) for g in gray_maps]
combined = np.max(np.stack(brightness_maps), axis=0)

# --- Slice each face image into character-sized tiles ---
# face_tiles[face_idx][row][col] = PIL Image (CW x CH)
face_tiles = []
for fi in face_images:
    tile_grid = []
    for r in range(ROWS):
        row_tiles = []
        for c in range(COLS):
            x0, y0 = c * CW, r * CH
            tile = fi.crop((x0, y0, x0 + CW, y0 + CH))
            row_tiles.append(tile)
        tile_grid.append(row_tiles)
    face_tiles.append(tile_grid)

# --- Build per-cell rotation pools ---
# Pool items: either a str (character) or an int (face_index to use)
print("Building rotation pools...")
rng = random.Random(42)

cell_pools = []        # list of lists: pool items per cell
cell_phases = []       # starting index in pool
cell_speeds = []       # frames per step

FACE_THRESHOLD = 0.05

for r in range(ROWS):
    row_pools, row_phases, row_speeds = [], [], []
    for c in range(COLS):
        b = float(combined[r, c])
        band_idx = 0
        for i, (lo, hi, chars) in enumerate(BANDS):
            if lo <= b < hi:
                band_idx = i
                break
        _, __, char_pool = BANDS[band_idx]

        # Build base char pool (8 entries)
        pool = list(char_pool)

        # Insert 1 face tile reference every FACE_TILE_EVERY slots
        # Pick which face to use for this cell (the closest face)
        best_face = 0
        best_val = 0.0
        for fi_idx, bmap in enumerate(brightness_maps):
            if bmap[r, c] > best_val:
                best_val = bmap[r, c]
                best_face = fi_idx

        # Insert face tile at a random position in the pool
        insert_pos = rng.randint(0, len(pool))
        pool.insert(insert_pos, ('face', best_face))  # tuple = image tile

        row_pools.append(pool)
        row_phases.append(rng.randint(0, len(pool) - 1))
        is_face = b > FACE_THRESHOLD
        row_speeds.append(1 if is_face else rng.randint(1, 3))

    cell_pools.append(row_pools)
    cell_phases.append(row_phases)
    cell_speeds.append(row_speeds)

# --- Font ---
FONT_SIZE = int(CH * 0.90)
font = None
for path in [
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf',
]:
    try:
        font = ImageFont.truetype(path, FONT_SIZE)
        print(f"Font: {path} @ {FONT_SIZE}px")
        break
    except:
        pass
if not font:
    font = ImageFont.load_default()


def band_color(b, f):
    # Cyan-dominant, magenta flash on faces every ~12 frames
    if b < 0.15:   return (20,  0,  40)
    if b < 0.30:   return (0,   60, 100)
    if b < 0.45:   return (0,  120, 160)
    if b < 0.60:   return (0,  190, 230)
    if b < 0.75:   return (80, 220, 255)
    if b < 0.88:   return (160,235, 255)
    return (220, 245, 255)


# --- Render frames ---
print(f"Rendering {FRAMES} frames...")
frames = []

for f in range(FRAMES):
    img = Image.new('RGB', (GIF_W, GIF_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    for r in range(ROWS):
        for c in range(COLS):
            pool  = cell_pools[r][c]
            phase = cell_phases[r][c]
            speed = cell_speeds[r][c]
            idx   = (phase + f * speed) % len(pool)
            item  = pool[idx]
            b     = float(combined[r, c])
            x, y  = c * CW, r * CH

            if isinstance(item, tuple) and item[0] == 'face':
                # Paste the face tile from the corresponding face image
                fi_idx = item[1]
                tile   = face_tiles[fi_idx][r][c]
                img.paste(tile, (x, y))
            else:
                # Draw text character
                color = band_color(b, f)
                # Pulse: brief brightness boost
                if b > FACE_THRESHOLD and f % 8 < 2:
                    color = tuple(min(255, int(v * 1.4)) for v in color)
                draw.text((x + 1, y), item, font=font, fill=color)

    # Scanline
    sl = Image.new('RGBA', (GIF_W, GIF_H), (0, 0, 0, 0))
    sld = ImageDraw.Draw(sl)
    for sy in range(0, GIF_H, 3):
        sld.line([(0, sy), (GIF_W, sy)], fill=(0, 0, 0, 28))
    img = Image.alpha_composite(img.convert('RGBA'), sl).convert('RGB')
    frames.append(img)

    if f % 6 == 0:
        print(f"  frame {f+1}/{FRAMES}")

# --- Save ---
out = '/mnt/shanebrain-raid/pulsar-sentinel/quantum-banner.gif'
frames[0].save(
    out, save_all=True, append_images=frames[1:],
    loop=0, duration=FRAME_MS, optimize=True, colors=128,
)
kb = os.path.getsize(out) // 1024
print(f"\n✓ {out}  ({kb} KB, {FRAMES} frames @ {FRAME_MS}ms)")
print(f"  Each cell pool: {len(cell_pools[0][0])} items (7 chars + 1 face tile)")
