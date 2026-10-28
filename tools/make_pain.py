#!/usr/bin/env python3
"""make_pain.py - the Pain Elemental's data for the PAIN=1 build (build.sh; README "Pain Elemental").

D32XR added the Pain Elemental (viciious/d32xr, 23-25 Oct 2026); DOOM CD32X Fusion's data has none of
it: no sprites in its IWAD, no sounds in SOUNDS.WAD, and its DOOM II maps have Cacodemons (and three
Imps on MAP25) where DOOM II has Pain Elementals. This makes them from your doom2.wad:

  make_pain.py iwad --iwad <IWAD> --doom2 data/doom2.wad --disc <the disc's WADs> --limit <bytes>
                    --out build/cart4_iwad.wad
      the 41 PAIN sprites (frames A-M), in the 32X sprite format (r_phase8.c R_DrawVisSprite: a header
      lump - width, height, offsets, an offset per column, 4-byte posts: top, length-1 with 0x80 on the
      column's last post, pixel offset - and the pixel lump after it), added before S_END. The pixels of
      all 41 are one pool: a run of pixels another frame already has is stored once (each sprite's
      pixel lump is the part of the pool its posts use, under 64 KB) - 118 KB instead of 149 KB.
      Then the IWAD is made to fit --limit (tools/make_cart4.py --any-size: walls to 16 colours, the
      least colour lost first). Fusion's IWAD already fills the game's 4 MB; when even every wall
      make_cart4.py can change does not make room, some of the Pain Elemental's frames are drawn at
      half width (each odd column repeats the even one), the least seen first: the death, the pain
      flinch, the attack, the floating (the 4 MB RAM cart: its save area takes 64 KB more).

  make_pain.py disc --doom2 data/doom2.wad --disc build/disc_files
      DOOM_II.WAD: the things standing where DOOM II has a Pain Elemental (same x, y, angle; Fusion's
      Cacodemon or Imp) become Pain Elementals again (type 71), their flags kept - 64 on 13 maps.
      SOUNDS.WAD: DSPESIT, DSPEPAIN, DSPEDTH added in the format of Fusion's smallest sounds (Creative
      Voice File, 2-bit ADPCM: src-md/cd/adpcm_voc2.s), encoded with a full search over the decoder's
      states. The Sega CD keeps every sound in one 453 KB buffer (src-md/cd/s_main.c s_membank,
      s_cd.c S_CD_LoadBuffers: all of SOUNDS.WAD in one read) which Fusion's sounds fill to 548 bytes.
      Room comes from two sounds that are never played - the first of the two VILATK (the game looks
      names up from the end, so the second one plays) and FLAMST (the game asks for "flamest") - and
      the three are made at the highest rate that then fits.
"""
import argparse, os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_rommaps as rm

MEMBANK = 453 * 1024          # src-md/cd/s_main.c S_MEMBANK_SIZE
WINDOW = 56000                # pixel runs shared within this distance (a sprite's pixels span < 64 KB)


def pwad(path):
    d = open(path, 'rb').read()
    n, o = struct.unpack('<II', d[4:12])
    out = []
    for i in range(n):
        p, s, nm = struct.unpack('<II8s', d[o + 16 * i:o + 16 * i + 16])
        out.append([nm.split(b'\0')[0].decode('latin1').upper(), p, s, nm])
    return d, out


def write_pwad(path, lumps):
    """lumps: (raw 8-byte name, data) in order; data from offset 12, directory last (as Fusion's)"""
    out = bytearray(b'PWAD' + bytes(8))
    dir_ = []
    for raw, data in lumps:
        dir_.append((len(out) if data else 0, len(data), raw))
        out += data
    o = len(out)
    for p, s, raw in dir_:
        out += struct.pack('<II8s', p, s, raw)
    struct.pack_into('<II', out, 4, len(lumps), o)
    open(path, 'wb').write(out)
    return out


# ---- sprites ---------------------------------------------------------------------------------------
def pc_columns(data):
    w, h, lo, to = struct.unpack('<hhhh', data[:8])
    cols = []
    for x in range(w):
        q = struct.unpack_from('<I', data, 8 + 4 * x)[0]
        posts = []
        while data[q] != 0xff:
            td, ln = data[q], data[q + 1]
            posts.append((td, data[q + 3:q + 3 + ln]))
            q += 4 + ln
        cols.append(posts)
    return w, h, lo, to, cols


