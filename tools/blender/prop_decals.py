"""Decal images for tools/blender/props.py (Blender's Python has no PIL). Run with normal Python first."""
import os

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "blender", "renders")


def font(size):
    for n in ("impact.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", n), size)
        except OSError:
            pass
    return ImageFont.load_default()


def draw_panel(img, d, font):
    W, H = img.size
    d.rectangle([0, 0, W, H], fill=(30, 32, 34))
    d.rectangle([6, 6, W - 7, 44], fill=(200, 160, 20))
    d.text((W // 2, 25), "FAZBEAR ENT. 5500W", font=font(26), fill=(20, 20, 20), anchor="mm")
    for i, x in enumerate((70, 190)):
        d.rounded_rectangle([x - 46, 70, x + 46, 170], 10, fill=(225, 225, 215))
        for sx in (-14, 14):
            d.rectangle([x + sx - 4, 100, x + sx + 4, 124], fill=(30, 30, 30))
        d.ellipse([x - 7, 136, x + 7, 150], fill=(30, 30, 30))
    d.text((W - 70, 80), "120V", font=font(22), fill=(230, 230, 230), anchor="mm")
    d.rectangle([W - 108, 100, W - 32, 170], fill=(15, 15, 15))
    d.rectangle([W - 100, 108, W - 40, 162], fill=(170, 30, 25))
    d.text((W - 70, 135), "ON/OFF", font=font(16), fill=(240, 240, 240), anchor="mm")
    d.text((W // 2, H - 22), "! WARNING  CARBON MONOXIDE  DO NOT USE INDOORS !", font=font(15), fill=(240, 200, 30),
           anchor="mm")

def draw_tank(img, d, font):
    W, H = img.size
    d.rectangle([0, 0, W, H], fill=(150, 22, 18))
    d.text((W // 2, H // 2 - 10), "FAZBEAR", font=font(70), fill=(245, 245, 240), anchor="mm")
    d.text((W // 2, H // 2 + 46), "POWER  SYSTEMS", font=font(30), fill=(20, 20, 20), anchor="mm")



def make(name, w, h, fn):
    img = Image.new("RGB", (w, h))
    fn(img, ImageDraw.Draw(img), font)
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, name))


if __name__ == "__main__":
    make("gen_panel_decal.png", 512, 256, draw_panel)
    make("gen_tank_decal.png", 512, 192, draw_tank)
