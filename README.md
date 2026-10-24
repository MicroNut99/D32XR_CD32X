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

Every command starts with the `cd`, so it works from any folder. The disc ends up in
`discs/<NAME>/<NAME>.cue` with its `.bin`: burn or load the `.cue`. A build takes about 5 minutes.
The discs build different game programs, so after switching discs the first boot copies the game
into the cart again.

**1. The DOOM disc** (DOOM, DOOM II, PLUTONIA, RESURRECTION, TNT MINI; CD audio = the IDKFA soundtrack):

```
cd /mnt/s/KoboPort/sega-toolchain-12.1/sega/D32XR_CD32X
NAME=D32XR_CD32X_IDKFA ./build.sh 2>&1 | tee build_log.txt
```

- Needs the 8 MB or 16 MB RAM cart (the 4 MB board is refused: the game fills it, save area
  included; for the 4 MB cart build 1b instead). On 16 MB, DOOM, DOOM II and RESURRECTION are
  preloaded into the cart.
- SIGIL and SIGIL II are not on this disc. `WITHSIGIL=1` puts them back (only the maps that fit the
  32X's RAM from the CD, with SIGIL's songs streamed from the data track).

**1b. The DOOM disc for the 4 MB cart** (`CART4=1`; the same five games):

```
cd /mnt/s/KoboPort/sega-toolchain-12.1/sega/D32XR_CD32X
CART4=1 NAME=D32XR_CD32X_IDKFA_4MB ./build.sh 2>&1 | tee build_log.txt
```

- Runs on the 4, 8 and 16 MB RAM carts, and saves in the cart's save area beside the game like
  the other boards. The log line `4 MB cart: yes (the game ends at 0x3EF464, 2972 bytes before the
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
ROMMAPS="E5M4 E5M5 E5M9 E6M4 E6M8" ROMBUDGET=64 ROMBUDGETS="E6M8=96" NOREJECT=1 SIGILONLY=1 MUSIC=sigil DRAWDIST=far NAME=D32XR_CD32X_SIGIL ./build.sh 2>&1 | tee build_log.txt
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

**2b. The SIGIL 32X+CD cartridge** (`CART=1`: SIGIL and SIGIL II for a flash cart, with the SIGIL
disc in the Sega CD):

```
cd /mnt/s/KoboPort/sega-toolchain-12.1/sega/D32XR_CD32X
CART=1 ROMMAPS="E5M4 E5M5 E5M9 E6M4 E6M8" ROMBUDGET=64 ROMBUDGETS="E6M8=96" NOREJECT=1 SIGILONLY=1 MUSIC=sigil DRAWDIST=far NAME=D32XR_CD32X_SIGIL ./build.sh 2>&1 | tee build_log.txt
```

- The same command as the SIGIL disc plus `CART=1`. It makes the disc as before and also
  `discs/<NAME>/<NAME>_32XCD.32x`: the cartridge ROM (4 MB) for a flash cart on the 32X.
- Play it as a 32X+CD game, the way Fusion itself runs: the cartridge in the 32X, **this SIGIL disc**
  in the Sega CD. The game boots from the cart (no RAM cart, no copying), and reads SIGIL.WAD,
  SIGIL_II.WAD, SOUNDS.WAD and the CD audio from the disc. The same disc still boots by itself as
  the CD32X disc into a RAM cart.
- The same game: the same 12 levels (E6M1 left out), the ROM maps, the draw distance, the pauses,
  the silent loading screens, the pictures. Only the 68000 side differs: it is built in D32XR's own
  cartridge mode (`tools/build_game.sh CART=1`: Mega CD mode 1, as upstream D32XR and Fusion), so
  saves go to the flash cart's save RAM.
- In ares: load the `.32x` as a Mega 32X cartridge and give it the disc when it asks for the CD.

**3. Variants of the SIGIL disc:**

| Want | Change the SIGIL command |
|---|---|
| keep DOOM on it (the same 12 levels) | drop `SIGILONLY=1` and use `ROMBUDGET=24` (DOOM's textures take the room; 8 / 16 MB only) |
| SIGIL's songs streamed instead of CD audio | `WITHSIGIL=1` on the DOOM disc instead (the CD maps only) |

**Both discs:** both engines have room for 230 walls and 32 floor / ceiling areas a frame (165 in
Fusion), part of it in stack space the game never reaches.

**Every switch** (put it in front of `./build.sh`, as in the commands above):

| Switch | Disc | What it does |
|---|---|---|
| `NAME=<name>` | both | the disc's name and folder (`discs/<name>/`; default `D32XR_CD32X_R2`) |
| `CART=1` | SIGIL | also the 32X+CD cartridge ROM `discs/<name>/<name>_32XCD.32x` (2b) |
| `CART4=1` | DOOM | the 4 MB cart build (1b): 13 walls in 4-bit, the game ends below the save area |
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
| `d32xr/doomdef.h`, `mars.h`, `marsnew.c`, `p_tick.c`, `r_phase2.c`, `r_phase6.c`, `r_phase7.c`, `r_phase8.c` | `CD32X_PAUSE`: pauses in the SH2 wait loops (both discs, `CD32X_IDLE`; README "Frame rate"). `r_data.c`: shorter sprite-setup error texts (room for them on the DOOM disc). |

## The boot stack

`cd32x/` is Hurrican CD32X P2a2's boot stack (Sub-CPU `main.c`, 68000 listener `hw_md.s`, SH2 loader `cdloader_sh2.c`), with no new command number:
- **The loader** (`CDL_D32XR_PAGE`): D32XR mode - the loading screen (picture, two text lines, the gold bar only while copying), the board probe, the checksums, the preload copy (CMD 68 pages 2-6) and the record.
- **The Sub-CPU** (`D32XR_CD=7`): `D32XR.32X` is file 20, files 300+ are the preload, CMD 46 wraps in the 4 MB for a WAD that goes on into the next page, CMD 60 leaves window 1 on page 7.
- **The 68000 listener:** `start_d32xr` (MD 35) sets the backdrop black (it was the D32X M1 debug red).

The full entry, with the save area pieces this uses, is section 15 of the shared registry: [CD32X_COMMAND_LEDGER_ADDITIONS.md](https://github.com/MicroNut99/docs/blob/main/CD32X_COMMAND_LEDGER_ADDITIONS.md).
