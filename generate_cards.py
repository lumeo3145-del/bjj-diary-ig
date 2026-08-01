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
PT_WHITE   = (206, 205, 200)  # PTブロックの見出し（ENより一段控えめ）
PT_FADE    = (132, 142, 162)  # PTブロックのサブ

HANDLES = {"ja": "@bjj.diary.jp", "en": "@bjj.diary"}

# EN card は英語 ｜ ポルトガル語 のバイリンガル eyebrow
EYEBROWS = {
    "tips":    {"ja": ("TRAINING TIPS", "BJJ DIARY"), "en": ("TRAINING TIPS", "DICAS DE TREINO")},
    "quote":   {"ja": ("ON THE MATS", "今日の一言"), "en": ("ON THE MATS", "NO TATAME")},
    "feature": {"ja": ("WHY BJJ DIARY", "アプリのこと"), "en": ("WHY BJJ DIARY", "SOBRE O APP")},
}

# PT の見出し・サブは EN のこの比率で描画（違和感なく控えめに）
PT_HEAD_RATIO = 0.65
PT_SUB_RATIO  = 0.85


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


def text_item(d, lines, path, start, min_size, max_w, fill, gap, lh_ratio=1.3):
    return {
        "kind": "text",
        "lines": lines,
        "path": path,
        "size": fit_size(d, lines, path, start, min_size, max_w),
        "fill": fill,
        "gap": gap,
        "lh_ratio": lh_ratio,
    }


def rule_item(color, gap, width=64, thickness=4):
    return {"kind": "rule", "color": color, "gap": gap, "width": width, "thickness": thickness}


