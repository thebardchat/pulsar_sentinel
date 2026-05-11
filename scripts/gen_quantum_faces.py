#!/usr/bin/env python3
"""
Quantum Face Renderer — Human faces built entirely from numbers/symbols.
The SHAPE comes from character density mapped to brightness.
The MOTION comes from characters cycling within each brightness band.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import math, os

# --- Output config ---
GIF_W, GIF_H = 860, 320
COLS, ROWS = 72, 28
CW = GIF_W / COLS
CH = GIF_H / ROWS
FRAMES = 20
FRAME_MS = 70

# --- Brightness → character bands (dark to bright) ---
# Each band has a pool; each frame picks the next char in pool
BANDS = [
    (0.00, 0.12, ['█','█','▓','W','M','#','@','B']),           # deep shadow
    (0.12, 0.28, ['0','8','9','Q','G','&','B','%']),            # shadow
    (0.28, 0.44, ['4','6','5','3','E','F','Z','ψ']),            # mid-dark
    (0.44, 0.58, ['0','7','2','J','T','I','1','Ω']),            # mid
    (0.58, 0.72, ['1','!','/','\\','|','(',')','-']),           # mid-light
    (0.72, 0.85, ['.','·',',','\'','^','`','~',':']),           # light
    (0.85, 1.00, [' ',' ','·','\'',' ',' ','·',' ']),          # highlight / void
]

BG_COLOR = (8, 8, 14)

def get_band(brightness):
    for i, (lo, hi, chars) in enumerate(BANDS):
        if lo <= brightness < hi:
            return i, chars
    return len(BANDS)-1, BANDS[-1][2]

def band_color(band_idx, is_face):
    """Color per brightness band"""
    colors = [
        (30,  0,  50),   # deep shadow - dark purple
        (0,  40,  80),   # shadow - dark cyan
        (0, 100, 160),   # mid-dark - cyan
        (0, 180, 220),   # mid - bright cyan
        (40, 220, 255),  # mid-light - ice cyan
        (180, 240, 255), # light
        (230, 248, 255), # highlight
    ]
    if not is_face:
        return tuple(max(0, c - 30) for c in colors[band_idx])
    return colors[band_idx]

def make_face_image(cx_norm, face_w, face_h):
    """Render a face into a float32 numpy array (0=dark, 1=bright).
       cx_norm: 0..1 across the full canvas.
       Returns brightness array shape (ROWS, COLS).
    """
    img = Image.new('L', (GIF_W, GIF_H), 0)
    d = ImageDraw.Draw(img)

    cx = int(cx_norm * GIF_W)
    cy = GIF_H // 2

    # --- Head ---
    hw, hh = face_w // 2, face_h // 2
    d.ellipse([cx-hw, cy-hh, cx+hw, cy+hh], fill=160)

    # --- Forehead brighter ---
    d.ellipse([cx-hw+10, cy-hh, cx+hw-10, cy], fill=200)

    # --- Cheeks / jaw shadow ---
    d.ellipse([cx-hw, cy, cx+hw, cy+hh+10], fill=120)

    # --- Brow ridge ---
    brow_y = cy - int(hh * 0.25)
    d.ellipse([cx - hw + 15, brow_y - 12, cx + hw - 15, brow_y + 6], fill=220)

    # --- Eyes (dark with highlight) ---
    eye_rx, eye_ry = int(face_w * 0.085), int(face_h * 0.065)
    eye_y = cy - int(hh * 0.18)
    for sign in [-1, 1]:
        ex = cx + sign * int(face_w * 0.22)
        # eye socket shadow
        d.ellipse([ex - eye_rx - 4, eye_y - eye_ry - 4,
                   ex + eye_rx + 4, eye_y + eye_ry + 4], fill=20)
        # iris
        d.ellipse([ex - eye_rx, eye_y - eye_ry,
                   ex + eye_rx, eye_y + eye_ry], fill=45)
        # pupil
        pr = min(eye_rx, eye_ry) // 2
        d.ellipse([ex - pr, eye_y - pr, ex + pr, eye_y + pr], fill=5)
        # catch light
        cl = max(2, pr // 2)
        d.ellipse([ex - eye_rx // 2, eye_y - eye_ry // 2,
                   ex - eye_rx // 2 + cl, eye_y - eye_ry // 2 + cl], fill=240)

    # --- Nose ---
    nose_y = cy + int(hh * 0.1)
    nose_w = int(face_w * 0.12)
    d.polygon([
        (cx, cy - int(hh * 0.05)),
        (cx - nose_w, nose_y + 8),
        (cx - nose_w + 5, nose_y + 14),
        (cx, nose_y + 8),
        (cx + nose_w - 5, nose_y + 14),
        (cx + nose_w, nose_y + 8),
    ], fill=100)

    # --- Philtrum shadow ---
    d.ellipse([cx - 8, nose_y + 8, cx + 8, nose_y + 22], fill=90)

    # --- Lips ---
    lip_y = cy + int(hh * 0.32)
    lip_w = int(face_w * 0.28)
    # upper lip
    d.ellipse([cx - lip_w, lip_y - 12, cx + lip_w, lip_y + 4], fill=80)
    # lower lip (fuller)
    d.ellipse([cx - lip_w + 6, lip_y, cx + lip_w - 6, lip_y + 18], fill=100)
    # lip line
    d.line([(cx - lip_w + 8, lip_y), (cx + lip_w - 8, lip_y)], fill=30, width=2)

    # --- Hair ---
    d.ellipse([cx - hw, cy - hh - 10, cx + hw, cy - int(hh * 0.4)], fill=40)

    # --- Ears ---
    ear_y = cy - int(hh * 0.05)
    ear_h = int(hh * 0.35)
    ear_w = int(face_w * 0.07)
    for sign in [-1, 1]:
        ex = cx + sign * (hw - 2)
        d.ellipse([ex - ear_w, ear_y - ear_h,
                   ex + ear_w, ear_y + ear_h], fill=130)

    # --- Neck ---
    neck_w = int(face_w * 0.22)
    d.rectangle([cx - neck_w, cy + hh - 10, cx + neck_w, GIF_H], fill=110)

    # Slight blur for smooth gradients
    img = img.filter(ImageFilter.GaussianBlur(radius=3))

    # Resize to character grid
    small = img.resize((COLS, ROWS), Image.LANCZOS)
    arr = np.array(small, dtype=np.float32) / 255.0
    return arr

# --- Build 3 face brightness maps ---
face_configs = [
    (0.17, 180, 240),  # left face
    (0.50, 180, 240),  # center face
    (0.83, 180, 240),  # right face
]

brightness_maps = []
for (cx_norm, fw, fh) in face_configs:
    brightness_maps.append(make_face_image(cx_norm, fw, fh))

# Composite brightness — max across all 3 faces
combined = np.max(np.stack(brightness_maps), axis=0)

# For each cell, determine band and face membership
cell_data = np.zeros((ROWS, COLS), dtype=int)  # band index
cell_is_face = np.zeros((ROWS, COLS), dtype=bool)
FACE_THRESHOLD = 0.04

for r in range(ROWS):
    for c in range(COLS):
        b = float(combined[r, c])
        band_idx, _ = get_band(b)
        cell_data[r, c] = band_idx
        # Is this cell "inside" any face shape?
        cell_is_face[r, c] = b > FACE_THRESHOLD

# Per-cell phase offsets for animation variety
rng = np.random.default_rng(42)
phases = rng.integers(0, 8, size=(ROWS, COLS))
# Face cells cycle slower than background
speeds = np.where(cell_is_face, 1, rng.integers(2, 5, size=(ROWS, COLS)))

# --- Load font ---
FONT_SIZE = int(CH * 0.92)
font = None
for path in [
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf',
    '/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf',
]:
    try:
        font = ImageFont.truetype(path, FONT_SIZE)
        print(f"Font: {path} @ {FONT_SIZE}px")
        break
    except:
        pass
if font is None:
    font = ImageFont.load_default()
    print("Font: default fallback")

# --- Render frames ---
print(f"Rendering {FRAMES} frames ({COLS}x{ROWS} grid)...")
frames = []

for f in range(FRAMES):
    img = Image.new('RGB', (GIF_W, GIF_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    for r in range(ROWS):
        for c in range(COLS):
            band_idx = int(cell_data[r, c])
            _, __, chars = BANDS[band_idx]
            is_face = bool(cell_is_face[r, c])

            # Which character this frame
            char_idx = (int(phases[r, c]) + f * int(speeds[r, c])) % len(chars)
            ch = chars[char_idx]

            x = c * CW
            y = r * CH

            color = band_color(band_idx, is_face)

            # Pulse: brighter on beat frames
            if is_face and f % 8 < 2:
                color = tuple(min(255, int(v * 1.35)) for v in color)
            # Occasional magenta flash on eyes/mouth region
            elif is_face and band_idx <= 2 and f % 12 == 0:
                color = (min(255, color[0]+120), color[1]//2, min(255, color[2]+80))

            draw.text((x + 1, y), ch, font=font, fill=color)

    # Scanline overlay
    scan_layer = Image.new('RGBA', (GIF_W, GIF_H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scan_layer)
    for sy in range(0, GIF_H, 3):
        sd.line([(0, sy), (GIF_W, sy)], fill=(0, 0, 0, 35))
    img = Image.alpha_composite(img.convert('RGBA'), scan_layer).convert('RGB')

    frames.append(img)
    if f % 8 == 0:
        print(f"  frame {f+1}/{FRAMES}")

# --- Save GIF ---
out = '/mnt/shanebrain-raid/pulsar-sentinel/quantum-banner.gif'
frames[0].save(
    out,
    save_all=True,
    append_images=frames[1:],
    loop=0,
    duration=FRAME_MS,
    optimize=True,
    colors=128,
)
size_kb = os.path.getsize(out) // 1024
print(f"\n✓ Saved → {out}  ({size_kb} KB, {FRAMES} frames @ {FRAME_MS}ms)")
print(f"  Grid: {COLS}×{ROWS}, GIF: {GIF_W}×{GIF_H}")