def convert_sprites(lumps, half=''):
    pool = bytearray()
    res = []
    for nm, data in lumps:
        w, h, lo, to, cols = pc_columns(data)
        if nm[4] in half:               # half width: each odd column draws the even one before it
            cols = [cols[x & ~1] for x in range(w)]
        lump0 = len(pool)
        for window in (WINDOW, 0):          # a big sprite: shared runs from its own pixels only
            del pool[lump0:]
            colrecs = []
            for posts in cols:
                recs = []
                for td, px in posts:
                    for k in range(0, len(px), 128):
                        run = bytes(px[k:k + 128])
                        i = pool.find(run, max(0, lump0 - window))
                        if i < 0:
                            i = len(pool)
                            pool += run
                        recs.append((td + k, len(run), i))
                colrecs.append(recs)
            spans = [(i, i + n) for recs in colrecs for (_, n, i) in recs] or [(lump0, lump0)]
            base = min(a for a, b in spans)
            span = max(b for a, b in spans) - base
            if span < 65536:
                break
        else:
            sys.exit('make_pain: %s pixels span %d bytes' % (nm, span))
        hdr = bytearray(struct.pack('>hhhh', w, h, lo, to) + bytes(2 * w))
        posts = bytearray()
        seen = {}
        for x, recs in enumerate(colrecs):
            if not recs:
                key = b'\xff'
            else:
                key = b''.join(struct.pack('>BBH', t, (n - 1) | (0x80 if j == len(recs) - 1 else 0), i - base)
                               for j, (t, n, i) in enumerate(recs))
            if key not in seen:
                seen[key] = len(hdr) + len(posts)
                posts += key
            struct.pack_into('>H', hdr, 8 + 2 * x, seen[key])
        res.append((nm, bytes(hdr + posts), base, span))
    return res, bytes(pool)


def write_iwad(L, D, out_path, pool):
    """make_cart4.py's writer (header, directory, the old data in blocks, the new lumps), plus the
    pixel pool: lumps with 'pool' set point into it"""
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
    while len(out) % 16:
        out += b'\0'
    pool_at = len(out)
    out += pool
    for l in L:
        if not l['size']:
            l['newpos'] = 0
        elif l.get('pool') is not None:
            l['newpos'] = pool_at + l['pool']
        elif l['pos'] is not None:
            k = bisect.bisect_right(bstart, l['pos']) - 1
            l['newpos'] = l['pos'] - blocks[k][0] + newbase[k]
        else:
            while len(out) % 4:
                out += b'\0'
            l['newpos'] = len(out)
            out += l['data']
    for i, l in enumerate(L):
        struct.pack_into('>II8s', out, 12 + 16 * i, l['newpos'], l['size'], l['raw'])
    open(out_path, 'wb').write(out)
    return len(out)


# frames drawn at half width when the game's 4 MB has no room for all of them at full width, first to last:
# the death (seen for under a second), the pain flinch, the attack, the floating
HALF = ['', 'HIJKLM', 'GHIJKLM', 'DEFGHIJKLM', 'ABCDEFGHIJKLM']


def pain_iwad(iwad, src, half, out):
    D, L = rm.read_iwad(iwad)
    names = [l['name'] for l in L]
    if any(n.startswith('PAIN') for n in names):
        sys.exit('make_pain: %s already has PAIN sprites' % iwad)
    conv, pool = convert_sprites(src, half)
    new = []
    for nm, hdr, base, span in conv:
        new.append({'name': nm, 'raw': nm.encode().ljust(8, b'\0'), 'size': len(hdr), 'pos': None, 'data': hdr})
        new.append({'name': '.', 'raw': b'.'.ljust(8, b'\0'), 'size': span, 'pos': None, 'data': None, 'pool': base})
    se = names.index('S_END')
    L[se:se] = new
    size = write_iwad(L, D, out, pool)
    return size - len(D), sum(len(c[1]) for c in conv), len(pool)


def cmd_iwad(a):
    import contextlib, io
    import make_cart4
    dd, dl = pwad(a.doom2)
    src = [(nm, dd[p:p + s]) for nm, p, s, raw in dl if nm.startswith('PAIN') and s]
    if len(src) != 41:
        sys.exit('make_pain: %s has %d PAIN sprites, not 41 (DOOM II\'s)' % (a.doom2, len(src)))
    tmp = a.out + '.pain.wad'
    # the room: the IWAD with every texture make_cart4.py --any-size can make 4-bit, against the limit
    with contextlib.redirect_stdout(io.StringIO()):
        least = make_cart4.shrink(a.iwad, a.disc, 0, None, any_size=True)
    room = a.limit - least - 1024
    for half in HALF:
        more, hs, px = pain_iwad(a.iwad, src, half, tmp)
        if more <= room:
            break
    else:
        sys.exit('make_pain: the Pain Elemental needs %d bytes, the game\'s 4 MB has %d' % (more, room))
    print('PAIN sprites: 41 (headers %d bytes, pixels %d bytes, %d bytes in all; room for %d)%s'
          % (hs, px, more, room, '; at half width: frames %s' % ' '.join(half) if half else ''))
    size = make_cart4.shrink(tmp, a.disc, a.limit, a.out, any_size=True)
    os.remove(tmp)
    if size > a.limit:
        sys.exit('make_pain: still %d bytes over' % (size - a.limit))


