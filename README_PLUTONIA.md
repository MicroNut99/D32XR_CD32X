# Plutonia on DOOM CD32X Fusion: what was done to restore it

The Plutonia Experiment (Final Doom, 1996). It is made at build time from **your own `plutonia.wad`** (`data/plutonia.wad`; no game data is in this
repository) by `tools/make_game.py`, and it runs on DOOM CD32X Fusion's engine (D32XR) on the 32X.

This file is about the restoration: what the 32X version of Plutonia was missing, what was done about
it, and what is still not the PC game. The build commands are in `README.md` ("Building": versions 1c,
4c, 4d, 5b and 5c, all with `PLUTEX=1`).

## What it is

**All the monsters.** The 32X ports of Plutonia were said to lack the Arch-vile and the Pain
Elemental, and to choke on MAP11 and MAP32. On this disc:

- **Arch-viles:** in Fusion's engine already. All 145 of Plutonia's are on its maps, MAP11 "Hunted"
  with all 23 of its own.
- **Pain Elementals:** D32XR's own code for it (added 23-25 Oct 2026), with its sprites and sounds made
  from your `doom2.wad`, behind `PAIN=1` (README "The Pain Elemental"). All 99 are on the maps; without
  `PAIN=1` they are Cacodemons.
- **MAP32 "Go 2 It":** every Cyberdemon, Arch-vile and Pain Elemental it has, for every skill.

**MAP11's special sectors** (`PLUTEX=1`). Two sectors of MAP11 have special 11 (as at the end of DOOM's
E1M8: god mode off, damage, the level ends at 10% health), which D32XR doesn't have: walking into them
stopped the game with "unknown special". `PLUTEX=1` adds it (`d32xr/p_spec.c`).

**Plutonia's own walls, floors and skies** (`PLUTEX=1`). The 32X keeps a map's own pictures in the RAM
its level data leaves free: 18 to 109 KB a map. Without `PLUTEX=1`, 696 of Plutonia's walls and floors
are drawn as the base game's closest-looking texture, and every map has DOOM II's sky.

`PLUTEX=1` uses what these carts have and a real cartridge doesn't: the game's 4 MB are RAM (the RAM
cart, the Mega EverDrive PRO's memory), so the game can write its own image while it runs.

1. At build time, the base game's textures and flats that Plutonia never uses itself (80 of them, about
   270 KB) are moved together into one block at the end of the game's IWAD (`tools/make_cartblk.py`).
2. For each Plutonia map, `tools/make_game.py` puts as many of the map's own pictures as fit into that
   block, in full colour where there is room, and the rest into the map's RAM as before.
3. When the map loads, the 68000 copies that map's pictures from the disc into the block (one read from
   the CD), and the 32X draws them from there, exactly as it draws the base game's own textures.
4. When you quit back to SELECT GAME, the block's original pictures are put back from a copy on the
   disc (about 2 seconds), so DOOM, DOOM II and the others look as they always did.

The result, look-alikes left in each map (EverDrive / 32X+CD; the 4 MB RAM cart has a little less room):

