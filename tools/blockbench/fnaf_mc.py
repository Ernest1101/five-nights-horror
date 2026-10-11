"""Detailed Minecraft-style FNAF animatronics (classic 16x: one texel per model pixel).

Modelled after the "FNAF 1 animatronics Minecraft style" look: chunky mottled fur, ragged fur
ruffles over every joint, fluffy cheeks and neck ruffs, bent arms holding props, pixel-art faces
and exposed endoskeleton parts. Bone names match fnaf_models so animations and mod code apply.
build_models.py builds these in Blockbench through the MCP server.
"""
import math
import random

from bbmodel_kit import Model
from fnaf_models import animations  # noqa: F401  (re-exported for build_models)

K, W = (22, 20, 20), (240, 240, 236)
TOOTH = (236, 232, 214)


# ====================================================================== helpers

def base_mats(m, fur, fur2=None, endo=(72, 72, 78)):
    m.mat("fur", fur, kind="mc")
    m.mat("fur2", fur2 or fur, kind="mc")
    m.mat("fur_dk", tuple(int(v * 0.5) for v in fur), kind="mc")
    m.mat("endo", endo, kind="mc")
    m.mat("endo_l", (172, 172, 178), kind="mc")
    m.mat("black", (30, 28, 30), kind="mc")
    m.mat("white", (236, 236, 232), kind="mc")
    m.mat("teeth", TOOTH, kind="mc")
    m.mat("red", (190, 24, 28), kind="mc")
    m.mat("mouth", (60, 16, 18), kind="mc")


def pix(rows, colors, glow="", flat="KWT"):
    return ("pix", dict(rows=rows, colors=colors, glow=glow, flat=flat))


def uid(m):
    m.__dict__["_n"] = m.__dict__.get("_n", 0) + 1
    return m._n


def fit(rows, w, h):
    """Pad/trim pixel-art rows to exactly w x h with '.' (keep material)."""
    rows = [r.ljust(w, ".")[:w] for r in rows][:h]
    return rows + ["." * w] * (h - len(rows))


def oval_rows(w, h, ow, oh, ch="b", seed=0, bottom=0):
    rnd = random.Random(seed)
    cx, cy = (w - 1) / 2, h - 1 - bottom - (oh - 1) / 2
    rows = []
    for y in range(h):
        r = ""
        for x in range(w):
            d = ((x - cx) / (ow / 2)) ** 2 + ((y - cy) / (oh / 2)) ** 2
            r += ch if d < 0.82 or (d < 1.08 and rnd.random() < 0.5) else "."
        rows.append(r)
    return rows


def fringe(m, bone, mat, cx, cz, rx, rz, y, n, drop=(1.2, 2.4), w=1.4, out=10, arc=(0, 360), seed=None):
    """Ring of small hanging fur flaps around an ellipse: the ragged ruffle over a joint.
    arc angles: 0 = +X, 90 = back (+Z), 180 = -X, 270 = front (-Z)."""
    rnd = random.Random(seed if seed is not None else uid(m))
    for i in range(n):
        a = math.radians(arc[0] + (arc[1] - arc[0]) * (i + 0.5) / n + rnd.uniform(-5, 5))
        x, z = cx + math.cos(a) * rx, cz + math.sin(a) * rz
        d = rnd.uniform(*drop)
        ww = w * rnd.uniform(0.8, 1.25)
        t = out * rnd.uniform(0.4, 1.2)
        m.box(bone, f"flap{uid(m)}", mat, [x - ww / 2, y - d, z - ww / 2], [x + ww / 2, y, z + ww / 2],
              rot=[-t * math.sin(a), 0, t * math.cos(a)], origin=[x, y, z])


def spikes(m, bone, mat, pts, size=(1, 1, 2.5), tilt=35, seed=1):
    """Fur strands sticking out: pts = [(x, y, z, yaw_deg)]."""
    rnd = random.Random(seed)
    for x, y, z, yaw in pts:
        ln = size[2] * rnd.uniform(0.7, 1.3)
        m.box(bone, f"spike{uid(m)}", mat, [x - size[0] / 2, y - size[1] / 2, z - ln], [x + size[0] / 2, y + size[1] / 2, z],
              rot=[rnd.uniform(-tilt, tilt) * 0.5, yaw, rnd.uniform(-tilt, tilt)], origin=[x, y, z])


# ====================================================================== skeleton

