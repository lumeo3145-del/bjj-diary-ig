# -*- coding: utf-8 -*-
"""
単発の告知カード生成（自動投稿のキューとは別枠）
usage: python3 generate_promo.py

日々の投稿とは意図的にフォーマットを変えている。特別感を出すため:
  - 濃紺ではなくブラジルカラー（緑地＋黄のひし形）
  - 端末は傾けず正面、画面全体を見せる
  - 帯バーは細くしてハンドルのみ
出力: output/promo_pt_launch.png
"""
import os

from PIL import Image, ImageDraw, ImageFilter

from generate_cards import SANS_BLACK, SANS_MED, SANS_REG, font

W = H = 1080

# ---- ブラジル国旗由来のパレット ----
BR_GREEN      = (0, 105, 47)
BR_GREEN_DEEP = (0, 74, 33)
BR_YELLOW     = (255, 205, 0)
BR_BLUE       = (0, 39, 118)
CREAM         = (250, 247, 240)
INK           = (26, 26, 26)

SHOT = "assets/mock_pt_journal.png"
OUT = "output/promo_pt_launch.png"


def background():
    """緑のグラデーション地に、黄のひし形をうっすら重ねる"""
    img = Image.new("RGB", (W, H), BR_GREEN)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=tuple(int(a + (b - a) * t) for a, b in zip(BR_GREEN, BR_GREEN_DEEP)))

    # 端末の背後に来るよう右寄りに配置したひし形（国旗のモチーフ）
    cx, cy, rx, ry = 812, 520, 430, 470
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).polygon(
        [(cx, cy - ry), (cx + rx, cy), (cx, cy + ry), (cx - rx, cy)],
        fill=BR_YELLOW + (46,),
    )
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"), (0, 0))
    return img


def phone(img, height=720, cx=812, cy=520):
    ph = Image.open(SHOT).convert("RGBA")
    r = height / ph.height
    ph = ph.resize((int(ph.width * r), height), Image.LANCZOS)
    x, y = cx - ph.width // 2, cy - ph.height // 2

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.paste(Image.new("RGBA", ph.size, (0, 30, 12, 130)), (x + 10, y + 22), ph.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    img.paste(Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB"), (0, 0))
    img.paste(ph, (x, y), ph)
    return img


def app_lockup(img, d, x=80, y=92, size=88):
    icon = Image.open("assets/app-icon.png").convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], size // 4, fill=255)
    img.paste(icon, (x, y), mask)
    d.text((x + size + 26, y + 8), "BJJ DIARY", font=font(SANS_MED, 34), fill=CREAM)
    d.text((x + size + 28, y + 50), "iOS", font=font(SANS_REG, 26), fill=BR_YELLOW)


def badge(d, text, x, y):
    f = font(SANS_MED, 30)
    w = d.textlength(text, font=f)
    d.rounded_rectangle([x, y, x + w + 44, y + 58], 29, fill=BR_YELLOW)
    d.text((x + 22, y + 12), text, font=f, fill=BR_BLUE)
    return y + 58


def handle_bar(d):
    top = H - 108
    d.rectangle([0, top, W, H], fill=(11, 11, 13))
    d.rectangle([0, top, W, top + 7], fill=BR_YELLOW)
    d.text((80, top + 34), "@bjj.diary", font=font(SANS_MED, 34), fill=CREAM)
    cta = "Free on the App Store"
    f = font(SANS_REG, 30)
    d.text((W - 80 - d.textlength(cta, font=f), top + 38), cta, font=f, fill=(150, 150, 150))


def main():
    os.makedirs("output", exist_ok=True)
    img = phone(background())
    d = ImageDraw.Draw(img)

    app_lockup(img, d)
    badge(d, "NOVIDADE", 80, 250)

    y = 342
    for ln in ["Agora em", "português."]:
        d.text((80, y), ln, font=font(SANS_BLACK, 88), fill=CREAM)
        y += 108
    d.rectangle([80, y + 24, 80 + 92, y + 30], fill=BR_YELLOW)

    y += 72
    for ln in ["Diário, notas, drills e estatísticas —", "o app inteiro em português."]:
        d.text((80, y), ln, font=font(SANS_REG, 32), fill=(222, 233, 222))
        y += 46

    y += 36
    for ln in ["BJJ Diary is now fully", "available in Portuguese."]:
        d.text((80, y), ln, font=font(SANS_MED, 30), fill=(176, 203, 179))
        y += 42

    handle_bar(d)
    img.save(OUT)
    print("generated:", OUT)


if __name__ == "__main__":
    main()
