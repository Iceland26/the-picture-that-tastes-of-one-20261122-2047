#!/usr/bin/env python3
"""The picture that tastes of one ingredient — one ripe strawberry.

Procedural, deterministic, Python 3.13 stdlib only. Renders a single ripe
strawberry on a matte white plate and writes /output/entry.png (960x960).

Run:  python3 main.py
"""
import math
import struct
import zlib

W = 960
H = 960
OUT = "/output/entry.png"

# ---------------------------------------------------------------- helpers
def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v

def mix(a, b, t):
    return a + (b - a) * t

def ss(a, b, x):  # smoothstep
    t = clamp((x - a) / (b - a))
    return t * t * (3.0 - 2.0 * t)

# ------------------------------------------------------------ scene layout
# Plate
PL_CX, PL_CY, PL_RX, PL_RY = 480.0, 600.0, 375.0, 145.0
# Strawberry body: top y0 -> tip y1, half-width profile halfw(t)
BY0, BY1 = 240.0, 700.0
BH = BY1 - BY0
B_MAXW = 272.0

def berry_cx(t):
    return 480.0 + 18.0 * math.sin(t * 1.8) - 9.0 * t

def berry_hw(t):
    # wide shoulders, tapering to a rounded tip; gently rounded crown
    w = B_MAXW * (1.0 - t ** 2.4) ** 0.6
    return w * (0.62 + 0.38 * ss(0.0, 0.18, t))

HW_TOP = berry_hw(0.0)  # crown half-width, for the curved top edge

# Calyx: 6 pointed leaves fanning from the crown
LEAF_CX, LEAF_CY = 480.0, 268.0
LEAVES = [(-0.85, 100.0), (-0.52, 112.0), (-0.18, 96.0),
          (0.18, 98.0), (0.52, 110.0), (0.85, 100.0)]  # angle rad, length

# Juice droplets on the plate (x, y, rx, ry)
DROPS = [(700.0, 648.0, 19.0, 11.0), (748.0, 668.0, 14.0, 9.0),
         (652.0, 692.0, 12.0, 8.0), (792.0, 636.0, 10.0, 6.0),
         (300.0, 668.0, 13.0, 8.0)]

# ------------------------------------------------------------- seed layout
# Achenes in staggered rows; analytic lookup per pixel (no RNG anywhere).
SEED_DT = 0.095
SEED_SP = 52.0

def seed_at(x, y):
    """Return (kind, d2) for the achene/dimple nearest pixel (x, y):
    kind 1 = seed body, 2 = dimple ring, 0 = none. d2 = normalised dist^2."""
    t = (y - BY0) / BH
    if t < 0.06 or t > 0.99:
        return 0, 0.0
    k = int(round(t / SEED_DT))
    tk = k * SEED_DT
    if tk < 0.08 or tk > 0.97:
        return 0, 0.0
    cxk = berry_cx(tk)
    hwk = berry_hw(tk)
    if hwk < 26.0:
        return 0, 0.0
    off = (k & 1) * (SEED_SP * 0.5)
    j = int(round((x - cxk - off) / SEED_SP))
    sx = cxk + off + j * SEED_SP
    if abs(sx - cxk) > hwk - 14.0:
        return 0, 0.0
    syk = BY0 + tk * BH
    # seed ellipse, slightly elongated along the berry surface
    dx = (x - sx) / 5.0
    dy = (y - syk) / 7.5
    d2 = dx * dx + dy * dy
    if d2 < 1.0:
        return 1, d2
    # dimple: dark crescent ring just outside the seed, biased downward
    dx2 = (x - sx) / 8.5
    dy2 = (y - syk - 2.0) / 11.0
    d2b = dx2 * dx2 + dy2 * dy2
    if 1.0 <= d2b < 1.7:
        return 2, d2b
    return 0, 0.0

