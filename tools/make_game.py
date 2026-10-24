#!/usr/bin/env python3
"""make_game.py - a PC game -> a D32XR game WAD for DOOM CD32X Fusion's select menu:
  --game plutonia : The Plutonia Experiment (your plutonia.wad)            -> PLUTONIA.WAD
  --game sigil    : SIGIL (DOOM.WAD + your sigil.wad, episode 5)            -> SIGIL.WAD
  --game sigil2   : SIGIL II (DOOM.WAD + your sigil2.wad, episode 6)        -> SIGIL_II.WAD

  make_game.py --game G --pc <WAD> [<PWAD> ...] --base doom32xf.wad --fusion <Fusion disc folder>
               [--hires <1K texture pack .pk3>] [--budgets FILE] [--title PIC] [--interpic PIC]
               [--maxlevel KB] --out OUT.WAD [--report FILE]

The Fusion disc's games are D32XR "PWADs" (little-endian): music lumps (M_START..M_END), DMAPINFO,
the maps as PC lumps, and after each map's BLOCKMAP up to MAX_AUX_TEXTURES lumps that the engine
loads into the 32X's RAM for that map only (p_setup.c): a sky (the map's sky name), textures
(T_START..T_END) and flats (F_START..F_END). An extra texture or flat can only REPLACE THE PICTURE
of a name the base game (the IWAD in the ROM) already has, with the base name's size. A name the
base game does not know is drawn as the stand-in texture (ASHWALL2). This tool:

 1. keeps every texture and flat the base game has (same name, same size);
 2. for each other one a map uses, takes a "donor" base name that map does not use (same size,
    its own picture, not part of an animation or a switch, unless the donor group is one of the
    same shape), puts Plutonia's picture under the donor's name and renames the map's sidedefs /
    sectors to it - the Fusion team's own method (Doom II's MAP01 carries a different picture
    under MARBLE3). Animations and switches go to donor animations / switch pairs of the same
    frame count and size, so they still animate and switch;
 3. stays within a RAM budget per map (estimated from the map's own size, calibrated on Fusion's
    own maps): flats first (4 KB), then the missing textures in 4-bit (16 colours, half the
    memory, the base game's own format), then 8-bit (all colours) for the most-used ones, then
    8-bit for base textures whose base picture is a 4-bit reduction, then the sky in 8-bit;
 4. for what still does not fit, picks the closest-looking base texture / flat of the same size;
 5. uses the 1K texture pack's pictures (--hires) for the names it has, shrunk to the textures'
    own size (area average in linear light, light sharpening, nearest palette colour in CIELAB);
 6. Pain Elementals (not in the engine) become Cacodemons (same health, also fly); things of
    type 0 are dropped (the engine stops on unknown types);
 7. music: the Fusion disc's VGM_PLUTONIA folder (the Plutonia MIDI Pack arranged for the Mega
    Drive by the Fusion team), DMAPINFO with Plutonia's names, skies, texts and secret levels.
"""
import argparse
import os
import re
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from d32xr_wad import read_wad, lzss_decode, PCWad, pc_patch, section          # noqa: E402
from d32xr_hires import Palette, Pack, area_resize_linear, to_palette, srgb_to_lin, lin_to_lab  # noqa: E402

# the level's own RAM in the 32X zone (bytes), fitted on the 30 Plutonia maps measured in ares
# (free-zone dumps after loading each map without extras; error 1.7 KB rms, 3.5 KB at most): over
# [1, lines, sides, vertexes, segs, subsectors, nodes, sectors, sectors^2/16, BLOCKMAP, things]
LEVEL_MODEL = (5117.50, 13.88, 9.75, 4.19, 0.00, 21.97, 0.00, 50.11, 0.00, 1.75, 50.58)
# the largest level that loaded and played (Plutonia MAP23: 157 KB); MAP28 (216 KB) and MAP29
# (184 KB) stop with "Z_Malloc failed" before the first frame
MAX_AUX = 64                     # MAX_AUX_TEXTURES in the CD32X build (p_setup.c)
SIGIL_TITLE_TICS = 300           # SIGIL / SIGIL II: the title's time before the game starts by itself
MAPLUMPS = ['THINGS', 'LINEDEFS', 'SIDEDEFS', 'VERTEXES', 'SEGS', 'SSECTORS', 'NODES', 'SECTORS', 'REJECT', 'BLOCKMAP']

# the engine's switch list (p_switch.c) and animations (p_spec.c)
ENGINE_SWITCHES = [('SW1BRN1', 'SW2BRN1'), ('SW1GARG', 'SW2GARG'), ('SW1GSTON', 'SW2GSTON'), ('SW1HOT', 'SW2HOT'),
                   ('SW1STAR', 'SW2STAR'), ('SW1WOOD', 'SW2WOOD'), ('SW1BLUE', 'SW2BLUE'), ('SW1BRCOM', 'SW2BRCOM'),
                   ('SW1BRMET', 'SW2BRMET'), ('SW1BRN2', 'SW2BRN2'), ('SW1BRNGN', 'SW2BRNGN'), ('SW1CMT', 'SW2CMT'),
                   ('SW1COMM', 'SW2COMM'), ('SW1COMP', 'SW2COMP'), ('SW1GORSK', 'SW2GORSK'), ('SW1GRAY', 'SW2GRAY'),
                   ('SW1GRAY1', 'SW2GRAY1'), ('SW1MET2', 'SW2MET2'), ('SW1METAL', 'SW2METAL'), ('SW1PIPE', 'SW2PIPE'),
                   ('SW1SLAD', 'SW2SLAD'), ('SW1STON1', 'SW2STON1'), ('SW1STONM', 'SW2STONM'), ('SW1WDMET', 'SW2WDMET'),
                   ('SW1DBLU', 'SW2DBLU'), ('SW1BRIK', 'SW2BRIK'), ('SW1BROWN', 'SW2BROWN'), ('SW1DRED', 'SW2DRED'),
                   ('SW1DYEL', 'SW2DYEL'), ('SW1MOD1', 'SW2MOD1'), ('SW1PANEL', 'SW2PANEL'), ('SW1ROCK', 'SW2ROCK'),
                   ('SW1STON6', 'SW2STON6'), ('SW1TEK', 'SW2TEK'), ('SW1WUD', 'SW2WUD'), ('SW1ZIM', 'SW2ZIM'),
                   ('SW1S0', 'SW1S1')]
ANIM_TEX = [('BLODGR1', 'BLODGR4'), ('SLADRIP1', 'SLADRIP3'), ('BLODRIP1', 'BLODRIP4'), ('FIREWALA', 'FIREWALL'),
            ('GSTFONT1', 'GSTFONT3'), ('FIRELAV3', 'FIRELAVA'), ('FIREMAG1', 'FIREMAG3'), ('FIREBLU1', 'FIREBLU2'),
            ('ROCKRED1', 'ROCKRED3'), ('BFALL1', 'BFALL4'), ('SFALL1', 'SFALL4'), ('WFALL1', 'WFALL4'), ('DBRAIN1', 'DBRAIN4')]
ANIM_FLAT = [('NUKAGE1', 'NUKAGE3'), ('FWATER1', 'FWATER4'), ('LAVA1', 'LAVA4'), ('BLOOD1', 'BLOOD3'),
             ('RROCK05', 'RROCK08'), ('SLIME01', 'SLIME04'), ('SLIME05', 'SLIME08'), ('SLIME09', 'SLIME12')]

# The Plutonia Experiment: level names, skies, secret exits, story texts (Final Doom)
NAMES = ['Congo', 'Well of Souls', 'Aztec', 'Caged', 'Ghost Town', "Baron's Lair", 'Caughtyard', 'Realm',
         'Abattoire', 'Onslaught', 'Hunted', 'Speed', 'The Crypt', 'Genesis', 'The Twilight', 'The Omen',
         'Compound', 'Neurosphere', 'NME', 'The Death Domain', 'Slayer', 'Impossible Mission', 'Tombstone',
         'The Final Frontier', 'The Temple of Darkness', 'Bunker', 'Anti-Christ', 'The Sewers',
         'Odyssey of Noises', 'The Gateway of Hell', 'Cyberden', 'Go 2 It']
