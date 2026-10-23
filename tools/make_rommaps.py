#!/usr/bin/env python3
"""make_rommaps.py - the game's IWAD with maps in it, for maps too big for the 32X's RAM from the CD.

  make_rommaps.py --iwad data/doom32xf.wad --maps ROMMAPS.WAD [ROMMAPS2.WAD ...] --out build/rom_iwad.wad
                  [--stub CPOS,SKEL,...] [--limit BYTES]

The CD32X engine (d32xr/p_setup.c, P_RomMap) uses a map it finds in the IWAD in place: the IWAD is
in the game's ROM image in the RAM cart, which the SH2s read directly, so the map's vertexes, segs,
nodes, reject and blockmap and its textures, flats and sky take no RAM. Only the rest (things,
linedefs, sidedefs, subsectors, sectors: the parts the game changes) is loaded into RAM.

The maps come from tools/make_game.py --rom-maps (already converted for Fusion: textures renamed,
the extra lumps after BLOCKMAP). Here their read-only lumps get the engine's own big-endian form:
  VERTEXES  mapvertex_t (x, y)
  SEGS      seg_t (linedef << 1 | side, v1, v2), each subsector's segs sorted by linedef (P_SortSegs)
  NODES     node_t (x, y, dx, dy, children[2], encbbox[2]): the boxes encoded as P_EncodeNodesBBoxes
  REJECT    packed as P_LoadRejectMatrix packs it (the upper triangle, one bit each)
  BLOCKMAP  int16
  SIDEDEFS  side_t (sector, top, bottom, mid, rowoffset, textureoffset 8.4), copied into RAM
The maps come first in the directory (before PLAYPALS), each followed by its extra lumps, then
ROMEND. THINGS, LINEDEFS, SSECTORS and SECTORS stay as they are (the engine converts them into
RAM as for a map on the CD).

Room: the ROM is 4 MB (the cart's window 0 and window 1). --stub frees the sprites of monsters and
things a map set never uses (default: DOOM II's): their lumps stay, by name, but point to one small
sprite. Lumps with the same bytes are stored once.
"""
import argparse, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from d32xr_wad import lzss_decode

DOOM2_ONLY = ('CPOS SKEL FATT FATB FBXP MANF BSPI APLS APBX VILE FIRE BOS2 SSWV PAIN KEEN BBRN BOSF '
              'HDB1 HDB2 HDB3 HDB4 HDB5 HDB6 POB1 POB2 BRS1 TLMP TLP2 MEGA SGN2').split()
ROM_LIMIT = 0x400000 - 0x2E7A4 - 4096       # the 4 MB less the program (D32XR.32x, IWAD at 0x2E7A4), a little spare
MAPLUMPS = ['THINGS', 'LINEDEFS', 'SIDEDEFS', 'VERTEXES', 'SEGS', 'SSECTORS', 'NODES', 'SECTORS', 'REJECT', 'BLOCKMAP']
BOXTOP, BOXBOTTOM, BOXLEFT, BOXRIGHT = range(4)


def read_iwad(path):
    """the Fusion IWAD (big-endian): the file's bytes and its entries in directory order, each with
    the byte range it reads (an uncompressed lump its size - lumps overlap there, a sprite's header
    and its pixels, a texture and the next -, a compressed one up to the next lump's position)"""
    d = open(path, 'rb').read()
    n, o = struct.unpack('>II', d[4:12])
    ents = []
    for i in range(n):
        p, s = struct.unpack('>II', d[o + i * 16:o + i * 16 + 8])
        ents.append([p, s, d[o + i * 16 + 8:o + i * 16 + 16]])
    starts = sorted(set(p for p, s, r in ents if s and p < len(d)) | {o, o + 16 * n, len(d)})
    import bisect
    out = []
    for p, s, raw in ents:
        name = (bytes([raw[0] & 0x7f]) + raw[1:]).split(b'\0')[0].decode('latin1').upper()
        l = {'name': name, 'raw': raw, 'size': s, 'pos': p, 'data': None}
        if s and p + 1 > len(d):
            l['pos'], l['data'] = None, bytes(s)          # PNAMES: past the end of the extracted IWAD (unused)
        elif s:
            j = bisect.bisect_right(starts, p)
            l['end'] = p + (starts[j] - p if raw[0] & 0x80 else s)
        out.append(l)
    return d, out


def read_pwad(path):
    d = open(path, 'rb').read()
    n, o = struct.unpack('<II', d[4:12])
    out = []
    for i in range(n):
        p, s, nm = struct.unpack('<II8s', d[o + i * 16:o + i * 16 + 16])
        out.append((nm.split(b'\0')[0].decode('latin1').upper(), d[p:p + s]))
    return out


