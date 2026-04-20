"""Generate 64x64 skill-card icons + Facebook/Roblox social icons via Pillow.

Each skill card shows a distinct sigil on a dark parchment background with a
gold border, so the 8 cards read as a matched set in the inventory. Social
icons are simple branded tiles used in the Credits screen of the GUI form.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 64
OUT = Path(__file__).resolve().parent.parent / "resource_pack" / "textures" / "items"
OUT.mkdir(parents=True, exist_ok=True)


def card_base() -> Image.Image:
    """Dark parchment rectangle with a glowing gold rim."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Outer shadow
    d.rounded_rectangle([2, 2, SIZE - 2, SIZE - 2], radius=6, fill=(14, 10, 6, 255))
    # Inner parchment
    d.rounded_rectangle([5, 5, SIZE - 5, SIZE - 5], radius=5, fill=(38, 28, 20, 255))
    # Inner lighter gradient
    for y in range(8, SIZE - 8):
        t = (y - 8) / (SIZE - 16)
        r = int(46 + t * 12)
        g = int(34 + t * 10)
        b = int(24 + t * 6)
        d.line([(8, y), (SIZE - 8, y)], fill=(r, g, b, 255))
    # Gold border
    d.rounded_rectangle([5, 5, SIZE - 5, SIZE - 5], radius=5, outline=(210, 170, 60, 255), width=1)
    d.rounded_rectangle([4, 4, SIZE - 4, SIZE - 4], radius=6, outline=(120, 90, 30, 220), width=1)
    return img


def draw_sigil(img: Image.Image, draw_fn) -> Image.Image:
    sigil_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(sigil_layer)
    draw_fn(d, sigil_layer)
    # Soft glow
    glow = sigil_layer.filter(ImageFilter.GaussianBlur(2.2))
    out = Image.alpha_composite(img, glow)
    out = Image.alpha_composite(out, sigil_layer)
    return out


def sigil_primary(d, _layer):
    # Four-point star, centered
    cx, cy = SIZE // 2, SIZE // 2
    d.polygon([(cx, cy - 18), (cx + 5, cy - 3), (cx + 18, cy),
               (cx + 5, cy + 3), (cx, cy + 18), (cx - 5, cy + 3),
               (cx - 18, cy), (cx - 5, cy - 3)],
              fill=(255, 230, 140, 255), outline=(255, 255, 220, 255))
    d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(255, 255, 230, 255))


def sigil_bastion(d, _layer):
    # Shield
    cx, cy = SIZE // 2, SIZE // 2
    d.polygon([(cx - 14, cy - 14), (cx + 14, cy - 14), (cx + 14, cy + 4),
               (cx, cy + 18), (cx - 14, cy + 4)],
              fill=(190, 200, 210, 255), outline=(250, 250, 255, 255))
    d.line([(cx, cy - 10), (cx, cy + 12)], fill=(120, 130, 150, 255), width=2)
    d.line([(cx - 10, cy - 4), (cx + 10, cy - 4)], fill=(120, 130, 150, 255), width=2)


def sigil_skyfall(d, _layer):
    # Downward triangle (meteor) + trail
    cx, cy = SIZE // 2, SIZE // 2
    d.polygon([(cx, cy + 12), (cx - 10, cy - 8), (cx + 10, cy - 8)],
              fill=(255, 140, 60, 255), outline=(255, 220, 140, 255))
    d.line([(cx - 6, cy - 10), (cx - 12, cy - 22)], fill=(255, 200, 100, 255), width=2)
    d.line([(cx + 4, cy - 10), (cx + 10, cy - 22)], fill=(255, 200, 100, 255), width=2)
    d.line([(cx, cy - 12), (cx, cy - 26)], fill=(255, 240, 170, 255), width=2)


def sigil_root(d, _layer):
    # Branching roots going downward
    cx, cy = SIZE // 2, SIZE // 2 - 4
    d.line([(cx, cy), (cx, cy + 18)], fill=(120, 200, 120, 255), width=3)
    d.line([(cx, cy + 6), (cx - 10, cy + 16)], fill=(120, 200, 120, 255), width=2)
    d.line([(cx, cy + 10), (cx + 12, cy + 18)], fill=(120, 200, 120, 255), width=2)
    d.line([(cx - 10, cy + 16), (cx - 14, cy + 22)], fill=(80, 150, 90, 255), width=2)
    d.line([(cx + 12, cy + 18), (cx + 16, cy + 22)], fill=(80, 150, 90, 255), width=2)
    d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(220, 255, 220, 255))


