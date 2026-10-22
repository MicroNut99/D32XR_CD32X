#!/usr/bin/env python3
"""make_spcm.py - SIGIL's and SIGIL II's music as D32XR streamed PCM files (SPCM) for the data track.

  make_spcm.py <folder with Track02.wav .. Track23.wav> <disc files folder>

Track02-12 = SIGIL's D_INTRO, D_E5M1 .. D_E5M9, D_INTER; Track13-23 = SIGIL II's D_INTRO, D_E6M1 ..
D_E6M9, D_INTER (tools/make_sigil_cdda.sh). Only the songs SIGIL.WAD / SIGIL_II.WAD in the disc
folder play (their DMAPINFO: title, intermission, victory, end and the maps on the disc) become
SIGIL/<song>.PCM / SIGIL2/<song>.PCM (the WADs' spcmDirs and music lump names, tools/make_game.py;
the game streams them from the data track through the Sega CD's PCM chip, d32xr/src-md/cd/s_spcm.c).

The file format is d32xr/raw2spcm's: a 2048-byte header sector ("SPCM", the sample rate and the
PCM chip's increment, big-endian, and the channel count), then the samples in 2048-byte sectors,
left and right sectors taking turns, 8-bit sign + magnitude (bit 7 set = positive, magnitude up
to 126: 0xFF is the chip's loop marker), then a silent sector.

The sound: mono, resampled to 21396 Hz (the PCM chip's increment 0x540: 25 minutes = 32.5 MB, what
fits beside the IDKFA CD audio and TNT MINI on an 80-minute disc) in the frequency domain (band-limited, no
aliasing); one gain for all the songs so the loudest peak of them all sits just under full scale
(the songs keep their levels against each other); TPDF dither into the 8 bits. NumPy only.
"""
import os, sys, wave
import numpy as np

INCR = 0x540                         # the PCM chip's step: 1.0 = 0x800 = 32604 Hz
RATE = INCR * 32604 // 2048          # 21396 Hz
CHANNELS = 1
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
    x = x[:, :2].mean(axis=1, keepdims=True) if CHANNELS == 1 else (np.repeat(x, 2, axis=1) if ch == 1 else x[:, :2])
    return x, sr


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
    """raw2spcm's layout: header sector, then sectors of samples (stereo: left and right sectors
    taking turns), then a silent sector (the player ignores the last sector)"""
    n, ch = pcm.shape
    blocks = (n + SECTOR - 1) // SECTOR
    hdr = bytearray(SECTOR)
    hdr[0:4] = b'SPCM'
    hdr[4:6] = RATE.to_bytes(2, 'big')
    hdr[6:8] = INCR.to_bytes(2, 'big')
    hdr[8] = ch
    pad = np.zeros((blocks * SECTOR, ch), np.uint8)
    pad[:n] = pcm
    body = np.stack([pad[:, c].reshape(blocks, SECTOR) for c in range(ch)], axis=1)
    with open(path, 'wb') as f:
        f.write(bytes(hdr))
        f.write(body.tobytes())
        f.write(bytes(SECTOR))


def wad_songs(path):
    """the songs a D32XR WAD's DMAPINFO plays: titleMus, intermissionMus, victoryMus, endMus, music"""
    import re, struct
    d = open(path, 'rb').read()
    n, o = struct.unpack('<II', d[4:12])
    for i in range(n):
        p, s, nm = struct.unpack('<II8s', d[o + i * 16:o + i * 16 + 16])
        if nm.split(b'\0')[0] == b'DMAPINFO':
            txt = d[p:p + s].decode('latin1')
            return sorted(set(x.upper() for x in re.findall(r'(?:titleMus|intermissionMus|victoryMus|endMus|music)\s*=\s*"(\w+)"', txt, re.I)))
    return []


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out = sys.argv[1], sys.argv[2]
    jobs = []
    t = 2
    for d, wad in (('SIGIL', 'SIGIL.WAD'), ('SIGIL2', 'SIGIL_II.WAD')):
        used = wad_songs(os.path.join(out, wad)) if os.path.exists(os.path.join(out, wad)) else []
        for song in SONGS[d]:
            p = os.path.join(src, 'Track%02d.wav' % t)
            t += 1
            if song not in used:
                continue
            if not os.path.exists(p):
                sys.exit('missing %s' % p)
            jobs.append((p, d, song))
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
    print('SPCM: %d songs, %.1f MB, %d Hz %s, gain %+.1f dB' % (len(jobs), total / 1e6, RATE, 'mono' if CHANNELS == 1 else 'stereo', 20 * np.log10(gain)))


if __name__ == '__main__':
    main()
