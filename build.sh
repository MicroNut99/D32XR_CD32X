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
# CART=ED: the Mega EverDrive PRO as the 16 MB cart (CD32X BootCamp docs/12).  The game's second 2 MB
#   go to page 1 (the 4 MB cart's place) instead of page 7, which would hold the EverDrive's bank 31
#   (its battery RAM); the preload stays in pages 2-6.  The game's own 68000 program writes the
#   EverDrive's window registers for its page switches (src-md/crt0.s CD32X_ED) and turns the write
#   bit on for its saves.  ED-SAVE (always with CART=ED): the save (piece 11) and the CD loader's
#   preload record (piece 15) are in the EverDrive's save bank (bank 31, its battery RAM) instead of
#   page 1, which the EverDrive wipes at its menu - the game's 68000 program reads and writes the bank
#   itself (crt0.s), the launcher's Sub-CPU program routes CMD 61 there (CART_EDSAVE, listener M1SAVE=1)
#   and the launcher's header declares save RAM (EDCD_SAVE=1 -> make_edcd.py; kept on the SD card as
#   MEGA/gamedata/<the launcher>/bram.srm).  The saves persist; the WADs (10 MB of PSRAM, pages 2-6)
#   are still copied in at every boot - nothing can keep them.
#   CART=ED EDCD=1 bash build.sh   -> discs/D32XR_CD32X_R2_EDCD_DOOM/ + cd32x/subcpu/EDCD_DOOM.32X, the
#                                     launcher started from the EverDrive menu with the disc in the
#                                     Sega CD (BOOTCAMP=<folder>, default ../CD32X-BootCamp)
CART="${CART:-}"
case "$CART" in ""|ED) ;; *) echo "*** CART is ED or unset - stopping"; exit 1;; esac
PAGE=7; [ "$CART" = ED ] && PAGE=1
GAME_ED=""; [ "$CART" = ED ] && GAME_ED="CD32X_ED=1 CD32X_PAGE=1"
# EDCD=1: the ROM on the EverDrive disc is built for the cartridge boot's map (MODE1=1 -> CD32X_MODE1).
# Without it the game's own 68000 code reads the Mega CD where a CD boot puts it - Word RAM at 0x200000,
# which in cartridge mode is the cart - and the disc's file list comes back empty ("No playable WADs
# found on the CD", 26 Oct 2026, in ares and on the console).  That disc is then EverDrive-only.
[ "${EDCD:-0}" = 1 ] && GAME_ED="$GAME_ED CD32X_MODE1=1"
# ED-SAVE (above) and ED-PAGE: -DCART_ED is what compiles the four word writes to CTRL4-7 into the
# launcher's CMD 68 (the EverDrive ignores the single even byte the 16MB-PCB page register wants)
EDSAVE_M1=""; EDSAVE_DEFS=""; [ "$CART" = ED ] && { EDSAVE_M1="M1SAVE=1"; EDSAVE_DEFS=" -DCART_EDSAVE -DCART_ED"; export EDCD_SAVE=1; }
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

# the names (MicroNut99, 26 Oct 2026: every new .32X and bin/cue carries a unique EDCD tag, so nothing
# can overwrite the 16 MB-cart build's or another variant's): the EverDrive build's disc is
# D32XR_CD32X_R2_EDCD_DOOM[_SIGIL][_ROMMAPS] and its launcher EDCD_DOOM[_SIGIL][_ROMMAPS].32X - the
# EverDrive keeps each launcher's saves under its own name (MEGA/gamedata/<launcher>/bram.srm), so a
# variant never reads another's.  The 16 MB-cart disc keeps its own name, as burned.
ED_TAG=""
if [ "$CART" = ED ]; then
  ED_TAG="_EDCD_DOOM"
  [ "$MUSIC" = sigil ] && ED_TAG="${ED_TAG}_SIGIL"
  [ -n "${ROMMAPS:-}" ] && ED_TAG="${ED_TAG}_ROMMAPS"
fi
# The override is DISC_NAME, NOT NAME: WSL exports NAME (the Windows machine's name) into every shell,
# so ${NAME:-...} silently takes it - the 26 Oct 13:18 build wrote discs/Mumra/Mumra.cue on a host
# called Mumra, with no EDCD tag on it at all.
NAME="${DISC_NAME:-D32XR_CD32X_R2$ED_TAG}"
if [ "$CART" = ED ]; then
  EDCD_32X="EDCD_DOOM${ED_TAG#_EDCD_DOOM}.32X"    # EDCD_DOOM.32X, EDCD_DOOM_SIGIL.32X, ...
