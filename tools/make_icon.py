"""Builds assets/VanadielNexus.ico from the large and small source artwork.

Large art is used for 48 px and up; the simplified small art for 16-32 px,
where the rune ring and sparkles would turn to mush. Corners are masked to
transparent so the rounded tile sits cleanly on any background.

    py tools/make_icon.py
"""
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
LARGE_SRC = os.path.join(ASSETS, "icon-source-large.jpg")
SMALL_SRC = os.path.join(ASSETS, "icon-source-small.jpg")
CORNER_RATIO = 0.13  # corner radius of the tile in the source art, as a fraction of its width
LARGE_SIZES = (256, 128, 64, 48)
SMALL_SIZES = (32, 24, 16)


def rounded(src_path: str) -> Image.Image:
    img = Image.open(src_path).convert("RGBA")
    w, h = img.size
    side = min(w, h)
    # Trim a thin edge: the source JPEGs have white anti-aliasing right at the tile border
    inset = int(side * 0.012)
    img = img.crop(((w - side) // 2 + inset, (h - side) // 2 + inset, (w + side) // 2 - inset, (h + side) // 2 - inset))
    side -= 2 * inset
    # Draw the mask at 4x and downsample for smooth anti-aliased corners
    big = Image.new("L", (side * 4, side * 4), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, side * 4 - 1, side * 4 - 1), radius=int(side * 4 * CORNER_RATIO), fill=255
    )
    img.putalpha(big.resize((side, side), Image.LANCZOS))
    return img


def main():
    large = rounded(LARGE_SRC)
    small = rounded(SMALL_SRC)
    frames = [large.resize((s, s), Image.LANCZOS) for s in LARGE_SIZES]
    frames += [small.resize((s, s), Image.LANCZOS) for s in SMALL_SIZES]

    ico_path = os.path.join(ASSETS, "VanadielNexus.ico")
    frames[0].save(ico_path, format="ICO", sizes=[f.size for f in frames], append_images=frames[1:])
    large.resize((512, 512), Image.LANCZOS).save(os.path.join(ASSETS, "icon-512.png"))
    print(f"Wrote {ico_path}")


if __name__ == "__main__":
    main()
