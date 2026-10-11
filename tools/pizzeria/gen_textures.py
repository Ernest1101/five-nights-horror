"""Realistic (grimy, worn) block textures + block/item models + blockstates for the pizzeria blocks.

    python tools/pizzeria/gen_textures.py

Textures are 64x64 (4x vanilla). Blocks with several texture variants get a blockstate that picks one at
random per position, so walls and floors do not repeat visibly. Must stay in sync with ModBlocks.java.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ASSETS = os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf")
TEX = os.path.join(ASSETS, "textures", "block")
S = 64
rng = np.random.default_rng(1987)


# ------------------------------------------------------------------ noise helpers

def vnoise(cells, size=S, stretch=(1, 1)):
    """Tileable value noise in [0, 1]; stretch=(sx, sy) makes streaks (cells per axis = cells*s)."""
    cx, cy = max(1, int(cells * stretch[0])), max(1, int(cells * stretch[1]))
    g = rng.random((cy, cx))
    ys = np.arange(size) / size * cy
    xs = np.arange(size) / size * cx
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    fy, fx = ys - y0, xs - x0
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    a = g[y0 % cy][:, x0 % cx]
    b = g[y0 % cy][:, (x0 + 1) % cx]
    c = g[(y0 + 1) % cy][:, x0 % cx]
    d = g[(y0 + 1) % cy][:, (x0 + 1) % cx]
    top = a + (b - a) * fx[None, :]
    bot = c + (d - c) * fx[None, :]
    return top + (bot - top) * fy[:, None]


def fbm(cells=4, octaves=4, stretch=(1, 1), size=S):
    out, amp, tot = np.zeros((size, size)), 1.0, 0.0
    for o in range(octaves):
        out += vnoise(cells * 2 ** o, size, stretch) * amp
        tot += amp
        amp *= 0.5
    return out / tot


def grain(amount):
    return 1 + (rng.random((S, S)) - 0.5) * amount


def rgb(c):
    return np.array(c, dtype=np.float64)


def canvas(c):
    return np.ones((S, S, 3)) * rgb(c)


def apply_dirt(img, strength=0.25, cells=3, tint=(70, 60, 45)):
    d = np.clip((fbm(cells, 5) - 0.42) * 3, 0, 1) * strength
    return img * (1 - d[..., None]) + rgb(tint) * d[..., None]


def drips(img, strength=0.3, tint=(60, 50, 35)):
    """Vertical grime streaks running down from the top (water / grease runs)."""
    n = fbm(6, 3, stretch=(2.5, 0.12))
    fall = np.linspace(1.0, 0.4, S)[:, None]
    d = np.clip((n - 0.5) * 3.2, 0, 1) * fall * strength
    return img * (1 - d[..., None]) + rgb(tint) * d[..., None]


def cracks(img, n=2, col=(40, 38, 35), alpha=0.7):
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    for _ in range(n):
        x, y = rng.uniform(0, S), rng.uniform(0, S)
        a = rng.uniform(0, 2 * math.pi)
        pts = [(x, y)]
        for _ in range(rng.integers(5, 14)):
            a += rng.normal(0, 0.6)
            x, y = x + math.cos(a) * 2.5, y + math.sin(a) * 2.5
            pts.append((x, y))
        dr.line(pts, fill=tuple(int(c) for c in col), width=1)
    out = np.asarray(im).astype(np.float64)
    return img * (1 - alpha) + out * alpha


def tiles(img, tile, grout, light=0.12, grout_w=1, colors=None, jitter=0.06):
    """Square tile grid: per-tile colour (optional checker), bevel highlight/shadow, grout lines."""
    out = img.copy()
    n = S // tile
    for ty in range(n):
        for tx in range(n):
            ys, xs = slice(ty * tile, (ty + 1) * tile), slice(tx * tile, (tx + 1) * tile)
            if colors is not None:
                out[ys, xs] = rgb(colors[(tx + ty) % len(colors)]) * (1 + rng.normal(0, jitter))
            else:
                out[ys, xs] *= 1 + rng.normal(0, jitter)
            out[ty * tile + grout_w, xs] *= 1 + light
            out[ys, tx * tile + grout_w] *= 1 + light
            out[(ty + 1) * tile - 1, xs] *= 1 - light
            out[ys, (tx + 1) * tile - 1] *= 1 - light
    for k in range(n):
        out[k * tile:k * tile + grout_w, :] = rgb(grout)
        out[:, k * tile:k * tile + grout_w] = rgb(grout)
    return out


def scuffs(img, n, col, alpha=0.35, length=(3, 9), mask=None):
    for _ in range(n):
        x, y = rng.integers(0, S), rng.integers(0, S)
        if mask is not None and not mask[y, x]:
            continue
        a = rng.uniform(0, math.pi)
        ln = rng.integers(*length)
        for k in range(ln):
            px, py = int(x + math.cos(a) * k) % S, int(y + math.sin(a) * k) % S
            img[py, px] = img[py, px] * (1 - alpha) + rgb(col) * alpha
    return img


def save(name, img, alpha=None):
    os.makedirs(TEX, exist_ok=True)
    arr = np.clip(img, 0, 255).astype(np.uint8)
    if alpha is not None:
        arr = np.dstack([arr, np.clip(alpha, 0, 255).astype(np.uint8)])
        Image.fromarray(arr, "RGBA").save(os.path.join(TEX, name + ".png"))
    else:
        Image.fromarray(arr, "RGB").save(os.path.join(TEX, name + ".png"))


# ------------------------------------------------------------------ textures

WHITE_TILE, BLACK_TILE = (212, 208, 196), (27, 27, 30)


def checker_floor(v):
    img = tiles(canvas((0, 0, 0)), 32, (78, 76, 72), 0.08, colors=[WHITE_TILE, BLACK_TILE], jitter=0.03)
    white = img.mean(axis=2) > 100
    img = scuffs(img, 40, (60, 55, 50), 0.4, mask=white)
    img = scuffs(img, 25, (90, 90, 92), 0.3, mask=~white)
    img = apply_dirt(img, 0.32, 2, (85, 72, 55))
    sheen = (fbm(2, 2) - 0.5) * 0.12
    img *= (1 + sheen)[..., None] * grain(0.06)[..., None]
    save(f"checker_floor_{v}", img)


def wall_checker(v):
    img = tiles(canvas((0, 0, 0)), 16, (70, 68, 64), 0.1, colors=[WHITE_TILE, BLACK_TILE], jitter=0.04)
    img = drips(img, 0.35, (70, 58, 40))
    img = apply_dirt(img, 0.22, 3)
    img = cracks(img, 1, (50, 48, 44), 0.5)
    img *= grain(0.07)[..., None]
    save(f"wall_checker_{v}", img)


def wall_red():
    img = canvas((148, 30, 26))
    for k in range(4):
        img[:, k * 16:(k + 1) * 16] *= 1 + rng.normal(0, 0.05)
    img[0:2] = rgb((70, 18, 14))
    img[S - 2:] = rgb((70, 18, 14))
    img[2] *= 1.25
    img[S - 3] *= 0.75
    for k in range(4):
        img[:, k * 16] = rgb((80, 30, 26))
    img[31:33] = rgb((85, 32, 28))
    img = drips(img, 0.3, (60, 30, 20))
    img = apply_dirt(img, 0.2)
    img *= grain(0.06)[..., None]
    save("wall_red", img)


def wall_base():
    img = tiles(canvas((44, 46, 52)), 32, (24, 24, 26), 0.08, jitter=0.04)
    img *= np.linspace(1.0, 0.7, S)[:, None, None]
    img = apply_dirt(img, 0.35, 3, (40, 34, 25))
    img = scuffs(img, 20, (90, 90, 95), 0.3)
    img *= grain(0.08)[..., None]
    save("wall_base", img)


def wall_plaster(v):
    img = canvas((116, 124, 128)) * (0.92 + 0.16 * fbm(3, 5))[..., None]
    img = drips(img, 0.45, (72, 66, 52))
    img = apply_dirt(img, 0.3, 2, (80, 75, 60))
    if v == 1:
        img = cracks(img, 3, (55, 55, 55), 0.8)
    if v == 2:   # peeling paint patch showing old cream paint underneath
        m = np.clip((fbm(3, 4) - 0.62) * 8, 0, 1)
        img = img * (1 - m[..., None]) + rgb((176, 166, 140)) * m[..., None]
    img *= grain(0.1)[..., None]
    save(f"wall_plaster_{v}", img)


def concrete_wall(v):
    img = canvas((104, 101, 96)) * (0.85 + 0.3 * fbm(4, 5))[..., None]
    pores = rng.random((S, S)) < 0.03
    img[pores] *= 0.6
    img = drips(img, 0.5, (50, 44, 34))
    img = cracks(img, 2 + v, (45, 43, 40), 0.8)
    img = apply_dirt(img, 0.3, 2, (60, 50, 35))
    img *= grain(0.12)[..., None]
    save(f"concrete_wall_{v}", img)


def ceiling_tile(v):
    img = canvas((186, 182, 170)) * (0.95 + 0.08 * fbm(4, 3))[..., None]
    # fissured acoustic pattern: short dark worms
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    for _ in range(140):
        x, y = rng.uniform(3, S - 3), rng.uniform(3, S - 3)
        a = rng.uniform(0, math.pi * 2)
        ln = rng.uniform(1, 3)
        dr.line([(x, y), (x + math.cos(a) * ln, y + math.sin(a) * ln)], fill=(128, 124, 114), width=1)
    img = np.asarray(im).astype(np.float64)
    if v >= 1:   # water stain ring
        cx, cy, r = rng.uniform(16, 48), rng.uniform(16, 48), rng.uniform(10, 20)
        yy, xx = np.mgrid[0:S, 0:S]
        d = np.hypot(xx - cx, yy - cy) / r
        stain = np.clip(1 - d, 0, 1) * 0.35 + np.exp(-((d - 1) * 9) ** 2) * 0.45
        stain *= 0.7 + 0.6 * fbm(4, 3)
        img = img * (1 - stain[..., None]) + rgb((140, 108, 60)) * stain[..., None]
    if v == 2:
        img = apply_dirt(img, 0.25, 3, (90, 85, 75))
    # T-bar grid frame
    img[0:2, :] = rgb((150, 150, 146))
    img[:, 0:2] = rgb((150, 150, 146))
    img[2, 2:] *= 0.8
    img[2:, 2] *= 0.8
    img *= grain(0.06)[..., None]
    save(f"ceiling_tile_{v}", img)


def ceiling_light(lit):
    img = canvas((160, 160, 156))
    yy, xx = np.mgrid[0:S, 0:S]
    inner = (xx >= 5) & (xx < S - 5) & (yy >= 5) & (yy < S - 5)
    if lit:
        tubes = np.exp(-((xx - 22) / 6.0) ** 2) + np.exp(-((xx - 42) / 6.0) ** 2)
        diff = rgb((236, 240, 236)) + tubes[..., None] * rgb((19, 15, 19))
    else:
        tubes = np.exp(-((xx - 22) / 4.0) ** 2) + np.exp(-((xx - 42) / 4.0) ** 2)
        diff = rgb((112, 116, 118)) - tubes[..., None] * rgb((30, 30, 30))
    prism = ((xx % 4 == 0) | (yy % 4 == 0)) & inner
    img[inner] = diff[inner]
    img[prism] *= 0.93 if lit else 0.85
    if not lit:   # dead bugs in the diffuser
        for _ in range(6):
            x, y = rng.integers(8, S - 8, 2)
            img[y:y + 2, x:x + 1] = rgb((30, 26, 20))
    img[4, 4:S - 4] = rgb((100, 100, 98))
    img[4:S - 4, 4] = rgb((100, 100, 98))
    img[0:2, :] = rgb((150, 150, 146))
    img[:, 0:2] = rgb((150, 150, 146))
    img *= grain(0.03)[..., None]
    save("ceiling_light_on" if lit else "ceiling_light", img)


def stage_planks(v):
    img = np.zeros((S, S, 3))
    for p in range(4):
        base = rgb((86, 56, 36)) * (1 + rng.normal(0, 0.08))
        g = fbm(2, 4, stretch=(0.25, 4))[p * 16:(p + 1) * 16]
        rings = 0.5 + 0.5 * np.sin(g * 40)
        img[p * 16:(p + 1) * 16] = base * (0.75 + 0.35 * rings)[..., None]
        off = rng.integers(0, S)
        img[p * 16:(p + 1) * 16, off] = rgb((30, 18, 10))
        for nx in (off + 3, (off + 61) % S):
            img[p * 16 + 4, nx % S] = rgb((40, 40, 42))
            img[p * 16 + 11, nx % S] = rgb((40, 40, 42))
        img[p * 16] = rgb((26, 16, 10))
        img[p * 16 + 1] *= 1.15
    worn = np.clip((fbm(2, 3) - 0.45) * 2.5, 0, 1) * 0.35
    img = img * (1 - worn[..., None]) + rgb((120, 92, 66)) * worn[..., None]
    img = scuffs(img, 30, (40, 26, 16), 0.4)
    img *= grain(0.08)[..., None]
    save(f"stage_planks_{v}", img)


def star(dr, cx, cy, r, col):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    dr.polygon(pts, fill=col)


def curtain(name, v, base, star_col, n_stars, fold=16, sheen=0.35):
    xx = np.arange(S)
    folds = 0.5 + 0.5 * np.sin((xx / fold + rng.uniform(0, 1)) * 2 * math.pi + 0.6 * np.sin(xx / 7.0))
    img = canvas(base) * (1 - sheen + sheen * 1.6 * folds)[None, :, None]
    img *= (0.9 + 0.2 * fbm(3, 3, stretch=(0.3, 2)))[..., None]
    if n_stars:
        big = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((S * 4, S * 4), Image.NEAREST)
        dr = ImageDraw.Draw(big)
        for _ in range(n_stars):
            cx, cy = rng.uniform(20, S * 4 - 20), rng.uniform(20, S * 4 - 20)
            star(dr, cx, cy, rng.uniform(10, 18), star_col)
        for _ in range(30):
            cx, cy = rng.uniform(0, S * 4), rng.uniform(0, S * 4)
            dr.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=star_col)
        img = np.asarray(big.resize((S, S), Image.LANCZOS)).astype(np.float64)
        img *= (1 - sheen + sheen * 1.6 * folds)[None, :, None] * 0.5 + 0.5
    img = apply_dirt(img, 0.15, 3, (20, 18, 16))
    img *= grain(0.08)[..., None]
    save(f"{name}_{v}" if v is not None else name, img)


def bath_tile(v):
    img = tiles(canvas((222, 224, 220)), 8, (150, 148, 140), 0.06, jitter=0.025)
    img = drips(img, 0.25, (120, 110, 80))
    img *= np.linspace(1.0, 0.85, S)[:, None, None]
    img = apply_dirt(img, 0.2, 3, (120, 110, 80))
    if v == 1:
        img = cracks(img, 2, (90, 88, 80), 0.8)
    img *= grain(0.05)[..., None]
    save(f"bath_tile_{v}", img)


def kitchen_tile(v):
    img = tiles(canvas((150, 72, 52)), 16, (60, 50, 44), 0.08, jitter=0.07)
    img = apply_dirt(img, 0.4, 3, (50, 40, 28))
    grease = np.clip((fbm(4, 4) - 0.6) * 4, 0, 1) * 0.3
    img = img * (1 - grease[..., None]) + rgb((40, 30, 15)) * grease[..., None]
    img *= grain(0.1)[..., None]
    save(f"kitchen_tile_{v}", img)


def dark_tile():
    img = tiles(canvas((54, 54, 58)), 32, (30, 30, 32), 0.1, jitter=0.05)
    img = apply_dirt(img, 0.4, 2, (35, 30, 22))
    img = scuffs(img, 30, (85, 85, 88), 0.3)
    img = cracks(img, 2, (25, 25, 26), 0.8)
    img *= grain(0.1)[..., None]
    save("dark_tile", img)


def tablecloth():
    xx = np.arange(S)
    top = canvas((234, 231, 222)) * (0.95 + 0.07 * fbm(3, 3))[..., None]
    for _ in range(4):   # sauce + soda stains
        cx, cy, r = rng.uniform(6, 58, 2).tolist() + [rng.uniform(2, 5)]
        yy, xg = np.mgrid[0:S, 0:S]
        d = np.hypot(xg - cx, yy - cy) / r
        col = rgb((170, 40, 25)) if rng.random() < 0.5 else rgb((120, 80, 40))
        ring = np.clip(1 - d, 0, 1) * 0.5 + np.exp(-((d - 1) * 4) ** 2) * 0.35
        top = top * (1 - ring[..., None]) + col * ring[..., None]
    top[0:3, :] *= 0.85
    top[:, 0:3] *= 0.9
    top *= grain(0.04)[..., None]
    save("tablecloth_top", top)
    folds = 0.5 + 0.5 * np.sin(xx / 9.0 * 2 * math.pi + 0.8 * np.sin(xx / 5.0))
    side = canvas((226, 222, 212)) * (0.8 + 0.25 * folds)[None, :, None]
    side[0:4] *= 1.05
    side[S - 4:] *= 0.8
    side = drips(side, 0.15, (150, 130, 100))
    side *= grain(0.04)[..., None]
    save("tablecloth_side", side)


def party_hat(v):
    cols = [((220, 40, 40), (250, 220, 60)), ((40, 110, 220), (250, 250, 250)), ((150, 50, 200), (90, 220, 120))][v]
    img = canvas(cols[0])
    yy, xx = np.mgrid[0:S, 0:S]
    stripes = ((xx + yy) // 8) % 2 == 0
    img[stripes] = rgb(cols[1])
    dots = ((xx % 12 - 6) ** 2 + (yy % 12 - 6) ** 2) < 5
    img[dots & ~stripes] = rgb((255, 255, 255))
    img *= (0.9 + 0.15 * fbm(3, 2))[..., None] * grain(0.06)[..., None]
    img[48:, :] = rgb((250, 250, 245)) * (0.9 + 0.2 * rng.random((16, S, 1)))   # pom-pom
    save(f"party_hat_{v}", img)


def confetti(v):
    rgba = np.zeros((S, S, 4))
    im = Image.fromarray(rgba.astype(np.uint8), "RGBA")
    dr = ImageDraw.Draw(im)
    cols = [(230, 50, 50), (250, 210, 40), (50, 130, 240), (80, 200, 90), (220, 70, 210), (250, 250, 250)]
    for _ in range(26):
        x, y = rng.uniform(1, S - 3, 2)
        c = cols[rng.integers(len(cols))]
        w, h = (2, 1) if rng.random() < 0.5 else (1, 2)
        dr.rectangle([x, y, x + w, y + h], fill=(*c, 255))
    if v == 2:   # crumpled napkin + paper cup lying on the floor
        dr.polygon([(36, 34), (48, 30), (54, 40), (44, 48), (34, 44)], fill=(236, 234, 226, 255), outline=(170, 168, 160, 255))
        dr.rectangle([12, 14, 24, 21], fill=(210, 40, 40, 255))
        dr.rectangle([12, 14, 14, 21], fill=(240, 240, 240, 255))
    if v == 1:   # dried soda puddle
        dr.ellipse([20, 30, 44, 46], fill=(70, 40, 20, 110))
    im.save(os.path.join(TEX, f"confetti_{v}.png"))


def balloon(v):
    col = [(215, 30, 35), (40, 90, 220), (240, 200, 30)][v]
    yy, xx = np.mgrid[0:S, 0:S]
    img = canvas(col) * (0.75 + 0.35 * np.clip(1 - np.hypot(xx - 22, yy - 20) / 40, 0, 1))[..., None]
    spec = np.exp(-(((xx - 20) / 5.0) ** 2 + ((yy - 16) / 7.0) ** 2))
    img = img * (1 - spec[..., None] * 0.7) + 255 * spec[..., None] * 0.7
    img[56:, :] = rgb(col) * 0.6                      # knot / string area of the atlas
    img[60:, 0:8] = rgb((200, 200, 200))
    save(f"balloon_{v}", img)


def font(size):
    for n in ("impact.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", n), size)
        except OSError:
            pass
    return ImageFont.load_default()


def monitor():
    case = canvas((168, 162, 146)) * (0.9 + 0.15 * fbm(3, 3))[..., None]
    case = apply_dirt(case, 0.25, 3, (100, 90, 70))
    case *= grain(0.06)[..., None]
    save("crt_case", case)
    scr = np.zeros((S, S, 3))
    yy, xx = np.mgrid[0:S, 0:S]
    noise = rng.random((S, S))
    scr[:] = (noise[..., None] * 60 + 20) * rgb((0.55, 0.75, 0.6))
    scr[yy % 2 == 0] *= 0.6
    vig = 1 - (((xx - 32) / 40) ** 2 + ((yy - 32) / 40) ** 2)
    scr *= np.clip(vig, 0.3, 1)[..., None]
    im = Image.fromarray(np.clip(scr, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, S - 1, S - 1], outline=(40, 40, 38), width=4)
    dr.text((10, 8), "CAM 1A", font=font(10), fill=(220, 230, 220))
    dr.ellipse([50, 8, 55, 13], fill=(220, 30, 30))
    im.save(os.path.join(TEX, "crt_screen.png"))


def arcade():
    def side(top):
        img = canvas((40, 22, 70)) * np.linspace(1.1, 0.7, S)[:, None, None]
        im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        dr = ImageDraw.Draw(im)
        for _ in range(5):
            star(dr, rng.uniform(6, 58), rng.uniform(6, 58), rng.uniform(3, 6), (250, 210, 60))
        if top:
            dr.text((32, 34), "FAZ", font=font(18), fill=(250, 200, 40), anchor="mm")
        img = np.asarray(im).astype(np.float64)
        img = apply_dirt(img, 0.2, 3, (20, 15, 10))
        img *= grain(0.06)[..., None]
        return img

    save("arcade_side_lower", side(False))
    save("arcade_side_upper", side(True))
    front = canvas((26, 24, 30)) * grain(0.08)[..., None]
    front[24:44, 22:42] = rgb((60, 60, 64))
    front[30:38, 30:34] = rgb((200, 160, 40))
    front[27:30, 25:39] = rgb((120, 30, 30))
    save("arcade_front", front)
    im = Image.new("RGB", (S, S), (6, 8, 16))
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, S - 1, S - 1], outline=(30, 30, 36), width=5)
    for i in range(8):
        dr.rectangle([10 + i * 6, 14, 13 + i * 6, 16], fill=(250, 220, 40))
    for ex in (11, 20):   # little pixel bear (the player)
        dr.ellipse([ex, 32, ex + 4, 36], fill=(150, 90, 40))
    dr.ellipse([12, 34, 23, 45], fill=(150, 90, 40))
    dr.rectangle([15, 38, 16, 39], fill=(250, 250, 250))
    dr.rectangle([19, 38, 20, 39], fill=(250, 250, 250))
    for i, c in enumerate([(230, 40, 40), (60, 140, 250), (250, 150, 200)]):
        dr.rectangle([34 + i * 9, 34, 40 + i * 9, 42], fill=c)
    dr.text((32, 52), "1UP 004200", font=font(8), fill=(240, 240, 240), anchor="mm")
    im.save(os.path.join(TEX, "arcade_screen.png"))
    mq = Image.new("RGB", (S, S), (240, 190, 30))
    dr = ImageDraw.Draw(mq)
    dr.rectangle([0, 0, S - 1, S - 1], outline=(140, 40, 20), width=3)
    dr.text((32, 32), "FREDDY'S", font=font(13), fill=(140, 30, 20), anchor="mm")
    mq.save(os.path.join(TEX, "arcade_marquee.png"))
    panel = canvas((30, 30, 36)) * grain(0.08)[..., None]
    for (x, y, c) in ((14, 30, (220, 30, 30)), (40, 26, (40, 120, 230)), (50, 34, (240, 200, 40))):
        panel[y - 3:y + 3, x - 3:x + 3] = rgb(c)
    save("arcade_panel", panel)


# ------------------------------------------------------------------ models / blockstates

def write_json(rel, data):
    path = os.path.join(ASSETS, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=1)


def cube_block(name, textures, item_tex=None):
    """Random-variant full cube: textures is a list of texture names, each gets a cube_all model."""
    variants = []
    for t in textures:
        write_json(f"models/block/{t}.json", {"parent": "minecraft:block/cube_all", "textures": {"all": f"fnaf:block/{t}"}})
        variants.append({"model": f"fnaf:block/{t}"})
    write_json(f"blockstates/{name}.json", {"variants": {"": variants if len(variants) > 1 else variants[0]}})
    write_json(f"models/item/{name}.json", {"parent": f"fnaf:block/{item_tex or textures[0]}"})


def main():
    for v in range(3):
        checker_floor(v)
        wall_plaster(v)
        concrete_wall(v)
        ceiling_tile(v)
        curtain("star_curtain", v, (16, 16, 26), (245, 205, 60), 3)
        curtain("cove_curtain", v, (84, 30, 118), (225, 225, 235), 3)
        party_hat(v)
        confetti(v)
        balloon(v)
    for v in range(2):
        wall_checker(v)
        stage_planks(v)
        bath_tile(v)
        kitchen_tile(v)
    curtain("red_curtain", None, (138, 16, 22), None, 0, fold=11, sheen=0.5)
    wall_red()
    wall_base()
    dark_tile()
    ceiling_light(True)
    ceiling_light(False)
    tablecloth()
    monitor()
    arcade()

    cube_block("checker_floor", [f"checker_floor_{v}" for v in range(3)])
    cube_block("wall_checker", [f"wall_checker_{v}" for v in range(2)])
    cube_block("wall_plaster", [f"wall_plaster_{v}" for v in range(3)])
    cube_block("concrete_wall", [f"concrete_wall_{v}" for v in range(3)])
    cube_block("ceiling_tile", ["ceiling_tile_0", "ceiling_tile_0", "ceiling_tile_1", "ceiling_tile_2"])
    cube_block("stage_planks", [f"stage_planks_{v}" for v in range(2)])
    cube_block("star_curtain", [f"star_curtain_{v}" for v in range(3)])
    cube_block("cove_curtain", [f"cove_curtain_{v}" for v in range(3)])
    cube_block("bath_tile", [f"bath_tile_{v}" for v in range(2)])
    cube_block("kitchen_tile", [f"kitchen_tile_{v}" for v in range(2)])
    for n in ("red_curtain", "wall_red", "wall_base", "dark_tile"):
        cube_block(n, [n])

    # ceiling light: lit / unlit
    write_json("models/block/ceiling_light.json", {"parent": "minecraft:block/cube_all", "textures": {"all": "fnaf:block/ceiling_light"}})
    write_json("models/block/ceiling_light_on.json", {"parent": "minecraft:block/cube_all", "textures": {"all": "fnaf:block/ceiling_light_on"}})
    write_json("blockstates/ceiling_light.json", {"variants": {"lit=false": {"model": "fnaf:block/ceiling_light"},
                                                              "lit=true": {"model": "fnaf:block/ceiling_light_on"}}})
    write_json("models/item/ceiling_light.json", {"parent": "fnaf:block/ceiling_light_on"})

    # party table: tablecloth top, draped sides
    write_json("models/block/party_table.json", {"parent": "minecraft:block/cube_bottom_top", "textures": {
        "top": "fnaf:block/tablecloth_top", "bottom": "fnaf:block/dark_tile", "side": "fnaf:block/tablecloth_side"}})
    write_json("blockstates/party_table.json", {"variants": {"": {"model": "fnaf:block/party_table"}}})
    write_json("models/item/party_table.json", {"parent": "fnaf:block/party_table"})

    # party hat: stacked cubes approximating a cone
    hat_variants = []
    for v in range(3):
        els = []
        for i, (r, h) in enumerate(((3.0, 2), (2.4, 2), (1.8, 2), (1.2, 2), (0.7, 2))):
            y = i * 2
            els.append({"from": [8 - r, y, 8 - r], "to": [8 + r, y + h, 8 + r],
                        "faces": {f: {"uv": [0, y * 2, 16, y * 2 + 4], "texture": "#hat"} for f in ("north", "south", "east", "west", "up")}})
        els.append({"from": [7, 10, 7], "to": [9, 12, 9], "faces": {f: {"uv": [0, 12, 4, 16], "texture": "#hat"} for f in
                                                                     ("north", "south", "east", "west", "up")}})
        write_json(f"models/block/party_hat_{v}.json", {"parent": "minecraft:block/block", "ambientocclusion": False,
                                                         "textures": {"hat": f"fnaf:block/party_hat_{v}", "particle": f"fnaf:block/party_hat_{v}"},
                                                         "elements": els})
        for rot in (0, 90):
            hat_variants.append({"model": f"fnaf:block/party_hat_{v}", "y": rot})
    write_json("blockstates/party_hat.json", {"variants": {"": hat_variants}})
    write_json("models/item/party_hat.json", {"parent": "fnaf:block/party_hat_0"})

    # balloon floating over the table, tied with a string
    bal = []
    for v in range(3):
        body = {f: {"uv": [0, 0, 16, 14], "texture": "#b"} for f in ("north", "south", "east", "west")}
        body["up"] = {"uv": [2, 2, 14, 14], "texture": "#b"}
        body["down"] = {"uv": [2, 2, 14, 14], "texture": "#b"}
        string = {f: {"uv": [0, 15, 2, 16], "texture": "#b"} for f in ("north", "south", "east", "west")}
        write_json(f"models/block/balloon_{v}.json", {"parent": "minecraft:block/block", "ambientocclusion": False,
                                                       "textures": {"b": f"fnaf:block/balloon_{v}", "particle": f"fnaf:block/balloon_{v}"},
                                                       "elements": [
                                                           {"from": [3.5, 20, 3.5], "to": [12.5, 31, 12.5], "faces": body},
                                                           {"from": [5, 18, 5], "to": [11, 20, 11], "faces": body},
                                                           {"from": [7, 16.5, 7], "to": [9, 18, 9], "faces": body},
                                                           {"from": [7.75, 0, 7.75], "to": [8.25, 16.5, 8.25], "faces": string}]})
        for rot in (0, 45):
            bal.append({"model": f"fnaf:block/balloon_{v}", "y": 0 if rot == 0 else 90})
    write_json("blockstates/balloon.json", {"variants": {"": bal}})
    write_json("models/item/balloon.json", {"parent": "fnaf:block/balloon_0",
                                            "display": {"gui": {"rotation": [30, 225, 0], "translation": [0, -4, 0], "scale": [0.45, 0.45, 0.45]}}})

    # confetti / litter decal on the floor
    conf = []
    for v in range(3):
        write_json(f"models/block/confetti_{v}.json", {"parent": "minecraft:block/thin_block", "ambientocclusion": False,
                                                        "textures": {"all": f"fnaf:block/confetti_{v}", "particle": f"fnaf:block/confetti_{v}"},
                                                        "elements": [{"from": [0, 0, 0], "to": [16, 0.25, 16],
                                                                      "faces": {"up": {"uv": [0, 0, 16, 16], "texture": "#all"}}}]})
        for rot in (0, 90, 180, 270):
            conf.append({"model": f"fnaf:block/confetti_{v}", "y": rot})
    write_json("blockstates/confetti.json", {"variants": {"": conf}})
    write_json("models/item/confetti.json", {"parent": "minecraft:item/generated", "textures": {"layer0": "fnaf:block/confetti_2"}})

    # CRT security monitor (faces south by default; screen on the north face of the model rotated to facing)
    crt = {"parent": "minecraft:block/block", "textures": {"case": "fnaf:block/crt_case", "screen": "fnaf:block/crt_screen",
                                                          "particle": "fnaf:block/crt_case"},
           "elements": [
               {"from": [2, 0, 3], "to": [14, 11, 12], "faces": {
                   "north": {"uv": [0, 0, 12, 11], "texture": "#case"}, "east": {"uv": [0, 0, 9, 11], "texture": "#case"},
                   "west": {"uv": [0, 0, 9, 11], "texture": "#case"}, "up": {"uv": [2, 3, 14, 12], "texture": "#case"},
                   "down": {"uv": [2, 3, 14, 12], "texture": "#case"},
                   "south": {"uv": [0, 0, 16, 16], "texture": "#screen"}}},
               {"from": [4, 1, 0.5], "to": [12, 9, 3], "faces": {
                   "north": {"uv": [4, 4, 12, 12], "texture": "#case"}, "east": {"uv": [0, 0, 3, 8], "texture": "#case"},
                   "west": {"uv": [0, 0, 3, 8], "texture": "#case"}, "up": {"uv": [0, 0, 8, 3], "texture": "#case"},
                   "down": {"uv": [0, 0, 8, 3], "texture": "#case"}}}]}
    write_json("models/block/crt_monitor.json", crt)
    write_json("blockstates/crt_monitor.json", {"variants": {f"facing={f}": {"model": "fnaf:block/crt_monitor", "y": y}
                                                             for f, y in (("south", 0), ("west", 90), ("north", 180), ("east", 270))}})
    write_json("models/item/crt_monitor.json", {"parent": "fnaf:block/crt_monitor"})

    # arcade cabinet, 2 blocks tall
    def faces(tex_side, tex_front, back="#lower"):
        return {"north": {"uv": [0, 0, 16, 16], "texture": back}, "south": {"uv": [0, 0, 16, 16], "texture": tex_front},
                "east": {"uv": [0, 0, 16, 16], "texture": tex_side}, "west": {"uv": [0, 0, 16, 16], "texture": tex_side},
                "up": {"uv": [0, 0, 16, 16], "texture": "#panel"}, "down": {"uv": [0, 0, 16, 16], "texture": back}}

    arc = {"parent": "minecraft:block/block", "textures": {
        "lower": "fnaf:block/arcade_side_lower", "upper": "fnaf:block/arcade_side_upper", "front": "fnaf:block/arcade_front",
        "screen": "fnaf:block/arcade_screen", "marquee": "fnaf:block/arcade_marquee", "panel": "fnaf:block/arcade_panel",
        "particle": "fnaf:block/arcade_side_lower"},
        "elements": [
            {"from": [1, 0, 1], "to": [15, 15, 13], "faces": faces("#lower", "#front")},
            {"from": [1, 15, 1], "to": [15, 17, 15], "faces": faces("#lower", "#panel")},
            {"from": [1, 17, 1], "to": [15, 28, 11], "faces": faces("#upper", "#screen")},
            {"from": [1, 28, 1], "to": [15, 32, 13], "faces": faces("#upper", "#marquee")}]}
    write_json("models/block/arcade.json", arc)
    write_json("blockstates/arcade.json", {"variants": {f"facing={f}": {"model": "fnaf:block/arcade", "y": y}
                                                        for f, y in (("south", 0), ("west", 90), ("north", 180), ("east", 270))}})
    write_json("models/item/arcade.json", {"parent": "fnaf:block/arcade",
                                           "display": {"gui": {"rotation": [30, 225, 0], "translation": [0, -3, 0], "scale": [0.42, 0.42, 0.42]}}})

    # mesh props: invisible block model (drawn by a block entity renderer), particle only
    for n, p in (("generator", "fnaf:block/concrete_wall_0"), ("desk_fan", "fnaf:block/crt_case")):
        write_json(f"models/block/{n}.json", {"textures": {"particle": p}})
        write_json(f"blockstates/{n}.json", {"variants": {"": {"model": f"fnaf:block/{n}"}}})
    print("ok")


if __name__ == "__main__":
    main()
