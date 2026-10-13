"""Cut the hero (1200x700) and thumbnail/teaser (1200x800) image of every article topic from the photos we already have.

    python3 geozo_site/make_images.py

Owner, 13.10 night: «картинки можно использовать те же самые» — so the ten topics of the multilingual site use the
photos of the Kazakhstan test (teasers/t1-t6.jpg, assets/*-hero.jpg) and three photos of the old blog of arcadiablog.com
(assets/src/). The sources and the crops are listed in multi_config.TOPICS. One picture serves every language.
Output: assets/<slug>.jpg (hero) and teasers/<slug>.jpg (list thumbnail and MGID creative).
"""
import sys
from pathlib import Path

from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import multi_config as mc  # noqa: E402

SIZES = {"assets": (1200, 700), "teasers": (1200, 800)}


def fit(im, w, h):
    """Centre-crop to the aspect ratio w:h, then resize."""
    sw, sh = im.size
    target = w / h
    if sw / sh > target:
        nw = round(sh * target)
        box = ((sw - nw) // 2, 0, (sw - nw) // 2 + nw, sh)
    else:
        nh = round(sw / target)
        box = (0, (sh - nh) // 2, sw, (sh - nh) // 2 + nh)
    return im.crop(box).resize((w, h), Image.LANCZOS)


def main():
    for t in mc.TOPICS:
        im = Image.open(HERE / t["src"]).convert("RGB")
        for box in t.get("blur", []):                       # blur a region of the source (a label) with soft edges, then crop
            mask = Image.new("L", im.size, 0)
            mask.paste(255, box)
            im = Image.composite(im.filter(ImageFilter.GaussianBlur(28)), im, mask.filter(ImageFilter.GaussianBlur(26)))
        if t["crop"]:
            im = im.crop(t["crop"])
        for folder, (w, h) in SIZES.items():
            out = HERE / folder / f"{t['slug']}.jpg"
            fit(im, w, h).save(out, quality=88, optimize=True)
            print(f"{out.relative_to(HERE)}  {w}x{h}  <- {t['src']}{' crop ' + str(t['crop']) if t['crop'] else ''}")


if __name__ == "__main__":
    main()