def body(m, P):
    lw, ld, hx = P["lw"], P["ld"], P["hx"]
    fh, sh, th = P.get("foot_h", 2), P["shin"], P["thigh"]
    L = fh + sh + 1 + th
    tw, td, pel, ch = P["tw"], P["td"], P["pelvis"], P["chest"]
    N = L + pel + ch
    aw, ua, fa = P["aw"], P["ua"], P["fa"]
    fr = P.get("fringe", True)

    m.bone("root", None, [0, 0, 0])
    m.bone("body", "root", [0, L, 0], P.get("body_rot"))
    for side, s in (("right", -1), ("left", 1)):
        x = s * hx
        leg = f"{side}_leg"
        m.bone(leg, "root", [x, L, 0], P.get(f"{side}_leg_rot"))
        yk = fh + sh
        tc, sc = P.get("thigh_c", "fur"), P.get("shin_c", "fur")
        m.box(leg, "thigh", tc, [x - lw / 2, yk + 1, -ld / 2], [x + lw / 2, L + 1, ld / 2], paint=P.get("thigh_paint"))
        m.box(leg, "thigh_top", tc, [x - lw / 2 - 0.5, L - 1.5, -ld / 2 - 0.5], [x + lw / 2 + 0.5, L + 1, ld / 2 + 0.5])
        m.box(leg, "knee", "endo", [x - 1.25, yk - 0.5, -1.25], [x + 1.25, yk + 1.5, 1.25])
        if P.get("endo_shin"):
            m.box(leg, "shin", "endo_l", [x - 1, fh, -1], [x + 1, yk, 1])
            m.box(leg, "piston", "endo", [x - 0.5, fh + 1, -2], [x + 0.5, yk - 1, -1])
            m.box(leg, "piston2", "endo", [x + 1, fh + 1, -0.5], [x + 1.6, yk - 1, 0.5])
        else:
            m.box(leg, "shin", sc, [x - lw / 2 + 0.5, fh, -ld / 2 + 0.5], [x + lw / 2 - 0.5, yk, ld / 2 - 0.5])
        if fr and not P.get("endo_shin"):
            fringe(m, leg, sc, x, 0, lw / 2 - 0.2, ld / 2 - 0.2, fh + 2.2, 9, drop=(1, 2.1), w=1.5, out=14)
        if fr:
            fringe(m, leg, tc, x, 0, lw / 2 + 0.1, ld / 2 + 0.1, yk + 1.5, 9, drop=(1.2, 2.4), w=1.6, out=14)
        foot(m, leg, x, lw, ld, fh, P)

    m.box("body", "pelvis", P.get("pelvis_c", "fur"), [-tw / 2 + 1, L - 1, -td / 2 + 1], [tw / 2 - 1, L + pel, td / 2 - 1],
          paint=P.get("pelvis_paint"))
    chest_paint = dict(P.get("chest_paint", {}))
    if P.get("belly") and "north" not in chest_paint:
        cols = {"b": m.mats[P["belly"]]["rgb"]}
        chest_paint["north"] = pix(oval_rows(int(tw), int(ch), tw - 4, ch - 1, seed=len(m.name)), cols)
    m.box("body", "chest", P.get("chest_c", "fur"), [-tw / 2, L + pel, -td / 2], [tw / 2, N, td / 2], paint=chest_paint)
    m.box("body", "back_hump", P.get("chest_c", "fur"), [-tw / 2 + 1, N - 3, td / 2], [tw / 2 - 1, N - 0.5, td / 2 + 1])
    if fr:
        fringe(m, "body", P.get("chest_c", "fur"), 0, 0, tw / 2 - 0.4, td / 2 - 0.4, L + pel + 1.2, 12, drop=(1, 2.2), w=1.6,
               out=12, arc=(0, 180))
        if P.get("belly"):
            fringe(m, "body", P["belly"], 0, 0, tw / 2 - 2.4, td / 2 - 0.4, L + pel + 1.2, 4, drop=(1, 1.8), w=1.5, out=10,
                   arc=(235, 305))

    hands = {}
    for side, s in (("right", -1), ("left", 1)):
        ax = s * (tw / 2 + aw / 2)
        arm, fore = f"{side}_arm", f"{side}_forearm"
        m.bone(arm, "body", [ax, N - 2, 0], P.get(f"{side}_arm_rot"))
        up, fo = P.get("upper_c", "fur"), P.get("fore_c", "fur")
        m.box(arm, "shoulder", up, [ax - aw / 2 - 1, N - 4.5, -aw / 2 - 1], [ax + aw / 2 + 1, N + 0.5, aw / 2 + 1])
        m.box(arm, "upper", up, [ax - aw / 2, N - 4.5 - ua, -aw / 2], [ax + aw / 2, N - 4.5, aw / 2])
        ey = N - 4.5 - ua
        m.box(arm, "elbow", "endo", [ax - 1.25, ey - 1, -1.25], [ax + 1.25, ey + 0.5, 1.25])
        if fr:
            fringe(m, arm, up, ax, 0, aw / 2, aw / 2, ey + 1.6, 8, drop=(1, 2), w=1.5, out=14)
        m.bone(fore, arm, [ax, ey - 0.5, 0], P.get(f"{side}_forearm_rot"))
        if P.get(f"{side}_fore_endo"):
            m.box(fore, "forearm", "endo_l", [ax - 1, ey - 1 - fa, -1], [ax + 1, ey - 1, 1])
            m.box(fore, "forearm_rod", "endo", [ax - 0.5, ey - 1 - fa + 1, -1.8], [ax + 0.5, ey - 2, -0.9])
        else:
            m.box(fore, "forearm", fo, [ax - aw / 2, ey - 1 - fa, -aw / 2], [ax + aw / 2, ey - 1, aw / 2], paint=P.get("fore_paint"))
        top = ey - 1 - fa - 1
        m.box(fore, "wrist", "endo", [ax - 1.25, top, -1.25], [ax + 1.25, top + 1, 1.25])
        if fr and not P.get(f"{side}_fore_endo"):
            fringe(m, fore, fo, ax, 0, aw / 2 - 0.1, aw / 2 - 0.1, top + 2.2, 8, drop=(1, 2), w=1.5, out=14)
        hand(m, fore, ax, top, s, aw, P.get(f"{side}_hand", "paw"), P.get("hand_c", "fur"))
        hands[side] = (ax, top, s, fore)

    m.bone("head", "body", [0, N, 0], P.get("head_rot"))
    nk = P.get("neck", 2)
    m.box("head", "neck", "endo", [-1.5, N - 0.5, -1.5], [1.5, N + nk, 1.5])
    m.params = P
    m.anchors = dict(L=L, N=N, y0=N + nk, tw=tw, td=td, hands=hands)
    return m.anchors


def foot(m, leg, x, lw, ld, fh, P):
    style = P.get("foot_style", "paw")
    fc = P.get("foot_c", "fur")
    if style == "paw":
        m.box(leg, "foot", fc, [x - lw / 2 - 0.75, 0, -ld / 2 - 2.5], [x + lw / 2 + 0.75, fh, ld / 2 + 0.75])
        m.box(leg, "foot_top", fc, [x - lw / 2, fh, -ld / 2 - 1.5], [x + lw / 2, fh + 1, ld / 2 - 0.5])
        for i, dx in enumerate((-2.4, -0.8, 0.8, 2.4)):
            m.box(leg, f"toe{i}", fc, [x + dx - 0.75, 0, -ld / 2 - 4], [x + dx + 0.75, 1.6, -ld / 2 - 2.5])
    elif style == "bird":
        m.box(leg, "foot", fc, [x - lw / 2, 0, -ld / 2 - 1], [x + lw / 2, fh, ld / 2])
        for i in (-1, 0, 1):
            m.box(leg, f"toe{i + 1}", fc, [x + i * 2 - 0.9, 0, -ld / 2 - 4.5], [x + i * 2 + 0.9, 1.8, -ld / 2 - 1],
                  rot=[0, i * 12, 0], origin=[x, 0, -ld / 2 - 1])
            m.box(leg, f"claw{i + 1}", "claw", [x + i * 2 - 0.6, 0, -ld / 2 - 6], [x + i * 2 + 0.6, 1.2, -ld / 2 - 4.5],
                  rot=[0, i * 12, 0], origin=[x, 0, -ld / 2 - 1])
        m.box(leg, "heel", fc, [x - 0.75, 0, ld / 2], [x + 0.75, 1.5, ld / 2 + 1.5])
    elif style == "endo":
        m.box(leg, "foot", "endo_l", [x - lw / 2 - 0.5, 0, -ld / 2 - 1], [x + lw / 2 + 0.5, 1.2, ld / 2 + 0.5])
        for i in (-1, 0, 1):
            m.box(leg, f"toe{i + 1}", "endo_l", [x + i * 1.6 - 0.6, 0, -ld / 2 - 3.5], [x + i * 1.6 + 0.6, 0.9, -ld / 2 - 1])
        m.box(leg, "ankle", "endo", [x - 0.75, 0.5, -0.75], [x + 0.75, 2.5, 0.75])
    elif style == "shoe":
        m.box(leg, "foot", fc, [x - lw / 2 - 0.5, 0, -ld / 2 - 1.5], [x + lw / 2 + 0.5, fh, ld / 2 + 0.5])


