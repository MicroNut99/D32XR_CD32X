#!/usr/bin/env python3
"""make_cart4.py - the DOOM disc's IWAD for the 4 MB RAM cart (build.sh CART4=1).

  make_cart4.py --iwad data/doom32xf.wad --disc <the disc's WADs> --out build/cart4_iwad.wad
                [--limit BYTES] [--keep N]

On the 4 MB board the cart's shared save area is its top 64 KB (0x3F0000-0x3FFFFF; DOOM saves in
piece 11). The DOOM disc's game image (program + Fusion's IWAD) fills the whole 4 MB, so the loader
refuses that board. This makes the IWAD small enough for the image to end below the save area:

  1. textures and flats no WAD on the disc uses point to one small one (tools/make_rommaps.py
     stub_unused - about 4 KB; every sprite is used by one of the five games);
  2. 8-bit wall textures become 4-bit (16 colours, the base game's own format: Fusion already has
     55 of its 148 textures so; the engine reads the depth from the header): first FIRST (the seven
     128 x 128 ones, 16 KB -> 9 KB each), then the 64 x 128 ones that lose the least colour, until the
     IWAD fits --limit. Textures other textures draw pieces of (decals) stay as they are; skies too.

Everything else keeps its bytes. --limit: the IWAD's largest size (default: the save area less a
219 KB program; the build's tools/fit_4mb.py checks the real end).
--any-size (PAIN=1, the Pain Elemental's sprites): after FIRST, textures of every size that get smaller,
decals with an even height and the 8-bit sky (SKY2) too, the least colour lost first (the default takes
only the 64 x 128 ones that are no decals).
"""
import argparse, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import make_rommaps as rm
import make_game as mg

SAVE_AREA = 0x3F0000
FIRST = ['WOOD5', 'TEKWALL4', 'PLAT1', 'MARBFACE', 'MARBFAC3', 'COMPTALL', 'BIGDOOR2']


def write_iwad(L, D, out_path):
    """header, directory, the IWAD's data in blocks of lumps that touch or overlap (same position
    within 16 bytes), then the new lumps (make_rommaps.py's writer, without maps)"""
    import bisect
    n = len(L)
    out = bytearray(b'IWAD' + struct.pack('>II', n, 12))
    out += bytes(16 * n)
    spans = sorted(set((l['pos'], l['end']) for l in L if l['size'] and l['pos'] is not None))
    blocks = []
    for p, e in spans:
        if blocks and p <= blocks[-1][1]:
            blocks[-1][1] = max(blocks[-1][1], e)
        else:
            blocks.append([p, e])
    bstart = [b[0] for b in blocks]
    newbase = []
    for p, e in blocks:
        while len(out) % 16 != p % 16:
            out += b'\0'
        newbase.append(len(out))
        out += D[p:e]
    pos_of = {}
    for l in L:
        if not l['size']:
            l['newpos'] = 0
        elif l['pos'] is not None:
            k = bisect.bisect_right(bstart, l['pos']) - 1
            l['newpos'] = l['pos'] - blocks[k][0] + newbase[k]
        else:
            if l['data'] not in pos_of:
                while len(out) % 16:
                    out += b'\0'
                pos_of[l['data']] = len(out)
                out += l['data']
            l['newpos'] = pos_of[l['data']]
    for i, l in enumerate(L):
        struct.pack_into('>II8s', out, 12 + 16 * i, l['newpos'], l['size'], l['raw'])
    if out_path:
        open(out_path, 'wb').write(out)
    return len(out)


