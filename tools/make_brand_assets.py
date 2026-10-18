"""生成 Home Assistant 集成的品牌图标（icon.png / logo.png）。

纯程序绘制，不依赖外部素材：

    python make_brand_assets.py

输出到 ../custom_components/fotile_dishwasher/brand/
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "custom_components" / "fotile_dishwasher" / "brand"

BG = (37, 99, 235)  # 蓝色圆角底
FG = (255, 255, 255)  # 白色洗碗机轮廓


def draw_icon(size: int) -> Image.Image:
    scale = 4  # 超采样，边缘更平滑
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 圆角方形背景
    radius = int(s * 0.22)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=radius, fill=BG)

    # 洗碗机机身
    body_w = s * 0.56
    body_h = s * 0.62
    x0 = (s - body_w) / 2
    y0 = (s - body_h) / 2
    body = [x0, y0, x0 + body_w, y0 + body_h]
    d.rounded_rectangle(body, radius=int(s * 0.06), outline=FG, width=int(s * 0.045))

    # 顶部控制条
    d.line(
        [(x0 + s * 0.02, y0 + body_h * 0.26), (x0 + body_w - s * 0.02, y0 + body_h * 0.26)],
        fill=FG,
        width=int(s * 0.035),
    )
    # 控制条上的旋钮
    knob_r = s * 0.045
    kx = x0 + body_w * 0.78
    ky = y0 + body_h * 0.13
    d.ellipse([kx - knob_r, ky - knob_r, kx + knob_r, ky + knob_r], outline=FG, width=int(s * 0.028))

    # 下方碗碟示意：两个圆弧
    arc_box = [
        x0 + body_w * 0.18,
        y0 + body_h * 0.45,
        x0 + body_w * 0.82,
        y0 + body_h * 0.85,
    ]
    d.arc(arc_box, start=200, end=340, fill=FG, width=int(s * 0.045))
    arc_box2 = [
        x0 + body_w * 0.28,
        y0 + body_h * 0.52,
        x0 + body_w * 0.72,
        y0 + body_h * 0.82,
    ]
    d.arc(arc_box2, start=200, end=340, fill=FG, width=int(s * 0.035))

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    icon = draw_icon(256)
    icon.save(OUT / "icon.png", "PNG")
    logo = draw_icon(256)
    logo.save(OUT / "logo.png", "PNG")
    print(f"已生成: {OUT / 'icon.png'}")
    print(f"已生成: {OUT / 'logo.png'}")


if __name__ == "__main__":
    main()
