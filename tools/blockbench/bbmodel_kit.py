"""Small toolkit for describing detailed Blockbench/GeckoLib models in code.

Geometry is bones + cubes in Blockbench pixel units (16 px = 1 block), facing north (-Z).
Every visible cube face gets its own rectangle in a generated texture atlas and is painted
procedurally: a material (color, noise, grime, pattern) plus optional painters for details
like eyes, teeth, holes, stitching or text. Faces can be hidden, which turns thin cubes into
decals (GeckoLib renders entities with alpha cutout, so transparent pixels are holes).
"""
import io
import math
import random

from PIL import Image, ImageDraw

FACES = ("north", "south", "east", "west", "up", "down")
DEFAULT_DENSITY = 3  # texels per model pixel


def _clamp(v):
    return max(0, min(255, int(round(v))))


def _mul(c, f):
    return tuple(_clamp(v * f) for v in c[:3])


def _mix(a, b, t):
    return tuple(_clamp(a[i] * (1 - t) + b[i] * t) for i in range(3))


class Model:
    def __init__(self, name, seed=1, grime=0.0, density=DEFAULT_DENSITY):
        self.name = name
        self.seed = seed
        self.grime = grime
        self.density = density
        self.bones = []
        self.by_name = {}
        self.mats = {}
        self.tex_size = None
        self._atlas = None
        self._glow = None

    # ------------------------------------------------------------------ materials
    def mat(self, key, rgb, kind="plain", noise=6, grime=None, pattern=None, rgb2=None, period=1.0,
            glow=False, shade=0.08):
        self.mats[key] = dict(rgb=tuple(rgb), kind=kind, noise=noise,
                              grime=self.grime if grime is None else grime,
                              pattern=pattern, rgb2=tuple(rgb2) if rgb2 else None, period=period,
                              glow=glow, shade=shade)

    # ------------------------------------------------------------------ geometry
    def bone(self, name, parent, pivot, rot=None):
        b = dict(name=name, parent=parent, pivot=list(pivot), rot=list(rot or [0, 0, 0]), cubes=[])
        self.bones.append(b)
        self.by_name[name] = b
        return b

    def box(self, bone, name, mat, frm, to, inflate=0, rot=None, origin=None, paint=None, only=None,
            d=None):
        """mat: material key or {face: key, '*': default}. paint: {face: (painter, params) | [..]}."""
        frm = [round(v, 3) for v in frm]
        to = [round(v, 3) for v in to]
        for i in range(3):
            if to[i] < frm[i]:
                frm[i], to[i] = to[i], frm[i]
        cube = dict(name=name, frm=frm, to=to, inflate=inflate, rot=list(rot or [0, 0, 0]),
                    origin=list(origin) if origin else None, mat=mat, paint=paint or {},
                    only=set(only) if only else None,
                    d=d or (self.density * 2 if mat == "teeth" else self.density))
        self.by_name[bone]["cubes"].append(cube)
        return cube

    def cbox(self, bone, name, mat, center, size, rot=None, origin=None, **kw):
        frm = [center[i] - size[i] / 2 for i in range(3)]
        to = [center[i] + size[i] / 2 for i in range(3)]
        if rot and any(rot) and origin is None:
            origin = list(center)
        return self.box(bone, name, mat, frm, to, rot=rot, origin=origin, **kw)

    def rbox(self, bone, name, mat, frm, to, b=0.6, paint=None, rot=None, origin=None, d=None):
        """Rounded box: three crossing cubes so every edge is bevelled by b."""
        size = [to[i] - frm[i] for i in range(3)]
        b = min(b, *(s / 2 - 0.05 for s in size))
        if rot and any(rot) and origin is None:
            origin = [(frm[i] + to[i]) / 2 for i in range(3)]
        if b < 0.1:
            return self.box(bone, name, mat, frm, to, rot=rot, origin=origin, paint=paint, d=d)
        paint = paint or {}
        pick = lambda fs: {f: paint[f] for f in fs if f in paint}
        x0, y0, z0 = frm
        x1, y1, z1 = to
        self.box(bone, name + "_z", mat, [x0 + b, y0 + b, z0], [x1 - b, y1 - b, z1], rot=rot, origin=origin,
                 paint=pick(("north", "south")), d=d)
        self.box(bone, name + "_x", mat, [x0, y0 + b, z0 + b], [x1, y1 - b, z1 - b], rot=rot, origin=origin,
                 paint=pick(("east", "west")), d=d)
        self.box(bone, name + "_y", mat, [x0 + b, y0, z0 + b], [x1 - b, y1, z1 - b], rot=rot, origin=origin,
                 paint=pick(("up", "down")), d=d)

    def crbox(self, bone, name, mat, center, size, **kw):
        frm = [center[i] - size[i] / 2 for i in range(3)]
        to = [center[i] + size[i] / 2 for i in range(3)]
        return self.rbox(bone, name, mat, frm, to, **kw)

    def decal(self, bone, name, center, size, painter, face="north", rot=None, origin=None, d=None):
        """Flat painted sticker: only one face is rendered. size = (w, h) in the face plane."""
        w, h = size
        thin = 0.1
        dims = {"north": [w, h, thin], "south": [w, h, thin], "east": [thin, h, w], "west": [thin, h, w],
                "up": [w, thin, h], "down": [w, thin, h]}[face]
        if rot and any(rot) and origin is None:
            origin = list(center)
        return self.cbox(bone, name, "_decal", center, dims, rot=rot, origin=origin,
                         paint={face: painter}, only=[face], d=d or self.density * 2)

    def sym(self, fn, *args, **kw):
        """Call a geometry method twice, mirrored across X=0. Coordinates are given for +X (left)."""
        name = args[1]
        for s, side in ((1, "l"), (-1, "r")):
            a = list(args)
            a[1] = f"{name}_{side}"
            k = dict(kw)
            if fn == self.decal:
                c = list(a[2])
                c[0] *= s
                a[2] = c
                if s == -1:
                    name_, params = a[4]
                    a[4] = (name_, dict(params, _mirror=not params.get("_mirror", False)))
                    if k.get("face") in ("east", "west"):
                        k["face"] = {"east": "west", "west": "east"}[k["face"]]
            elif fn in (self.cbox, self.crbox):
                c = list(a[3])
                c[0] *= s
                a[3] = c
            elif fn in (self.box, self.rbox):
                f, t = list(a[3]), list(a[4])
                f[0], t[0] = f[0] * s, t[0] * s
                a[3], a[4] = f, t
            if k.get("origin"):
                o = list(k["origin"])
                o[0] *= s
                k["origin"] = o
            if k.get("rot"):
                r = k["rot"]
                k["rot"] = [r[0], r[1] * s, r[2] * s]
            if s == -1:
                k = _mirror_paint(k)
            fn(*a, **k)

    def height(self):
        return max((c["to"][1] for b in self.bones for c in b["cubes"]), default=0)

    # ------------------------------------------------------------------ texture
    def finalize(self):
        if self._atlas is not None:
            return
        rnd = random.Random(self.seed)
        self.mats.setdefault("_decal", dict(rgb=(255, 0, 255), kind="plain", noise=0, grime=0, pattern=None,
                                            rgb2=None, period=1, glow=False, shade=0))
        rects = []
        for b in self.bones:
            for c in b["cubes"]:
                sx, sy, sz = (c["to"][i] - c["frm"][i] for i in range(3))
                dims = {"north": (sx, sy), "south": (sx, sy), "east": (sz, sy), "west": (sz, sy),
                        "up": (sx, sz), "down": (sx, sz)}
                c["uv"] = {}
                for f in FACES:
                    if c["only"] is not None and f not in c["only"]:
                        c["uv"][f] = None
                        continue
                    w, h = dims[f]
                    tw = max(1, int(round(w * c["d"])))
                    th = max(1, int(round(h * c["d"])))
                    rects.append((c, f, tw, th))
        # shelf packing, tallest first; 1 texel of edge padding around every rect
        rects.sort(key=lambda r: (-r[3], -r[2]))
        for size in (128, 256, 512, 1024, 2048):
            placed, x, y, shelf = [], 0, 0, 0
            ok = True
            for r in rects:
                w, h = r[2] + 2, r[3] + 2
                if x + w > size:
                    x, y, shelf = 0, y + shelf, 0
                if y + h > size or w > size:
                    ok = False
                    break
                placed.append((r, x + 1, y + 1))
                x += w
                shelf = max(shelf, h)
            if ok:
                break
        self.tex_size = size
        atlas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        for (c, f, w, h), px, py in placed:
            img, gimg = self._paint_face(c, f, w, h, rnd)
            atlas.paste(img, (px, py))
            glow.paste(gimg, (px, py))
            _extrude(atlas, px, py, w, h)
            c["uv"][f] = [px, py, px + w, py + h]
        self._atlas, self._glow = atlas, glow

    def _paint_face(self, c, f, w, h, rnd):
        key = c["mat"].get(f, c["mat"].get("*")) if isinstance(c["mat"], dict) else c["mat"]
        mt = self.mats[key]
        ctx = dict(D=c["d"], rnd=rnd, mat=mt, face=f, mats=self.mats)
        img = paint_base(w, h, ctx)
        gimg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if mt["glow"]:
            gimg = img.copy()
        jobs = c["paint"].get(f)
        if jobs:
            if isinstance(jobs, tuple):
                jobs = [jobs]
            for name, params in jobs:
                PAINTERS[name](img, gimg, params, ctx)
                if params.get("_mirror"):
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                    gimg = gimg.transpose(Image.FLIP_LEFT_RIGHT)
        return img, gimg

    def texture_png(self, glow_only=False):
        self.finalize()
        out = io.BytesIO()
        (self._glow if glow_only else self._atlas).save(out, "PNG", optimize=True)
        return out.getvalue()


