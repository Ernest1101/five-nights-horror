"""Turns the exported FNAF 1 map (blender/map/fnaf1_tris.npz, see tools/blender/map_export.py) into
mod data. Every block cell that contains map geometry becomes a fnaf:map_block that draws its own
piece of the real model (client) and collides with it (both sides):

  assets/fnaf/textures/block/map/*.png      map textures (+ palette for flat-colour materials)
  assets/fnaf/map/fnaf1.fmap                geometry per cell (gzip, big endian)
  data/fnaf/map/fnaf1.fcol                  collision boxes per cell (gzip, read from the classpath)
  data/fnaf/structures/pizzeria.nbt         the map blocks as a structure template
  data/fnaf/pizzeria/markers.json           spawns, posters, generator

    python tools/pizzeria/build_map.py
"""
import gzip
import io
import json
import math
import os
import struct
import sys
from collections import defaultdict

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "blender", "map")
ASSETS = os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf")
DATA = os.path.join(ROOT, "src", "main", "resources", "data", "fnaf")
sys.path.insert(0, HERE)

EPS = 1e-5
# materials that never block movement (decor, lights, wires, chairs so the dining room stays walkable)
SOFT = {"wire", "party_hat", "posters", "celebrate", "sign", "Material.005", "Material.002", "chair", "curtain",
        "sun1", "sun2", "foxy_cove_purple", "arcade_screen", "monitor_screen", "button_door", "ceiling_light"}
LAMP_MATS = {"Material.005"}
DOOR_MATS = {"door"}                 # the office doors: drawn and solid only while closed
# ordinary doors of the map (door slabs that were part of the walls): opened / closed by clicking them
ROOM_DOORS = {"Object_252": True,     # dining -> side room (backstage camera)
              "Object_260": True,     # stage side door
              "Object_275": True, "Object_280": True,   # red double doors in the dining room
              "Object_345": False,    # dining -> west hall (open, like in FNAF)
              "Object_353": False,    # dining -> east hall (open)
              "Object_361": True,     # west hall -> supply closet
              "Object_538": True}     # dining -> right corridor
ROOM_DOOR_BIT = 8
DOOR_BUTTON_MATS = {"button_door"}   # red wall buttons that toggle the nearest door
LIGHT_BUTTON_MATS = {"Material.002"} # white wall buttons that light the hall outside the door
DOOR_BIT = 0x4000


# ------------------------------------------------------------------ textures