def texture_numbers(L, D):
    """the IWAD's texture names -> the engine's texture numbers (R_CheckTextureNumForName: TEXTURE1's
    order, the first match)"""
    t = next(l for l in L if l['name'] == 'TEXTURE1')
    data = D[t['pos']:t['end']]
    if t['raw'][0] & 0x80:
        data = lzss_decode(data)
    cnt = struct.unpack('<i', data[:4])[0]
    num = {}
    for i, off in enumerate(struct.unpack('<%di' % cnt, data[4:4 + 4 * cnt])):
        num.setdefault(data[off:off + 8].split(b'\0')[0].decode('latin1').upper(), i)
    return num


def rom_sides(sd, texnum):
    """SIDEDEFS -> side_t (P_LoadSideDefs: sector, top, bottom, mid, rowoffset, textureoffset 8.4)"""
    out = bytearray()
    nm = lambda b: b.split(b'\0')[0].decode('latin1').upper()
    for k in range(0, len(sd) - 29, 30):
        to, ro = struct.unpack_from('<hh', sd, k)
        t = []
        for o in (4, 12, 20):
            n = nm(sd[k + o:k + o + 8])
            t.append(0 if not n or n[0] == '-' else texnum.get(n, 0) & 0xff)
        sec = struct.unpack_from('<h', sd, k + 28)[0]
        off = ((to & 0xfff) | ((ro & 0x0f00) << 4)) & 0xffff
        out += struct.pack('>hBBBBH', sec, t[0], t[1], t[2], ro & 0xff, off)
    return bytes(out)