def draw_stack(d, items, x, top, bottom, align="center", scale=1.0):
    """items を top〜bottom に積む。収まらなければ全体を段階的に縮小
    align="top" は端末画像を避けたいモックアップ用（下ほど画像が張り出すため）"""
    def measure(s):
        h = 0
        for it in items:
            h += int(it["gap"] * s)
            if it["kind"] == "text":
                h += len(it["lines"]) * int(it["size"] * s * it["lh_ratio"])
            else:
                h += it["thickness"] + 10
        return h

    while measure(scale) > bottom - top and scale > 0.6:
        scale -= 0.05

    y = top if align == "top" else max(top, (top + bottom - measure(scale)) // 2)
    for it in items:
        y += int(it["gap"] * scale)
        if it["kind"] == "text":
            size = max(int(it["size"] * scale), 20)
            lh = int(size * it["lh_ratio"])
            y = multiline(d, it["lines"], font(it["path"], size), x, y, it["fill"], lh)
        else:
            d.rectangle([x, y, x + it["width"], y + it["thickness"]], fill=it["color"])
            y += it["thickness"] + 10
    return y


def build_stack(d, data, ctype, head_path, head_start, max_w,
                head_fill, sub_fill, pt_head_fill, pt_sub_fill, rule_color, sub_size):
    """EN見出し／サブ → 区切り → PT見出し／サブ の順に積む"""
    headline = data["headline"]
    sub = data.get("sub", [])
    head_min = 44 if ctype != "quote" else 48

    items = [text_item(d, headline, head_path, head_start, head_min, max_w, head_fill, 0)]
    if sub:
        items.append(text_item(d, sub, SANS_REG, sub_size, 24, max_w, sub_fill,
                               55, lh_ratio=1.5))

    head_size = items[0]["size"]
    pt_head = data.get("headline_pt", [])
    pt_sub = data.get("sub_pt", [])
    if pt_head or pt_sub:
        items.append(rule_item(rule_color, 62))
        if pt_head:
            items.append(text_item(d, pt_head, head_path,
                                   int(head_size * PT_HEAD_RATIO), 34, max_w,
                                   pt_head_fill, 34))
        if pt_sub:
            items.append(text_item(d, pt_sub, SANS_REG, int(sub_size * PT_SUB_RATIO),
                                   22, max_w, pt_sub_fill, 34, lh_ratio=1.5))
    return items


def render(entry, lang):
    data = entry[lang]
    ctype = entry.get("type", "tips")
    if ctype == "mockup":
        return render_mockup(entry, lang)
    img = weave_texture(Image.new("RGB", (W, H), GI_NAVY))
    d = ImageDraw.Draw(img)

    en, jp = EYEBROWS.get(ctype, EYEBROWS["tips"])[lang]
    eyebrow(d, en, jp)

    head_path = SERIF_BLK if ctype == "quote" else SANS_BLACK
    items = build_stack(
        d, data, ctype, head_path, 100 if ctype == "quote" else 112, W - 160,
        head_fill=GI_WHITE, sub_fill=FADE, pt_head_fill=PT_WHITE, pt_sub_fill=PT_FADE,
        rule_color=RANK_RED, sub_size=38,
    )
    draw_stack(d, items, 80, 230, H - 190)

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




# ===== mockup card =====
CREAM      = (250, 247, 240)
RULE_GRAY  = (215, 211, 204)
MARGIN_RED = (234, 92, 78)
INK        = (58, 50, 44)
INK_SOFT   = (135, 126, 117)
INK_FAINT  = (165, 157, 148)  # クリーム面のPTサブ

ASSET_STYLE = {
    "tilt_ja_journal": dict(height=1150, cx=810, cy=560, rotate=0),
    "tilt_ja_drills":  dict(height=1150, cx=810, cy=560, rotate=0),
    "mock_ja_stats":   dict(height=1020, cx=800, cy=545, rotate=-6),
    "mock_ja_notes":   dict(height=1020, cx=800, cy=545, rotate=-6),
    "mock_ja_comp":    dict(height=1020, cx=800, cy=545, rotate=-6),
    "mock_en_stats":   dict(height=1020, cx=800, cy=545, rotate=-6),
    "mock_en_notes":   dict(height=1020, cx=800, cy=545, rotate=-6),
    "mock_en_comp":    dict(height=1020, cx=800, cy=545, rotate=-6),
}


def notebook_bg():
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    for y in range(150, H - 150, 96):
        d.line([(140, y), (W, y)], fill=RULE_GRAY, width=3)
    d.line([(120, 0), (120, H)], fill=MARGIN_RED, width=5)
    return img


def paste_phone(img, asset, style):
    phone = Image.open(f"assets/{asset}.png").convert("RGBA")
    if style["rotate"]:
        phone = phone.rotate(style["rotate"], expand=True, resample=Image.BICUBIC)
    r = style["height"] / phone.height
    phone = phone.resize((int(phone.width * r), style["height"]), Image.LANCZOS)
    alpha = phone.split()[3].point(lambda a: int(a * 0.25))
    sh = Image.new("RGBA", phone.size, (0, 0, 0, 0))
    sh.putalpha(alpha)
    x, y = style["cx"] - phone.width // 2, style["cy"] - phone.height // 2
    img.paste(Image.new("RGB", phone.size, (60, 50, 44)), (x + 14, y + 20), sh)
    img.paste(phone, (x, y), phone)
    return img


def belt_bar_cream(d, handle):
    belt_bar(d, handle)  # 同じ帯バー（黒背景なのでクリームでも成立）


def render_mockup(entry, lang):
    data = entry[lang]
    asset = data["image"]
    style = ASSET_STYLE[asset]
    img = notebook_bg()
    img = paste_phone(img, asset, style)
    d = ImageDraw.Draw(img)
    eb = "WHY BJJ DIARY" if lang == "ja" else "WHY BJJ DIARY ｜ SOBRE O APP"
    f_eb = font(SANS_MED, 30 if lang == "ja" else 26)
    d.text((170, 130), eb, font=f_eb, fill=MARGIN_RED)
    d.rectangle([170, 188, 234, 193], fill=MARGIN_RED)
    # 端末画像の張り出し量に合わせてテキスト幅を決める（tiltは大きく傾き左に食い込む）
    max_w = 385 if lang == "en" else (400 if asset.startswith("tilt") else 420)
    items = build_stack(
        d, data, "mockup", SANS_BLACK, 92, max_w,
        head_fill=INK, sub_fill=INK_SOFT, pt_head_fill=INK_SOFT, pt_sub_fill=INK_FAINT,
        rule_color=MARGIN_RED, sub_size=35,
    )
    draw_stack(d, items, 170, 290, H - 200, align="top")
    belt_bar_cream(d, HANDLES[lang])
    out = f"output/{entry['date']}_{lang}.png"
    img.save(out)
    print("generated:", out)


if __name__ == "__main__":
    main()