P1TEXT = ("YOU GLOAT OVER THE STEAMING CARCASS OF THE*GUARDIAN. WITH ITS DEATH, YOU'VE WRESTED*THE "
          "ACCELERATOR FROM THE STINKING CLAWS*OF HELL. YOU RELAX AND GLANCE AROUND THE*ROOM. DAMN! THERE "
          "WAS SUPPOSED TO BE AT*LEAST ONE WORKING PROTOTYPE, BUT YOU CAN'T*SEE IT. THE DEMONS MUST HAVE "
          "TAKEN IT.**YOU MUST FIND THE PROTOTYPE, OR ALL YOUR*STRUGGLES WILL HAVE BEEN WASTED. KEEP*MOVING, "
          "KEEP FIGHTING, KEEP KILLING.*OH YES, KEEP LIVING, TOO.")
P2TEXT = ("EVEN THE DEADLY ARCH-VILE LABYRINTH COULD*NOT STOP YOU, AND YOU'VE GOTTEN TO THE*PROTOTYPE "
          "ACCELERATOR WHICH IS SOON*EFFICIENTLY AND PERMANENTLY DEACTIVATED.**YOU'RE GOOD AT THAT KIND OF THING.")
P3TEXT = ("YOU'VE BASHED AND BATTERED YOUR WAY INTO*THE HEART OF THE DEVIL-HIVE. TIME FOR A*SEARCH-AND-"
          "DESTROY MISSION, AIMED AT THE*GATEKEEPER, WHOSE FOUL OFFSPRING IS*CASCADING TO EARTH. YEAH, HE'S "
          "BAD. BUT*YOU KNOW WHO'S WORSE!**GRINNING EVILLY, YOU CHECK YOUR GEAR, AND*GET READY TO GIVE THE "
          "BASTARD A LITTLE HELL*OF YOUR OWN MAKING!")
P4TEXT = ("THE GATEKEEPER'S EVIL FACE IS SPLATTERED*ALL OVER THE PLACE. AS ITS TATTERED CORPSE*COLLAPSES, AN "
          "INVERTED GATE FORMS AND*SUCKS DOWN THE SHARDS OF THE LAST*PROTOTYPE ACCELERATOR, NOT TO MENTION "
          "THE*FEW REMAINING DEMONS. YOU'RE DONE. HELL*HAS GONE BACK TO POUNDING BAD DEAD FOLKS*INSTEAD OF "
          "GOOD LIVE ONES. REMEMBER TO*TELL YOUR GRANDKIDS TO PUT A ROCKET*LAUNCHER IN YOUR COFFIN. IF YOU GO "
          "TO HELL*WHEN YOU DIE, YOU'LL NEED IT FOR SOME*FINAL CLEANING-UP ...")
P5TEXT = ("YOU'VE FOUND THE SECOND-HARDEST LEVEL WE*GOT. HOPE YOU HAVE A SAVED GAME A LEVEL OR*TWO "
          "PREVIOUS. IF NOT, BE PREPARED TO DIE*APLENTY. FOR MASTER MARINES ONLY.")
P6TEXT = ("BETCHA WONDERED JUST WHAT WAS THE HARDEST*LEVEL WE HAD READY FOR YA? NOW YOU KNOW.*NO ONE GETS OUT ALIVE.")


def die(msg):
    sys.exit('*** make_plutonia: ' + msg)


# ------------------------------------------------------------------------------------------------
# the base game (the IWAD in the ROM, big-endian)


START_NEAR = 768        # map units around player 1's start whose walls count START_BOOST times
START_BOOST = 64
SIGNATURE_TEX = {'SIGILTX2', 'SIGILTEX', 'SW1LION', 'SW2LION'}   # kept first: the packs' own art (SIGIL II's
                       # demon face) and DOOM's lion-head switch (SIGIL II E6M8's start column)
SIGNATURE_BOOST = 64
SIGNATURE_STANDIN = {'SIGILTX2': ('MARBFACE', 'MARBFAC3', 'MARBFAC2'),   # no room: DOOM's demon faces,
                     'SW1LION': ('SW1ROCK',), 'SW2LION': ('SW2ROCK',)}   # its skull switch on dark stone

