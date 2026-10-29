from PIL import Image, ImageDraw

def draw_mic_icon(filename, active=False):
    size = (64, 64)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Colors
    bg_fill = (16, 185, 129, 255) if active else (51, 65, 85, 255)
    border = (52, 211, 153, 255) if active else (71, 85, 105, 255)
    icon_color = (255, 255, 255, 255)

    # Background circle
    draw.ellipse([4, 4, 60, 60], fill=bg_fill, outline=border, width=2)

    # Microphone capsule
    # Capsule center at x=32, y=24
    draw.rounded_rectangle([26, 16, 38, 34], radius=6, fill=icon_color)

    # Arc / U-holder around capsule
    draw.arc([22, 22, 42, 40], start=0, end=180, fill=icon_color, width=3)

    # Base stem and stand
    draw.line([32, 40, 32, 48], fill=icon_color, width=3)
    draw.line([25, 48, 39, 48], fill=icon_color, width=3)

    img.save(filename, format="PNG")

draw_mic_icon("assets/mic_idle.png", active=False)
draw_mic_icon("assets/mic_active.png", active=True)
print("Created assets/mic_idle.png and assets/mic_active.png successfully!")
