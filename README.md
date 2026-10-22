# D32XR CD32X: DOOM CD32X Fusion from the CD

DOOM CD32X Fusion v3.0 runs on **Sega CD + 32X + the 16 MB RAM cart**, booted from the disc. No flash cart is needed.

1. The disc boots.
2. The loader copies the game and the WADs into the RAM cart.
3. D32XR starts from the cart, with all of Fusion's features:
   - the FMV
   - the game select menu
   - the WADs, the music and the sound effects through the Sega CD

The game is DOOM CD32X Fusion v3.0, built from the D32XR team's source: viciious/d32xr, tag `fusion_v3.0`, the same commit as v3.5. Built without the CD32X changes, it comes out byte for byte your Fusion ROM; only the build date in the header differs. The CD32X build also brings back Resurrection's title fire and fixes the melt bug that came with it (see below).

**R2 status:** in ares, the disc boots, fills the cart (first boot ~5 min), checks it at later boots (game select menu after ~50 s), reads the preloaded WADs from the cart (checked with a disc whose DOOM.WAD title lump was damaged: the title came out right), shows the fire on Resurrection's title only, and melts cleanly into the first demo. Not yet tested on the console.

## What you need

- Sega CD + 32X.
- The **16 MB RAM cart** (the 16MB-PCB-CD32X board).
  - **8 MB:** runs, without the preload (every WAD comes from the CD).
  - **4 MB:** refused. The game's 4 MB would overwrite the shared save area.
- Your **DOOM CD32X Fusion v3.0 ROM** (`DCD32XF_V3.32x`). The game's data (its IWAD) is taken from it.
- Your **DOOM CD32X Fusion disc image** (`DCD32XF_V3.bin`). Its files (WADs, music, video) go onto the new disc.

These are never committed.

## The cart

| Page (2 MB) | Holds |
|---|---|
| 0 | the game, first 2 MB (window 0) |
| 1 | the shared save area and the other titles' data. Untouched, except Doom's saves in **piece 11** and the loader's record in **piece 15** (test scratch) |
| 2-6 | **the preload**: SOUNDS.WAD, DOOM.WAD, DOOM_II.WAD, RESURRECTION.WAD (10.1 MB of 10.3 MB) |
| 7 | the game, second 2 MB (window 1 while the game runs) |

**What's not in the cart:**
- TNT_MINI.WAD (2.5 MB) and MAPDEV.WAD (4.8 MB): no room left. They are read from the CD as before.
- The video and the VGM music files: the Sega CD streams those itself.

**The order** is `PRELOAD_ORDER` in `tools/make_preload.py`. Each file is taken if it still fits.

**How the game reads a preloaded WAD** (`d32xr/src-md/scd_fs.c`):
- It reads from the cart instead of the CD: same bytes, no seeking.
- The 68000 does the copy. It maps the page into window 1 and parks both SH2s meanwhile, as D32XR does for save RAM. Then it maps page 7 back.

## Every boot

1. **Board probe.** Markers go into save piece 15 of pages 1, 2 and 6, then are read back. The result is 4, 8 or 16 MB.
2. **Checks.** The loader computes the checksums of the game and of every preloaded WAD in the cart, and compares them with the ones the build computed.
3. **Copying, only if needed.** If anything doesn't match, the loading screen says **FIRST TIME: COPYING DOOM INTO THE RAM CART** and copies those files from the disc. That happens the first time, or after another title used those pages.
   - Hold **A + B + C** at power-on to copy everything again.
4. **Record.** Save piece 15 of page 1 gets the record `D32XR PRELOAD OK`. Only then does the game read the WADs from the cart.

The loading screen is your DOOM logo (`data/splash.png`) with a gold bar.

## Resurrection's title fire (on; `FIRE=0` leaves it out)

Resurrection v3.5 has the burning title. In this build **only RESURRECTION** gets it; DOOM, DOOM II and TNT MINI keep their titles as Fusion shows them.

**Why DOOM CD32X Fusion has no fire:**

