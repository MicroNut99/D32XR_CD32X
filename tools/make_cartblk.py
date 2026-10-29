#!/usr/bin/env python3
"""make_cartblk.py - PLUTEX (build.sh PLUTEX=1): the game's IWAD with the textures and flats a game on
the disc never uses itself moved together into one block at its end, which that game's maps fill with
their own pictures at load time (the cart's memory is RAM: the RAM cart, the EverDrive's PSRAM).

  make_cartblk.py --iwad IN.wad --keep KEEP.txt --out OUT.wad [--limit BYTES]

KEEP.txt (tools/make_game.py --cart-keep-out): the base game's texture and flat lumps that game needs
as they are (one name per line). Every other lump of the main T_START..T_END and F_START..F_END goes
into the block, unless it shares bytes with a lump that stays (then it stays too).

The directory keeps its entries in their order (the engine's lump numbers do not change); only their
positions change. Every lump keeps its position modulo 16 (the alignment the engine reads it with).
Two lumps are added at the end of the directory:
  CARTBLK  8 bytes, big-endian: the block's offset in the IWAD, its length
  CARTREC  16 bytes of zeros: the record the engine sets while the block holds another game's
           pictures ('PLTX'), so any other game puts the block back (from PLUTONIA.WAD's CARTPOOL)
           first - also after a reset, as the cart keeps its memory
The block's original bytes are written to OUT.wad.pool (make_game.py puts them in PLUTONIA.WAD).
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_rommaps as rm                 # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--iwad', required=True)
    ap.add_argument('--keep', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--limit', type=int, default=0, help='the largest the IWAD may be (bytes)')
    a = ap.parse_args()

    D, L = rm.read_iwad(a.iwad)
    keep = set(x.strip().upper() for x in open(a.keep) if x.strip() and not x.startswith('#'))
    if any(l['name'] in ('CARTBLK', 'CARTREC') for l in L):
        sys.exit('*** make_cartblk: %s has a block already' % a.iwad)

    # the main texture and flat sections (not a ROM map's extras: those follow a BLOCKMAP)
    cand = set()
    sec, prev = None, None
    for i, l in enumerate(L):
        n = l['name']
        if n in ('T_START', 'F_START'):
            sec = n[0] if prev != 'BLOCKMAP' else None
        elif n in ('T_END', 'F_END'):
            sec = None
        elif sec and l['size'] and l['pos'] is not None and n not in keep:
            cand.add(i)
        prev = n
    # a lump may move only when every lump that shares a byte with it moves too
    spans = [(l['pos'], l['end'], i) for i, l in enumerate(L) if l['size'] and l['pos'] is not None]
    spans.sort()
    changed = True
    while changed:
        changed = False
        for i in sorted(cand):
            p, e = L[i]['pos'], L[i]['end']
            for q, f, j in spans:
                if q >= e:
                    break
                if f > p and j not in cand:
                    cand.discard(i)
                    changed = True
                    break
    # the bytes that move: the union of the moving lumps' ranges, in groups that touch or overlap
    mv = sorted(set((L[i]['pos'], L[i]['end']) for i in cand))
    groups = []
    for p, e in mv:
        if groups and p <= groups[-1][1]:
            groups[-1][1] = max(groups[-1][1], e)
        else:
            groups.append([p, e])

    # the rest of the data (after the old directory), in blocks of lumps that touch or overlap
    n_old = len(L)
    stay = sorted(set((l['pos'], l['end']) for i, l in enumerate(L)
                      if l['size'] and l['pos'] is not None and i not in cand))
    blocks = []
    for p, e in stay:
        if blocks and p <= blocks[-1][1]:
            blocks[-1][1] = max(blocks[-1][1], e)
        else:
            blocks.append([p, e])
    n = n_old + 2
    out = bytearray(b'IWAD' + struct.pack('>II', n, 12))
    out += bytes(16 * n)
    where = {}                                   # old block start -> new start
    for p, e in blocks:
        while len(out) % 16 != p % 16:
            out += b'\0'
        where[p] = len(out)
        out += D[p:e]
    while len(out) % 16:
        out += b'\0'
    blk_at = len(out)
    for p, e in groups:
        while len(out) % 16 != p % 16:
            out += b'\0'
        where[p] = len(out)
        out += D[p:e]
    while len(out) % 16:
        out += b'\0'
    blk_len = len(out) - blk_at
    pool = bytes(out[blk_at:blk_at + blk_len])
    import bisect
    allb = sorted(blocks + groups)
    starts = [b[0] for b in allb]
    for i, l in enumerate(L):
        if not l['size']:
            np_ = 0
        elif l['pos'] is None:
            while len(out) % 4:
                out += b'\0'
            np_ = len(out)
            out += l['data']
        else:
            k = bisect.bisect_right(starts, l['pos']) - 1
            np_ = l['pos'] - allb[k][0] + where[allb[k][0]]
        struct.pack_into('>II8s', out, 12 + 16 * i, np_, l['size'], l['raw'])
    blk = struct.pack('>II', blk_at, blk_len)
    rec_at = len(out)
    out += blk
    out += bytes(16)
    struct.pack_into('>II8s', out, 12 + 16 * n_old, rec_at, 8, b'CARTBLK\0')
    struct.pack_into('>II8s', out, 12 + 16 * (n_old + 1), rec_at + 8, 16, b'CARTREC\0')
    if a.limit and len(out) > a.limit:
        sys.exit('*** make_cartblk: %d bytes, more than the limit %d' % (len(out), a.limit))
    open(a.out, 'wb').write(out)
    open(a.out + '.pool', 'wb').write(pool)
    names = sorted(L[i]['name'] for i in cand)
    print('cart block: %d lumps (%d textures and flats the game never uses itself), %d bytes at 0x%x of the IWAD; '
          'IWAD %d -> %d bytes' % (len(cand), len(names), blk_len, blk_at, len(D), len(out)))


if __name__ == '__main__':
    main()
