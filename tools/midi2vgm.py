#!/usr/bin/env python3
"""midi2vgm.py - a MIDI song -> the Mega Drive VGM D32XR plays (.ZGM: YM2612 + SN76489 PSG, 1/60 s
steps, the whole song looping, compressed with the VGM player's LZSS) - the format of the Fusion
disc's own tracks (VGM 1.60: commands 0x52/0x53 YM2612, 0x50 PSG, 0x62 wait 1/60 s, 0x66 end).

  midi2vgm.py <song.mid> <GENMIDI lump or a WAD that has one> <out.zgm> [--raw out.vgm]

The instruments are DOOM's own: the GENMIDI lump (the OPL2 patches DOOM's DMX driver plays MIDI
with on FM sound cards). Each OPL voice (modulator -> carrier) becomes one YM2612 operator pair:
a double-voice patch fills both pairs of algorithm 4 (OP1->OP2, OP3->OP4), an additive one uses
algorithm 7. Envelopes, multipliers, feedback and levels map 1:1 where the chips agree (OPL attack /
decay rates x2 for the YM2612's 5-bit rates, sustain level and release as they are, OPL's
non-sustaining notes decay with D2R).

Voices: six FM channels for the melodic parts and the drums with a pitch (kicks, toms, and every
drum when no PSG fits), the PSG noise channel for snares, hi-hats and cymbals, and the three PSG
square channels for notes when all FM channels are busy (oldest note stolen otherwise).
Volume: velocity x channel volume x expression, a square law (as GM), on the carriers' level.
"""
import math
import struct
import sys

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))

YM_CLOCK = 7670453
PSG_CLOCK = 3579545
FPS = 60
SAMPLES_PER_FRAME = 735
MASTER_DB = 15.0          # attenuation on every carrier: about the loudness of the Fusion disc's tracks


# ------------------------------------------------------------------------------------------------
# MIDI

def read_midi(data):
    if data[:4] != b'MThd':
        raise ValueError('not a MIDI file')
    hl = struct.unpack('>I', data[4:8])[0]
    fmt, ntr, div = struct.unpack('>HHH', data[8:14])
    p = 8 + hl
    events = []                                   # (tick, order, type, ch, a, b)
    order = 0
    for _ in range(ntr):
        if data[p:p + 4] != b'MTrk':
            break
        ln = struct.unpack('>I', data[p + 4:p + 8])[0]
        q = p + 8
        end = q + ln
        tick = 0
        run = 0
        while q < end:
            v = 0
            while True:
                c = data[q]; q += 1
                v = (v << 7) | (c & 0x7f)
                if not c & 0x80:
                    break
            tick += v
            st = data[q]
            if st & 0x80:
                q += 1
            else:
                st = run
            if st == 0xff:
                t = data[q]; q += 1
                l = 0
                while True:
                    c = data[q]; q += 1
                    l = (l << 7) | (c & 0x7f)
                    if not c & 0x80:
                        break
                if t == 0x51:
                    events.append((tick, order, 'tempo', 0, int.from_bytes(data[q:q + 3], 'big'), 0))
                q += l
                continue
            if st in (0xf0, 0xf7):
                l = 0
                while True:
                    c = data[q]; q += 1
                    l = (l << 7) | (c & 0x7f)
                    if not c & 0x80:
                        break
                q += l
                continue
            run = st
            kind, ch = st & 0xf0, st & 0x0f
            if kind in (0xc0, 0xd0):
                a = data[q]; q += 1
                if kind == 0xc0:
                    events.append((tick, order, 'prog', ch, a, 0))
            else:
                a, b = data[q], data[q + 1]; q += 2
                if kind == 0x90 and b:
                    events.append((tick, order, 'on', ch, a, b))
                elif kind in (0x80, 0x90):
                    events.append((tick, order, 'off', ch, a, 0))
                elif kind == 0xb0:
                    events.append((tick, order, 'cc', ch, a, b))
                elif kind == 0xe0:
                    events.append((tick, order, 'bend', ch, (b << 7 | a) - 8192, 0))
            order += 1
        p = end
    events.sort(key=lambda e: (e[0], 0 if e[2] == 'off' else 1, e[1]))
    # ticks -> seconds
    out = []
    tempo = 500000
    last_tick = 0
    t = 0.0
    for e in events:
        t += (e[0] - last_tick) * tempo / 1e6 / div
        last_tick = e[0]
        if e[2] == 'tempo':
            tempo = e[4]
            continue
        out.append((t,) + e[2:])
    return out


# ------------------------------------------------------------------------------------------------
# GENMIDI (DOOM's OPL2 instruments)