# ---- sounds: Creative 2-bit ADPCM ------------------------------------------------------------------
# (delta, level change) per level 0-5 and code 0-3: src-md/cd/adpcm.c adpcm_voc2_steps_indices
STEPS = [[(0, 0), (1, 1), (0, 0), (-1, 1)],
         [(1, -1), (3, 1), (-1, -1), (-3, 1)],
         [(2, -1), (6, 1), (-2, -1), (-6, 1)],
         [(4, -1), (12, 1), (-4, -1), (-12, 1)],
         [(8, -1), (24, 1), (-8, -1), (-24, 1)],
         [(16, -1), (48, 0), (-16, -1), (-48, 0)]]


def voc2_decode(ref, codes):
    v, lev, out = ref, 0, []
    for c in codes:
        d, inc = STEPS[lev][c]
        v = min(255, max(0, v + d))
        lev += inc
        out.append(v)
    return out


def voc2_encode(target):
    """the codes whose decoding is nearest the target (least squares; a full search over the
    decoder's 6 x 256 states)"""
    T = len(target)
    ref = int(round(target[0]))
    INF = 1e30
    cost = np.full((6, 256), INF)
    cost[0, ref] = 0.0
    back = np.zeros((T, 6, 256), np.int16)
    vals = np.arange(256)
    for t in range(T):
        err = (vals - target[t]) ** 2
        new = np.full((6, 256), INF)
        nb = np.zeros((6, 256), np.int16)
        for L in range(6):
            cl = cost[L]
            if not np.isfinite(cl).any() or cl.min() >= INF:
                continue
            for c in range(4):
                d, inc = STEPS[L][c]
                L2 = L + inc
                cand = np.full(256, INF)
                src = np.zeros(256, np.int64)
                if d >= 0:
                    cand[d:] = cl[:256 - d]
                    src[d:] = vals[:256 - d]
                    if d > 0:
                        k = 255 - d + int(np.argmin(cl[255 - d:]))
                        cand[255], src[255] = cl[k], k
                else:
                    e = -d
                    cand[:256 - e] = cl[e:]
                    src[:256 - e] = vals[e:]
                    k = int(np.argmin(cl[:e + 1]))
                    cand[0], src[0] = cl[k], k
                cand = cand + err
                better = cand < new[L2]
                new[L2][better] = cand[better]
                nb[L2][better] = (L * 256 + src[better]) | (c << 11)
        cost = new
        back[t] = nb
    L, v = np.unravel_index(int(np.argmin(cost)), cost.shape)
    codes = []
    for t in range(T - 1, -1, -1):
        b = int(back[t][L][v])
        codes.append(b >> 11)
        p = b & 0x7ff
        L, v = p >> 8, p & 0xff
    codes.reverse()
    assert v == ref and L == 0
    return ref, codes


def voc_file(tc, ref, codes):
    codes = codes + [0] * (-len(codes) % 4)
    data = bytes((codes[i] << 6) | (codes[i + 1] << 4) | (codes[i + 2] << 2) | codes[i + 3]
                 for i in range(0, len(codes), 4))
    blk = bytes([tc, 3, ref]) + data
    hdr = b'Creative Voice File\x1a' + struct.pack('<HHH', 26, 0x010a, (~0x010a + 0x1234) & 0xffff)
    return hdr + bytes([1]) + struct.pack('<I', len(blk))[:3] + blk + b'\0'


