#!/usr/bin/env python3
"""extract_iso.py <disc.bin or .iso> <folder>

Copies every file of a disc's ISO 9660 data track into <folder> (the DOOM CD32X Fusion disc:
its WADs, music and video go on the CD32X disc too). Takes a plain 2048-byte-sector image
(.iso, or a .bin with a MODE1/2048 cue) or a raw 2352-byte-sector one (MODE1/2352).
Entries whose size runs past the end of the image are skipped and listed (the Fusion V3 image
has two: VGM_DOOM/D_BUNNY.ZGM and VGM_DOOM_II/D_DOOM.ZGM).
"""
import os
import struct
import sys


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    raw = open(sys.argv[1], 'rb').read()
    if raw[16 * 2048 + 1:16 * 2048 + 6] == b'CD001':
        iso = raw
    elif raw[16 * 2352 + 16 + 1:16 * 2352 + 16 + 6] == b'CD001':
        iso = b''.join(raw[i * 2352 + 16:i * 2352 + 16 + 2048] for i in range(len(raw) // 2352))
    else:
        sys.exit('*** %s: no ISO 9660 volume found' % sys.argv[1])
    pvd = iso[16 * 2048:17 * 2048]
    root = pvd[156:190]
    count = [0, 0]

    def walk(lba, size, path):
        d = iso[lba * 2048:lba * 2048 + size]
        i = 0
        while i < len(d):
            n = d[i]
            if n == 0:
                i = (i // 2048 + 1) * 2048
                continue
            r = d[i:i + n]
            el, es = struct.unpack('<I', r[2:6])[0], struct.unpack('<I', r[10:14])[0]
            name = r[33:33 + r[32]]
            if name not in (b'\0', b'\1'):
                p = os.path.join(path, name.decode('ascii').split(';')[0])
                if r[25] & 2:
                    os.makedirs(p, exist_ok=True)
                    walk(el, es, p)
                elif el * 2048 + es > len(iso):
                    print('skipped (size past the end of the image): %s' % p)
                else:
                    open(p, 'wb').write(iso[el * 2048:el * 2048 + es])
                    count[0] += 1
                    count[1] += es
            i += n

    os.makedirs(sys.argv[2], exist_ok=True)
    walk(struct.unpack('<I', root[2:6])[0], struct.unpack('<I', root[10:14])[0], sys.argv[2])
    print('%d files, %d bytes -> %s' % (count[0], count[1], sys.argv[2]))


if __name__ == '__main__':
    main()
