"""d32xr_wad.py - reading PC and D32XR WADs, Jaguar LZSS, PC textures and patches (the tools' shared code)."""
import struct
def read_wad(path, endian=None):
    d=open(path,'rb').read()
    if endian is None:
        n,o=struct.unpack('<II',d[4:12]); endian='<'
        if o>len(d) or n>100000: endian='>'
    n,o=struct.unpack(endian+'II',d[4:12])
    L=[]
    for i in range(n):
        p,s=struct.unpack(endian+'II',d[o+i*16:o+i*16+8]); raw=d[o+i*16+8:o+i*16+16]
        nm=(bytes([raw[0]&0x7f])+raw[1:]).split(b'\0')[0].decode('latin1')
        L.append({'name':nm,'pos':p,'size':s,'comp':raw[0]>>7,'data':d[p:p+s]})
    return d[:4].decode(),L

def lzss_decode(inp):
    inp=bytes(inp)+bytes(64); out=bytearray(); i=0; n=len(inp)
    while i<n:
        idb=inp[i]; i+=1
        for b in range(8):
            if idb&1:
                pos=(inp[i]<<4)|(inp[i+1]>>4); ln=(inp[i+1]&0xf)+1; i+=2
                if ln==1: return bytes(out)
                src=len(out)-pos-1
                for j in range(ln): out.append(out[src+j])
            else:
                out.append(inp[i]); i+=1
            idb>>=1
    return bytes(out)

def lzss_encode(data):
    """Jaguar LZSS: id byte (LSB first), 1 = back reference (12-bit distance-1, 4-bit length-1, lengths 3-16), end = length 1"""
    out=bytearray(); i=0; n=len(data)
    # hash chains for speed
    head={}; prev=[-1]*n
    def insert(p):
        if p+3<=n:
            k=data[p:p+3]; prev[p]=head.get(k,-1); head[k]=p
    items=[]
    while i<n:
        best_len=0; best_d=0
        if i+3<=n:
            p=head.get(data[i:i+3],-1); tries=0
            while p>=0 and i-p<=4096 and tries<256:
                l=0
                while l<16 and i+l<n and data[p+l]==data[i+l]: l+=1
                if l>best_len: best_len=l; best_d=i-p
                if l==16: break
                p=prev[p]; tries+=1
        if best_len>=3:
            items.append((1,best_d-1,best_len-1))
            for k in range(best_len): insert(i+k)
            i+=best_len
        else:
            items.append((0,data[i])); insert(i); i+=1
    items.append((1,0,0))  # end of stream: length field 0 -> len 1
    for g in range(0,len(items),8):
        grp=items[g:g+8]; idb=0
        for b,it in enumerate(grp):
            if it[0]: idb|=1<<b
        out.append(idb)
        for it in grp:
            if it[0]: out.append((it[1]>>4)&0xff); out.append(((it[1]&0xf)<<4)|it[2])
            else: out.append(it[1])
    return bytes(out)

def pc_textures(L):
    """PC TEXTURE1/2 + PNAMES -> {name: (w, h, masked, [(ox, oy, patchname)])}"""
    lump=lambda n:[l for l in L if l['name']==n]
    pn=lump('PNAMES')[0]['data']; n=struct.unpack('<I',pn[:4])[0]
    pnames=[pn[4+i*8:12+i*8].split(b'\0')[0].decode('latin1').upper() for i in range(n)]
    tex={}
    for tn in ('TEXTURE1','TEXTURE2'):
        for l in lump(tn):
            d=l['data']; c=struct.unpack('<I',d[:4])[0]
            for o in struct.unpack('<%dI'%c,d[4:4+4*c]):
                name=d[o:o+8].split(b'\0')[0].decode('latin1').upper()
                masked,w,h=struct.unpack('<IHH',d[o+8:o+16]); pc=struct.unpack('<H',d[o+20:o+22])[0]
                ps=[]
                for k in range(pc):
                    ox,oy,pi=struct.unpack('<hhH',d[o+22+k*10:o+28+k*10]); ps.append((ox,oy,pnames[pi]))
                tex[name]=(w,h,masked,ps)
    return tex

def pc_patch(data):
    """PC patch -> (w, h, leftoff, topoff, pixels[w*h] row-major, mask[w*h])"""
    w,h,lo,to=struct.unpack('<hhhh',data[:8])
    cols=struct.unpack('<%dI'%w,data[8:8+4*w])
    px=bytearray(w*h); mk=bytearray(w*h)
    for x,c in enumerate(cols):
        p=c; top=-1
        while True:
            td=data[p]
            if td==0xff: break
            ln=data[p+1]
            for i in range(ln):
                y=td+i
                if 0<=y<h: px[y*w+x]=data[p+3+i]; mk[y*w+x]=1
            p+=4+ln
    return w,h,lo,to,px,mk