def hand(m, fore, ax, top, s, aw, style, mat):
    if style == "none":
        return
    if style == "endo":
        m.box(fore, "palm", "endo_l", [ax - 0.75, top - 2, -1.5], [ax + 0.75, top, 1.5])
        for i in (-1, 0, 1):
            m.box(fore, f"finger{i + 1}", "endo_l", [ax - 0.4, top - 4.5, i * 1.1 - 0.4], [ax + 0.4, top - 2, i * 1.1 + 0.4])
        return
    m.box(fore, "palm", mat, [ax - aw / 2 - 0.25, top - 3, -aw / 2 - 0.75], [ax + aw / 2 + 0.25, top, aw / 2 + 0.75])
    for i, z in enumerate((-1.9, -0.65, 0.6, 1.85)):
        ln = 2.6 if i in (1, 2) else 2.2
        m.box(fore, f"finger{i}", mat, [ax - 0.7 - s * 0.3, top - 3 - ln, z - 0.55], [ax + 0.7 - s * 0.3, top - 3, z + 0.55])
    m.box(fore, "thumb", mat, [ax - 0.7, top - 2.8, -aw / 2 - 2.2], [ax + 0.7, top - 0.5, -aw / 2 - 0.6])


def bowtie(m, a, mat):
    N, td = a["N"], a["td"]
    c = m.mats[mat]["rgb"]
    m.box("body", "bowtie", mat, [-3, N - 2.5, -td / 2 - 1], [3, N - 0.5, -td / 2],
          paint={"north": pix(["xx..xx", "xxxxxx", "xx..xx"], {"x": c}, flat="")})
    m.box("body", "bow_knot", mat, [-0.75, N - 2, -td / 2 - 1.5], [0.75, N - 1, -td / 2 - 1])


def cheeks(m, y0, fur, w=5.0, hd=4.5):
    """Fluffy sideburns beside the muzzle plus a ragged neck ruff along the jaw line."""
    for s in (1, -1):
        m.box("head", f"cheek{s}", fur, [s * (w - 1) - 1.2, y0 - 0.5, -hd], [s * (w - 1) + 1.2, y0 + 3.5, -hd + 3])
    fringe(m, "head", fur, 0, 0, w, hd - 0.5, y0 + 0.8, 11, drop=(1, 2.4), w=1.7, out=16, arc=(0, 180))


# ====================================================================== bears

def freddy(name="freddy", golden=False):
    m = Model(name, seed=11 if not golden else 12, density=1, grime=0.0)
    if golden:
        base_mats(m, (206, 170, 44), (226, 196, 86))
    else:
        base_mats(m, (124, 72, 34), (198, 140, 90))
    m.mat("mic", (40, 40, 44), kind="mc")
    m.mat("mic_head", (150, 150, 156), kind="mc")
    P = dict(lw=5.5, ld=5.5, hx=3.4, shin=4, thigh=5, tw=14, td=9, pelvis=3, chest=10, aw=4.5, ua=5, fa=4, belly="fur2")
    if golden:
        P.update(right_forearm_rot=[18, 0, 0], left_forearm_rot=[18, 0, 0], head_rot=[8, 0, 8])
    else:
        P.update(right_forearm_rot=[70, 0, -14], left_forearm_rot=[62, 0, 18], right_arm_rot=[8, 0, 0], left_arm_rot=[8, 0, 0])
    a = body(m, P)
    y0, N, L, td, tw = a["y0"], a["N"], a["L"], a["td"], a["tw"]
    bowtie(m, a, "black")
    dk = m.mats["fur_dk"]["rgb"]
    if golden:
        eyes = ["", "", "..KKK..KKK", "..KWK..KWK", "..KKK..KKK"]
    else:
        eyes = ["", "", "..KKK..KKK", "..WBB..BBW", "..WBB..BBW"]
    m.box("head", "skull", "fur", [-5, y0, -4.5], [5, y0 + 8.5, 4.5],
          paint={"north": pix(fit(eyes, 10, 8), {"K": K, "W": W, "B": (60, 120, 230)}, glow="W" if golden else "B")})
    m.box("head", "brow_ridge", "fur", [-5.5, y0 + 6.5, -5.2], [5.5, y0 + 7.8, -4.5])
    for s in (1, -1):
        m.box("head", f"eyebrow{s}", "black", [s * 3.8 - 2, y0 + 7.2, -5.7], [s * 3.8 + 2, y0 + 8.2, -5.2], rot=[0, 0, -s * 14],
              origin=[s * 3.8, y0 + 7.7, -5.5])
    cheeks(m, y0, "fur")
    m.box("head", "muzzle", "fur2", [-3.5, y0 + 0.5, -7], [3.5, y0 + 4, -4.5],
          paint={"north": pix(["d.....d", ".......", ".d...d."], {"K": K, "d": dk}, flat="K")})
    m.box("head", "nose", "black", [-1.5, y0 + 3, -7.7], [1.5, y0 + 4.5, -6.9])
    m.box("head", "mouth", "mouth", [-3, y0 - 0.5, -6.5], [3, y0 + 0.6, -4.5])
    m.box("head", "teeth_up", "teeth", [-3.2, y0 - 0.2, -6.8], [3.2, y0 + 0.8, -6.3],
          paint={"north": pix(["TTTTTTT"], {"T": TOOTH}, flat="T")})
    m.bone("jaw", "head", [0, y0 + 0.2, -3])
    m.box("jaw", "jaw", "fur2", [-3.5, y0 - 2, -7], [3.5, y0 - 0.2, -2.5])
    m.box("jaw", "teeth_dn", "teeth", [-3, y0 - 0.5, -6.7], [3, y0, -6.2], paint={"north": pix(["TTTTT"], {"T": TOOTH}, flat="T")})
    for s in (1, -1):
        m.box("head", f"ear{s}", "fur", [s * 5.2 - 2, y0 + 6.8, -0.9], [s * 5.2 + 2, y0 + 10.8, 0.9])
        m.box("head", f"ear_in{s}", "fur_dk" if golden else "fur2", [s * 5.2 - 1.2, y0 + 7.4, -1.3], [s * 5.2 + 1.2, y0 + 9.8, -0.9])
    for i, (x, rz) in enumerate(((-1.5, -10), (0.5, 4), (2, 14))):
        m.box("head", f"tuft{i}", "fur", [x - 0.7, y0 + 8.5, -1.5 + i], [x + 0.7, y0 + 10, -0.3 + i], rot=[0, 0, rz],
              origin=[x, y0 + 8.5, -1])
    m.box("head", "hat_brim", "black", [-3.5, y0 + 8.5, -3.5], [3.5, y0 + 9.5, 3.5])
    m.box("head", "hat_top", "black", [-2.5, y0 + 9.5, -2.5], [2.5, y0 + 14, 2.5])
    m.box("head", "hat_band", "black", [-2.7, y0 + 9.5, -2.7], [2.7, y0 + 10.5, 2.7])
    if golden:
        m.decal("body", "tear", [3.2, L + 7, -td / 2 - 0.06], [3, 3], ("hole", dict(bars=1)))
        m.decal("right_leg", "tear", [-3.4, 9, -2.8], [2.4, 2.4], ("hole", dict(bars=1)))
    else:
        ax, top, s, fore = a["hands"]["right"]
        m.bone("mic", fore, [ax, top, 0], [-70, 0, 14])
        m.box("mic", "mic_handle", "mic", [ax - 0.6, top - 3.5, -3.1], [ax + 0.6, top + 2, -1.9])
        m.box("mic", "mic_head", "mic_head", [ax - 1.2, top + 2, -3.7], [ax + 1.2, top + 4.4, -1.3],
              paint={f: pix(["g.g", ".g.", "g.g"], {"g": (70, 70, 74)}, flat="g") for f in ("north", "south", "east", "west")})
        m.box("mic", "mic_ring", "endo_l", [ax - 0.9, top + 1.4, -3.4], [ax + 0.9, top + 2, -1.6])
    return m, dict(width=0.9, height=2.3, egg=(0x7C4822, 0x1A1A1A) if not golden else (0xCEAA2C, 0x1E1C1E))


