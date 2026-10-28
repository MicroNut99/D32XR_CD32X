#!/usr/bin/env python3
"""make_preload.py - the RAM cart's preload: which of the Fusion disc's files are kept in the
16 MB cart, and where.

  make_preload.py plan <fusion folder> <plan.json> <68000 header> <Sub-CPU header>
  make_preload.py loader <plan.json> <D32XR.32X> <loader header>

The 16 MB board (16MB-PCB-CD32X) shows the SH2s and the 68000 two 2 MB windows of its eight
2 MB pages. DOOM CD32X Fusion's 4 MB ROM sits in page 0 (window 0) and page 7 (window 1, set
at the hand-over). Page 1 keeps the shared save area and the other titles' data, so it is left
alone. Pages 2-6 hold the preload: the WADs the game reads through the 68000 (W_ReadLump etc.
via scd_fs.c), copied once from the disc, then read from the cart instead of the CD.

Layout (one "linear" space over pages 2-6):
  - each page holds 63 chunks of 32 KB (0x000000-0x1F7FFF); its last 32 KB are left free:
    the board probe writes save piece 15 at 0x1FF000, and other titles keep page records in
    the last 64 KB;
  - a file starts on a 32 KB boundary, so the loader copies it chunk by chunk (Sub-CPU CMD 46)
    and a page change always falls between two chunks;
  - linear L -> page 2 + L / 0x1F8000, offset L % 0x1F8000;
  - files are taken in PRELOAD_ORDER, each one if it still fits.

plan writes:
  - plan.json: the files, their place and checksum (for the loader step);
  - the 68000's table (d32xr/src-md/cd32x_preload.h's format): name, length, linear start;
  - the Sub-CPU's table: CMD 38 file 300 + n opens preload file n.
loader writes the SH2 loader's table: the ROM's length and checksum (pages 0 + 7), and each
file's CMD 38 number, length, linear start, chunks and checksum.

Checksum (the loader computes the same over the cart): over the big-endian 32-bit words,
s = rotate-left-1(s) + word, then the last 0-3 bytes added one by one.
"""
import json
import os
import struct
import sys

PRELOAD_ORDER = ['SOUNDS.WAD', 'DOOM.WAD', 'DOOM_II.WAD', 'RESURRECTION.WAD', 'TNT_MINI.WAD', 'MAPDEV.WAD',
                 'SIGIL.WAD', 'SIGIL_II.WAD']   # the SIGIL disc: SOUNDS + the two SIGILs
CHUNK = 0x8000
PAGE_USE = 63 * CHUNK            # 0x1F8000
FIRST_PAGE, LAST_PAGE = 2, 6
SPACE = (LAST_PAGE - FIRST_PAGE + 1) * PAGE_USE
FILE_BASE = 300                  # CMD 38 file number of preload file 0


def checksum(data):
    s = 0
    n = len(data) & ~3
    for (w,) in struct.iter_unpack('>I', data[:n]):
        s = (((s << 1) | (s >> 31)) + w) & 0xFFFFFFFF
    for b in data[n:]:
        s = (s + b) & 0xFFFFFFFF
    return s


