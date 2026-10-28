#!/usr/bin/env python3
"""fit_4mb.py - the SIGIL disc's game for the 4 MB RAM cart too.

  fit_4mb.py <ROMS/D32XR.32X> <the IWAD in it>

On the 4 MB board the cart's shared save area (pieces 0-15, 0x3F0000-0x3FFFFF; DOOM's saves in
piece 11) is in the same 4 MB as the game. The game image (program + IWAD) is padded to 4 MB by the
build; here it is cut back to the end of its IWAD, rounded up to the loader's 32 KB chunk, so the
loader copies (and checksums) only that. If it ends at 0x3F0000 or below, the loader also runs on
the 4 MB board (cdloader_sh2.c: PL_ROM_LENGTH) and the save area is never touched; otherwise the
image is left as it was (8 / 16 MB boards only).
"""
import sys

SAVE_AREA = 0x3F0000
CHUNK = 0x8000


def main():
    rom_path, iwad_path = sys.argv[1], sys.argv[2]
    rom = open(rom_path, 'rb').read()
    iwad = open(iwad_path, 'rb').read()
    at = rom.find(iwad[:4096], 0x20000)
    if at < 0 or rom[at:at + len(iwad)] != iwad:
        sys.exit('fit_4mb: the IWAD is not in %s' % rom_path)
    end = at + len(iwad)
    used = (end + CHUNK - 1) // CHUNK * CHUNK
    if used > SAVE_AREA:
        print('    4 MB cart: no (the game ends at 0x%06X, past the save area at 0x%06X by %d bytes)'
              % (end, SAVE_AREA, end - SAVE_AREA))
        return
    if any(rom[used:]):
        sys.exit('fit_4mb: data after the IWAD in %s' % rom_path)
    rom = rom[:used]
    open(rom_path, 'wb').write(rom)
    print('    4 MB cart: yes (the game ends at 0x%06X, %d bytes before the save area; the loader copies '
          'up to 0x%06X)' % (end, SAVE_AREA - end, (len(rom) + CHUNK - 1) // CHUNK * CHUNK))


if __name__ == '__main__':
    main()
