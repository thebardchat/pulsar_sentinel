#!/usr/bin/env python3
"""
Quantum Face Renderer v5 — Ghost in the Machine
- Anatomically correct, naturally-open eyes (upper lid covers ~35% of iris)
- 6 eyes flash independently across 24 frames — never two at once
- Face tiles paste only for the flashing eye, staggered per face/side
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

# Per-eye flash schedule: (face_idx, eye_sign) -> frame
# 6 eyes spread across 24 frames, no two adjacent
EYE_FLASH_MAP = {(0,-1):2, (2,1):6, (1,-1):11, (0,1):15, (2,-1):19, (1,1):22}
FRAME_FLASH = {}
for (fi, s), fr in EYE_FLASH_MAP.items():
    FRAME_FLASH.setdefault(fr, []).append((fi, s))

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


def draw_anatomical_eye(d, ex, ey, rx, ry, scheme):
    """
    Anatomically correct eye in resting (natural) position.
    Upper lid covers ~35% of iris. Draw-over approach: full eyeball first,
    then lid polygons cover top and bottom. Lateral canthus slightly higher
    than medial (canthal tilt).
    """
    if scheme == 'cyan':
        sclera_c = (220, 228, 222)
        iris_o   = (0, 160, 200)
        iris_i   = (0, 80, 140)
        vein_c   = (190, 70, 85)
        lid_c    = (0, 55, 75)
    else:
        sclera_c = (238, 232, 226)
        iris_o   = (55, 105, 168)
        iris_i   = (30, 62, 112)
        vein_c   = (210, 90, 98)
        lid_c    = (78, 48, 36)

    lash_c  = (8, 8, 14)
    carun_c = (215, 138, 138)

    # 1. SCLERA
    d.ellipse([ex-rx, ey-ry, ex+rx, ey+ry], fill=sclera_c)

    # 2. VEINS
    for ang in [18, 158, 198, 342]:
        r = math.radians(ang)
        d.line([
            (int(ex + rx*0.35*math.cos(r)), int(ey + ry*0.35*math.sin(r))),
            (int(ex + rx*0.80*math.cos(r)), int(ey + ry*0.80*math.sin(r)))
        ], fill=vein_c, width=1)

    # 3. IRIS
    ir = int(min(rx, ry) * 0.62)
    d.ellipse([ex-ir, ey-ir, ex+ir, ey+ir], fill=iris_o)
    for ang in range(0, 360, 14):
        r = math.radians(ang)
        d.line([
            (int(ex + ir*0.28*math.cos(r)), int(ey + ir*0.28*math.sin(r))),
            (int(ex + ir*0.93*math.cos(r)), int(ey + ir*0.93*math.sin(r)))
        ], fill=iris_i, width=1)
    ir2 = int(ir * 0.52)
    d.ellipse([ex-ir2, ey-ir2, ex+ir2, ey+ir2], fill=iris_i)

    # 4. PUPIL
    pr = int(ir * 0.40)
    d.ellipse([ex-pr, ey-pr, ex+pr, ey+pr], fill=(6, 6, 10))

    # 5. CATCH LIGHTS
    cl = max(pr//2, 3)
    d.ellipse([ex-ir//2-cl//2, ey-ir//2-cl//2,
               ex-ir//2+cl,    ey-ir//2+cl], fill=(255, 255, 255))
    cl2 = max(cl//2, 2)
    d.ellipse([ex+ir//3, ey+ir//4, ex+ir//3+cl2, ey+ir//4+cl2],
              fill=(210, 235, 255))

    # 6. UPPER EYELID POLYGON (draw-over top of sclera)
    # Lid margin: medial canthus (inner/left) is lower, lateral (outer/right) is higher
    # Max depth at center: covers 35% of iris from top
    N = 28
    med_y   = ey + int(ry * 0.05)    # medial canthus y (inner corner, slightly below center)
    lat_y   = ey - int(ry * 0.08)    # lateral canthus y (outer corner, slightly above center)
    lid_max = ey - int(ir * 0.35)    # deepest point of lid margin (at center of lid)

    # Build lid margin points (medial=left to lateral=right)
    lid_margin = []
    for i in range(N+1):
        t = i / N
        x = int(ex - rx + t * 2 * rx)
        # Canthal tilt baseline
        y_base = int(med_y + t * (lat_y - med_y))
        # Lid dip: sin curve, peak slightly toward lateral side
        dip = math.sin(math.pi * min(t * 1.1, 1.0))
        y = int(y_base + (lid_max - y_base) * dip)
        lid_margin.append((x, y))

    # Polygon: top arc of sclera (left→right through top), then lid margin (right→left)
    upper_pts = []
    for ang in range(181, 361, 7):
        r = math.radians(ang)
        upper_pts.append((int(ex + rx*math.cos(r)), int(ey + ry*math.sin(r))))
    upper_pts.append((ex + rx, lat_y))
    for pt in reversed(lid_margin):
        upper_pts.append(pt)
    upper_pts.append((ex - rx, med_y))

    if len(upper_pts) >= 3:
        d.polygon(upper_pts, fill=lid_c)

    # 7. LOWER EYELID POLYGON (thin strip)
    low_top_y = ey + ir    # upper edge of lower lid = iris bottom

    lower_pts = []
    for ang in range(0, 181, 7):
        r = math.radians(ang)
        lower_pts.append((int(ex + rx*math.cos(r)), int(ey + ry*math.sin(r))))
    # Upper edge of lower lid (slight upward curve at center)
    for i in range(N+1):
        t = i / N
        x = int(ex - rx + t * 2 * rx)
        y = int(low_top_y - math.sin(math.pi * t) * 3)
        lower_pts.append((x, y))

    if len(lower_pts) >= 3:
        d.polygon(lower_pts, fill=lid_c)

    # 8. LID MARGIN LINES
    for i in range(len(lid_margin)-1):
        d.line([lid_margin[i], lid_margin[i+1]], fill=lash_c, width=2)
    # Lower lid edge
    for i in range(N):
        t0, t1 = i/N, (i+1)/N
        x0 = int(ex - rx + t0*2*rx); x1 = int(ex - rx + t1*2*rx)
        y0 = int(low_top_y - math.sin(math.pi*t0)*3)
        y1 = int(low_top_y - math.sin(math.pi*t1)*3)
        d.line([(x0,y0),(x1,y1)], fill=(100, 65, 50), width=1)

    # 9. EYELID CREASE (subtle arc above upper lid)
    crease_pts = []
    for i in range(N+1):
        t = i / N
        idx = min(i, N)
        lm_y = lid_margin[idx][1]
        x = int(ex - rx*0.88 + t * 2 * rx*0.88)
        dip = math.sin(math.pi * min(t*1.1, 1.0))
        y = int(lm_y - ry * 0.20 * dip)
        crease_pts.append((x, y))
    darker_lid = tuple(max(0, v-28) for v in lid_c)
    for i in range(len(crease_pts)-1):
        d.line([crease_pts[i], crease_pts[i+1]], fill=darker_lid, width=1)

    # 10. UPPER LASHES (from lid margin, angled outward and up)
    for ang in range(208, 335, 10):
        r_ang = math.radians(ang)
        lx1 = int(ex + rx * math.cos(r_ang))
        ly1 = int(ey + ry * math.sin(r_ang))
        # Central lashes go more upward; edge lashes angle outward
        center_offset = (ang - 270) / 65.0
        sweep = math.radians(12 + abs(center_offset) * 9)
        lx2 = int(lx1 + rx * 0.23 * math.cos(r_ang - sweep))
        ly2 = int(ly1 + ry * 0.38 * math.sin(r_ang - sweep))
        d.line([(lx1,ly1),(lx2,ly2)], fill=lash_c, width=2)

    # 11. LOWER LASHES (sparse, shorter, angle downward)
    for ang in range(28, 155, 24):
        r_ang = math.radians(ang)
        lx1 = int(ex + rx * math.cos(r_ang))
        ly1 = int(ey + ry * math.sin(r_ang))
        lx2 = int(lx1 + rx*0.12 * math.cos(r_ang + math.radians(10)))
        ly2 = int(ly1 + ry*0.20 * math.sin(r_ang + math.radians(10)))
        d.line([(lx1,ly1),(lx2,ly2)], fill=lash_c, width=1)

    # 12. CARUNCLE (medial canthus pink flesh)
    d.ellipse([ex-rx-1, ey-3, ex-rx+6, ey+5], fill=carun_c)


def render_face_image(cx_frac, fw, fh, scheme='cyan'):
    img = Image.new('RGB', (GIF_W, GIF_H), BG_COLOR)
    d = ImageDraw.Draw(img)
    cx = int(cx_frac * GIF_W)
    cy = GIF_H // 2
    hw, hh = fw//2, fh//2

    cyan = scheme == 'cyan'
    skin_hi  = (0, 220, 200)  if cyan else (255, 205, 170)
    skin_mid = (0, 140, 160)  if cyan else (210, 155, 115)
    skin_lo  = (0,  70,  90)  if cyan else (150,  95,  65)
    hair_col = (0,  35,  65)  if cyan else ( 35,  22,  10)
    lip_col  = (255, 70, 200) if cyan else (185,  65,  65)

    # Head
    d.ellipse([cx-hw, cy-hh, cx+hw, cy+hh], fill=skin_mid)
    d.ellipse([cx-hw+20, cy-hh+5, cx+hw-20, cy-hh+hh//2], fill=skin_hi)
    d.ellipse([cx-hw+10, cy+hh//4, cx+hw-10, cy+hh+8], fill=skin_lo)
    for sign in [-1, 1]:
        x0 = cx+sign*(hw//3); x1 = cx+sign*(hw//3)+hw//4
        d.ellipse([min(x0,x1), cy-hh//6, max(x0,x1), cy+hh//6], fill=skin_hi)
    for sign in [-1, 1]:
        x0 = cx+sign*(hw-18); x1 = cx+sign*hw
        d.ellipse([min(x0,x1), cy-hh//3, max(x0,x1), cy+hh//4], fill=skin_lo)

    # Hair
    d.ellipse([cx-hw, cy-hh-12, cx+hw, cy-int(hh*0.3)], fill=hair_col)
    d.ellipse([cx-hw, cy-hh, cx-hw+22, cy+hh//4], fill=hair_col)
    d.ellipse([cx+hw-22, cy-hh, cx+hw, cy+hh//4], fill=hair_col)

    eye_y  = cy - int(hh * 0.18)
    eye_rx = int(fw * 0.095)
    eye_ry = int(fh * 0.075)

    # Eyebrows
    for sign in [-1, 1]:
        bx = cx + sign * int(fw * 0.22)
        for i in range(-eye_rx, eye_rx, 2):
            arch = int((1 - (i/eye_rx)**2) * 6)
            d.line([(bx+i, eye_y-eye_ry-8+arch),
                    (bx+i, eye_y-eye_ry-5+arch)], fill=hair_col, width=2)

    # Eye sockets
    for sign in [-1, 1]:
        ex = cx + sign * int(fw * 0.22)
        d.ellipse([ex-eye_rx-8, eye_y-eye_ry-6,
                   ex+eye_rx+8, eye_y+eye_ry+8], fill=skin_lo)

    # Anatomically correct eyes
    for sign in [-1, 1]:
        ex = cx + sign * int(fw * 0.22)
        draw_anatomical_eye(d, ex, eye_y, eye_rx, eye_ry, scheme)

    # Nose
    nose_y = cy + int(hh*0.12)
    for ny in range(eye_y+eye_ry, nose_y, 2):
        alpha = (ny - (eye_y+eye_ry)) / max(1, nose_y-(eye_y+eye_ry))
        nw_l = int(4 + alpha * 10)
        d.line([(cx-nw_l, ny),(cx+nw_l, ny)], fill=skin_lo, width=1)
    nw = int(fw*0.08)
    d.ellipse([cx-nw, nose_y-5, cx+nw, nose_y+10], fill=skin_lo)
    for sign in [-1, 1]:
        nox = cx + sign * int(nw*0.8)
        d.ellipse([nox-5, nose_y+2, nox+5, nose_y+12],
                  fill=tuple(max(0,v-25) for v in skin_lo))
    d.ellipse([cx-3, nose_y-8, cx+3, nose_y+2], fill=skin_hi)
    d.line([(cx, nose_y+10),(cx, cy+int(hh*0.28))], fill=skin_lo, width=2)

    # Lips
    lip_y = cy + int(hh*0.32)
    lw = int(fw*0.27)
    d.polygon([
        (cx-lw, lip_y), (cx-lw//2, lip_y-10), (cx-4, lip_y-5),
        (cx, lip_y-8), (cx+4, lip_y-5), (cx+lw//2, lip_y-10), (cx+lw, lip_y),
    ], fill=lip_col)
    d.ellipse([cx-lw+8, lip_y, cx+lw-8, lip_y+17],
              fill=tuple(min(255,v+40) for v in lip_col))
    d.line([(cx-lw+4, lip_y),(cx+lw-4, lip_y)],
           fill=tuple(max(0,v-50) for v in lip_col), width=2)
    d.ellipse([cx-lw//4, lip_y+3, cx+lw//4, lip_y+9], fill=skin_hi)

    # Ears
    ear_h = int(hh*0.30); ear_w = int(fw*0.075); ear_y = cy - int(hh*0.05)
    for sign in [-1, 1]:
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
    for sign in [-1, 1]:
        d.line([(cx+sign*nk, cy+hh-10),(cx+sign*nk, GIF_H)],
               fill=skin_lo, width=2)
    d.line([(cx, cy+hh-5),(cx, GIF_H)], fill=skin_hi, width=3)

    img = img.filter(ImageFilter.GaussianBlur(radius=1.5))
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

gray_maps = [fi.convert('L') for fi in face_images]
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
            x0, y0 = c*CW, r*CH
            row.append(fi.crop((x0, y0, x0+CW, y0+CH)))
        tg.append(row)
    face_tiles.append(tg)

# --- Per-eye cell sets: (face_idx, sign) -> set of (r, c) ---
eye_cells = {}
for fi_idx, (cx_frac, fw, fh, sc) in enumerate(FACE_CONFIGS):
    cx = int(cx_frac * GIF_W)
    cy = GIF_H // 2
    hh = fh // 2
    eye_y  = cy - int(hh * 0.18)
    eye_rx = int(fw * 0.095)
    eye_ry = int(fh * 0.075)
    for sign in [-1, 1]:
        ex_px = cx + sign * int(fw * 0.22)
        x0 = max(0, ex_px - eye_rx - 12)
        x1 = min(GIF_W-1, ex_px + eye_rx + 12)
        y0 = max(0, eye_y - eye_ry - 12)
        y1 = min(GIF_H-1, eye_y + eye_ry + 10)
        c0 = int(x0/CW); c1 = int(x1/CW) + 1
        r0 = int(y0/CH); r1 = int(y1/CH) + 1
        cell_set = set()
        for r in range(r0, min(r1, ROWS)):
            for c in range(c0, min(c1, COLS)):
                cell_set.add((r, c))
        eye_cells[(fi_idx, sign)] = cell_set

total_eye_cells = sum(len(v) for v in eye_cells.values())
print(f"Eye-region cells: {total_eye_cells} across 6 eyes")

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
        b = float(combined[r, c])
        band_idx = 0
        for i, (lo, hi, chars) in enumerate(BANDS):
            if lo <= b < hi:
                band_idx = i; break
        pool = list(BANDS[band_idx][2])

        best_fi, best_val = 0, 0.0
        for fi_idx, bmap in enumerate(brightness_maps):
            if bmap[r, c] > best_val:
                best_val, best_fi = bmap[r, c], fi_idx
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
    if b < 0.15: return (20,   0,  40)
    if b < 0.30: return (0,   55,  95)
    if b < 0.45: return (0,  115, 155)
    if b < 0.60: return (0,  185, 225)
    if b < 0.75: return (70, 215, 255)
    if b < 0.88: return (150,232, 255)
    return (215, 245, 255)


# --- Render ---
print(f"Rendering {FRAMES} frames...")
frames = []

for f in range(FRAMES):
    img = Image.new('RGB', (GIF_W, GIF_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Which eye cells flash this frame?
    flash_cell_map = {}  # (r,c) -> fi_idx
    for (fi_idx, sign) in FRAME_FLASH.get(f, []):
        for (r, c) in eye_cells.get((fi_idx, sign), set()):
            flash_cell_map[(r, c)] = fi_idx

    for r in range(ROWS):
        for c in range(COLS):
            x, y = c * CW, r * CH
            b = float(combined[r, c])

            if (r, c) in flash_cell_map:
                fi_idx = flash_cell_map[(r, c)]
                img.paste(face_tiles[fi_idx][r][c], (x, y))
                continue

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
flash_info = {fr: [(fi,s) for (fi,s) in eyes] for fr, eyes in FRAME_FLASH.items()}
print(f"  Eye flashes: {flash_info}")