else
  # EDCD=1 without CART=ED: the launcher carries the page-7 program (the 16MB-PCB cart), which is
  # NOT the EverDrive's - its own name, so it can never overwrite the EverDrive build's saves
  EDCD_32X="EDCD_DOOM_PAGE7${ROMMAPS:+_ROMMAPS}.32X"
fi
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
# the first of these files that exists, in the order given (ls would sort them)
first_of() { for f in "$@"; do [ -f "$f" ] && { echo "$f"; return; }; done; }
for G in sigil sigil2; do
  # SIGIL and SIGIL II are on their own disc (MUSIC=sigil, with their own CD audio); the DOOM
  # disc leaves them off (WITHSIGIL=1 puts them back, with the streamed SPCM music)
  [ "$MUSIC" = sigil ] || [ -n "${WITHSIGIL:-}" ] || continue
  if [ $G = sigil ]; then PW=sigil.wad; PIC=sigil; OUTW=SIGIL.WAD; CDT=1
  else                    PW=sigil2.wad; PIC=Sigil2; OUTW=SIGIL_II.WAD; CDT=12; fi
  SMUS="--music spcm"; [ "$MUSIC" = sigil ] && SMUS="--music cd --cdtrack $CDT"
  [ -f "$DATA/sigil/$PW" ] && [ -f "$DATA/doom.wad" ] || continue
  # the pictures: the title <name>.jpg, else <name>_1.jpg, .png, the .webp from the SIGIL download
  # (the first that exists); the tally / loading background of both: art/sigil-wallpaper.jpg (in
  # the repository); SIGILPIC=<file> another picture for both (lump:SIGILINT / lump:SIGILIN2: a WAD's
  # own art). SIGIL II's lion-head switch (SW1LION / SW2LION: E6M8's start pillar) shows the goat
  # from that picture (its middle strip); SIGILPILLAR=0 keeps the lion
  PIC="$(first_of "$DATA/sigil/$PIC.jpg" "$DATA/sigil/${PIC}_1.jpg" "$DATA/sigil/$PIC.png" "$DATA/sigil/$PIC.webp")"
  WALL="$HERE/art/sigil-wallpaper.jpg"
  TEXIMG=""; [ $G = sigil2 ] && [ "${SIGILPILLAR:-1}" != 0 ] \
    && TEXIMG="--tex-image SW1LION,SW2LION=$HERE/art/sigil-wallpaper.jpg@0.288,0.05,0.71,0.888"
  [ -n "${SIGILPIC:-}" ] && WALL="$SIGILPIC"
  echo "==> $OUTW (from data/sigil/$PW${ROMMAPS:+; ROM maps of $ROMMAPS})"
  ROMOPT=""; [ -n "$ROMMAPS" ] && ROMOPT="--rom-maps $HERE/build/rom_$G.wad --rom ${ROMMAPS// /,} --rom-budget ${ROMBUDGET:-64}${ROMBUDGETS:+ --rom-budgets ${ROMBUDGETS// /,}}"
  python3 "$HERE/tools/make_game.py" --game $G --pc "$DATA/doom.wad" "$DATA/sigil/$PW" --base "$DATA/doom32xf.wad" \
          --fusion "$DATA/fusion" --title "$PIC" --interpic "$WALL" $TEXIMG $SMUS $ROMOPT \
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
# CART4=1: the DOOM disc for the 4 MB RAM cart too (README "Building", 1b): textures and flats no game
# uses stubbed, 13 walls in 4-bit (16 colours), so the game ends below the cart's save area
if [ -n "${CART4:-}" ] && [ -z "$ROMMAPS" ]; then
  echo "==> the IWAD for the 4 MB cart (tools/make_cart4.py)"
  python3 "$HERE/tools/make_cart4.py" --iwad "$DATA/doom32xf.wad" --disc $(ls "$DISC"/*.WAD) \
          --out "$HERE/build/cart4_iwad.wad" > "$HERE/build/cart4_log.txt" \
    || { tail -5 "$HERE/build/cart4_log.txt"; echo "*** 4 MB IWAD failed"; exit 1; }
  cat "$HERE/build/cart4_log.txt"
  IWAD="$HERE/build/cart4_iwad.wad"
fi
echo "==> preload (the WADs kept in the 16 MB cart, pages 2-6)"
python3 "$HERE/tools/make_preload.py" plan "$DISC" "$HERE/build/preload.json" \
        "$HERE/build/cd32x_preload.h" "$HERE/cd32x/subcpu/preload_names.h"
echo "==> game (DOOM CD32X Fusion v3.0, CD32X=1${FIRE:+, with the title fire})"
DRAWDIST="${DRAWDIST:-}" ROMMAPS="$ROMMAPS" IWAD="$IWAD" CDONLY="$CDONLY" PRELOAD_H="$HERE/build/cd32x_preload.h" bash "$HERE/tools/build_game.sh" "$HERE/build/D32XR_CD32X.32x" CD32X=1 $GAME_ED
PREP_MODE1=""; if [ "${EDCD:-0}" = 1 ]; then PREP_MODE1="--mode1"; fi   # MODE1-1 (EDCD=1, below): the RAM jump table too
python3 "$HERE/tools/prep_openlara_cd.py" $PREP_MODE1 "$HERE/build/D32XR_CD32X.32x" "$ROMS/D32XR.32X"
# the ROM map disc (SIGIL): cut to its used length, so it also runs on the 4 MB RAM cart beside
# the save area when it fits (tools/fit_4mb.py)
{ [ -n "$ROMMAPS" ] || [ -n "${CART4:-}" ]; } && python3 "$HERE/tools/fit_4mb.py" "$ROMS/D32XR.32X" "$IWAD"
python3 "$HERE/tools/make_preload.py" loader "$HERE/build/preload.json" "$ROMS/D32XR.32X" "$HERE/cd32x/sh2/preload.h"
echo "==> loading screen"
# --ed: "LOADING GAME" instead of "FIRST TIME: COPYING ..." - the EverDrive's PSRAM has no battery and
# its menu wipes banks 0-29, so every boot is the first one (MicroNut99, 26 Oct 2026)
SPLASH_ED=""; [ "$CART" = ED ] && SPLASH_ED="--ed"
if [ -f "$DATA/splash.png" ]; then python3 "$HERE/tools/make_splash.py" $SPLASH_ED "$DATA/splash.png" "$ROMS/IMAGE.RAW"
else                               python3 "$HERE/tools/make_splash.py" $SPLASH_ED - "$ROMS/IMAGE.RAW"; fi
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

# EDCD=1 (MODE1-1, CD32X BootCamp docs/12): EDCD_DOOM.32X, made by the BootCamp's edboot/build_edcd.sh
# around this disc's Sub-CPU program built a second time for the cartridge boot (MODE1=1 M1PAGE=1, in a
# copy of cd32x/subcpu: the disc keeps the normal program)
if [ "${EDCD:-0}" = 1 ]; then
  BC="${BOOTCAMP:-$HERE/../CD32X-BootCamp}"
  [ -f "$BC/edboot/build_edcd.sh" ] || { echo "*** EDCD=1 needs the CD32X BootCamp next to this folder (or BOOTCAMP=<folder>): not at $BC"; exit 1; }
  echo "==> $EDCD_32X: the disc started from the EverDrive PRO (cartridge boot)"
  T=$(mktemp -d); mkdir -p "$T/subcpu/ROMS" "$T/sh2"
  find "$HERE/cd32x/subcpu" -maxdepth 1 -type f -exec cp {} "$T/subcpu/" \;
  cp "$HERE/cd32x/sh2/CDLOADER.32x" "$T/sh2/"
  ( cd "$T/subcpu" && make clean > /dev/null && make CDROMPlayer.bin MODE1=1 M1CTRL0=0x8000 M1PAGE=1 $EDSAVE_M1 CART_DEFS="-DCART_PAGED$EDSAVE_DEFS" GAME_DEFS="-DD32XR_CD=$PAGE" > "$T/mode1.log" 2>&1 ) \
    || { tail -20 "$T/mode1.log"; echo "*** the MODE1 Sub-CPU program did not build"; exit 1; }
  echo "    MODE1 program: M1PAGE=1 ${EDSAVE_M1:-(no M1SAVE)} CART_DEFS=\"-DCART_PAGED$EDSAVE_DEFS\"${EDCD_SAVE:+, EDCD_SAVE=$EDCD_SAVE (the RA header)}"
  bash "$BC/edboot/build_edcd.sh" "$T/subcpu/CDROMPlayer.bin" "$HERE/cd32x/sh2/CDLOADER.32x" "$HERE/cd32x/subcpu/$EDCD_32X"
  rm -rf "$T"
  echo "==> $EDCD_32X: $HERE/cd32x/subcpu/$EDCD_32X - copy it to the EverDrive's SD card and start it from the menu"
  echo "    with the disc above in the Sega CD (not \"Run Mega-CD\")"
fi
