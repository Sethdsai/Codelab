"""
Generate richly detailed 64x64 item textures for the Elemental Powers Bedrock addon.

Every item is rendered procedurally with Pillow. Each texture is built from multiple
passes (background gradient, themed shape, highlights, particles, glow rim) so the
final PNG looks hand-painted rather than flat.
"""
from __future__ import annotations

import math
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SIZE = 64
OUT_DIR = Path(__file__).resolve().parent.parent / "resource_pack" / "textures" / "items"
PACK_ICONS = [
    Path(__file__).resolve().parent.parent / "behavior_pack" / "pack_icon.png",
    Path(__file__).resolve().parent.parent / "resource_pack" / "pack_icon.png",
]


# ---------- helpers ----------------------------------------------------------
def lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def radial_gradient(size: int, inner, outer, center=None) -> Image.Image:
    img = Image.new("RGBA", (size, size), outer + (255,))
    cx, cy = center or (size / 2, size / 2)
    max_d = math.hypot(max(cx, size - cx), max(cy, size - cy))
    px = img.load()
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - cx, y - cy) / max_d
            d = max(0.0, min(1.0, d))
            c = lerp(inner, outer, d)
            px[x, y] = c + (255,)
    return img


def linear_gradient(size: int, top, bottom) -> Image.Image:
    img = Image.new("RGBA", (size, size))
    px = img.load()
    for y in range(size):
        c = lerp(top, bottom, y / (size - 1))
        for x in range(size):
            px[x, y] = c + (255,)
    return img


def noise_layer(size: int, amount: float = 20, seed: int = 0) -> Image.Image:
    rng = random.Random(seed)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    for y in range(size):
        for x in range(size):
            v = int(rng.random() * amount)
            px[x, y] = (v, v, v, int(amount))
    return img


def alpha_mask_circle(size: int, radius: int, center=None, feather: int = 0) -> Image.Image:
    cx, cy = center or (size / 2, size / 2)
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=255)
    if feather:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    return mask


def paste_with_mask(base: Image.Image, overlay: Image.Image, mask: Image.Image) -> None:
    base.paste(overlay, (0, 0), mask)


def sprinkle_specks(img: Image.Image, colors, count: int, seed: int) -> None:
    rng = random.Random(seed)
    d = ImageDraw.Draw(img)
    for _ in range(count):
        x = rng.randint(0, img.width - 1)
        y = rng.randint(0, img.height - 1)
        r = rng.choice([0, 0, 1, 1, 2])
        c = rng.choice(colors)
        a = rng.randint(180, 255)
        if r == 0:
            d.point((x, y), fill=c + (a,))
        else:
            d.ellipse((x - r, y - r, x + r, y + r), fill=c + (a,))


def glow_outline(shape: Image.Image, color, radius: int = 3) -> Image.Image:
    alpha = shape.split()[-1]
    glow = Image.new("RGBA", shape.size, color + (0,))
    glow.putalpha(alpha.filter(ImageFilter.GaussianBlur(radius)))
    return glow


def finalize(img: Image.Image, bg_alpha_mask: Image.Image | None = None) -> Image.Image:
    if bg_alpha_mask is not None:
        r, g, b, a = img.split()
        a = Image.eval(a, lambda v: v)
        a = Image.composite(a, Image.new("L", img.size, 0), bg_alpha_mask)
        img.putalpha(a)
    return img


