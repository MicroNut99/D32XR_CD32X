# D32XR CD32X: DOOM CD32X Fusion from the CD

DOOM CD32X Fusion v3.0 on **Sega CD + 32X + the 8 / 16 MB RAM cart**, boots all from a CD only.

1. The disc boots, and the loader copies the game (and, on the 16 MB cart, the main WADs) into the RAM cart.
2. D32XR starts from the cart with all of Fusion's own features (the FMV intro, the game select menu, the WADs, music and sound effects through the Sega CD) and the additions below.

The game is DOOM CD32X Fusion v3.0, built from the D32XR team's source (viciious/d32xr, tag `fusion_v3.0`, the same commit as v3.5). Built without the CD32X changes, it comes out byte for byte the Fusion ROM; only the build date in the header differs.

## What it is, and what it isn't

**It is:**
- Fusion v3.0's engine and its own WADs (DOOM, DOOM II, Resurrection, TNT MINI), unchanged, running from the CD + RAM cart instead of a flash cart.
- Three more games converted from your PC WADs at build time: **PLUTONIA**, **SIGIL** and **SIGIL II**.
- Two disc layouts from one build script (below): Fusion's **IDKFA** CD soundtrack, or SIGIL's music as CD audio.
- A handful of fixes and additions: Resurrection's title fire back (and the melt bug it brought, fixed), CD music that comes back after the game reads the disc, quieter FMV sound, a cleaner loading screen.

**It isn't:**
- A new port or a new engine: it is D32XR. Everything the 32X's memory and speed limit in Fusion is limited here too.
- The PC versions of PLUTONIA and SIGIL: their maps run on the 32X's 256 KB of working RAM, so the biggest maps are left out and many textures are stand-ins (see "What's missing").
- A disc with game data in it: you build it from your own files (`data/`, never committed).
- Tested on the console yet: everything was run in ares (with the 16 MB board emulated).

## The two discs