def plan(folder, out_json, out_68k, out_sub):
    files = []
    linear = 0
    skipped = []
    # NOPRELOAD=1 (build.sh): no files - the loader copies the ROM only and the game reads the CD
    order = [] if os.environ.get('NOPRELOAD', '0') == '1' else PRELOAD_ORDER
    if not order:
        print('preload: NOPRELOAD=1 - nothing in the cart, the game reads every WAD from the CD')
    for name in order:
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            continue
        data = open(path, 'rb').read()
        start = (linear + CHUNK - 1) & ~(CHUNK - 1)
        if start + len(data) > SPACE:
            skipped.append('%s (%d bytes)' % (name, len(data)))
            continue
        files.append({'name': name, 'length': len(data), 'linear': start, 'sum': checksum(data)})
        linear = start + len(data)
    json.dump({'files': files}, open(out_json, 'w'), indent=1)

    with open(out_68k, 'w') as f:
        f.write('/* made by tools/make_preload.py - the WADs kept in the 16 MB RAM cart (pages %d-%d) */\n'
                % (FIRST_PAGE, LAST_PAGE))
        f.write('#define CD32X_PRELOAD_COUNT %d\n' % len(files))
        f.write('static const cd32x_preload_t cd32x_preload[CD32X_PRELOAD_COUNT + 1] = {\n')
        for e in files:
            f.write('    { "%s", %d, 0x%06X },\n' % (e['name'], e['length'], e['linear']))
        f.write('    { "", 0, 0 }\n};\n')

    with open(out_sub, 'w') as f:
        f.write('/* made by tools/make_preload.py - CMD 38 file %d + n = preload file n */\n' % FILE_BASE)
        f.write('#define PRELOAD_FILE_BASE %d\n#define PRELOAD_COUNT %d\n' % (FILE_BASE, len(files)))
        f.write('static const char *const preload_names[PRELOAD_COUNT + 1] = {\n')
        for e in files:
            f.write('    "%s",\n' % e['name'])
        f.write('    ""\n};\n')

    used = sum(e['length'] for e in files)
    print('preload: %d files, %d of %d bytes in pages %d-%d (%.1f %%)'
          % (len(files), used, SPACE, FIRST_PAGE, LAST_PAGE, 100.0 * used / SPACE))
    for e in files:
        p, o = FIRST_PAGE + e['linear'] // PAGE_USE, e['linear'] % PAGE_USE
        print('    %-18s %8d bytes  page %d +0x%06X' % (e['name'], e['length'], p, o))
    for s in skipped:
        print('    not in the cart (no room): %s' % s)


def loader(in_json, rom_path, out_h):
    files = json.load(open(in_json))['files']
    rom = open(rom_path, 'rb').read()
    with open(out_h, 'w') as f:
        f.write('/* made by tools/make_preload.py - what the loader checks and copies into the 16 MB cart */\n')
        f.write('#define PL_ROM_LENGTH 0x%06X\n#define PL_ROM_SUM 0x%08X\n' % (len(rom), checksum(rom)))
        f.write('#define PL_CHUNK 0x%X\n#define PL_PAGE_USE 0x%06X\n#define PL_FIRST_PAGE %d\n'
                % (CHUNK, PAGE_USE, FIRST_PAGE))
        # LOADER_CHECK (build.sh): each 32 KB chunk's checksum, so the loader can find a chunk that came
        # out wrong and copy it again (only compiled with CDL_LOADER_CHECK)
        nch = (len(rom) + CHUNK - 1) // CHUNK
        f.write('#if defined(CDL_LOADER_CHECK) && CDL_LOADER_CHECK\n#define PL_ROM_CHUNKS %d\n' % nch)
        f.write('static const uint32_t pl_rom_chunk[PL_ROM_CHUNKS] = {\n')
        for i in range(0, nch, 8):
            f.write('    ' + ', '.join('0x%08X' % checksum(rom[k * CHUNK:(k + 1) * CHUNK])
                                      for k in range(i, min(i + 8, nch))) + ',\n')
        f.write('};\n#endif\n')
        f.write('#define PL_COUNT %d\n' % len(files))
        f.write('static const struct { uint16_t file; uint32_t length, linear, sum; } pl_files[PL_COUNT + 1] = {\n')
        for i, e in enumerate(files):
            f.write('    { %d, 0x%06X, 0x%06X, 0x%08X },   /* %s */\n'
                    % (FILE_BASE + i, e['length'], e['linear'], e['sum'], e['name']))
        f.write('    { 0, 0, 0, 0 }\n};\n')
    print('loader table: ROM %d bytes, sum %08X; %d preload files -> %s' % (len(rom), checksum(rom), len(files), out_h))


def main():
    if len(sys.argv) == 6 and sys.argv[1] == 'plan':
        plan(*sys.argv[2:])
    elif len(sys.argv) == 5 and sys.argv[1] == 'loader':
        loader(*sys.argv[2:])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
