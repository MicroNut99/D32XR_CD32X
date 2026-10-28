# D32XR CD32X: DOOM CD32X Fusion from the CD

DOOM CD32X Fusion v3.0 on **Sega CD + 32X + a 4 / 8 / 16 MB RAM cart**, booted from a CD. No flash cart is needed.

1. The disc boots, and the loader copies the game (and, on the 16 MB cart, the main WADs) into the RAM cart.
2. D32XR starts from the cart with all of Fusion's own features (the FMV intro, the game select menu, the WADs, music and sound effects through the Sega CD) and the additions below.

The game is DOOM CD32X Fusion v3.0, built from the D32XR team's source (viciious/d32xr, tag `fusion_v3.0`, the same commit as v3.5). Built without the CD32X changes, it comes out byte for byte the Fusion ROM; only the build date in the header differs.

## Cart features

- **Fast load.** The first boot copies the game into the RAM cart (and, on the 16 MB cart, the main
  WADs: SOUNDS, DOOM, DOOM II, RESURRECTION, or SIGIL and SIGIL II). That takes a few minutes, behind
  **FIRST TIME: COPYING DOOM INTO THE RAM CART** and a gold bar. Every later boot checks the cart
  with checksums and, when everything matches, starts the game straight away, copying nothing. Only
  what changed is copied again (after switching discs: the other disc's game).
- **Preloaded WADs (16 MB cart).** The game reads them from the cart instead of the CD: the same
  bytes, no seeking, so levels load faster. On 4 and 8 MB the WADs are read from the CD.
- **A + B + C reset.** Hold **A + B + C** while the disc boots to copy everything into the cart again,
  checked or not (if the cart's contents are ever damaged, or another title used those pages).
- **Saves on the cart.** Games save in the cart's shared save area (piece 11), battery-backed, kept
  across boots and disc changes; the other titles' saves are left alone.
- **Every board.** The 16 MB cart (with the preload), the 8 MB cart, and the 4 MB cart (the SIGIL disc,
  and the DOOM disc built with `CART4=1`; the save area is in the game's 4 MB there, so the game must
  end below it).

How it works in detail: "The cart" and "Every boot" below.

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

| | **DOOM disc** (IDKFA, the default) | **SIGIL disc** (`MUSIC=sigil` + the ROM maps, see Building) |
|---|---|---|
| Games in the select menu | DOOM, DOOM II, PLUTONIA, RESURRECTION, TNT MINI | SIGIL (7 levels), SIGIL II (5 levels) |
| RAM cart | 8 or 16 MB | 4, 8 or 16 MB |
| CD audio tracks | **2-26: Fusion's IDKFA soundtrack**, taken byte for byte from your IDKFA disc image | **2-23: Buckethead's SIGIL and THORR's SIGIL II albums** (11 tracks each: title, the 9 maps, intermission; SIGIL's title and intermission are DOOM / Resurrection's IDKFA tracks; the 5 maps not on the disc get 1 s of silence) |
| DOOM, RESURRECTION music | FM (Fusion's VGM) or, with the music option on CD, the IDKFA tracks | FM (the CD option means FM here: the CD tracks are SIGIL's) |
| DOOM II, PLUTONIA music | FM, or with CD the IDKFA tracks: these games have no tracks of their own on that disc, so their track numbers wrap onto DOOM's songs (as on Fusion's own IDKFA disc) | FM |
| TNT MINI music | FM, or with CD the IDKFA tracks by its song numbers (it has no tracks of its own either) | FM |
| SIGIL, SIGIL II music | not on this disc (`WITHSIGIL=1`: streamed from the data track, Fusion's SPCM) | **CD audio**, whatever the music option (off silences it) |
| Left off the disc | `MAPDEV.WAD` (Fusion's map-testing file; the menu hides it) and the loose `VGM_*` folders (spare copies of music already inside the WADs) | DOOM, DOOM II, PLUTONIA, RESURRECTION, TNT MINI, MAPDEV |
| Size | about 79:46 of an 80:00 CD (estimated from the IDKFA cue; the build prints the real figure and warns above 80:00) | about 72 minutes |

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

- **SIGIL E5M6, E5M7 and SIGIL II E6M1, E6M5, E6M6, E6M7** are not on the SIGIL disc: E5M6, E5M7,
  E6M5, E6M6 and E6M7 don't fit the 32X's RAM even as ROM maps; E6M1 fits but plays too badly (see
  "Why six SIGIL levels are left out"). Their CD audio tracks are on the disc (1 s of silence), so the numbering stays.
- **PLUTONIA MAP28 and MAP29:** the same reason (`Z_Malloc failed` in ares). The map before goes on to the next one that fits.
- **Textures:** a map's own textures share the memory left after its level data. What doesn't fit is drawn as the base game's closest-looking texture of the same size (the build report lists every one). The SIGIL maps are so big that almost all their own textures are stand-ins (lava falls and red rock show as wood and step textures). Skies: the map's own sky only when it fits, else the base game's (SIGIL: the red hell sky).
- **SIGIL's "real" soundtracks** (Buckethead for SIGIL, Thorr for SIGIL II) are not on the discs: the only SIGIL music supplied was the OPL soundtrack video, so its CD tracks and streamed songs sound like FM synth music. SIGIL II's songs are its MIDIs played through an OPL3 emulator with DOOM's instruments, the same kind of sound. Give the build other WAVs (`data/sigil_cdda/Track02-23.wav`) to change that.
- **No skill / level choice when PLUTONIA, SIGIL or SIGIL II start:** like Fusion's WADs without attract demos, the title goes straight into the first map on medium. Pick the skill and the level with Start, Game, New Game.
- **The preload** (16 MB cart) holds SOUNDS, DOOM, DOOM II and RESURRECTION. TNT MINI, PLUTONIA and the SIGILs are read from the CD (no room left in pages 2-6).
- **8 MB cart:** runs, without the preload. **4 MB cart:** the normal DOOM disc is refused (its game fills the whole 4 MB, save area included); the switched build `CART4=1` runs on it, with 13 wall textures in 16 colours (see "Building", 1b).
- **Black patches** in some outdoor spots (also in Plutonia MAP07): gaps the 32X engine leaves empty, as in Fusion.
- **FMV sound in ares** is rough on this disc and on Fusion's own disc alike (the same recording, measured): an emulator matter as far as can be told.
- **Console:** not run yet.

## What you need

- Sega CD + 32X and one of: the **16 MB RAM cart** (8 MB works without the preload), the **4 MB RAM
  cart** (build 1b or the SIGIL disc), or the **Mega EverDrive PRO** (build 4).
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

Every command starts with the `cd`, so it works from any folder. The disc ends up in
`discs/<NAME>/<NAME>.cue` with its `.bin`: burn or load the `.cue`. A build takes about 5 minutes.
The discs build different game programs, so after switching discs the first boot copies the game
into the cart again.

**Which command for which version** (the full commands are in the sections below):

| Version | Runs on | Command after the `cd` | Makes |
|---|---|---|---|
| 1. DOOM disc | 8 / 16 MB RAM cart (disc boot) | `DISC_NAME=D32XR_CD32X_IDKFA ./build.sh 2>&1 \| tee build_log.txt` | `discs/D32XR_CD32X_IDKFA/` |
| 1b. DOOM disc, 4 MB | 4 / 8 / 16 MB RAM cart (disc boot) | `CART4=1 BRAMSAVE=1 PAIN=1 DISC_NAME=D32XR_CD32X_IDKFA_4MB_V3 ./build.sh 2>&1 \| tee build_log.txt` | `discs/D32XR_CD32X_IDKFA_4MB_V3/` (the save in the Sega CD's backup RAM; the Pain Elemental) |
| 2. SIGIL disc | 4 / 8 / 16 MB RAM cart (disc boot) | the long command in section 2 (`... DISC_NAME=D32XR_CD32X_SIGIL ./build.sh`) | `discs/D32XR_CD32X_SIGIL/` |
| 4. DOOM for the EverDrive | Mega EverDrive PRO (cartridge boot) | `CART=ED EDCD=1 NOPRELOAD=1 LOADER_CHECK=1 EDCD_VER=4 PAIN=1 ./build.sh 2>&1 \| tee build_log.txt` | `discs/D32XR_CD32X_R2_EDCD_DOOM_NP_V4_PAIN/` + `cd32x/subcpu/EDCD_DOOM_NP_V4_PAIN.32X` (the Pain Elemental) |
| 4b. DOOM for the EverDrive, 16 MB (preload) | Mega EverDrive PRO (cartridge boot) | `CART=ED EDCD=1 LOADER_CHECK=1 EDCD_VER=4 PAIN=1 ./build.sh 2>&1 \| tee build_log.txt` | `discs/D32XR_CD32X_R2_EDCD_DOOM_V4_PAIN/` + `cd32x/subcpu/EDCD_DOOM_V4_PAIN.32X` (the Pain Elemental; SOUNDS, DOOM, DOOM II, RESURRECTION copied into the EverDrive's memory) |
| 5. DOOM 32X+CD (cartridge + disc) | a flash cart with the 32X game (Mega EverDrive X3 / X5 / X7 / PRO) + the disc in the Sega CD | `CARTCD=1 PAIN=1 DISC_NAME=DOOM32XCD_V1 ./build.sh 2>&1 \| tee build_log.txt` | `discs/DOOM32XCD_V1/`: `DOOM32XCD_V1.32x` (the cartridge ROM, for the SD card) + `DOOM32XCD_V1.cue` / `.bin` |

For a new build of the same version, give it a new name so it never overwrites the last one: a new
`DISC_NAME` (e.g. `D32XR_CD32X_IDKFA_4MB_V4`), or for the EverDrive the next `EDCD_VER` (5, 6, ...).
`PAIN=1` (the Pain Elemental, section "The Pain Elemental") needs your `doom2.wad` in `data/`.

**1. The DOOM disc** (DOOM, DOOM II, PLUTONIA, RESURRECTION, TNT MINI; CD audio = the IDKFA soundtrack):

```
cd /mnt/s/KoboPort/sega-toolchain-12.1/sega/D32XR_CD32X
DISC_NAME=D32XR_CD32X_IDKFA ./build.sh 2>&1 | tee build_log.txt
```

- Needs the 8 MB or 16 MB RAM cart (the 4 MB board is refused: the game fills it, save area
  included; for the 4 MB cart build 1b instead). On 16 MB, DOOM, DOOM II and RESURRECTION are
  preloaded into the cart.
- SIGIL and SIGIL II are not on this disc. `WITHSIGIL=1` puts them back (only the maps that fit the
  32X's RAM from the CD, with SIGIL's songs streamed from the data track).

**1b. The DOOM disc for the 4 MB cart** (`CART4=1`; the same five games):

```
cd /mnt/s/KoboPort/sega-toolchain-12.1/sega/D32XR_CD32X
CART4=1 BRAMSAVE=1 PAIN=1 DISC_NAME=D32XR_CD32X_IDKFA_4MB_V3 ./build.sh 2>&1 | tee build_log.txt
```

- `PAIN=1` (28 Oct 2026, V3): the Pain Elemental (section "The Pain Elemental"). On the 4 MB cart its
  frames other than the floating ones are drawn at half width, and 42 walls and the SKY2 sky are in 16
  colours. Without `PAIN=1` (and with `DISC_NAME=D32XR_CD32X_IDKFA_4MB_V2`) it makes the V2 disc as before.

- `BRAMSAVE=1` (28 Oct 2026): the save is a file in the Sega CD's own backup RAM, `D32XR_DOOM_` - 2048
  bytes in 32 blocks of 64: D32XR's 10 slots of 200 bytes (9 games and the options) - instead of
  piece 11 of the RAM cart's save area. The 68000 keeps a copy of the save; the game's byte reads and
  writes use it, and each save writes the file (`src-md/crt0.s` read_sram, `src-md/scd.c`, the
  Sub-CPU's commands `\` and `]` in `src-md/cd/crt.s` and `s_main.c`).
  - The first boot moves a save over: with no file yet, piece 11 of the cart is taken when it holds
    DOOM's options, written to the backup RAM at once.
  - The Sega CD's backup RAM has 125 free blocks when empty; the file takes 32. If it is missing,
    unformatted or full, the cart's piece 11 stays the save, as without `BRAMSAVE`.
  - Not with `CART=ED` (the EverDrive build keeps its save in the EverDrive's save bank).
  - Without `BRAMSAVE=1` the program is byte for byte the same as before.
  - Tested in ares (28 Oct 2026, 4 MB cart, disc boot): a save in the cart (a game slot and the
    options) moved into the backup RAM on the first boot; with the cart's piece 11 then emptied, Load Game
    still listed the slot (read from the file); an options change wrote the file again, the cart
    left untouched.

- Runs on the 4, 8 and 16 MB RAM carts. Without `BRAMSAVE=1` it saves in the cart's save area beside
  the game like the other boards. The log line `4 MB cart: yes (the game ends at 0x3EF464, 2972 bytes before the
  save area ...)` confirms the fit; `4 MB cart: no` means the program grew and it doesn't fit.
- How it fits: on the 4 MB board the save area is the cart's top 64 KB (0x3F0000-0x3FFFFF), and the
  normal game image (program + Fusion's IWAD) fills all 4 MB. `tools/make_cart4.py` makes a copy of
  Fusion's IWAD 66 KB smaller (`build/cart4_iwad.wad`; the build log lists what it did):
  - textures and flats none of the five games uses point to one small one (4 KB; every sprite is
    used by one of the games, so none can go);
  - 13 wall textures are stored in 16 colours (4-bit) instead of 256: WOOD5, TEKWALL4, PLAT1,
    MARBFACE, MARBFAC3, COMPTALL, BIGDOOR2, then BRONZE3, METAL4, BRICK5, MARBLE3, PANEL4 and
    BRICKLIT (the ones that lose the least colour). This is Fusion's own format - it already stores
    55 of its 148 textures that way - and the engine needs no change. The skies stay as they are.
- The difference to the normal disc: those 13 walls in 16 colours, on every board the disc runs on.
  Use the normal disc on the 8 / 16 MB carts for full colour (and the preload on 16 MB).
- Tested in ares on the 4 MB cart: boot, all five games (10 levels, 60 s each, from the CD), the
  options written to save piece 11 with the other 15 pieces and the game untouched, also after a
  reboot. A checkpoint save itself is untested (Fusion saves at checkpoints, after the first area).

**2. The SIGIL disc** (SIGIL and SIGIL II, 12 of their 18 levels; CD audio = Buckethead and THORR):

```
cd /mnt/s/KoboPort/sega-toolchain-12.1/sega/D32XR_CD32X
ROMMAPS="E5M4 E5M5 E5M9 E6M4 E6M8" ROMBUDGET=64 ROMBUDGETS="E6M8=96" NOREJECT=1 SIGILONLY=1 MUSIC=sigil DRAWDIST=far DISC_NAME=D32XR_CD32X_SIGIL ./build.sh 2>&1 | tee build_log.txt
```

- Runs on the 4, 8 and 16 MB RAM carts. The log line `4 MB cart: yes (...)` says it fits before
  the 4 MB board's save area; on 16 MB, SIGIL.WAD and SIGIL_II.WAD are preloaded.
- Levels: E5M1-5, E5M8, E5M9 and E6M2-4, E6M8, E6M9. E5M6, E5M7, E6M5, E6M6 and E6M7 are too big
  for the 32X's RAM; E6M1 fits (add it to `ROMMAPS`, `ROMBUDGET=30`) but plays badly: about 10 fps
  and its many far-off enemies shoot from the darkness (README "Why six SIGIL levels are left out").
- `ROMMAPS`: the maps too big to load from the CD run from the game's ROM image in the cart
  (`tools/make_rommaps.py`): their read-only parts are used in place.
- `ROMBUDGET=64`: KB of each ROM map's own textures (more = fewer look-alike textures; with E6M1
  too, 30 is the most that still fits the 4 MB board). Walls near player 1's start count 64 times
  and the packs' signature art (SIGILTX2, the lion-head switch) is placed first, so what you see
  first is real.
- `ROMBUDGETS="E6M8=96"`: a map's own budget instead of `ROMBUDGET` (E6M8's start pillars,
  SKSPINE1, need it; the game still ends about 105 KB before the 4 MB board's save area).
- `NOREJECT=1`: the ROM maps without their sight tables (room in the ROM).
- `SIGILONLY=1`: DOOM.WAD (and the other games) left off; their textures make room for the ROM
  maps and their textures.
- `DRAWDIST=far`: the farther draw distance (darkness from 190 walls a frame, beyond 1536 units);
  without it, from 150 walls beyond 1024 (less of the view, but busy views reach the wall limit
  far less often).
- `NOIDLE=1`: leaves out the pauses in the SH2 wait loops (both discs; on by default; see
  "Frame rate").
- The pictures (`data/sigil/`, the first that exists): the titles `sigil.jpg` / `Sigil2.jpg` (else
  `<name>_1.jpg`, `.png`, the `.webp` from the download); the intermission / level loading picture
  of both: `art/sigil-wallpaper.jpg` (the goat, full screen; in the repository, not `data/`).
  `SIGILPIC=<file>` puts another picture there for both; `SIGILPIC=lump:SIGILINT` or
  `lump:SIGILIN2` a WAD's own art (SIGIL II's is widescreen: its 4:3 middle).
- SIGIL II's lion-head switch (SW1LION / SW2LION, E6M8's start pillars) shows the goat from
  `art/sigil-wallpaper.jpg` (its middle strip, 64 x 128; `tools/make_game.py --tex-image`) instead
  of DOOM's lion. `SIGILPILLAR=0` keeps the lion. In E6M2 and E6M3 (no room for their own textures)
  the switch stays the base game's skull switch.
- Silent loading screens: the title (the SIGIL logo while the first map loads) has no song, and the
  music stops while a level loads (`d32xr/g_game.c`, SIGIL disc only); the intermission keeps its
  song, the level's own starts once it's loaded. CD tracks 02 and 13 (the title songs) are no
  longer played.
- The music: `data/sigil_albums/Track02-23.wav`, made once from your albums:

```
cd /mnt/s/KoboPort/sega-toolchain-12.1/sega/D32XR_CD32X
python3 tools/make_sigil_albums.py --sigil "SIGIL1_Music/flac" --sigil2 "SIGIL II THORR Music/SIGIL_II_MP3_V1_0.WAD" --idkfa "DOOM CD32X FUSION V3 with IDKFA Soundtrack/DOOM CD32X FUSION V3 with IDKFA Soundtrack.cue" --out data/sigil_albums --cap 280
```

  (needs ffmpeg: Buckethead's 9 tracks, the SIGIL II MP3 WAD's 11 songs, and SIGIL's title and
  intermission from the IDKFA disc; every song at -21 dBFS, faded out at 4:40 so the disc fits a
  74-minute CD.) Without `data/sigil_albums` the disc uses the OPL renders in `data/sigil_cdda`.
- Engine changes only on this disc (the DOOM disc's program has no room for them beside Fusion's
  IWAD): the ROM-map loader, the draw distance (far open lines drawn as darkness in busy views)
  and the black clear after a frame that ran out of walls.

**3. Variants of the SIGIL disc:**

| Want | Change the SIGIL command |
|---|---|
| keep DOOM on it (the same 12 levels) | drop `SIGILONLY=1` and use `ROMBUDGET=24` (DOOM's textures take the room; 8 / 16 MB only) |
| SIGIL's songs streamed instead of CD audio | `WITHSIGIL=1` on the DOOM disc instead (the CD maps only) |

**4. DOOM for the Mega EverDrive PRO** (the same five games as 1; the EverDrive's launcher starts the
disc as a cartridge boot):

```
cd /mnt/s/KoboPort/sega-toolchain-12.1/sega/D32XR_CD32X
CART=ED EDCD=1 NOPRELOAD=1 LOADER_CHECK=1 EDCD_VER=4 PAIN=1 ./build.sh 2>&1 | tee build_log.txt
```

- Makes the disc `discs/D32XR_CD32X_R2_EDCD_DOOM_NP_V4_PAIN/` and the launcher
  `cd32x/subcpu/EDCD_DOOM_NP_V4_PAIN.32X`. Burn the disc; copy the launcher to the EverDrive's SD card and
  start it from the EverDrive's menu with the disc in the Sega CD (not "Run Mega-CD"). The disc is
  EverDrive-only (its ROM is built for the cartridge boot's map).
- `NOPRELOAD=1`: the loader copies only the game's 4 MB and the game reads every WAD from the CD.
  The EverDrive's menu wipes its PSRAM, so whatever is in the cart is copied again at every start:
  about 1 minute of LOADING GAME on the console (the owner, 28 Oct 2026). ares takes 88 s for it and
  290 s with the preload, far longer than the console (not 5 minutes there either, the owner): ares's
  Sega CD loading is to be matched to the console's (README-CD32X.md of the ares build, "Console
  timing"). A 1x CD gives 150 KB/s: 27 s for 4 MB, 93 s for 14.1 MB.
- `LOADER_CHECK=1`: each 32 KB of the game is checked and copied again if it came out wrong (the
  `4DE2` stop on the console, 27 Oct 2026); a stop shows its code on screen.
- `EDCD_VER=4`: `_V4` on both names. Use the next number for each new build: the EverDrive keeps
  each launcher's saves under its own name (`MEGA/gamedata/EDCD_DOOM_NP_V4_PAIN.32X/bram.srm`), so a new
  version starts without the last one's saves.
- `PAIN=1` (V4): the Pain Elemental (section "The Pain Elemental"), all its frames at full width; 35
  walls are in 16 colours to make room. `_PAIN` on both names. Without it: the V3 build
  (`EDCD_VER=3`, no `PAIN=1`).
- **4b, the EverDrive's 16 MB** (28 Oct 2026): the same command without `NOPRELOAD=1`
  (`CART=ED EDCD=1 LOADER_CHECK=1 EDCD_VER=4 PAIN=1 ./build.sh`): the disc
  `discs/D32XR_CD32X_R2_EDCD_DOOM_V4_PAIN/` and the launcher `EDCD_DOOM_V4_PAIN.32X` (no `_NP`, so it
  never overwrites 4's). The loader also copies SOUNDS, DOOM, DOOM II and RESURRECTION into the
  EverDrive's PSRAM (pages 2-6, 10.1 MB) and the game reads them from there instead of the CD (TNT MINI
  and PLUTONIA still from the CD). The EverDrive's menu wipes its PSRAM, so all of it is copied again at
  every start: 14.1 MB instead of 4's 4 MB - at least 93 s at the CD's 1x speed (ares: 290 s; the
  console is much faster than ares - not yet timed with this build). The game is the same 4 MB as 4's. Tested in ares: the launcher, the load with its checks, SELECT GAME, DOOM II MAP21 (Ultra-Violence) and MAP23 from the
  EverDrive's memory, and a test copy with a Pain Elemental on MAP01 (it shows, spits Lost Souls). The
  preload reads have not run on a console yet (4 and earlier EverDrive builds were `NOPRELOAD=1`).
- The save (the options and Fusion's checkpoint) is in the EverDrive's save bank (bank 31), not in
  the game's 4 MB, so the 4 MB game of 1b is not needed here.
- Tested: V2 on the console (27 Oct 2026, "100% working"); V3 in ares (LOADING GAME, the video,
  SELECT GAME, DOOM's title). V3 only differs from V2 in its build stamp. V4 in ares (28 Oct 2026):
  the launcher, LOADING GAME, SELECT GAME, DOOM II with a Pain Elemental (see "The Pain Elemental").

**5. DOOM 32X+CD** (the same five games; the way Fusion itself runs: the game is a cartridge, the
Sega CD supplies the levels, sounds, video and music):

```
cd /mnt/s/KoboPort/sega-toolchain-12.1/sega/D32XR_CD32X
CARTCD=1 PAIN=1 DISC_NAME=DOOM32XCD_V1 ./build.sh 2>&1 | tee build_log.txt
```

- Makes `discs/DOOM32XCD_V1/` with `DOOM32XCD_V1.32x` (the cartridge ROM, 4 MB) and the disc
  `DOOM32XCD_V1.cue` / `.bin`. Copy the `.32x` to the flash cart's SD card and start it from the cart's
  menu with the disc in the Sega CD (the 32X and the Sega CD both attached). Burn the disc as usual.
- For the carts that cannot load a game from the disc into themselves (the Mega EverDrive X3, X5, X7):
  the menu loads the game from the SD card in seconds - no LOADING GAME, no launcher. It runs on the PRO
  too. Not on the Mega EverDrive Core, which cannot use a Sega CD from a cartridge game.
- The ROM is D32XR's own cartridge build (no `CD32X=1`: no boot stack, no RAM cart pages, no loading),
  as the SIGIL 32X+CD project builds SIGIL; the saves are in the cartridge's save RAM (16 KB, declared
  in the ROM's header, as Fusion's). The disc is a plain data track (the WADs, SOUNDS.WAD, the video;
  no boot program) plus the CD audio.
- `PAIN=1`: the Pain Elemental, as on the EverDrive (all frames full width, 35 walls in 16 colours).
  Without it, Fusion's game with PLUTONIA added.
- Tested in ares (28 Oct 2026, the cartridge + the disc): the video, SELECT GAME in 25 s, DOOM II with
  a Pain Elemental on MAP01 (test copy of the disc), an options change written to the cartridge's save
  RAM. Not on a console yet; whether the X series gives a cartridge game the Sega CD as the PRO does has
  to be seen on one.

**Both discs:** both engines have room for 230 walls and 32 floor / ceiling areas a frame (165 in
Fusion), part of it in stack space the game never reaches.

**Every switch** (put it in front of `./build.sh`, as in the commands above):

| Switch | Disc | What it does |
|---|---|---|
| `DISC_NAME=<name>` | both | the disc's name and folder (`discs/<name>/`; default `D32XR_CD32X_R2`, `D32XR_CD32X_R2_4MB` with `CART4=1`). Not `NAME`: WSL exports NAME (the PC's name) into every shell, so build.sh ignores it |
| `CART4=1` | DOOM | the 4 MB cart build (1b): 13 walls in 4-bit, the game ends below the save area |
| `BRAMSAVE=1` | both | the save as the file `D32XR_DOOM_` (32 blocks) in the Sega CD's backup RAM instead of the cart's save area; the first boot moves a cart save over (1b). The default disc name gets `_BRAM`. Not with `CART=ED` |
| `CARTCD=1` | DOOM | the 32X+CD version (5): the game as a cartridge ROM for a flash cart's SD card + the disc it reads; names get `_32XCD`. Not with `CART`, `EDCD`, `CART4`, `BRAMSAVE` or `ROMMAPS` |
| `PAIN=1` | DOOM | the Pain Elemental (from D32XR, 23-25 Oct 2026; its data from your `data/doom2.wad`): section "The Pain Elemental". The disc and launcher names get `_PAIN`. Not with `ROMMAPS` |
| `WITHSIGIL=1` | DOOM | SIGIL and SIGIL II on the DOOM disc too (the maps that fit the RAM from the CD; songs streamed) |
| `MUSIC=sigil` | SIGIL | CD audio = SIGIL's and SIGIL II's songs (`data/sigil_albums`, else `data/sigil_cdda`); default `MUSIC=idkfa` = the IDKFA soundtrack |
| `SIGILONLY=1` | SIGIL | only SIGIL and SIGIL II on the disc (DOOM and the others left off: room for the ROM maps' textures) |
| `ROMMAPS="E5M4 ..."` | SIGIL | the maps that run from the game's ROM image (too big to load from the CD) |
| `ROMBUDGET=64` | SIGIL | KB of each ROM map's own textures (default 64) |
| `ROMBUDGETS="E6M8=96"` | SIGIL | a ROM map's own texture budget instead of `ROMBUDGET` |
| `NOREJECT=1` | SIGIL | the ROM maps without their sight (reject) tables: room in the ROM |
| `DRAWDIST=far` | SIGIL | the farther draw distance (darkness beyond 1536 units from 190 walls a frame, instead of 1024 from 150) |
| `NOIDLE=1` | both | no pauses in the SH2 wait loops ("Frame rate") |
| `FIRE=0` | both | no title fire (Resurrection's) |
| `HIRES=0` | DOOM | PLUTONIA without the 1K texture pack |
| `PLUT_BUDGETS=<file>` | DOOM | PLUTONIA's per-map texture budgets (default `tools/plutonia_budgets.txt`) |
| `CUT="..."` | both | the Fusion disc files left off (`CUT=""` keeps all) |
| `IDKFA=<cue>` | DOOM | the IDKFA soundtrack disc image (default: the `.cue` in "DOOM CD32X FUSION V3 with IDKFA Soundtrack") |
| `SIGILCDDA=<folder>` | SIGIL | other SIGIL CD audio tracks (`Track02-23.wav`) |
| `SIGILPIC=<file>` | SIGIL | another intermission / loading picture for SIGIL and SIGIL II (default: `art/sigil-wallpaper.jpg`; `lump:SIGILINT` / `lump:SIGILIN2`: a WAD's own art) |
| `SIGILPILLAR=0` | SIGIL | SIGIL II's lion-head switch stays the lion (default: the goat from `art/sigil-wallpaper.jpg`) |
| `CART=ED EDCD=1` | both | the **Mega EverDrive PRO** build (section 4): the EverDrive as the 16 MB cart, plus the launcher `EDCD_DOOM.32X` for its SD card (start that with the disc in the Sega CD, not "Run Mega-CD"). The ROM is built for the cartridge boot's map, so that disc is EverDrive-only - README "The two memory maps" |
| `LOADER_DIAG=1` | both | the loading screen off, so the Sub-CPU's green `STATE:` text shows: `4Cnn` is the chunk being copied. For a load that stops - the number says where, and whether it is still moving |
| `NOPRELOAD=1` | both | nothing preloaded into the cart: the loader copies the game's 4 MB only and the game reads every WAD from the CD (D32XR's own way). For the EverDrive (`CART=ED`), whose menu wipes its PSRAM so the preload was copied again at every start: 4 MB of loading instead of 14 (console: about 1 minute for the 4 MB; ares: 88 s instead of 290, slower than the console). The disc and launcher get `_NP` in their names (`D32XR_CD32X_R2_EDCD_DOOM_NP`, `EDCD_DOOM_NP.32X`) |
| `EDCD_VER=<n>` | both | with `CART=ED`: `_V<n>` on the disc's and the launcher's names (`D32XR_CD32X_R2_EDCD_DOOM_NP_V2`, `EDCD_DOOM_NP_V2.32X`), so a new build never overwrites the last one |
| `LOADER_CHECK=1` | both | the game's 4 MB are checked 32 KB at a time against the build's own table, and a piece that came out wrong is copied again from the CD (up to 3 times; `4Bnn` shows for about 3 s when nn pieces were copied twice). A loader stop shows its code over the loading screen instead of a bar that just stops: `4Enn` piece nn never came out right, `4DE2` the whole ROM still wrong, `4DE6` it changed after its check |
| `GENDEV=<folder>` | both | the D32XR devkit's folder (default `/opt/d32xr-dk/opt/toolchains/sega`) |

**Emulator test options** (never for a disc you play): `TEST_GOD=1` the player takes no damage;
`TEST_STATS=1` the renderer's counters (walls, floor / ceiling areas, stack depth) for an ares RAM
dump; `TEST_WALLS=n`, `TEST_PLANES=n` other limits; `TEST_EXIT=1` every level ends by itself after
about 300 frames (to see the intermission and the next loading screen); `TEST_DEBUG=1` D32XR's
timing screen on from the start (in a disc you play: Options + MODE; its times read 0 in ares).

**The build's tools** (`tools/`):

| Tool | Does |
|---|---|
| `extract_iwad.py`, `extract_iso.py` | the IWAD out of your ROM, the files out of your Fusion disc image |
| `make_game.py` | PLUTONIA / SIGIL / SIGIL II: the maps, the donor textures within each map's RAM budget, the 1K pack, the pictures, DMAPINFO (music, CD tracks) |
| `make_spcm.py` | SIGIL's streamed songs (only those the WADs play) for the IDKFA disc |
| `extract_cue_audio.py` | the IDKFA disc's audio tracks, byte for byte |
| `make_sigil_cdda.sh`, `oplrender.c` | SIGIL's 22 songs as WAVs: cut from the OPL soundtrack video (SIGIL) and rendered through an OPL3 emulator (SIGIL II) |
| `make_preload.py`, `make_splash.py`, `build_game.sh` | the preload plan and checksums, the loading screen, the game build |
| `make_rommaps.py` | the SIGIL disc's IWAD: the ROM maps in the engine's own form, DOOM II's monster sprites and unused textures / flats pointed to one small one |
| `make_sigil_albums.py` | the SIGIL disc's 22 CD audio tracks from Buckethead's and THORR's albums |
| `fit_4mb.py` | cuts the game to its used size (SIGIL disc, `CART4=1` DOOM disc), so it runs on the 4 MB board beside the save area |
| `make_cart4.py` | `CART4=1`: Fusion's IWAD 66 KB smaller for the 4 MB cart (unused textures/flats stubbed, 13 walls in 4-bit) |
| `../cd32x/subcpu/make_mixed_cd2.py` | the mixed-mode `.bin` / `.cue` |

## Why six SIGIL levels are left out
The 32X has 256 KB of RAM. D32XR keeps a level in a 210 KB memory pool (the zone); a map loaded
from the CD needs its whole level data there, about 175 KB at most with its textures. Five SIGIL
maps are bigger than that, so they run as ROM maps (`ROMMAPS`): their vertexes, segs, nodes, reject
and blockmap are used in place from the cart. Even so, a map's lines, sides, sectors, subsectors
and its things (every monster and item becomes a 32X object) must be built in RAM. The six left out
are the biggest in those (counts from the WADs; for comparison the largest maps on the disc):

| Map | Level data | Things | Lines | Sides | Sectors | Subsectors | Result in ares |
|---|---|---|---|---|---|---|---|
| E5M6 Unspeakable Persecution | 325 KB | 436 | 4830 | 8450 | 538 | 3573 | `Z_Malloc: failed on 11720` while loading |
| E5M7 Nightmare Underworld | 387 KB | 520 | 5629 | 8999 | 837 | 4217 | `Z_Malloc: failed on 17980` |
| E6M5 Wrathful Reckoning | 319 KB | 414 | 4720 | 7885 | 705 | 3293 | `Z_Malloc: failed on 9704` |
| E6M6 Vengeance Unleashed | 337 KB | 508 | 4887 | 8331 | 483 | 3820 | `Z_Malloc: failed on 14296` |
| E6M7 Descent Into Terror | 351 KB | 647 | 4953 | 8223 | 725 | 3366 | `Z_Malloc: failed on 20092` |
| E6M1 Cursed Darkness | 319 KB | 284 | 4461 | 7990 | 402 | 4049 | loads (as a ROM map), but about 10 fps, and far-off enemies shoot from the darkness: left out by choice |
| *E5M4 (on the disc)* | 301 KB | 375 | 4427 | 6805 | 579 | 3184 | plays |
| *E6M4 (on the disc)* | 306 KB | 264 | 4443 | 7595 | 483 | 3788 | plays |

When one of the five loads, the zone fills with about 180 KB of level data and the next 10-20 KB
request fails: they would need 10-20 KB more RAM than the 32X has for them. The zone can't give it
(taking 11 KB from it already broke the big SIGIL II maps that do fit), the 16 MB cart doesn't
help (it adds cart space, not RAM), and the rest of the 32X's RAM is the program, the frame
buffers' work area and the stacks. E6M1 can be put back with `ROMMAPS="E5M4 E5M5 E5M9 E6M1 E6M4
E6M8" ROMBUDGET=30` (it still fits the 4 MB board).

## Frame rate
The two SH2s share one bus, and the main SH2 has priority. A wait loop that reads a register or a
lock as fast as it can takes the bus again and again while the other SH2 draws. On both discs every
such loop of a frame pauses about 1.4-7 us between tries, in registers from the cache
(`CD32X_PAUSE` in `d32xr/doomdef.h`; the same fix as OpenLara CD32X's REV-1). The loops: the second
SH2 waiting for the next wall from the BSP walk (`r_phase2.c`), the wall drawing waiting for a
prepared wall and the wall lock (`r_phase6.c`), the floor / ceiling lock and hand-over
(`r_phase7.c`), the sprite hand-over (`r_phase8.c`), the end of the frame (`p_tick.c`), the main
SH2 waiting for the second one's walls / planes / sprites / sight checks (`mars.h`) and the second
SH2's idle loop (`marsnew.c`). The rare waits (melt, automap, title, sound / video set-up) stay as
they were: each pause costs about 12 bytes, and the DOOM disc's program has 128 bytes to spare
beside Fusion's IWAD (the sprite-setup error texts are shorter for it, `r_data.c`). The SIGIL disc's
main SH2 stack keeps about 2 KB spare above its measured depth (7.1 KB). `NOIDLE=1` leaves the
pauses out.

Measured in ares with its console timing (`ARES_32X_TIMING=console`), standing 60 s at the start
of a map (god mode, no input), frames drawn:

| Map | Without | With the pauses |
|---|---|---|
| SIGIL E5M9 Realm of Iblis | 8.9 fps | 9.8 fps (+10 %) |
| SIGIL E6M3 Twilight Desolation | 6.0 fps | 6.4 fps (+8 %) |
| SIGIL E6M4 Fragments of Sanity | 6.3 fps | 6.7 fps (+7 %) |
| SIGIL E6M8 Abyss of Despair | 6.9 fps | 7.3 fps (+5 %) |
| PLUTONIA MAP01 | 14.7 fps | 15.0 fps (+2 %) |
| PLUTONIA MAP04 | 19.9 fps | 20.0 fps |
| PLUTONIA MAP06 | 9.2 fps | 9.8 fps (+6 %) |
| PLUTONIA MAP08 | 16.5 fps | 18.3 fps (+11 %) |
| PLUTONIA MAP20 | 6.0 fps | 6.7 fps (+11 %) |
| PLUTONIA MAP32 | 13.3 fps | 14.1 fps (+6 %) |

(SIGIL: an earlier set of pause sites; PLUTONIA: the `CART4=1` disc on the 4 MB cart.) Compare
builds standing still: a scripted player who walks and fires ends up somewhere else in each build
(the game runs by time, the script by frames), wakes other monsters, and the frame rate then swings
between about 7 and 15 fps whatever the code.

All 137 levels of the DOOM disc (16 MB cart) and the SIGIL disc's 12 levels (4 MB cart) were played
60 s each with the pauses in ares: no crash, hang or error screen.

Tried and left out: the renderer at `-O2` instead of `-Os`. Its hot code is in the 32X's SDRAM;
`-O2` makes it 4 KB bigger, which the stack doesn't have (black screen), and with 6 KB of zone
given up for a test it was *slower* (E6M4 6.3, E6M8 7.0 fps): bigger code misses the SH2's 4 KB
cache more often. Even `-O2` on the renderer's cart code alone grew the SDRAM code 4 KB (inlining).

## The Pain Elemental (`PAIN=1`)

D32XR added the Pain Elemental on 23 Oct 2026 ("Add Pain Elemental"; on 25 Oct the Icon of Sin
spawns it too and the cast at the end shows it). DOOM CD32X Fusion, which these discs are built on, has
none of it: no code, no sprites or sounds, and its DOOM II maps have a Cacodemon (three Imps on MAP25)
wherever DOOM II has a Pain Elemental. `PAIN=1` puts all of it in, and it needs your `doom2.wad` in
`data/` (the build stops without it):

- **Code** (`CD32X_PAIN`, set by `tools/build_game.sh`): D32XR's commits 6dc5d59, b9c8ade and
  335f59b - the monster (`A_PainAttack`, `A_PainDie`: a Lost Soul out of its mouth, three when it
  dies, no more when 21 are about), the Arch-Vile raising it, the Icon of Sin spawning it (DOOM II's
  odds), the cast ("pain elemental"; "arch vile" as D32XR now spells it). D32XR's mobj list is one
  pointer here (Fusion's), so the Lost Soul count walks `mobjhead.next`.
- **Sprites** (`tools/make_pain.py iwad`): DOOM II's 41 PAIN sprites in the 32X format, added to the
  IWAD; identical runs of pixels are stored once (118 KB instead of 149 KB).
- **Sounds** (`tools/make_pain.py disc`): DSPESIT, DSPEPAIN, DSPEDTH in SOUNDS.WAD, in the format of
  Fusion's smallest sounds (Creative Voice File, 2-bit ADPCM). The Sega CD keeps every sound in one
  453 KB buffer which Fusion's sounds fill to 548 bytes: two sounds that are never played make the room
  (the first of the two VILATK - the game finds the second - and FLAMST - the game asks for
  "flamest"), and the three are made at 7042 Hz, the most that fits.
- **Maps:** DOOM_II.WAD's 64 Pain Elementals are back (MAP08-11, 15, 17, 20, 21, 23, 25, 27-29: the
  Cacodemons / Imps standing on their spots, with their flags); PLUTONIA.WAD keeps its 96
  (`tools/make_game.py --keep-pain`; without `PAIN=1` they become Cacodemons, as before).
- **Room:** Fusion's IWAD already fills the game's 4 MB, so walls go to 16 colours, the least colour
  lost first (`tools/make_cart4.py --any-size`: any size that gets smaller, textures other textures
  draw pieces of when their height is even - `R_CompositeColumn` reads 4-bit ones - and the 8-bit sky
  SKY2 as Fusion's other skies). The EverDrive (4): 35 walls, all frames at full width. The 4 MB RAM
  cart (1b) has 64 KB less (its save area): 42 walls and SKY2, and the Pain Elemental's attack, pain
  and death frames at half width (each odd column repeats the even one); its floating frames stay full.
  `make_pain.py` takes the least loss that fits: half width only for what the walls cannot make room for.
- **Not checked:** DOOM II's second attract demo plays on MAP11, which now has four Pain Elementals
  where Fusion's recording had Cacodemons, so it may play out differently.
- **Tested in ares (28 Oct 2026):** both builds, with a copy of each disc whose DOOM II MAP01 has a
  Pain Elemental in front of the start: it shows, floats over, spits Lost Souls (frames 1b half / 4
  full width), the sounds play; with a test build of 1b (health 10) it bursts into its death frames and
  three Lost Souls. The builds without `PAIN=1` are byte for byte the same as before (game builds
  compared).

## The cart

| Page (2 MB) | Holds |
|---|---|
| 0 | the game, first 2 MB (window 0) |
| 1 | the shared save area and other titles' data. Untouched, except DOOM's saves in **piece 11** and the loader's record in **piece 15** (test scratch) |
| 2-6 | **the preload**: SOUNDS.WAD, DOOM.WAD, DOOM_II.WAD, RESURRECTION.WAD (10.1 MB of 10.3 MB) |
| 7 | the game, second 2 MB (window 1 while the game runs) |

**The 4 MB board** has no pages: the cart is the game's 4 MB, and the shared save area is its top
64 KB (0x3F0000-0x3FFFFF, the same 16 pieces; DOOM's saves in piece 11). The loader copies a game
there only when it ends below 0x3F0000 (`cd32x/sh2/cdloader_sh2.c`), else it shows "THIS DISC NEEDS
THE 8 MB OR 16 MB RAM CART". The SIGIL disc and the `CART4=1` DOOM disc fit; the normal DOOM disc
doesn't. No preload: the WADs are read from the CD.

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

## The melt bug, second cause: the column store in a cartridge boot (EverDrive, 26 Oct 2026)

**What you see:** on the EverDrive build (`CART=ED EDCD=1`) the melt is broken - its pictures are
garbage - while the same disc's CD boot is clean. Nothing to do with the fire or the first melt bug
above, whose fix is still in place.

**The cause** (`d32xr/src-md/crt0.s`, `cpy_md_vram`): the melt keeps its starting and ending pictures
in Mega Drive VRAM, a column at a time -

```
wipe_StartScreen -> I_StoreScreenCopy -> Mars_StoreWordColumnInMDVRAM
wipe_EndScreen   -> I_SwapScreenCopy  -> Mars_SwapWordColumnWithMDVRAM
                                            -> crt0.s cpy_md_vram -> lea COL_STORE,a0
```

`COL_STORE` is "Word RAM + 2 KB", and it was chosen by `.ifdef CD32X` alone: `0x200800`, which is where
Word RAM is **when the disc boots** (mode 2). Started from the EverDrive the console stays in cartridge
mode, where `0x200800` is the **cart**: the column writes land nowhere and the reads come back as ROM
bytes, so every picture the melt saves is garbage.

**The fix:** `COL_STORE` follows `CD32X_MODE1` like the rest of the mode-dependent addresses -
`0x600800` in a cartridge boot. Commit `6378b4f`, completing `d0aa18f`.

**How it was found:** the first melt bug's write-up above says the melt's starting picture is whatever
is on screen when it begins, so the search started at what fills that picture - and that path ends in
`cpy_md_vram`, one of the five places in the game's own 68000 code that name a Mega CD address. The
same question had already been asked of `scd*.c` and `vgm.c` for the "No playable WADs found on the CD"
bug; `COL_STORE` was the one that was missed, because it is an `.equ` in `crt0.s` rather than a
`#define` beside the others.

## The two memory maps (`CD32X_MODE1`)

A CD boot and a cartridge boot are mirror images, and the game's own 68000 code addresses both sides
directly, so the EverDrive disc needs its own ROM:

| | Mega CD | Word RAM | the cart |
|---|---|---|---|
| the disc booted (mode 2), `CD32X=1` | `0x000000` | `0x200000` | `0x400000` with RV = 1 |
| started from the EverDrive (mode 1), `CD32X_MODE1=1` | `0x400000` | `0x600000` | `0x000000` |

`build.sh` sets `CD32X_MODE1=1` when `EDCD=1`, the same way it passes `CD32X_ED` and `CD32X_PAGE`
(`src-md/Makefile`: `-DCD32X_MODE1` and `--defsym CD32X_MODE1=1`). It reaches `MCD_BASE` (`scd.c`),
`MD_WORDRAM` (`scd_fs.c`, `scd_roq.c`, `vgm.c`), `SCD_PCM_WORDRAM` (`scd_pcm.c`) and, in `crt0.s`,
`CD32X_CART` with `CD32X_W1`, `CD32X_SAVE`, `CD32X_EDSAVE` and `COL_STORE` derived from it.

Without it the game reads its disc-directory buffer at `0x200000` - the cart in that mode - finds
nothing and stops with **"No playable WADs found on the CD"** (`gs_main.c`), after the WADs have loaded
perfectly well. That was the EverDrive build's symptom until 26 Oct 2026, in ares and on the console
alike.

**The EverDrive disc is therefore EverDrive-only**: its ROM is built for mode 1 and will not boot from
the Sega CD by itself. The CD-boot disc is unchanged, byte for byte.

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
| `d32xr/src-md/scd*.c`, `vgm.c`, `crt0.s`, `Makefile` | `CD32X_MODE1`: the cartridge boot's map for the EverDrive disc (README "The two memory maps"). |
| `d32xr/src-md/crt0.s` | The melt bug's second cause: `COL_STORE` follows the boot mode (README "The melt bug, second cause"). |
| `d32xr/src-md/crt0.s` | `COL_STORE`'s `CD32X_MODE1` test only inside `CD32X` (where it is defined): D32XR's own cartridge build (`CARTCD=1`) assembles again; the `CD32X` builds are byte for byte the same. |
| `d32xr/marssound.c`, `marshw.*`, `d_mapinfo.*` | `cdMusic`, `musicStream`, the CD track restart after disc reads, `CD32X_CDONLY` (set by `build_game.sh` for the SIGIL disc). |
| `d32xr/marsroq.c` | The FMV sound at half volume (-6 dB) around the PWM centre. |
| `d32xr/p_setup.c` | `MAX_AUX_TEXTURES` 64 (from 32): more of a map's own textures. |
| `d32xr/info.c`, `info.h`, `p_enemy.c`, `sounds.c`, `sounds.h`, `f_main.c` | `CD32X_PAIN` (`PAIN=1`): the Pain Elemental, D32XR's own code (section "The Pain Elemental"). |
| `d32xr/doomdef.h`, `mars.h`, `marsnew.c`, `p_tick.c`, `r_phase2.c`, `r_phase6.c`, `r_phase7.c`, `r_phase8.c` | `CD32X_PAUSE`: pauses in the SH2 wait loops (both discs, `CD32X_IDLE`; README "Frame rate"). `r_data.c`: shorter sprite-setup error texts (room for them on the DOOM disc). |

## The boot stack

`cd32x/` is Hurrican CD32X P2a2's boot stack (Sub-CPU `main.c`, 68000 listener `hw_md.s`, SH2 loader `cdloader_sh2.c`), with no new command number:
- **The loader** (`CDL_D32XR_PAGE`): D32XR mode - the loading screen (picture, two text lines, the gold bar only while copying), the board probe, the checksums, the preload copy (CMD 68 pages 2-6) and the record.
- **The Sub-CPU** (`D32XR_CD=7`): `D32XR.32X` is file 20, files 300+ are the preload, CMD 46 wraps in the 4 MB for a WAD that goes on into the next page, CMD 60 leaves window 1 on page 7.
- **The 68000 listener:** `start_d32xr` (MD 35) sets the backdrop black (it was the D32X M1 debug red).

The full entry, with the save area pieces this uses, is section 15 of the shared registry: [CD32X_COMMAND_LEDGER_ADDITIONS.md](https://github.com/MicroNut99/docs/blob/main/CD32X_COMMAND_LEDGER_ADDITIONS.md).
