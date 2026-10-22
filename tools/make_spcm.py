#!/usr/bin/env python3
"""make_spcm.py - SIGIL's and SIGIL II's music as D32XR streamed PCM files (SPCM) for the data track.

  make_spcm.py <folder with Track02.wav .. Track23.wav> <disc files folder>

Track02-12 -> SIGIL/D_INTRO.PCM, D_E5M1.PCM .. D_E5M9.PCM, D_INTER.PCM
Track13-23 -> SIGIL2/D_INTRO.PCM, D_E6M1.PCM .. D_E6M9.PCM, D_INTER.PCM
(the WADs' spcmDirs and music lump names, tools/make_game.py; the game streams them from the
data track through the Sega CD's PCM chip, d32xr/src-md/cd/s_spcm.c)

The file format is d32xr/raw2spcm's: a 2048-byte header sector ("SPCM", the sample rate and the
PCM chip's increment, big-endian, and the channel count), then the samples in 2048-byte sectors,
left and right sectors taking turns, 8-bit sign + magnitude (bit 7 set = positive, magnitude up
to 126: 0xFF is the chip's loop marker), then a silent sector.

The sound: resampled to 24453 Hz (the PCM chip's increment 0x600, the rate s_spcm.c names) in the
frequency domain (band-limited, no aliasing); one gain for all 22 songs so the loudest peak of
them all sits just under full scale (the songs keep their levels against each other); TPDF
dither into the 8 bits. NumPy only.
"""
import os, sys, wave
import numpy as np

RATE = 24453
INCR = RATE * 2048 // 32604          # 0x600
SECTOR = 2048

SONGS = {'SIGIL': ['D_INTRO'] + ['D_E5M%d' % k for k in range(1, 10)] + ['D_INTER'],
         'SIGIL2': ['D_INTRO'] + ['D_E6M%d' % k for k in range(1, 10)] + ['D_INTER']}


def read_wav(path):
    w = wave.open(path, 'rb')
    if w.getsampwidth() != 2:
        sys.exit('%s: needs 16-bit PCM' % path)
    ch, sr = w.getnchannels(), w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float64) / 32768.0
    x = x.reshape(-1, ch)
    if ch == 1:
        x = np.repeat(x, 2, axis=1)
    return x[:, :2], sr


def resample(x, sr, rate):
    """band-limited resampling of each channel (FFT: drop / pad the spectrum)"""
    n = len(x)
    m = int(round(n * rate / sr))
    out = np.empty((m, x.shape[1]))
    for c in range(x.shape[1]):
        X = np.fft.rfft(x[:, c])
        k = m // 2 + 1
        Y = np.zeros(k, complex)
        k0 = min(k, len(X))
        Y[:k0] = X[:k0]
        out[:, c] = np.fft.irfft(Y, m) * (m / n)
    return out


def to_spcm(x, gain, rng):
    """float samples -> sign + magnitude bytes (raw2spcm's rawu82spcm on 8-bit)"""
    v = x * gain * 126.0 + (rng.random(x.shape) - rng.random(x.shape))     # TPDF dither
    v = np.clip(np.round(v), -126, 126).astype(np.int16)
    return np.where(v > 0, v | 128, -v).astype(np.uint8)


def write_spcm(path, pcm):
    n = len(pcm)
    blocks = (n + SECTOR - 1) // SECTOR
    hdr = bytearray(SECTOR)
    hdr[0:4] = b'SPCM'
    hdr[4:6] = RATE.to_bytes(2, 'big')
    hdr[6:8] = INCR.to_bytes(2, 'big')
    hdr[8] = 2
    body = np.zeros((blocks, 2, SECTOR), np.uint8)              # sector by sector: left, right
    pad = np.zeros((blocks * SECTOR, 2), np.uint8)
    pad[:n] = pcm
    body[:, 0, :] = pad[:, 0].reshape(blocks, SECTOR)
    body[:, 1, :] = pad[:, 1].reshape(blocks, SECTOR)
    with open(path, 'wb') as f:
        f.write(bytes(hdr))
        f.write(body.tobytes())
        f.write(bytes(SECTOR))                                   # the silent end sector


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out = sys.argv[1], sys.argv[2]
    jobs = []
    t = 2
    for d in ('SIGIL', 'SIGIL2'):
        for song in SONGS[d]:
            p = os.path.join(src, 'Track%02d.wav' % t)
            if not os.path.exists(p):
                sys.exit('missing %s' % p)
            jobs.append((p, d, song))
            t += 1
    # one gain for all of them: the loudest peak just under full scale
    peak = 0.0
    for p, _, _ in jobs:
        x, _ = read_wav(p)
        peak = max(peak, float(np.abs(x).max()))
    gain = 0.97 / peak if peak > 0 else 1.0
    rng = np.random.default_rng(0x51611)
    total = 0
    for p, d, song in jobs:
        x, sr = read_wav(p)
        y = resample(x, sr, RATE)
        os.makedirs(os.path.join(out, d), exist_ok=True)
        dst = os.path.join(out, d, song + '.PCM')
        write_spcm(dst, to_spcm(y, gain, rng))
        total += os.path.getsize(dst)
        print('  %-28s %6.1f s  %5.1f MB' % ('%s/%s.PCM' % (d, song), len(y) / RATE, os.path.getsize(dst) / 1e6))
    print('SPCM: 22 songs, %.0f MB, gain %+.1f dB' % (total / 1e6, 20 * np.log10(gain)))


if __name__ == '__main__':
    main()