# ---------- per-item textures ------------------------------------------------
def orb_base(inner, mid, outer, accent_specks, seed: int) -> Image.Image:
    """Generic glowing orb used as foundation for element orbs."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    # outer glow halo
    halo = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(halo)
    for r, a in [(31, 40), (28, 70), (25, 110), (22, 150)]:
        d.ellipse((SIZE / 2 - r, SIZE / 2 - r, SIZE / 2 + r, SIZE / 2 + r),
                  fill=outer + (a,))
    halo = halo.filter(ImageFilter.GaussianBlur(2))
    img = Image.alpha_composite(img, halo)

    # main sphere
    sphere = radial_gradient(SIZE, inner, outer, center=(SIZE / 2 - 5, SIZE / 2 - 5))
    mask = alpha_mask_circle(SIZE, 22)
    sphere.putalpha(mask)
    img = Image.alpha_composite(img, sphere)

    # inner swirl / highlight ring
    swirl = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(swirl)
    for i, r in enumerate([20, 17, 14, 11, 8]):
        c = lerp(mid, inner, i / 4)
        sd.arc((SIZE / 2 - r, SIZE / 2 - r, SIZE / 2 + r, SIZE / 2 + r),
               start=200 + i * 20, end=340 + i * 20, fill=c + (200,), width=2)
    swirl = swirl.filter(ImageFilter.GaussianBlur(0.6))
    img = Image.alpha_composite(img, swirl)

    # specular highlight
    hl = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.ellipse((SIZE / 2 - 14, SIZE / 2 - 18, SIZE / 2 - 2, SIZE / 2 - 8),
               fill=(255, 255, 255, 130))
    hd.ellipse((SIZE / 2 - 10, SIZE / 2 - 16, SIZE / 2 - 4, SIZE / 2 - 12),
               fill=(255, 255, 255, 220))
    hl = hl.filter(ImageFilter.GaussianBlur(1))
    img = Image.alpha_composite(img, hl)

    # accent specks
    sprinkle_specks(img, accent_specks, count=40, seed=seed)

    return img


def tex_fire_orb() -> Image.Image:
    img = orb_base(
        inner=(255, 240, 170),
        mid=(255, 140, 30),
        outer=(160, 20, 10),
        accent_specks=[(255, 200, 60), (255, 240, 200), (255, 80, 20)],
        seed=1,
    )
    # flame tongues
    flames = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    fd = ImageDraw.Draw(flames)
    for angle in range(0, 360, 30):
        a = math.radians(angle)
        x1 = SIZE / 2 + math.cos(a) * 18
        y1 = SIZE / 2 + math.sin(a) * 18
        x2 = SIZE / 2 + math.cos(a) * 28
        y2 = SIZE / 2 + math.sin(a) * 28
        fd.line((x1, y1, x2, y2), fill=(255, 180, 40, 220), width=2)
        fd.line((x1, y1, (x1 + x2) / 2, (y1 + y2) / 2), fill=(255, 240, 180, 230), width=1)
    flames = flames.filter(ImageFilter.GaussianBlur(0.8))
    img = Image.alpha_composite(img, flames)
    return img


def tex_water_orb() -> Image.Image:
    img = orb_base(
        inner=(220, 240, 255),
        mid=(60, 140, 220),
        outer=(10, 40, 110),
        accent_specks=[(200, 230, 255), (100, 200, 255), (255, 255, 255)],
        seed=2,
    )
    # wave ripples
    waves = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    wd = ImageDraw.Draw(waves)
    for i, (y, amp, w) in enumerate([(30, 3, 2), (36, 2, 1), (42, 3, 2)]):
        pts = []
        for x in range(20, 45):
            yy = y + math.sin((x + i * 3) * 0.6) * amp
            pts.append((x, yy))
        wd.line(pts, fill=(230, 245, 255, 220), width=w)
    img = Image.alpha_composite(img, waves)
    # droplet highlight
    dd = ImageDraw.Draw(img)
    dd.ellipse((26, 20, 30, 26), fill=(255, 255, 255, 230))
    return img


def tex_earth_orb() -> Image.Image:
    img = orb_base(
        inner=(180, 140, 90),
        mid=(110, 70, 35),
        outer=(50, 30, 15),
        accent_specks=[(200, 170, 100), (90, 60, 30), (40, 90, 40)],
        seed=3,
    )
    # stone chunks + crystals
    cd = ImageDraw.Draw(img)
    for (x, y, r, col) in [
        (22, 30, 5, (150, 110, 70)),
        (40, 36, 4, (130, 95, 55)),
        (30, 44, 3, (95, 65, 30)),
        (36, 24, 3, (170, 130, 80)),
    ]:
        cd.ellipse((x - r, y - r, x + r, y + r), fill=col + (255,))
    # crystal spike
    cd.polygon([(34, 22), (38, 30), (34, 38), (30, 30)], fill=(120, 210, 130, 255))
    cd.polygon([(34, 22), (34, 30), (30, 30)], fill=(170, 240, 170, 255))
    # grass tufts on top
    cd.line((24, 22, 24, 18), fill=(100, 210, 100, 255), width=1)
    cd.line((26, 22, 26, 19), fill=(80, 180, 80, 255), width=1)
    cd.line((28, 22, 28, 17), fill=(110, 220, 110, 255), width=1)
    return img


def tex_air_orb() -> Image.Image:
    img = orb_base(
        inner=(240, 255, 255),
        mid=(180, 220, 230),
        outer=(80, 120, 150),
        accent_specks=[(255, 255, 255), (200, 230, 240), (160, 200, 220)],
        seed=4,
    )
    # swirling wind streaks
    swirl = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(swirl)
    for i, r in enumerate([8, 12, 16, 20]):
        sd.arc((SIZE / 2 - r, SIZE / 2 - r, SIZE / 2 + r, SIZE / 2 + r),
               start=190 + i * 25, end=350 + i * 25,
               fill=(255, 255, 255, 220 - i * 30), width=2)
        sd.arc((SIZE / 2 - r, SIZE / 2 - r, SIZE / 2 + r, SIZE / 2 + r),
               start=20 + i * 25, end=140 + i * 25,
               fill=(240, 250, 255, 180 - i * 25), width=1)
    swirl = swirl.filter(ImageFilter.GaussianBlur(0.4))
    img = Image.alpha_composite(img, swirl)
    return img


def tex_lightning_orb() -> Image.Image:
    img = orb_base(
        inner=(255, 255, 210),
        mid=(230, 200, 80),
        outer=(60, 50, 120),
        accent_specks=[(255, 255, 180), (200, 180, 255), (255, 240, 120)],
        seed=5,
    )
    # lightning bolt
    bd = ImageDraw.Draw(img)
    bolt = [(30, 18), (36, 28), (30, 32), (38, 46)]
    bd.line(bolt, fill=(255, 255, 200, 255), width=3)
    bd.line(bolt, fill=(255, 255, 255, 255), width=1)
    # glow around bolt
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.line(bolt, fill=(255, 240, 120, 200), width=5)
    glow = glow.filter(ImageFilter.GaussianBlur(2))
    img = Image.alpha_composite(glow, img)
    # sparks
    sprinkle_specks(img, [(255, 255, 200), (200, 180, 255)], 25, seed=55)
    return img


def tex_light_orb() -> Image.Image:
    img = orb_base(
        inner=(255, 255, 240),
        mid=(255, 230, 130),
        outer=(220, 170, 40),
        accent_specks=[(255, 255, 255), (255, 240, 170), (255, 220, 90)],
        seed=6,
    )
    # radiant rays
    rays = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rays)
    for angle in range(0, 360, 15):
        a = math.radians(angle)
        length = 30 if angle % 30 == 0 else 26
        x1 = SIZE / 2 + math.cos(a) * 22
        y1 = SIZE / 2 + math.sin(a) * 22
        x2 = SIZE / 2 + math.cos(a) * length
        y2 = SIZE / 2 + math.sin(a) * length
        rd.line((x1, y1, x2, y2), fill=(255, 245, 200, 220), width=1)
    rays = rays.filter(ImageFilter.GaussianBlur(0.5))
    img = Image.alpha_composite(img, rays)
    # bright core
    cd = ImageDraw.Draw(img)
    cd.ellipse((SIZE / 2 - 6, SIZE / 2 - 6, SIZE / 2 + 6, SIZE / 2 + 6),
               fill=(255, 255, 255, 230))
    return img


def tex_dark_orb() -> Image.Image:
    img = orb_base(
        inner=(90, 40, 130),
        mid=(45, 20, 70),
        outer=(8, 0, 20),
        accent_specks=[(160, 80, 220), (220, 160, 255), (70, 30, 110)],
        seed=7,
    )
    # swirling void
    swirl = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(swirl)
    for i, r in enumerate([6, 10, 14, 18]):
        sd.arc((SIZE / 2 - r, SIZE / 2 - r, SIZE / 2 + r, SIZE / 2 + r),
               start=10 + i * 40, end=170 + i * 40,
               fill=(140, 60, 200, 200), width=2)
    swirl = swirl.filter(ImageFilter.GaussianBlur(0.8))
    img = Image.alpha_composite(img, swirl)
    # soul sparks
    sprinkle_specks(img, [(180, 100, 230), (220, 160, 255)], 30, seed=77)
    # central void
    dd = ImageDraw.Draw(img)
    dd.ellipse((SIZE / 2 - 5, SIZE / 2 - 5, SIZE / 2 + 5, SIZE / 2 + 5),
               fill=(5, 0, 15, 255))
    return img


def tex_gui_tool() -> Image.Image:
    """An ornate magical tome bound with a glowing rune."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # book cover
    d.rounded_rectangle((10, 8, 54, 56), radius=3, fill=(40, 20, 60, 255),
                        outline=(15, 5, 30, 255), width=1)
    d.rounded_rectangle((12, 10, 52, 54), radius=2, fill=(70, 30, 110, 255))
    # pages edge
    d.rectangle((52, 12, 54, 52), fill=(240, 230, 200, 255))
    for y in range(12, 52, 2):
        d.line((52, y, 54, y), fill=(200, 190, 160, 255))
    # gold ornate border
    d.rectangle((14, 12, 50, 14), fill=(230, 190, 80, 255))
    d.rectangle((14, 50, 50, 52), fill=(230, 190, 80, 255))
    d.rectangle((14, 12, 16, 52), fill=(230, 190, 80, 255))
    d.rectangle((48, 12, 50, 52), fill=(230, 190, 80, 255))
    # corner gems
    for (x, y) in [(14, 12), (48, 12), (14, 50), (48, 50)]:
        d.ellipse((x, y, x + 2, y + 2), fill=(255, 240, 150, 255))
    # central glowing rune (elemental sigil: pentagon with circle)
    cx, cy = 32, 32
    pts = [(cx + math.cos(math.radians(a - 90)) * 11,
            cy + math.sin(math.radians(a - 90)) * 11)
           for a in range(0, 360, 72)]
    # draw star
    order = [0, 2, 4, 1, 3, 0]
    path = [pts[i] for i in order]
    glow_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    gd.line(path, fill=(255, 220, 140, 255), width=2)
    gd.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), outline=(255, 220, 140, 255), width=1)
    blurred = glow_layer.filter(ImageFilter.GaussianBlur(1.6))
    img = Image.alpha_composite(img, blurred)
    img = Image.alpha_composite(img, glow_layer)
    # center gem
    d2 = ImageDraw.Draw(img)
    d2.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=(255, 240, 180, 255),
               outline=(200, 120, 40, 255))
    # sparkle
    d2.point((cx - 1, cy - 1), fill=(255, 255, 255, 255))
    # book spine shadow
    sd = ImageDraw.Draw(img)
    sd.line((10, 9, 10, 56), fill=(20, 10, 35, 255), width=1)
    sd.line((54, 9, 54, 56), fill=(25, 12, 40, 255), width=1)
    return img


