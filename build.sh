#!/bin/bash
# D32XR CD32X - builds the disc: Doom 32X Resurrection v3.5 booting from the Sega CD into the
# RAM cart (8 / 16 MB board: the game's second 2 MB in page 7), with D32XR's own Sega CD code
# (CD music, PCM sound effects) running in mega CD mode 2. README.md tells how.
#
#   ./build.sh 2>&1 | tee build_log.txt
#
# Needs (in the project folder's data/, never committed):
#   - your Doom 32X Resurrection v3.5 ROM (any *.32x there, e.g. DCD32XF_V3.32x): its IWAD
#     is the game's data (tools/extract_iwad.py takes it out once -> data/doom32xf.wad)
#   - optional: splash.png (the picture of the loading screen: the DOOM logo)
#   - optional: music/Track02.wav ... (CD audio tracks 2 and on); none: one silent track
# and the D32XR team's devkit (GENDEV, default /opt/d32xr-dk/opt/toolchains/sega) for the game,
# Chilly Willy's toolchain in /opt/toolchains/sega for the boot stack (cd32x/).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
trap 'echo; echo "*** BUILD FAILED at line $LINENO: $BASH_COMMAND"' ERR
NAME="${NAME:-D32XR_CD32X_R1}"
PAGE=7
DATA="$HERE/data"
ROMS="$HERE/cd32x/subcpu/ROMS"
mkdir -p "$ROMS" "$HERE/build"

echo "==> game data"
if [ ! -f "$DATA/doom32xf.wad" ]; then
  ROM="$(ls "$DATA"/*.32x "$DATA"/*.32X 2>/dev/null | head -1)"
  [ -n "$ROM" ] || { echo "*** put your Doom 32X Resurrection v3.5 ROM (.32x) in $DATA - stopping"; exit 1; }
  python3 "$HERE/tools/extract_iwad.py" "$ROM" "$DATA/doom32xf.wad"
fi
echo "==> game (D32XR v3.5, CD32X=1)"
bash "$HERE/tools/build_game.sh" "$HERE/build/D32XR_CD32X.32x" CD32X=1
python3 "$HERE/tools/prep_openlara_cd.py" "$HERE/build/D32XR_CD32X.32x" "$ROMS/D32XR.32X"
echo "==> loading screen"
if [ -f "$DATA/splash.png" ]; then python3 "$HERE/tools/make_splash.py" "$DATA/splash.png" "$ROMS/IMAGE.RAW"
else                               python3 "$HERE/tools/make_splash.py" - "$ROMS/IMAGE.RAW"; fi
echo "==> SH2 loader"
cd "$HERE/cd32x/sh2" && make -f Makefile.cdloader clean > /dev/null \
  && make -f Makefile.cdloader LOADER_DEFS="-DCDL_TARGET_OPENLARA=0 -DCDL_SPLASH=1 -DCDL_D32XR_PAGE=$PAGE"
echo "==> Sub-CPU and 68000 listener"
cd "$HERE/cd32x/subcpu" && make clean > /dev/null \
  && make cd CART_DEFS=-DCART_PAGED GAME_DEFS="-DD32XR_CD=$PAGE" VOLID=DOOM_CD32X EXTRA_DIR="${CDFS:+$DATA/fusion}"
ISO="$HERE/cd32x/subcpu/CDROMPlayer.iso"
grep -a -q "SH2-D32XR-CD-M1-LOADER" "$ISO" || { echo "*** the disc does not hold the D32XR loader - stopping"; exit 1; }
for f in APP.BIN CDLOADER.BIN D32XR.32X IMAGE.RAW; do
  [ -f "$HERE/cd32x/subcpu/cd/$f" ] || { echo "*** $f is not on the disc - stopping"; exit 1; }
done
cmp -s "$HERE/cd32x/subcpu/cd/D32XR.32X" "$ROMS/D32XR.32X" || { echo "*** the disc has an old game - stopping"; exit 1; }

echo "==> CD audio"
MUS="$HERE/build/music"; rm -rf "$MUS"; mkdir -p "$MUS"
if ls "$DATA"/music/Track*.wav > /dev/null 2>&1; then
  cp "$DATA"/music/Track*.wav "$MUS"/
else
  python3 - "$MUS/Track02.wav" <<'PY'
import sys, wave
w = wave.open(sys.argv[1], "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
w.writeframes(bytes(4 * 44100 * 2)); w.close()
PY
  echo "    no data/music/Track*.wav: one silent audio track"
fi
cd "$HERE/cd32x/subcpu" && python3 make_mixed_cd2.py CDROMPlayer.iso "$MUS"/Track*.wav --out "$NAME"
mkdir -p "$HERE/discs/$NAME" && mv -f "$NAME.bin" "$NAME.cue" "$HERE/discs/$NAME/"
echo
echo "==> done: discs/$NAME/$NAME.cue (with its .bin)"