def golden_freddy():
    return freddy("golden_freddy", golden=True)


# ====================================================================== rabbits

def rabbit(m, a, eye_rows, eye_cols, glow, broken_ear=False, mouth_rows=None, ragged=False):
    y0 = a["y0"]
    m.box("head", "skull", "fur", [-5, y0, -4.5], [5, y0 + 8.5, 4.5], paint={"north": pix(fit(eye_rows, 10, 8), eye_cols, glow=glow)})
    m.box("head", "brow_ridge", "fur", [-5.4, y0 + 6.3, -5.1], [5.4, y0 + 7.6, -4.5])
    for s in (1, -1):
        m.box("head", f"eyebrow{s}", "black", [s * 3.6 - 2, y0 + 7.0, -5.6], [s * 3.6 + 2, y0 + 8, -5.1], rot=[0, 0, -s * 12],
              origin=[s * 3.6, y0 + 7.5, -5.3])
    cheeks(m, y0, "fur", w=5.0, hd=4.5)
    m.box("head", "muzzle", "fur2", [-3.8, y0 + 0.4, -7], [3.8, y0 + 4.2, -4.5],
          paint={"north": pix(mouth_rows or ["...NN...", ".d.NN.d.", ".d...d.."], {"N": (70, 36, 90), "d": (110, 110, 140), "g": (150, 150, 150),
                                                                                  "T": TOOTH}, flat="N")})
    m.box("head", "mouth", "mouth", [-3.2, y0 - 0.5, -6.5], [3.2, y0 + 0.6, -4.5])
    m.box("head", "teeth_up", "teeth", [-3.4, y0 - 0.2, -6.8], [3.4, y0 + 0.9, -6.3], paint={"north": pix(["TTTTTTTT"], {"T": TOOTH}, flat="T")})
    m.bone("jaw", "head", [0, y0 + 0.2, -3])
    m.box("jaw", "jaw", "fur2", [-3.7, y0 - 2, -7], [3.7, y0 - 0.2, -2.5])
    m.box("jaw", "teeth_dn", "teeth", [-3.2, y0 - 0.5, -6.7], [3.2, y0, -6.2], paint={"north": pix(["TTTTTTT"], {"T": TOOTH}, flat="T")})
    inner = m.mats["fur2"]["rgb"]
    for side, s in (("left", 1), ("right", -1)):
        bn = f"{side}_ear"
        broken = broken_ear and side == "right"
        m.bone(bn, "head", [s * 2.6, y0 + 8, 0], [0, 0, -6 * s] if not broken else [-35, 0, -40 * s])
        h = 5 if broken else 11
        m.box(bn, "ear", "fur", [s * 2.6 - 1.7, y0 + 8, -0.8], [s * 2.6 + 1.7, y0 + 8 + h, 0.8],
              paint={"north": pix(["fff"] + ["fbf"] * (h - 2) + ["fff"], {"b": inner, "f": m.mats["fur"]["rgb"]}, flat="")})
        m.box(bn, "ear_in", "fur2", [s * 2.6 - 0.9, y0 + 9, -1.2], [s * 2.6 + 0.9, y0 + 7 + h, -0.8])
        if broken:
            m.box(bn, "ear_wire", "endo_l", [s * 2.6 - 0.5, y0 + 13, -0.5], [s * 2.6 + 0.5, y0 + 15.5, 0.5])
            m.box(bn, "ear_wire2", "red", [s * 2.6 + 0.5, y0 + 12.5, -0.3], [s * 2.6 + 1, y0 + 14, 0.3], rot=[0, 0, -25],
                  origin=[s * 2.6 + 0.7, y0 + 12.5, 0])
    m.box("head", "forelock", "fur", [-1, y0 + 8.5, -3], [1, y0 + 10, -1.5], rot=[-20, 0, 0], origin=[0, y0 + 8.5, -2])
    if ragged:
        spikes(m, "head", "fur", [(s * 5.0, y0 + 2 + dy, -1 + dz, 90 * s) for s in (1, -1) for dy, dz in ((0, 0), (2.5, 1.5))],
               size=(1, 1, 2), seed=5)


