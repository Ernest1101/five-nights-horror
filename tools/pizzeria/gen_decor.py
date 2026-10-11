"""Furniture and fittings for the pizzeria, so the whole map uses the mod's own textures and models
(no vanilla barrels, stairs-as-chairs, cauldrons, levers ...). Writes textures, block models,
blockstates and item models. Run after gen_textures.py:

    python tools/pizzeria/gen_decor.py

Must stay in sync with ModBlocks.java. Model convention: the front of a facing block points south
(+Z) and blockstates rotate it with y = 0/90/180/270 for south/west/north/east.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

import gen_textures as gt
from gen_textures import S, apply_dirt, canvas, cracks, drips, fbm, font, grain, rgb, rng, scuffs, star, tiles, write_json

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = gt.TEX
FACINGS = (("south", 0), ("west", 90), ("north", 180), ("east", 270))


def save(name, img):
    gt.save(name, img)


def save_rgba(name, im):
    os.makedirs(TEX, exist_ok=True)
    im.save(os.path.join(TEX, name + ".png"))


def pil(img):
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def arr(im):
    return np.asarray(im.convert("RGB")).astype(np.float64)


def metal(base, scratch=40, dirt=0.25, brushed=True):
    img = canvas(base)
    if brushed:
        img *= (0.9 + 0.2 * fbm(4, 3, stretch=(6, 0.2)))[..., None]
    img = scuffs(img, scratch, tuple(min(255, c + 50) for c in base), 0.35)
    img = apply_dirt(img, dirt, 3, (50, 45, 35))
    return img * grain(0.05)[..., None]


def plastic(base, dirt=0.2):
    yy, xx = np.mgrid[0:S, 0:S]
    img = canvas(base) * (0.92 + 0.12 * np.clip(1 - np.hypot(xx - 20, yy - 18) / 60, 0, 1))[..., None]
    img = scuffs(img, 15, tuple(c * 0.7 for c in base), 0.3)
    img = apply_dirt(img, dirt, 3, (70, 60, 45))
    return img * grain(0.04)[..., None]


def porcelain():
    img = plastic((228, 228, 222), 0.18)
    img = drips(img, 0.15, (150, 130, 80))
    return img


def wood(base=(92, 60, 38), planks=4, vertical=False):
    g = fbm(2, 4, stretch=(0.25, 4)) if not vertical else fbm(2, 4, stretch=(4, 0.25))
    img = canvas(base) * (0.75 + 0.35 * (0.5 + 0.5 * np.sin(g * 40)))[..., None]
    for k in range(1, planks):
        if vertical:
            img[:, k * S // planks] *= 0.55
        else:
            img[k * S // planks] *= 0.55
    img = scuffs(img, 20, (40, 26, 16), 0.3)
    return img * grain(0.06)[..., None]


# ------------------------------------------------------------------ textures

def textures():
    save("chair_metal", metal((62, 62, 66)))
    save("chair_seat", plastic((176, 32, 30)))
    save("porcelain", porcelain())
    save("chrome", metal((178, 180, 184), 25, 0.15))
    save("steel", metal((140, 142, 144), 30, 0.3))
    save("black_plastic", plastic((30, 30, 32), 0.15))
    save("leather", plastic((26, 24, 24), 0.1) * (0.9 + 0.2 * fbm(8, 2))[..., None])

    # plates with food (cutout, round)
    for v in range(3):
        im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([2, 2, 61, 61], fill=(236, 234, 228, 255), outline=(190, 186, 176, 255), width=3)
        d.ellipse([12, 12, 51, 51], outline=(210, 206, 198, 255), width=1)
        if v == 0:   # pizza slice
            d.polygon([(18, 46), (46, 40), (30, 14)], fill=(214, 150, 60, 255))
            d.polygon([(21, 43), (43, 38), (30, 18)], fill=(246, 200, 80, 255))
            for (x, y) in ((28, 30), (34, 36), (26, 38), (31, 24)):
                d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(170, 40, 30, 255))
        elif v == 1:   # crumbs + sauce smear
            d.arc([16, 18, 48, 44], 200, 320, fill=(160, 40, 25, 255), width=4)
            for _ in range(25):
                x, y = rng.uniform(16, 48, 2)
                d.point((x, y), fill=(200, 150, 70, 255))
        else:   # birthday cake piece
            d.polygon([(20, 40), (44, 40), (40, 22), (24, 22)], fill=(250, 240, 230, 255))
            d.rectangle([22, 30, 42, 33], fill=(240, 120, 170, 255))
            d.ellipse([29, 20, 35, 26], fill=(220, 40, 60, 255))
        save_rgba(f"plate_{v}", im)

    cup = canvas((230, 230, 225))
    cup[:, ::16] = rgb((200, 30, 30))
    for k in range(4):
        cup[:, k * 16:k * 16 + 6] = rgb((200, 30, 30))
    im = pil(cup)
    ImageDraw.Draw(im).text((32, 34), "FAZ", font=font(14), fill=(250, 220, 40), anchor="mm")
    save("soda_cup", arr(im) * grain(0.04)[..., None])
    top = Image.new("RGB", (S, S), (240, 240, 236))
    ImageDraw.Draw(top).ellipse([26, 26, 38, 38], fill=(200, 30, 30))
    save("soda_top", arr(top))

    # paper streamers (cross model, cutout)
    for v in range(3):
        im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        cols = [(230, 50, 50), (250, 210, 40), (60, 130, 240), (90, 200, 90), (220, 80, 210)]
        d.line([(0, 3), (16, 7), (32, 4), (48, 8), (63, 3)], fill=(200, 200, 200, 255), width=1)
        for k in range(8):
            x = 4 + k * 8
            y = 4 + int(2 * math.sin(k))
            c = cols[(k + v) % len(cols)]
            ln = int(rng.uniform(16, 52))
            pts = [(x, y)]
            for j in range(1, ln, 4):
                pts.append((x + 2 * math.sin(j * 0.5 + k), y + j))
            d.line(pts, fill=(*c, 255), width=3)
        save_rgba(f"streamer_{v}", im)

    # cobweb
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = 6, 6
    for k in range(9):
        a = k * math.pi / 16
        d.line([(cx, cy), (cx + 70 * math.cos(a), cy + 70 * math.sin(a))], fill=(225, 225, 225, 200), width=1)
    for r in range(8, 70, 8):
        pts = [(cx + r * math.cos(a) * (1 + 0.08 * math.sin(a * 7)), cy + r * math.sin(a)) for a in np.linspace(0, math.pi / 2, 12)]
        d.line(pts, fill=(215, 215, 215, 170), width=1)
    save_rgba("cobweb", im)

    # dirty window glass (translucent) and mirror
    a = np.full((S, S), 70.0)
    a += (fbm(4, 4) - 0.5) * 80 + drips(np.zeros((S, S, 3)) + 100, 0.6)[..., 0] * 0.0
    g = canvas((170, 190, 195)) * (0.8 + 0.3 * fbm(3, 3))[..., None]
    a[:3, :] = a[-3:, :] = 255
    a[:, :3] = a[:, -3:] = 255
    g[:3, :] = g[-3:, :] = g[:, :3] = g[:, -3:] = rgb((60, 62, 66))
    gt.save("window_glass", g, np.clip(a, 40, 255))
    mir = canvas((200, 206, 210)) * (0.75 + 0.35 * np.linspace(1, 0.5, S)[None, :, None])
    mir = apply_dirt(mir, 0.25, 3, (110, 100, 80))
    mir = cracks(mir, 2, (90, 90, 95), 0.7)
    mir[:2, :] = mir[-2:, :] = mir[:, :2] = mir[:, -2:] = rgb((150, 150, 150))
    save("mirror", mir)

    sign = pil(canvas((238, 236, 226)) * grain(0.05)[..., None])
    d = ImageDraw.Draw(sign)
    d.text((32, 18), "SORRY!", font=font(16), fill=(30, 30, 30), anchor="mm")
    d.text((32, 38), "OUT OF", font=font(11), fill=(30, 30, 30), anchor="mm")
    d.text((32, 50), "ORDER", font=font(11), fill=(30, 30, 30), anchor="mm")
    d.rectangle([0, 0, S - 1, S - 1], outline=(180, 176, 160), width=2)
    save("sign_out_of_order", arr(sign))

    # cardboard boxes
    for v, text in enumerate(("", "PARTY SUPPLIES", "FRAGILE")):
        box = canvas((170, 128, 82)) * (0.9 + 0.15 * fbm(5, 3))[..., None]
        box[:, 28:36] = rgb((196, 170, 120))
        im = pil(box)
        if text:
            ImageDraw.Draw(im).text((32, 46), text, font=font(9 if len(text) > 8 else 12), fill=(60, 30, 20), anchor="mm")
        save(f"box_side_{v}", apply_dirt(arr(im), 0.2, 3) * grain(0.05)[..., None])
    top = canvas((176, 134, 88))
    top[:, 29:35] = rgb((196, 170, 120))
    top[31:33, :] = rgb((120, 86, 50))
    save("box_top", top * grain(0.05)[..., None])

    soup = canvas((90, 40, 20)) * (0.8 + 0.3 * fbm(4, 3))[..., None]
    save("soup", soup)
    save("bucket_yellow", plastic((230, 190, 30), 0.35))
    mop = canvas((200, 196, 180)) * (0.7 + 0.3 * fbm(2, 2, stretch=(8, 0.2)))[..., None]
    save("mop", apply_dirt(mop, 0.4, 3, (90, 80, 60)))
    save("wood_handle", wood((150, 110, 70), 1, True))

    can = plastic((96, 100, 104), 0.35)
    can[:, ::8] *= 0.8
    im = pil(can)
    ImageDraw.Draw(im).text((32, 30), "FAZBEAR", font=font(10), fill=(220, 200, 60), anchor="mm")
    save("trash_side", arr(im))
    trash = canvas((60, 62, 60))
    im = pil(trash)
    d = ImageDraw.Draw(im)
    for _ in range(14):
        x, y = rng.uniform(4, 56, 2)
        c = [(230, 230, 220), (200, 40, 40), (240, 200, 60), (120, 80, 40)][rng.integers(4)]
        d.polygon([(x, y), (x + rng.uniform(4, 10), y + rng.uniform(-3, 3)), (x + rng.uniform(2, 8), y + rng.uniform(4, 9))], fill=c)
    save("trash_top", arr(im))

    shelf = metal((112, 116, 120), 20, 0.35)
    shelf[::8, ::8] *= 0.5
    save("shelf_metal", shelf)
    items = canvas((40, 40, 44))
    im = pil(items)
    d = ImageDraw.Draw(im)
    x = 0
    while x < S:
        w = int(rng.uniform(6, 14))
        h = int(rng.uniform(20, 56))
        c = [(200, 40, 40), (40, 110, 220), (240, 220, 200), (240, 190, 40), (90, 160, 90), (160, 120, 80)][rng.integers(6)]
        d.rectangle([x, S - h, x + w - 1, S - 1], fill=c, outline=tuple(int(k * 0.6) for k in c))
        if rng.random() < 0.5:
            d.rectangle([x + 2, S - h + 6, x + w - 3, S - h + 12], fill=(240, 240, 240))
        x += w + 1
    save("shelf_items", arr(im) * grain(0.05)[..., None])

    bench = wood((120, 86, 56), 3)
    im = pil(bench)
    d = ImageDraw.Draw(im)
    d.line([(8, 10), (26, 24)], fill=(160, 160, 165), width=3)          # wrench
    d.ellipse([4, 6, 12, 14], outline=(160, 160, 165), width=2)
    d.line([(36, 40), (58, 52)], fill=(200, 40, 30), width=2)            # wires
    d.line([(36, 44), (56, 58)], fill=(40, 90, 200), width=2)
    for _ in range(10):
        x, y = rng.uniform(30, 60), rng.uniform(4, 30)
        d.ellipse([x, y, x + 2, y + 2], fill=(150, 150, 150))
    d.ellipse([10, 40, 22, 52], fill=(240, 240, 240))                     # a loose eyeball
    d.ellipse([14, 44, 18, 48], fill=(40, 90, 200))
    save("workbench_top", arr(im))

    save("desk_top", apply_dirt(wood((72, 52, 40), 2), 0.25, 3))
    save("desk_front", wood((64, 46, 34), 1, True))

    wrap = canvas((240, 140, 180))
    for k in range(0, S, 8):
        wrap[:, k:k + 4] = rgb((250, 190, 215))
    save("cupcake_wrapper", wrap * grain(0.04)[..., None])
    frost = canvas((246, 160, 200)) * (0.9 + 0.15 * fbm(4, 2))[..., None]
    im = pil(frost)
    d = ImageDraw.Draw(im)
    for _ in range(20):
        x, y = rng.uniform(2, 60, 2)
        d.rectangle([x, y, x + 2, y + 1], fill=[(250, 250, 250), (90, 200, 240), (250, 220, 40)][rng.integers(3)])
    save("cupcake_frosting", arr(im))
    face = arr(im).copy()
    im = pil(face)
    d = ImageDraw.Draw(im)
    for ex in (16, 40):
        d.ellipse([ex, 18, ex + 10, 34], fill=(250, 250, 250), outline=(30, 30, 30))
        d.ellipse([ex + 3, 24, ex + 8, 32], fill=(110, 40, 160))
    d.polygon([(20, 46), (44, 46), (32, 56)], fill=(250, 120, 40))
    save("cupcake_face", arr(im))
    candle = canvas((240, 240, 230))
    candle[:, ::6] = rgb((90, 160, 240))
    candle[:12] = rgb((255, 200, 60))
    save("candle", candle)

    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for (x, y, a) in ((6, 8, 0), (24, 14, 1), (14, 30, 2)):
        d.polygon([(x, y), (x + 30, y + a * 2), (x + 28, y + 34), (x - 2, y + 32)], fill=(238, 236, 228, 255), outline=(170, 168, 160, 255))
        for k in range(5):
            d.line([(x + 3, y + 6 + k * 5), (x + 24, y + 6 + k * 5 + a)], fill=(120, 120, 140, 255))
    save_rgba("papers", im)

    grille = canvas((26, 26, 28))
    yy, xx = np.mgrid[0:S, 0:S]
    grille[(xx % 3 == 0) | (yy % 3 == 0)] *= 1.8
    cone = np.hypot(xx - 32, yy - 36) < 20
    grille[cone] *= 0.6
    grille[np.abs(np.hypot(xx - 32, yy - 36) - 20) < 1.2] = rgb((70, 70, 72))
    save("speaker_front", grille * grain(0.05)[..., None])
    save("speaker_side", plastic((22, 22, 24), 0.2))

    save("counter_top", metal((170, 172, 174), 50, 0.35))
    cab = canvas((206, 204, 196))
    cab[:, 31:33] = rgb((120, 120, 118))
    cab[20:24, 24:28] = rgb((80, 80, 82))
    cab[20:24, 36:40] = rgb((80, 80, 82))
    cab[:4] = rgb((150, 150, 148))
    save("counter_side", drips(apply_dirt(cab, 0.3, 3), 0.25) * grain(0.05)[..., None])

    oven = metal((150, 152, 154), 20, 0.4)
    oven[22:52, 8:56] = rgb((18, 18, 20))
    oven[24:50, 10:54] = rgb((30, 26, 22)) * (0.8 + 0.4 * fbm(3, 2)[24:50, 10:54])[..., None]
    oven[16:19, 10:54] = rgb((200, 200, 205))
    for k in range(4):
        oven[4:12, 10 + k * 13:18 + k * 13] = rgb((30, 30, 30))
    save("oven_front", oven)
    burn = metal((40, 40, 42), 10, 0.3)
    for (x, y) in ((16, 16), (48, 16), (16, 48), (48, 48)):
        rr = np.hypot(xx - x, yy - y)
        burn[(rr > 8) & (rr < 11)] = rgb((90, 90, 92))
    save("oven_top", burn)

    for part in ("lower", "upper"):
        fr = plastic((226, 226, 220), 0.3)
        fr[:, 52:55] = rgb((170, 170, 172))
        if part == "upper":
            fr[S - 3:, :] = rgb((120, 120, 120))
            im = pil(fr)
            ImageDraw.Draw(im).rectangle([10, 10, 24, 26], fill=(250, 220, 60))   # a sticky note
            fr = arr(im)
        save(f"fridge_{part}", drips(fr, 0.2))
    save("fridge_side", plastic((214, 214, 208), 0.3))

    stall = plastic((196, 182, 150), 0.3)
    stall[4:6, 4:6] = stall[4:6, -6:-4] = stall[-6:-4, 4:6] = stall[-6:-4, -6:-4] = rgb((90, 90, 90))
    stall = scuffs(stall, 15, (60, 60, 140), 0.6)      # pen graffiti
    save("stall_wall", stall)
    sd = plastic((186, 170, 136), 0.3)
    sd[:, :2] = sd[:, -2:] = rgb((120, 110, 90))
    save("stall_door_bottom", sd)
    sdt = sd.copy()
    sdt[30:38, 50:58] = rgb((150, 150, 150))
    sdt[32:36, 52:56] = rgb((200, 40, 40))
    save("stall_door_top", sdt)

    steel = metal((96, 100, 104), 40, 0.45)
    for x in (4, 59):
        for y in range(4, 64, 12):
            steel[y:y + 2, x:x + 2] = rgb((150, 150, 155))
    bottom = steel.copy()
    stripes = ((xx + yy) // 8) % 2 == 0
    band = (yy > 44)
    bottom[band & stripes] = rgb((230, 180, 30))
    bottom[band & ~stripes] = rgb((20, 20, 20))
    bottom = apply_dirt(bottom, 0.3, 3)
    save("security_door_bottom", bottom)
    topd = steel.copy()
    topd[14:34, 20:44] = rgb((40, 50, 54)) * (0.7 + 0.5 * fbm(3, 2)[14:34, 20:44])[..., None]
    topd[14:16, 20:44] = topd[32:34, 20:44] = rgb((60, 60, 60))
    save("security_door_top", topd)

    panel = metal((120, 122, 126), 15, 0.3)
    im = pil(panel)
    ImageDraw.Draw(im).text((32, 10), "DOOR", font=font(10), fill=(20, 20, 20), anchor="mm")
    save("button_panel", arr(im))
    save("button_red", plastic((150, 20, 20), 0.1))
    save("button_red_on", plastic((255, 60, 50), 0.0))
    save("button_white", plastic((236, 236, 230), 0.15))

    for lit in (False, True):
        lamp = canvas((255, 236, 170) if lit else (60, 58, 50))
        rr = np.hypot(xx - 32, yy - 32)
        lamp *= (1.0 - (rr / 60) * (0.3 if lit else 0.5))[..., None]
        cage = ((xx % 16 < 2) | (yy % 16 < 2))
        lamp[cage] = rgb((40, 40, 40))
        save("door_light_on" if lit else "door_light", lamp)


# ------------------------------------------------------------------ models

def auto_uv(frm, to, face):
    """Vanilla-style UVs from the element box, kept inside 0..16: Minecraft does not wrap UVs, so a part
    taller than a block (chair backs, fridge) would otherwise sample the neighbouring atlas sprite."""
    (x1, y1, z1), (x2, y2, z2) = frm, to
    u, v = {"north": ((16 - x2, 16 - x1), (16 - y2, 16 - y1)), "south": ((x1, x2), (16 - y2, 16 - y1)),
            "east": ((16 - z2, 16 - z1), (16 - y2, 16 - y1)), "west": ((z1, z2), (16 - y2, 16 - y1)),
            "up": ((x1, x2), (z1, z2)), "down": ((x1, x2), (16 - z2, 16 - z1))}[face]

    def fit(a, b):
        if b - a > 16:
            return 0, 16
        if a < 0:
            return 0, b - a
        if b > 16:
            return a - (b - 16), 16
        return a, b

    (u1, u2), (v1, v2) = fit(*u), fit(*v)
    return [round(u1, 3), round(v1, 3), round(u2, 3), round(v2, 3)]


def el(frm, to, tex, faces=("north", "south", "east", "west", "up", "down"), rot=None, uv=None):
    e = {"from": list(frm), "to": list(to), "faces": {}}
    if isinstance(tex, dict):
        faces = [f for f in faces if f in tex]
    for f in faces:
        t = tex[f] if isinstance(tex, dict) else tex
        face = {"texture": t, "uv": uv[f] if uv and f in uv else auto_uv(frm, to, f)}
        e["faces"][f] = face
    if rot:
        e["rotation"] = rot
    return e


def model(name, textures, elements, parent="minecraft:block/block", ao=True):
    m = {"parent": parent, "textures": textures, "elements": elements}
    if not ao:
        m["ambientocclusion"] = False
    write_json(f"models/block/{name}.json", m)


def facing_state(name, models=None):
    models = models or [name]
    write_json(f"blockstates/{name}.json", {"variants": {
        f"facing={f}": [{"model": f"fnaf:block/{m}", "y": y} for m in models] if len(models) > 1 else {"model": f"fnaf:block/{models[0]}", "y": y}
        for f, y in FACINGS}})


def plain_state(name, models):
    write_json(f"blockstates/{name}.json", {"variants": {"": [{"model": f"fnaf:block/{m}"} for m in models] if len(models) > 1
                                                         else {"model": f"fnaf:block/{models[0]}"}}})


def item(name, parent=None, generated=None, gui_scale=None):
    if generated:
        write_json(f"models/item/{name}.json", {"parent": "minecraft:item/generated", "textures": {"layer0": generated}})
        return
    m = {"parent": parent or f"fnaf:block/{name}"}
    if gui_scale:
        m["display"] = {"gui": {"rotation": [30, 225, 0], "translation": [0, 0, 0], "scale": [gui_scale] * 3}}
    write_json(f"models/item/{name}.json", m)


def tx(**k):
    return {key: f"fnaf:block/{v}" for key, v in k.items()}


def models():
    # party chair (sitter faces south)
    legs = [el((x, 0, z), (x + 1.2, 8, z + 1.2), "#metal") for x in (3, 11.8) for z in (3, 11.8)]
    chair = legs + [el((2.5, 8, 2.5), (13.5, 9.5, 13.5), "#seat"),
                    el((3, 9.5, 2.5), (4.2, 21, 3.7), "#metal"), el((11.8, 9.5, 2.5), (13, 21, 3.7), "#metal"),
                    el((2.5, 14, 2.6), (13.5, 21, 3.6), "#seat")]
    model("chair", {**tx(metal="chair_metal", seat="chair_seat"), "particle": "fnaf:block/chair_seat"}, chair)
    facing_state("chair")
    item("chair")

    # plates and soda cups on the tables
    for v in range(3):
        model(f"plate_{v}", {**tx(p=f"plate_{v}"), "particle": f"fnaf:block/plate_{v}"},
              [el((2, 0, 2), (14, 0.6, 14), "#p", ("up",))], ao=False)
    plain_state("plate", [f"plate_{v}" for v in range(3)])
    item("plate", generated="fnaf:block/plate_0")
    cup = [el((6, 0, 6), (10, 7, 10), {"north": "#side", "south": "#side", "east": "#side", "west": "#side", "up": "#top", "down": "#top"}),
           el((8.5, 7, 7.5), (9.1, 10, 8.1), "#top", rot={"origin": [8, 7, 8], "axis": "z", "angle": -22.5})]
    model("soda_cup", {**tx(side="soda_cup", top="soda_top"), "particle": "fnaf:block/soda_cup"}, cup)
    plain_state("soda_cup", ["soda_cup"])
    item("soda_cup")

    # crossed sprites
    for v in range(3):
        write_json(f"models/block/streamer_{v}.json", {"parent": "minecraft:block/cross", "textures": {"cross": f"fnaf:block/streamer_{v}"}})
    plain_state("streamer", [f"streamer_{v}" for v in range(3)])
    item("streamer", generated="fnaf:block/streamer_0")
    write_json("models/block/cobweb.json", {"parent": "minecraft:block/cross", "textures": {"cross": "fnaf:block/cobweb"}})
    plain_state("cobweb", ["cobweb"])
    item("cobweb", generated="fnaf:block/cobweb")

    # wall-mounted flat things: plate against the north side, facing south
    def wall_flat(name, tex, frm, to, depth=1.0):
        model(name, {**tx(t=tex), "particle": f"fnaf:block/{tex}"},
              [el((frm[0], frm[1], 0), (to[0], to[1], depth), "#t")])
        facing_state(name)
        item(name)

    wall_flat("mirror", "mirror", (1, 1), (15, 15), 0.5)
    wall_flat("out_of_order_sign", "sign_out_of_order", (2, 3), (14, 13), 0.5)
    model("office_window", {**tx(t="window_glass"), "particle": "fnaf:block/window_glass"},
          [el((0, 0, 7.5), (16, 16, 8.5), "#t")])
    facing_state("office_window")
    item("office_window", generated="fnaf:block/window_glass")

    # cardboard boxes
    for v in range(3):
        write_json(f"models/block/box_{v}.json", {"parent": "minecraft:block/cube_bottom_top", "textures": tx(
            top="box_top", bottom="box_top", side=f"box_side_{v}")})
    plain_state("cardboard_box", [f"box_{v}" for v in range(3)])
    item("cardboard_box", "fnaf:block/box_1")

    # restroom sink (basin on a pedestal), toilet
    sink = [el((5, 0, 5), (11, 11, 10), "#p"), el((1, 11, 1), (15, 14, 13), "#p"),
            el((7, 14, 1), (9, 17, 3), "#c"), el((7, 16, 3), (9, 17, 6), "#c")]
    model("sink", {**tx(p="porcelain", c="chrome"), "particle": "fnaf:block/porcelain"}, sink)
    facing_state("sink")
    item("sink")
    toilet = [el((4, 0, 4), (12, 7, 14), "#p"), el((3, 7, 4), (13, 8.5, 15), "#p"),
              el((2, 7, 0.5), (14, 16, 4.5), "#p"), el((1.5, 16, 0), (14.5, 17, 5), "#p"), el((11, 14, 4.5), (12.5, 15, 5.5), "#c")]
    model("toilet", {**tx(p="porcelain", c="chrome"), "particle": "fnaf:block/porcelain"}, toilet)
    facing_state("toilet")
    item("toilet")

    # kitchen: pot of soup, oven, fridge, counter
    pot = [el((3, 0, 3), (13, 7, 13), {"north": "#s", "south": "#s", "east": "#s", "west": "#s", "down": "#s", "up": "#soup"}),
           el((1, 5, 7), (3, 6, 9), "#s"), el((13, 5, 7), (15, 6, 9), "#s")]
    model("cooking_pot", {**tx(s="steel", soup="soup"), "particle": "fnaf:block/steel"}, pot)
    plain_state("cooking_pot", ["cooking_pot"])
    item("cooking_pot")
    oven = [el((0, 0, 0), (16, 16, 16), {"south": "#front", "north": "#side", "east": "#side", "west": "#side", "up": "#top", "down": "#side"}),
            el((3, 12.5, 16), (13, 13.5, 17), "#c")]
    model("oven", {**tx(front="oven_front", side="steel", top="oven_top", c="chrome"), "particle": "fnaf:block/steel"}, oven)
    facing_state("oven")
    item("oven")
    fridge = [el((1, 0, 1), (15, 16, 15), {"south": "#lower", "north": "#side", "east": "#side", "west": "#side", "down": "#side", "up": "#side"}),
              el((1, 16, 1), (15, 31, 15), {"south": "#upper", "north": "#side", "east": "#side", "west": "#side", "up": "#side"})]
    model("fridge", {**tx(lower="fridge_lower", upper="fridge_upper", side="fridge_side"), "particle": "fnaf:block/fridge_side"}, fridge)
    facing_state("fridge")
    item("fridge", gui_scale=0.4)
    write_json("models/block/counter.json", {"parent": "minecraft:block/cube_bottom_top", "textures": tx(
        top="counter_top", bottom="dark_tile", side="counter_side")})
    plain_state("counter", ["counter"])
    item("counter")

    # supply closet / backstage: metal shelving, workbench, mop bucket, trash can
    shelf = [el((x, 0, z), (x + 1, 16, z + 1), "#m") for x in (0.5, 14.5) for z in (1, 14)]
    for y in (0, 7.5, 15):
        shelf.append(el((0.5, y, 1), (15.5, y + 1, 15), "#m"))
    shelf += [el((1.5, 1, 2), (14.5, 7.5, 13), {"north": "#i", "south": "#i", "east": "#i", "west": "#i", "up": "#m"}),
              el((1.5, 8.5, 3), (14.5, 14, 12), {"north": "#i", "south": "#i", "east": "#i", "west": "#i", "up": "#m"})]
    model("metal_shelf", {**tx(m="shelf_metal", i="shelf_items"), "particle": "fnaf:block/shelf_metal"}, shelf)
    facing_state("metal_shelf")
    item("metal_shelf")
    bench = [el((0, 12, 0), (16, 14, 16), {"up": "#top", "north": "#side", "south": "#side", "east": "#side", "west": "#side", "down": "#side"})]
    bench += [el((x, 0, z), (x + 2, 12, z + 2), "#m") for x in (1, 13) for z in (1, 13)]
    bench.append(el((1, 3, 1), (15, 4, 15), "#m"))
    model("workbench", {**tx(top="workbench_top", side="desk_front", m="chair_metal"), "particle": "fnaf:block/workbench_top"}, bench)
    facing_state("workbench")
    item("workbench")
    bucket = [el((3, 0, 3), (13, 8, 13), "#b"), el((7.5, 8, 7.5), (8.5, 26, 8.5), "#h"), el((5, 8, 5), (11, 11, 11), "#mop")]
    model("mop_bucket", {**tx(b="bucket_yellow", h="wood_handle", mop="mop"), "particle": "fnaf:block/bucket_yellow"}, bucket)
    plain_state("mop_bucket", ["mop_bucket"])
    item("mop_bucket", gui_scale=0.5)
    trash = [el((3, 0, 3), (13, 13, 13), {"north": "#s", "south": "#s", "east": "#s", "west": "#s", "down": "#s", "up": "#t"}),
             el((2.5, 13, 2.5), (13.5, 14, 13.5), {"north": "#s", "south": "#s", "east": "#s", "west": "#s", "down": "#s", "up": "#t"})]
    model("trash_can", {**tx(s="trash_side", t="trash_top"), "particle": "fnaf:block/trash_side"}, trash)
    plain_state("trash_can", ["trash_can"])
    item("trash_can")

    # office: desk, swivel chair, papers, Chica's cupcake
    desk = [el((0, 14, 0), (16, 16, 16), {"up": "#top", "north": "#front", "south": "#front", "east": "#front", "west": "#front", "down": "#front"}),
            el((0, 0, 14), (16, 14, 15.5), "#front")]
    model("office_desk", {**tx(top="desk_top", front="desk_front"), "particle": "fnaf:block/desk_top"}, desk)
    facing_state("office_desk")
    item("office_desk")
    base = [el((7, 0, 1), (9, 1.5, 15), "#b"), el((1, 0, 7), (15, 1.5, 9), "#b"), el((7, 1.5, 7), (9, 7, 9), "#b")]
    ochair = base + [el((2.5, 7, 2.5), (13.5, 9.5, 13.5), "#l"), el((3, 9.5, 2), (13, 22, 4), "#l"),
                     el((2, 11, 4), (3, 12, 12), "#b"), el((13, 11, 4), (14, 12, 12), "#b")]
    model("office_chair", {**tx(l="leather", b="black_plastic"), "particle": "fnaf:block/leather"}, ochair)
    facing_state("office_chair")
    item("office_chair")
    model("papers", {**tx(p="papers"), "particle": "fnaf:block/papers"}, [el((1, 0, 1), (15, 0.3, 15), "#p", ("up",))], ao=False)
    facing_state("papers")
    item("papers", generated="fnaf:block/papers")
    cake = [el((5, 0, 5), (11, 4, 11), "#w"),
            el((4.5, 4, 4.5), (11.5, 7, 11.5), {"south": "#face", "north": "#f", "east": "#f", "west": "#f", "up": "#f", "down": "#f"}),
            el((5.5, 7, 5.5), (10.5, 8, 10.5), "#f"), el((7.5, 8, 7.5), (8.5, 12, 8.5), "#c")]
    model("cupcake", {**tx(w="cupcake_wrapper", f="cupcake_frosting", face="cupcake_face", c="candle"), "particle": "fnaf:block/cupcake_frosting"}, cake)
    facing_state("cupcake")
    item("cupcake")

    # stage speaker cabinet
    model("speaker", {**tx(front="speaker_front", side="speaker_side"), "particle": "fnaf:block/speaker_side"},
          [el((0, 0, 0), (16, 16, 16), {"south": "#front", "north": "#side", "east": "#side", "west": "#side", "up": "#side", "down": "#side"})])
    facing_state("speaker")
    item("speaker")

    # simple cubes
    for name, tex in (("stall_wall", "stall_wall"),):
        gt.cube_block(name, [tex])

    # stage step slab
    p = "fnaf:block/stage_planks_0"
    for n, parent in (("stage_step", "slab"), ("stage_step_top", "slab_top")):
        write_json(f"models/block/{n}.json", {"parent": f"minecraft:block/{parent}", "textures": {"bottom": p, "top": p, "side": p}})
    vs = json.load(open(os.path.join(HERE, "vanilla", "dark_oak_slab.json")))
    s = json.dumps(vs).replace("minecraft:block/dark_oak_slab_top", "fnaf:block/stage_step_top") \
        .replace("minecraft:block/dark_oak_planks", "fnaf:block/stage_planks_0").replace("minecraft:block/dark_oak_slab", "fnaf:block/stage_step")
    write_json("blockstates/stage_step.json", json.loads(s))
    item("stage_step")

    # doors: restroom stall door + steel security door
    for name, kind in (("stall_door", "oak_door"), ("security_door", "iron_door")):
        for part in ("bottom_left", "bottom_left_open", "bottom_right", "bottom_right_open",
                     "top_left", "top_left_open", "top_right", "top_right_open"):
            write_json(f"models/block/{name}_{part}.json", {"parent": f"minecraft:block/door_{part}", "textures": tx(
                bottom=f"{name}_bottom", top=f"{name}_top")})
        vs = json.load(open(os.path.join(HERE, "vanilla", f"{kind}.json")))
        write_json(f"blockstates/{name}.json", json.loads(json.dumps(vs).replace(f"minecraft:block/{kind}", f"fnaf:block/{name}")))
        item(name, generated=f"fnaf:block/{name}_top")

    # door button (lever logic) + light button (button logic) + hall light (lamp logic)
    for name, btn in (("door_button", "button_red"), ("door_button_on", "button_red_on")):
        pressed = name.endswith("on")
        model(name, {**tx(p="button_panel", b=btn), "particle": "fnaf:block/button_panel"},
              [el((3, 0, 2), (13, 1.5, 14), "#p"), el((5.5, 1.5, 5), (10.5, 2.2 if pressed else 3.6, 11), "#b")], ao=False)
    vs = json.load(open(os.path.join(HERE, "vanilla", "lever.json")))
    s = json.dumps(vs).replace("minecraft:block/lever_on", "fnaf:block/door_button").replace("minecraft:block/lever", "fnaf:block/door_button_on")
    write_json("blockstates/door_button.json", json.loads(s))
    item("door_button")
    for n, parent in (("light_button", "button"), ("light_button_pressed", "button_pressed"), ("light_button_inventory", "button_inventory")):
        write_json(f"models/block/{n}.json", {"parent": f"minecraft:block/{parent}", "textures": tx(texture="button_white")})
    vs = json.load(open(os.path.join(HERE, "vanilla", "stone_button.json")))
    s = json.dumps(vs).replace("minecraft:block/stone_button_pressed", "fnaf:block/light_button_pressed").replace(
        "minecraft:block/stone_button", "fnaf:block/light_button")
    write_json("blockstates/light_button.json", json.loads(s))
    item("light_button", "fnaf:block/light_button_inventory")
    for lit in (False, True):
        n = "door_light_on" if lit else "door_light"
        write_json(f"models/block/{n}.json", {"parent": "minecraft:block/cube_all", "textures": tx(all=n)})
    write_json("blockstates/door_light.json", {"variants": {"lit=false": {"model": "fnaf:block/door_light"},
                                                            "lit=true": {"model": "fnaf:block/door_light_on"}}})
    item("door_light")

    # spare animatronic heads: drawn by a block entity renderer from the animatronic meshes
    write_json("models/block/spare_head.json", {"textures": {"particle": "fnaf:block/stage_planks_0"}})
    plain_state("spare_head", ["spare_head"])
    write_json("models/item/spare_head.json", {"parent": "builtin/entity", "gui_light": "side", "display": {
        "gui": {"rotation": [20, 200, 0], "translation": [0, 0, 0], "scale": [1.0, 1.0, 1.0]},
        "ground": {"rotation": [0, 0, 0], "translation": [0, 3, 0], "scale": [0.4, 0.4, 0.4]},
        "fixed": {"rotation": [0, 180, 0], "translation": [0, 0, 0], "scale": [0.8, 0.8, 0.8]},
        "thirdperson_righthand": {"rotation": [75, 45, 0], "translation": [0, 2.5, 0], "scale": [0.5, 0.5, 0.5]},
        "firstperson_righthand": {"rotation": [0, 45, 0], "translation": [0, 0, 0], "scale": [0.6, 0.6, 0.6]}}})


if __name__ == "__main__":
    textures()
    models()
    print("ok")