| | **IDKFA disc** (default) | **SIGIL disc** (`MUSIC=sigil`) |
|---|---|---|
| Games in the select menu | DOOM, DOOM II, PLUTONIA, RESURRECTION, SIGIL, SIGIL II, TNT MINI | the same |
| CD audio tracks | **2-26: Fusion's IDKFA soundtrack**, taken byte for byte from your IDKFA disc image | **2-23: SIGIL's and SIGIL II's songs** (11 each) |
| DOOM, RESURRECTION music | FM (Fusion's VGM) or, with the music option on CD, the IDKFA tracks | FM (the CD option means FM here: the CD tracks are SIGIL's) |
| DOOM II, PLUTONIA music | FM, or with CD the IDKFA tracks: these games have no tracks of their own on that disc, so their track numbers wrap onto DOOM's songs (as on Fusion's own IDKFA disc) | FM |
| TNT MINI music | FM, or with CD the IDKFA tracks by its song numbers (it has no tracks of its own either) | FM |
| SIGIL, SIGIL II music | **streamed from the data track** (Fusion's SPCM: 8-bit, 21.4 kHz mono), whatever the music option (off silences it) | **CD audio**, whatever the music option (off silences it) |
| Left off the disc | `MAPDEV.WAD` (Fusion's map-testing file; the menu hides it) and the loose `VGM_*` folders (spare copies of music already inside the WADs) | nothing |
| Size | about 79:46 of an 80:00 CD (estimated from the IDKFA cue; the build prints the real figure and warns above 80:00) | 64:52 |

Both are **mixed-mode** discs: one `.bin` (data track 1, then the audio tracks, no gaps between them, like the IDKFA disc's cue) and its `.cue`. The audio tracks can be replaced later without touching the data.

**Plutonia's CD tracks:** each Plutonia map is given the CD track of the DOOM II map with the same number (worked out from Fusion's DOOM_II.WAD exactly as the game does), its title / intermission / victory / end too.

## What's included

| Game | Maps | Notes |
|---|---|---|
| DOOM | Fusion's | unchanged |
| DOOM II | Fusion's | unchanged |
| RESURRECTION | Fusion's | **the burning title** of Resurrection v3.5 (only this game; `FIRE=0` leaves it out) |
| TNT MINI | Fusion's | unchanged |
| PLUTONIA | MAP01-27, MAP30-32 | from your `plutonia.wad`; textures from the 1K texture pack where it has them (shrunk to the real sizes); its own TITLEPIC, INTERPIC, BOSSBACK |
| SIGIL | E5M1, E5M2, E5M3, E5M8 | from your `doom.wad` + `sigil.wad`; title = your `sigil.jpg` (the whole logo fitted, flat dark red); tally screen = your `sigil-wallpaper_1.jpg` |
| SIGIL II | E6M2, E6M3, E6M9 | from `doom.wad` + `sigil2.wad`; title = your `Sigil2_1.jpg`; tally screen = `sigil-wallpaper_1.jpg` |

Also:
- **CD music in levels:** the drive cannot play CD audio and read data at once, so a level's or an intermission's CD track stopped for good when the game read the disc. Now the game counts its disc reads and, half a second after the last one, starts the track again (`marssound.c`, `S_UpdateSounds`). Seen in ares: the SIGIL disc plays E5M1's track through the level.
- **The FMV intro's sound** at half volume (-6 dB), at your request; otherwise the same decoder and data as Fusion's.
- **The loading screen:** your DOOM logo; when the cart has to be filled, the text **FIRST TIME: COPYING DOOM INTO THE RAM CART** and a gold bar that grows. Nothing else (no frame, no empty bar).
- **No red flash** as the loader hands over to the game (a leftover debug colour in the boot stack).
- The melt bug fixed (see below).
- Saves in the RAM cart's shared save area (piece 11), battery-backed.

## What's missing

- **SIGIL maps E5M4, E5M5, E5M6, E5M7, E5M9** and **SIGIL II maps E6M1, E6M4, E6M5, E6M6, E6M7, E6M8**: each map's level data alone (190-390 KB) is bigger than the 32X can hold (about 177 KB for a level and its textures together, measured in ares). Their music is on the SIGIL disc's CD tracks already, so they can be added if a way to fit them is found.
- **PLUTONIA MAP28 and MAP29:** the same reason (`Z_Malloc failed` in ares). The map before goes on to the next one that fits.
- **Textures:** a map's own textures share the memory left after its level data. What doesn't fit is drawn as the base game's closest-looking texture of the same size (the build report lists every one). The SIGIL maps are so big that almost all their own textures are stand-ins (lava falls and red rock show as wood and step textures). Skies: the map's own sky only when it fits, else the base game's (SIGIL: the red hell sky).
- **SIGIL's "real" soundtracks** (Buckethead for SIGIL, Thorr for SIGIL II) are not on the discs: the only SIGIL music supplied was the OPL soundtrack video, so its CD tracks and streamed songs sound like FM synth music. SIGIL II's songs are its MIDIs played through an OPL3 emulator with DOOM's instruments, the same kind of sound. Give the build other WAVs (`data/sigil_cdda/Track02-23.wav`) to change that.
- **No skill / level choice when PLUTONIA, SIGIL or SIGIL II start:** like Fusion's WADs without attract demos, the title goes straight into the first map on medium. Pick the skill and the level with Start, Game, New Game.
- **The preload** (16 MB cart) holds SOUNDS, DOOM, DOOM II and RESURRECTION. TNT MINI, PLUTONIA and the SIGILs are read from the CD (no room left in pages 2-6).
- **8 MB cart:** runs, without the preload. **4 MB cart:** refused (the game's 4 MB would overwrite the shared save area).
- **Black patches** in some outdoor spots (also in Plutonia MAP07): gaps the 32X engine leaves empty, as in Fusion.
- **FMV sound in ares** is rough on this disc and on Fusion's own disc alike (the same recording, measured): an emulator matter as far as can be told.
- **Console:** not run yet.

## What you need

- Sega CD + 32X, the **16 MB RAM cart** (the 16MB-PCB-CD32X board; 8 MB works without the preload).
- In the project's `data/` folder (never committed):

| File | Use |
|---|---|
| `data/DCD32XF_V3.32x` | your Fusion ROM: the game's data (IWAD) |
| `data/DCD32XF_V3.bin` | your Fusion disc image: its WADs, music and video (copied once into `data/fusion/`) |
| `data/splash.png` | the loading screen picture (the DOOM logo) |
| `data/plutonia.wad`, `data/hires/*.pk3` | PLUTONIA (optional; the 1K texture pack optional) |
| `data/doom.wad`, `data/sigil/sigil.wad`, `data/sigil/sigil2.wad` | SIGIL, SIGIL II (optional) |
| `data/sigil/sigil.jpg`, `Sigil2_1.jpg`, `sigil-wallpaper_1.jpg` | their title and tally pictures (else `sigil.webp`, `Sigil2.webp`, `sigil-wallpaper.jpg`) |
| `data/sigil_cdda/Track02-23.wav` | SIGIL's and SIGIL II's 22 songs: the SIGIL disc's CD tracks, and the source of the IDKFA disc's streamed songs (`tools/make_sigil_cdda.sh` makes them) |
| `DOOM CD32X FUSION V3 with IDKFA Soundtrack/*.cue` + `.bin` (project folder) | the IDKFA disc's CD audio (`IDKFA=<cue>` for another place), else `data/music/Track02.wav ...`, else one silent track |

## Building

**Requirements** (WSL / Linux):
- The **D32XR team's devkit** `chillys-sega-devkit-20220418` (viciious/32XDK releases), at `/opt/d32xr-dk/opt/toolchains/sega`, or set `GENDEV=<folder>`.
- **Chilly Willy's toolchain** in `/opt/toolchains/sega`, for the boot stack.
- `genisoimage`, Python 3 with NumPy and Pillow (`sudo apt install python3-numpy python3-pil genisoimage`). No SciPy.
- Only for `tools/make_sigil_cdda.sh`: ffmpeg, git, cmake, gcc / g++ (it builds libADLMIDI).

**The IDKFA disc:**

```
cd /mnt/s/KoboPort/sega-toolchain-12.1/sega/D32XR_CD32X
NAME=D32XR_CD32X_IDKFA bash build.sh 2>&1 | tee build_log.txt
```

**The SIGIL disc:**

```
cd /mnt/s/KoboPort/sega-toolchain-12.1/sega/D32XR_CD32X
MUSIC=sigil NAME=D32XR_CD32X_SIGIL bash build.sh 2>&1 | tee build_log.txt
```

Each takes about 5 minutes (converting PLUTONIA with the texture pack is the slow part). The disc is `discs/<NAME>/<NAME>.cue` with its `.bin`. Burn or load the `.cue`. The two discs build different game programs, so after switching discs the first boot copies the game into the cart again.

**Options:** `NAME=<name>` the disc's name; `MUSIC=sigil` the SIGIL disc; `FIRE=0` no title fire; `HIRES=0` PLUTONIA without the texture pack; `CUT="..."` the Fusion files left off (`CUT=""` keeps all); `IDKFA=<cue>` the IDKFA disc image; `PLUT_BUDGETS=<file>` Plutonia's texture budgets.

**The build's tools** (`tools/`):

| Tool | Does |
|---|---|
| `extract_iwad.py`, `extract_iso.py` | the IWAD out of your ROM, the files out of your Fusion disc image |
| `make_game.py` | PLUTONIA / SIGIL / SIGIL II: the maps, the donor textures within each map's RAM budget, the 1K pack, the pictures, DMAPINFO (music, CD tracks) |
| `make_spcm.py` | SIGIL's streamed songs (only those the WADs play) for the IDKFA disc |
| `extract_cue_audio.py` | the IDKFA disc's audio tracks, byte for byte |
| `make_sigil_cdda.sh`, `oplrender.c` | SIGIL's 22 songs as WAVs: cut from the OPL soundtrack video (SIGIL) and rendered through an OPL3 emulator (SIGIL II) |
| `make_preload.py`, `make_splash.py`, `build_game.sh` | the preload plan and checksums, the loading screen, the game build |
| `../cd32x/subcpu/make_mixed_cd2.py` | the mixed-mode `.bin` / `.cue` |

## The cart

| Page (2 MB) | Holds |
|---|---|
| 0 | the game, first 2 MB (window 0) |
| 1 | the shared save area and other titles' data. Untouched, except DOOM's saves in **piece 11** and the loader's record in **piece 15** (test scratch) |
| 2-6 | **the preload**: SOUNDS.WAD, DOOM.WAD, DOOM_II.WAD, RESURRECTION.WAD (10.1 MB of 10.3 MB) |
| 7 | the game, second 2 MB (window 1 while the game runs) |

**How the game reads a preloaded WAD** (`d32xr/src-md/scd_fs.c`):
- It reads from the cart instead of the CD: same bytes, no seeking.
- The 68000 does the copy. It maps the page into window 1 and parks both SH2s meanwhile, as D32XR does for save RAM. Then it maps page 7 back.

## Every boot

1. **Board probe.** Markers go into save piece 15 of pages 1, 2 and 6, then are read back: 4, 8 or 16 MB.
2. **Checks.** The loader computes the checksums of the game and of every preloaded WAD in the cart and compares them with the ones the build computed.
3. **Copying, only if needed.** If anything doesn't match (the first time, or after another title used those pages), the loading screen shows **FIRST TIME: COPYING DOOM INTO THE RAM CART** and the gold bar, and copies just those files. Hold **A + B + C** at power-on to copy everything again.
4. **Record.** Save piece 15 of page 1 gets `D32XR PRELOAD OK`. Only then does the game read the WADs from the cart.

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

## Music in detail

**CD audio** (`d32xr/marssound.c`, `marshw.c`, `d_mapinfo.*`, under `CD32X`):
- The music option works as in Fusion for the Fusion games: FM = their VGM music, CD = the disc's CD tracks (on the SIGIL disc, CD means FM for them: `CD32X_CDONLY`).
- A WAD whose DMAPINFO `gameinfo` says `cdMusic = 1` (SIGIL / SIGIL II on the SIGIL disc) plays the CD track its `cdTrack` / `titleCdTrack` / `intermissionCdTrack` fields name, whatever the option (off still silences it).
- A WAD that says `musicStream = 1` (SIGIL / SIGIL II on the IDKFA disc) plays its streamed PCM files (`spcmDirs`: `SIGIL/`, `SIGIL2/` on the data track) whatever the option.
- **The restart after reads:** the game counts the requests that make the drive read (`mars_cd_reads`); a looping CD track stopped by a read is started again 15 tics after the last one.

**SIGIL's songs:**
- **SIGIL:** cut from `SIGIL-DOOM-OPL-Soundtrack.mp4` (James Paddock's MIDIs played on an OPL chip) at the video's caption changes, in the silence or fade between two songs.
- **SIGIL II:** that video only has SIGIL, so SIGIL II's MIDIs are played through an OPL3 emulator (libADLMIDI, Nuked OPL3) with DOOM's DMX instruments: one pass, then 9.6 s of the loop fading out, like the video; +4.3 dB to match its level (measured on SIGIL's MIDIs rendered the same way).
- `tools/make_sigil_cdda.sh <the .mp4> <sigil2.wad>` makes `data/sigil_cdda/Track02-23.wav`.
- **On the IDKFA disc** they become Fusion's streamed format (`tools/make_spcm.py`: band-limited resampling to 21,396 Hz, one gain for all songs, dithered to 8 bits, mono; only the 11 songs the WADs play, 32.5 MB). Checked in ares: a 441 Hz test tone in place of the title song came out at the right pitch with no dropouts, and E5M1's song played straight through the level.

## What changed in D32XR (all under `CD32X` or the build options)

| Where | Change |
|---|---|
| `d32xr/src-md/scd*.c`, `vgm.c` | Mega CD mode 2 addresses: BIOS `0x000000`, Program RAM window `0x020000`, Word RAM `0x200000`. D32XR restarts the Sega CD with its own Sub-CPU program, as on a cartridge. |
| `d32xr/src-md/crt0.s` | After the work RAM clear, `_start` writes the Sega CD BIOS's RAM interrupt jumps again (`0xFFFD06` / `0xFFFD0C` / `0xFFFD12`, plus `0xA12006`), with the stack below them. |
| `d32xr/src-md/crt0.s` | Save RAM → the cart's save piece 11. `cd32x_cart_copy`: the reads from cart pages 2-6. |
| `d32xr/src-md/scd_fs.c` | The preload: preloaded WADs are read from the cart. |
| `d32xr/src-md/main.c`, `Makefile` | No MegaSD / EverDrive code. |
| `d32xr/m_fire.c`, `Makefile` | `FIRE_TIME`: the fire and v3.5's title time for Resurrection only. |
| `d32xr/d_main.c` | The melt bug: the screen backup around `M_Start` kept with the CD. |
| `d32xr/marssound.c`, `marshw.*`, `d_mapinfo.*` | `cdMusic`, `musicStream`, the CD track restart after disc reads, `CD32X_CDONLY` (set by `build_game.sh` for the SIGIL disc). |
| `d32xr/marsroq.c` | The FMV sound at half volume (-6 dB) around the PWM centre. |
| `d32xr/p_setup.c` | `MAX_AUX_TEXTURES` 64 (from 32): more of a map's own textures. |

## The boot stack

`cd32x/` is Hurrican CD32X P2a2's boot stack (Sub-CPU `main.c`, 68000 listener `hw_md.s`, SH2 loader `cdloader_sh2.c`), with no new command number:
- **The loader** (`CDL_D32XR_PAGE`): D32XR mode - the loading screen (picture, two text lines, the gold bar only while copying), the board probe, the checksums, the preload copy (CMD 68 pages 2-6) and the record.
- **The Sub-CPU** (`D32XR_CD=7`): `D32XR.32X` is file 20, files 300+ are the preload, CMD 46 wraps in the 4 MB for a WAD that goes on into the next page, CMD 60 leaves window 1 on page 7.
- **The 68000 listener:** `start_d32xr` (MD 35) sets the backdrop black (it was the D32X M1 debug red).

The full entry, with the save area pieces this uses, is section 15 of the shared registry: [CD32X_COMMAND_LEDGER_ADDITIONS.md](https://github.com/MicroNut99/docs/blob/main/CD32X_COMMAND_LEDGER_ADDITIONS.md).
