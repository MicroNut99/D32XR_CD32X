#!/usr/bin/env python3
"""make_sigil_albums.py - the SIGIL disc's CD audio from the albums: Buckethead's SIGIL soundtrack and
THORR's SIGIL II soundtrack (build.sh MUSIC=sigil plays data/sigil_cdda/Track02-23.wav).

  make_sigil_albums.py --sigil <folder: Buckethead's 9 tracks, .flac or .mp3, in album order>
                       --sigil2 <SIGIL_II_MP3_V1_0.WAD>
                       --idkfa <DOOM CD32X FUSION V3 with IDKFA Soundtrack.cue>
                       --out data/sigil_cdda [--cap 300] [--fade 6] [--skip E5M6,E5M7,E6M5,E6M6,E6M7]

The tracks, in the order tools/make_game.py numbers them (title, the 9 maps, intermission):
  Track02     SIGIL title          = the IDKFA disc's track 24 (DOOM / Resurrection's title, D_INTRO)
  Track03-11  E5M1-E5M9            = Buckethead's tracks 1-9 (one per map, in album order)
  Track12     SIGIL intermission   = the IDKFA disc's track 22 (DOOM / Resurrection's D_INTER)
  Track13     SIGIL II title       = the MP3 WAD's D_INTRO
  Track14-22  E6M1-E6M9            = its D_E6M1 .. D_E6M9 (its MAPINFO: each map its own song)
  Track23     SIGIL II intermission = its D_INTER
A song longer than --cap seconds fades out over its last --fade seconds there (the CD audio loops
in a level, so it starts over). The songs of maps not on the disc (--skip: too big for the 32X's
RAM) become 1 s of silence, so the numbering stays. Every song is brought to --level dBFS RMS
(default -21: the albums are mastered near 0 dBFS, far louder than the game's sounds, and the
console's mixer clips) with peaks under -1 dBFS. 44.1 kHz 16-bit stereo WAV; ffmpeg decodes.
"""
import argparse, os, re, struct, subprocess, sys, tempfile

SECTOR = 2352
RATE = 44100


LEVEL = -21.0                  # dBFS RMS of every song (the albums are mastered near 0 dBFS:
                               # far louder than the game's sounds, and the console's mixer clips)
PEAK = -1.0                    # dBFS: no sample above this


def ffmpeg_wav(src, dst, cap, fade, seek=None, length=None, fmt=None):
    """src -> 44.1 kHz 16-bit stereo WAV, at most cap seconds (faded out at the end when cut),
    at LEVEL dBFS RMS with peaks under PEAK dBFS (decoded in floating point, so the albums' own
    overs are not clipped)"""
    import numpy as np, wave
    cmd = ['ffmpeg', '-v', 'error', '-y']
    if fmt:
        cmd += ['-f', fmt, '-ar', str(RATE), '-ac', '2']
    cmd += ['-i', src, '-t', '%.3f' % cap, '-ar', str(RATE), '-ac', '2', '-f', 'f32le', '-']
    x = np.frombuffer(subprocess.run(cmd, check=True, capture_output=True).stdout, '<f4').reshape(-1, 2).astype(np.float64)
    n = len(x)
    if n >= int(cap * RATE) - RATE // 10:           # cut: fade out over the last fade seconds
        k = int(fade * RATE)
        x[n - k:] *= np.linspace(1.0, 0.0, k)[:, None]
    rms = float(np.sqrt(np.mean(x ** 2))) or 1e-9
    gain = 10 ** (LEVEL / 20) / rms
    peak = float(np.abs(x).max()) * gain
    if peak > 10 ** (PEAK / 20):
        gain *= 10 ** (PEAK / 20) / peak
    y = np.clip(np.round(x * gain * 32767), -32768, 32767).astype('<i2')
    w = wave.open(dst, 'wb')
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(RATE)
    w.writeframes(y.tobytes())
    w.close()
    return n / RATE


def silence(dst, seconds=1.0):
    import wave
    w = wave.open(dst, 'wb')
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(RATE)
    w.writeframes(bytes(int(RATE * seconds) * 4))
    w.close()
    return seconds


