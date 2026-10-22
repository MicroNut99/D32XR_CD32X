#!/usr/bin/env python3
"""make_splash.py <picture or -> <IMAGE.RAW>

The loading screen the CD loader shows while it copies the game into the RAM cart: 320 x 224
pixels, one byte each (as the 32X frame buffer holds them from byte 0x200 on), then the 256
palette entries (32X colour words, big-endian), then 320 x 9 text strips (STRIP_TEXTS) that the
loader copies under the bar (lines 214-222): "FIRST TIME: COPYING DOOM INTO THE RAM CART" when
the cart does not hold the game (or a WAD of the preload) yet, "THIS DISC NEEDS THE 8 MB OR
16 MB RAM CART" on a 4 MB cart. The loader draws the progress bar itself with entries 253 (empty), 254
(filled) and 255 (frame), at lines 203-213 (BAR_Y0 / BAR_Y1 of cdloader_sh2.c).

The picture (data/splash.png: the DOOM logo the user chose, kept in data/, never committed) is
scaled to fit 304 x 192 pixels, centred at the top, on black. With "-" instead of a picture: a
black screen with the bar only.
"""
import struct
import sys

from PIL import Image

W, H = 320, 224
BLACK = 252

# a 5 x 7 font for the line under the bar (no font files needed on the build machine)
FONT = {
    'A': ['01110', '10001', '10001', '11111', '10001', '10001', '10001'],
    'B': ['11110', '10001', '10001', '11110', '10001', '10001', '11110'],
    'C': ['01110', '10001', '10000', '10000', '10000', '10001', '01110'],
    'D': ['11110', '10001', '10001', '10001', '10001', '10001', '11110'],
    'E': ['11111', '10000', '10000', '11110', '10000', '10000', '11111'],
    'F': ['11111', '10000', '10000', '11110', '10000', '10000', '10000'],
    'G': ['01110', '10001', '10000', '10111', '10001', '10001', '01111'],
    'H': ['10001', '10001', '10001', '11111', '10001', '10001', '10001'],
    'I': ['01110', '00100', '00100', '00100', '00100', '00100', '01110'],
    'K': ['10001', '10010', '10100', '11000', '10100', '10010', '10001'],
    'L': ['10000', '10000', '10000', '10000', '10000', '10000', '11111'],
    'M': ['10001', '11011', '10101', '10101', '10001', '10001', '10001'],
    'N': ['10001', '11001', '10101', '10011', '10001', '10001', '10001'],
    'O': ['01110', '10001', '10001', '10001', '10001', '10001', '01110'],
    'P': ['11110', '10001', '10001', '11110', '10000', '10000', '10000'],
    'R': ['11110', '10001', '10001', '11110', '10100', '10010', '10001'],
    'S': ['01111', '10000', '10000', '01110', '00001', '00001', '11110'],
    'T': ['11111', '00100', '00100', '00100', '00100', '00100', '00100'],
    'U': ['10001', '10001', '10001', '10001', '10001', '10001', '01110'],
    'V': ['10001', '10001', '10001', '10001', '10001', '01010', '00100'],
    'W': ['10001', '10001', '10001', '10101', '10101', '10101', '01010'],
    'Y': ['10001', '10001', '01010', '00100', '00100', '00100', '00100'],
    '0': ['01110', '10001', '10011', '10101', '11001', '10001', '01110'],
    '1': ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
    '2': ['01110', '10001', '00001', '00010', '00100', '01000', '11111'],
    '3': ['11111', '00010', '00100', '00010', '00001', '10001', '01110'],
    '4': ['00010', '00110', '01010', '10010', '11111', '00010', '00010'],
    '5': ['11111', '10000', '11110', '00001', '00001', '10001', '01110'],
    '6': ['00110', '01000', '10000', '11110', '10001', '10001', '01110'],
    '7': ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
    '8': ['01110', '10001', '10001', '01110', '10001', '10001', '01110'],
    '9': ['01110', '10001', '10001', '01111', '00001', '00010', '01100'],
    ':': ['00000', '00100', '00100', '00000', '00100', '00100', '00000'],
    '-': ['00000', '00000', '00000', '01110', '00000', '00000', '00000'],
    '.': ['00000', '00000', '00000', '00000', '00000', '00100', '00100'],
    ',': ['00000', '00000', '00000', '00000', '00100', '00100', '01000'],
    ' ': ['00000'] * 7,
}
STRIP_H = 9          # lines of the text strip (the loader copies it to lines 214-222)
STRIP_TEXTS = ['FIRST TIME: COPYING DOOM INTO THE RAM CART',     # 0: the cart does not hold it (yet)
               'THIS DISC NEEDS THE 8 MB OR 16 MB RAM CART']      # 1: a 4 MB cart (the loader stops)


def text_strip(text, colour, back):
    """320 x STRIP_H bytes: the text centred, one pixel per font dot, 6 pixels a letter."""
    strip = bytearray([back]) * (W * STRIP_H)
    x0 = (W - 6 * len(text)) // 2
    for n, ch in enumerate(text):
        rows = FONT[ch]
        for y in range(7):
            for x in range(5):
                if rows[y][x] == '1':
                    strip[(y + 1) * W + x0 + 6 * n + x] = colour
    return strip


def compose(path):
    pic = Image.open(path).convert('RGB')
    scale = min(304 / pic.width, 192 / pic.height)
    pic = pic.resize((int(pic.width * scale), int(pic.height * scale)), Image.LANCZOS)
    out = Image.new('RGB', (W, H), (0, 0, 0))
    out.paste(pic, ((W - pic.width) // 2, 4 + (192 - pic.height) // 2))
    return out


def to32x(r, g, b):
    v = (r >> 3) | (g >> 3) << 5 | (b >> 3) << 10
    return v or 0x0400


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    pix = bytearray([BLACK]) * (W * H)
    pal = [(0, 0, 0)] * 256
    if sys.argv[1] != '-':
        img = compose(sys.argv[1])
        q = img.quantize(colors=250, method=Image.MEDIANCUT, dither=Image.NONE)
        qp = q.getpalette()[:250 * 3]
        data = q.tobytes()
        for i in range(250):
            pal[1 + i] = tuple(qp[i * 3:i * 3 + 3])
        pix = bytearray(1 + v for v in data)     # entries 1-250; 0 and 252 stay black
    pal[253] = (48, 10, 0)        # the bar: empty
    pal[254] = (255, 190, 40)     # filled (the logo's gold)
    pal[255] = (255, 255, 255)    # frame
    out = bytes(pix) + b''.join(struct.pack('>H', to32x(*rgb)) for rgb in pal)
    # after the palette: the lines the loader can show under the bar (STRIP_TEXTS), text 255,
    # back 252
    for text in STRIP_TEXTS:
        out += bytes(text_strip(text, 255, BLACK))
    open(sys.argv[2], 'wb').write(out)
    print('loading screen: %s (%d bytes)' % (sys.argv[2], len(out)))


if __name__ == '__main__':
    main()