def tex_dark_scythe() -> Image.Image:
    """Ornate dark scythe with glowing purple blade edge."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # --- shaft (diagonal) ---
    shaft = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shaft)
    # draw a thick diagonal wood shaft from bottom-left to top-right
    shaft_pts = [(10, 54), (40, 18)]
    sd.line(shaft_pts, fill=(50, 30, 20, 255), width=5)
    sd.line(shaft_pts, fill=(85, 55, 30, 255), width=3)
    sd.line(shaft_pts, fill=(130, 85, 45, 255), width=1)
    # wrapping bands
    for (x, y) in [(16, 48), (22, 41), (28, 34), (34, 27)]:
        sd.line((x - 2, y + 2, x + 3, y - 3), fill=(220, 180, 60, 255), width=2)
        sd.line((x - 2, y + 2, x + 3, y - 3), fill=(255, 230, 130, 255), width=1)
    img = Image.alpha_composite(img, shaft)

    # --- blade ---
    blade_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blade_layer)
    # curved blade via multiple arcs - dark base
    bd.arc((18, 4, 58, 44), start=200, end=340, fill=(20, 5, 30, 255), width=7)
    # steel middle
    bd.arc((20, 6, 56, 42), start=200, end=340, fill=(80, 40, 120, 255), width=5)
    # sharp purple edge
    bd.arc((22, 8, 54, 40), start=200, end=340, fill=(180, 80, 220, 255), width=3)
    # glowing inner edge
    bd.arc((24, 10, 52, 38), start=200, end=340, fill=(230, 170, 255, 255), width=1)

    # blade spike at tip
    bd.polygon([(55, 22), (62, 14), (58, 26)], fill=(40, 15, 60, 255))
    bd.polygon([(55, 22), (60, 16), (57, 25)], fill=(140, 70, 200, 255))

    # glow layer under blade
    glow = blade_layer.copy().filter(ImageFilter.GaussianBlur(2))
    img = Image.alpha_composite(img, glow)
    img = Image.alpha_composite(img, blade_layer)

    # --- pommel / skull on base of shaft ---
    pd = ImageDraw.Draw(img)
    pd.ellipse((6, 50, 16, 60), fill=(30, 15, 45, 255), outline=(15, 5, 25, 255))
    pd.ellipse((8, 52, 14, 58), fill=(180, 130, 230, 255))
    pd.point((10, 55), fill=(10, 0, 15, 255))
    pd.point((12, 55), fill=(10, 0, 15, 255))

    # purple sparkles trailing the blade
    sprinkle_specks(img, [(200, 120, 240), (240, 200, 255), (160, 80, 220)], 25, seed=99)

    # rim light on shaft
    rd = ImageDraw.Draw(img)
    rd.line((11, 53, 39, 19), fill=(200, 150, 90, 140), width=1)

    return img


def tex_staff(inner, mid, outer, gem_inner, gem_outer, sparkle_colors,
              seed: int) -> Image.Image:
    """Generic magical staff base (shared silhouette with element-specific gem)."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # shaft diagonal bottom-left to top-right
    shaft_pts = [(10, 54), (44, 14)]
    d.line(shaft_pts, fill=(45, 25, 15, 255), width=5)
    d.line(shaft_pts, fill=(100, 65, 35, 255), width=3)
    d.line(shaft_pts, fill=(150, 100, 55, 255), width=1)
    # metal wrappings
    for (x, y) in [(16, 48), (24, 40), (32, 32)]:
        d.line((x - 2, y + 2, x + 3, y - 3), fill=(210, 180, 80, 255), width=2)
        d.line((x - 2, y + 2, x + 3, y - 3), fill=(255, 235, 140, 255), width=1)

    # ornate head/claw around gem
    head_cx, head_cy = 46, 14
    d.polygon([(head_cx - 9, head_cy + 6), (head_cx - 14, head_cy),
               (head_cx - 9, head_cy - 6), (head_cx, head_cy - 10),
               (head_cx + 9, head_cy - 6), (head_cx + 12, head_cy),
               (head_cx + 9, head_cy + 6), (head_cx, head_cy + 10)],
              outline=(60, 35, 10, 255), fill=(180, 140, 60, 255))
    d.polygon([(head_cx - 6, head_cy + 3), (head_cx - 9, head_cy),
               (head_cx - 6, head_cy - 3), (head_cx, head_cy - 6),
               (head_cx + 6, head_cy - 3), (head_cx + 8, head_cy),
               (head_cx + 6, head_cy + 3), (head_cx, head_cy + 6)],
              fill=(230, 190, 90, 255))

    # gem: radial gradient circle
    gem_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gem_img = radial_gradient(SIZE, gem_inner, gem_outer, center=(head_cx - 2, head_cy - 2))
    gmask = alpha_mask_circle(SIZE, 6, center=(head_cx, head_cy))
    gem_img.putalpha(gmask)
    gem_layer = Image.alpha_composite(gem_layer, gem_img)
    # gem specular
    gd = ImageDraw.Draw(gem_layer)
    gd.ellipse((head_cx - 4, head_cy - 5, head_cx - 1, head_cy - 2),
               fill=(255, 255, 255, 220))

    # glow
    glow = gem_layer.copy().filter(ImageFilter.GaussianBlur(3))
    img = Image.alpha_composite(img, glow)
    img = Image.alpha_composite(img, gem_layer)

    # elemental sparkles near gem
    sparkle_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sprinkle_specks(sparkle_layer, sparkle_colors, 30, seed=seed)
    # mask sparkles to top-right half only
    mask = Image.new("L", (SIZE, SIZE), 0)
    md = ImageDraw.Draw(mask)
    md.rectangle((28, 0, SIZE, 32), fill=255)
    sparkle_layer.putalpha(
        Image.eval(sparkle_layer.split()[-1], lambda v: v).point(lambda v: v)
    )
    img = Image.alpha_composite(img, sparkle_layer)

    # pommel crystal
    pd = ImageDraw.Draw(img)
    pd.polygon([(10, 56), (6, 58), (10, 62), (14, 58)], fill=inner + (255,),
               outline=(0, 0, 0, 255))
    pd.polygon([(10, 56), (8, 58), (10, 60), (12, 58)], fill=mid + (255,))

    return img


