"""Draw Nodavira's project-specific vector geometry and Windows icon.

No downloaded artwork or font files. SVG and ICO share the same coordinates.
Pillow is a build-time dependency only.
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
INK = '#201b32'
VIOLET = '#7252db'
LILAC = '#c7b6ff'
AMBER = '#f5bd64'
PAPER = '#f7f5fb'
RIBBON = [(14,48),(14,16),(23,16),(42,42),(42,29),(50,29),
          (50,48),(41,48),(22,22),(22,48)]
GLYPHS = {
    'N': 'M0 32V0L22 32V0',
    'O': 'M8 0H14Q22 0 22 8V24Q22 32 14 32H8Q0 32 0 24V8Q0 0 8 0Z',
    'D': 'M0 0H10Q22 0 22 12V20Q22 32 10 32H0Z',
    'A': 'M0 32L11 0L22 32M5 20H17',
    'V': 'M0 0L11 32L22 0',
    'I': 'M4 0H18M11 0V32M4 32H18',
    'R': 'M0 32V0H13Q22 0 22 8Q22 16 13 16H0M12 16L23 32',
}


def mark(color=LILAC, accent=AMBER):
    points = ' '.join(f'{x},{y}' for x,y in RIBBON)
    return (f'<polygon points="{points}" fill="{color}"/>'
            f'<rect x="42" y="16" width="8" height="8" rx="2" fill="{accent}"/>')


def wordmark(color=INK):
    # Letterforms drawn on a 22 x 32 grid; no font embedding/substitution.
    letters = ''.join(f'<path transform="translate({i*36} 0)" d="{GLYPHS[c]}"/>'
                      for i,c in enumerate('NODAVIRA'))
    return (f'<g transform="translate(82 16)" fill="none" stroke="{color}" '
            f'stroke-width="3" stroke-linejoin="round" stroke-linecap="round">{letters}</g>')


def svg(width, height, content, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="{title}"><title>{title}</title>{content}</svg>\n')


def main():
    brand = ROOT/'brand'
    brand.mkdir(exist_ok=True)
    tile = f'<rect width="64" height="64" rx="16" fill="{INK}"/>'
    (ROOT/'static/favicon.svg').write_text(svg(64,64,tile+mark(),'Nodavira'),encoding='utf-8')
    (brand/'mark.svg').write_text(svg(64,64,mark(VIOLET),'Nodavira — símbolo'),encoding='utf-8')
    (brand/'wordmark.svg').write_text(svg(380,64,mark(VIOLET)+wordmark(),'Nodavira'),encoding='utf-8')
    (ROOT/'static/wordmark.svg').write_text(svg(380,64,mark()+wordmark(PAPER),'Nodavira'),encoding='utf-8')
    (brand/'wordmark-light.svg').write_text((ROOT/'static/wordmark.svg').read_text(encoding='utf-8'),encoding='utf-8')

    scale=16
    icon=Image.new('RGBA',(64*scale,64*scale))
    draw=ImageDraw.Draw(icon)
    draw.rounded_rectangle((0,0,64*scale-1,64*scale-1),radius=16*scale,fill=INK)
    draw.polygon([(x*scale,y*scale) for x,y in RIBBON],fill=LILAC)
    draw.rounded_rectangle((42*scale,16*scale,50*scale,24*scale),radius=2*scale,fill=AMBER)
    icon=icon.resize((256,256),Image.Resampling.LANCZOS)
    icon.save(ROOT/'static/app.ico',sizes=[(n,n) for n in (16,20,24,32,40,48,64,128,256)])
    icon.save(brand/'app-icon.png')
    icon.save(ROOT/'static/app.png')

    # Editable GitHub banner: geometric wordmark rather than a font-based image.
    banner=(f'<rect width="1200" height="360" rx="24" fill="{INK}"/>'
            f'<path d="M860 0L1110 360M990 0L1200 305" stroke="#332948" stroke-width="70"/>'
            f'<g transform="translate(72 85) scale(2.15)">{mark()+wordmark(PAPER)}</g>'
            f'<path d="M102 267H178" stroke="{AMBER}" stroke-width="5"/>'
            '<text x="201" y="273" fill="#d4cddd" font-family="Segoe UI,Arial,sans-serif" '
            'font-size="21" letter-spacing="2">CLAREZA EM CADA CONSULTA.</text>')
    (brand/'banner.svg').write_text(svg(1200,360,banner,'Nodavira — Clareza em cada consulta'),encoding='utf-8')
    print('Nodavira: vetores, PNG e ICO (9 tamanhos) gerados.')


if __name__=='__main__':
    main()