def section(L, a, b, alt=()):
    out=[]; on=False
    for l in L:
        if l['name'] in (a,)+tuple(x[0] for x in alt): on=True; continue
        if l['name'] in (b,)+tuple(x[1] for x in alt): on=False; continue
        if on and l['size']>0: out.append(l)
    return out

class PCWad:
    """one PC IWAD, or an IWAD with PWADs on top (later WADs replace lumps, textures, patches, flats
    of the same name: SIGIL on DOOM.WAD)"""
    def __init__(self, paths):
        if isinstance(paths, str):
            paths = [paths]
        self.L = []
        self.by = {}
        self.tex = {}
        self.patches = {}
        self.flats = {}
        self.flat_order = []
        self.type = None
        for path in paths:
            t, L = read_wad(path, '<')
            self.type = self.type or t
            self.L += L
            for l in L:
                self.by[l['name']] = l
            if any(l['name'] in ('TEXTURE1', 'TEXTURE2') for l in L) and any(l['name'] == 'PNAMES' for l in L):
                self.tex.update(pc_textures(L))
            for l in section(L, 'P_START', 'P_END', (('PP_START', 'PP_END'),)):
                self.patches[l['name']] = l
            for l in section(L, 'F_START', 'F_END', (('FF_START', 'FF_END'),)):
                if l['size'] == 4096:
                    if l['name'] not in self.flats:
                        self.flat_order.append(l['name'])
                    self.flats[l['name']] = l['data']
        first = read_wad(paths[0], '<')[1]
        self.pal = [l for l in first if l['name'] == 'PLAYPAL'][0]['data'][:768]
        self._cache = {}

    def compose(self, name):
        """-> (w, h, pixels row-major, mask) of a PC texture"""
        if name in self._cache: return self._cache[name]
        w,h,masked,ps=self.tex[name]
        px=bytearray(w*h); mk=bytearray(w*h)
        for ox,oy,pn in ps:
            l=self.patches.get(pn) or self.by.get(pn)
            if l is None: continue
            pw,ph,_,_,ppx,pmk=pc_patch(l['data'])
            for y in range(ph):
                ty=oy+y
                if ty<0 or ty>=h: continue
                for x in range(pw):
                    tx=ox+x
                    if 0<=tx<w and pmk[y*pw+x]:
                        px[ty*w+tx]=ppx[y*pw+x]; mk[ty*w+tx]=1
        self._cache[name]=(w,h,bytes(px),bytes(mk))
        return self._cache[name]

def lzss_decode_big(inp):
    """the VGM (.ZGM) variant of the Jaguar LZSS (window > 4 KB, src-md/vgm.c): back reference =
    16-bit distance-1 (big-endian) + 8-bit length-1; length 1 = end of stream"""
    inp = bytes(inp) + bytes(64); out = bytearray(); i = 0; n = len(inp)
    while i < n:
        idb = inp[i]; i += 1
        for b in range(8):
            if idb & 1:
                pos = (inp[i] << 8) | inp[i + 1]; ln = inp[i + 2] + 1; i += 3
                if ln == 1:
                    return bytes(out)
                src = len(out) - pos - 1
                for j in range(ln):
                    out.append(out[src + j])
            else:
                out.append(inp[i]); i += 1
            idb >>= 1
    return bytes(out)


def lzss_encode_big(data, window=0x7F00):
    """encoder for lzss_decode_big (lengths 3-256, distances up to the player's 32 KB ring)"""
    out = bytearray(); i = 0; n = len(data); head = {}; prev = [-1] * n; items = []
    def ins(p):
        if p + 3 <= n:
            k = data[p:p + 3]; prev[p] = head.get(k, -1); head[k] = p
    while i < n:
        bl = 0; bd = 0
        if i + 3 <= n:
            p = head.get(data[i:i + 3], -1); tries = 0
            while p >= 0 and i - p <= window and tries < 64:
                l = 0
                while l < 256 and i + l < n and data[p + l] == data[i + l]:
                    l += 1
                if l > bl:
                    bl, bd = l, i - p
                if l == 256:
                    break
                p = prev[p]; tries += 1
        if bl >= 4:
            items.append((1, bd - 1, bl - 1))
            for k in range(bl):
                ins(i + k)
            i += bl
        else:
            items.append((0, data[i])); ins(i); i += 1
    items.append((1, 0, 0))
    for g in range(0, len(items), 8):
        grp = items[g:g + 8]; idb = 0
        for b, it in enumerate(grp):
            if it[0]:
                idb |= 1 << b
        out.append(idb)
        for it in grp:
            if it[0]:
                out += bytes(((it[1] >> 8) & 0xff, it[1] & 0xff, it[2]))
            else:
                out.append(it[1])
    return bytes(out)
