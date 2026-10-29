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
# pauses in the wait loops of the two SH2s, both discs (README "Frame rate"; doomdef.h CD32X_PAUSE;
# off: NOIDLE=1; only with CD32X=1, so the plain Fusion build stays the release's)
case " $* " in *" CD32X=1 "*) [ -z "${NOIDLE:-}" ] && sed -i '1i #define CD32X_IDLE 1' "$B/doomdef.h" ;; esac
# BRAMSAVE=1 (build.sh): the save as a file in the Sega CD's backup RAM instead of the cart's piece 11
# (marshw.c Mars_WriteSRAM, src-md/crt0.s read_sram / write_sram, src-md/scd.c, src-md/cd/crt.s and s_main.c)
if [ -n "${BRAMSAVE:-}" ]; then
  sed -i '1i #define CD32X_BRAMSAVE 1' "$B/marshw.c" "$B/src-md/scd.c" "$B/src-md/cd/s_main.c"
  sed -i '1i .equ CD32X_BRAMSAVE, 1' "$B/src-md/crt0.s" "$B/src-md/cd/crt.s"
fi
# PAIN=1 (build.sh): the Pain Elemental, from D32XR (viciious/d32xr 23-25 Oct 2026): info.c / info.h, p_enemy.c,
# sounds.c / sounds.h, f_main.c (the cast); its sprites and sounds come from tools/make_pain.py
[ -n "${PAIN:-}" ] && sed -i '1i #define CD32X_PAIN 1' "$B/info.h" "$B/info.c" "$B/sounds.h" "$B/sounds.c" "$B/p_enemy.c" "$B/f_main.c"
# PLUTEX=1 (build.sh): Plutonia's pictures written into the IWAD's cart block when a map loads (p_setup.c,
# w_wad.c, marshw.c Mars_CartWrite, src-md/crt0.s cart_write: the 68000's command 16)
if [ -n "${PLUTEX:-}" ]; then
  sed -i '1i #define CD32X_PLUTEX 1' "$B/doomdef.h" "$B/marshw.c"
  sed -i '1i .equ CD32X_PLUTEX, 1' "$B/src-md/crt0.s"
fi
# CARTCD_ED=1 (build.sh CARTCD=1 PLUTEX=1): the cartridge for the Mega EverDrive PRO's SSF mode ("SEGA SSF",
# its write bit for PLUTEX, the save in its save bank: crt0.s, src-md/crt0.s)
[ -n "${CARTCD_ED:-}" ] && sed -i '1i .equ CARTCD_ED, 1' "$B/crt0.s" "$B/src-md/crt0.s"
# CARTCD_EDX=1 (build.sh CARTCD=1 PLUTEX=1 EDX=1): that cartridge for the Mega EverDrive X3 / X5 / X7 instead -
# its save in the upper 256 KB of bank 31 (their battery SRAM), CTRL0's X bit (32X mode) in every write to it
# (crt0.s, src-md/crt0.s, src-md/everdrive.c)
if [ -n "${CARTCD_EDX:-}" ]; then
  sed -i '1i .equ CARTCD_EDX, 1' "$B/crt0.s" "$B/src-md/crt0.s"
  sed -i '1i #define CARTCD_EDX 1' "$B/src-md/everdrive.c"
