#!/bin/bash
# make_sigil_cdda.sh - SIGIL's and SIGIL II's music as CD audio tracks -> data/sigil_cdda/Track02..23.wav
# (README "SIGIL music"). Needs ffmpeg, cmake, gcc/g++, git.
#
#   tools/make_sigil_cdda.sh <SIGIL-DOOM-OPL-Soundtrack.mp4> <sigil2.wad>
#
# Track02-12 SIGIL: cut from the OPL soundtrack video at its track changes (the captions; each cut
#                   sits in the silence / at the end of the fade between two songs)
# Track13-23 SIGIL II: its MIDIs played through an OPL3 emulator with DOOM's DMX instruments (the same
#                   kind of sound as the video): one pass + 9.6 s of the loop fading out (like the
#                   video), +4.3 dB (measured: the video's level against the same render of SIGIL's MIDIs)
# Order of each game: title (D_INTRO), E?M1 .. E?M9, intermission (D_INTER); make_game.py --cdtrack 1 / 12.
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
MP4="$1"; WAD2="$2"; OUT="$HERE/data/sigil_cdda"; W="$HERE/build/sigil_cdda"
[ -f "$MP4" ] && [ -f "$WAD2" ] || { echo "usage: $0 <SIGIL-DOOM-OPL-Soundtrack.mp4> <sigil2.wad>"; exit 1; }
mkdir -p "$OUT" "$W"
n=2
cut() { ffmpeg -y -v error -ss "$1" -to "$2" -i "$MP4" -vn -ar 44100 -ac 2 -c:a pcm_s16le "$OUT/Track$(printf %02d $n).wav"; n=$((n+1)); }
#   start    end      song
cut 0      16.8      # "Lands of Ire" (title)
cut 16.8   143.9     # "Hate Machine" (E5M1)
cut 143.9  268.0     # "Ain't the Boss of Me" (E5M2)
cut 268.0  480.1     # "Quell the Beast" (E5M3)
cut 480.1  660.3     # "Riot Squadron" (E5M4)
cut 660.3  844.4     # "Alice" (E5M5)
cut 844.4  1011.5    # "Besieged City" (E5M6)
cut 1011.5 1358.6    # "Watching You" (E5M7)
cut 1358.6 1629.7    # "Halls of Perdition" (E5M8)
cut 1629.7 1934.6    # "Adrenaline in the Blood" (E5M9)
cut 1934.6 2064.8    # "Big Guns" (intermission)

# SIGIL II: libADLMIDI + tools/oplrender.c
if [ ! -x "$W/oplrender" ]; then
  [ -d "$W/libADLMIDI" ] || git clone -q --depth 1 https://github.com/Wohlstand/libADLMIDI.git "$W/libADLMIDI"
  cmake -S "$W/libADLMIDI" -B "$W/libADLMIDI/build" -DCMAKE_BUILD_TYPE=Release -DUSE_NUKED_EMULATOR=ON \
        -DlibADLMIDI_SHARED=OFF -DlibADLMIDI_STATIC=ON > /dev/null
  make -C "$W/libADLMIDI/build" -j4 ADLMIDI_static > /dev/null 2>&1 || make -C "$W/libADLMIDI/build" -j4 > /dev/null
  gcc -O2 "$HERE/tools/oplrender.c" -I"$W/libADLMIDI/include" "$W/libADLMIDI/build/libADLMIDI.a" -lstdc++ -lm -lpthread -o "$W/oplrender"
fi
python3 - "$WAD2" "$W" <<'PY'
import struct, sys
d = open(sys.argv[1], 'rb').read(); n, o = struct.unpack('<II', d[4:12])
for i in range(n):
    p, s, nm = struct.unpack('<II8s', d[o + i * 16:o + i * 16 + 16]); nm = nm.split(b'\0')[0].decode()
    if nm.startswith('D_') and d[p:p + 4] == b'MThd':
        open('%s/%s.mid' % (sys.argv[2], nm), 'wb').write(d[p:p + s])
PY
BANK=16   # libADLMIDI's embedded "DMX (Bobby Prince v1)": DOOM's GENMIDI
for s in D_INTRO D_E6M1 D_E6M2 D_E6M3 D_E6M4 D_E6M5 D_E6M6 D_E6M7 D_E6M8 D_E6M9 D_INTER; do
  TAIL=9.6; [ $s = D_INTRO ] && TAIL=1.0
  "$W/oplrender" "$W/$s.mid" "$W/$s.wav" $BANK $TAIL
  ffmpeg -y -v error -i "$W/$s.wav" -af volume=4.3dB -c:a pcm_s16le "$OUT/Track$(printf %02d $n).wav"; n=$((n+1))
done
echo "data/sigil_cdda: Track02-$(printf %02d $((n-1))).wav"
