# -*- coding: utf-8 -*-
"""
柔術日記 Instagram カード一括生成
usage: python3 generate_cards.py [--only 2026-08-01]

content/queue.json を読み、output/{date}_{lang}.png を生成する。
必要フォント: Noto Sans CJK / Noto Serif CJK
  Ubuntu: sudo apt install fonts-noto-cjk fonts-noto-cjk-extra
  macOS : brew install --cask font-noto-sans-cjk-jp font-noto-serif-cjk-jp
"""
import argparse
import glob
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W = H = 1080

# ---- palette: 道着とベルト ----
GI_NAVY    = (23, 36, 61)
GI_WHITE   = (241, 237, 227)
BELT_BLACK = (11, 11, 13)
RANK_RED   = (178, 35, 53)
FADE       = (168, 177, 196)

HANDLES = {"ja": "@bjj.diary.jp", "en": "@bjj.diary"}

EYEBROWS = {
    "tips":    {"ja": ("TRAINING TIPS", "柔術日記"), "en": ("TRAINING TIPS", "BJJ DIARY")},
    "quote":   {"ja": ("ON THE MATS", "今日の一言"), "en": ("ON THE MATS", "BJJ DIARY")},
    "feature": {"ja": ("WHY 柔術日記", "アプリのこと"), "en": ("WHY BJJ DIARY", "THE APP")},
    "trivia":  {"ja": ("BJJ TRIVIA", "柔術豆知識"), "en": ("BJJ TRIVIA", "BJJ DIARY")},
}


def find_font(patterns):
    dirs = [
        "/usr/share/fonts/opentype/noto",
        "/usr/share/fonts/truetype/noto",
        os.path.expanduser("~/Library/Fonts"),
        "/Library/Fonts", "/System/Library/Fonts",
    ]
    for d in dirs:
        for p in patterns:
            hits = glob.glob(os.path.join(d, p))
            if hits:
                return hits[0]
    sys.exit(f"フォントが見つかりません: {patterns} — READMEのフォント項を参照")


SANS_BLACK = find_font(["NotoSansCJK-Black.ttc", "NotoSansCJKjp-Black.otf", "NotoSansJP-Black.*"])
SANS_REG   = find_font(["NotoSansCJK-Regular.ttc", "NotoSansCJKjp-Regular.otf", "NotoSansJP-Regular.*"])
SANS_MED   = find_font(["NotoSansCJK-Medium.ttc", "NotoSansCJKjp-Medium.otf", "NotoSansJP-Medium.*"])
SERIF_BLK  = find_font(["NotoSerifCJK-Black.ttc", "NotoSerifCJKjp-Black.otf", "NotoSerifJP-Black.*"])


def font(path, size):
    return ImageFont.truetype(path, size, index=0)


def weave_texture(img):
    d = ImageDraw.Draw(img, "RGBA")
    step = 14
    for y in range(0, H, step):
        off = (y // step % 2) * step // 2
        for x in range(-step, W + step, step):
            d.ellipse([x + off, y, x + off + 3, y + 3], fill=(255, 255, 255, 7))
    return img


def belt_bar(d, handle):
    top = H - 150
    d.rectangle([0, top, W, H], fill=BELT_BLACK)
    rb_x0, rb_x1 = W - 340, W - 120
    d.rectangle([rb_x0, top, rb_x1, H], fill=RANK_RED)
    for i in range(2):
        sx = rb_x0 + 46 + i * 60
        d.rectangle([sx, top, sx + 22, H], fill=GI_WHITE)
    d.text((60, top + 55), handle, font=font(SANS_MED, 34), fill=GI_WHITE)


def eyebrow(d, en, jp, y=92):
    f_en = font(SANS_MED, 30)
    d.text((80, y), en, font=f_en, fill=RANK_RED)
    w = d.textlength(en, font=f_en)
    d.text((80 + w + 28, y), "｜ " + jp, font=font(SANS_REG, 30), fill=FADE)
    d.rectangle([80, y + 58, 80 + 64, y + 63], fill=RANK_RED)


def multiline(d, lines, fnt, x, y, fill, lh):
    for ln in lines:
        d.text((x, y), ln, font=fnt, fill=fill)
        y += lh
    return y


def fit_size(d, lines, path, start, min_size, max_w):
    """max_w に収まる最大フォントサイズを探す"""
    size = start
    while size > min_size:
        f = font(path, size)
        if all(d.textlength(ln, font=f) <= max_w for ln in lines):
            return size
        size -= 4
    return min_size


def render(entry, lang):
    data = entry[lang]
    ctype = entry.get("type", "tips")
    img = weave_texture(Image.new("RGB", (W, H), GI_NAVY))
    d = ImageDraw.Draw(img)

    en, jp = EYEBROWS.get(ctype, EYEBROWS["tips"])[lang]
    eyebrow(d, en, jp)

    headline = data["headline"]
    sub = data.get("sub", [])

    if ctype == "quote":
        size = fit_size(d, headline, SERIF_BLK, 100, 56, W - 160)
        f_head = font(SERIF_BLK, size)
    else:
        size = fit_size(d, headline, SANS_BLACK, 112, 56, W - 160)
        f_head = font(SANS_BLACK, size)

    lh = int(size * 1.3)
    block_h = len(headline) * lh + (len(sub) * 60 + 55 if sub else 0)
    y0 = max(230, (170 + (H - 150) - block_h) // 2)  # eyebrow下〜帯上で概ね中央
    y = multiline(d, headline, f_head, 80, y0, GI_WHITE, lh)
    if sub:
        multiline(d, sub, font(SANS_REG, 38), 80, y + 55, FADE, 58)

    belt_bar(d, HANDLES[lang])
    out = f"output/{entry['date']}_{lang}.png"
    img.save(out)
    print("generated:", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="特定日のみ生成 (YYYY-MM-DD)")
    args = ap.parse_args()

    os.makedirs("output", exist_ok=True)
    with open("content/queue.json", encoding="utf-8") as f:
        queue = json.load(f)

    for entry in queue:
        if args.only and entry["date"] != args.only:
            continue
        for lang in ("ja", "en"):
            if lang in entry:
                render(entry, lang)


if __name__ == "__main__":
    main()
