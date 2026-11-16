"""Render browser identity assets. Requires Pillow; run from any directory."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / 'frontend' / 'public'
SCALE = 4
INK = '#101010'
IVORY = '#f5efdf'


def stack(draw, x, y, size):
    def box(a, b, c, d):
        return tuple(round(v * SCALE) for v in (x+a*size, y+b*size, x+c*size, y+d*size))
    for a, b in ((0, .286), (.143, .143), (.286, 0)):
        draw.rounded_rectangle(box(a, b, a+.714, b+.714),
                               radius=round(size*.1*SCALE), fill=INK,
                               outline=IVORY, width=round(size*.08*SCALE))


def font(size, bold=False):
    name = 'Arial Bold.ttf' if bold else 'Arial.ttf'
    return ImageFont.truetype('/System/Library/Fonts/Supplemental/' + name, size*SCALE)


OUT.mkdir(parents=True, exist_ok=True)
icon = Image.new('RGBA', (256*SCALE, 256*SCALE))
d = ImageDraw.Draw(icon)
d.rounded_rectangle((0, 0, 256*SCALE-1, 256*SCALE-1), radius=56*SCALE, fill=INK)
stack(d, 60, 60, 140)
icon = icon.resize((256, 256), Image.Resampling.LANCZOS)
icon.save(OUT / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
icon.resize((180, 180), Image.Resampling.LANCZOS).save(OUT / 'apple-touch-icon.png')

preview = Image.new('RGB', (1200*SCALE, 630*SCALE), INK)
d = ImageDraw.Draw(preview)
stack(d, 305, 140, 230)
d.text((590*SCALE, 135*SCALE), 'EYE', font=font(100, True), fill=IVORY)
d.text((590*SCALE, 235*SCALE), 'TEST', font=font(100, True), fill=IVORY)
d.text((600*SCALE, 445*SCALE), 'Basketball clips.', font=font(50), fill=IVORY, anchor='mm')
preview.resize((1200, 630), Image.Resampling.LANCZOS).save(OUT / 'social-preview.png')
