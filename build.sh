#!/bin/bash
# D32XR CD32X - builds the disc: DOOM CD32X Fusion v3.0 booting from the Sega CD into the RAM
# cart (8 / 16 MB board: the game's second 2 MB in page 7), with D32XR's own Sega CD code (WADs,
# music, video, PCM sound effects) running in mega CD mode 2. README.md tells how.
#
#   ./build.sh 2>&1 | tee build_log.txt
#
# Needs (in the project folder's data/, never committed):
#   - your DOOM CD32X Fusion v3.0 ROM (any *.32x there, e.g. DCD32XF_V3.32x): its IWAD
#     is the game's data (tools/extract_iwad.py takes it out once -> data/doom32xf.wad)
#   - your DOOM CD32X Fusion disc image (DCD32XF_V3.bin or .iso): its files (WADs, music,
#     video) go on the new disc (tools/extract_iso.py copies them once -> data/fusion/)
#   - optional: splash.png (the picture of the loading screen: the DOOM logo)
#   - optional: plutonia.wad (+ hires/*.pk3), doom.wad + sigil/sigil.wad, sigil/sigil2.wad (+ pictures):
#     PLUTONIA.WAD, SIGIL.WAD, SIGIL_II.WAD (tools/make_game.py)
#   - optional: sigil_cdda/Track02..23.wav (SIGIL's music -> streamed PCM files, tools/make_sigil_cdda.sh)
#   - optional: sigil_albums/Track02..23.wav (MUSIC=sigil: the albums as CD audio, tools/make_sigil_albums.py)
#   - optional: music/Track02.wav ... (the CD audio tracks: DOOM / DOOM II / Resurrection / Plutonia's
#     soundtrack, Fusion's numbering); else the tracks of "DOOM CD32X FUSION V3 with IDKFA
#     Soundtrack/*.cue" in the project folder (IDKFA=<cue>); none: one silent track
# and the D32XR team's devkit (GENDEV, default /opt/d32xr-dk/opt/toolchains/sega) for the game,
# Chilly Willy's toolchain in /opt/toolchains/sega for the boot stack (cd32x/).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
trap 'echo; echo "*** BUILD FAILED at line $LINENO: $BASH_COMMAND"' ERR
NAME="${NAME:-D32XR_CD32X_R2}"
PAGE=7
# the music (README "Music"): MUSIC=idkfa (default) - CD audio = Fusion's IDKFA soundtrack, SIGIL's
# songs streamed from the data track; MUSIC=sigil - CD audio = SIGIL's and SIGIL II's songs
MUSIC="${MUSIC:-idkfa}"
CDONLY=""; [ "$MUSIC" = sigil ] && CDONLY=1
# the title fire (README: "The title fire"): on unless FIRE=0
FIRE="${FIRE-1}"; [ "$FIRE" = 0 ] && FIRE=""; export FIRE
# ROMMAPS="E5M9 E6M8 ..." (the SIGIL edition, README "SIGIL in the ROM"): those SIGIL / SIGIL II maps,
# too big for the 32X's RAM from the CD, go into the game's ROM image (their read-only parts used in
# place: tools/make_rommaps.py, d32xr/p_setup.c). The room comes from DOOM II's monster sprites, so
# the games that need them (DOOM II, TNT MINI, PLUTONIA, RESURRECTION) and MAPDEV are left off.
ROMMAPS="${ROMMAPS:-}"
DATA="$HERE/data"
ROMS="$HERE/cd32x/subcpu/ROMS"
mkdir -p "$ROMS" "$HERE/build"

echo "==> game data"
if [ ! -f "$DATA/doom32xf.wad" ]; then
  ROM="$(ls "$DATA"/*.32x "$DATA"/*.32X 2>/dev/null | head -1)"
  [ -n "$ROM" ] || { echo "*** put your Doom 32X Resurrection v3.5 ROM (.32x) in $DATA - stopping"; exit 1; }
  python3 "$HERE/tools/extract_iwad.py" "$ROM" "$DATA/doom32xf.wad"
fi
if [ ! -f "$DATA/fusion/SOUNDS.WAD" ]; then
  IMG="$(ls "$DATA"/*.bin "$DATA"/*.BIN "$DATA"/*.iso "$DATA"/*.ISO 2>/dev/null | head -1)"
  [ -n "$IMG" ] || { echo "*** put your DOOM CD32X Fusion disc image (.bin or .iso) in $DATA - stopping"; exit 1; }
  python3 "$HERE/tools/extract_iso.py" "$IMG" "$DATA/fusion"