| Map | Name | Without `PLUTEX` | EverDrive, 32X+CD | 4 MB RAM cart |
|---|---|---|---|---|
| MAP01 | Congo | 11, DOOM II sky | 0, own sky | 0, own sky |
| MAP02 | Well of Souls | 22, DOOM II sky | 1, own sky | 1, own sky |
| MAP03 | Aztec | 26, DOOM II sky | 1, own sky | 1, own sky |
| MAP04 | Caged | 25, DOOM II sky | 1, own sky | 1, own sky |
| MAP05 | Ghost Town | 20, DOOM II sky | 1, own sky | 1, own sky |
| MAP06 | Baron's Lair | 35, DOOM II sky | 1, own sky | 1, own sky |
| MAP07 | Caughtyard | 4, DOOM II sky | 1, own sky | 1, own sky |
| MAP08 | Realm | 30, DOOM II sky | 1, own sky | 1, own sky |
| MAP09 | Abattoire | 33, DOOM II sky | 0, own sky | 0, own sky |
| MAP10 | Onslaught | 40, DOOM II sky | 1, DOOM II sky | 1, DOOM II sky |
| MAP11 | Hunted | 19, DOOM II sky | 2, own sky | 2, own sky |
| MAP12 | Speed | 9, DOOM II sky | 0, own sky | 0, own sky |
| MAP13 | The Crypt | 50, DOOM II sky | 15, DOOM II sky | 17, DOOM II sky |
| MAP14 | Genesis | 12, DOOM II sky | 1, own sky | 1, own sky |
| MAP15 | The Twilight | 3, DOOM II sky | 3, own sky | 3, own sky |
| MAP16 | The Omen | 5, DOOM II sky | 0, own sky | 0, own sky |
| MAP17 | Compound | 21, DOOM II sky | 1, own sky | 1, own sky |
| MAP18 | Neurosphere | 15, DOOM II sky | 0, own sky | 0, own sky |
| MAP19 | NME | 14, DOOM II sky | 1, own sky | 1, own sky |
| MAP20 | The Death Domain | 42, DOOM II sky | 1, DOOM II sky | 1, DOOM II sky |
| MAP21 | Slayer | 0, DOOM II sky | 0, own sky | 0, own sky |
| MAP22 | Impossible Mission | 44, DOOM II sky | 8, DOOM II sky | 10, DOOM II sky |
| MAP23 | Tombstone | 36, DOOM II sky | 2, own sky | 2, own sky |
| MAP24 | The Final Frontier | 3, DOOM II sky | 1, own sky | 1, own sky |
| MAP25 | The Temple of Darkness | 42, DOOM II sky | 0, DOOM II sky | 2, DOOM II sky |
| MAP26 | Bunker | 46, DOOM II sky | 5, DOOM II sky | 7, DOOM II sky |
| MAP27 | Anti-Christ | 6, DOOM II sky | 1, own sky | 1, own sky |
| MAP28 | The Sewers | not in the game | 18, DOOM II sky | 20, DOOM II sky |
| MAP29 | Odyssey of Noises | not in the game | 5, DOOM II sky | 6, DOOM II sky |
| MAP30 | The Gateway of Hell | 40, DOOM II sky | 9, DOOM II sky | 12, DOOM II sky |
| MAP31 | Cyberden | 28, DOOM II sky | 0, own sky | 0, own sky |
| MAP32 | Go 2 It | 15, DOOM II sky | 0, own sky | 0, own sky |
| | **All** | **696** | **81** | **95** |

