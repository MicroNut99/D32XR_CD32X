#!/bin/bash
# build_game.sh <out.32x> [CD32X=1]: builds D32XR v3.5 (d32xr/) the way the Doom 32X Resurrection
# v3.5 release was built (the CI's second option: DISABLE_CDFS, fire, DMA sound, small lumps,
# 4 mip levels - the program comes out byte for byte the release's), with the IWAD from
# data/doom32xf.wad, in build/d32xr (a copy: the source folder stays clean).
# GENDEV = the D32XR team's devkit (chillys-sega-devkit-20220418), default /opt/d32xr-dk/opt/toolchains/sega.
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$(realpath -m "$1")"; shift
DK="${GENDEV:-/opt/d32xr-dk/opt/toolchains/sega}"
[ -x "$DK/sh-elf/bin/sh-elf-gcc" ] || { echo "*** no devkit in $DK (set GENDEV)"; exit 1; }
[ -f "$HERE/data/doom32xf.wad" ] || { echo "*** no data/doom32xf.wad (tools/extract_iwad.py <your v3.5 ROM> data/doom32xf.wad)"; exit 1; }
B="$HERE/build/d32xr"
rm -rf "$B"; mkdir -p "$HERE/build"; cp -r "$HERE/d32xr" "$B"
cp "$HERE/data/doom32xf.wad" "$B/doom32xf.wad"
cd "$B"
# CDFS=1: the Fusion build - the game reads WADs from the CD (the game select menu, SOUNDS.WAD)
NOCDFS="DISABLE_CDFS=1"; [ -n "${CDFS:-}" ] && NOCDFS="D32XR_CDFS=1"
env $NOCDFS ENABLE_FIRE_ANIMATION=1 ENABLE_DMA_SOUND=1 USE_SMALL_LUMPS=1 MIPLEVELS=4 "$@" \
  make -j8 release ROOTDIR="$DK" GENDEV="$DK" TITLE="${TITLE:-Doom 32X Resurrection}" VERSION="${VERSION:-3.5}" > build.log 2>&1 \
  || { grep -n -i -B2 -A2 " error\|undefined ref" build.log | head -40; echo "*** game build failed (build/d32xr/build.log)"; exit 1; }
cp D32XR.32x "$OUT"
echo "game: $OUT ($(stat -c %s "$OUT") bytes)"