def cue_track(cue, num, dst, cap, fade):
    """one audio track of a .cue/.bin (raw CD audio) -> WAV"""
    base = os.path.dirname(os.path.abspath(cue))
    tracks, cur = [], None
    msf = lambda s: (lambda m, sec, f: (m * 60 + sec) * 75 + f)(*map(int, s.split(':')))
    for line in open(cue, encoding='latin1'):
        line = line.strip()
        m = re.match(r'FILE\s+"([^"]+)"', line, re.I)
        if m:
            cur = os.path.join(base, m.group(1))
        m = re.match(r'TRACK\s+(\d+)', line, re.I)
        if m:
            tracks.append([int(m.group(1)), cur, None, None])
        m = re.match(r'INDEX\s+(\d+)\s+(\S+)', line, re.I)
        if m and tracks:
            tracks[-1][2 if int(m.group(1)) == 0 else 3] = msf(m.group(2))
    i = next(k for k, t in enumerate(tracks) if t[0] == num)
    f, start = tracks[i][1], tracks[i][3]
    end = os.path.getsize(f) // SECTOR
    if i + 1 < len(tracks) and tracks[i + 1][1] == f:
        end = tracks[i + 1][2] if tracks[i + 1][2] is not None else tracks[i + 1][3]
    with open(f, 'rb') as src, tempfile.NamedTemporaryFile(suffix='.raw', delete=False) as tmp:
        src.seek(start * SECTOR)
        left = (end - start) * SECTOR
        while left:
            b = src.read(min(left, SECTOR * 4096))
            tmp.write(b)
            left -= len(b)
    try:
        return ffmpeg_wav(tmp.name, dst, cap, fade, fmt='s16le', length=(end - start) / 75.0)
    finally:
        os.unlink(tmp.name)


def wad_lumps(path):
    d = open(path, 'rb').read()
    n, o = struct.unpack('<II', d[4:12])
    out = {}
    for i in range(n):
        p, s, nm = struct.unpack('<II8s', d[o + i * 16:o + i * 16 + 16])
        out.setdefault(nm.split(b'\0')[0].decode('latin1').upper(), d[p:p + s])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--sigil', required=True)
    ap.add_argument('--sigil2', required=True)
    ap.add_argument('--idkfa', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--cap', type=float, default=300.0)
    ap.add_argument('--fade', type=float, default=6.0)
    ap.add_argument('--level', type=float, default=LEVEL, help='dBFS RMS of every song (default -21)')
    ap.add_argument('--skip', default='E5M6,E5M7,E6M5,E6M6,E6M7')
    ap.add_argument('--tracks', help='only these tracks, e.g. 2-5 (default all; the summary needs all)')
    a = ap.parse_args()
    globals()['LEVEL'] = a.level
    skip = set(x.strip().upper() for x in a.skip.split(',') if x.strip())
    os.makedirs(a.out, exist_ok=True)
    songs = sorted(f for f in os.listdir(a.sigil) if f.lower().endswith('.flac'))
    if len(songs) != 9:
        songs = sorted(f for f in os.listdir(a.sigil) if f.lower().endswith('.mp3'))
    songs.sort(key=lambda f: int(re.match(r'\s*(\d+)', f).group(1)))
    if len(songs) != 9:
        sys.exit('%s: needs Buckethead\'s 9 tracks (.flac or .mp3, numbered)' % a.sigil)
    W = wad_lumps(a.sigil2)
    total = 0.0
    plan = [('SIGIL title (IDKFA track 24)', ('cue', 24))]
    plan += [('E5M%d %s' % (k + 1, songs[k]), ('file', os.path.join(a.sigil, songs[k]), 'E5M%d' % (k + 1))) for k in range(9)]
    plan += [('SIGIL intermission (IDKFA track 22)', ('cue', 22))]
    plan += [('SIGIL II title D_INTRO', ('lump', 'D_INTRO', None))]
    plan += [('E6M%d D_E6M%d' % (k, k), ('lump', 'D_E6M%d' % k, 'E6M%d' % k)) for k in range(1, 10)]
    plan += [('SIGIL II intermission D_INTER', ('lump', 'D_INTER', None))]
    lo, hi = (map(int, a.tracks.split('-')) if '-' in a.tracks else (int(a.tracks),) * 2) if a.tracks else (2, 23)
    for n, (what, src) in enumerate(plan):
        if not lo <= n + 2 <= hi:
            continue
        dst = os.path.join(a.out, 'Track%02d.wav' % (n + 2))
        if src[0] != 'cue' and src[-1] in skip:
            sec = silence(dst)
            what += ' - not on the disc: 1 s of silence'
        elif src[0] == 'cue':
            sec = cue_track(a.idkfa, src[1], dst, a.cap, a.fade)
        elif src[0] == 'file':
            sec = ffmpeg_wav(src[1], dst, a.cap, a.fade)
        else:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                tmp.write(W[src[1]])
            try:
                sec = ffmpeg_wav(tmp.name, dst, a.cap, a.fade)
            finally:
                os.unlink(tmp.name)
        total += sec
        print('  Track%02d %5.1f s  %s' % (n + 2, sec, what), flush=True)
    print('SIGIL CD audio: 22 tracks, %.1f min -> %s' % (total / 60, a.out))


if __name__ == '__main__':
    main()