# ------------------------------------------------------------------- render
def render():
    img = bytearray(W * H * 3)
    for y in range(H):
        fy = float(y)
        row = y * W * 3
        # background: warm cream vertical gradient + soft vignette
        bg_t = fy / (H - 1)
        bg_r = mix(255.0, 243.0, bg_t)
        bg_g = mix(249.0, 230.0, bg_t)
        bg_b = mix(242.0, 216.0, bg_t)
        # plate ellipse (normalised)
        pdx = (480.0 - PL_CX) / PL_RX  # placeholder, per-pixel below
        for x in range(W):
            fx = float(x)
            # --- background with gentle vignette
            vx = (fx - 480.0) / 480.0
            vy = (fy - 480.0) / 480.0
            vig = 1.0 - 0.10 * (vx * vx + vy * vy) * 0.5
            r, g, b = bg_r * vig, bg_g * vig, bg_b * vig

            # --- soft shadow under the plate
            sdx = (fx - 480.0) / 395.0
            sdy = (fy - 622.0) / 158.0
            sd = sdx * sdx + sdy * sdy
            if 0.7 < sd < 1.6:
                a = 0.16 * ss(1.6, 0.85, sd)
                r = mix(r, 120.0, a); g = mix(g, 100.0, a); b = mix(b, 88.0, a)

            # --- plate (matte white, rim slightly warm grey)
            pdx = (fx - PL_CX) / PL_RX
            pdy = (fy - PL_CY) / PL_RY
            pd = pdx * pdx + pdy * pdy
            if pd < 1.05:
                pa = clamp((1.05 - pd) / 0.05)  # anti-aliased rim
                # radial shading: brighter centre-top, faint warm rim
                pr = mix(252.0, 232.0, ss(0.2, 1.0, pd))
                pg = mix(250.0, 224.0, ss(0.2, 1.0, pd))
                pb = mix(246.0, 210.0, ss(0.2, 1.0, pd))
                # faint inner ring near the rim
                ring = ss(0.86, 0.90, pd) * (1.0 - ss(0.94, 0.99, pd))
                pr = mix(pr, 214.0, ring * 0.5)
                pg = mix(pg, 203.0, ring * 0.5)
                pb = mix(pb, 188.0, ring * 0.5)
                r = mix(r, pr, pa); g = mix(g, pg, pa); b = mix(b, pb, pa)

                # --- cast shadow of the berry on the plate
                bdx = (fx - 495.0) / 245.0
                bdy = (fy - 655.0) / 38.0
                bd = bdx * bdx + bdy * bdy
                if bd < 1.0:
                    a = 0.22 * (1.0 - bd)
                    r = mix(r, 150.0, a); g = mix(g, 110.0, a); b = mix(b, 100.0, a)

                # --- juice droplets (glossy, translucent red)
                for (dx0, dy0, drx, dry) in DROPS:
                    ddx = (fx - dx0) / drx
                    ddy = (fy - dy0) / dry
                    dd = ddx * ddx + ddy * ddy
                    if dd < 1.0:
                        a = 0.55 * (1.0 - dd * 0.4)
                        r = mix(r, 226.0, a); g = mix(g, 28.0, a); b = mix(b, 62.0, a)
                        # specular dot
                        sdx2 = (fx - dx0 + 3.0) / 3.5
                        sdy2 = (fy - dy0 + 2.0) / 2.5
                        if sdx2 * sdx2 + sdy2 * sdy2 < 1.0:
                            r = mix(r, 255.0, 0.85); g = mix(g, 255.0, 0.85)
                            b = mix(b, 255.0, 0.85)

            # --- strawberry body
            if BY0 - 4.0 <= fy <= BY1 + 4.0:
                t = (fy - BY0) / BH
                if 0.0 <= t <= 1.0:
                    cx = berry_cx(t)
                    hw = berry_hw(t)
                    dist = abs(fx - cx) - hw if hw >= 0.5 else 99.0
                    # curved crown: top edge dips down toward the shoulders
                    y_top = BY0 + 45.0 * min(1.0, ((fx - 480.0) / HW_TOP) ** 2)
                    if dist < 2.0 and fy >= y_top - 1.0:
                        aa = clamp(1.0 - dist / 2.0) * clamp(fy - y_top + 1.0)
                        nx = (fx - cx) / hw
                        ny = t
                        # vertical red gradient: bright top -> deep bottom
                        if ny < 0.45:
                            gt = ny / 0.45
                            br = mix(255.0, 232.0, gt)
                            bgc = mix(51.0, 8.0, gt)
                            bb = mix(102.0, 58.0, gt)
                        else:
                            gt = (ny - 0.45) / 0.55
                            br = mix(232.0, 198.0, gt)
                            bgc = mix(8.0, 0.0, gt)
                            bb = mix(58.0, 48.0, gt)
                        # 3D roundness: brighter upper-left, darker edges
                        roundness = 1.0 - 0.42 * (nx * nx) - 0.18 * ny * ny
                        light = 0.82 + 0.30 * (1.0 - nx * nx) * (1.0 - ny * 0.5)
                        # broad specular sheen, upper-left
                        sx2 = nx + 0.42
                        sy2 = ny - 0.26
                        sd2 = sx2 * sx2 * 2.6 + sy2 * sy2 * 5.0
                        spec = (1.0 - sd2) if sd2 < 1.0 else 0.0
                        spec = spec * spec
                        # small bright tip highlight near the bottom curve
                        tx2 = nx - 0.15
                        ty2 = ny - 0.82
                        td2 = tx2 * tx2 * 4.0 + ty2 * ty2 * 9.0
                        tspec = (1.0 - td2) if td2 < 1.0 else 0.0
                        tspec = tspec * tspec * 0.5
                        fr = br * roundness * light + 150.0 * spec + 90.0 * tspec
                        fg = bgc * roundness * light + 110.0 * spec + 60.0 * tspec
                        fb = bb * roundness * light + 130.0 * spec + 80.0 * tspec
                        # achenes + dimples
                        kind, d2 = seed_at(fx, fy)
                        if kind == 1:
                            # pale yellow-green seed, darker rim
                            edge = ss(0.55, 1.0, d2)
                            fr = mix(232.0, 188.0, edge)
                            fg = mix(220.0, 166.0, edge)
                            fb = mix(138.0, 92.0, edge)
                        elif kind == 2:
                            fr *= 0.78; fg *= 0.72; fb *= 0.72
                        # subtle procedural grain
                        grain = ((x * 7 + y * 13) % 5 - 2) * 1.2
                        fr += grain; fg += grain; fb += grain
                        r = mix(r, clamp(fr, 0.0, 255.0), aa)
                        g = mix(g, clamp(fg, 0.0, 255.0), aa)
                        b = mix(b, clamp(fb, 0.0, 255.0), aa)

            # --- calyx leaves + stem (over the berry crown)
            # stem
            if 205.0 <= fy <= 292.0:
                scx = 480.0 + 6.0 * math.sin((fy - 205.0) * 0.03)
                if abs(fx - scx) < 5.0:
                    a = clamp(1.0 - (abs(fx - scx) - 3.5) / 1.5)
                    r = mix(r, 96.0, a); g = mix(g, 124.0, a); b = mix(b, 62.0, a)
            # leaves
            lx = fx - LEAF_CX
            ly = fy - LEAF_CY
            ld = math.sqrt(lx * lx + ly * ly)
            if 4.0 < ld < 140.0:
                ang = math.atan2(ly, lx) + math.pi / 2.0  # 0 = pointing up
                # wrap angle to [-pi, pi]
                if ang > math.pi:
                    ang -= 2.0 * math.pi
                elif ang < -math.pi:
                    ang += 2.0 * math.pi
                for (la, llen) in LEAVES:
                    da = abs(ang - la)
                    if da < 0.42 and ld < llen:
                        # leaf width tapers to a point
                        along = ld / llen
                        halfw_leaf = 19.0 * (1.0 - along) * (0.55 + 0.45 * ss(0.0, 0.25, along))
                        perp = da * ld
                        if perp < halfw_leaf:
                            laa = clamp((halfw_leaf - perp) / 2.0 + 0.5)
                            # green gradient, darker at base
                            gr = mix(58.0, 34.0, along)
                            gg = mix(138.0, 96.0, along)
                            gb = mix(52.0, 30.0, along)
                            # centre vein
                            if perp < 1.6:
                                gr = mix(gr, 150.0, 0.55)
                                gg = mix(gg, 205.0, 0.55)
                                gb = mix(gb, 110.0, 0.55)
                            r = mix(r, gr, laa); g = mix(g, gg, laa); b = mix(b, gb, laa)
                            break

            o = row + x * 3
            img[o] = int(clamp(r, 0.0, 255.0))
            img[o + 1] = int(clamp(g, 0.0, 255.0))
            img[o + 2] = int(clamp(b, 0.0, 255.0))
    return img

# ------------------------------------------------------------------ PNG out
def write_png(img):
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += img[y * W * 3:(y + 1) * W * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(OUT, "wb") as f:
        f.write(png)
    return len(png)

if __name__ == "__main__":
    img = render()
    n = write_png(img)
    print(f"wrote {OUT}: {n} bytes, {W}x{H}")