def read_genmidi(data):
    if data[:8] != b'#OPL_II#':
        raise ValueError('not a GENMIDI lump')
    ins = []
    for i in range(175):
        b = data[8 + i * 36:8 + i * 36 + 36]
        flags, fine, fixed = struct.unpack('<HBB', b[:4])
        voices = []
        for v in range(2):
            o = 4 + v * 16
            m = b[o:o + 16]
            voices.append({'mod': m[0:6], 'fb': m[6], 'car': m[7:13], 'off': struct.unpack('<h', m[14:16])[0]})
        ins.append({'fixed': bool(flags & 1), 'double': bool(flags & 4), 'fine': fine, 'note': fixed, 'v': voices})
    return ins


def opl_op(b):
    """OPL operator bytes (0x20 char, 0x60 attack/decay, 0x80 sustain/release, 0xE0 wave, 0x40 ksl, level)"""
    char, ad, sr, wave, ksl, lvl = b
    return {'mult': char & 15, 'sus': bool(char & 0x20), 'ar': ad >> 4, 'dr': ad & 15, 'sl': sr >> 4,
            'rr': sr & 15, 'tl': lvl & 63, 'am': bool(char & 0x80)}


# ------------------------------------------------------------------------------------------------
# the VGM writer

class VGM:
    def __init__(self):
        self.cmds = bytearray()
        self.frames = 0
        self.ym = {}                  # (port, reg) -> value, to skip unchanged writes

    def w(self, port, reg, val, force=False):
        val &= 0xff
        if not force and self.ym.get((port, reg)) == val and reg not in (0x28,):
            return
        self.ym[(port, reg)] = val
        self.cmds += bytes((0x52 + port, reg, val))

    def psg(self, b):
        self.cmds += bytes((0x50, b & 0xff))

    def wait_frames(self, n):
        for _ in range(n):
            self.cmds.append(0x62)
        self.frames += n

    def finish(self):
        hdr = bytearray(0x80)
        hdr[0:4] = b'Vgm '
        data = bytes(self.cmds) + b'\x66'
        struct.pack_into('<I', hdr, 0x04, 0x80 + len(data) - 4)
        struct.pack_into('<I', hdr, 0x08, 0x160)
        struct.pack_into('<I', hdr, 0x0c, PSG_CLOCK)
        struct.pack_into('<I', hdr, 0x18, self.frames * SAMPLES_PER_FRAME)
        struct.pack_into('<I', hdr, 0x1c, 0x80 - 0x1c)                    # loop: the whole song
        struct.pack_into('<I', hdr, 0x20, self.frames * SAMPLES_PER_FRAME)
        struct.pack_into('<I', hdr, 0x24, FPS)
        struct.pack_into('<H', hdr, 0x28, 0x0009)                         # SN76489 feedback
        hdr[0x2a] = 16                                                     # shift register width
        struct.pack_into('<I', hdr, 0x2c, YM_CLOCK)
        struct.pack_into('<I', hdr, 0x34, 0x80 - 0x34)
        return bytes(hdr) + data


OPN_SLOT = [0, 8, 4, 12]             # register offsets of OP1, OP2, OP3, OP4

NOISE_NOTES = {37: (1, 4), 38: (1, 9), 39: (1, 8), 40: (1, 9), 42: (0, 3), 44: (0, 3), 46: (0, 10),
               49: (0, 24), 51: (0, 14), 52: (0, 24), 53: (0, 12), 54: (0, 5), 55: (0, 18), 56: (0, 4),
               57: (0, 24), 59: (0, 14), 69: (0, 3), 70: (0, 4), 75: (0, 3)}   # rate, decay frames


def fnum_block(freq):
    """YM2612: freq = F * clock / 144 / 2^20 * 2^(block-1)  ->  F in 1024..2047 when it can be"""
    fn = freq * 144 * (1 << 20) / YM_CLOCK          # F at block 1
    block = 1
    while fn >= 2048 and block < 7:
        fn /= 2
        block += 1
    while fn < 1024 and block > 0:
        fn *= 2
        block -= 1
    return max(1, min(2047, int(round(fn)))), block


