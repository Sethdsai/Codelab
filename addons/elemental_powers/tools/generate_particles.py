"""
Generate custom 16x16 particle textures for the Elemental Powers addon.

Each PNG is a single sprite the particle system billboards. Kept small (16x16)
because particles are sampled at high frequency and big textures tank FPS on
mobile Bedrock. Outputs to resource_pack/textures/particle/.
"""
from __future__ import annotations

import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

SIZE = 16
OUT = Path(__file__).resolve().parent.parent / "resource_pack" / "textures" / "particle"
OUT.mkdir(parents=True, exist_ok=True)


def base() -> Image.Image:
    return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))


def glow(img: Image.Image, color, intensity: float = 1.0) -> Image.Image:
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    cx, cy = SIZE / 2, SIZE / 2
    for r in range(SIZE // 2, 0, -1):
        a = int(255 * intensity * (1 - r / (SIZE / 2)) ** 2)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (a,))
    g = g.filter(ImageFilter.GaussianBlur(1.2))
    return Image.alpha_composite(g, img)


def chain_link() -> Image.Image:
    img = base()
    d = ImageDraw.Draw(img)
    # A single bright chain link: an oval outline that glows electric blue
    for thickness in range(3):
        alpha = 255 - thickness * 80
        d.ellipse([3 - thickness, 3 - thickness, 12 + thickness, 12 + thickness],
                  outline=(140, 220, 255, alpha), width=1)
    # Inner bright core
    d.ellipse([6, 6, 9, 9], fill=(255, 255, 255, 255))
    # Tiny sparks at the edges
    for _ in range(6):
        x = random.randint(0, SIZE - 1)
        y = random.randint(0, SIZE - 1)
        if 3 <= x <= 12 and 3 <= y <= 12:
            continue
        d.point([x, y], fill=(220, 245, 255, 200))
    img = glow(img, (80, 150, 240), 0.4)
    return img


def ember() -> Image.Image:
    img = base()
    d = ImageDraw.Draw(img)
    # Flame-shaped ember: taller than wide
    cx, cy = SIZE // 2, SIZE // 2 + 1
    d.ellipse([cx - 2, cy - 5, cx + 2, cy + 4], fill=(255, 210, 80, 255))
    d.ellipse([cx - 3, cy - 2, cx + 3, cy + 5], fill=(255, 120, 30, 200))
    d.polygon([(cx, cy - 6), (cx - 1, cy - 2), (cx + 1, cy - 2)], fill=(255, 240, 200, 255))
    # Embers around
    for _ in range(8):
        x = cx + random.randint(-6, 6)
        y = cy + random.randint(-6, 6)
        if 0 <= x < SIZE and 0 <= y < SIZE:
            d.point([x, y], fill=(255, 180, 60, 160))
    img = glow(img, (255, 120, 0), 0.35)
    return img


def frost_crystal() -> Image.Image:
    img = base()
    d = ImageDraw.Draw(img)
    cx, cy = SIZE / 2, SIZE / 2
    # Six-pointed snowflake
    for ang_deg in (0, 60, 120):
        ang = math.radians(ang_deg)
        dx = math.cos(ang) * 6
        dy = math.sin(ang) * 6
        d.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=(200, 235, 255, 255), width=1)
    # Small branches
    for ang_deg in (0, 60, 120, 180, 240, 300):
        ang = math.radians(ang_deg)
        tx = cx + math.cos(ang) * 3
        ty = cy + math.sin(ang) * 3
        bx = tx + math.cos(ang + math.pi / 3) * 2
        by = ty + math.sin(ang + math.pi / 3) * 2
        d.line([(tx, ty), (bx, by)], fill=(220, 245, 255, 200), width=1)
    # Core
    d.ellipse([cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5], fill=(255, 255, 255, 255))
    img = glow(img, (170, 220, 255), 0.3)
    return img


def shadow_wisp() -> Image.Image:
    img = base()
    d = ImageDraw.Draw(img)
    cx, cy = SIZE / 2, SIZE / 2
    # Dark purple blob with wispy tails
    d.ellipse([cx - 4, cy - 5, cx + 4, cy + 4], fill=(30, 0, 50, 220))
    d.ellipse([cx - 2, cy - 3, cx + 2, cy + 2], fill=(90, 30, 130, 255))
    # Wispy trails
    for ang_deg in (45, 135, 225, 315):
        ang = math.radians(ang_deg)
        for i in range(1, 4):
            x = cx + math.cos(ang) * i * 1.4
            y = cy + math.sin(ang) * i * 1.4
            d.point([x, y], fill=(70, 20, 110, 200 - i * 40))
    img = glow(img, (90, 30, 130), 0.35)
    return img


def divine_spark() -> Image.Image:
    img = base()
    d = ImageDraw.Draw(img)
    cx, cy = SIZE / 2, SIZE / 2
    # Four-point star
    d.polygon([(cx, cy - 7), (cx + 1, cy - 1), (cx + 7, cy),
               (cx + 1, cy + 1), (cx, cy + 7), (cx - 1, cy + 1),
               (cx - 7, cy), (cx - 1, cy - 1)],
              fill=(255, 240, 180, 255))
    # Bright core
    d.ellipse([cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5], fill=(255, 255, 255, 255))
    img = glow(img, (255, 220, 140), 0.5)
    return img


def main() -> None:
    random.seed(7)
    specs = {
        "elem_chain_link": chain_link(),
        "elem_ember": ember(),
        "elem_frost_crystal": frost_crystal(),
        "elem_shadow_wisp": shadow_wisp(),
        "elem_divine_spark": divine_spark(),
    }
    for name, img in specs.items():
        path = OUT / f"{name}.png"
        img.save(path)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