def rom_map(M, texnum):
    """the read-only lumps of one map in the engine's form (see the top)"""
    sh = lambda b, f: [struct.unpack_from(f, b, k) for k in range(0, len(b) - struct.calcsize(f) + 1, struct.calcsize(f))]
    verts = sh(M['VERTEXES'], '<hh')
    out = {'VERTEXES': b''.join(struct.pack('>hh', x, y) for x, y in verts), 'SIDEDEFS': rom_sides(M['SIDEDEFS'], texnum)}
    # world box (P_LoadVertexes)
    wb = [-32768, 32767, 32767, -32768]                 # top, bottom, left, right
    for x, y in verts:
        wb[BOXLEFT] = min(wb[BOXLEFT], x); wb[BOXRIGHT] = max(wb[BOXRIGHT], x)
        wb[BOXBOTTOM] = min(wb[BOXBOTTOM], y); wb[BOXTOP] = max(wb[BOXTOP], y)
    # segs: packed, sorted in each subsector (stable, as P_isortsegs)
    segs = []
    for v1, v2, ang, ld, side, off in sh(M['SEGS'], '<HHhHHh'):
        if ld >= 0x4000:
            sys.exit('a linedef number over 16383 does not fit the packed seg')
        segs.append(((ld << 1) | (1 if side else 0), v1, v2))
    for cnt, first in sh(M['SSECTORS'], '<HH'):
        segs[first:first + cnt] = sorted(segs[first:first + cnt], key=lambda t: t[0])
    out['SEGS'] = b''.join(struct.pack('>HHH', *t) for t in segs)
    # nodes with encoded boxes (P_EncodeNodesBBoxes)
    nodes = sh(M['NODES'], '<hhhh8hHH')
    bb = []
    for n in nodes:
        bb += list(n[4:12])
    enc = [[0, 0] for _ in nodes]

    def side_enc(b, ob, pc, nc):
        length = ob[pc] - ob[nc] + 15
        if length < 16:
            return 0
        unit = length // 16
        nu = 0
        length = b[nc] - ob[nc]
        if length > 0:
            nu = min(15, length // unit)
            b[nc] = ob[nc] + nu * unit
        pu = 0
        length = ob[pc] - b[pc]
        if length > 0:
            pu = min(15, length // unit)
            b[pc] = ob[pc] - pu * unit
        return (pu << 4) | nu

    def rec(nn, outer):
        if nn & 0x8000:
            return
        for j in range(2):
            b = bb[nn * 8 + j * 4:nn * 8 + j * 4 + 4]
            e = side_enc(b, outer, BOXRIGHT, BOXLEFT) << 8
            e |= side_enc(b, outer, BOXTOP, BOXBOTTOM)
            bb[nn * 8 + j * 4:nn * 8 + j * 4 + 4] = b
            enc[nn][j] = e
            rec(nodes[nn][12 + j], b)
    if nodes:
        sys.setrecursionlimit(100000)
        rec(len(nodes) - 1, wb)
    out['NODES'] = b''.join(struct.pack('>hhhhHHHH', *(n[0:4] + n[12:14] + tuple(enc[i])))
                            for i, n in enumerate(nodes))
    # reject, packed (P_LoadRejectMatrix)
    ns = len(M['SECTORS']) // 26
    rej = M['REJECT']
    size = ((ns + 1) * ns // 2 + 7) // 8
    packed = bytearray(size)
    ob = 0
    for i in range(ns):
        for j in range(i, ns):
            k = i * ns + j
            if k // 8 < len(rej) and rej[k // 8] & (1 << (k & 7)):
                packed[ob >> 3] |= 1 << (ob & 7)
            ob += 1
    out['REJECT'] = bytes(packed)
    bm = M['BLOCKMAP']
    out['BLOCKMAP'] = struct.pack('>%dh' % (len(bm) // 2), *struct.unpack('<%dh' % (len(bm) // 2), bm[:len(bm) // 2 * 2]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--iwad', required=True)
    ap.add_argument('--maps', nargs='+', required=True)
    ap.add_argument('--stub', default=','.join(DOOM2_ONLY), help='sprite names (4 letters) to point to one small sprite')
    ap.add_argument('--limit', type=int, default=ROM_LIMIT)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    D, L = read_iwad(a.iwad)
    # stub sprites: header lump + '.' data lump pairs point to the smallest sprite left
    stub = set(x.strip().upper() for x in a.stub.split(',') if x.strip())
    ins, owner, pairs = False, None, []
    for i, l in enumerate(L):
        if l['name'] == 'S_START':
            ins = True
        elif l['name'] == 'S_END':
            ins = False
        elif ins and l['name'] != '.' and i + 1 < len(L) and L[i + 1]['name'] == '.':
            pairs.append((i, i + 1))
    keep = [(h, d) for h, d in pairs if L[h]['name'][:4] not in stub]
    dh, dd = min(keep, key=lambda hd: L[hd[0]]['size'] + L[hd[1]]['size'])
    for h, d in pairs:
        if L[h]['name'][:4] in stub:
            for x, y in ((h, dh), (d, dd)):
                for k in ('pos', 'size', 'end', 'data'):
                    L[x][k] = L[y].get(k)
                L[x]['raw'] = bytes([(L[x]['raw'][0] & 0x7f) | (L[y]['raw'][0] & 0x80)]) + L[x]['raw'][1:]
    stubbed = len(set(L[h]['name'][:4] for h, d in pairs if L[h]['name'][:4] in stub))

    # the maps
    texnum = texture_numbers(L, D)
    have = set(l['name'] for l in L)
    added = []
    for path in a.maps:
        P = read_pwad(path)
        i = 0
        while i < len(P):
            name, data = P[i]
            if i + 10 < len(P) and [n for n, _ in P[i + 1:i + 11]] == MAPLUMPS:
                if name in have:
                    sys.exit('%s is in the IWAD already' % name)
                M = {n: d for n, d in P[i + 1:i + 11]}
                R = rom_map(M, texnum)
                first = len(added)
                added.append((name, b''))
                for n in MAPLUMPS:
                    added.append((n, R.get(n, M[n])))
                i += 11
                while i < len(P) and not (i + 10 < len(P) and [n for n, _ in P[i + 1:i + 11]] == MAPLUMPS):
                    added.append(P[i])
                    i += 1
                mb = sum(len(d) for _, d in added[first:first + 11])
                xb = sum(len(d) for _, d in added[first + 11:])
                print('  %s: map %d KB + textures, flats, sky %d KB' % (name, mb // 1024, xb // 1024))
                continue
            i += 1
    nmaps = sum(1 for n, d in added if n.startswith('E') and len(n) == 4 and not d)
    added.append(('ROMEND', b''))                 # ends the last map's extra lumps
    # the maps go FIRST in the directory: the engine looks names up from the end backwards
    # (W_CheckWadForName), so the IWAD's own F_START, T_START / T_END, SKY3 ... stay the ones it finds,
    # not a map's (its extra lumps use the same names); a map reads its lumps forwards up to ROMEND
    L = [{'name': n, 'raw': n.encode('latin1')[:8].ljust(8, b'\0'), 'size': len(d), 'data': d, 'pos': None}
         for n, d in added] + L

    # write: header, directory, then the IWAD's data in blocks of lumps that touch or overlap (kept
    # as they are, at the same position within 16 bytes), then the new lumps (16-byte aligned, the
    # same bytes stored once)
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
    import bisect
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
    freed = len(D) - sum(e - p for p, e in blocks) - 16 * (n - len(read_iwad(a.iwad)[1]))
    open(a.out, 'wb').write(out)
    print('ROM IWAD: %s, %d bytes (%d free in the 4 MB ROM): %d maps added (%d KB), %d sprites stubbed (%d KB freed)'
          % (a.out, len(out), a.limit - len(out), nmaps, sum(len(d) for _, d in added) // 1024, stubbed, freed // 1024))
    if len(out) > a.limit:
        sys.exit('*** too big for the ROM by %d bytes' % (len(out) - a.limit))


if __name__ == '__main__':
    main()
