#!/usr/bin/env python3
"""extract_cue_audio.py - the CD audio tracks of a .cue/.bin disc image -> Track02.wav, Track03.wav ...

  extract_cue_audio.py <disc.cue> <output folder>

For the CD audio of DOOM CD32X Fusion V3 with IDKFA Soundtrack (build.sh): each AUDIO track of the
cue becomes TrackNN.wav (NN = its track number), 44.1 kHz 16-bit stereo, byte for byte the disc's
audio (CD audio is little-endian 16-bit stereo already). A track runs from its INDEX 01 to the next
track's INDEX 00 (or INDEX 01), the last one to the end of its file. Python only.
"""
import os, re, struct, sys

SECTOR = 2352


def msf(s):
    m, sec, f = (int(x) for x in s.split(':'))
    return (m * 60 + sec) * 75 + f


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    cue, out = sys.argv[1], sys.argv[2]
    base = os.path.dirname(os.path.abspath(cue))
    tracks = []                  # (number, type, file, index00, index01)
    cur_file = None
    for line in open(cue, encoding='latin1'):
        line = line.strip()
        m = re.match(r'FILE\s+"([^"]+)"', line, re.I) or re.match(r'FILE\s+(\S+)', line, re.I)
        if m:
            cur_file = os.path.join(base, m.group(1))
            continue
        m = re.match(r'TRACK\s+(\d+)\s+(\S+)', line, re.I)
        if m:
            tracks.append([int(m.group(1)), m.group(2).upper(), cur_file, None, None])
            continue
        m = re.match(r'INDEX\s+(\d+)\s+(\d+:\d+:\d+)', line, re.I)
        if m and tracks:
            tracks[-1][3 if int(m.group(1)) == 0 else 4] = msf(m.group(2))
    os.makedirs(out, exist_ok=True)
    n = 0
    total = 0
    for i, (num, typ, f, i0, i1) in enumerate(tracks):
        if typ != 'AUDIO':
            continue
        if not os.path.exists(f):
            sys.exit('%s: missing %s' % (cue, f))
        size = os.path.getsize(f) // SECTOR
        end = size
        if i + 1 < len(tracks) and tracks[i + 1][2] == f:
            nx = tracks[i + 1]
            end = nx[3] if nx[3] is not None else nx[4]
        start = i1
        length = (end - start) * SECTOR
        dst = os.path.join(out, 'Track%02d.wav' % num)
        with open(f, 'rb') as src, open(dst, 'wb') as w:
            w.write(b'RIFF' + struct.pack('<I', 36 + length) + b'WAVEfmt ' +
                    struct.pack('<IHHIIHH', 16, 1, 2, 44100, 44100 * 4, 4, 16) + b'data' + struct.pack('<I', length))
            src.seek(start * SECTOR)
            left = length
            while left:
                b = src.read(min(left, SECTOR * 4096))
                if not b:
                    sys.exit('%s: ends early' % f)
                w.write(b)
                left -= len(b)
        n += 1
        total += end - start
    print('%d audio tracks, %.2f min -> %s' % (n, total / 4500, out))


if __name__ == '__main__':
    main()