fi
# the disc's files: the Fusion disc's, plus PLUTONIA.WAD made from your plutonia.wad (a fifth game
# in the select menu, tools/make_game.py; README "Plutonia")
DISC="$HERE/build/disc_files"; rm -rf "$DISC"; mkdir -p "$DISC"; cp -r "$DATA/fusion/." "$DISC/"
# left off the IDKFA disc to make room (README "The disc"): Fusion's map-testing MAPDEV.WAD (the
# menu hides it) and the loose VGM folders (copies of music already inside the WADs; never read).
# CUT="" keeps them all.
if [ "$MUSIC" = sigil ]; then CUT="${CUT-}"           # the SIGIL disc has room for everything
else CUT="${CUT-MAPDEV.WAD VGM_DOOM VGM_DOOM_II VGM_PLUTONIA VGM_TNT}"; fi
[ -n "$ROMMAPS" ] && CUT="$CUT MAPDEV.WAD DOOM_II.WAD TNT_MINI.WAD RESURRECTION.WAD VGM_DOOM_II VGM_PLUTONIA VGM_TNT"
# SIGILONLY=1 (with ROMMAPS): DOOM.WAD left off too - only SIGIL and SIGIL II on the disc, so the
# textures and flats only DOOM's maps use make room for one more ROM map
[ -n "$ROMMAPS" ] && [ -n "${SIGILONLY:-}" ] && CUT="$CUT DOOM.WAD VGM_DOOM"
for f in $CUT; do rm -rf "$DISC/$f"; done
if [ -f "$DATA/plutonia.wad" ] && [ -z "$ROMMAPS" ]; then
  echo "==> PLUTONIA.WAD (from data/plutonia.wad${HIRES:+}, budgets ${PLUT_BUDGETS:-tools/plutonia_budgets.txt})"
  PK="$(ls "$DATA"/hires/*.pk3 2>/dev/null | head -1)"; [ "${HIRES:-1}" = 0 ] && PK=""
  python3 "$HERE/tools/make_game.py" --game plutonia --pc "$DATA/plutonia.wad" --base "$DATA/doom32xf.wad" --fusion "$DATA/fusion" \
          ${PK:+--hires "$PK"} --budgets "${PLUT_BUDGETS:-$HERE/tools/plutonia_budgets.txt}" \
          --out "$DISC/PLUTONIA.WAD" --report "$HERE/build/plutonia_report.txt" > "$HERE/build/plutonia_log.txt" \
    || { tail -20 "$HERE/build/plutonia_log.txt"; echo "*** PLUTONIA.WAD failed"; exit 1; }
  tail -1 "$HERE/build/plutonia_log.txt"
fi
# SIGIL / SIGIL II (README "SIGIL"): episodes 5 / 6 on top of your doom.wad, music = the disc's CD audio
rm -f "$HERE"/build/rom_sigil*.wad
for G in sigil sigil2; do
  # SIGIL and SIGIL II are on their own disc (MUSIC=sigil, with their own CD audio); the DOOM
  # disc leaves them off (WITHSIGIL=1 puts them back, with the streamed SPCM music)
  [ "$MUSIC" = sigil ] || [ -n "${WITHSIGIL:-}" ] || continue
  if [ $G = sigil ]; then PW=sigil.wad; PIC=sigil; OUTW=SIGIL.WAD; CDT=1
  else                    PW=sigil2.wad; PIC=Sigil2; OUTW=SIGIL_II.WAD; CDT=12; fi
  SMUS="--music spcm"; [ "$MUSIC" = sigil ] && SMUS="--music cd --cdtrack $CDT"
  [ -f "$DATA/sigil/$PW" ] && [ -f "$DATA/doom.wad" ] || continue
  # the pictures: your <name>_1.jpg / .jpg first (newart: <name>_1.jpg made at 320 x 224), else the .webp from the SIGIL download; the tally
  # background: sigil-wallpaper_1.jpg (made at 320 x 224: used as it is), else sigil-wallpaper.jpg
  PIC="$(ls "$DATA/sigil/${PIC}_1.jpg" "$DATA/sigil/$PIC.jpg" "$DATA/sigil/$PIC.png" "$DATA/sigil/$PIC.webp" 2>/dev/null | head -1)"
  WALL="$(ls "$DATA/sigil/sigil-wallpaper_1.jpg" "$DATA/sigil/sigil-wallpaper.jpg" 2>/dev/null | head -1)"
  echo "==> $OUTW (from data/sigil/$PW${ROMMAPS:+; ROM maps of $ROMMAPS})"
  ROMOPT=""; [ -n "$ROMMAPS" ] && ROMOPT="--rom-maps $HERE/build/rom_$G.wad --rom ${ROMMAPS// /,} --rom-budget ${ROMBUDGET:-64}"
  python3 "$HERE/tools/make_game.py" --game $G --pc "$DATA/doom.wad" "$DATA/sigil/$PW" --base "$DATA/doom32xf.wad" \
          --fusion "$DATA/fusion" --title "$PIC" --interpic "$WALL" $SMUS $ROMOPT \
          --out "$DISC/$OUTW" --report "$HERE/build/${G}_report.txt" > "$HERE/build/${G}_log.txt" \
    || { tail -20 "$HERE/build/${G}_log.txt"; echo "*** $OUTW failed"; exit 1; }
  tail -1 "$HERE/build/${G}_log.txt"