def bonnie():
    m = Model("bonnie", seed=21, density=1)
    base_mats(m, (86, 72, 172), (156, 172, 228))
    m.mat("guitar", (196, 26, 30), kind="mc")
    m.mat("neck", (26, 24, 26), kind="mc")
    P = dict(lw=5.5, ld=5.5, hx=3.4, shin=4, thigh=5, tw=14, td=9, pelvis=3, chest=10, aw=4.5, ua=5, fa=4, belly="fur2",
             right_forearm_rot=[60, 0, -10], left_forearm_rot=[75, 0, 22], right_arm_rot=[10, 0, 0], left_arm_rot=[18, 0, 0])
    a = body(m, P)
    rabbit(m, a, ["", "", ".KKK..KKK.", ".KWPP.PPWK", ".KWPP.PPWK"], {"K": K, "W": W, "P": (226, 50, 170)}, "P")
    bowtie(m, a, "red")
    L, td = a["L"], a["td"]
    gc = [-1.5, L + 6, -td / 2 - 2.5]
    rot = [0, 0, 38]

    def g(name, mat, f, t, paint=None):
        m.box("body", name, mat, [gc[0] + f[0], gc[1] + f[1], gc[2] + f[2]], [gc[0] + t[0], gc[1] + t[1], gc[2] + t[2]],
              rot=rot, origin=gc, paint=paint)

    g("g_body", "guitar", [-2.5, -1, -0.75], [2.5, 2.5, 0.75])
    g("g_prong_l", "guitar", [-3.5, -7, -0.75], [-1.2, -1, 0.75], paint={"north": pix([".w."] * 6, {"w": W}, flat="w")})
    g("g_prong_r", "guitar", [1.2, -7, -0.75], [3.5, -1, 0.75], paint={"north": pix([".w."] * 6, {"w": W}, flat="w")})
    g("g_pickup", "black", [-1.5, 0.2, -0.95], [1.5, 1.2, -0.75])
    g("g_neck", "neck", [-0.6, 2.5, -0.6], [0.6, 16, 0.6], paint={"north": pix(["K", "W"] * 6 + ["K"], {"K": K, "W": W}, flat="KW")})
    g("g_head", "guitar", [-1.2, 16, -0.6], [1.2, 19, 0.6])
    return m, dict(width=0.9, height=2.6, egg=(0x5648AC, 0xC41A1E))


# ====================================================================== chica

def chica():
    m = Model("chica", seed=31, density=1)
    base_mats(m, (234, 198, 34), (246, 222, 90))
    m.mat("beak", (238, 124, 22), kind="mc")
    m.mat("leg_o", (232, 112, 26), kind="mc")
    m.mat("claw", (214, 238, 244), kind="mc")
    m.mat("bib", (240, 240, 236), kind="mc")
    m.mat("plate", (226, 236, 240), kind="mc")
    m.mat("cake", (206, 96, 40), kind="mc")
    m.mat("frosting", (236, 70, 120), kind="mc")
    m.mat("candle", (246, 226, 90), kind="mc")
    m.mat("flame", (255, 170, 40), kind="mc", glow=True)
    P = dict(lw=5.5, ld=5.5, hx=3.4, shin=4, thigh=5, tw=14, td=9.5, pelvis=3, chest=10, aw=4.5, ua=5, fa=4,
             shin_c="leg_o", foot_c="leg_o", foot_style="bird", left_forearm_rot=[78, 0, 6], right_forearm_rot=[30, 0, 0],
             left_arm_rot=[12, 0, 0])
    a = body(m, P)
    y0, N, L, td = a["y0"], a["N"], a["L"], a["td"]
    m.box("head", "skull", "fur", [-5.2, y0, -4.8], [5.2, y0 + 9.5, 4.8],
          paint={"north": pix(fit(["", "", "KKKK..KKKK", ".KKKK.KKKK", ".KWPP.PPWK", ".KWPP.PPWK", "..KK....KK"], 10, 10),
                              {"K": K, "W": W, "P": (220, 60, 160)}, glow="P")})
    cheeks(m, y0, "fur", w=5.2, hd=4.8)
    m.box("head", "beak", "beak", [-3.2, y0 + 1.8, -9], [3.2, y0 + 4.2, -4.8], paint={"north": pix(["..NN..", "......"], {"N": (150, 70, 20)}, flat="N")})
    m.box("head", "beak_tip", "beak", [-2.4, y0 + 2.2, -10], [2.4, y0 + 3.6, -9])
    m.box("head", "mouth", "mouth", [-2.8, y0 + 0.8, -8], [2.8, y0 + 1.8, -4.8])
    m.box("head", "teeth_up", "teeth", [-2.9, y0 + 1.5, -9], [2.9, y0 + 2.3, -8.4], paint={"north": pix(["TTTTTT"], {"T": TOOTH}, flat="T")})
    m.bone("jaw", "head", [0, y0 + 1.6, -3.4])
    m.box("jaw", "jaw", "beak", [-2.7, y0 - 0.3, -9], [2.7, y0 + 1.6, -3.4])
    m.box("jaw", "teeth_dn", "teeth", [-2.6, y0 + 1.1, -8.8], [2.6, y0 + 1.8, -8.3], paint={"north": pix(["TTTTT"], {"T": TOOTH}, flat="T")})
    for s in (1, -1):
        m.box("head", f"eyebrow{s}", "black", [s * 3.4 - 2.6, y0 + 7.3, -5.4], [s * 3.4 + 2.6, y0 + 8.6, -4.9], rot=[0, 0, -s * 22],
              origin=[s * 3.4, y0 + 7.9, -5.2])
    for i, (x, rz, hh) in enumerate(((-1.5, 24, 3), (0, 0, 4), (1.5, -24, 3))):
        m.box("head", f"tuft{i}", "fur", [x - 0.7, y0 + 9.5, -0.5], [x + 0.7, y0 + 9.5 + hh, 0.5], rot=[0, 0, rz], origin=[x, y0 + 9.5, 0])
        m.box("head", f"tuft_t{i}", "fur2", [x - 0.4, y0 + 9.5 + hh, -0.3], [x + 0.4, y0 + 10.5 + hh, 0.3], rot=[0, 0, rz],
              origin=[x, y0 + 9.5, 0])
    m.box("body", "bib", "bib", [-5.5, L + 4, -td / 2 - 0.5], [5.5, N - 0.5, -td / 2], d=3,
          paint={"north": [("text", dict(text="LET'S\nEAT!!", bg=(242, 242, 238),
                                         colors=[(150, 60, 200), (240, 190, 30), (60, 170, 230), (230, 70, 150), (240, 130, 30)])),
                           ("frame", dict(color=(150, 60, 200), width=1))]})
    for i, (x, y, c) in enumerate(((-4.6, 4.5, (60, 180, 70)), (4.5, 5, (40, 150, 230)), (-4.6, 8, (240, 190, 30)),
                                   (4.4, 9, (230, 60, 150)), (0, 4.4, (240, 130, 30)))):
        m.decal("body", f"conf{i}", [x, L + y, -td / 2 - 0.55], [1, 1], ("fill", dict(color=c)))
    ax, top = a["hands"]["left"][0], a["hands"]["left"][1]
    hx, hyc = ax, top - 1.5
    m.bone("cupcake", "left_forearm", [hx, hyc, 0], [-78, 0, -6])
    m.box("cupcake", "plate", "plate", [hx - 3.5, hyc + 1.5, -3.5], [hx + 3.5, hyc + 2.2, 3.5])
    m.box("cupcake", "cake", "cake", [hx - 2.5, hyc + 2.2, -2.5], [hx + 2.5, hyc + 4.5, 2.5])
    m.box("cupcake", "frosting", "frosting", [hx - 3, hyc + 4.5, -3], [hx + 3, hyc + 8, 3],
          paint={"north": pix(["......", "WYK.KY", "......", "..TTT."], {"Y": (246, 220, 40), "K": K, "W": W, "T": TOOTH}, glow="Y", flat="WKYT")})
    m.box("cupcake", "frosting_top", "frosting", [hx - 1.8, hyc + 8, -1.8], [hx + 1.8, hyc + 9, 1.8])
    m.box("cupcake", "candle", "candle", [hx - 0.5, hyc + 9, -0.5], [hx + 0.5, hyc + 11, 0.5])
    m.box("cupcake", "flame", "flame", [hx - 0.5, hyc + 11, -0.5], [hx + 0.5, hyc + 12, 0.5])
    return m, dict(width=0.9, height=2.3, egg=(0xEAC622, 0xEE7C16))