def resample(x, rate_in, rate_out):
    """band-limited resampling by the spectrum (numpy only; no SciPy needed)"""
    x = np.asarray(x, float) - 128.0
    n = len(x)
    m = int(round(n * rate_out / rate_in))
    X = np.fft.rfft(x)
    Y = np.zeros(m // 2 + 1, complex)
    k = min(len(X), len(Y))
    Y[:k] = X[:k]
    y = np.fft.irfft(Y, m) * (m / n)
    return np.clip(y + 128.0, 0, 255)


def cmd_disc(a):
    disc = a.disc
    dd, dl = pwad(a.doom2)
    pcl = {nm: dd[p:p + s] for nm, p, s, raw in dl}
    # ---- DOOM_II.WAD: the Pain Elementals back
    path = os.path.join(disc, 'DOOM_II.WAD')
    fd = bytearray(open(path, 'rb').read())
    _, fl = pwad(path)
    pc_maps, cur = {}, None
    for nm, p, s, raw in dl:
        if nm.startswith('MAP') and len(nm) == 5:
            cur = nm
        if nm == 'THINGS' and cur:
            pc_maps[cur] = dd[p:p + s]
    total, cur = 0, None
    for nm, p, s, raw in fl:
        if nm.startswith('MAP') and len(nm) == 5:
            cur = nm
        if nm != 'THINGS' or cur not in pc_maps:
            continue
        if raw[0] & 0x80:
            sys.exit('make_pain: %s %s THINGS is compressed' % (path, cur))
        pc = pc_maps[cur]
        pe = {pc[k:k + 6] for k in range(0, len(pc) - 9, 10) if struct.unpack_from('<H', pc, k + 6)[0] == 71}
        if not pe:
            continue
        n = 0
        for k in range(p, p + s - 9, 10):
            if bytes(fd[k:k + 6]) in pe and struct.unpack_from('<H', fd, k + 6)[0] in (3005, 3001):
                struct.pack_into('<H', fd, k + 6, 71)
                n += 1
        if n != len(pe):
            sys.exit('make_pain: %s %s: %d Pain Elementals in DOOM II, %d places found' % (path, cur, len(pe), n))
        total += n
        print('  %s: %d Pain Elementals' % (cur, n))
    open(path, 'wb').write(fd)
    print('DOOM_II.WAD: %d Pain Elementals back' % total)

    # ---- SOUNDS.WAD
    path = os.path.join(disc, 'SOUNDS.WAD')
    sd, sl = pwad(path)
    names = [x[0] for x in sl]
    ds, de = names.index('DS_START'), names.index('DS_END')
    vil = [i for i in range(ds + 1, de) if names[i] == 'VILATK']
    drop = set(vil[:-1]) | {i for i in range(ds + 1, de) if names[i] == 'FLAMST'}
    keep = [(sl[i][3], sd[sl[i][1]:sl[i][1] + sl[i][2]]) for i in range(len(sl)) if i not in drop]
    kept = sum(len(dat) for raw, dat in keep)
    src = []
    for nm in ('DSPESIT', 'DSPEPAIN', 'DSPEDTH'):
        x = pcl[nm]
        fmt, rate, cnt = struct.unpack('<HHI', x[:8])
        src.append((nm[2:], rate, np.frombuffer(x[8:8 + cnt], np.uint8)))

    def need(extra):      # S_CD_LoadBuffers: the lumps from the first to the last, + 2 KB + 7
        return 12 + kept + extra + 0x7FF + 7
    tc = 0xA5             # Fusion's rate (10989 Hz), down until the three fit with 256 bytes to spare
    while True:
        rate = 1000000 // (256 - tc)
        est = sum(35 + (int(len(s) * rate / r) + 3) // 4 for _, r, s in src)
        if need(est) + 256 <= MEMBANK or tc < 0x60:
            break
        tc -= 1
    new = []
    for nm, r, s in src:
        y = resample(s, r, 1000000 / (256 - tc))
        ref, codes = voc2_encode(y)
        dec = np.array(voc2_decode(ref, codes), float)
        snr = 10 * np.log10(((y - 128) ** 2).sum() / max(1e-9, ((y - dec) ** 2).sum()))
        f = voc_file(tc, ref, codes)
        new.append((nm.encode().ljust(8, b'\0'), f))
        print('  %s: %d samples at %d Hz -> %d bytes (2-bit ADPCM, SNR %.1f dB)' % (nm, len(y), 1000000 // (256 - tc), len(f), snr))
    total = need(sum(len(f) for _, f in new))
    if total > MEMBANK:
        sys.exit('make_pain: the sounds need %d bytes of the Sega CD\'s %d' % (total, MEMBANK))
    end = [i for i, (raw, dat) in enumerate(keep) if raw.split(b'\0')[0] == b'DS_END'][0]
    keep[end:end] = new
    write_pwad(path, keep)
    print('SOUNDS.WAD: %s dropped (never played), PESIT PEPAIN PEDTH added; the Sega CD\'s sound buffer: '
          '%d of %d bytes' % (' '.join(names[i] for i in sorted(drop)), total, MEMBANK))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('iwad')
    p.add_argument('--iwad', required=True)
    p.add_argument('--doom2', required=True)
    p.add_argument('--disc', nargs='+', required=True, help='the WADs on the disc (make_cart4.py)')
    p.add_argument('--limit', type=int, required=True, help='the IWAD\'s largest size')
    p.add_argument('--out', required=True)
    p = sp.add_parser('disc')
    p.add_argument('--doom2', required=True)
    p.add_argument('--disc', required=True)
    a = ap.parse_args()
    if not os.path.isfile(a.doom2):
        sys.exit('make_pain: no %s (PAIN=1 takes the Pain Elemental from your doom2.wad)' % a.doom2)
    cmd_iwad(a) if a.cmd == 'iwad' else cmd_disc(a)


if __name__ == '__main__':
    main()