def _mirror_paint(k):
    k = dict(k)
    p = k.get("paint")
    if isinstance(k.get("mat"), dict):
        m = dict(k["mat"])
        m["east"], m["west"] = k["mat"].get("west", m.get("*")), k["mat"].get("east", m.get("*"))
        k["mat"] = m
    if p:
        p2 = {}
        for face, jobs in p.items():
            face2 = {"east": "west", "west": "east"}.get(face, face)
            if isinstance(jobs, tuple):
                jobs = [jobs]
            p2[face2] = [(n, dict(params, _mirror=not params.get("_mirror", False))) for n, params in jobs]
        k["paint"] = p2
    return k


def _extrude(img, x, y, w, h):
    px = img.load()
    for i in range(w):
        px[x + i, y - 1] = px[x + i, y]
        px[x + i, y + h] = px[x + i, y + h - 1]
    for j in range(-1, h + 1):
        px[x - 1, y + j] = px[x, max(y, min(y + h - 1, y + j))]
        px[x + w, y + j] = px[x + w - 1, max(y, min(y + h - 1, y + j))]


# ====================================================================== painters

def paint_base(w, h, ctx):
    mt, rnd, D, face = ctx["mat"], ctx["rnd"], ctx["D"], ctx["face"]
    img = Image.new("RGBA", (w, h))
    px = img.load()
    cols = [rnd.uniform(-1, 1) for _ in range(w)]
    rows = [rnd.uniform(-1, 1) for _ in range(h)]
    face_f = {"up": 1.06, "down": 0.86}.get(face, 1.0)
    per = max(1, mt["period"] * D)
    for y in range(h):
        for x in range(w):
            alt = False
            p = mt["pattern"]
            if p == "stripes_h":
                alt = int(y // per) % 2 == 1
            elif p == "stripes_v":
                alt = int(x // per) % 2 == 1
            elif p == "check":
                alt = (int(x // per) + int(y // per)) % 2 == 1
            elif p == "dots":
                alt = x % 4 == 1 and y % 4 == 1
            base = mt["rgb2"] if alt and mt["rgb2"] else mt["rgb"]
            if mt["kind"] == "mc":
                # Minecraft-style mottling: every texel picks one of a few tones
                r = rnd.random()
                tone = 0.74 if r < 0.12 else 0.88 if r < 0.4 else 1.0 if r < 0.82 else 1.13
                px[x, y] = tuple(_clamp(v * tone * face_f) for v in base) + (255,)
                continue
            n = rnd.uniform(-1, 1) * mt["noise"]
            if mt["kind"] == "fur":
                n += cols[x] * mt["noise"] * 0.7 + (rnd.random() < 0.05) * -12
            elif mt["kind"] == "metal":
                n += rows[y] * mt["noise"] * 0.8
            elif mt["kind"] == "cloth":
                n += ((x + y) % 2) * -5
            f = face_f
            if w > 2 and h > 2 and (x == 0 or y == 0 or x == w - 1 or y == h - 1):
                f *= 1 - mt["shade"]
            px[x, y] = (_clamp(base[0] * f + n), _clamp(base[1] * f + n), _clamp(base[2] * f + n), 255)
    g = mt["grime"]
    if g > 0:
        spots = int(w * h * 0.004 * g) + (1 if rnd.random() < g else 0)
        for _ in range(spots):
            cx, cy = rnd.uniform(0, w), rnd.uniform(0, h)
            r = max(1.8, rnd.uniform(0.6, 1 + 2.5 * g) * D * 0.5)
            dark = rnd.uniform(0.55, 0.8)
            tint = (60, 45, 25) if rnd.random() < 0.5 else (20, 20, 20)
            for yy in range(max(0, int(cy - r)), min(h, int(cy + r) + 1)):
                for xx in range(max(0, int(cx - r)), min(w, int(cx + r) + 1)):
                    dd = ((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r + 1e-6)
                    if dd <= 1 and rnd.random() > dd * 0.6:
                        c = px[xx, yy]
                        px[xx, yy] = _mix(_mul(c, dark), tint, 0.25) + (255,)
    return img


def _ellipse_mask(w, h, inset=0.0):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).ellipse([inset, inset, w - 1 - inset, h - 1 - inset], fill=255)
    return m


def _clear(img):
    img.paste((0, 0, 0, 0), [0, 0, img.size[0], img.size[1]])


def p_eye(img, glow, p, ctx):
    """Round eye decal: sclera, iris, pupil, glint and an optional eyelid band on top."""
    w, h = img.size
    _clear(img)
    mask = _ellipse_mask(w, h)
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, w - 1, h - 1], fill=p.get("sclera", (236, 234, 226)) + (255,))
    r = h * p.get("iris_r", 0.34)
    cx, cy = w * (0.5 + p.get("look", -0.08)), h * 0.56
    iris = p["iris"]
    d.ellipse([cx - r, cy - r, cx + r - 1, cy + r - 1], fill=_mul(iris, 0.7) + (255,))
    d.ellipse([cx - r * 0.8, cy - r * 0.8, cx + r * 0.8 - 1, cy + r * 0.8 - 1], fill=iris + (255,))
    pr = max(1.0, r * 0.42)
    d.ellipse([cx - pr, cy - pr, cx + pr - 1, cy + pr - 1], fill=p.get("pupil", (10, 10, 12)) + (255,))
    gx, gy = int(cx - r * 0.45), int(cy - r * 0.5)
    if 0 <= gx < w and 0 <= gy < h:
        img.putpixel((gx, gy), (255, 255, 255, 255))
    if p.get("glow", True):
        gd = ImageDraw.Draw(glow)
        gd.ellipse([cx - r * 0.8, cy - r * 0.8, cx + r * 0.8 - 1, cy + r * 0.8 - 1], fill=iris + (255,))
        gd.ellipse([cx - pr, cy - pr, cx + pr - 1, cy + pr - 1], fill=(0, 0, 0, 0))
    lid = p.get("lid")
    if lid:
        lh = h * p.get("lid_frac", 0.28)
        px = img.load()
        for y in range(int(math.ceil(lh))):
            for x in range(w):
                if px[x, y][3]:
                    px[x, y] = (lid if y < lh - 1 else _mul(lid, 0.6)) + (255,)
        glow.paste((0, 0, 0, 0), [0, 0, w, int(math.ceil(lh))])
    img.putalpha(Image.composite(img.getchannel("A"), Image.new("L", (w, h), 0), mask))


def p_socket(img, glow, p, ctx):
    """Empty black eye socket with a tiny glowing pinpoint."""
    w, h = img.size
    _clear(img)
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, w - 1, h - 1], fill=(8, 6, 8, 255))
    d.ellipse([1, 1, w - 2, h - 2], fill=(2, 2, 3, 255))
    cx, cy = int(w * 0.5), int(h * 0.55)
    s = max(1, int(ctx["D"] * 0.35))
    col = p.get("pin", (255, 255, 255))
    for yy in range(cy - s // 2, cy - s // 2 + s):
        for xx in range(cx - s // 2, cx - s // 2 + s):
            img.putpixel((xx, yy), col + (255,))
            glow.putpixel((xx, yy), col + (255,))


def p_teeth(img, glow, p, ctx):
    w, h = img.size
    n = p.get("n", 8)
    up = p.get("up", True)
    col = p.get("color", (228, 222, 196))
    rnd = ctx["rnd"]
    pointed = p.get("pointed", False)
    px = img.load()
    if pointed:
        _clear(img)
    else:
        img.paste(p.get("gap", (60, 30, 28)) + (255,), [0, 0, w, h])
    d = ImageDraw.Draw(img)
    for i in range(n):
        x0 = round(i * w / n)
        x1 = round((i + 1) * w / n) - 1
        c = _mul(_mix(col, (190, 170, 110), rnd.uniform(0, p.get("yellow", 0.25))), rnd.uniform(0.9, 1.05))
        if pointed:
            mid = (x0 + x1) / 2
            poly = [(x0, 0), (x1, 0), (mid, h - 1)] if up else [(x0, h - 1), (x1, h - 1), (mid, 0)]
            d.polygon(poly, fill=c + (255,))
        else:
            right = x1 - 1 if x1 - x0 >= 2 else x1
            d.rectangle([x0, 0, right, h - 1], fill=c + (255,))
            edge = h - 1 if up else 0
            d.line([x0, edge, right, edge], fill=_mul(c, 0.8) + (255,))


def p_oval(img, glow, p, ctx):
    w, h = img.size
    if p.get("clear", True):
        _clear(img)
    d = ImageDraw.Draw(img)
    c = p["color"]
    rim = p.get("rim")
    if rim:
        d.ellipse([0, 0, w - 1, h - 1], fill=rim + (255,))
        d.ellipse([1, 1, w - 2, h - 2], fill=c + (255,))
    else:
        d.ellipse([0, 0, w - 1, h - 1], fill=c + (255,))
    rnd = ctx["rnd"]
    px = img.load()
    for y in range(h):
        for x in range(w):
            if px[x, y][3]:
                n = rnd.uniform(-1, 1) * p.get("noise", 6)
                q = px[x, y]
                px[x, y] = (_clamp(q[0] + n), _clamp(q[1] + n), _clamp(q[2] + n), 255)
    if p.get("glow"):
        glow.paste(img, (0, 0), img)


def p_nose(img, glow, p, ctx):
    w, h = img.size
    d = ImageDraw.Draw(img)
    d.ellipse([w * 0.18, h * 0.12, w * 0.45, h * 0.42], fill=_mul(p.get("color", (60, 50, 50)), 2.2) + (255,))


def p_dots(img, glow, p, ctx):
    w, h = img.size
    rnd = ctx["rnd"]
    for _ in range(p.get("n", 6)):
        x, y = rnd.randrange(1, max(2, w - 1)), rnd.randrange(int(h * 0.3), max(int(h * 0.3) + 1, h - 1))
        img.putpixel((x, y), p.get("color", (40, 25, 15)) + (255,))


def p_grille(img, glow, p, ctx):
    w, h = img.size
    for y in range(1, h, 2):
        for x in range((y // 2) % 2, w, 2):
            img.putpixel((x, y), p.get("color", (40, 40, 44)) + (255,))


def p_stitch(img, glow, p, ctx):
    w, h = img.size
    col = p.get("color", (40, 28, 20))
    if p.get("axis", "v") == "v":
        x = int(w * p.get("at", 0.5))
        for y in range(1, h - 1):
            if y % 3:
                img.putpixel((x, y), col + (255,))
    else:
        y = int(h * p.get("at", 0.5))
        for x in range(1, w - 1):
            if x % 3:
                img.putpixel((x, y), col + (255,))


def p_torn(img, glow, p, ctx):
    """Ragged bottom edge with holes, for torn cloth/fur."""
    w, h = img.size
    rnd = ctx["rnd"]
    px = img.load()
    depth = p.get("depth", 1.5) * ctx["D"]
    for x in range(w):
        cut = int(rnd.uniform(0, depth))
        for y in range(h - cut, h):
            px[x, y] = (0, 0, 0, 0)
        if h - cut - 1 >= 0:
            q = px[x, h - cut - 1]
            px[x, h - cut - 1] = _mul(q, 0.7) + (255,)


def p_hole(img, glow, p, ctx):
    """Torn hole showing the endoskeleton: dark cavity, metal bars and wires."""
    w, h = img.size
    rnd = ctx["rnd"]
    _clear(img)
    cx, cy = w / 2, h / 2
    pts = []
    for i in range(14):
        a = i / 14 * math.tau
        rr = rnd.uniform(0.75, 1.0)
        pts.append((cx + math.cos(a) * (w / 2 - 0.5) * rr, cy + math.sin(a) * (h / 2 - 0.5) * rr))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    inner = Image.new("RGBA", (w, h), (18, 14, 12, 255))
    d = ImageDraw.Draw(inner)
    metal = p.get("metal", (120, 120, 126))
    for i in range(p.get("bars", 2)):
        y = int(h * (i + 1) / (p.get("bars", 2) + 1))
        d.line([0, y, w, y], fill=metal + (255,), width=max(1, ctx["D"] // 2))
        d.line([0, y + 1, w, y + 1], fill=_mul(metal, 0.6) + (255,))
    for col in p.get("wires", [(170, 30, 30), (40, 60, 160)]):
        x0, x1 = rnd.uniform(0, w), rnd.uniform(0, w)
        d.line([x0, 0, x1, h], fill=col + (255,), width=1)
    img.paste(inner, (0, 0), mask)
    edge = mask.filter(__import__("PIL.ImageFilter", fromlist=["MaxFilter"]).MaxFilter(3))
    rim = Image.new("RGBA", (w, h), _mul(p.get("rim", (60, 40, 30)), 1) + (255,))
    ring = Image.composite(rim, Image.new("RGBA", (w, h), (0, 0, 0, 0)), edge)
    ring.paste(img, (0, 0), mask)
    img.paste(ring)


def p_mask(img, glow, p, ctx):
    """The Puppet's mask."""
    w, h = img.size
    d = ImageDraw.Draw(img)
    gd = ImageDraw.Draw(glow)
    for sx in (0.3, 0.7):
        ex, ey, ew, eh = w * sx, h * 0.38, w * 0.13, h * 0.1
        d.line([ex, ey + eh, ex, h * 0.78], fill=(120, 55, 150, 255), width=max(1, int(w * 0.05)))
        d.ellipse([ex - ew, ey - eh, ex + ew, ey + eh], fill=(6, 6, 8, 255))
        d.rectangle([ex - 0.5, ey - 0.5, ex + 0.5, ey + 0.5], fill=(255, 255, 255, 255))
        gd.rectangle([ex - 0.5, ey - 0.5, ex + 0.5, ey + 0.5], fill=(255, 255, 255, 255))
        cx, cy, cr = w * (0.5 + (sx - 0.5) * 1.55), h * 0.6, w * 0.09
        d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(205, 36, 50, 255))
        d.line([ex - ew, ey - eh * 1.8, ex + ew, ey - eh * 1.4 if sx < 0.5 else ey - eh * 1.8],
               fill=(20, 20, 24, 255), width=1)
    d.chord([w * 0.33, h * 0.68, w * 0.67, h * 0.9], 0, 180, fill=(200, 30, 40, 255))
    d.line([w * 0.33, h * 0.79, w * 0.67, h * 0.79], fill=(90, 10, 16, 255), width=1)


def p_smile(img, glow, p, ctx):
    """Open cartoon smile with a row of teeth (Balloon Boy)."""
    w, h = img.size
    _clear(img)
    d = ImageDraw.Draw(img)
    d.chord([0, -h, w - 1, h - 1], 0, 180, fill=(70, 18, 20, 255))
    d.rectangle([w * 0.15, 0, w * 0.85, h * 0.3], fill=(240, 236, 226, 255))
    for i in range(1, 6):
        x = w * 0.15 + i * w * 0.7 / 6
        d.line([x, 0, x, h * 0.3], fill=(170, 160, 150, 255))
    d.chord([w * 0.3, h * 0.55, w * 0.7, h * 1.2], 180, 360, fill=(200, 80, 90, 255))


def p_stripe_band(img, glow, p, ctx):
    w, h = img.size
    d = ImageDraw.Draw(img)
    n = p.get("n", 3)
    for i in range(n):
        y = h * (i + 0.5) / n
        d.line([0, y, w, y], fill=p.get("color", (235, 235, 235)) + (255,), width=max(1, int(h / n / 2)))


def p_rivets(img, glow, p, ctx):
    w, h = img.size
    if w < 4 or h < 4:
        return
    for x, y in ((1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)):
        img.putpixel((x, y), (200, 200, 205, 255))


def p_strings(img, glow, p, ctx):
    w, h = img.size
    d = ImageDraw.Draw(img)
    for i in range(p.get("n", 4)):
        x = w * (i + 0.5) / p.get("n", 4)
        d.line([x, 0, x, h], fill=p.get("color", (215, 215, 200)) + (255,))


def p_pickups(img, glow, p, ctx):
    w, h = img.size
    d = ImageDraw.Draw(img)
    for fy in (0.3, 0.55):
        d.rectangle([w * 0.25, h * fy, w * 0.75, h * fy + max(1, h * 0.09)], fill=(25, 25, 25, 255))
    d.rectangle([w * 0.3, h * 0.8, w * 0.7, h * 0.86], fill=(170, 170, 170, 255))
    for i in range(4):
        x = w * (0.35 + i * 0.1)
        d.line([x, 0, x, h * 0.83], fill=(220, 220, 205, 255))


FONT = {
    "A": ["010", "101", "111", "101", "101"], "B": ["110", "101", "110", "101", "110"],
    "E": ["111", "100", "110", "100", "111"], "L": ["100", "100", "100", "100", "111"],
    "N": ["101", "111", "111", "111", "101"], "O": ["111", "101", "101", "101", "111"],
    "S": ["011", "100", "010", "001", "110"], "T": ["111", "010", "010", "010", "010"],
    "!": ["1", "1", "1", "0", "1"], "'": ["1", "1", "0", "0", "0"], " ": ["0", "0", "0", "0", "0"],
}


def p_text(img, glow, p, ctx):
    w, h = img.size
    lines = p["text"].split("\n")
    cols = p.get("colors", [(30, 30, 30)])
    if p.get("bg"):
        img.paste(p["bg"] + (255,), [0, 0, w, h])
    line_w = max(sum(len(FONT[ch][0]) + 1 for ch in ln) - 1 for ln in lines)
    scale = max(1, min((w - 2) // line_w, (h - 2) // (len(lines) * 6)))
    total_h = len(lines) * 6 * scale - scale
    y = (h - total_h) // 2
    k = 0
    for ln in lines:
        lw = (sum(len(FONT[ch][0]) + 1 for ch in ln) - 1) * scale
        x = (w - lw) // 2
        for ch in ln:
            glyph = FONT[ch]
            col = cols[k % len(cols)]
            if ch != " ":
                k += 1
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit == "1":
                        for sy in range(scale):
                            for sx in range(scale):
                                xx, yy = x + gx * scale + sx, y + gy * scale + sy
                                if 0 <= xx < w and 0 <= yy < h:
                                    img.putpixel((xx, yy), col + (255,))
            x += (len(glyph[0]) + 1) * scale
        y += 6 * scale


def p_rounded(img, glow, p, ctx):
    """Cut the corners of a face so a flat plate reads as rounded (bibs, signs)."""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    r = p.get("r", 0.25) * min(w, h)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    img.putalpha(Image.composite(img.getchannel("A"), Image.new("L", (w, h), 0), mask))


def p_frame(img, glow, p, ctx):
    w, h = img.size
    ImageDraw.Draw(img).rectangle([0, 0, w - 1, h - 1], outline=p.get("color", (130, 60, 190)) + (255,),
                                  width=p.get("width", 1))


def p_fill(img, glow, p, ctx):
    w, h = img.size
    rnd = ctx["rnd"]
    px = img.load()
    for y in range(h):
        for x in range(w):
            n = rnd.uniform(-1, 1) * p.get("noise", 4)
            c = p["color"]
            px[x, y] = (_clamp(c[0] + n), _clamp(c[1] + n), _clamp(c[2] + n), 255)
    if p.get("glow"):
        glow.paste(img)


def p_pix(img, glow, p, ctx):
    """Pixel art stretched over the face: rows of chars, '.' keeps the material, ' ' is transparent.
    Colours are mottled like the material unless the key is listed in 'flat'."""
    w, h = img.size
    rows, cmap = p["rows"], p["colors"]
    flat, glows = p.get("flat", "KW"), p.get("glow", "")
    rnd = ctx["rnd"]
    for y in range(h):
        row = rows[min(len(rows) - 1, y * len(rows) // h)]
        for x in range(w):
            ch = row[min(len(row) - 1, x * len(row) // w)]
            if ch == ".":
                continue
            if ch == " ":
                img.putpixel((x, y), (0, 0, 0, 0))
                continue
            c = cmap[ch]
            if ch not in flat:
                r = rnd.random()
                c = _mul(c, 0.86 if r < 0.3 else 1.0 if r < 0.8 else 1.1)
            img.putpixel((x, y), c + (255,))
            if ch in glows:
                glow.putpixel((x, y), c + (255,))


PAINTERS = dict(pix=p_pix, frame=p_frame, fill=p_fill,eye=p_eye, socket=p_socket, teeth=p_teeth, oval=p_oval, nose=p_nose, dots=p_dots,
                grille=p_grille, stitch=p_stitch, torn=p_torn, hole=p_hole, mask=p_mask, smile=p_smile,
                band=p_stripe_band, rivets=p_rivets, strings=p_strings, pickups=p_pickups, text=p_text,
                rounded=p_rounded)