(The counts are the build's own report, `build/plutonia_report.txt`, which names every look-alike.)

**MAP28 "The Sewers" and MAP29 "Odyssey of Noises"** are back. Their level data is bigger than the
32X's RAM (216 and 184 KB, where 175 KB is the most that loads), so they were left out. With `PLUTEX=1`
their read-only parts (vertexes, segs, nodes, reject and blockmap: 96 KB) go into the cart block in the
engine's own form and are used in place; the rest fits the RAM.

**Plutonia's own presentation:** its level names, its four story texts and the two secret-level texts,
its title and intermission pictures, its secret exits (MAP15 to MAP31, MAP31 to MAP32), and the Fusion
team's Mega Drive arrangement of the Plutonia MIDI pack as its FM music (or the CD audio option, with
DOOM II's tracks for the same map numbers).

**Which versions:**

| Version | Plutonia's own textures | Notes |
|---|---|---|
| 1c: 4 MB RAM cart disc | yes | after a power-off in the middle of Plutonia, the next start copies the game again (about a minute, like the first start) |
| 4c / 4d: Mega EverDrive PRO (EDCD) | yes | every start copies the game anyway (the EverDrive's menu wipes its memory) |
| 5b: 32X+CD | yes | **Mega EverDrive PRO only** (its SSF mode: the game writes its own memory); saves in the PRO's save memory |
| 5c: 32X+CD, `EDX=1` | yes | **Mega EverDrive X3 / X5 / X7 only** (the same write bit; the save where their SRAM is, the upper half of bank 31); not run on one yet |
| 1, 1b, 4, 4b, 5 (no `PLUTEX`) | no | Plutonia as before: look-alikes, DOOM II's sky, no MAP28 / MAP29, and MAP11's two special sectors stop the game |

## Which maps change the most

Compared with Plutonia before the restoration (no `PLUTEX`), version 5b (32X+CD, Mega EverDrive PRO): the
look-alikes each map loses (its own walls and floors now drawn as themselves), and its sky. From the
table above and `build/plutonia_report.txt`.

| Map | Name | Its own textures back | Sky |
|---|---|---|---|
| MAP28 | The Sewers | not in the game before; now playable (18 look-alikes left) | DOOM II's |
| MAP29 | Odyssey of Noises | not in the game before; now playable (5 left) | DOOM II's |
| MAP25 | The Temple of Darkness | 42 (42 -> 0) | DOOM II's |
| MAP20 | The Death Domain | 41 (42 -> 1) | DOOM II's |
| MAP26 | Bunker | 41 (46 -> 5) | DOOM II's |
| MAP10 | Onslaught | 39 (40 -> 1) | DOOM II's |
| MAP22 | Impossible Mission | 36 (44 -> 8) | DOOM II's |
| MAP13 | The Crypt | 35 (50 -> 15) | DOOM II's |
| MAP06 | Baron's Lair | 34 (35 -> 1) | **its own** |
| MAP23 | Tombstone | 34 (36 -> 2) | **its own** |
| MAP09 | Abattoire | 33 (33 -> 0) | **its own** |
| MAP30 | The Gateway of Hell | 31 (40 -> 9) | DOOM II's |
| MAP08 | Realm | 29 (30 -> 1) | **its own** |
| MAP31 | Cyberden | 28 (28 -> 0) | **its own** |

- **The most different to look at:** MAP06, MAP23, MAP09, MAP08 and MAP31 - nearly all their textures
  and their own sky.
- **In play:** MAP11 "Hunted" - its two special sectors no longer stop the game.
- **The latest fixes:** MAP25-27 no longer stop with "unknown special" or "Z_Malloc failed" (each map
  reads only its own cart block), and the sky fix.
- **The least change:** MAP21 "Slayer" (only its sky; it had no look-alikes), MAP15 "The Twilight" (its
  sky; its 3 look-alikes stay), MAP24 "The Final Frontier" and MAP07 "Caughtyard" (2 and 3 textures, and
  their own sky).
- **The 4 MB RAM cart (1c):** a few more stay look-alikes, 95 in all instead of 81 (the table above).

## What it isn't

- **Not every texture.** 81 walls and floors (95 on the 4 MB cart) are still drawn as a base-game
  look-alike, most of them on MAP13, MAP28, MAP30 and MAP22. The block holds about 270 KB, and those maps
  have more of their own pictures than that and their RAM can take.
- **Not every sky.** Nine maps (MAP10, 13, 20, 22, 25, 26, 28, 29, 30) keep DOOM II's sky: their own
  textures took the room first.
- **Not every animation.** 53 animated walls or switches show one picture (waterfalls, lava and fire
  walls, some switches: they still work, but look the same on and off). The engine animates only the
  base game's animations, and the base game has no free one of the right length for these.
- **Not the see-through textures.** 28 railings, vines and grates that you see through are drawn with a
  base-game see-through texture (e.g. `A-RAIL1` as `BRNBIGC`): the engine draws see-through middle
  walls only from sprite-shaped textures.
- **Not the PC's colours exactly.** The 32X draws textures with 256 or 16 colours each; walls that did
  not fit in full colour are in 16 colours (on the 4 MB cart more of them), and the 1K texture pack's
  pictures are shrunk to the textures' own size.
- **Not Plutonia's own MIDI music:** the FM music is the Fusion team's Mega Drive arrangement; the CD
  audio option plays DOOM II's soundtrack.
- **Not the PC engine.** It is D32XR, the 32X engine Fusion is built on: its frame rate, draw distance,
  low-detail options and the black patches it leaves in some outdoor spots (as in Fusion) all apply. The
  busiest maps (MAP32's crowd, the open maps) run slower; the frame rate there has not been measured.
- **Not for a plain cartridge.** The restored textures need a cart whose memory the game can write: the
  RAM cart or a Mega EverDrive in its SSF mode. The 32X+CD cartridge comes in two builds, 5b for the PRO
  and 5c for the X3 / X5 / X7: never swap them (each saves where the other cart's OS keeps its own data).
  On a real ROM cartridge or another flash cart, use 5 without `PLUTEX`.
- **Not on a console yet.** Everything above was checked in ares (see "Tested"). The cart writes use the
  same steps as the saves, which do run on the console, but this build has not.
- **Not included:** no game data is in the repository or the build's source. You need your own
  `plutonia.wad` (and `doom2.wad` for `PAIN=1`; the optional 1K texture pack in `data/hires/`).

## Tested (ares, 28 Oct 2026)

The tests ran in ares (the emulator) with test builds of the same versions: `TEST_EXIT=1` ends every map
by itself about 5 seconds after it starts (then the intermission and the next map's loading),
`TEST_GOD=1`, and `TEST_WARP=n` starts Plutonia at MAPn (README "Emulator test options"). Apart from
those switches the game program is the one the build commands make.

| Version | What ran |
|---|---|
| 1c: 4 MB RAM cart | every map from MAP01 to MAP30 (in four runs: MAP01-MAP19, MAP20-MAP26, MAP27-MAP29, MAP30 and the cast), with the texts between; MAP31 and MAP32 on their own (each going on to MAP16). After MAP29 and after MAP30 the block in the cart was compared with that map's `CARTDATA`: the same, byte for byte, the record `PLTX`, the rest of the IWAD unchanged |
| 4d: EverDrive PRO, 16 MB | the launcher, the loader (with its check), SELECT GAME, MAP26, MAP27, MAP28 |
| 4c: EverDrive PRO, no preload | the launcher, the loader, SELECT GAME, MAP28, MAP29 |
| 5b: 32X+CD, EverDrive PRO | the cartridge boot, SELECT GAME, MAP28, MAP29, MAP30 |
| 5c: 32X+CD, X-series build | in ares, whose EverDrive is the PRO (it ignores the X bit): the cartridge boot, SELECT GAME, MAP28, MAP29, MAP30; the quick saves at the map exits went to the upper 256 KB of bank 31 (odd bytes: "PLUTONIA.WAD", "The Gateway of Hell"), the lower half untouched. Not on an X3 / X5 / X7 |

Also checked, on the first test builds (the same cart code): quitting to SELECT GAME puts the block
back byte for byte (4 MB cart, EverDrive 16 MB, 32X+CD); MAP01's own slime on the 32X+CD cartridge (it
showed blue water before `CD32X_AUX64`); the 32X+CD cartridge's save in the PRO's save bank. The builds
without `PLUTEX=1` were built from this version and the one before and compared: the game programs
(RAM cart, EverDrive, cartridge, with and without `PAIN=1` / `BRAMSAVE=1`) and PLUTONIA.WAD are byte for
byte the same.

**A fault the tests found and that is fixed:** a map looks for its `CARTMAP` / `CARTDATA` among the
lumps after it, and the engine's list of those holds 64 lumps, the next maps' too. A map with few extra
lumps of its own (MAP25, MAP26, MAP27) took a later map's instead (MAP26 took MAP29's): the wrong
pictures, and MAP29's level pointers, so the game stopped ("unknown special", "Z_Malloc failed"). It now
takes only the map's own first two extra lumps; every map ran after that. Also fixed (found reading the
code): a map's own 8-bit sky after a map with the base game's 4-bit sky was drawn as 4-bit.

**Not tested:** a real console; playing the maps through (the test builds leave each map after 5
seconds: no fights, MAP11's special sectors not walked into, MAP30's boss not killed); the frame rate.

## Playtest: MAP11 and MAP30 (ares, 29 Oct 2026)

**How:** version 1c (4 MB RAM cart, `PLUTEX=1`), medium skill, in `ares-headless` with ares's **real Sega 32X
hardware timing** (ares CD32X v1.3: Settings > Real Sega 32X Hardware Timing; `ARES_32X_TIMING=console`), and
`TEST_PLAYTEST=1`: the map plays itself. It visits up to 12 of its monsters' places for 3 s each, turning
a full circle and making a noise there (as a shot would); kills every monster from close by; sets off every
line special from its front and stands in every special sector; then takes the exit. The frame rate is
the 32X pictures shown per second; the counts come from the game itself (`pt_report`).

**Frame rate** (32X pictures a second; the game shows at most 20):

| | MAP11 "Hunted" | MAP30 "The Gateway of Hell" |
|---|---|---|
| Tour of the monsters' places, average | **13.2 fps** | **14.9 fps** |
| The places, from slowest to fastest (3 s each) | 10.6 - 20.4 | 11.9 - 20.1 |
| Slowest single second | 9 | 10 |
| Setting off the line specials (all over the map) | 17.4 | 15.6 |
| The same MAP30 tour with ares's own (faster) timing | - | 17.4 |

The busiest views (open courtyards, many monsters awake) run at 10-12 fps, closed rooms and corridors
at 16-20. MAP11's 18 arch-viles awake at once cost about the same as MAP30's open arena. The real
hardware timing is ares's first calibration from the timing probe and has not yet been checked
against a game's frame rate on the console: take these as estimates, best for comparing places.

**Monster deaths:**

| | MAP11 | MAP30 |
|---|---|---|
| Monsters at the start (medium) | 18 (all arch-viles) | 23 (6 chaingunners, 4 mancubi, 4 lost souls, 2 each of barons, arch-viles, revenants, arachnotrons, 1 Cyberdemon) |
| Died | 18 (15 killed by the test, 3 by the others' fire) | 28: all 23, and 5 of the Icon of Sin's |
| Raised by arch-viles | 0 (they cannot raise arch-viles) | 0 |
| Kills at the intermission | 100% | 28 (the cube monsters count too) |
| Boss deaths (`A_BossDeath`) | - | 9 (mancubi, arachnotrons, barons, Cyberdemon): no effect, as on the PC (MAP30 has no boss specials) |
| The Icon of Sin | - | its spawner woke at the noise, shot 14 cubes, 12 became monsters (the other 2 were still flying); killing the brain ended the map (`A_BrainDie`), then the intermission and the cast |

**Triggers:**
- MAP11: all 51 line specials that are not the exit set off: the 6 switches and doors all worked (23,
  31, 55 x2, 135, 137); 45 walk-over lines (doors 2 x4 and 90 x19, floors 38 x3, teleports 97 x12, monster
  teleports 125 / 126 x7). Both special-11 sectors stood in (no stop: the new `p_spec.c` code); the
  secret found (100%); the exit line (52) ended the map.
- MAP30: all 28 line specials set off: both switches worked (14, 123), 26 walk-over lines (97 x11, 126
  x8, 109 x4, 30, 37, 141); the damage sectors 5, 7 and 16 stood in.
- No stop in any run: no "unknown special", no `Z_Malloc` failure, no other error.

**What this does not cover:** the console itself; the player's own weapons (the test hurts the monsters
directly; the brain was killed the same way, not with rockets through the wall); a full fight with
every monster awake and shooting for minutes; the special-11 sectors ending the map at 10% health (the
test's god mode keeps the health at 100%).

## Files

| File | What it does |
|---|---|
| `tools/make_game.py` | Plutonia's maps, pictures, DMAPINFO, texts; `--cart-keep-out` (which base textures Plutonia uses), `--cart-iwad` (the pictures for the block, `CARTMAP` / `CARTDATA` per map, `CARTPOOL`), MAP28 / MAP29's read-only lumps |
| `tools/make_cartblk.py` | the block in the game's IWAD (`CARTBLK`, `CARTREC`) |
| `d32xr/p_setup.c` | the block written at a map's load, the pictures and their own sizes, `P_CartLevel` for MAP28 / MAP29, the block put back (`P_CartLeave`) |
| `d32xr/w_wad.c`, `marshw.c` | a lump from the CD into the cart (`W_ReadLumpToCart`, `Mars_CartWrite`) |
| `d32xr/src-md/crt0.s` | the 68000's command 16 (`cart_write`); the 32X+CD cartridge's save in the PRO's save bank (`CARTCD_ED`), or in the X-series' SRAM with the X bit (`CARTCD_EDX`) |
| `d32xr/src-md/everdrive.c` | D32XR's EverDrive check with the X bit (`CARTCD_EDX`) |
| `d32xr/crt0.s` | the 32X+CD cartridge's `SEGA SSF` header (`CARTCD_ED`) |
| `d32xr/d_main.c` | `P_CartLeave` at SELECT GAME |
| `d32xr/p_spec.c` | sector special 11 (MAP11) |
| `d32xr/p_tick.c`, `p_enemy.c`, `p_inter.c`, `doomdef.h` | the playtest (`TEST_PLAYTEST=1`, emulator testing only) |
| `build.sh`, `tools/build_game.sh` | `PLUTEX=1` (and `CARTCD_ED`, `CD32X_AUX64` with `CARTCD=1`; `CARTCD_EDX` with `EDX=1`) |

All of it is behind `PLUTEX=1`: without it every build is byte for byte the same as before (the game
programs of the RAM cart, EverDrive and 32X+CD builds and PLUTONIA.WAD were compared).