# ====================================================================== foxy

def foxy():
    m = Model("foxy", seed=41, density=1, grime=0.5)
    base_mats(m, (176, 40, 32), (216, 150, 122))
    m.mat("pants", (110, 62, 30), kind="mc")
    m.mat("hook", (176, 176, 180), kind="mc")
    m.mat("inner", (92, 18, 16), kind="mc")
    torn = {f: pix(["...."] * 4 + ["  . ", " .  "], {}) for f in ("north", "south", "east", "west")}
    P = dict(lw=4.5, ld=4.5, hx=2.8, shin=5, thigh=5, tw=12, td=8, pelvis=3, chest=9, aw=3.5, ua=5, fa=4, belly="fur2",
             thigh_c="pants", pelvis_c="pants", thigh_paint=torn, endo_shin=True, foot_style="endo",
             right_hand="none", left_hand="endo", left_fore_endo=True, right_forearm_rot=[20, 0, 0],
             right_arm_rot=[0, 0, -40], left_arm_rot=[10, 0, 0], head_rot=[-4, -8, 6])
    a = body(m, P)
    y0, N, L, td, tw = a["y0"], a["N"], a["L"], a["td"], a["tw"]
    m.box("head", "skull", "fur", [-4.2, y0, -4.2], [4.2, y0 + 7.5, 4.2],
          paint={"north": pix(fit(["", "", "KKKK..KK", "KKKK.WYK", "KKKK.WYK"], 8, 7), {"K": K, "W": W, "Y": (250, 210, 30)}, glow="Y")})
    m.box("head", "brow", "fur", [-4.5, y0 + 5.5, -4.8], [4.5, y0 + 6.7, -4.2])
    m.box("head", "snout", "fur", [-2.2, y0 + 1.2, -8.5], [2.2, y0 + 3.4, -4.2], paint={"down": pix(["tttt"], {"t": m.mats["fur2"]["rgb"]})})
    m.box("head", "nose", "black", [-1.1, y0 + 2.7, -9], [1.1, y0 + 3.9, -8])
    m.box("head", "mouth", "mouth", [-2, y0 + 0.2, -8], [2, y0 + 1.3, -4.2])
    m.box("head", "teeth_up", "teeth", [-2.1, y0 + 0.6, -8.2], [2.1, y0 + 1.5, -7.7], paint={"north": pix(["TTTT"], {"T": TOOTH}, flat="T")})
    m.bone("jaw", "head", [0, y0 + 0.4, -3.4], [-12, 0, 0])
    m.box("jaw", "jaw", "fur2", [-2.2, y0 - 1.5, -8], [2.2, y0 + 0.2, -3.4])
    m.box("jaw", "teeth_dn", "teeth", [-2, y0 - 0.2, -7.8], [2, y0 + 0.5, -7.3], paint={"north": pix(["TTTT"], {"T": TOOTH}, flat="T")})
    m.box("head", "patch_strap", "black", [-4.6, y0 + 5, -4.4], [4.6, y0 + 5.9, 4.4], rot=[0, 0, -14], origin=[0, y0 + 5.5, 0])
    m.box("head", "patch", "black", [0.6, y0 + 3.6, -4.8], [3.6, y0 + 6.2, -4.2])
    cheeks(m, y0, "fur", w=4.4, hd=4.2)
    for s in (1, -1):
        m.box("head", f"ear{s}", "fur", [s * 3.2 - 1.9, y0 + 6.5, -0.7], [s * 3.2 + 1.9, y0 + 10.5, 0.7], rot=[0, 0, -12 * s],
              origin=[s * 3.2, y0 + 6.5, 0])
        m.box("head", f"ear_tip{s}", "fur", [s * 3.9 - 0.7, y0 + 10.5, -0.5], [s * 3.9 + 0.7, y0 + 12.5, 0.5], rot=[0, 0, -12 * s],
              origin=[s * 3.2, y0 + 6.5, 0])
        m.box("head", f"ear_in{s}", "inner", [s * 3.2 - 1, y0 + 7.2, -1.1], [s * 3.2 + 1, y0 + 10, -0.7], rot=[0, 0, -12 * s],
              origin=[s * 3.2, y0 + 6.5, 0])
    spikes(m, "head", "fur", [(s * 4.4, y0 + 1.5 + dy, dz, 90 * s) for s in (1, -1) for dy, dz in ((0, -1), (1.8, 0.5), (3.4, -0.5))] +
           [(dx, y0 + 7.5, dz, 0) for dx, dz in ((-1.5, 1), (1, -1.5), (2.5, 1))], size=(1, 1, 2.6), seed=3)
    # ragged torn fur all over the torso and arms, showing the endoskeleton underneath
    for k, yy in enumerate((N - 1.5, N - 4.5, N - 7.5)):
        fringe(m, "body", "fur", 0, 0, tw / 2 - 0.3, td / 2 - 0.3, yy, 12, drop=(1.5, 3.2), w=1.8, out=26, arc=(0, 360), seed=70 + k)
    spikes(m, "body", "fur", [(s * (tw / 2 + 0.2), N - 2 - 2.5 * k, 0, 90 * s) for s in (1, -1) for k in range(3)], size=(1, 1.4, 3), seed=9)
    m.decal("body", "chest_hole", [-1.4, L + 6.5, -td / 2 - 0.06], [4.5, 4], ("hole", dict(bars=2)))
    m.decal("body", "chest_hole2", [3, L + 4, -td / 2 - 0.06], [2.5, 2.5], ("hole", dict(bars=1)))
    rx = -(tw / 2 + 3.5 / 2)
    for k in range(3):
        fringe(m, "right_arm", "fur", rx, 0, 1.9, 1.9, N - 5.5 - 2.5 * k, 8, drop=(1.2, 2.6), w=1.5, out=24, seed=90 + k)
    ax, top, s, fore = a["hands"]["right"]
    m.box(fore, "hook_cuff", "hook", [ax - 1.5, top - 1, -1.5], [ax + 1.5, top + 0.5, 1.5])
    m.box(fore, "hook_shaft", "hook", [ax - 0.5, top - 4.5, -0.5], [ax + 0.5, top - 1, 0.5])
    m.box(fore, "hook_bend", "hook", [ax - 0.5, top - 5.5, -2.5], [ax + 0.5, top - 4.5, 0.5])
    m.box(fore, "hook_up", "hook", [ax - 0.5, top - 5.5, -3.5], [ax + 0.5, top - 2.8, -2.5])
    m.box(fore, "hook_tip", "hook", [ax - 0.4, top - 3.2, -3.4], [ax + 0.4, top - 1.8, -2.6], rot=[-30, 0, 0], origin=[ax, top - 2.8, -3])
    return m, dict(width=0.8, height=2.4, egg=(0xB02820, 0xD8967A))


