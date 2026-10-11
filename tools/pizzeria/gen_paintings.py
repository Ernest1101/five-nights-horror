"""Painting textures for the pizzeria (32 px per block).

Posters use transparent renders of the in-game 3D models (made in Blender), the rest is drawn here.
    python tools/pizzeria/gen_paintings.py <render_dir>
"""
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf", "textures", "painting")
PX = 32
rnd = random.Random(3)


def font(size, bold=True):
    for name in ("impact.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(os.path.join("C:\\Windows\\Fonts", name), size)
        except OSError:
            continue
    return ImageFont.load_default()


def outlined(d, xy, text, f, fill, outline=(0, 0, 0), w=4, anchor="mm"):
    for dx in range(-w, w + 1):
        for dy in range(-w, w + 1):
            if dx * dx + dy * dy <= w * w:
                d.text((xy[0] + dx, xy[1] + dy), text, font=f, fill=outline, anchor=anchor)
    d.text(xy, text, font=f, fill=fill, anchor=anchor)


def fit(img, box_w, box_h):
    bb = img.getbbox()
    img = img.crop(bb) if bb else img
    s = min(box_w / img.width, box_h / img.height)
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)


def finish(big, blocks_w, blocks_h, name):
    os.makedirs(OUT, exist_ok=True)
    small = big.resize((blocks_w * PX, blocks_h * PX), Image.LANCZOS).filter(ImageFilter.UnsharpMask(1.2, 80, 2))
    small.convert("RGB").save(os.path.join(OUT, name + ".png"))


def confetti(d, w, h, n):
    for _ in range(n):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        c = rnd.choice([(240, 60, 60), (250, 210, 40), (60, 140, 240), (90, 210, 90), (220, 80, 220), (250, 250, 250)])
        r = rnd.uniform(4, 10)
        if rnd.random() < 0.5:
            d.ellipse([x - r, y - r, x + r, y + r], fill=c)
        else:
            pts = [(x + r * (1 if i % 2 == 0 else 0.45) * __import__("math").cos(i * 0.6283 - 1.57),
                    y + r * (1 if i % 2 == 0 else 0.45) * __import__("math").sin(i * 0.6283 - 1.57)) for i in range(10)]
            d.polygon(pts, fill=c)