def shrink(iwad, disc, limit, out, any_size=False):
    """the IWAD made small enough (see above); returns its size"""
    D, L = rm.read_iwad(iwad)
    B = mg.Base(iwad)
    names = [l['name'] for l in L]
    pal = mg.Palette(D[L[names.index('PLAYPALS')]['pos']:][:768])

    t, f = rm.disc_names(disc)
    freed = rm.stub_unused(L, D, t, f)
    print('  unused textures and flats: %d KB freed' % (freed // 1024))
    size = write_iwad(L, D, None)

    # textures other textures draw pieces of (decals): kept 8-bit (--any-size: 4-bit too when their height
    # is even - r_data.c R_CompositeColumn reads 4-bit decals, Fusion has some)
    tl = L[names.index('TEXTURE1')]
    td = D[tl['pos']:tl['end']]
    td = rm.lzss_decode(td) if tl['raw'][0] & 0x80 else td
    cnt = struct.unpack('<i', td[:4])[0]
    defs = []
    for off in struct.unpack('<%di' % cnt, td[4:4 + 4 * cnt]):
        pc = struct.unpack_from('<h', td, off + 20)[0]
        defs.append((td[off:off + 8].split(b'\0')[0].decode('latin1').upper(),
                     [struct.unpack_from('<h', td, off + 22 + 10 * k + 4)[0] for k in range(max(0, pc))]))
    patched = set()
    for tn, patches in defs:
        patched |= {defs[p][0] for p in patches if 0 <= p < cnt and defs[p][0] != tn}

    ts, te = names.index('T_START'), names.index('T_END')
    starts = {}
    for l in L:
        if l['size'] and l['pos'] is not None:
            starts.setdefault(l['pos'], []).append(l['name'])

    def sky(i):
        """--any-size: an 8-bit sky picture (SKY2: 256 x 128, a 16-byte header, columns) -> 4-bit with one
        row of colours, as Fusion's other skies and tools/make_game.py's (jag4 sky=True)"""
        l = L[i]
        if not any_size or not l['name'].startswith('SKY') or not l['size'] or l['pos'] is None or l['raw'][0] & 0x80:
            return None
        w, h, depth, _, flags = struct.unpack('>5H', D[l['pos']:l['pos'] + 10])
        if depth != 3 or flags != 1 or l['size'] != 16 + w * h or len(starts.get(l['pos'], [])) != 1:
            return None
        return w, h, D[l['pos'] + 16:l['pos'] + 16 + w * h]

    def candidate(i):
        l = L[i]
        nm = l['name']
        s = sky(i)
        if s:
            w, h, cm = s
        else:
            if not l['size'] or l['pos'] is None or l['raw'][0] & 0x80 or nm not in B.index or nm not in t:
                return None
            if B.depth.get(nm) != 3 or len(starts.get(l['pos'], [])) != 1:
                return None
            k = B.index[nm]
            w, h = B.tex[k]['w'], B.tex[k]['h']
            if nm in patched and not (any_size and h % 2 == 0):
                return None
            if l['size'] != w * h:
                return None
            if any_size and w * h // 2 + 16 + 33 * 32 >= w * h:      # the 4-bit one would be no smaller
                return None
            cm = D[l['pos']:l['pos'] + w * h]
        img = np.frombuffer(cm, np.uint8)
        idx, cols = mg.quantize16(img, pal)
        q = np.array(cols, np.uint8)[idx]
        err = float(np.sqrt(((pal.lab[img] - pal.lab[q]) ** 2).sum(-1)).mean())
        return (w, h, cm, err, bool(s))

    byname = {L[i]['name']: i for i in range(ts + 1, te)}
    order = [byname[n] for n in FIRST if n in byname]
    rest = []
    others = [i for i in range(len(L)) if any_size and L[i]['name'].startswith('SKY') and not ts < i < te]
    for i in list(range(ts + 1, te)) + others:
        if i in order:
            continue
        c = candidate(i)
        if c and (any_size or c[0] * c[1] == 64 * 128):
            rest.append((c[3], i))
    order += [i for _, i in sorted(rest)]

    done = []
    for i in order:
        if size <= limit:
            break
        c = candidate(i)
        if not c:
            continue
        w, h, cm, err, issky = c
        data = mg.jag4(w, h, cm, B.colormap, pal, sky=True) if issky else mg.jag4(w, h, cm, B.colormap, pal)
        l = L[i]
        l['pos'], l['data'], l['size'], l['end'] = None, data, len(data), None
        l['raw'] = bytes([l['raw'][0] & 0x7f]) + l['raw'][1:]
        size = write_iwad(L, D, None)
        done.append('%s %dx%d (colour error %.1f)' % (l['name'], w, h, err))
    size = write_iwad(L, D, out)
    print('  4-bit now: %s' % (', '.join(done) or 'none'))
    print('4 MB IWAD: %s, %d bytes (%d less than %s; limit %d, %d spare)'
          % (out, size, len(D) - size, os.path.basename(iwad), limit, limit - size))
    return size


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--iwad', required=True)
    ap.add_argument('--disc', nargs='+', required=True, help='the WADs on the disc (their maps)')
    ap.add_argument('--limit', type=int, default=SAVE_AREA - 219 * 1024)
    ap.add_argument('--any-size', action='store_true')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    size = shrink(a.iwad, a.disc, a.limit, a.out, a.any_size)
    if size > a.limit:
        sys.exit('make_cart4: still %d bytes over' % (size - a.limit))


if __name__ == '__main__':
    main()
