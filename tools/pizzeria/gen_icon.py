"""Finishes the mod icon from the Blender render (tools/blender/mod_icon.py -> blender/icon/icon_raw.png):
crop on the face, dark red grade, vignette, film grain, CCTV scanlines and static, title.

    python tools/pizzeria/gen_icon.py

Writes src/main/resources/assets/fnaf/icon.png (in-game mod list, no text) and
blender/icon/avatar_curseforge.png + avatar_square.png (with the title, for CurseForge / Discord).
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "blender", "icon", "icon_raw.png")
OUT = os.path.join(ROOT, "blender", "icon")
rng = np.random.default_rng(1987)


FONTS = os.path.join(ROOT, "tools", "fonts")       # Google Fonts (OFL / Apache), see tools/fonts/README.txt


def font(size, names=("impact.ttf", "arialbd.ttf")):
    for n in names:
        for d in (FONTS, r"C:\Windows\Fonts"):
            try:
                return ImageFont.truetype(os.path.join(d, n), size)
            except OSError:
                pass
    return ImageFont.load_default()


def fit(text, names, max_w, max_h):
    """Largest font size that fits the box."""
    size = max_h
    while size > 10:
        f = font(size, names)
        l, t, r, b = f.getbbox(text)
        if r - l <= max_w and b - t <= max_h:
            return size
        size -= 4
    return size


def grade(im):
    a = np.asarray(im.convert("RGB")).astype(np.float64) / 255
    h, w, _ = a.shape
    # contrast + crush the blacks, push the shadows to red
    lum = a.mean(axis=2, keepdims=True)
    a = np.clip((a - 0.04) * 1.25, 0, 1) ** 1.15
    a = a * (1 - 0.25 * (1 - lum)) + np.array([0.10, 0.0, 0.0]) * (1 - lum) * 0.35
    a = a * 0.8 + lum * np.array([1.0, 0.75, 0.7]) * 0.2        # slightly desaturated, warm
    # vignette
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - w * 0.5) / (w * 0.5), (yy - h * 0.46) / (h * 0.5))
    a *= np.clip(1.25 - 0.85 * r ** 1.6, 0.05, 1)[..., None]
    # film grain
    a += (rng.random((h, w, 1)) - 0.5) * 0.07
    # CCTV scanlines
    a[::4] *= 0.86
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def static_bands(im, n=5):
    d = ImageDraw.Draw(im, "RGBA")
    w, h = im.size
    for _ in range(n):
        y = int(rng.integers(0, h))
        bh = int(rng.integers(1, 4))
        d.rectangle([0, y, w, y + bh], fill=(255, 255, 255, int(rng.integers(18, 45))))
    # torn line: shift a strip sideways
    y = int(h * 0.7)
    strip = im.crop((0, y, w, y + 10))
    im.paste(strip, (int(w * 0.03), y))
    return im


def glitch_text(im, text, cx, cy, size, color=(225, 20, 20), names=("impact.ttf",)):
    f = font(size, names)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # chromatic split + dark outline for readability
    for dx, col in ((-4, (0, 200, 255, 110)), (4, (255, 0, 40, 140))):
        d.text((cx + dx, cy), text, font=f, fill=col, anchor="mm")
    d.text((cx, cy), text, font=f, fill=color + (255,), anchor="mm", stroke_width=max(3, size // 22), stroke_fill=(0, 0, 0, 255))
    im = Image.alpha_composite(im.convert("RGBA"), layer)
    return im


# (top line font, bottom line font, camera HUD font)
STYLE = (("Anton-Regular.ttf",), ("Nosifer-Regular.ttf",), ("VT323-Regular.ttf",))
VARIANTS = {
    "A_bebas_creepster": (("BebasNeue-Regular.ttf",), ("Creepster-Regular.ttf",), ("VT323-Regular.ttf",)),
    "B_anton_nosifer": (("Anton-Regular.ttf",), ("Nosifer-Regular.ttf",), ("VT323-Regular.ttf",)),
    "C_rubik_glitch": (("RubikGlitch-Regular.ttf",), ("RubikGlitch-Regular.ttf",), ("ShareTechMono-Regular.ttf",)),
    "D_elite_butcherman": (("SpecialElite-Regular.ttf",), ("Butcherman-Regular.ttf",), ("VT323-Regular.ttf",)),
    "E_bebas_eater": (("BebasNeue-Regular.ttf",), ("Eater-Regular.ttf",), ("ShareTechMono-Regular.ttf",)),
    "F_pixel": (("PressStart2P-Regular.ttf",), ("PressStart2P-Regular.ttf",), ("VT323-Regular.ttf",)),
    "G_metal": (("Anton-Regular.ttf",), ("MetalMania-Regular.ttf",), ("VT323-Regular.ttf",)),
}


def avatar(base, path, top_font, bottom_font, hud_font):
    av = base.copy()
    d = ImageDraw.Draw(av, "RGBA")
    d.rectangle([0, 790, 1024, 1024], fill=(0, 0, 0, 150))
    av = glitch_text(av, "FIVE NIGHTS", 512, 852, fit("FIVE NIGHTS", top_font, 820, 100), (235, 235, 235), top_font)
    av = glitch_text(av, "HORROR", 512, 950, fit("HORROR", bottom_font, 900, 140), (220, 18, 18), bottom_font)
    d = ImageDraw.Draw(av, "RGBA")
    d.ellipse([44, 44, 80, 80], fill=(230, 20, 20, 255))
    d.text((96, 62), "REC", font=font(60, hud_font), fill=(235, 235, 235, 255), anchor="lm")
    d.text((980, 62), "12 AM", font=font(68, hud_font), fill=(235, 235, 235, 255), anchor="rm")
    av.convert("RGB").save(path, optimize=True)


def main():
    raw = Image.open(RAW).convert("RGB")
    s = raw.size[0]
    # face from the hat to the bow tie
    box = (int(s * 0.08), int(s * 0.07), int(s * 0.92), int(s * 0.91))
    face = raw.crop(box).resize((1024, 1024), Image.LANCZOS)
    base = static_bands(grade(face))
    # the eyes glint in the dark
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for ex, ey in ((0.38, 0.425), (0.585, 0.425)):
        x, y = ex * 1024, ey * 1024
        gd.ellipse([x - 26, y - 26, x + 26, y + 26], fill=(180, 210, 255, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    base = Image.alpha_composite(base.convert("RGBA"), glow)

    icon = base.resize((512, 512), Image.LANCZOS).convert("RGB")
    icon.save(os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf", "icon.png"), optimize=True)

    avatar(base, os.path.join(OUT, "avatar_curseforge.png"), *STYLE)
    Image.open(os.path.join(OUT, "avatar_curseforge.png")).resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "avatar_512.png"))
    print("ok")


def variants():
    """Contact sheet of the title font options (blender/icon/variants.png)."""
    main()
    base = Image.open(os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf", "icon.png")).resize((1024, 1024))
    tiles = []
    for name, st in VARIANTS.items():
        p = os.path.join(OUT, f"variant_{name}.png")
        avatar(base.convert("RGBA"), p, *st)
        im = Image.open(p).resize((400, 400), Image.LANCZOS)
        ImageDraw.Draw(im).text((8, 380), name, font=font(18, ("arialbd.ttf",)), fill=(255, 255, 0))
        tiles.append(im)
    sheet = Image.new("RGB", (4 * 400, 2 * 400), (30, 30, 30))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 4) * 400, (i // 4) * 400))
    sheet.save(os.path.join(OUT, "variants.png"))


if __name__ == "__main__":
    import sys
    variants() if "variants" in sys.argv else main()