1. **It no longer fit the 4 MB ROM.** The fire is a build option (`ENABLE_FIRE_ANIMATION`). Fusion's IWAD is 3,970,535 bytes. With the fire code, the program grows from 0x36000 to 0x36C00, so the ROM comes to 0x4001E7: **487 bytes more than 4 MB**. Fusion was built without the option, so the program stayed at 0x36000 and the ROM ended at 0x3FF5E7.
2. **The Fusion WADs switch it off.** RESURRECTION.WAD's `DMAPINFO` sets `stopFireTime = 0` (no fire), even in a build with the option. Resurrection v3.5's IWAD sets `stopFireTime = 470`.

**The fix (CD32X build):**
- **Room.** The MegaSD and EverDrive code (`src-md/megasd.c`, `everdrive.c`) is no longer linked. It is never used on the RAM cart, and three no-op stubs stand in for its CD music calls. The program then rounds down to 0x36800, and the ROM with the fire ends at 0x3FFDE7, with 536 bytes to spare.
- **Fire time, Resurrection only** (`m_fire.c`, `FIRE_TIME=470`). When the game picked in the select menu is `RESURRECTION.WAD` and its `DMAPINFO` says `stopFireTime = 0`, the fire burns 470 tics, as in v3.5. The other games' title pictures are not made for the fire: DOOM's showed it as a strip across the top.
- **Title time, Resurrection only** (`m_fire.c`). The title waits for a count of drawn frames (`titleTime`). Fusion's RESURRECTION.WAD says 13000, which is made for the fast title without the fire. With the fire drawn every frame, the title stayed up for about 4 minutes before the credits and the demo. With the fire, the build uses v3.5's 900.

The WADs are not changed.

## The melt bug: the "one inch mess" at the top of the first melt

**What you see:** with the title fire compiled in, the first melt into the demo (from the credits screen) starts with a band of coloured garbage about 16 lines high across the top of the screen. The band moves down as the jagged edge of the melt, instead of the melt's clean black edge. It was already on the credits screen for a moment before the melt began.

**The cause** (`d32xr/d_main.c`, `RunMenu`):
1. D32XR's 68000 uses the start of the 32X frame buffer as its transfer buffer for everything it reads from the CD (`read_cd_file` in `src-md/crt0.s` copies to `MARS_FRAMEBUFFER`). Every CD read overwrites the top lines of the picture on screen.
2. The game hides this by backing the screen up on the Mega Drive side before a CD read (`I_StoreScreenCopy`) and putting it back afterwards (`I_RestoreScreenCopy`).
3. Between the title and the first demo, `RunMenu` calls `M_Start`, which loads the menu's graphics from the CD. Its backup and restore were wrapped in `#ifndef ENABLE_FIRE_ANIMATION`, so **every build with the fire skipped them**.
4. On a cartridge build with the fire (Resurrection v3.5: `DISABLE_CDFS`, nothing comes from the CD) that costs nothing. On a CD build with the fire, the menu's CD data was left on the top of the credits screen. The melt into the demo captures that screen as its starting picture, so the garbage became the melt's leading edge.

That is why Resurrection v3.5 (fire, no CD) and the Fusion release (CD, no fire) both look right: the bug needs **fire + CD** together.

**The fix:** the backup and restore around `M_Start` are kept whenever the CD file system is on:

```c
#if !defined(ENABLE_FIRE_ANIMATION) || !defined(DISABLE_CDFS)
	I_StoreScreenCopy();
#endif
	M_Start();
#if !defined(ENABLE_FIRE_ANIMATION) || !defined(DISABLE_CDFS)
	I_RestoreScreenCopy();
#endif
```

**Checked in ares**, frame by frame through the credits and the first melt:
- DOOM: clean credits, clean melt.
- RESURRECTION: fire, then title, credits, then a clean melt into the demo.
- The untouched Resurrection v3.5 ROM, for comparison: clean.
- The build before the fix: the band.

## More games: PLUTONIA, SIGIL, SIGIL II

`build.sh` adds three games to the select menu when your PC WADs are in `data/` (`tools/make_game.py` converts them):

