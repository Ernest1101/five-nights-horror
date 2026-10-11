"""Petrol can (jerry can) for the blackout refuelling: textures, block model, blockstate and item model.

    python tools/pizzeria/gen_gascan.py

The can stands upright, its thin side along X (front of the block = south, like every facing decor block).
"""
import numpy as np
from PIL import Image, ImageDraw

import gen_decor as gd
from gen_textures import S, apply_dirt, canvas, fbm, font, grain, rng, scuffs


def red_paint():
    img = canvas((168, 30, 24))
    img *= (0.88 + 0.2 * fbm(5, 4))[..., None]
    img = scuffs(img, 22, (120, 116, 108), 0.55, (2, 6))       # paint chipped down to bare metal
    img = apply_dirt(img, 0.35, 3, (52, 40, 30))
    return img * grain(0.06)[..., None]


def side():
    img = red_paint()
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    m = 6
    # pressed rim around the panel
    d.rectangle([m - 2, m - 2, S - m + 1, S - m + 1], outline=(110, 18, 14), width=2)
    d.rectangle([m, m, S - m - 1, S - m - 1], outline=(206, 60, 48), width=1)
    # the embossed X of a jerry can: light edge on top, dark edge below
    for (x1, y1, x2, y2) in ((m + 3, m + 3, S - m - 4, S - m - 4), (S - m - 4, m + 3, m + 3, S - m - 4)):
        d.line([x1, y1 + 2, x2, y2 + 2], fill=(96, 14, 10), width=3)
        d.line([x1, y1, x2, y2], fill=(214, 70, 56), width=3)
        d.line([x1, y1 + 1, x2, y2 + 1], fill=(182, 40, 30), width=2)
    # stencilled label
    f = font(11)
    d.rectangle([S // 2 - 15, S - 21, S // 2 + 15, S - 9], fill=(226, 190, 40))
    d.text((S // 2, S - 15), "FUEL", font=f, fill=(24, 18, 12), anchor="mm")
    img = np.asarray(im).astype(np.float64)
    img = apply_dirt(img, 0.22, 4, (40, 30, 22))
    # dark petrol stains running down from the spout
    for _ in range(4):
        x = int(rng.integers(S // 2, S - 8))
        h = int(rng.integers(10, 30))
        img[:h, x:x + 2] *= 0.72
    return img


def edge():
    img = red_paint()
    img[:, S // 2 - 1:S // 2 + 1] *= 0.7               # weld seam
    return img


def handle():
    return gd.metal((120, 22, 18), 10, 0.3, brushed=False)


def cap():
    img = gd.plastic((38, 36, 34), 0.25)
    img[:, ::6] *= 0.8                                 # ribbed grip
    return img


def model():
    t = "#side", "#edge", "#handle", "#cap"
    body = gd.el((5.5, 0, 3), (10.5, 12, 13), {"east": t[0], "west": t[0], "north": t[1], "south": t[1], "up": t[1], "down": t[1]},
                 uv={"east": [0, 0, 16, 16], "west": [0, 0, 16, 16]})
    seam = gd.el((7.6, 12, 3), (8.4, 12.5, 10.5), t[1], ("north", "south", "east", "west", "up"))
    handle = [gd.el((7.2, 14, 3.6), (8.8, 15.2, 10.4), t[2]),
              gd.el((7.2, 12, 3.6), (8.8, 14, 4.8), t[2], ("north", "south", "east", "west")),
              gd.el((7.2, 12, 6.4), (8.8, 14, 7.6), t[2], ("north", "south", "east", "west")),
              gd.el((7.2, 12, 9.2), (8.8, 14, 10.4), t[2], ("north", "south", "east", "west"))]
    tilt = {"angle": 22.5, "axis": "x", "origin": [8, 12, 11.8]}
    spout = [gd.el((6.9, 11.5, 10.9), (9.1, 14, 12.7), t[1], rot=tilt),
             gd.el((6.6, 14, 10.6), (9.4, 15.4, 13), t[3], rot=tilt)]
    gd.model("gas_can", {"particle": "fnaf:block/gas_can_side", "side": "fnaf:block/gas_can_side",
                         "edge": "fnaf:block/gas_can_edge", "handle": "fnaf:block/gas_can_handle", "cap": "fnaf:block/gas_can_cap"},
             [body, seam, *handle, *spout])
    gd.facing_state("gas_can")
    gd.item("gas_can", gui_scale=0.75)


if __name__ == "__main__":
    for name, fn in (("gas_can_side", side), ("gas_can_edge", edge), ("gas_can_handle", handle), ("gas_can_cap", cap)):
        gd.save(name, fn())
    model()
    print("ok")