# ====================================================================== the rest

def springtrap():
    m = Model("springtrap", seed=51, density=1, grime=0.6)
    base_mats(m, (118, 124, 58), (152, 150, 92))
    m.mat("hole", (24, 20, 18), kind="mc")
    chest_art = ["." * 14] * 2 + ["...HHHHH......", "..HgHgHgH.....", "..HgHrHgH.....", "..HgHrHgH.....", "...HHrHH......", "......r.......",
                 "." * 14, "." * 14]
    P = dict(lw=5.5, ld=5.5, hx=3.4, shin=4, thigh=5, tw=14, td=9, pelvis=3, chest=10, aw=4.5, ua=5, fa=4, belly="fur2",
             left_hand="endo", head_rot=[-6, 0, -6], right_forearm_rot=[25, 0, 0], left_forearm_rot=[35, 0, 0],
             chest_paint={"north": pix(chest_art, {"H": (24, 20, 18), "g": (150, 150, 150), "r": (170, 30, 30)}, flat="")})
    a = body(m, P)
    rabbit(m, a, ["", "", ".KKK..KKK.", ".KKKK.KKKK", ".KWKK.KWKK"], {"K": K, "W": (236, 236, 210)}, "W", broken_ear=True, ragged=True,
           mouth_rows=["..NNN..", ".......", "g.....g", "TgTgTgT"])
    m.by_name["jaw"]["rot"] = [-14, 0, 0]
    N, L, td, tw = a["N"], a["L"], a["td"], a["tw"]
    for k, yy in enumerate((N - 2, N - 5.5)):
        fringe(m, "body", "fur", 0, 0, tw / 2 - 0.3, td / 2 - 0.3, yy, 12, drop=(1.2, 2.6), w=1.7, out=22, seed=60 + k)
    m.decal("body", "side_hole", [tw / 2 + 0.06, L + 5, 0], [3, 3], ("hole", dict(bars=1)), face="east")
    m.decal("left_leg", "leg_hole", [3.4, 9, -2.8], [2.6, 3], ("hole", dict(bars=2)))
    return m, dict(width=0.9, height=2.5, egg=(0x767C3A, 0x40381E))