| Game | Your files | Maps on the disc |
|---|---|---|
| **PLUTONIA** | `data/plutonia.wad`, optional `data/hires/*.pk3` (the 1K texture pack) | MAP01-27, MAP30-32 (MAP28 and MAP29 left out) |
| **SIGIL** | `data/doom.wad`, `data/sigil/sigil.wad`, `sigil.webp`, `sigil-wallpaper.jpg` | E5M1, E5M2, E5M3, E5M8 |
| **SIGIL II** | `data/doom.wad`, `data/sigil/sigil2.wad`, `Sigil2.webp`, `sigil-wallpaper.jpg` | E6M2, E6M3, E6M9 |

**The pictures:**
- PLUTONIA: its own TITLEPIC, INTERPIC and BOSSBACK.
- SIGIL: title `sigil.jpg` (else `sigil.webp`). SIGIL II: title `Sigil2_1.jpg` (made at 320 x 224, used as it is; else `Sigil2.jpg` / `Sigil2.webp`). The whole logo is shrunk to fit the screen.
- Both SIGILs: `sigil-wallpaper_1.jpg` (made at 320 x 224, used as it is; else `sigil-wallpaper.jpg`) behind the kill / item / secret tally between levels (the `INTERPIC`).

**The 32X's RAM is the limit.** A level and its textures share about 177 KB of the 32X's memory. This figure was measured in ares on all 32 Plutonia maps: what the texture cache had left, plus the level's own data.
- A map whose level data alone is bigger than that cannot load (`Z_Malloc failed`), so it is left out. The episode's "next" goes on to the next map that fits.
  - PLUTONIA: MAP28 and MAP29 failed in ares.
  - SIGIL: E5M4-7 and E5M9 are 190-390 KB.
  - SIGIL II: all but E6M2, E6M3 and E6M9 are 245-350 KB.
- **Textures:** each map gets what is left over as a budget for its own textures, flats and sky (`tools/plutonia_budgets.txt` for Plutonia, measured; the same measurement as a formula for the SIGILs).
  - What is seen most per byte goes in first: flats by their floor area, walls by their length.
  - A texture that does not fit is drawn as the base game's closest-looking texture of the same size (the build report lists every one).
  - The SIGIL maps on the disc are so big that almost nothing is left for their own textures, so most of their walls show base-game look-alikes.
- **The 1K texture pack** is new art drawn for those names, not an upscale of the originals. Its pictures are shrunk to the textures' real sizes (averaged in linear light, then matched to the palette in CIELAB) wherever Plutonia uses a name it has.

## SIGIL music: CD audio

SIGIL and SIGIL II play their music from the disc's **CD audio tracks**. The other games keep Fusion's FM (VGM) music.

| Disc track | |
|---|---|
| 2-12 | SIGIL: title, E5M1-E5M9, intermission |
| 13-23 | SIGIL II: title, E6M1-E6M9, intermission |