fi
# CARTCD=1 PLUTEX=1 (build.sh): the 32X+CD cartridge reads up to 64 extra lumps per map, as the CD32X build
# (p_setup.c MAX_AUX_TEXTURES; the cartridge build's 32 is enough for the plain PLUTONIA.WAD - 21 at most -,
# not for PLUTEX's, whose planner allows 64): CD32X_AUX64
[ -n "${CARTCD:-}" ] && [ -n "${PLUTEX:-}" ] && sed -i '1i #define CD32X_AUX64 1' "$B/p_setup.c"
# DRAWDIST=far: the farther draw distance (r_phase1.c)
[ "${DRAWDIST:-}" = far ] && sed -i '1i #define CD32X_DRAWDIST_FAR 1' "$B/r_phase1.c"
# PRELOAD_H: the 68000's table of the WADs kept in the 16 MB cart (tools/make_preload.py)
[ -n "${PRELOAD_H:-}" ] && cp "$PRELOAD_H" "$B/src-md/cd32x_preload.h"
# CDONLY=1 (build.sh MUSIC=sigil): the SIGIL CD audio disc - only cdMusic games play CD audio, the
# music option CD means FM for the others (marssound.c, CD32X_CDONLY)
[ -n "${CDONLY:-}" ] && sed -i '1i #define CD32X_CDONLY 1' "$B/marssound.c" "$B/g_game.c"
# TEST_GOD=1: emulator testing only - the player takes no damage
[ -n "${TEST_GOD:-}" ] && sed -i 's|^\tif ( !(target->flags \& MF_SHOOTABLE) )$|\tif (target->player) return;\n&|' "$B/p_inter.c"
# TEST_STATS=1: emulator testing only - r_main.c keeps the renderer's peak use against its limits (r_stat)
[ -n "${TEST_STATS:-}" ] && sed -i '1i #define R_STATS 1' "$B/r_main.c" && sed -i '1i #define R_STATS_STACK 1' "$B/marsonly.c"
# TEST_DEBUG=1: emulator testing only - D32XR's timing screen on from the start (fps, game logic, BSP,
# walls, planes, sprites, render, draw, total in ms; normally Options + MODE)
[ -n "${TEST_DEBUG:-}" ] && sed -i 's/^VINT \tdebugmode = DEBUGMODE_NONE;/VINT \tdebugmode = DEBUGMODE_ALLCOUNT;/' "$B/marsnew.c"
# TEST_EXIT=1: emulator testing only - every level ends by itself after about 300 frames (the
# intermission, the next map's loading screen)
[ -n "${TEST_EXIT:-}" ] && sed -i 's|^\tgameaction = ga_nothing;$|&\n\t{ static int test_exit; if (++test_exit > 300) { test_exit = 0; G_ExitLevel(); } }|' "$B/p_tick.c"
# TEST_WARP=n: emulator testing only - a game the title starts by itself (PLUTONIA, the SIGILs) starts at MAPn
# (RunTitle's startmap; with TEST_EXIT: a run through the maps from there)
[ -n "${TEST_WARP:-}" ] && sed -i "s/^\tstartmap = 1;\$/\tstartmap = $TEST_WARP;/" "$B/d_main.c"
# TEST_SPECIAL=1: emulator testing only - the "unknown special" stop says the number first, and the sector
[ -n "${TEST_SPECIAL:-}" ] && sed -i 's|"unknown special %i",sector->special);|"%i: unknown special, sector %i", sector->special, (int)(sector - sectors));|' "$B/p_spec.c"
# TEST_WALLS=n TEST_PLANES=n: emulator testing only - other renderer limits (MAXWALLCMDS 165, MAXVISPLANES 32)
[ -n "${TEST_WALLS:-}" ] && sed -i "s/^#define\tMAXWALLCMDS\t\t165/#define\tMAXWALLCMDS\t\t$TEST_WALLS/" "$B/r_local.h"
[ -n "${TEST_PLANES:-}" ] && sed -i "s/^#define\tMAXVISPLANES\t32/#define\tMAXVISPLANES\t$TEST_PLANES/" "$B/r_local.h"
cd "$B"
OPTS=""; [ -n "${FIRE:-}" ] && OPTS="ENABLE_FIRE_ANIMATION=1 FIRE_TIME=470"
env $OPTS "$@" \
  make -j8 release ROOTDIR="$DK" GENDEV="$DK" TITLE="${TITLE:-Doom CD32X Fusion}" VERSION="${VERSION:-3.0}" \
  ${CARTCD_ED:+"MAPPER=SEGA SSF"} > build.log 2>&1 \
  || { grep -n -i -B2 -A2 " error\|undefined ref" build.log | head -40; echo "*** game build failed (build/d32xr/build.log)"; exit 1; }
cp D32XR.32x "$OUT"
echo "game: $OUT ($(stat -c %s "$OUT") bytes)"