def tex_fire_staff():
    return tex_staff(
        inner=(255, 240, 180), mid=(255, 140, 40), outer=(140, 30, 10),
        gem_inner=(255, 245, 200), gem_outer=(160, 30, 10),
        sparkle_colors=[(255, 200, 60), (255, 240, 200), (255, 80, 20)], seed=101,
    )


def tex_water_staff():
    return tex_staff(
        inner=(220, 240, 255), mid=(60, 140, 220), outer=(10, 40, 110),
        gem_inner=(230, 245, 255), gem_outer=(20, 60, 150),
        sparkle_colors=[(200, 230, 255), (100, 200, 255), (255, 255, 255)], seed=102,
    )


def tex_earth_staff():
    return tex_staff(
        inner=(180, 140, 90), mid=(110, 70, 35), outer=(50, 30, 15),
        gem_inner=(180, 230, 140), gem_outer=(40, 90, 30),
        sparkle_colors=[(160, 230, 140), (90, 60, 30), (200, 170, 100)], seed=103,
    )


def tex_air_staff():
    return tex_staff(
        inner=(240, 255, 255), mid=(180, 220, 230), outer=(80, 120, 150),
        gem_inner=(240, 255, 255), gem_outer=(100, 160, 200),
        sparkle_colors=[(255, 255, 255), (200, 230, 240), (160, 200, 220)], seed=104,
    )