- **SIGIL:** cut from `SIGIL-DOOM-OPL-Soundtrack.mp4` (James Paddock's MIDIs played on an OPL chip). The cuts sit at the video's caption changes, in the silence or fade between two songs.
- **SIGIL II:** that video only has SIGIL, so SIGIL II's MIDIs are played through an OPL3 emulator (libADLMIDI, Nuked OPL3) with DOOM's own DMX instruments, the same kind of sound as the video. Each track is one pass of the song, then 9.6 s of its loop fading out, like the video's. The level is raised 4.3 dB to match the video: that gap was measured by rendering SIGIL's MIDIs the same way.
- `tools/make_sigil_cdda.sh <the .mp4> <sigil2.wad>` makes `data/sigil_cdda/Track02-23.wav`, and `build.sh` puts them on the disc (about 61 minutes, about 640 MB).

**In the game** (`d32xr/marssound.c`, `d_mapinfo.c`, under `CD32X`):
- A WAD whose DMAPINFO `gameinfo` says `cdMusic = 1` plays the CD track that its `cdTrack` / `titleCdTrack` / `intermissionCdTrack` fields name, whatever the music option says.
- Turning the music off still turns it off.
- **The drive cannot play CD audio and read data at once:** every read (a level's lumps, the intermission's pictures) stops the track. The game counts its disc reads (`marshw.c`, `mars_cd_reads`), and half a second after the last one it starts the level's or the intermission's track again (`S_UpdateSounds`).
- The other games never play CD audio, because the disc's tracks are SIGIL's. For them the CD music option means FM.

## Building

**Requirements** (WSL / Linux):
- The **D32XR team's devkit** `chillys-sega-devkit-20220418` (viciious/32XDK releases), at `/opt/d32xr-dk/opt/toolchains/sega`, or set `GENDEV=<folder>`.
- **Chilly Willy's toolchain** in `/opt/toolchains/sega`, for the boot stack.
- `genisoimage`, and Python 3 with Pillow.

**Your files** go in the project's `data/` folder:

| File | Use |
|---|---|
| `data/DCD32XF_V3.32x` | your Fusion ROM: the game's data (IWAD) |
| `data/DCD32XF_V3.bin` | your Fusion disc image: its WADs, music and video (copied once into `data/fusion/`) |
| `data/splash.png` | the loading screen picture (the DOOM logo) |
| `data/plutonia.wad`, `data/hires/*.pk3` | PLUTONIA (optional) |
| `data/doom.wad`, `data/sigil/` (sigil.wad, sigil2.wad, sigil.webp, Sigil2.webp, sigil-wallpaper.jpg) | SIGIL, SIGIL II (optional) |
| `data/sigil_cdda/Track02-23.wav` | SIGIL's music (`tools/make_sigil_cdda.sh`); without them, one silent track |

**Build:**

```
cd /mnt/s/KoboPort/sega-toolchain-12.1/sega/D32XR_CD32X && \
bash build.sh 2>&1 | tee build_log.txt
```

**The disc:** `discs/D32XR_CD32X_R2/D32XR_CD32X_R2.cue` (with its `.bin`), in the project folder. Burn the `.cue`.

**Options:**
- `FIRE=0`: Resurrection's title as in the Fusion release, with no fire.
- `NAME=<name>`: the disc's name.

## What changed in D32XR (all under `CD32X` or the build options)

| Where | Change |
|---|---|
| `d32xr/src-md/scd*.c`, `vgm.c` | Mega CD mode 2 addresses: BIOS `0x000000`, Program RAM window `0x020000`, Word RAM `0x200000`. D32XR restarts the Sega CD with its own Sub-CPU program, as on a cartridge. |
| `d32xr/src-md/crt0.s` | After the work RAM clear, `_start` writes the Sega CD BIOS's RAM interrupt jumps again (`0xFFFD06` / `0xFFFD0C` / `0xFFFD12`, plus `0xA12006`), with the stack below them. |
| `d32xr/src-md/crt0.s` | Save RAM → the cart's save piece 11. `cd32x_cart_copy`: the reads from cart pages 2-6. |
| `d32xr/src-md/scd_fs.c` | The preload: preloaded WADs are read from the cart. |
| `d32xr/src-md/main.c`, `Makefile` | No MegaSD / EverDrive code. |
| `d32xr/m_fire.c`, `Makefile` | `FIRE_TIME`: the fire and v3.5's title time for Resurrection only (see the title fire). |
| `d32xr/d_main.c` | The melt bug: the screen backup around `M_Start` kept with the CD (see the melt bug). |
| `d32xr/marssound.c`, `d_mapinfo.*` | `cdMusic`: CD audio for SIGIL / SIGIL II only (see SIGIL music). |
| `d32xr/p_setup.c` | `MAX_AUX_TEXTURES` 64 (from 32): more of a map's own textures. |

**The boot stack** (`cd32x/`) is Hurrican CD32X P2a2's, with these changes:
- **The loader:** D32XR mode, the loading screen and its two text lines, the board probe, the checksums, the preload copy and the record.
- **The Sub-CPU:**
  - `D32XR.32X` is file 20.
  - Files 300+ are the preload.
  - CMD 46 / 47 wrap in the 4 MB, for a WAD that goes on into the next page.
  - CMD 60 leaves window 1 on page 7.