class Converter:
    def __init__(self, genmidi):
        self.ins = read_genmidi(genmidi)
        self.v = VGM()
        # FM channels: owner (midi ch, note) or None, start frame, released frame
        self.fm = [{'own': None, 'start': -1, 'rel': -999, 'patch': None} for _ in range(6)]
        self.sq = [{'own': None, 'start': -1, 'vol': 15} for _ in range(3)]
        self.noise = {'left': 0, 'vol': 15, 'decay': 0}
        self.prog = [0] * 16
        self.vol = [100] * 16
        self.expr = [127] * 16
        self.pan = [64] * 16
        self.bend = [0] * 16
        self.frame = 0

    # ---- YM2612 ------------------------------------------------------------------------------
    def ym_init(self):
        v = self.v
        v.w(0, 0x22, 0, True)
        v.w(0, 0x27, 0, True)
        v.w(0, 0x2b, 0, True)
        for ch in range(6):
            v.w(0, 0x28, ch if ch < 3 else ch + 1, True)
        for port in (0, 1):
            for c in range(3):
                for s in OPN_SLOT:
                    v.w(port, 0x40 + s + c, 127, True)
                    v.w(port, 0x80 + s + c, 0xff, True)
                    v.w(port, 0x90 + s + c, 0, True)
                v.w(port, 0xb4 + c, 0xc0, True)
        for ch in range(4):
            v.psg(0x90 | (ch << 5) | 15)

    def set_patch(self, ch, gi, gain_db, pan):
        port, c = ch // 3, ch % 3
        ins = self.ins[gi]
        voices = ins['v'] if ins['double'] else ins['v'][:1]
        additive = any(vv['fb'] & 1 for vv in voices)
        alg = 7 if additive else 4
        fb = (voices[0]['fb'] >> 1) & 7
        v = self.v
        v.w(port, 0xb0 + c, (fb << 3) | alg)
        lr = 0xc0 if 40 <= pan <= 88 else 0x80 if pan < 40 else 0x40
        v.w(port, 0xb4 + c, lr)
        att = int(round((gain_db + MASTER_DB) / 0.75))
        for k in range(2):
            vv = voices[k] if k < len(voices) else None
            for role, slot in (('mod', OPN_SLOT[2 * k]), ('car', OPN_SLOT[2 * k + 1])):
                r = slot + c
                if vv is None:
                    v.w(port, 0x40 + r, 127)
                    continue
                o = opl_op(vv[role])
                dt = 1 if k == 1 else 0
                v.w(port, 0x30 + r, (dt << 4) | o['mult'])
                tl = o['tl']
                if role == 'car' or alg == 7:
                    tl += att
                v.w(port, 0x40 + r, min(127, tl))
                ar = min(31, o['ar'] * 2 + (1 if o['ar'] else 0))
                v.w(port, 0x50 + r, ar)
                v.w(port, 0x60 + r, min(31, o['dr'] * 2))
                v.w(port, 0x70 + r, 0 if o['sus'] else min(31, o['rr'] * 2))
                v.w(port, 0x80 + r, (o['sl'] << 4) | o['rr'])
                v.w(port, 0x90 + r, 0)

    def ym_key(self, ch, on):
        sel = ch if ch < 3 else ch + 1
        self.v.w(0, 0x28, (0xf0 if on else 0) | sel, True)

    def ym_freq(self, ch, freq):
        port, c = ch // 3, ch % 3
        fn, bl = fnum_block(freq)
        self.v.w(port, 0xa4 + c, (bl << 3) | (fn >> 8))
        self.v.w(port, 0xa0 + c, fn & 0xff)

    # ---- notes ----------------------------------------------------------------------------------
    def gain_db(self, ch, vel):
        g = (vel / 127.0) * (self.vol[ch] / 127.0) * (self.expr[ch] / 127.0)
        g = max(g, 1e-3) ** 2 if False else max(g, 1e-3)
        return -40 * math.log10(g)                 # square law: 40 log10

    def note_freq(self, note, bend=0.0):
        # +1 octave as DOOM's DMX OPL driver: GENMIDI's patches use carrier multiplier 0.5
        return 880.0 * 2 ** ((note - 69 + bend) / 12.0)

    def note_on(self, ch, note, vel):
        if ch == 9 and note in NOISE_NOTES:
            rate, dec = NOISE_NOTES[note]
            vol = max(0, min(15, int(round(self.gain_db(ch, vel) / 2.5))) )
            self.v.psg(0xe0 | 0x04 | rate)
            self.noise = {'left': dec, 'vol': vol, 'decay': dec}
            self.v.psg(0xf0 | vol)
            return
        if ch == 9:
            gi = 128 + note - 35
            if not 128 <= gi < 175:
                return
        else:
            gi = self.prog[ch]
        ins = self.ins[gi]
        n = ins['note'] if ins['fixed'] else note
        n += ins['v'][0]['off']
        # an FM channel: free, then released longest ago, then the oldest
        cands = sorted(range(6), key=lambda k: (self.fm[k]['own'] is not None, self.fm[k]['rel'] if self.fm[k]['own'] is None else self.fm[k]['start']))
        k = cands[0]
        if self.fm[k]['own'] is not None and ch != 9:
            # all six sound: a PSG square for this note if one is free
            for s in range(3):
                if self.sq[s]['own'] is None:
                    self.sq_on(s, ch, note, vel)
                    return
        if self.fm[k]['own'] is not None:
            self.ym_key(k, False)
        self.set_patch(k, gi, self.gain_db(ch, vel), self.pan[ch])
        self.ym_freq(k, self.note_freq(n, self.bend[ch] if ch != 9 else 0))
        self.ym_key(k, True)
        self.fm[k].update(own=(ch, note), start=self.frame, n=n)

    def note_off(self, ch, note):
        for k in range(6):
            if self.fm[k]['own'] == (ch, note):
                self.ym_key(k, False)
                self.fm[k].update(own=None, rel=self.frame)
        for s in range(3):
            if self.sq[s]['own'] == (ch, note):
                self.v.psg(0x90 | (s << 5) | 15)
                self.sq[s]['own'] = None

    def sq_on(self, s, ch, note, vel):
        f = self.note_freq(note, self.bend[ch])
        per = max(1, min(1023, int(round(PSG_CLOCK / (32 * f)))))
        self.v.psg(0x80 | (s << 5) | (per & 15))
        self.v.psg(per >> 4)
        vol = max(0, min(15, int(round(self.gain_db(ch, vel) / 2.0)) + 2))
        self.v.psg(0x90 | (s << 5) | vol)
        self.sq[s].update(own=(ch, note), start=self.frame)

    def frame_tick(self):
        nz = self.noise
        if nz['left'] > 0:
            nz['left'] -= 1
            vol = nz['vol'] + int(round((15 - nz['vol']) * (1 - nz['left'] / max(1, nz['decay']))))
            self.v.psg(0xf0 | min(15, vol))

    def bend_update(self, ch):
        for k in range(6):
            if self.fm[k]['own'] and self.fm[k]['own'][0] == ch and ch != 9:
                self.ym_freq(k, self.note_freq(self.fm[k]['n'], self.bend[ch]))

    # ---- the song ------------------------------------------------------------------------------
    def convert(self, events):
        self.ym_init()
        i = 0
        n = len(events)
        while i < n:
            t = events[i][0]
            f = int(t * FPS + 0.5)
            if f > self.frame:
                while self.frame < f:
                    self.v.wait_frames(1)
                    self.frame += 1
                    self.frame_tick()
            ev = events[i]
            _, kind, ch, a, b = ev
            if kind == 'on':
                self.note_on(ch, a, b)
            elif kind == 'off':
                self.note_off(ch, a)
            elif kind == 'prog':
                self.prog[ch] = a & 127
            elif kind == 'cc':
                if a == 7:
                    self.vol[ch] = b
                elif a == 11:
                    self.expr[ch] = b
                elif a == 10:
                    self.pan[ch] = b
                elif a in (120, 123):
                    for k in range(6):
                        if self.fm[k]['own'] and self.fm[k]['own'][0] == ch:
                            self.note_off(ch, self.fm[k]['own'][1])
            elif kind == 'bend':
                self.bend[ch] = a / 8192.0 * 2
                self.bend_update(ch)
            i += 1
        for k in range(6):
            self.ym_key(k, False)
        for s in range(4):
            self.v.psg(0x90 | (s << 5) | 15)
        self.v.wait_frames(FPS // 2)
        return self.v.finish()


def genmidi_from(path):
    d = open(path, 'rb').read()
    if d[:8] == b'#OPL_II#':
        return d
    n, o = struct.unpack('<II', d[4:12])
    for i in range(n):
        p, s = struct.unpack('<II', d[o + i * 16:o + i * 16 + 8])
        if d[o + i * 16 + 8:o + i * 16 + 16].rstrip(b'\0') == b'GENMIDI':
            return d[p:p + s]
    raise SystemExit('no GENMIDI in %s' % path)


def convert(midi_bytes, genmidi):
    from d32xr_wad import lzss_encode_big, lzss_decode_big
    vgm = Converter(genmidi).convert(read_midi(midi_bytes))
    z = lzss_encode_big(vgm)
    assert lzss_decode_big(z)[:len(vgm)] == vgm
    return vgm, z


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    vgm, z = convert(open(sys.argv[1], 'rb').read(), genmidi_from(sys.argv[2]))
    open(sys.argv[3], 'wb').write(z)
    if '--raw' in sys.argv:
        open(sys.argv[sys.argv.index('--raw') + 1], 'wb').write(vgm)
    print('%s: %d frames (%.0f s), VGM %d bytes -> %s %d bytes' % (sys.argv[1], len(vgm), 0, len(vgm), sys.argv[3], len(z)))


if __name__ == '__main__':
    main()