def celebrate(render):
    W, H = 1280, 960
    img = Image.new("RGBA", (W, H), (14, 12, 22, 255))
    d = ImageDraw.Draw(img)
    confetti(d, W, H, 140)
    group = fit(Image.open(render).convert("RGBA"), W * 0.95, H * 0.7)
    img.alpha_composite(group, ((W - group.width) // 2, H - group.height - 10))
    outlined(d, (W // 2, 120), "CELEBRATE!", font(190), (255, 220, 40), (150, 20, 20), 9)
    d.rectangle([0, 0, W - 1, H - 1], outline=(200, 40, 40), width=18)
    finish(img, 4, 3, "celebrate")


def freddy_poster(render):
    W, H = 640, 960
    img = Image.new("RGBA", (W, H), (36, 20, 14, 255))
    d = ImageDraw.Draw(img)
    for y in range(0, H, 24):
        d.line([0, y, W, y], fill=(48, 28, 18, 255), width=10)
    fr = fit(Image.open(render).convert("RGBA"), W * 0.95, H * 0.72)
    img.alpha_composite(fr, ((W - fr.width) // 2, H - fr.height - 20))
    outlined(d, (W // 2, 80), "FREDDY", font(120), (255, 210, 60), (60, 20, 10), 7)
    outlined(d, (W // 2, 180), "FAZBEAR'S PIZZA", font(64), (255, 255, 255), (60, 20, 10), 5)
    d.rectangle([0, 0, W - 1, H - 1], outline=(250, 200, 60), width=14)
    finish(img, 2, 3, "freddy_poster")


def golden_poster(render):
    W, H = 640, 960
    img = Image.new("RGBA", (W, H), (8, 6, 4, 255))
    face = fit(Image.open(render).convert("RGBA"), W * 1.15, H * 0.95)
    dark = Image.new("RGBA", face.size, (0, 0, 0, 0))
    face = Image.blend(face, dark, 0.15)
    img.alpha_composite(face, ((W - face.width) // 2, (H - face.height) // 2 + 40))
    d = ImageDraw.Draw(img)
    for _ in range(900):
        x, y = rnd.randrange(W), rnd.randrange(H)
        g = rnd.randrange(30, 120)
        d.point((x, y), fill=(g, g, g, 255))
    outlined(d, (W // 2, 90), "IT'S ME", font(110), (150, 20, 20), (0, 0, 0), 5)
    finish(img, 2, 3, "golden_poster")


def rules():
    W, H = 640, 960
    img = Image.new("RGBA", (W, H), (226, 220, 196, 255))
    d = ImageDraw.Draw(img)
    outlined(d, (W // 2, 90), "RULES FOR", font(96), (180, 30, 30), (90, 10, 10), 3)
    outlined(d, (W // 2, 190), "SAFETY", font(110), (180, 30, 30), (90, 10, 10), 3)
    f = font(36, False)
    lines = ["1. No running", "2. No yelling", "3. No screaming", "4. No hitting", "5. Don't touch", "   the animatronics",
             "6. Stay with an adult", "7. Have fun!"]
    for i, ln in enumerate(lines):
        d.text((60, 300 + i * 70), ln, font=f, fill=(40, 30, 30))
    d.rectangle([0, 0, W - 1, H - 1], outline=(120, 100, 70), width=16)
    for _ in range(40):
        x, y, r = rnd.randrange(W), rnd.randrange(H), rnd.randrange(8, 30)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(200, 190, 160, 255) if rnd.random() < 0.7 else (150, 120, 90, 255))
    finish(img, 2, 3, "rules")


def drawing(i, body, accent, ears):
    W = H = 512
    img = Image.new("RGBA", (W, H), (246, 244, 236, 255))
    d = ImageDraw.Draw(img)

    def crayon(pts, col, width=14):
        jit = [(x + rnd.uniform(-5, 5), y + rnd.uniform(-5, 5)) for x, y in pts]
        d.line(jit + [jit[0]], fill=col, width=width, joint="curve")

    import math
    cx, cy = 256, 230
    ring = [(cx + 120 * math.cos(a / 16 * 6.283), cy + 110 * math.sin(a / 16 * 6.283)) for a in range(16)]
    d.polygon(ring, fill=body)
    crayon(ring, (40, 30, 30))
    if ears == "bear":
        for sx in (-1, 1):
            e = [(cx + sx * 100 + 40 * math.cos(a / 10 * 6.283), cy - 110 + 40 * math.sin(a / 10 * 6.283)) for a in range(10)]
            d.polygon(e, fill=body)
            crayon(e, (40, 30, 30), 10)
    elif ears == "bunny":
        for sx in (-1, 1):
            e = [(cx + sx * 50 - 22, cy - 90), (cx + sx * 60, cy - 260), (cx + sx * 50 + 22, cy - 90)]
            d.polygon(e, fill=body)
            crayon(e, (40, 30, 30), 10)
    elif ears == "fox":
        for sx in (-1, 1):
            e = [(cx + sx * 40, cy - 90), (cx + sx * 110, cy - 200), (cx + sx * 115, cy - 70)]
            d.polygon(e, fill=body)
            crayon(e, (40, 30, 30), 10)
    elif ears == "chick":
        crayon([(cx - 10, cy - 105), (cx, cy - 160), (cx + 15, cy - 105)], (250, 200, 30), 16)
    for sx in (-1, 1):
        d.ellipse([cx + sx * 45 - 22, cy - 40, cx + sx * 45 + 22, cy + 4], fill=(255, 255, 255))
        d.ellipse([cx + sx * 45 - 9, cy - 26, cx + sx * 45 + 9, cy - 8], fill=accent)
    d.chord([cx - 60, cy + 10, cx + 60, cy + 80], 0, 180, fill=(40, 20, 20))
    for t in range(5):
        d.line([cx - 50 + t * 25, cy + 45, cx - 50 + t * 25, cy + 60], fill=(255, 255, 255), width=8)
    # stick-figure kid holding a balloon
    kx = 420
    crayon([(kx, 360), (kx, 450)], (40, 30, 30), 8)
    d.ellipse([kx - 25, 310, kx + 25, 360], outline=(40, 30, 30), width=8)
    crayon([(kx - 40, 390), (kx + 40, 390)], (40, 30, 30), 8)
    crayon([(kx, 450), (kx - 30, 500)], (40, 30, 30), 8)
    crayon([(kx, 450), (kx + 30, 500)], (40, 30, 30), 8)
    d.line([kx + 40, 390, kx + 60, 300], fill=(60, 60, 60), width=4)
    d.ellipse([kx + 30, 240, kx + 90, 305], fill=rnd.choice([(240, 60, 60), (60, 140, 240), (250, 210, 40)]))
    d.rectangle([0, 0, W - 1, H - 1], outline=(200, 190, 170), width=10)
    finish(img, 1, 1, f"drawing{i}")


def main(render_dir):
    celebrate(os.path.join(render_dir, "p_celebrate.png"))
    freddy_poster(os.path.join(render_dir, "p_freddy.png"))
    golden_poster(os.path.join(render_dir, "p_golden.png"))
    rules()
    drawing(1, (130, 76, 34), (60, 120, 230), "bear")
    drawing(2, (90, 80, 190), (220, 40, 140), "bunny")
    drawing(3, (240, 210, 40), (150, 60, 200), "chick")
    drawing(4, (190, 50, 40), (250, 200, 40), "fox")
    print("ok")


if __name__ == "__main__":
    main(sys.argv[1])
