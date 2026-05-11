#!/usr/bin/env python3
"""
Quantum Face Renderer v4 — Ghost in the Machine
- Richer face geometry with detailed eyeballs
- Eye-region cells SYNC their flash so the full eye appears at once
- 2 subliminal eyeball flashes per loop (1 frame each = 65ms, barely perceptible)
- Everything else: chars cycle independently
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np
import math, os, random

GIF_W, GIF_H = 860, 320
COLS, ROWS = 72, 28
CW = int(GIF_W / COLS)
CH = int(GIF_H / ROWS)
FRAMES = 24
FRAME_MS = 65

# Subliminal eye flash on these frame indices (1 frame = 65ms each)
EYE_FLASH_FRAMES = {5, 17}

BANDS = [
    (0.00, 0.12, ['█','▓','#','@','M','W','B','0']),
    (0.12, 0.28, ['0','8','9','Q','G','B','%','&']),
    (0.28, 0.44, ['4','6','5','3','E','F','Z','ψ']),
    (0.44, 0.58, ['7','2','J','T','I','1','Ω','0']),
    (0.58, 0.72, ['!','/','-','|','(',')',':','1']),
    (0.72, 0.85, ['.','·',',','\'','^','`','~',':']),
    (0.85, 1.00, [' ',' ','·','\'',' ',' ','·',' ']),
]
BG_COLOR = (8, 8, 14)


def draw_eyeball(d, ex, ey, rx, ry, scheme):
    """Draw a detailed eyeball centered at (ex,ey) with radii rx,ry."""
    cyan = scheme == 'cyan'
    white  = (210, 230, 230) if cyan else (235, 235, 240)
    iris_o = (0, 160, 200)   if cyan else (40, 90, 160)
    iris_i = (0, 80, 140)    if cyan else (20, 50, 100)
    pupil  = (4, 4, 8)
    vein   = (180, 60, 80)   if cyan else (200, 80, 90)
    lid    = (0, 60, 80)     if cyan else (60, 30, 20)

    # Sclera (white of eye)
    d.ellipse([ex-rx, ey-ry, ex+rx, ey+ry], fill=white)

    # Subtle veins
    for angle in [15, 155, 200, 340]:
        rad = math.radians(angle)
        vx1 = int(ex + rx * 0.35 * math.cos(rad))
        vy1 = int(ey + ry * 0.35 * math.sin(rad))
        vx2 = int(ex + rx * 0.80 * math.cos(rad))
        vy2 = int(ey + ry * 0.80 * math.sin(rad))
        d.line([(vx1,vy1),(vx2,vy2)], fill=vein, width=1)

    # Iris outer
    ir = int(min(rx,ry) * 0.62)
    d.ellipse([ex-ir, ey-ir, ex+ir, ey+ir], fill=iris_o)

    # Iris radial texture (spokes)
    for angle in range(0, 360, 18):
        rad = math.radians(angle)
        ix2 = int(ex + ir * 0.92 * math.cos(rad))
        iy2 = int(ey + ir * 0.92 * math.sin(rad))
        ix1 = int(ex + ir * 0.30 * math.cos(rad))
        iy1 = int(ey + ir * 0.30 * math.sin(rad))
        d.line([(ix1,iy1),(ix2,iy2)], fill=iris_i, width=1)

    # Iris inner gradient ring
    ir2 = int(ir * 0.55)
    d.ellipse([ex-ir2, ey-ir2, ex+ir2, ey+ir2], fill=iris_i)

    # Pupil
    pr = int(ir * 0.38)
    d.ellipse([ex-pr, ey-pr, ex+pr, ey+pr], fill=pupil)

    # Primary catch light (top-left)
    cl = max(pr//2, 3)
    d.ellipse([ex-ir//2-cl//2, ey-ir//2-cl//2,
               ex-ir//2+cl,   ey-ir//2+cl], fill=(255,255,255))

    # Secondary small catch light (bottom-right)
    cl2 = max(cl//2, 2)
    d.ellipse([ex+ir//3, ey+ir//3, ex+ir//3+cl2, ey+ir//3+cl2],
              fill=(200,230,255) if cyan else (200,200,220))

    # Upper eyelid (crease shadow)
    d.arc([ex-rx, ey-ry, ex+rx, ey+ry], start=200, end=340, fill=lid, width=3)

    # Eyelashes — upper
    for angle in range(205, 338, 12):
        rad = math.radians(angle)
        lx1 = int(ex + rx * math.cos(rad))
        ly1 = int(ey + ry * math.sin(rad))
        lx2 = int(ex + (rx+5) * math.cos(rad - math.radians(8)))
        ly2 = int(ey + (ry+6) * math.sin(rad - math.radians(8)))
        d.line([(lx1,ly1),(lx2,ly2)], fill=lid, width=2)

    # Eyelashes — lower (sparser)
    for angle in range(20, 160, 22):
        rad = math.radians(angle)
        lx1 = int(ex + rx * math.cos(rad))
        ly1 = int(ey + ry * math.sin(rad))
        lx2 = int(ex + (rx+3) * math.cos(rad + math.radians(5)))
        ly2 = int(ey + (ry+3) * math.sin(rad + math.radians(5)))
        d.line([(lx1,ly1),(lx2,ly2)], fill=lid, width=1)


def render_face_image(cx_frac, fw, fh, scheme='cyan'):
    img = Image.new('RGB', (GIF_W, GIF_H), BG_COLOR)
    d = ImageDraw.Draw(img)
    cx = int(cx_frac * GIF_W)
    cy = GIF_H // 2
    hw, hh = fw//2, fh//2

    cyan = scheme == 'cyan'
    skin_hi  = (0,220,200) if cyan else (255,205,170)
    skin_mid = (0,140,160) if cyan else (210,155,115)
    skin_lo  = (0, 70, 90) if cyan else (150, 95, 65)
    hair_col = (0, 35, 65) if cyan else (35, 22, 10)
    lip_col  = (255,70,200) if cyan else (185,65,65)

    # Head base
    d.ellipse([cx-hw, cy-hh, cx+hw, cy+hh], fill=skin_mid)
    # Forehead highlight (top-center)
    d.ellipse([cx-hw+20, cy-hh+5, cx+hw-20, cy-hh+hh//2], fill=skin_hi)
    # Jaw shadow
    d.ellipse([cx-hw+10, cy+hh//4, cx+hw-10, cy+hh+8], fill=skin_lo)
    # Cheekbone highlights
    for sign in [-1,1]:
        x0 = cx+sign*(hw//3); x1 = cx+sign*(hw//3)+hw//4
        d.ellipse([min(x0,x1), cy-hh//6, max(x0,x1), cy+hh//6], fill=skin_hi)
    # Temple shadows
    for sign in [-1,1]:
        x0 = cx+sign*(hw-18); x1 = cx+sign*hw
        d.ellipse([min(x0,x1), cy-hh//3, max(x0,x1), cy+hh//4], fill=skin_lo)

    # Hair
    d.ellipse([cx-hw, cy-hh-12, cx+hw, cy-int(hh*0.3)], fill=hair_col)
    d.ellipse([cx-hw, cy-hh, cx-hw+22, cy+hh//4], fill=hair_col)
    d.ellipse([cx+hw-22, cy-hh, cx+hw, cy+hh//4], fill=hair_col)

    # Eyebrows (arched)
    eye_y = cy - int(hh * 0.18)
    eye_rx = int(fw * 0.095)
    eye_ry = int(fh * 0.075)
    for sign in [-1,1]:
        bx = cx + sign * int(fw * 0.22)
        for i in range(-eye_rx, eye_rx, 2):
            arch = int((1 - (i/eye_rx)**2) * 6)
            d.line([(bx+i, eye_y-eye_ry-8+arch),
                    (bx+i, eye_y-eye_ry-5+arch)], fill=hair_col, width=2)

    # Eye sockets shadow
    for sign in [-1,1]:
        ex = cx + sign * int(fw * 0.22)
        d.ellipse([ex-eye_rx-8, eye_y-eye_ry-6,
                   ex+eye_rx+8, eye_y+eye_ry+8], fill=skin_lo)

    # Detailed eyeballs
    for sign in [-1,1]:
        ex = cx + sign * int(fw * 0.22)
        draw_eyeball(d, ex, eye_y, eye_rx, eye_ry, scheme)

    # Nose bridge
    nose_y = cy + int(hh*0.12)
    for ny in range(eye_y+eye_ry, nose_y, 2):
        alpha = (ny - (eye_y+eye_ry)) / max(1, nose_y-(eye_y+eye_ry))
        nw_l = int(4 + alpha * 10)
        d.line([(cx-nw_l, ny),(cx+nw_l, ny)], fill=skin_lo, width=1)

    # Nose tip
    nw = int(fw*0.08)
    d.ellipse([cx-nw, nose_y-5, cx+nw, nose_y+10], fill=skin_lo)
    # Nostrils
    for sign in [-1,1]:
        nox = cx + sign * int(nw*0.8)
        d.ellipse([nox-5, nose_y+2, nox+5, nose_y+12],
                  fill=tuple(max(0,v-25) for v in skin_lo))
    # Nose highlight
    d.ellipse([cx-3, nose_y-8, cx+3, nose_y+2], fill=skin_hi)

    # Philtrum
    d.line([(cx, nose_y+10),(cx, cy+int(hh*0.28))], fill=skin_lo, width=2)

    # Lips
    lip_y = cy + int(hh*0.32)
    lw = int(fw*0.27)
    # upper lip (M-shape)
    d.polygon([
        (cx-lw, lip_y),
        (cx-lw//2, lip_y-10),
        (cx-4, lip_y-5),
        (cx, lip_y-8),
        (cx+4, lip_y-5),
        (cx+lw//2, lip_y-10),
        (cx+lw, lip_y),
    ], fill=lip_col)
    # lower lip
    d.ellipse([cx-lw+8, lip_y, cx+lw-8, lip_y+17],
              fill=tuple(min(255,v+40) for v in lip_col))
    # lip line
    d.line([(cx-lw+4, lip_y),(cx+lw-4, lip_y)],
           fill=tuple(max(0,v-50) for v in lip_col), width=2)
    # lip highlight
    d.ellipse([cx-lw//4, lip_y+3, cx+lw//4, lip_y+9], fill=skin_hi)

    # Ears
    ear_h = int(hh*0.30)
    ear_w = int(fw*0.075)
    ear_y = cy - int(hh*0.05)
    for sign in [-1,1]:
        ex = cx + sign*(hw-3)
        d.ellipse([ex-ear_w, ear_y-ear_h, ex+ear_w, ear_y+ear_h], fill=skin_mid)
        d.ellipse([ex-ear_w+4, ear_y-int(ear_h*0.7),
                   ex+ear_w-3, ear_y+int(ear_h*0.7)], fill=skin_lo)
        d.arc([ex-ear_w+4, ear_y-int(ear_h*0.5),
               ex+ear_w-2, ear_y+int(ear_h*0.5)],
              start=60, end=300, fill=skin_hi, width=2)

    # Neck
    nk = int(fw*0.19)
    d.rectangle([cx-nk, cy+hh-10, cx+nk, GIF_H], fill=skin_mid)
    for sign in [-1,1]:
        d.line([(cx+sign*nk, cy+hh-10),(cx+sign*nk, GIF_H)],
               fill=skin_lo, width=2)
    # Neck highlight (down center)
    d.line([(cx, cy+hh-5),(cx, GIF_H)], fill=skin_hi, width=3)

    img = img.filter(ImageFilter.GaussianBlur(radius=1.5))
    # slight pop
    img = ImageEnhance.Contrast(img).enhance(1.2)
    img = ImageEnhance.Color(img).enhance(1.3)
    return img


# --- Face positions ---
FACE_CONFIGS = [
    (0.17, 185, 248, 'cyan'),
    (0.50, 185, 248, 'cyan'),
    (0.83, 185, 248, 'cyan'),
]

print("Rendering face images...")
face_images = []
for (cx, fw, fh, sc) in FACE_CONFIGS:
    face_images.append(render_face_image(cx, fw, fh, sc))

# Brightness maps for band selection
gray_maps     = [fi.convert('L') for fi in face_images]
brightness_maps = []
for g in gray_maps:
    sm = g.resize((COLS, ROWS), Image.LANCZOS)
    brightness_maps.append(np.array(sm, dtype=np.float32)/255.0)

combined = np.max(np.stack(brightness_maps), axis=0)

# --- Slice tiles ---
print("Slicing tiles...")
face_tiles = []
for fi in face_images:
    tg = []
    for r in range(ROWS):
        row = []
        for c in range(COLS):
            x0,y0 = c*CW, r*CH
            row.append(fi.crop((x0,y0,x0+CW,y0+CH)))
        tg.append(row)
    face_tiles.append(tg)

# --- Identify eye-region cells (for synced subliminal flash) ---
# Eye cells are those whose brightness in the eye socket area is very low (dark sockets)
# and position roughly matches where eyes are for each face.
eye_region = set()  # (r, c)
for fi_idx, (cx_frac, fw, fh, sc) in enumerate(FACE_CONFIGS):
    cx = int(cx_frac * GIF_W)
    cy = GIF_H // 2
    hh = fh // 2
    eye_y  = cy - int(hh * 0.18)
    eye_rx = int(fw * 0.095)
    eye_ry = int(fh * 0.075)
    for sign in [-1, 1]:
        ex = cx + sign * int(fw * 0.22)
        # expand slightly so the full eye + lashes is captured
        x0 = max(0, ex - eye_rx - 12)
        x1 = min(GIF_W-1, ex + eye_rx + 12)
        y0 = max(0, eye_y - eye_ry - 10)
        y1 = min(GIF_H-1, eye_y + eye_ry + 8)
        c0 = int(x0 / CW); c1 = int(x1 / CW) + 1
        r0 = int(y0 / CH); r1 = int(y1 / CH) + 1
        for r in range(r0, min(r1, ROWS)):
            for c in range(c0, min(c1, COLS)):
                eye_region.add((r, c, fi_idx))

print(f"Eye-region cells: {len(eye_region)}")

# --- Build per-cell pools ---
print("Building pools...")
rng = random.Random(42)
FACE_THRESHOLD = 0.05

cell_pools  = []
cell_phases = []
cell_speeds = []

for r in range(ROWS):
    rp, rph, rsp = [], [], []
    for c in range(COLS):
        b = float(combined[r,c])
        band_idx = 0
        for i,(lo,hi,chars) in enumerate(BANDS):
            if lo <= b < hi:
                band_idx = i; break
        pool = list(BANDS[band_idx][2])

        # Best-match face tile
        best_fi, best_val = 0, 0.0
        for fi_idx, bmap in enumerate(brightness_maps):
            if bmap[r,c] > best_val:
                best_val, best_fi = bmap[r,c], fi_idx

        # Insert face tile: 1 slot in the pool
        pool.insert(rng.randint(0, len(pool)), ('face', best_fi))

        rp.append(pool)
        rph.append(rng.randint(0, len(pool)-1))
        is_face = b > FACE_THRESHOLD
        rsp.append(1 if is_face else rng.randint(1, 3))

    cell_pools.append(rp)
    cell_phases.append(rph)
    cell_speeds.append(rsp)

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


def band_color(b):
    if b < 0.15: return (20,  0,  40)
    if b < 0.30: return (0,   55, 95)
    if b < 0.45: return (0,  115, 155)
    if b < 0.60: return (0,  185, 225)
    if b < 0.75: return (70, 215, 255)
    if b < 0.88: return (150,232, 255)
    return (215, 245, 255)


# --- Render ---
print(f"Rendering {FRAMES} frames...")
frames = []

# Pre-build eye flash tiles per fi_idx
eye_flash_tiles = {}
for (r, c, fi_idx) in eye_region:
    if fi_idx not in eye_flash_tiles:
        eye_flash_tiles[fi_idx] = {}
    eye_flash_tiles[fi_idx][(r,c)] = face_tiles[fi_idx][r][c]

for f in range(FRAMES):
    img = Image.new('RGB', (GIF_W, GIF_H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    is_eye_flash = f in EYE_FLASH_FRAMES

    for r in range(ROWS):
        for c in range(COLS):
            x, y = c * CW, r * CH
            b = float(combined[r,c])

            # --- Subliminal eye flash: all eye cells show real face ---
            if is_eye_flash:
                for fi_idx in range(len(face_images)):
                    if (r, c, fi_idx) in {e for e in eye_region}:
                        img.paste(face_tiles[fi_idx][r][c], (x, y))
                        break
                else:
                    # Normal char for non-eye cells even on flash frame
                    pool  = cell_pools[r][c]
                    phase = cell_phases[r][c]
                    speed = cell_speeds[r][c]
                    idx   = (phase + f * speed) % len(pool)
                    item  = pool[idx]
                    color = band_color(b)
                    if isinstance(item, tuple):
                        img.paste(face_tiles[item[1]][r][c], (x, y))
                    else:
                        draw.text((x+1, y), item, font=font, fill=color)
                continue

            # --- Normal frame ---
            pool  = cell_pools[r][c]
            phase = cell_phases[r][c]
            speed = cell_speeds[r][c]
            idx   = (phase + f * speed) % len(pool)
            item  = pool[idx]
            color = band_color(b)

            if b > FACE_THRESHOLD and f % 8 < 2:
                color = tuple(min(255, int(v*1.4)) for v in color)

            if isinstance(item, tuple) and item[0] == 'face':
                img.paste(face_tiles[item[1]][r][c], (x, y))
            else:
                draw.text((x+1, y), item, font=font, fill=color)

    # Scanlines
    sl = Image.new('RGBA', (GIF_W, GIF_H), (0,0,0,0))
    sld = ImageDraw.Draw(sl)
    for sy in range(0, GIF_H, 3):
        sld.line([(0,sy),(GIF_W,sy)], fill=(0,0,0,25))
    img = Image.alpha_composite(img.convert('RGBA'), sl).convert('RGB')
    frames.append(img)

    if f % 6 == 0:
        print(f"  frame {f+1}/{FRAMES}")

out = '/mnt/shanebrain-raid/pulsar-sentinel/quantum-banner.gif'
frames[0].save(
    out, save_all=True, append_images=frames[1:],
    loop=0, duration=FRAME_MS, optimize=True, colors=192,
)
kb = os.path.getsize(out) // 1024
print(f"\n✓ {out}  ({kb} KB, {FRAMES} frames @ {FRAME_MS}ms)")
print(f"  Eye flash on frames: {sorted(EYE_FLASH_FRAMES)}")