def sigil_slipstream(d, _layer):
    # Wing-like swoosh
    cx, cy = SIZE // 2, SIZE // 2
    for i, alpha in enumerate((255, 180, 120)):
        off = i * 3
        d.arc([cx - 18 + off, cy - 10 - off, cx + 18 - off, cy + 18 - off],
              start=180, end=360, fill=(180, 230, 255, alpha), width=3)
    d.line([(cx - 18, cy), (cx + 18, cy)], fill=(220, 245, 255, 255), width=2)


def sigil_conduit(d, _layer):
    # Lightning bolt
    cx, cy = SIZE // 2, SIZE // 2
    pts = [(cx - 2, cy - 18), (cx + 6, cy - 4), (cx - 1, cy - 2),
           (cx + 4, cy + 18), (cx - 5, cy + 4), (cx + 2, cy + 2)]
    d.polygon(pts, fill=(255, 230, 100, 255), outline=(255, 255, 200, 255))


def sigil_climax(d, _layer):
    # Sunburst with rays
    cx, cy = SIZE // 2, SIZE // 2
    for ang_deg in range(0, 360, 30):
        ang = math.radians(ang_deg)
        d.line([(cx + math.cos(ang) * 6, cy + math.sin(ang) * 6),
                (cx + math.cos(ang) * 20, cy + math.sin(ang) * 20)],
               fill=(255, 200, 80, 255), width=2)
    d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=(255, 250, 170, 255),
              outline=(255, 220, 100, 255))


def sigil_plunge(d, _layer):
    # Downward arrow / crater
    cx, cy = SIZE // 2, SIZE // 2
    d.line([(cx, cy - 14), (cx, cy + 10)], fill=(170, 120, 220, 255), width=4)
    d.polygon([(cx - 10, cy + 4), (cx + 10, cy + 4), (cx, cy + 18)],
              fill=(170, 120, 220, 255), outline=(220, 180, 255, 255))
    # Crater ring
    d.arc([cx - 16, cy + 12, cx + 16, cy + 28], start=180, end=360,
          fill=(110, 70, 150, 255), width=2)


SIGILS = {
    "primary": sigil_primary,
    "bastion": sigil_bastion,
    "skyfall": sigil_skyfall,
    "root": sigil_root,
    "slipstream": sigil_slipstream,
    "conduit": sigil_conduit,
    "climax": sigil_climax,
    "plunge": sigil_plunge,
}


def make_card(slot_id: str) -> Image.Image:
    base = card_base()
    return draw_sigil(base, SIGILS[slot_id])


def facebook_icon() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Blue square
    d.rounded_rectangle([2, 2, SIZE - 2, SIZE - 2], radius=8, fill=(24, 119, 242, 255))
    # Stylized "f"
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    except Exception:
        font = ImageFont.load_default()
    # Center the glyph
    try:
        bbox = d.textbbox((0, 0), "f", font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        w, h = font.getsize("f")
    d.text(((SIZE - w) // 2, (SIZE - h) // 2 - 4), "f", fill=(255, 255, 255, 255), font=font)
    # Inner glow rim
    d.rounded_rectangle([3, 3, SIZE - 3, SIZE - 3], radius=7,
                        outline=(140, 200, 255, 200), width=1)
    return img


def roblox_icon() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Dark red tile
    d.rounded_rectangle([2, 2, SIZE - 2, SIZE - 2], radius=8, fill=(35, 35, 40, 255))
    # Rotated red square (simplified Roblox logo)
    cx, cy = SIZE // 2, SIZE // 2
    size = 28
    pts = [(cx, cy - size / 1.414), (cx + size / 1.414, cy),
           (cx, cy + size / 1.414), (cx - size / 1.414, cy)]
    d.polygon(pts, fill=(226, 35, 26, 255), outline=(255, 150, 140, 255))
    # Inner tile
    inner = 8
    pts2 = [(cx, cy - inner / 1.414), (cx + inner / 1.414, cy),
            (cx, cy + inner / 1.414), (cx - inner / 1.414, cy)]
    d.polygon(pts2, fill=(30, 30, 35, 255))
    d.rounded_rectangle([3, 3, SIZE - 3, SIZE - 3], radius=7,
                        outline=(120, 120, 130, 200), width=1)
    return img


def main() -> None:
    for slot_id in SIGILS:
        img = make_card(slot_id)
        path = OUT / f"elem_card_{slot_id}.png"
        img.save(path)
        print(f"wrote {path}")
    facebook_icon().save(OUT / "elem_icon_facebook.png")
    print(f"wrote {OUT / 'elem_icon_facebook.png'}")
    roblox_icon().save(OUT / "elem_icon_roblox.png")
    print(f"wrote {OUT / 'elem_icon_roblox.png'}")


if __name__ == "__main__":
    main()