def build_textures(mats):
    """Copies the map textures into the block atlas folder and paints a palette for flat materials.
    Returns per material: sprite id, fixed uv (flat colours) or None, flags."""
    out_dir = os.path.join(ASSETS, "textures", "block", "map")
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, f))
    pal = Image.new("RGBA", (64, 64), (128, 128, 128, 255))
    slots = 0
    res, done = [], {}
    for m in mats:
        flags = (1 if m["cutout"] else 0) | (2 if m["emissive"] else 0)
        if m["texture"] and os.path.exists(m["texture"]):
            src = m["texture"]
            name = os.path.splitext(os.path.basename(src))[0].lower()
            if src not in done:
                im = Image.open(src).convert("RGBA")
                size = min(1024, 1 << int(math.log2(max(im.width, im.height))))
                w = size if im.width >= im.height else max(16, size * im.height // im.width)
                h = size if im.height >= im.width else max(16, size * im.width // im.height)
                w, h = 1 << int(round(math.log2(w))), 1 << int(round(math.log2(h)))
                im = im.resize((max(w, h), max(w, h)), Image.LANCZOS)     # atlas sprites must be square here
                im.save(os.path.join(out_dir, name + ".png"))
                done[src] = name
            res.append(dict(sprite=f"fnaf:block/map/{done[src]}", uv=None, flags=flags))
        else:
            c = tuple(int(255 * min(1.0, max(0.0, x)) ** (1 / 2.2)) for x in m["color"])
            if m["emissive"]:
                # glowing parts keep their hue (red door buttons), plain emitters (lamps) are warm white
                peak = max(m["color"])
                c = tuple(int(255 * x / peak) for x in m["color"]) if peak > 0.05 else (255, 250, 235)
            x, y = (slots % 8) * 8, (slots // 8) * 8
            pal.paste(c + (255,), (x, y, x + 8, y + 8))
            res.append(dict(sprite="fnaf:block/map/palette", uv=((x + 4) / 64, (y + 4) / 64), flags=flags))
            slots += 1
    pal.save(os.path.join(out_dir, "palette.png"))
    return res


# ------------------------------------------------------------------ clipping

def split(poly, axis, k):
    """Splits a convex polygon [(pos3, uv2), ...] by the plane coord[axis] == k (axis 0..2 = pos, 3..4 = uv)."""
    def val(v):
        return v[0][axis] if axis < 3 else v[1][axis - 3]

    lo, hi = [], []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        va, vb = val(a) - k, val(b) - k
        if va <= 0:
            lo.append(a)
        if va >= 0:
            hi.append(a)
        if (va < 0 < vb) or (vb < 0 < va):
            t = va / (va - vb)
            p = tuple(a[0][j] + (b[0][j] - a[0][j]) * t for j in range(3))
            u = tuple(a[1][j] + (b[1][j] - a[1][j]) * t for j in range(2))
            c = tuple(a[2][j] + (b[2][j] - a[2][j]) * t for j in range(3))
            lo.append((p, u, c))
            hi.append((p, u, c))
    return lo, hi


def chop(poly, axis):
    """Cuts a polygon along every integer plane of one axis; returns the pieces."""
    vals = [v[0][axis] if axis < 3 else v[1][axis - 3] for v in poly]
    a, b = math.floor(min(vals) + EPS), math.floor(max(vals) - EPS)
    pieces, rest = [], poly
    for k in range(a + 1, b + 1):
        lo, hi = split(rest, axis, k)
        if len(lo) >= 3:
            pieces.append(lo)
        rest = hi
        if len(rest) < 3:
            break
    if len(rest) >= 3:
        pieces.append(rest)
    return pieces


def area2(poly):
    p0 = np.array(poly[0][0])
    s = np.zeros(3)
    for i in range(1, len(poly) - 1):
        s += np.cross(np.array(poly[i][0]) - p0, np.array(poly[i + 1][0]) - p0)
    return np.linalg.norm(s)


# ------------------------------------------------------------------ main build

def build():
    d = np.load(os.path.join(SRC, "fnaf1_tris.npz"))
    meta = json.load(open(os.path.join(SRC, "fnaf1_meta.json")))
    mats = meta["materials"]
    tex = build_textures(mats)
    pos, uv, mat, obj = d["pos"].astype(np.float64), d["uv"].astype(np.float64), d["mat"], d["obj"]
    # baked shade per corner (tools/blender/map_bake.py); white when the map was exported without a bake
    col = d["col"].astype(np.float64) if "col" in d.files else np.ones(pos.shape)
    col = np.clip(0.14 + 0.9 * col, 0, 1.15)            # keep the darkest corners readable in game
    uv[..., 1] = 1.0 - uv[..., 1]                       # Blender v goes up, sprite v goes down
    # flat colour materials sample one palette pixel
    for mi, t in enumerate(tex):
        if t["uv"] is not None:
            uv[mat == mi] = t["uv"]
    # drop degenerate triangles and helper objects without a material (light volumes of the source scene)
    cr = np.cross(pos[:, 1] - pos[:, 0], pos[:, 2] - pos[:, 0])
    none = np.array([m["name"] == "none" for m in mats])
    keep = (np.linalg.norm(cr, axis=1) > 1e-7) & ~none[mat]
    pos, uv, mat, obj, col = pos[keep], uv[keep], mat[keep], obj[keep], col[keep]

    cells = defaultdict(list)          # (x, y, z) -> [(mat, [(pos_local, uv), ...]), ...]
    flags = defaultdict(int)           # (x, y, z) -> 1 door, 2 door button, 4 light button
    door_obj = set()
    room_obj = {}                      # object index -> closed by default
    global CLOSED_CELLS
    CLOSED_CELLS = set()
    boxes = defaultdict(dict)          # (x, y, z) -> {obj: [lo3, hi3]}
    lamps = set()
    soft_obj = set()
    obj_mat = defaultdict(lambda: defaultdict(int))
    for o, m in zip(obj, mat):
        obj_mat[int(o)][int(m)] += 1
    for o, counts in obj_mat.items():
        dom = mats[max(counts, key=counts.get)]["name"]
        ob = meta["objects"][o]
        size = np.array(ob["hi"]) - np.array(ob["lo"])
        if meta["objects"][o]["name"] in ROOM_DOORS:
            door_obj.add(o)
            room_obj[o] = ROOM_DOORS[meta["objects"][o]["name"]]
        elif dom in DOOR_MATS:
            door_obj.add(o)
        elif dom in SOFT or size.max() < 0.45:
            soft_obj.add(o)
    # signs, handles and lettering lying on an ordinary door swing with it
    global DOOR_OF, DOOR_TRIS, DOOR_CELLS_OF
    DOOR_OF, DOOR_TRIS, DOOR_CELLS_OF = {}, defaultdict(list), defaultdict(set)
    for s_ in list(room_obj):
        DOOR_OF[s_] = s_
        slo, shi = np.array(meta["objects"][s_]["lo"]), np.array(meta["objects"][s_]["hi"])
        thin = 0 if shi[0] - slo[0] < shi[2] - slo[2] else 2
        pad = np.array([0.08, 0.08, 0.08])
        pad[thin] = 0.3
        for o in obj_mat:
            if o in room_obj or meta["objects"][o]["tris"] > 4000:
                continue
            olo, ohi = np.array(meta["objects"][o]["lo"]), np.array(meta["objects"][o]["hi"])
            if np.all(olo >= slo - pad) and np.all(ohi <= shi + pad):
                DOOR_OF[o] = s_
                room_obj[o] = room_obj[s_]
                door_obj.add(o)
                soft_obj.add(o)
    # the other pieces of a door (backside panel etc.) share its parent node
    door_parents = {meta["objects"][o]["parent"] for o in door_obj}
    for o in obj_mat:
        if meta["objects"][o]["parent"] in door_parents:
            door_obj.add(o)
            soft_obj.discard(o)

    cmin = np.floor(pos.min(axis=1) + EPS).astype(int)
    cmax = np.floor(pos.max(axis=1) - EPS).astype(int)
    umin = np.floor(uv.min(axis=1) + 1e-4)
    umax = np.floor(uv.max(axis=1) - 1e-4)
    simple = np.all(cmin == cmax, axis=1) & np.all(umin == umax, axis=1)
    print(f"{len(pos)} triangles, {simple.sum()} need no clipping")

    def add(poly, m, o):
        if len(poly) < 3 or area2(poly) < 1e-7:
            return
        c = np.floor(np.mean([v[0] for v in poly], axis=0)).astype(int)
        key = tuple(int(x) for x in c)
        uo = np.floor(np.min([v[1] for v in poly], axis=0) + 1e-4) if tex[m]["uv"] is None else np.zeros(2)
        loc = [(tuple(np.clip(np.array(v[0]) - c, 0, 1)), tuple(np.clip(np.array(v[1]) - uo, 0, 1)), v[2]) for v in poly]
        name = mats[m]["name"]
        door = o in door_obj
        if o in DOOR_OF:
            # ordinary doors are drawn by the client door renderer (they swing), not in the block mesh
            DOOR_TRIS[DOOR_OF[o]].append((m, [(tuple(v[0]), tuple(v[1]), tuple(v[2])) for v in poly]))
            DOOR_CELLS_OF[DOOR_OF[o]].add(key)
            cells[key]
        else:
            cells[key].append((m | (DOOR_BIT if door else 0), loc))
        if name in LAMP_MATS:
            lamps.add(key)
        flags[key] |= (1 if door else 0) | (2 if name in DOOR_BUTTON_MATS else 0) | (4 if name in LIGHT_BUTTON_MATS else 0) \
            | (ROOM_DOOR_BIT if o in room_obj else 0)
        if room_obj.get(o):
            CLOSED_CELLS.add(key)
        if o not in soft_obj:
            p = np.array([v[0] for v in loc])
            o = ("door", o) if door else o
            b = boxes[key].get(o)
            lo, hi = p.min(axis=0), p.max(axis=0)
            boxes[key][o] = [np.minimum(b[0], lo), np.maximum(b[1], hi)] if b else [lo, hi]

    idx = np.nonzero(simple)[0]
    for i in idx:
        add([(tuple(pos[i, k]), tuple(uv[i, k]), tuple(col[i, k])) for k in range(3)], int(mat[i]), int(obj[i]))
    for i in np.nonzero(~simple)[0]:
        polys = [[(tuple(pos[i, k]), tuple(uv[i, k]), tuple(col[i, k])) for k in range(3)]]
        axes = (0, 1, 2) + ((3, 4) if tex[int(mat[i])]["uv"] is None else ())
        for ax in axes:
            polys = [q for p in polys for q in chop(p, ax)]
        for p in polys:
            add(p, int(mat[i]), int(obj[i]))
    # anything below the floor is never seen
    cells = {k: v for k, v in cells.items() if k[1] >= 0}
    boxes = {k: v for k, v in boxes.items() if k[1] >= 0}
    print(f"{len(cells)} cells, {sum(len(v) for v in cells.values())} polygons, {len(lamps)} lamp cells, "
          f"{sum(1 for f in flags.values() if f & 1)} door cells")
    global FLAGS
    FLAGS = dict(flags)
    return tex, cells, boxes, lamps


def render_top(tex, cells, path, max_y=3.4):
    """Top-down picture of everything below max_y (blocks above the floor) with a 1-block grid."""
    from PIL import ImageDraw
    px = 20
    xs = [k[0] for k in cells]
    zs = [k[2] for k in cells]
    w, h = (max(xs) + 2) * px, (max(zs) + 2) * px
    im = Image.new("RGB", (w, h), (40, 40, 40))
    dr = ImageDraw.Draw(im)
    colors = []
    for t in tex:
        sp = Image.open(os.path.join(ASSETS, "textures", "block", "map", t["sprite"].split("/")[-1] + ".png")).convert("RGB")
        if t["uv"] is not None:
            colors.append(sp.getpixel((int(t["uv"][0] * 64), int(t["uv"][1] * 64))))
        else:
            colors.append(tuple(int(c) for c in np.asarray(sp.resize((4, 4))).reshape(-1, 3).mean(axis=0)))
    items = []
    for (x, y, z), polys in cells.items():
        for m, poly in polys:
            m &= ~DOOR_BIT
            ys = [v[0][1] + y for v in poly]
            if max(ys) - 1.0 > max_y:
                continue
            items.append((max(ys), m, [((v[0][0] + x) * px, (v[0][2] + z) * px) for v in poly]))
    items.sort(key=lambda t: t[0])
    for _, m, pts in items:
        dr.polygon(pts, fill=colors[m])
    for x in range(0, w // px):
        dr.line([(x * px, 0), (x * px, h)], fill=(90, 90, 90) if x % 5 else (255, 255, 0), width=1)
        if x % 5 == 0:
            dr.text((x * px + 2, 2), str(x), fill=(255, 255, 0))
    for z in range(0, h // px):
        dr.line([(0, z * px), (w, z * px)], fill=(90, 90, 90) if z % 5 else (255, 255, 0), width=1)
        if z % 5 == 0:
            dr.text((2, z * px + 2), str(z), fill=(255, 255, 0))
    im.save(path)


def write_geometry(tex, cells):
    out = io.BytesIO()
    w = out.write
    w(b"FMAP" + struct.pack(">ii", 3, len(tex)))
    for t in tex:
        s = t["sprite"].encode()
        w(struct.pack(">h", len(s)) + s + struct.pack(">b", t["flags"]))
    w(struct.pack(">i", len(cells)))
    ntri = 0
    for (x, y, z), polys in sorted(cells.items()):
        # convex pieces go out as quads (a triangle repeats its last corner): half the vertices of a fan
        tris = []
        for m, poly in polys:
            k = 1
            while k < len(poly) - 1:
                if k + 2 < len(poly):
                    tris.append((m, poly[0], poly[k], poly[k + 1], poly[k + 2]))
                    k += 2
                else:
                    tris.append((m, poly[0], poly[k], poly[k + 1], poly[k + 1]))
                    k += 1
        ntri += len(tris)
        w(struct.pack(">hhhi", x, y, z, len(tris)))
        for m, *vs in tris:
            w(struct.pack(">h", m))
            for p, u, c in vs:
                w(struct.pack(">hhhHH", *(int(round(x * 2048)) for x in p), *(int(round(x * 65535)) for x in u)))
                w(struct.pack(">BBB", *(int(max(0, min(255, round(x * 228)))) for x in c)))
    path = os.path.join(ASSETS, "map", "fnaf1.fmap")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wb", compresslevel=6) as f:
        f.write(out.getvalue())
    print(f"geometry: {ntri} quads, {os.path.getsize(path) / 1e6:.1f} MB")


def collision(cells, boxes, doors=False):
    """Per cell up to 6 boxes in 1/16 block units; floors/ceilings become solid slabs, thin walls get 2px.
    doors=False: everything except the office doors, doors=True: only the doors."""
    out = {}
    for key, objs in boxes.items():
        bs = []
        for o, (lo, hi) in objs.items():
            if (isinstance(o, tuple) and o[0] == "door") != doors:
                continue
            lo, hi = lo.copy(), hi.copy()
            size = hi - lo
            if size[1] < 0.06 and size[0] > 0.3 and size[2] > 0.3:       # horizontal sheet
                if lo[1] > 0.5:
                    lo[1] = 0.0                                          # floor: solid below it
                else:
                    hi[1] = 1.0                                          # ceiling: solid above
            for a in (0, 2):
                if hi[a] - lo[a] < 0.125:
                    c = (hi[a] + lo[a]) / 2
                    lo[a], hi[a] = max(0, c - 0.0625), min(1, c + 0.0625)
            if hi[1] - lo[1] < 0.0625:
                hi[1] = min(1.0, lo[1] + 0.0625)
            bs.append((lo, hi))
        if len(bs) > 6:
            lo = np.min([b[0] for b in bs], axis=0)
            hi = np.max([b[1] for b in bs], axis=0)
            bs = [(lo, hi)]
        q = []
        for lo, hi in bs:
            a = np.clip(np.floor(lo * 16), 0, 16).astype(int)
            b = np.clip(np.ceil(hi * 16), 0, 16).astype(int)
            if np.all(b > a):
                q.append((*a, *b))
        if q:
            out[key] = q
    return out


def write_collision(col, door_col):
    """Per cell: flags (1 door, 2 door button, 4 light button), boxes, boxes of the closed door."""
    keys = sorted(set(col) | set(door_col) | {k for k, f in FLAGS.items() if f})
    out = io.BytesIO()
    out.write(b"FCOL" + struct.pack(">ii", 2, len(keys)))
    for k in keys:
        out.write(struct.pack(">hhhb", *k, FLAGS.get(k, 0)))
        for bs in (col.get(k, []), door_col.get(k, [])):
            out.write(struct.pack(">b", len(bs)))
            for b in bs:
                out.write(struct.pack(">6b", *b))
    path = os.path.join(DATA, "map", "fnaf1.fcol")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wb") as f:
        f.write(out.getvalue())
    print(f"collision: {len(col)} cells")


def write_doors(col):
    """Swinging doors for the client (assets/fnaf/map/fnaf1_doors.bin): hinge on one vertical edge, opening
    90 degrees to whichever side the walls leave room for."""
    meta = json.load(open(os.path.join(SRC, "fnaf1_meta.json")))

    def blocked(x, y, z):
        c = (int(math.floor(x)), int(math.floor(y)), int(math.floor(z)))
        lx, ly, lz = (x - c[0]) * 16, (y - c[1]) * 16, (z - c[2]) * 16
        return any(b[0] <= lx <= b[3] and b[1] <= ly <= b[4] and b[2] <= lz <= b[5] for b in col.get(c, []))

    out = io.BytesIO()
    doors = [s for s in DOOR_TRIS if DOOR_CELLS_OF[s]]
    out.write(b"FDOR" + struct.pack(">ii", 2, len(doors)))
    for s in doors:
        ob = meta["objects"][s]
        lo, hi = np.array(ob["lo"]), np.array(ob["hi"])
        along = 0 if hi[0] - lo[0] > hi[2] - lo[2] else 2
        mid = (lo + hi) / 2
        width = hi[along] - lo[along]
        y = lo[1] + 1.3
        best = None
        for edge in (lo[along], hi[along]):
            # double doors: never hinge where the other leaf meets this one
            if any(o != s and abs(meta["objects"][o]["lo"][along] - edge) < 0.15 or o != s
                   and abs(meta["objects"][o]["hi"][along] - edge) < 0.15 for o in doors
                   if abs(meta["objects"][o]["lo"][2 - along] - lo[2 - along]) < 0.3):
                continue
            hinge = mid.copy()
            hinge[along] = edge
            rest = width if edge == lo[along] else -width          # hinge -> free edge
            for ang in (90.0, -90.0):
                t = math.radians(ang)
                vx, vz = (rest, 0.0) if along == 0 else (0.0, rest)
                ex, ez = vx * math.cos(t) + vz * math.sin(t), -vx * math.sin(t) + vz * math.cos(t)
                hits = sum(blocked(hinge[0] + ex * k / 6, y, hinge[2] + ez * k / 6) for k in range(1, 7))
                side = ez if along == 0 else ex                 # which side of the wall the open door ends up on
                score = (hits, 0 if side > 0 else 1, 0 if edge == lo[along] else 1)
                if best is None or score < best[0]:
                    best = (score, hinge, ang)
        _, hinge, ang = best
        cells_ = sorted(DOOR_CELLS_OF[s])
        out.write(struct.pack(">h", len(cells_)))
        for c in cells_:
            out.write(struct.pack(">hhh", *c))
        tris = [(m, p[0], p[k], p[k + 1]) for m, p in DOOR_TRIS[s] for k in range(1, len(p) - 1)]
        out.write(struct.pack(">fff", float(hinge[0]), float(hinge[2]), ang))
        out.write(struct.pack(">i", len(tris)))
        for m, *vs in tris:
            out.write(struct.pack(">h", m))
            for p, u, c in vs:
                out.write(struct.pack(">8f", *p, *u, *(min(1.2, x) for x in c)))
        print(f"door {ob['name']}: {len(tris)} tris, hinge {np.round(hinge[[0, 2]], 2)}, swing {ang}")
    with gzip.open(os.path.join(ASSETS, "map", "fnaf1_doors.bin"), "wb") as f:
        f.write(out.getvalue())


def write_structure(cells, lamps, extra):
    import gen_pizzeria as gp          # reuse the NBT writer
    keys = set(cells) | set(extra)
    xs = [k[0] for k in keys]
    ys = [k[1] for k in keys]
    zs = [k[2] for k in keys]
    size = [max(xs) + 2, max(ys) + 2, max(zs) + 2]
    assert min(xs) >= 0 and min(ys) >= 0 and min(zs) >= 0, (min(xs), min(ys), min(zs))
    palette, index, entries = [], {}, []

    def state(name, props):
        k = (name, tuple(sorted(props.items())))
        if k not in index:
            index[k] = len(palette)
            e = {"Name": name}
            if props:
                e["Properties"] = dict(props)
            palette.append(e)
        return index[k]

    for key in sorted(cells):
        if key in extra:
            continue
        lamp = "true" if key in lamps else "false"
        closed = "true" if key in CLOSED_CELLS else "false"
        entries.append({"pos": list(key), "state": state("fnaf:map_block", {"lamp": lamp, "powered": lamp, "flash": "0",
                                                                             "closed": closed})})
    for key, (name, props) in extra.items():
        entries.append({"pos": list(key), "state": state(name, props)})
    root = {"DataVersion": 3465, "size": size, "palette": palette, "blocks": entries, "entities": []}
    raw = io.BytesIO()
    raw.write(struct.pack(">b", 10))
    gp.write_string(raw, "")
    gp.write_value(raw, "compound", root)
    with gzip.open(os.path.join(DATA, "structures", "pizzeria.nbt"), "wb") as f:
        f.write(raw.getvalue())
    print(f"structure {size}, {len(entries)} blocks")
    return size


if __name__ == "__main__":
    tex, cells, boxes, lamps = build()
    render_top(tex, cells, os.path.join(HERE, "map_top.png"))
    write_geometry(tex, cells)
    col = collision(cells, boxes)
    write_collision(col, collision(cells, boxes, doors=True))
    write_doors(col)
    # gameplay placements are added by place_map_markers() once the layout is known
    import map_markers
    extra, markers = map_markers.placements(cells, col)
    size = write_structure(cells, lamps, extra)
    markers["size"] = size
    with open(os.path.join(DATA, "pizzeria", "markers.json"), "w") as f:
        json.dump(markers, f, indent=1)
    with open(os.path.join(SRC, "cells_top.json"), "w") as f:
        json.dump(sorted({(k[0], k[2]) for k in cells}), f)
