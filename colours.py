import random
import spectrum

def cmyk2rgb(cmyk):
    c, m, y, k = cmyk
    r = 255 * (1 - c / 100) * (1 - k / 100)
    g = 255 * (1 - m / 100) * (1 - k / 100)
    b = 255 * (1 - y / 100) * (1 - k / 100)
    return (int(r), int(g), int(b))

# Colour palettes from Spectrum published by Thames & Hudson
palettes = [[cmyk2rgb(col) for col in palette] for palette in spectrum.palettes]

active_palette = None

def randomize_palette():
    global active_palette
    active_palette = random.choice(palettes)

def hsv2rgb(h,s,v):
    return (round(i * 255) for i in colorsys.hls_to_rgb(h/256,s/256,v/256))

def rand_rgb():
    return (random.randrange(256), random.randrange(256), random.randrange(256))

def rand_from_palette(exclude=None):
    pal = active_palette.copy()
    try:
        if len(pal) > 1 and exclude is not None:
            pal.remove(exclude)
    except ValueError:
        pass
    return random.choice(pal)

randomize_palette()