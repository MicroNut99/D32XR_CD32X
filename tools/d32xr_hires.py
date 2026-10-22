"""Downsampling the 1K texture pack to the textures' native size, in the game's palette."""
import io, zipfile
import numpy as np
from PIL import Image

def srgb_to_lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return 255.0 * np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)

def lin_to_lab(rgb):
    m = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = rgb @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)

class Palette:
    def __init__(self, pal768, exclude=()):
        p = np.frombuffer(pal768, np.uint8).reshape(256, 3).astype(np.float64)
        self.lin = srgb_to_lin(p)
        self.lab = lin_to_lab(self.lin)
        self.ok = np.ones(256, bool)
        for i in exclude: self.ok[i] = False
    def nearest(self, lab):                       # lab: (..., 3)
        d = ((lab[..., None, :] - self.lab[None, :, :]) ** 2).sum(-1)
        d[..., ~self.ok] = 1e18
        return d.argmin(-1)

def area_resize_linear(img, w, h):
    """area average in linear light (exact box filter for integer factors, else via PIL BOX on 16-bit)"""
    a = srgb_to_lin(np.asarray(img.convert('RGB'), np.float64))
    H, W = a.shape[:2]
    if W % w == 0 and H % h == 0:
        return a.reshape(h, H // h, w, W // w, 3).mean(axis=(1, 3))
    out = []
    for c in range(3):
        ch = Image.fromarray((a[..., c] * 65535).astype(np.uint16).astype(np.int32), 'I')
        out.append(np.asarray(ch.resize((w, h), Image.BOX), np.float64) / 65535)
    return np.stack(out, -1)

def to_palette(lin, pal, dither=0.0, sharpen=0.0):
    """linear RGB (h, w, 3) -> palette indices (h, w); optional unsharp mask and error diffusion (in linear light)"""
    if sharpen:
        from scipy.ndimage import gaussian_filter
        blur = np.stack([gaussian_filter(lin[..., c], 0.7, mode='wrap') for c in range(3)], -1)
        lin = np.clip(lin + sharpen * (lin - blur), 0, 1)
    if not dither:
        return pal.nearest(lin_to_lab(lin))
    h, w = lin.shape[:2]
    buf = lin.copy(); idx = np.zeros((h, w), np.int64)
    for y in range(h):
        xs = range(w) if y % 2 == 0 else range(w - 1, -1, -1)     # serpentine
        sgn = 1 if y % 2 == 0 else -1
        for x in xs:
            c = buf[y, x]; i = pal.nearest(lin_to_lab(c[None, :]))[0]
            idx[y, x] = i; e = (c - pal.lin[i]) * dither
            if 0 <= x + sgn < w: buf[y, x + sgn] += e * 7 / 16
            if y + 1 < h:
                if 0 <= x - sgn < w: buf[y + 1, x - sgn] += e * 3 / 16
                buf[y + 1, x] += e * 5 / 16
                if 0 <= x + sgn < w: buf[y + 1, x + sgn] += e * 1 / 16
    return idx

class Pack:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.files = {n.split('/')[-1].rsplit('.', 1)[0].upper(): n for n in self.z.namelist() if n.lower().endswith('.png')}
    def has(self, name): return name.upper() in self.files
    def image(self, name): return Image.open(io.BytesIO(self.z.read(self.files[name.upper()])))