def tex_lightning_staff():
    return tex_staff(
        inner=(255, 255, 210), mid=(230, 200, 80), outer=(60, 50, 120),
        gem_inner=(255, 255, 220), gem_outer=(120, 100, 200),
        sparkle_colors=[(255, 255, 180), (200, 180, 255), (255, 240, 120)], seed=105,
    )


def tex_light_staff():
    return tex_staff(
        inner=(255, 255, 240), mid=(255, 230, 130), outer=(220, 170, 40),
        gem_inner=(255, 255, 240), gem_outer=(240, 190, 60),
        sparkle_colors=[(255, 255, 255), (255, 240, 170), (255, 220, 90)], seed=106,
    )


def tex_dark_staff():
    return tex_staff(
        inner=(90, 40, 130), mid=(45, 20, 70), outer=(8, 0, 20),
        gem_inner=(180, 100, 230), gem_outer=(30, 5, 50),
        sparkle_colors=[(160, 80, 220), (220, 160, 255), (70, 30, 110)], seed=107,
    )


def tex_pack_icon() -> Image.Image:
    """128x128 pack icon - elemental seven-pointed star."""
    s = 128
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    # background radial
    bg = radial_gradient(s, (50, 20, 90), (5, 0, 20))
    img = Image.alpha_composite(img, bg)
    d = ImageDraw.Draw(img)
    cx, cy = s / 2, s / 2
    colors = [
        (255, 120, 40),   # fire
        (70, 150, 230),   # water
        (140, 90, 40),    # earth
        (220, 240, 240),  # air
        (255, 230, 100),  # lightning
        (255, 245, 180),  # light
        (140, 60, 200),   # dark
    ]
    # outer star of 7 points
    for i, col in enumerate(colors):
        a = math.radians(-90 + i * (360 / 7))
        x = cx + math.cos(a) * 46
        y = cy + math.sin(a) * 46
        # petal
        petal = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        pd = ImageDraw.Draw(petal)
        pd.ellipse((x - 18, y - 18, x + 18, y + 18), fill=col + (230,))
        petal = petal.filter(ImageFilter.GaussianBlur(2))
        img = Image.alpha_composite(img, petal)
        pd2 = ImageDraw.Draw(img)
        pd2.ellipse((x - 12, y - 12, x + 12, y + 12), fill=col + (255,))
        pd2.ellipse((x - 6, y - 8, x - 2, y - 4), fill=(255, 255, 255, 200))

    # central white sigil
    core = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    cd = ImageDraw.Draw(core)
    cd.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), fill=(255, 255, 255, 80))
    core = core.filter(ImageFilter.GaussianBlur(4))
    img = Image.alpha_composite(img, core)
    d2 = ImageDraw.Draw(img)
    d2.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=(255, 255, 255, 240))
    # inner heptagram
    pts = [(cx + math.cos(math.radians(-90 + i * 360 / 7)) * 14,
            cy + math.sin(math.radians(-90 + i * 360 / 7)) * 14)
           for i in range(7)]
    order = [0, 3, 6, 2, 5, 1, 4, 0]
    path = [pts[i] for i in order]
    d2.line(path, fill=(80, 30, 140, 255), width=2)
    return img


# ---------- run --------------------------------------------------------------
TEXTURES = {
    "elem_fire_orb": tex_fire_orb,
    "elem_water_orb": tex_water_orb,
    "elem_earth_orb": tex_earth_orb,
    "elem_air_orb": tex_air_orb,
    "elem_lightning_orb": tex_lightning_orb,
    "elem_light_orb": tex_light_orb,
    "elem_dark_orb": tex_dark_orb,
    "elem_fire_staff": tex_fire_staff,
    "elem_water_staff": tex_water_staff,
    "elem_earth_staff": tex_earth_staff,
    "elem_air_staff": tex_air_staff,
    "elem_lightning_staff": tex_lightning_staff,
    "elem_light_staff": tex_light_staff,
    "elem_dark_staff": tex_dark_staff,
    "elem_dark_scythe": tex_dark_scythe,
    "elem_gui_tool": tex_gui_tool,
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, fn in TEXTURES.items():
        img = fn()
        path = OUT_DIR / f"{name}.png"
        img.save(path)
        print(f"wrote {path}")

    icon = tex_pack_icon()
    for p in PACK_ICONS:
        p.parent.mkdir(parents=True, exist_ok=True)
        icon.save(p)
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
