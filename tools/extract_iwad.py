#!/usr/bin/env python3
"""extract_iwad.py <rom.32x> <out.wad>

Takes the IWAD out of a Doom 32X Resurrection cartridge ROM (the game data the build appends
to the program, see d32xr/Makefile: program padded to BINSIZE KB, then the WAD). The WAD is
found by its header ("IWAD" + lump count + directory offset, big-endian in D32XR's format) and
runs to the end of the ROM's used part (the build pads the ROM with zeros, dd conv=sync, so
trailing zeros cut here come back the same in the new ROM).

The WAD is the game's data (id Software's and the D32XR team's): it is never committed, the
user supplies the ROM.
"""
import struct
import sys


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    rom = open(sys.argv[1], 'rb').read()
    if rom[0x100:0x108] != b'SEGA 32X':
        sys.exit('*** %s is not a 32X ROM' % sys.argv[1])
    pos = -1
    i = rom.find(b'IWAD')
    while i >= 0:
        n, ofs = struct.unpack('>II', rom[i + 4:i + 12])
        # D32XR's WAD: the lump directory sits right after the header (offset 12) and every
        # entry is 16 bytes; the program before it is padded to a whole KB
        if i % 1024 == 0 and 0 < n < 10000 and ofs == 12:
            pos = i
            break
        i = rom.find(b'IWAD', i + 1)
    if pos < 0:
        sys.exit('*** no D32XR IWAD found in %s' % sys.argv[1])
    end = len(rom)
    while end > pos and rom[end - 1] == 0x00:
        end -= 1
    title = rom[0x120:0x150].decode('ascii', 'replace').strip()
    open(sys.argv[2], 'wb').write(rom[pos:end])
    print('%s: "%s", IWAD at 0x%X, %d lumps, %d bytes -> %s'
          % (sys.argv[1], title, pos, n, end - pos, sys.argv[2]))


if __name__ == '__main__':
    main()
