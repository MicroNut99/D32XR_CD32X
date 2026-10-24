#!/bin/bash
# build_game.sh <out.32x> [CD32X=1]: builds DOOM CD32X Fusion v3.0 from d32xr/ (viciious/d32xr
# tag fusion_v3.0 = v3.5) the way the Fusion release was built - D32XR's default options: the CD
# file system on (WADs, music and video from the disc), no title fire. Without CD32X=1 the
# program comes out byte for byte the release's (only the build date differs).
# FIRE=1: the title fire of Resurrection v3.5 (ENABLE_FIRE_ANIMATION, FIRE_TIME=470), see README
# (build.sh sets it unless FIRE=0).
# The IWAD comes from data/doom32xf.wad (tools/extract_iwad.py takes it out of the Fusion ROM).
# Built in build/d32xr (a copy: the source folder stays clean).
# GENDEV = the D32XR team's devkit (chillys-sega-devkit-20220418), default /opt/d32xr-dk/opt/toolchains/sega.
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$(realpath -m "$1")"; shift
DK="${GENDEV:-/opt/d32xr-dk/opt/toolchains/sega}"
[ -x "$DK/sh-elf/bin/sh-elf-gcc" ] || { echo "*** no devkit in $DK (set GENDEV)"; exit 1; }
[ -f "$HERE/data/doom32xf.wad" ] || { echo "*** no data/doom32xf.wad (tools/extract_iwad.py <your Fusion ROM> data/doom32xf.wad)"; exit 1; }
B="$HERE/build/d32xr"
rm -rf "$B"; mkdir -p "$HERE/build"; cp -r "$HERE/d32xr" "$B"
# IWAD=<file>: another IWAD (build.sh ROMMAPS: with the ROM maps, tools/make_rommaps.py)
cp "${IWAD:-$HERE/data/doom32xf.wad}" "$B/doom32xf.wad"
# the ROM maps' engine side (p_setup.c) only on that disc (build.sh ROMMAPS=...)
[ -n "${ROMMAPS:-}" ] && sed -i '1i #define CD32X_ROMMAPS 1' "$B/p_setup.c"
# and the draw distance (far lines as darkness in busy views, r_phase1.c / r_phase6.c): the SIGIL
# disc's maps need it; on the DOOM disc the program has no room for it beside Fusion's IWAD
[ -n "${ROMMAPS:-}" ] && sed -i '1i #define CD32X_DARKFAR 1' "$B/r_phase1.c" "$B/r_phase6.c" "$B/r_main.c"
# the SIGIL disc's speed-ups (README "Frame rate"; the DOOM disc has no room for them):
# - pauses in the wait loops of the two SH2s (doomdef.h CD32X_PAUSE; off: NOIDLE=1)
[ -n "${ROMMAPS:-}" ] && [ -z "${NOIDLE:-}" ] && sed -i '1i #define CD32X_IDLE 1' "$B/doomdef.h"
# TEST_O2SDRAM=1: emulator testing only - the renderer's SDRAM code at -O2 (4 KB more SDRAM; the zone
# gives 6 KB so the main SH2's stack still fits - too little zone for the biggest maps)
[ -n "${TEST_O2SDRAM:-}" ] && for f in "$B"/r_main.c "$B"/r_phase*.c; do sed -i '1i #define CD32X_O2_SDRAM 1' "$f"; done && \
  sed -i 's|^#define ATTR_DATA_CACHE_ALIGN __attribute__((section(".sdata"), optimize("Os")))$|#ifdef CD32X_O2_SDRAM\n#define ATTR_DATA_CACHE_ALIGN __attribute__((section(".sdata"), optimize("O2")))\n#else\n&\n#endif|' "$B/doomdef.h" && \
  sed -i 's|^#define BASE_ZONE_SIZE 0x33000$|#define BASE_ZONE_SIZE 0x31800|' "$B/marsnew.c"
# DRAWDIST=far: the farther draw distance (r_phase1.c)
[ "${DRAWDIST:-}" = far ] && sed -i '1i #define CD32X_DRAWDIST_FAR 1' "$B/r_phase1.c"
# PRELOAD_H: the 68000's table of the WADs kept in the 16 MB cart (tools/make_preload.py)
[ -n "${PRELOAD_H:-}" ] && cp "$PRELOAD_H" "$B/src-md/cd32x_preload.h"
# CDONLY=1 (build.sh MUSIC=sigil): the SIGIL CD audio disc - only cdMusic games play CD audio, the
# music option CD means FM for the others (marssound.c, CD32X_CDONLY)
[ -n "${CDONLY:-}" ] && sed -i '1i #define CD32X_CDONLY 1' "$B/marssound.c"
# TEST_GOD=1: emulator testing only - the player takes no damage
[ -n "${TEST_GOD:-}" ] && sed -i 's|^\tif ( !(target->flags \& MF_SHOOTABLE) )$|\tif (target->player) return;\n&|' "$B/p_inter.c"
# TEST_STATS=1: emulator testing only - r_main.c keeps the renderer's peak use against its limits (r_stat)
[ -n "${TEST_STATS:-}" ] && sed -i '1i #define R_STATS 1' "$B/r_main.c" && sed -i '1i #define R_STATS_STACK 1' "$B/marsonly.c"
# TEST_WALLS=n TEST_PLANES=n: emulator testing only - other renderer limits (MAXWALLCMDS 165, MAXVISPLANES 32)
[ -n "${TEST_WALLS:-}" ] && sed -i "s/^#define\tMAXWALLCMDS\t\t165/#define\tMAXWALLCMDS\t\t$TEST_WALLS/" "$B/r_local.h"
[ -n "${TEST_PLANES:-}" ] && sed -i "s/^#define\tMAXVISPLANES\t32/#define\tMAXVISPLANES\t$TEST_PLANES/" "$B/r_local.h"
cd "$B"
OPTS=""; [ -n "${FIRE:-}" ] && OPTS="ENABLE_FIRE_ANIMATION=1 FIRE_TIME=470"
env $OPTS "$@" \
  make -j8 release ROOTDIR="$DK" GENDEV="$DK" TITLE="${TITLE:-Doom CD32X Fusion}" VERSION="${VERSION:-3.0}" > build.log 2>&1 \
  || { grep -n -i -B2 -A2 " error\|undefined ref" build.log | head -40; echo "*** game build failed (build/d32xr/build.log)"; exit 1; }
cp D32XR.32x "$OUT"
echo "game: $OUT ($(stat -c %s "$OUT") bytes)"
