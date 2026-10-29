import os
from PIL import Image, ImageDraw, ImageFilter

os.makedirs("assets", exist_ok=True)

size = (256, 256)
img = Image.new("RGBA", size, (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

margin = 12
radius = 48
draw.rounded_rectangle(
    [margin, margin, size[0] - margin, size[1] - margin],
    radius=radius,
    fill=(15, 23, 42, 255),
    outline=(56, 189, 248, 180),
    width=3,
)

glow_layer = Image.new("RGBA", size, (0, 0, 0, 0))
glow_draw = ImageDraw.Draw(glow_layer)
glow_draw.ellipse([60, 60, 196, 196], fill=(14, 165, 233, 40))
glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(16))
img = Image.alpha_composite(img, glow_layer)
draw = ImageDraw.Draw(img)

bars = [
    (76, 128, 24),
    (96, 128, 48),
    (116, 128, 76),
    (136, 128, 92),
    (156, 128, 64),
    (176, 128, 36),
]

colors = [
    (56, 189, 248),
    (59, 130, 246),
    (99, 102, 241),
    (129, 140, 248),
    (168, 85, 247),
    (192, 132, 252),
]

for (x, cy, h), color in zip(bars, colors):
    y0 = cy - h // 2
    y1 = cy + h // 2
    draw.rounded_rectangle([x - 5, y0, x + 5, y1], radius=5, fill=(*color, 255))

draw.ellipse([136 - 6, 128 - 46 - 16, 136 + 6, 128 - 46 - 4], fill=(244, 63, 94, 255))

img.save("assets/icon.png", format="PNG")
img.save("assets/icon.ico", format="ICO", sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
