"""FNAF 1 night layout on the downloaded map: animatronic route nodes and security cameras.

    python tools/pizzeria/night_layout.py

Reads the map collision (data/fnaf/map/fnaf1.fcol) to put every node on the floor it stands on (the stage
is raised) and writes data/fnaf/pizzeria/night.json (map block coordinates; the game adds the pizzeria
origin). Used by NightManager on the server and by the camera tablet on the client. Also draws the
camera map texture (assets/fnaf/textures/gui/cam_map.png) from the map walls.
"""
import gzip
import json
import math
import os
import struct

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COL = os.path.join(ROOT, "src", "main", "resources", "data", "fnaf", "map", "fnaf1.fcol")
OUT = os.path.join(ROOT, "src", "main", "resources", "data", "fnaf", "pizzeria", "night.json")
GUI = os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf", "textures", "gui")

# name: (x, z, yaw) - yaw 0 looks south, 90 west, 180 north, -90 east
NODES = {
    "stage_freddy": (25.5, 11.5, 0), "stage_bonnie": (22.5, 11.5, 0), "stage_chica": (28.5, 11.5, 0),
    "dining_w": (15.5, 19.5, -30), "dining_c": (25.5, 25.5, 0), "dining_e": (35.5, 19.5, 30),
    "backstage": (7.5, 19.5, -90), "supply": (12.5, 33.5, -45),
    "w_hall": (21.2, 33.5, 0), "w_corner": (21.2, 43.6, 170), "left_door": (22.3, 40.9, -90),
    "e_hall": (29.3, 33.5, 0), "e_corner": (29.3, 43.6, -170), "right_door": (28.7, 40.9, 90),
    "restrooms": (42.0, 18.5, 0), "kitchen": (42.0, 27.5, 0),
    "cove_in": (12.5, 27.5, -90), "cove_peek": (14.2, 28.0, -90), "cove_out": (16.0, 29.5, -70),
    "foxy_run": (21.2, 31.4, 0),
    "office_left": (24.0, 41.6, -90), "office_right": (26.8, 41.6, 90),
}

# id: (label, x, y, z, target x, target z, pitch); None position = audio only
CAMERAS = [
    ("1A", "Show Stage", (25.5, 4.3, 18.5), (25.5, 11.5), 22),
    ("1B", "Dining Area", (38.5, 4.3, 28.5), (25.0, 20.0), 22),
    ("1C", "Pirate Cove", (18.5, 4.0, 23.5), (12.5, 28.0), 18),
    ("5", "Backstage", (10.5, 4.0, 12.0), (7.0, 20.0), 25),
    ("3", "Supply Closet", (14.6, 3.6, 35.6), (12.0, 32.0), 30),
    ("2A", "West Hall", (21.2, 3.9, 31.8), (21.2, 40.0), 12),
    ("2B", "W. Hall Corner", (22.4, 4.3, 37.2), (21.2, 43.6), 30),
    ("4A", "East Hall", (29.3, 3.9, 31.8), (29.3, 40.0), 12),
    ("4B", "E. Hall Corner", (28.4, 4.3, 37.2), (29.3, 43.6), 30),
    ("6", "Kitchen", None, (42.0, 27.5), 0),
    ("7", "Restrooms", (42.0, 4.3, 15.0), (42.0, 24.0), 25),
]


def load_collision():
    d = gzip.open(COL).read()
    _, n = struct.unpack(">ii", d[4:12])
    p = 12
    col = {}
    for _ in range(n):
        x, y, z, f = struct.unpack(">hhhb", d[p:p + 7])
        p += 7
        bs = []
        for k in range(2):
            c = d[p]
            p += 1
            for _ in range(c):
                b = struct.unpack(">6b", d[p:p + 6])
                p += 6
                if k == 0:
                    bs.append(b)
        col[(x, y, z)] = (f, bs)
    return col


def floor_height(col, x, z):
    """Top of whatever is under the centre of column (x, z), starting from the ground floor (y = 1)."""
    cx, cz = int(math.floor(x)), int(math.floor(z))
    y = 1
    top = 0.0
    while y < 5:
        _, bs = col.get((cx, y, cz), (0, []))
        under = [b for b in bs if b[0] < 12 and b[3] > 4 and b[2] < 12 and b[5] > 4]
        if not under:
            break
        t = max(b[4] for b in under) / 16
        top = y + t
        if t < 1.0:
            break
        y += 1
    return round(max(1.0, top), 3)


def yaw_to(src, dst):
    dx, dz = dst[0] - src[0], dst[1] - src[1]
    return round(math.degrees(math.atan2(-dx, dz)), 1)


def cam_map(col):
    """FNAF-style camera map: thin light walls on dark, drawn from the map's wall cells."""
    os.makedirs(GUI, exist_ok=True)
    s = 8
    im = Image.new("RGBA", (48 * s, 48 * s), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    for (x, y, z), (f, bs) in col.items():
        if y != 2:
            continue
        for b in bs:
            if b[4] - b[1] < 8:
                continue
            x0, x1 = x + b[0] / 16, x + b[3] / 16
            z0, z1 = z + b[2] / 16, z + b[5] / 16
            dr.rectangle([x0 * s, z0 * s, max(x0 * s + 1, x1 * s), max(z0 * s + 1, z1 * s)], fill=(200, 200, 200, 230))
    im.save(os.path.join(GUI, "cam_map.png"))


def main():
    col = load_collision()
    nodes = {k: [x, floor_height(col, x, z), z, yaw] for k, (x, z, yaw) in NODES.items()}
    cams = []
    for cid, label, pos, target, pitch in CAMERAS:
        e = {"id": cid, "label": label, "target": list(target)}
        if pos:
            e.update(pos=list(pos), yaw=yaw_to((pos[0], pos[2]), target), pitch=pitch)
        cams.append(e)
    with open(OUT, "w") as f:
        json.dump({"nodes": nodes, "cameras": cams, "map_size": 48}, f, indent=1)
    cam_map(col)
    for k, v in nodes.items():
        print(f"{k:14s} {v}")


if __name__ == "__main__":
    main()