done
# SIGIL's and SIGIL II's music: streamed PCM files on the data track (folders SIGIL/ and SIGIL2/,
# tools/make_spcm.py) from data/sigil_cdda/Track02-23.wav (tools/make_sigil_cdda.sh)
if [ "$MUSIC" != sigil ] && { [ -f "$DISC/SIGIL.WAD" ] || [ -f "$DISC/SIGIL_II.WAD" ]; }; then
  if [ -f "$DATA/sigil_cdda/Track23.wav" ]; then
    echo "==> SIGIL music (streamed PCM files, from data/sigil_cdda)"
    python3 "$HERE/tools/make_spcm.py" "$DATA/sigil_cdda" "$DISC" > "$HERE/build/spcm_log.txt" \
      || { tail -5 "$HERE/build/spcm_log.txt"; echo "*** SIGIL music failed"; exit 1; }
    tail -1 "$HERE/build/spcm_log.txt"
  else
    echo "    no data/sigil_cdda/Track02-23.wav: SIGIL plays no music (tools/make_sigil_cdda.sh makes them)"
  fi
fi
IWAD="$DATA/doom32xf.wad"
if [ -n "$ROMMAPS" ]; then
  echo "==> the ROM maps ($ROMMAPS) into the game's IWAD"
  # NOREJECT=1: the ROM maps without reject tables (more room, more sight checks)
  python3 "$HERE/tools/make_rommaps.py" --iwad "$DATA/doom32xf.wad" --maps $(ls "$HERE"/build/rom_sigil*.wad) \
          --disc $(ls "$DISC"/*.WAD) ${NOREJECT:+--no-reject} --out "$HERE/build/rom_iwad.wad"
  IWAD="$HERE/build/rom_iwad.wad"
fi
echo "==> preload (the WADs kept in the 16 MB cart, pages 2-6)"
python3 "$HERE/tools/make_preload.py" plan "$DISC" "$HERE/build/preload.json" \
        "$HERE/build/cd32x_preload.h" "$HERE/cd32x/subcpu/preload_names.h"
echo "==> game (DOOM CD32X Fusion v3.0, CD32X=1${FIRE:+, with the title fire})"
ROMMAPS="$ROMMAPS" IWAD="$IWAD" CDONLY="$CDONLY" PRELOAD_H="$HERE/build/cd32x_preload.h" bash "$HERE/tools/build_game.sh" "$HERE/build/D32XR_CD32X.32x" CD32X=1
python3 "$HERE/tools/prep_openlara_cd.py" "$HERE/build/D32XR_CD32X.32x" "$ROMS/D32XR.32X"
python3 "$HERE/tools/make_preload.py" loader "$HERE/build/preload.json" "$ROMS/D32XR.32X" "$HERE/cd32x/sh2/preload.h"
echo "==> loading screen"
if [ -f "$DATA/splash.png" ]; then python3 "$HERE/tools/make_splash.py" "$DATA/splash.png" "$ROMS/IMAGE.RAW"
else                               python3 "$HERE/tools/make_splash.py" - "$ROMS/IMAGE.RAW"; fi
echo "==> SH2 loader"
cd "$HERE/cd32x/sh2" && make -f Makefile.cdloader clean > /dev/null \
  && make -f Makefile.cdloader LOADER_DEFS="-DCDL_TARGET_OPENLARA=0 -DCDL_SPLASH=1 -DCDL_D32XR_PAGE=$PAGE"
echo "==> Sub-CPU and 68000 listener"
cd "$HERE/cd32x/subcpu" && make clean > /dev/null \
  && make cd CART_DEFS=-DCART_PAGED GAME_DEFS="-DD32XR_CD=$PAGE" VOLID=DOOM_CD32X EXTRA_DIR="$DISC"
ISO="$HERE/cd32x/subcpu/CDROMPlayer.iso"
grep -a -q "SH2-D32XR-CD-M1-LOADER" "$ISO" || { echo "*** the disc does not hold the D32XR loader - stopping"; exit 1; }
for f in APP.BIN CDLOADER.BIN D32XR.32X IMAGE.RAW SOUNDS.WAD ${SIGILONLY:-DOOM.WAD} VIDEO/IDLOGO.ROQ; do
  [ "$f" = 1 ] && continue
  [ -f "$HERE/cd32x/subcpu/cd/$f" ] || { echo "*** $f is not on the disc - stopping"; exit 1; }
done
cmp -s "$HERE/cd32x/subcpu/cd/D32XR.32X" "$ROMS/D32XR.32X" || { echo "*** the disc has an old game - stopping"; exit 1; }

echo "==> CD audio"
MUS="$HERE/build/music"; rm -rf "$MUS"; mkdir -p "$MUS"
# the CD audio tracks: the soundtrack of DOOM, DOOM II, Resurrection and Plutonia (the music option
# CD), numbered as Fusion's WADs number them (README "CD audio"): data/music/Track02.wav ...
IDKFA="${IDKFA:-$HERE/DOOM CD32X FUSION V3 with IDKFA Soundtrack/DOOM CD32X FUSION V3 with IDKFA Soundtrack.cue}"
if [ "$MUSIC" = sigil ]; then
  # the SIGIL CD audio disc: SIGIL's songs on tracks 2-12, SIGIL II's on 13-23 - the albums
  # (Buckethead, THORR: data/sigil_albums, tools/make_sigil_albums.py) if made, else the OPL
  # renders (data/sigil_cdda, tools/make_sigil_cdda.sh); SIGILCDDA=<folder> for another
  SCD="${SIGILCDDA:-$DATA/sigil_albums}"; [ -f "$SCD/Track23.wav" ] || SCD="$DATA/sigil_cdda"
  ls "$SCD"/Track*.wav > /dev/null 2>&1 || { echo "*** MUSIC=sigil needs data/sigil_albums or data/sigil_cdda Track02-23.wav"; exit 1; }
  cp "$SCD"/Track*.wav "$MUS"/
  echo "    SIGIL's CD audio from ${SCD#$HERE/}"
  echo "    $(ls "$MUS" | wc -l) audio tracks: SIGIL's and SIGIL II's songs"
elif ls "$DATA"/music/Track*.wav > /dev/null 2>&1; then
  cp "$DATA"/music/Track*.wav "$MUS"/
  echo "    $(ls "$MUS" | wc -l) audio tracks from data/music"
elif [ -f "$IDKFA" ]; then
  # Fusion's IDKFA soundtrack, its tracks 2-26 exactly as on that disc (IDKFA=<cue> for another)
  python3 "$HERE/tools/extract_cue_audio.py" "$IDKFA" "$MUS"
else
  python3 - "$MUS/Track02.wav" <<'PY'
import sys, wave
w = wave.open(sys.argv[1], "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
w.writeframes(bytes(4 * 44100 * 2)); w.close()
PY
  echo "    no data/music/Track*.wav: one silent audio track"
fi
# no gaps between the audio tracks (like the IDKFA disc's cue): 2 s each would cost 7 MB
cd "$HERE/cd32x/subcpu" && python3 make_mixed_cd2.py CDROMPlayer.iso "$MUS"/Track*.wav --pregap 0 --out "$NAME"
SECTORS=$(( $(stat -c %s "$NAME.bin") / 2352 ))
printf "    the disc: %d sectors = %d:%02d of an 80:00 CD\n" $SECTORS $((SECTORS / 4500)) $((SECTORS % 4500 / 75))
[ $SECTORS -le 359849 ] || echo "*** WARNING: longer than an 80-minute CD ($SECTORS > 359849 sectors)"
mkdir -p "$HERE/discs/$NAME" && mv -f "$NAME.bin" "$NAME.cue" "$HERE/discs/$NAME/"
echo
echo "==> done: discs/$NAME/$NAME.cue (with its .bin)"