def balloon_boy():
    m = Model("balloon_boy", seed=61, density=1)
    base_mats(m, (240, 206, 172))
    m.mat("shirt", (206, 40, 40), kind="mc", pattern="stripes_h", rgb2=(40, 70, 190), period=1.0)
    m.mat("pants", (44, 70, 182), kind="mc")
    m.mat("shoe", (92, 56, 30), kind="mc")
    m.mat("hat", (210, 40, 40), kind="mc", pattern="stripes_v", rgb2=(40, 80, 200), period=2.0)
    m.mat("prop", (245, 210, 40), kind="mc")
    m.mat("balloon", (226, 40, 40), kind="mc", pattern="stripes_v", rgb2=(245, 215, 40), period=1.0)
    m.mat("hair", (96, 58, 32), kind="mc")
    m.mat("sign", (240, 240, 230), kind="mc")
    m.mat("stick", (120, 80, 40), kind="mc")
    P = dict(lw=3, ld=3, hx=2, shin=3, thigh=3, tw=9, td=6, pelvis=2, chest=6, aw=3, ua=3, fa=3, foot_style="shoe",
             thigh_c="pants", shin_c="pants", foot_c="shoe", pelvis_c="pants", chest_c="shirt", upper_c="shirt",
             fore_c="fur", hand_c="fur", neck=1, fringe=False)
    a = body(m, P)
    y0 = a["y0"]
    m.box("head", "skull", "fur", [-5, y0, -5], [5, y0 + 9, 5],
          paint={"north": pix(["..........", "..........", "..........", ".WWW..WWW.", ".WBB..BBW.", ".WBK..KBW.",
                               "pp......pp", "..KTTTTK..", "...KKKK...", ".........."],
                              {"W": W, "B": (60, 120, 230), "K": (60, 20, 20), "T": W, "p": (240, 140, 140)}, glow="B")})
    m.box("head", "nose", "fur", [-0.7, y0 + 3, -5.8], [0.7, y0 + 4.2, -5])
    m.box("head", "hair", "hair", [-5.25, y0 + 6, -2], [5.25, y0 + 8, 5.25])
    for s in (1, -1):
        m.box("head", f"ear{s}", "fur", [s * 5 - 0.5, y0 + 3, -1], [s * 5 + 1, y0 + 6, 1])
    m.bone("jaw", "head", [0, y0, -3])
    m.box("jaw", "jaw", "fur", [-3, y0 - 1, -5.25], [3, y0, -2])
    m.box("head", "hat", "hat", [-5.5, y0 + 8, -5.5], [5.5, y0 + 11, 5.5])
    m.box("head", "hat_brim", "hat", [-3, y0 + 8, -7], [3, y0 + 8.5, -5.5])
    m.box("head", "prop_stem", "prop", [-0.5, y0 + 11, -0.5], [0.5, y0 + 13, 0.5])
    m.box("head", "prop_blade1", "prop", [-4, y0 + 13, -0.5], [4, y0 + 13.5, 0.5], rot=[0, 30, 0], origin=[0, y0 + 13, 0])
    m.box("head", "prop_blade2", "prop", [-4, y0 + 13, -0.5], [4, y0 + 13.5, 0.5], rot=[0, -60, 0], origin=[0, y0 + 13, 0])
    ax, top, s, fore = a["hands"]["right"]
    m.box(fore, "string", "black", [ax - 2.5, top - 1, -1.75], [ax - 2, top + 15, -1.25], rot=[0, 0, 10], origin=[ax, top, -1.5])
    m.box(fore, "balloon", "balloon", [ax - 7, top + 15, -4], [ax - 2, top + 21, 1])
    m.box(fore, "balloon_tie", "balloon", [ax - 5, top + 14, -2], [ax - 4, top + 15, -1])
    ax, top, s, fore = a["hands"]["left"]
    m.box(fore, "sign_stick", "stick", [ax - 0.5, top - 3, -2.5], [ax + 0.5, top + 6, -1.5])
    m.box(fore, "sign", "sign", [ax - 3.5, top + 5, -3], [ax + 3.5, top + 9, -2.5],
          paint={"north": pix([".......", "rbyrbyr", ".......", "......."], {"r": (220, 40, 40), "b": (40, 80, 200), "y": (230, 170, 20)}, flat="")})
    return m, dict(width=0.6, height=1.6, egg=(0xCE2828, 0x2C46B6))


def puppet():
    m = Model("puppet", seed=71, density=1)
    base_mats(m, (24, 24, 28))
    m.mat("mask", (242, 242, 240), kind="mc")
    stripes = pix(["K", "W", "K", "W", "K", "W"], {"K": (24, 24, 28), "W": W})
    P = dict(lw=2, ld=2, hx=1.5, shin=9, thigh=8, foot_h=1, tw=7, td=5, pelvis=2, chest=11, aw=2, ua=8, fa=8, neck=3, fringe=False,
             fore_paint={f: pix(["."] * 5 + ["K", "W", "K", "W", "K"], {"K": (24, 24, 28), "W": W}) for f in ("north", "south", "east", "west")},
             chest_paint={"north": pix([".......", "...W...", ".......", "...W...", ".......", "...W...", "......."] + ["......."] * 4, {"W": W})})
    a = body(m, P)
    y0 = a["y0"]
    for side, s in (("left", 1), ("right", -1)):
        m.box(f"{side}_leg", "cuff", "fur", [s * 1.5 - 1.25, 1, -1.25], [s * 1.5 + 1.25, 4, 1.25], paint={f: stripes for f in ("north", "south", "east", "west")})
    m.box("head", "skull", "fur", [-3.5, y0, -3.5], [3.5, y0 + 8, 3.5])
    m.box("head", "mask", "mask", [-3.5, y0 + 0.5, -4], [3.5, y0 + 7.5, -3.5],
          paint={"north": pix([".......", ".K...K.", "KWK.KWK", ".K...K.", "rp...pr", ".p...p.", "..RRR..", "...R..."],
                              {"K": (10, 10, 12), "W": W, "p": (130, 60, 160), "r": (205, 36, 50), "R": (200, 30, 40)}, glow="W")})
    m.bone("jaw", "head", [0, y0, -2])
    m.box("jaw", "jaw", "mask", [-1.5, y0 - 0.5, -4], [1.5, y0 + 0.5, -2.5])
    return m, dict(width=0.6, height=2.7, egg=(0x16161A, 0xE8E8E8))


def endoskeleton():
    m = Model("endoskeleton", seed=81, density=1, grime=0.3)
    base_mats(m, (150, 150, 156), (110, 110, 116))
    P = dict(lw=2, ld=2, hx=2.5, shin=5, thigh=5, tw=8, td=4, pelvis=2, chest=10, aw=2, ua=6, fa=5, neck=2, fringe=False,
             thigh_c="endo_l", endo_shin=True, foot_style="endo", pelvis_c="endo", chest_c="endo", upper_c="endo_l", fore_c="endo_l",
             left_hand="endo", right_hand="endo",
             chest_paint={f: pix(["........", "gggggggg", "........", "gggggggg", "........", "gggggggg", "........", "gggggggg", "........", "........"],
                                 {"g": (176, 176, 182)}) for f in ("north", "south")})
    a = body(m, P)
    y0 = a["y0"]
    m.box("head", "skull", "endo_l", [-4, y0 + 1, -3.5], [4, y0 + 7, 4],
          paint={"north": pix(["........", "........", ".WW..WW.", ".WR..RW.", "........", "........"], {"W": W, "R": (235, 30, 30)}, glow="R")})
    m.box("head", "teeth", "teeth", [-3, y0, -4], [3, y0 + 1.5, -3])
    m.bone("jaw", "head", [0, y0 + 1, -1])
    m.box("jaw", "jaw", "endo_l", [-3.5, y0 - 1, -4.5], [3.5, y0, -0.5], paint={"north": pix(["TTTTTTT"], {"T": TOOTH}, flat="T")})
    for s in (1, -1):
        m.box("head", f"ear_post_{s}", "endo", [s * 3 - 0.5, y0 + 7, -0.5], [s * 3 + 0.5, y0 + 9, 0.5])
        m.box("head", f"ear_{s}", "endo_l", [s * 3 - 1, y0 + 9, -1], [s * 3 + 1, y0 + 11, 0])
    return m, dict(width=0.7, height=2.3, egg=(0x76767C, 0xEB1E1E))


CHARACTERS = [freddy, bonnie, chica, foxy, golden_freddy, springtrap, balloon_boy, puppet, endoskeleton]