class Base:
    def __init__(self, path):
        _, self.L = read_wad(path, '>')
        L = self.L
        get = lambda l: lzss_decode(l['data'])[:l['size']] if l['comp'] else l['data']
        self.get = get
        t1 = [l for l in L if l['name'] == 'TEXTURE1'][0]
        d = get(t1)
        n = struct.unpack('<I', d[:4])[0]
        self.tex = []
        for o in struct.unpack('<%dI' % n, d[4:4 + 4 * n]):
            name = d[o:o + 8].split(b'\0')[0].decode('latin1').upper()
            masked, w, h = struct.unpack('<IHH', d[o + 8:o + 16])
            pc = struct.unpack('<H', d[o + 20:o + 22])[0]
            pt = [struct.unpack('<H', d[o + 22 + k * 10 + 4:o + 22 + k * 10 + 6])[0] for k in range(pc)]
            self.tex.append({'name': name, 'w': w, 'h': h, 'masked': masked & 0xff, 'patches': pt})
        self.index = {t['name']: i for i, t in enumerate(self.tex)}
        # the main texture block: the T_START..T_END not right after a BLOCKMAP (those are maps' extras)
        self.tlumps = {}
        prev = None
        on = False
        main = False
        for l in L:
            if l['name'] == 'T_START':
                on = True
                main = prev != 'BLOCKMAP'
            elif l['name'] == 'T_END':
                on = False
            elif on and main and l['size']:
                self.tlumps.setdefault(l['name'], l)
            prev = l['name']
        self.sprites = set(l['name'] for l in section(L, 'S_START', 'S_END'))
        self.flats = []
        prev = None
        on = main = False
        for l in L:
            if l['name'] == 'F_START':
                on = True
                main = prev != 'BLOCKMAP'
            elif l['name'] == 'F_END':
                on = False
            elif on and main and l['size']:
                self.flats.append(l['name'])
            prev = l['name']
        self.flatset = set(self.flats)
        cms = [get(l) for l in L if l['name'] == 'COLORMAP']
        self.colormap = cms[-1]                      # the hi-res colormaps (R_InitColormaps)
        # lump identity of each texture (R_InitTextures): own lump / sprite / first patch / 0
        ids = []
        for t in self.tex:
            if t['masked']:
                ids.append(('S', t['name']) if t['name'] in self.sprites else None)
            else:
                ids.append(('T', t['name']) if t['name'] in self.tlumps else None)
        for i, t in enumerate(self.tex):
            if ids[i] is None and t['patches']:
                p = t['patches'][0]
                if 0 <= p < len(self.tex) and ids[p] is not None:
                    ids[i] = ids[p]
        ids = [x if x is not None else ('0',) for x in ids]
        self.ids = ids
        from collections import Counter
        c = Counter(ids)
        # 4-bit pictures in the base game (depth 2: 16 colours per texture)
        self.depth = {}
        for name, l in self.tlumps.items():
            dd = get(l)
            if len(dd) >= 16:
                w, h, dep = struct.unpack('>HHH', dd[:6])
                i = self.index.get(name)
                if i is not None and (w, h) == (self.tex[i]['w'], self.tex[i]['h']) and dep in (2, 3):
                    self.depth[name] = dep
                    continue
            self.depth[name] = 3
        sw = set(a for p in ENGINE_SWITCHES for a in p)
        anim = set()
        self.anim_groups = []                         # base texture animations: [names] in number order
        for a, b in ANIM_TEX:
            if a in self.index and b in self.index:
                ia, ib = self.index[a], self.index[b]
                grp = [self.tex[k]['name'] for k in range(min(ia, ib), max(ia, ib) + 1)]
                self.anim_groups.append(grp)
                anim.update(grp)
        self.switch_pairs = [(a, b) for a, b in ENGINE_SWITCHES if a in self.index and b in self.index and a != b]
        self.donors = []
        for i, t in enumerate(self.tex):
            n = t['name']
            if i < 2 or t['masked'] or ids[i][0] != 'T' or c[ids[i]] != 1 or t['patches'] and ids[i][1] != n:
                continue
            if n in sw or n in anim or n.startswith('SKY'):
                continue
            self.donors.append(n)
        fanim = set()
        self.flat_anim_groups = []
        for a, b in ANIM_FLAT:
            if a in self.flatset and b in self.flatset:
                ia, ib = self.flats.index(a), self.flats.index(b)
                grp = self.flats[min(ia, ib):max(ia, ib) + 1]
                self.flat_anim_groups.append(grp)
                fanim.update(grp)
        self.flat_donors = [f for f in self.flats if f not in fanim and f not in ('F_SKY1', 'F_STCOL2', 'FLAT5_7')]

    def picture(self, name):
        """the base picture (w, h, column-major palette indices) for the look comparisons"""
        i = self.index[name]
        w, h = self.tex[i]['w'], self.tex[i]['h']
        l = self.tlumps.get(self.ids[i][1]) if self.ids[i][0] == 'T' else None
        if l is None:
            return None
        d = self.get(l)
        if len(d) >= 16 and struct.unpack('>HH', d[:4]) == (w, h) and struct.unpack('>H', d[4:6])[0] in (2, 3):
            dep = struct.unpack('>H', d[4:6])[0]
            body = d[16:]
            if dep == 3:
                return w, h, body[:w * h]
            tab = body[w * h // 2:]
            pal = [tab[2 * k] for k in range(16)]
            out = bytearray(w * h)
            for x in range(w):
                for y in range(h):
                    b = body[x * (h // 2) + y // 2]
                    out[x * h + y] = pal[(b >> 4) if y % 2 == 0 else (b & 15)]
            return w, h, bytes(out)
        if len(d) >= w * h:
            return w, h, d[:w * h]
        return None


# ------------------------------------------------------------------------------------------------
# pictures in the engine's formats

def colmajor(w, h, rowpx):
    a = np.frombuffer(rowpx, np.uint8).reshape(h, w)
    return a.T.tobytes()


def jag8(w, h, cm):
    """8-bit texture: header (depth 3, flags 1 = column major) + w*h bytes column major"""
    return struct.pack('>8H', w, h, 3, 0, 1, 0, 0, 0) + cm


def jag4(w, h, cm, colormap, palette, sky=False):
    """4-bit texture (the base game's format): header (depth 2, flags 9 = column major + colormap
    appended), two pixels a byte (even line in the upper nibble), then 33 light levels x 16 colours
    x 2 bytes (sky: one row) = COLORMAP[level][index ^ 0x80]"""
    a = np.frombuffer(cm, np.uint8)
    idx, cols = quantize16(a, palette)
    body = bytearray()
    q = idx.reshape(w, h)
    for x in range(w):
        col = q[x]
        for y in range(0, h, 2):
            lo = col[y + 1] if y + 1 < h else 0
            body.append((int(col[y]) << 4) | int(lo))
    tab = bytearray()
    levels = 1 if sky else 33
    for lv in range(levels):
        for k in range(16):
            v = cols[k] if sky else colormap[lv * 256 + (cols[k] ^ 0x80)]
            tab += bytes((v, v))
    return struct.pack('>8H', w, h, 2, 0, 9, 0, 0, 0) + bytes(body) + bytes(tab)


def quantize16(indices, palette):
    """palette indices -> (0..15 per pixel, the 16 palette entries): k-means in CIELAB, centres
    snapped to palette colours"""
    u, inv, cnt = np.unique(indices, return_inverse=True, return_counts=True)
    if len(u) <= 16:
        cols = list(u) + [u[0]] * (16 - len(u))
        return inv.astype(np.uint8), [int(c) for c in cols]
    lab = palette.lab[u]
    wts = cnt.astype(np.float64)
    # init: the 16 most used colours spread by farthest-point
    order = np.argsort(-wts)
    centres = [lab[order[0]]]
    for _ in range(15):
        d = np.min([((lab - c) ** 2).sum(-1) for c in centres], axis=0) * np.sqrt(wts)
        centres.append(lab[int(np.argmax(d))])
    centres = np.array(centres)
    for _ in range(12):
        asg = ((lab[:, None, :] - centres[None]) ** 2).sum(-1).argmin(1)
        for k in range(16):
            m = asg == k
            if m.any():
                centres[k] = (lab[m] * wts[m, None]).sum(0) / wts[m].sum()
    # snap to palette entries
    cols = palette.nearest(centres)
    clab = palette.lab[cols]
    asg = ((lab[:, None, :] - clab[None]) ** 2).sum(-1).argmin(1)
    return asg[inv].astype(np.uint8), [int(c) for c in cols]


def jagpic(w, h, rowpx):
    """a full-screen / menu picture (row major, depth 3, flags 0)"""
    return struct.pack('>8H', w, h, 3, 0, 0, 0, 0, 0) + rowpx


def patch_picture(data, w=None, h=None, fill=0):
    pw, ph, _, _, px, mk = pc_patch(data)
    px = bytes(p if m else fill for p, m in zip(px, mk))
    if w is None:
        return pw, ph, px
    a = np.frombuffer(px, np.uint8).reshape(ph, pw)
    ys = (np.arange(h) * ph // h)
    xs = (np.arange(w) * pw // w)
    return w, h, a[ys][:, xs].tobytes()


# ------------------------------------------------------------------------------------------------

class Converter:
    def __init__(self, args):
        self.args = args
        self.game = args.game
        self.pc = PCWad(args.pc)
        if self.game == 'plutonia' and (self.pc.type != 'IWAD' or 'MAP01' not in self.pc.by):
            die('%s is not a Doom II-format IWAD' % args.pc)
        self.base = Base(args.base)
        self.pal = Palette(self.pc.pal)
        self.pack = Pack(args.hires) if args.hires else None
        self.fusion = args.fusion
        self.budget = args.budget * 1024
        self.rom_maps, self.rom_lumps = set(), []
        self.report = []
        self.look_cache = {}
        self.budgets = None
        self.cur_map = None
        if args.budgets:
            self.budgets = {}
            for line in open(args.budgets):
                p = line.split()
                if len(p) >= 2 and re.match(r'(MAP\d\d|E\dM\d)$', p[0]):
                    self.budgets[p[0]] = int(p[1]) * 1024

    # the picture of a Plutonia texture, column major, from the 1K pack when it has the name
    def tex_picture(self, name):
        w, h, _, _ = self.pc.tex[name]
        if self.pack and self.pack.has(name):
            lin = area_resize_linear(self.pack.image(name), w, h)
            idx = to_palette(lin, self.pal, sharpen=0.35).astype(np.uint8)
            return w, h, colmajor(w, h, idx.tobytes()), True
        w, h, px, mk = self.pc.compose(name)
        return w, h, colmajor(w, h, px), False

    def flat_picture(self, name):
        if self.pack and self.pack.has(name):
            lin = area_resize_linear(self.pack.image(name), 64, 64)
            return to_palette(lin, self.pal, sharpen=0.35).astype(np.uint8).tobytes(), True
        return self.pc.flats[name], False

    def look(self, kind, name):
        """a small Lab thumbnail for the closest-texture choice"""
        key = (kind, name)
        if key in self.look_cache:
            return self.look_cache[key]
        if kind == 'pc':
            w, h, cm, _ = self.tex_picture(name)
        elif kind == 'base':
            p = self.base.picture(name)
            if p is None:
                self.look_cache[key] = None
                return None
            w, h, cm = p
        elif kind == 'pcflat':
            w, h, cm = 64, 64, colmajor(64, 64, self.flat_picture(name)[0])
        else:
            l = [x for x in self.base.L if x['name'] == name and x['size'] == 4096][0]
            w, h, cm = 64, 64, colmajor(64, 64, self.base.get(l)[:4096])
        a = np.frombuffer(cm, np.uint8).reshape(w, h)
        lab = self.pal.lab[a]
        tw, th = 4, 8 if h >= w else 4
        lab = lab[:(w // tw) * tw, :(h // th) * th].reshape(tw, w // tw, th, h // th, 3).mean(axis=(1, 3))
        self.look_cache[key] = lab
        return lab

    def closest(self, kind, name, candidates):
        me = self.look('pc' if kind == 'tex' else 'pcflat', name)
        best, bd = None, 1e18
        for c in candidates:
            v = self.look('base' if kind == 'tex' else 'baseflat', c)
            if v is None or v.shape != me.shape:
                continue
            d = ((v - me) ** 2).sum()
            if d < bd:
                best, bd = c, d
        return best

    # --------------------------------------------------------------------------------------------
    def convert_map(self, mapname, lumps, sky):
        M = {n: bytearray(lumps[n]) for n in MAPLUMPS}
        verts = [struct.unpack('<hh', M['VERTEXES'][k:k + 4]) for k in range(0, len(M['VERTEXES']), 4)]
        sides = [M['SIDEDEFS'][k:k + 30] for k in range(0, len(M['SIDEDEFS']), 30)]
        nm = lambda b: b.split(b'\0')[0].decode('latin1').upper()
        tex_w, flat_w = {}, {}
        masked_mid = set()
        # the walls around player 1's start are what you see first: they count START_BOOST times
        start = None
        for k in range(0, len(M['THINGS']), 10):
            x, y, _, ty, _ = struct.unpack('<hhhhh', M['THINGS'][k:k + 10])
            if ty == 1:
                start = (x, y)
        for k in range(0, len(M['LINEDEFS']), 14):
            v1, v2, flags, special, tag, s1, s2 = struct.unpack('<HHHHHHH', M['LINEDEFS'][k:k + 14])
            (x1, y1), (x2, y2) = verts[v1], verts[v2]
            ln = max(8, int(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5))
            if start and (((x1 + x2) / 2 - start[0]) ** 2 + ((y1 + y2) / 2 - start[1]) ** 2) ** 0.5 < START_NEAR:
                ln *= START_BOOST
            for s in (s1, s2):
                if s == 0xffff or s >= len(sides):
                    continue
                sd = sides[s]
                for o in (4, 12, 20):
                    t = nm(sd[o:o + 8])
                    if t and t != '-':
                        tex_w[t] = tex_w.get(t, 0) + ln * (SIGNATURE_BOOST if t in SIGNATURE_TEX else 1)
                        if o == 20 and s2 != 0xffff:
                            masked_mid.add(t)
        # flats: the floor / ceiling area of the sectors that use them (shoelace over the linedefs)
        area = [0.0] * (len(M['SECTORS']) // 26)
        for k in range(0, len(M['LINEDEFS']), 14):
            v1, v2, flags, special, tag, s1, s2 = struct.unpack('<HHHHHHH', M['LINEDEFS'][k:k + 14])
            (x1, y1), (x2, y2) = verts[v1], verts[v2]
            cr = (x1 * y2 - x2 * y1) / 2.0
            for s, sg in ((s1, 1), (s2, -1)):
                if s != 0xffff and s < len(sides):
                    sec = struct.unpack('<H', sides[s][28:30])[0]
                    if sec < len(area):
                        area[sec] += sg * cr
        for k in range(0, len(M['SECTORS']), 26):
            for o in (4, 12):
                f = nm(M['SECTORS'][k + o:k + o + 8])
                flat_w[f] = flat_w.get(f, 0) + abs(area[k // 26]) + 1
        B = self.base
        used_base = set(t for t in tex_w if t in B.index)
        rename_t, rename_f = {}, {}
        aux_t, aux_f = [], []                         # (donor name, payload builder, weight, bytes4, bytes8)
        log = []

        # ---- textures: units that need a place ------------------------------------------------
        def fits_base(t):
            i = B.index.get(t)
            if i is None or t not in self.pc.tex:
                return i is not None
            w, h, _, _ = self.pc.tex[t]
            return (w, h) == (B.tex[i]['w'], B.tex[i]['h'])

        units = []
        seen = set()
        pc_names = list(self.pc.tex.keys())
        for a, b in ANIM_TEX:
            if a in self.pc.tex and b in self.pc.tex:
                ia, ib = pc_names.index(a), pc_names.index(b)
                frames = pc_names[min(ia, ib):max(ia, ib) + 1]
                if any(f in tex_w for f in frames):
                    seen.update(frames)
                    if not all(fits_base(f) for f in frames) or frames not in B.anim_groups:
                        units.append(('anim', frames, sum(tex_w.get(f, 0) for f in frames)))
        for t in list(tex_w):
            if t in seen:
                continue
            if t.startswith('SW1') or t.startswith('SW2'):
                p1, p2 = 'SW1' + t[3:], 'SW2' + t[3:]
                if p1 in seen:
                    continue
                if p1 in self.pc.tex and p2 in self.pc.tex:
                    seen.update((p1, p2))
                    if not (fits_base(p1) and fits_base(p2) and (p1, p2) in B.switch_pairs):
                        units.append(('switch', [p1, p2], tex_w.get(p1, 0) + tex_w.get(p2, 0)))
                    continue
            seen.add(t)
            if fits_base(t) and t in B.index:
                continue
            if t not in self.pc.tex:
                log.append('unknown texture %s (no picture) -> stand-in' % t)
                continue
            units.append(('single', [t], tex_w[t]))
        units.sort(key=lambda u: -u[2])

        free = [d for d in B.donors if d not in used_base]
        free_sw = [p for p in B.switch_pairs if p[0] not in used_base and p[1] not in used_base]
        free_anim = [g for g in B.anim_groups if not any(x in used_base for x in g)]
        taken = set()

        def take_single(t):
            w, h, _, _ = self.pc.tex[t]
            for d in free:
                i = B.index[d]
                if d not in taken and (B.tex[i]['w'], B.tex[i]['h']) == (w, h):
                    taken.add(d)
                    return d
            return None

        # ---- flats ----------------------------------------------------------------------------
        funits = []
        fseen = set()
        flat_names = self.pc.flat_order
        for a, b in ANIM_FLAT:
            if a in self.pc.flats and b in self.pc.flats:
                ia, ib = flat_names.index(a), flat_names.index(b)
                frames = flat_names[min(ia, ib):max(ia, ib) + 1]
                if any(f in flat_w for f in frames):
                    fseen.update(frames)
                    if frames not in B.flat_anim_groups:
                        funits.append(('anim', frames, sum(flat_w.get(f, 0) for f in frames)))
        for f in flat_w:
            if f in fseen or f == 'F_SKY1':
                continue
            fseen.add(f)
            if f in B.flatset:
                continue
            if f not in self.pc.flats:
                log.append('unknown flat %s -> stand-in' % f)
                continue
            funits.append(('single', [f], flat_w[f]))
        funits.sort(key=lambda u: -u[2])
        used_bflats = set(f for f in flat_w if f in B.flatset)
        ffree = [d for d in B.flat_donors if d not in used_bflats]
        ffree_anim = [g for g in B.flat_anim_groups if not any(x in used_bflats for x in g)]
        ftaken = set()

        # ---- the RAM budget: what is seen most per byte first ----------------------------------------
        budget = self.map_budget(lumps)
        slots = MAX_AUX - 4 - (1 if sky else 0)
        spent = 0
        plan = []                                    # [kind, PC name, donor, depth]
        sky_depth = 0
        WALL_H = 96                                  # a wall's visible height (map units) for the weights

        def tsize(t, depth):
            w, h, _, _ = self.pc.tex[t]
            return 16 + (w * h if depth == 3 else w * h // 2 + 1056)

        def flat_fallback(frames, why):
            for f in frames:
                c = self.closest('flat', f, [x for x in B.flats if x not in ftaken and x != 'F_SKY1'])
                rename_f[f] = c
                log.append('flat %s -> looks like %s (%s)' % (f, c, why))

        def place_flat(kind, frames):
            nonlocal spent
            if kind == 'anim':
                grp = next((g for g in ffree_anim if len(g) == len(frames) and not set(g) & ftaken), None)
                if grp and spent + 4096 * len(frames) <= budget and len(plan) + len(frames) <= slots:
                    ftaken.update(grp)
                    for f, d in zip(frames, grp):
                        rename_f[f] = d
                        plan.append(['flat', f, d, 3])
                    spent += 4096 * len(frames)
                    return
            d = next((x for x in ffree if x not in ftaken), None)
            if d and spent + 4096 <= budget and len(plan) < slots:
                ftaken.add(d)
                for f in frames:
                    rename_f[f] = d
                plan.append(['flat', frames[0], d, 3])
                spent += 4096
                if kind == 'anim':
                    log.append('animated flat %s: one picture (no free animation of %d frames)' % (frames[0], len(frames)))
            else:
                flat_fallback(frames, 'no room')

        pending = []

        def tex_fallback(frames, why):
            w, h, _, _ = self.pc.tex[frames[0]]
            cands = [t['name'] for t in B.tex if not t['masked'] and t['name'] not in taken and
                     (t['w'], t['h']) == (w, h) and B.picture(t['name']) is not None] or \
                    [t['name'] for t in B.tex if not t['masked'] and t['name'] not in taken and B.picture(t['name']) is not None]
            pair = [next((x for x in SIGNATURE_STANDIN.get(f, ()) if x in cands), None) for f in frames]
            if all(pair) and len(set(pair)) == len(frames) > 1:     # a switch: the base game's look-alike pair
                for f, c in zip(frames, pair):
                    rename_t[f] = c
                log.append('switch %s -> looks like %s (%s)' % ('/'.join(frames), '/'.join(pair), why))
                return
            c = next((x for x in SIGNATURE_STANDIN.get(frames[0], ()) if x in cands), None) or \
                self.closest('tex', frames[0], cands)
            for f in frames:
                rename_t[f] = c
            log.append('texture %s -> looks like %s (%s)' % (frames[0], c, why))

        def place_tex(kind, frames, wgt):
            nonlocal spent
            w, h, _, _ = self.pc.tex[frames[0]]
            if any(f in masked_mid and self.has_holes(f) for f in frames):
                cands = [t['name'] for t in B.tex if t['masked'] and (t['w'], t['h']) == (w, h)] or \
                        [t['name'] for t in B.tex if t['masked']]
                c = self.closest('tex', frames[0], cands) or cands[0]
                for f in frames:
                    rename_t[f] = c
                log.append('see-through %s -> %s' % (frames[0], c))
                return
            cost = sum(tsize(f, 2) for f in frames)
            donors = None
            if kind == 'anim':
                donors = next((g for g in free_anim if len(g) == len(frames) and not set(g) & taken and
                               all((B.tex[B.index[x]]['w'], B.tex[B.index[x]]['h']) == (w, h) for x in g)), None)
            elif kind == 'switch':
                p = next((p for p in free_sw if not set(p) & taken and
                          all((B.tex[B.index[x]]['w'], B.tex[B.index[x]]['h']) == self.pc.tex[f][:2] for x, f in zip(p, frames))), None)
                donors = list(p) if p else None
            if donors and spent + cost <= budget and len(plan) + len(frames) <= slots:
                taken.update(donors)
                for f, d in zip(frames, donors):
                    rename_t[f] = d
                    plan.append(['tex', f, d, 2])
                    pending.append((tex_w.get(f, 1), len(plan) - 1))
                spent += cost
                return
            if kind != 'single':
                log.append('%s %s: no %s donor of the same shape -> one picture' % (kind, '/'.join(frames), kind))
            cost = tsize(frames[0], 2)
            d = take_single(frames[0]) if spent + cost <= budget and len(plan) < slots else None
            if d:
                for f in frames:
                    rename_t[f] = d
                plan.append(['tex', frames[0], d, 2])
                pending.append((wgt, len(plan) - 1))
                spent += cost
            else:
                tex_fallback(frames, 'no room')

        work = []
        for kind, frames, wgt in funits:
            work.append((wgt / (4096.0 * len(frames)), 'flat', kind, frames, wgt))
        for kind, frames, wgt in units:
            work.append((wgt * WALL_H / float(sum(tsize(f, 2) for f in frames)), 'tex', kind, frames, wgt))
        work.sort(key=lambda x: (not set(x[3]) & SIGNATURE_TEX, -x[0]))
        for _, what, kind, frames, wgt in work:
            if what == 'flat':
                place_flat(kind, frames)
            else:
                place_tex(kind, frames, wgt)

        # 8-bit for the most used of the placed ones
        for wgt, k in sorted(pending, key=lambda x: -x[0]):
            t = plan[k][1]
            extra = tsize(t, 3) - tsize(t, 2)
            if spent + extra <= budget:
                plan[k][3] = 3
                spent += extra
        # 8-bit for base textures that are 4-bit in the base game (or have a 1K-pack picture)
        ups = []
        for t in used_base:
            if t in self.pc.tex and fits_base(t) and t in B.tlumps and B.ids[B.index[t]] == ('T', t):
                better = B.depth.get(t) == 2 or (self.pack and self.pack.has(t))
                if better and not any(t in g for g in B.anim_groups) and t not in [a for p in ENGINE_SWITCHES for a in p]:
                    ups.append((tex_w[t], t))
        for wgt, t in sorted(ups, reverse=True):
            c = tsize(t, 3)
            if spent + c <= budget and len(plan) < slots:
                plan.append(['tex', t, t, 3])
                spent += c
        # the game's own sky last: 8-bit, else 4-bit, else the base game's sky
        if sky and spent + 32784 <= budget:
            sky_depth = 3
            spent += 32784
        elif sky and spent + 16432 <= budget:
            sky_depth = 2
            spent += 16432
        elif sky:
            sky = None
            log.append('sky: the base game\'s (no room)')

        # ---- rewrite the map ---------------------------------------------------------------------
        def put(b, o, name):
            b[o:o + 8] = name.encode('latin1')[:8].ljust(8, b'\0')
        for s in range(len(sides)):
            for o in (4, 12, 20):
                t = nm(M['SIDEDEFS'][s * 30 + o:s * 30 + o + 8])
                if t in rename_t and rename_t[t]:
                    put(M['SIDEDEFS'], s * 30 + o, rename_t[t])
        for k in range(0, len(M['SECTORS']), 26):
            for o in (4, 12):
                f = nm(M['SECTORS'][k + o:k + o + 8])
                if f in rename_f and rename_f[f]:
                    put(M['SECTORS'], k + o, rename_f[f])
        things = bytearray()
        pe = 0
        for k in range(0, len(M['THINGS']), 10):
            th = bytearray(M['THINGS'][k:k + 10])
            ty = struct.unpack('<H', th[6:8])[0]
            if ty == 0:
                continue
            if ty == 71:
                th[6:8] = struct.pack('<H', 3005)
                pe += 1
            things += th
        M['THINGS'] = things
        if pe:
            log.append('%d Pain Elementals -> Cacodemons' % pe)

        # ---- the extra lumps ----------------------------------------------------------------------
        extra = []
        if sky:
            extra.append((sky.upper(), self.sky_lump(getattr(self, 'sky_source', {}).get(sky.upper(), sky.upper()), sky_depth)))
        texs = [p for p in plan if p[0] == 'tex']
        flats = [p for p in plan if p[0] == 'flat']
        if texs:
            extra.append(('T_START', b''))
            for _, t, d, dep in texs:
                w, h, cm, hi = self.tex_picture(t)
                extra.append((d, jag8(w, h, cm) if dep == 3 else jag4(w, h, cm, B.colormap, self.pal)))
            extra.append(('T_END', b''))
        if flats:
            extra.append(('F_START', b''))
            for _, f, d, _ in flats:
                extra.append((d, self.flat_picture(f)[0]))
            extra.append(('F_END', b''))
        n4 = sum(1 for p in texs if p[3] == 2)
        nhi = sum(1 for p in texs if self.pack and self.pack.has(p[1]))
        self.report.append('%s %-22s budget %3d KB, used %3d KB: %2d textures (%d 4-bit, %d from the 1K pack), '
                           '%d flats, sky %s; %d substituted'
                           % (mapname, '"%s"' % self.map_names.get(mapname, ''), budget // 1024, spent // 1024, len(texs),
                              n4, nhi, len(flats), {0: '-', 2: '4-bit', 3: '8-bit'}[sky_depth],
                              sum(1 for x in log if 'looks like' in x or 'see-through' in x)))
        for x in log:
            self.report.append('      ' + x)
        return [(mapname, b'')] + [(n, bytes(M[n])) for n in MAPLUMPS] + extra

    def has_holes(self, t):
        w, h, px, mk = self.pc.compose(t)
        return 0 in mk

    def map_budget(self, lumps):
        """RAM for the map's extras: measured (--budgets: free zone RAM after loading the map without
        extras, minus the margin), else K - the map's own footprint"""
        if self.cur_map in self.rom_maps:
            # a ROM map's extras stay in the ROM: no RAM (--rom-budget, or its own: --rom-budgets)
            per = dict(x.split('=') for x in (self.args.rom_budgets or '').replace(',', ' ').split() if '=' in x)
            return int(per.get(self.cur_map, self.args.rom_budget)) * 1024
        if self.budgets is not None:
            return self.budgets.get(self.cur_map, 0)
        # measured on Plutonia's 32 maps in ares: texture cache + level data = 177.4 KB (+-3 KB
        # against LEVEL_MODEL), less the 24 KB the cache needs for the base game's own textures
        # and a 4 KB margin
        return int(max(0, 149.4 - self.level_size(lumps) - 3) * 1024)

    @staticmethod
    def footprint(lumps):
        return sum(len(lumps[n]) for n in MAPLUMPS if n != 'THINGS') + len(lumps['THINGS']) // 10 * 96

    def calibrate(self):
        """K = the largest (footprint + extras) among the maps on the Fusion disc - they all run"""
        K = 0
        for f in ('DOOM.WAD', 'DOOM_II.WAD', 'TNT_MINI.WAD', 'RESURRECTION.WAD'):
            p = os.path.join(self.fusion, f)
            if not os.path.exists(p):
                continue
            _, L = read_wad(p, '<')
            for i, l in enumerate(L):
                if l['name'] == 'THINGS' and i + 9 < len(L) and L[i + 9]['name'] == 'BLOCKMAP':
                    lumps = {n: L[i + k]['data'] for k, n in enumerate(MAPLUMPS)}
                    ex = 0
                    for x in L[i + 10:i + 10 + 32]:
                        if x['size'] == 0 and x['name'] not in ('T_START', 'T_END', 'F_START', 'F_END'):
                            break
                        ex += x['size']
                    K = max(K, self.footprint(lumps) + ex)
        self.K = K if not self.budget else self.budget
        return K

    def sky_lump(self, name, depth):
        if self.pack and self.pack.has(name):
            img = self.pack.image(name)
            lin = area_resize_linear(img, 256, 128)
            idx = to_palette(lin, self.pal, sharpen=0.2).astype(np.uint8)
            cm = colmajor(256, 128, idx.tobytes())
        else:
            w, h, px, mk = self.pc.compose(name)
            a = np.frombuffer(px, np.uint8).reshape(h, w)
            xs = np.arange(256) * w // 256          # the whole panorama in 256 columns
            ys = np.arange(128) * h // 128
            cm = colmajor(256, 128, a[ys][:, xs].tobytes())
        if depth == 3:
            return jag8(256, 128, cm)
        return jag4(256, 128, cm, self.base.colormap, self.pal, sky=True)

    # --------------------------------------------------------------------------------------------
    def image_picture(self, path, w, h, dither=0.5, fit=False):
        """a picture file (webp / jpg / png) -> w x h palette indices (row major): cropped to the
        screen's shape (fit: the whole picture, centred on black with a margin - for a logo), area
        average in linear light, nearest palette colour in CIELAB with light error diffusion
        (smooth gradients in photos and paintings)"""
        from PIL import Image
        if path.startswith('lump:'):
            # a picture of the PWAD itself (SIGIL's SIGILINT, SIGIL II's widescreen SIGILIN2): DOOM's
            # 320 x 200 screen is 4:3 with tall pixels - square pixels first (200 -> 240 lines), then
            # the 4:3 middle as below (a 446-wide picture loses its sides, as on a 4:3 DOOM)
            pw, ph, _, _, px, mk = pc_patch(self.pc.by[path[5:]]['data'])
            pal = np.frombuffer(self.pc.pal, np.uint8).reshape(256, 3)
            rgb = pal[np.frombuffer(bytes(px), np.uint8)].reshape(ph, pw, 3)
            rgb = rgb * np.frombuffer(bytes(mk), np.uint8).reshape(ph, pw, 1)
            src = Image.fromarray(rgb.astype(np.uint8)).resize((pw, ph * 6 // 5), Image.LANCZOS).convert('RGBA')
        else:
            src = Image.open(path).convert('RGBA')
        img = Image.new('RGBA', src.size, (0, 0, 0, 255))
        img.alpha_composite(src)                        # transparent -> black
        img = img.convert('RGB')
        target = 4 / 3                                  # the TV picture the 320 x 224 screen fills
        iw, ih = img.size
        if iw == w and abs(ih - h) <= 8:
            # made for the screen (320 x 224 for the 320 x 220 title): used as it is, centred
            canvas = Image.new('RGB', (w, h), (0, 0, 0))
            canvas.paste(img, (0, (h - ih) // 2))
            img = canvas
        elif fit is None:
            pass
        elif fit:
            m = 1.0 if fit is True else fit             # fit=1.12: a 6 % margin on each side
            cw, ch = max(iw * m, ih * m * target), max(ih * m, iw * m / target)
            cw, ch = int(round(cw)), int(round(ch))
            canvas = Image.new('RGB', (cw, ch), (0, 0, 0))
            canvas.paste(img, ((cw - iw) // 2, (ch - ih) // 2))
            img = canvas
        elif iw / ih > target:
            nw = int(ih * target)
            img = img.crop(((iw - nw) // 2, 0, (iw - nw) // 2 + nw, ih))
        else:
            nh = int(iw / target)
            img = img.crop((0, (ih - nh) // 2, iw, (ih - nh) // 2 + nh))
        lin = area_resize_linear(img, w, h)
        return to_palette(lin, self.pal, dither=dither).astype(np.uint8).tobytes()

    def map_lumps(self, m):
        i = max(k for k, l in enumerate(self.pc.L) if l['name'] == m)     # the last WAD's map
        ml = {self.pc.L[i + 1 + k]['name']: self.pc.L[i + 1 + k]['data'] for k in range(10)}
        if list(ml) != MAPLUMPS:
            die('%s: unexpected map lumps %s' % (m, list(ml)))
        return ml

    def level_size(self, ml):
        """the level's own RAM in KB (LEVEL_MODEL)"""
        c = {n: len(ml[n]) for n in MAPLUMPS}
        ns = c['SECTORS'] // 26
        f = [1, c['LINEDEFS'] / 14, c['SIDEDEFS'] / 30, c['VERTEXES'] / 4, c['SEGS'] / 12, c['SSECTORS'] / 4,
             c['NODES'] / 28, ns, (ns + 1) * ns / 16, c['BLOCKMAP'], c['THINGS'] / 10]
        return sum(a * b for a, b in zip(LEVEL_MODEL, f)) / 1024

    def build(self, out):
        if self.game == 'plutonia':
            lumps = self.build_plutonia()
        else:
            lumps = self.build_sigil()
        write_pwad(out, lumps)
        if self.args.rom_maps:
            write_pwad(self.args.rom_maps, self.rom_lumps)
        return lumps

    def doom2_cd_tracks(self):
        """Fusion's DOOM_II.WAD: the CD audio track of each map number (cdTrack, else cdTrackOffset +
        its song's number among the music lumps M_START..M_END) and of the title / intermission /
        victory / end"""
        _, L = read_wad(os.path.join(self.fusion, 'DOOM_II.WAD'), '<')
        names = [l['name'] for l in L]
        songs = names[names.index('M_START') + 1:names.index('M_END')] if 'M_START' in names else []
        dm = next(l['data'] for l in L if l['name'] == 'DMAPINFO').decode('latin1')
        gi = re.search(r'gameinfo\s*\{(.*?)\}', dm, re.S | re.I)
        out = {'maps': {}, 'cdTrackOffset': 0}
        for k in ('cdTrackOffset', 'titleCdTrack', 'intermissionCdTrack', 'victoryCdTrack', 'endCdTrack'):
            m = re.search(r'\b%s\s*=\s*(\d+)' % k, gi.group(1) if gi else '', re.I)
            if m:
                out[k] = int(m.group(1))
        for name, body in re.findall(r'map\s+"?(\w+)"?[^{]*\{(.*?)\}', dm, re.S | re.I):
            num = re.search(r'mapnumber\s*=\s*(\d+)', body, re.I)
            n = int(num.group(1)) if num else (int(name[3:]) if name.upper().startswith('MAP') else 0)
            cda = re.search(r'\bcdTrack\s*=\s*(\d+)', body, re.I)
            mus = re.search(r'\bmusic\s*=\s*"?(\w+)"?', body, re.I)
            if cda:
                out['maps'][n] = int(cda.group(1))
            elif mus and mus.group(1).upper() in songs:
                out['maps'][n] = out['cdTrackOffset'] + songs.index(mus.group(1).upper()) + 1
        return out

    def fusion_lump(self, wad, name):
        _, L = read_wad(os.path.join(self.fusion, wad), '<')
        return next(l['data'] for l in L if l['name'] == name)

    def convert_maps(self, maps):
        out = []
        for m, sky in maps:
            ml = self.map_lumps(m)
            self.cur_map = m
            if m not in self.rom_maps and self.budgets is not None and self.budgets.get(m, 0) < 16 * 1024 + 16416:
                sky = None                        # no room even for the 4-bit sky: the base game's sky
            lumps = self.convert_map(m, ml, sky)
            if m in self.rom_maps:
                self.rom_lumps += lumps           # --rom-maps: into the ROM (tools/make_rommaps.py)
            else:
                out += lumps
        return out

    # ---- The Plutonia Experiment -----------------------------------------------------------------
    def build_plutonia(self):
        self.map_names = {'MAP%02d' % (n + 1): NAMES[n] for n in range(32)}
        lumps = []
        pc = self.pc
        lumps.append(('PLAYPAL', pc.by['PLAYPAL']['data']))
        # music
        vdir = os.path.join(self.fusion, 'VGM_PLUTONIA')
        music = {}
        if os.path.isdir(vdir):
            for f in sorted(os.listdir(vdir)):
                m = re.match(r'(MAP\d\d|TTL|INT|READ)_.*\.ZGM$', f.upper())
                if m:
                    key = m.group(1)
                    music['P_' + key[:6]] = open(os.path.join(vdir, f), 'rb').read()
        lumps.append(('M_START', b''))
        for k in sorted(music):
            lumps.append((k, music[k]))
        lumps.append(('M_END', b''))
        mus = lambda n: ('P_MAP%02d' % n) if 'P_MAP%02d' % n in music else 'P_MAP01'
        # maps the 32X's RAM cannot hold: left out, "next" goes on to the next one that fits
        fits = []
        for n in range(1, 33):
            m = 'MAP%02d' % n
            kb = self.level_size(self.map_lumps(m))
            if kb <= self.args.maxlevel:
                fits.append(m)
            else:
                self.report.append('%s %-22s level %3.0f KB: TOO BIG for the 32X (limit %d KB) - left out'
                                   % (m, '"%s"' % NAMES[n - 1], kb, self.args.maxlevel))
        def chain(n):
            while n and 'MAP%02d' % n not in fits:
                n = n + 1 if n < 30 else None
            return n
        # the CD audio list: Plutonia plays the same CD tracks as DOOM II (Fusion's DOOM_II.WAD:
        # map n's cdTrack = cdaNum, else cdTrackOffset + the number of its song among the music
        # lumps, as g_game.c computes it; the title / intermission / victory / end tracks too)
        cd2 = self.doom2_cd_tracks()
        # DMAPINFO
        dm = ['gameinfo', '{',
              '    cdTrackOffset = %d' % cd2['cdTrackOffset']] + \
             ['    %s = %d' % (k, cd2[k]) for k in ('titleCdTrack', 'intermissionCdTrack', 'victoryCdTrack', 'endCdTrack') if cd2.get(k)] + [
              '    titleMus = "P_TTL"', '    intermissionMus = "P_INT"', '    victoryMus = "P_READ"',
              '    endMus = "P_READ"', '    borderFlat = "FLAT5_7"', '    titleTime = 16000', '    titlePage = "title"',
              '    creditsTime = 900', '    creditsPage = "credits1"', '    endText = "%s"' % P4TEXT,
              '    endFlat = "RROCK17"', '\tendShowCast = 2', '\tstopFireTime = 0', '\ttitleStartPos = 0',
              '\tnoAttractDemo = 1', '}']
        for n in range(1, 33):
            if 'MAP%02d' % n not in fits:
                continue
            sky = 'sky1' if n <= 11 else 'sky2' if n <= 20 else 'sky3'
            nxt = chain({15: 16, 30: None, 31: 16, 32: 16}.get(n, n + 1))
            e = ['map "MAP%02d" "%s"' % (n, NAMES[n - 1]), '{', '    sky = "%s"' % sky]
            if nxt:
                e.append('    next = "MAP%02d"' % nxt)
            e += ['    mapnumber = %d' % n, '    music = "%s"' % mus(n)]
            if cd2['maps'].get(n):
                e.append('    cdTrack = %d' % cd2['maps'][n])
            if n == 6:
                e += ['    intermissionText = "%s"' % P1TEXT, '\tintermissionFlat = "SLIME16"']
            if n == 11:
                e += ['    intermissionText = "%s"' % P2TEXT, '\tintermissionFlat = "RROCK14"']
            if n == 20:
                e += ['    intermissionText = "%s"' % P3TEXT, '\tintermissionFlat = "RROCK11"']
            if n == 15:
                e += ['\tsecretnext = "MAP31"', '\tsecretIntermissionText = "%s"' % P5TEXT]
            if n == 31:
                e += ['\tsecretnext = "MAP32"', '\tsecretIntermissionText = "%s"' % P6TEXT]
            if n == 7:
                e += ['\tmancubiSpecial', '\tarachnoSpecial']
            e.append('}')
            dm += e
        lumps.append(('DMAPINFO', ('\r\n'.join(dm) + '\r\n').encode('latin1')))
        credits1 = ('ci ^99The Plutonia Experiment\nxi\nr  ^A2Levels\nc  ^A2...\nli Dario Casali\nli Milo Casali\nxi\n'
                    'r  ^A2Published by\nc  ^A2...\nli id Software\nxi\nci ^99id Software is:\nxi\n'
                    'r  ^A2Programmers\nc  ^A2...\nli John Carmack\nli John Romero\nli Dave Taylor\nxi\n'
                    'r  ^A2Artists\nc  ^A2...\nli Adrian Carmack\nli Kevin Cloud\nxi\nr  ^A2Music/FX\nc  ^A2...\n'
                    'li Robert Prince\n')
        lumps.append(('CREDITS1', credits1.encode('latin1')))
        lumps.append(('CREDITS2', self.fusion_lump('DOOM_II.WAD', 'CREDITS2').replace(b'DOOM II 32X Resurrection', b'DOOM CD32X Fusion')))
        lumps += self.convert_maps([('MAP%02d' % n, 'sky1' if n <= 11 else 'sky2' if n <= 20 else 'sky3') for n in range(1, 33)
                                    if 'MAP%02d' % n in fits])
        def pic(name, w, h):
            pw, ph, px = patch_picture(pc.by[name]['data'], w, h)
            return jagpic(pw, ph, px)
        lumps.append(('TITLE', pic('TITLEPIC', 320, 220)))
        lumps.append(('INTERPIC', pic('INTERPIC', 320, 224)))
        pw, ph, px = patch_picture(pc.by['M_DOOM']['data'])
        lumps.append(('M_DOOM', jagpic(pw, ph, px)))
        for n in ('PERCENT', 'I_KILLS', 'I_ITEMS', 'I_SECRET', 'I_LEVEL', 'I_FINISH'):
            lumps.append((n, self.fusion_lump('DOOM_II.WAD', n)))
        lumps.append(('BOSSBACK', pic('BOSSBACK', 320, 224)))
        return lumps

    # ---- SIGIL / SIGIL II (episodes 5 / 6 for The Ultimate DOOM) ----------------------------------
    def build_sigil(self):
        ep = 5 if self.game == 'sigil' else 6
        title = 'SIGIL' if ep == 5 else 'SIGIL II'
        umap = parse_umapinfo(self.pc.by['UMAPINFO']['data'].decode('latin1'))
        maps = ['E%dM%d' % (ep, k) for k in range(1, 10)]
        self.map_names = {m: umap.get(m, {}).get('levelname', m) for m in maps}
        # maps the 32X's RAM cannot hold (the level alone, before any texture): left out, the
        # episode's "next" chain goes on to the next one that fits
        # --rom-maps: the maps named by --rom go into the game's ROM instead (their read-only parts
        # used in place, tools/make_rommaps.py) and stay in the episode
        fits, sizes = [], {}
        want_rom = set(x.upper() for x in (self.args.rom or '').split(',') if x) if self.args.rom_maps else set()
        for m in maps:
            sizes[m] = self.level_size(self.map_lumps(m))
            if m in want_rom:
                self.rom_maps.add(m)
                fits.append(m)
            elif sizes[m] <= self.args.maxlevel:
                fits.append(m)
        for m in maps:
            self.report.append('%s %-28s level %4.0f KB %s' % (m, '"%s"' % self.map_names[m], sizes[m],
                               'ROM map' if m in self.rom_maps else 'ok' if m in fits else
                               'TOO BIG for the 32X (limit %d KB): left out' % self.args.maxlevel))
        if not fits:
            die('no %s map fits the 32X' % title)
        def nxt(m, key='next'):
            seen = set()
            n = umap.get(m, {}).get(key)
            while n and n not in fits and n not in seen:
                seen.add(n)
                n = umap.get(n, {}).get('next')
            return n if n in fits else None
        # the music: streamed PCM files in a folder on the data track (spcmDirs; tools/make_spcm.py
        # makes SIGIL/<song>.PCM, SIGIL2/<song>.PCM). The player finds a file by its song's music
        # lump name, so the WAD lists the songs as (empty) music lumps; musicStream = 1 makes the
        # game play them whatever the music option says.
        order = ['D_INTRO'] + ['D_E%dM%d' % (ep, k) for k in range(1, 10)] + ['D_INTER']
        lumps = [('PLAYPAL', self.pc.by['PLAYPAL']['data']), ('M_START', b'')]
        lumps += [(song, b'SPCM') for song in order]
        lumps.append(('M_END', b''))
        spcm_dir = 'SIGIL' if ep == 5 else 'SIGIL2'
        last = [m for m in fits if not nxt(m)]
        endtext = ''
        for m in maps:
            if umap.get(m, {}).get('intertext'):
                endtext = umap[m]['intertext']
        txt = lambda t: t.upper().replace('"', "'").replace('\n', '*')
        # --music cd: the disc's CD audio tracks instead (the SIGIL CD audio disc, build.sh MUSIC=sigil):
        # the 11 songs on tracks --cdtrack .. --cdtrack + 10 (DMAPINFO cdTrack n = the disc's track n + 1)
        cdt = lambda song: self.args.cdtrack + order.index(song)
        if self.args.music == 'cd':
            mus_cfg = ['    cdMusic = 1', '    intermissionCdTrack = %d' % cdt('D_INTER'),
                       '    victoryCdTrack = %d' % cdt('D_INTER'), '    endCdTrack = %d' % cdt('D_INTER')]
        else:
            mus_cfg = ['    musicStream = 1', '    spcmDirs = "%s"' % spcm_dir]
        # the title (the logo while the first map loads) is silent on the SIGIL CD audio disc: no
        # title song -> S_StartSong stops the music (cdMusic, CD track 0)
        dm = ['gameinfo', '{', '    titleMus = "%s"' % ('' if self.args.music == 'cd' else 'D_INTRO'),
              '    intermissionMus = "D_INTER"', '    victoryMus = "D_INTER"',
              '    endMus = "D_INTER"'] + mus_cfg + ['    borderFlat = "FLOOR7_2"',
              # the title shows for SIGIL_TITLE_TICS, then the game starts by itself (no button; no
              # credits pages, no attract demo) - Fusion's 13000 waited minutes for a press
              '    titleTime = %d' % SIGIL_TITLE_TICS, '    titlePage = "title"',
              '    creditsTime = 0', '    creditsPage = ""', '    endText = "%s"' % txt(endtext),
              '    endFlat = "MFLR8_3"', '\tendShowCast = 0', '\tstopFireTime = 0', '\ttitleStartPos = 0',
              '\tnoAttractDemo = 1', '}']
        # the map's sky goes by the base game's hell sky's name: its own SKY5 / SKY6 picture under that
        # name when it fits in the map's RAM, else the base game's SKY3 (red hell) - not SKY1
        sky = 'sky3'
        self.sky_source = {'SKY3': 'SKY%d' % ep}
        for i, m in enumerate(fits):
            u = umap.get(m, {})
            e = ['map "%s" "%s"' % (m, self.map_names[m]), '{', '    sky = "%s"' % sky]
            if nxt(m):
                e.append('    next = "%s"' % nxt(m))
            song = (u.get('music') or 'D_E%dM%s' % (ep, m[-1])).upper()
            song = song if song in order else 'D_E%dM%s' % (ep, m[-1])
            e += ['    mapnumber = %d' % (i + 1), '    music = "%s"' % song]
            if self.args.music == 'cd':
                e.append('    cdTrack = %d' % cdt(song))
            if nxt(m, 'nextsecret'):
                e.append('\tsecretnext = "%s"' % nxt(m, 'nextsecret'))
            if i == 0:
                e.append('\tpistolStart')
            e.append('}')
            dm += e
        lumps.append(('DMAPINFO', ('\r\n'.join(dm) + '\r\n').encode('latin1')))
        credits1 = ('ci ^99%s\nxi\nr  ^A2Levels\nc  ^A2...\nli John Romero\nxi\nr  ^A2Published by\nc  ^A2...\n'
                    'li Romero Games\nxi\nci ^99id Software is:\nxi\nr  ^A2Programmers\nc  ^A2...\nli John Carmack\n'
                    'li John Romero\nli Dave Taylor\nxi\nr  ^A2Artists\nc  ^A2...\nli Adrian Carmack\nli Kevin Cloud\n' % title)
        lumps.append(('CREDITS1', credits1.encode('latin1')))
        lumps.append(('CREDITS2', self.fusion_lump('DOOM.WAD', 'CREDITS2')))
        lumps += self.convert_maps([(m, sky) for m in fits])
        # SIGIL's flat red logo: nearest colour, no dithering (dithered, a bright red speckle covered it);
        # SIGIL II's shaded logo keeps the light dithering
        lumps.append(('TITLE', jagpic(320, 220, self.image_picture(self.args.title, 320, 220,
                                                                   dither=0.0 if ep == 5 else 0.5, fit=True))))
        lumps.append(('INTERPIC', jagpic(320, 224, self.image_picture(self.args.interpic, 320, 224))))
        for n in ('M_DOOM', 'PERCENT', 'I_KILLS', 'I_ITEMS', 'I_SECRET', 'I_LEVEL', 'I_FINISH'):
            lumps.append((n, self.fusion_lump('DOOM.WAD', n)))
        return lumps


def parse_umapinfo(text):
    """UMAPINFO -> {map: {levelname, next, nextsecret, music, skytexture, intertext}} (lower-case keys)"""
    out = {}
    text = re.sub(r'//[^\n]*', '', text)
    for m, body in re.findall(r'map\s+(\w+)\s*\{(.*?)\}', text, re.S | re.I):
        d = {}
        for k, v in re.findall(r'(\w+)\s*=\s*((?:"[^"]*"\s*,?\s*)+|[^\n]+)', body):
            k = k.lower()
            strs = re.findall(r'"([^"]*)"', v)
            d[k] = '\\n'.join(strs) if k == 'intertext' else (strs[0] if strs else v.strip())
        out[m.upper()] = d
    return out


def write_pwad(path, lumps):
    data = bytearray(b'PWAD' + bytes(8))
    dirent = []
    for name, d in lumps:
        dirent.append((len(data), len(d), name))
        data += d
        while len(data) % 4:
            data += b'\0'
    off = len(data)
    for pos, size, name in dirent:
        data += struct.pack('<II', pos if size else 0, size) + name.encode('latin1')[:8].ljust(8, b'\0')
    struct.pack_into('<II', data, 4, len(dirent), off)
    open(path, 'wb').write(data)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--game', choices=('plutonia', 'sigil', 'sigil2'), default='plutonia')
    ap.add_argument('--pc', required=True, nargs='+', help='the PC IWAD (and PWADs on top)')
    ap.add_argument('--title', help='SIGIL: the title picture')
    ap.add_argument('--interpic', help='SIGIL: the intermission / level loading picture (a file, or lump:NAME '
                    'for a picture in the PWAD)')
    ap.add_argument('--music', choices=('spcm', 'cd'), default='spcm',
                    help='SIGIL: streamed PCM files on the data track (spcm) or the disc\'s CD audio tracks (cd)')
    ap.add_argument('--cdtrack', type=int, default=1, help='SIGIL --music cd: the cdTrack of its title song (11 tracks: title, E?M1-9, intermission)')
    ap.add_argument('--rom-maps', help='SIGIL: a PWAD for the maps named by --rom (they go into the ROM: tools/make_rommaps.py)')
    ap.add_argument('--rom', help='SIGIL with --rom-maps: the ROM maps, e.g. E5M4,E5M9')
    ap.add_argument('--rom-budget', type=int, default=160, help='KB of ROM for a ROM map\'s textures, flats and sky')
    ap.add_argument('--rom-budgets', help='ROM maps with their own budget, e.g. "E6M8=96"')
    ap.add_argument('--maxlevel', type=int, default=175, help='KB of RAM a level may take (bigger maps are left out)')
    ap.add_argument('--base', required=True)
    ap.add_argument('--fusion', required=True)
    ap.add_argument('--hires')
    ap.add_argument('--budget', type=int, default=0, help='KB of RAM for a map + its extras (0: calibrate)')
    ap.add_argument('--budgets', help='file: lines "MAPxx KB" - RAM for each map\'s extras (measured)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--report')
    a = ap.parse_args()
    c = Converter(a)
    c.build(a.out)
    rep = '\n'.join(c.report) + '\n'
    if a.report:
        open(a.report, 'w').write(rep)
    print(rep)
    print('%s: %s (%d bytes)' % (os.path.basename(a.out).upper(), a.out, os.path.getsize(a.out)))


if __name__ == '__main__':
    main()
