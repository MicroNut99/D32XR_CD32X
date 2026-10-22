# D32XR CD32X

Doom 32X Resurrection v3.5 on **Sega CD + 32X + RAM cart**, booted from the disc. No flash cart is needed.

1. The disc boots.
2. The loader copies the game into the RAM cart. While it copies, the loading screen shows the DOOM logo and a progress bar.
3. D32XR starts from the cart. It is the same program as the v3.5 release, plus the CD32X changes below.

**R1 status:**
- Boots, copies the game, and the title (with the fire) and the demos run in ares.
- Not yet tested on the console.

## What you need

- Sega CD + 32X.
- The **8 MB / 16 MB RAM cart** (the 16MB-PCB-CD32X board).
  - The game's first 2 MB go in page 0.
  - The game's second 2 MB go in **page 7**.
  - Page 1, with the shared save area and the other titles' data, is left alone.
- Your **Doom 32X Resurrection v3.5 ROM** (e.g. `DCD32XF_V3.32x`). The game's data (the IWAD) is taken from it.
  - It is never committed.

## The first boot

When the cart does not hold this game yet, the loading screen says **FIRST TIME: COPYING DOOM INTO THE RAM CART**.
- The copy takes about 80 s.
- After that, the loader compares three pieces of the cart with the disc and skips the copy. The game starts about 28 s after power-on.
- Hold **A + B + C** at power-on to copy again anyway.

## Building

**Requirements** (WSL / Linux):
- The **D32XR team's devkit**: `chillys-sega-devkit-20220418`, from viciious/32XDK's releases. Unpacked at `/opt/d32xr-dk/opt/toolchains/sega`, or set `GENDEV=<folder>`. It builds the game exactly as the v3.5 release was built.
- **Chilly Willy's toolchain** in `/opt/toolchains/sega`, for the boot stack (`cd32x/`).
- `genisoimage`, plus Python 3 with Pillow.

**Your files**, in the project's `data/` folder (never committed):

| File | Use |
|---|---|
| `data/DCD32XF_V3.32x` (any `.32x`) | your v3.5 ROM: the game's data |
| `data/splash.png` | the loading screen picture (the DOOM logo); without it, a black screen with the bar |
| `data/music/Track02.wav` ... | CD audio tracks 2 and on; without them, one silent track |

**Build:**

```
cd /mnt/s/KoboPort/sega-toolchain-12.1/sega/D32XR_CD32X && \
bash build.sh 2>&1 | tee build_log.txt
```

**The disc:** `discs/D32XR_CD32X_R1/D32XR_CD32X_R1.cue` (with its `.bin`), in the project folder. Burn the `.cue`.

- `NAME=<name>` changes the disc's name.

## What changed in D32XR (all under `CD32X`)

| Where | Change |
|---|---|
| `d32xr/src-md/crt0.s` | After its work RAM clear, `_start` writes the Sega CD BIOS's RAM interrupt jumps again (vertical blank `0xFFFD06`, external `0xFFFD12`, horizontal blank `0xFFFD0C` via `0xA12006`), with the stack below them. On the console in CD mode, the 68000 takes its vectors from the BIOS. |
| `d32xr/src-md/crt0.s` | Save RAM is replaced by the cart's shared save area, **piece 11** (cart `0x3FB000`). Each access maps page 1, then page 7 again (RV = 1, SH2s parked). |
| `d32xr/src-md/scd*.c`, `vgm.c` | Mega CD mode 2 addresses: BIOS `0x000000`, Program RAM window `0x020000`, Word RAM `0x200000`. D32XR restarts the Sega CD with its own Sub-CPU program, as on a cartridge. |
| `d32xr/src-md/main.c` | No MegaSD / EverDrive probes. They write `0xA130xx`, where the RAM cart keeps its page latches. |

The boot stack (`cd32x/`) is Hurrican CD32X P2a2's, with these changes:
- The loader runs in D32XR mode, with the loading screen and window 1 on page 7.
- The Sub-CPU opens `D32XR.32X` as file 20.
- CMD 60 leaves window 1 on page 7.
