#include <stddef.h>
#include <stdint.h>
/* SELF-CONTAINED: no D32XR headers.  This loader is built with its OWN CD-boot start-up
   (cdl_crt0.s - with the 56-byte CD boot table the 32X boot ROM reads in CD mode) and its own
   linker script (cdloader.ld).  D32XR's crt0.s / linker scripts are for a cartridge: built with
   them, the SH2 started inside D32XR's cartridge start-up and never reached main() (console
   test 1: "SH2 READY FOR ISOLATED TEST: FFFF"). */
/* OpenLara CD32X OL-1: 1 = the 68000 stays in the listener (no CMD 60) and the SH2s are
   released with COMM0 = COMM4 = 0 instead of M_OK/S_OK.  0 = original D32XR behaviour. */
/* OJ-J4B DIAGNOSTICS SWITCH (with KOBO_DIAG_TEXT / KOBO_BOOT_TEXT in subcpu/main.c and
   OJ32X_DIAG_TEXT in port/plat_mars.c): 1 = the Genesis text (white start-up messages, green
   STATE codes) is switched on and drawn IN FRONT of the splash (DISPMODE bit 7, Kobo K18);
   0 = text off, the splash shows alone (OpenLara's release setting, OL-3). */
#ifndef OJ_DIAG_TEXT
#define OJ_DIAG_TEXT 0
#endif

#ifndef CDL_TARGET_OPENLARA
#define CDL_TARGET_OPENLARA 1
#endif
/* D32XR CD32X (Doom 32X Resurrection from the CD, README.md): CDL_TARGET_OPENLARA 0
   (the 68000 runs D32XR's own Genesis code: CMD 60, "M_OK" / "S_OK"), with the loading screen
   (CDL_SPLASH 1) and the 8 / 16 MB RAM cart: CDL_D32XR_PAGE = the page that holds the game's
   second 2 MB (window 1), set with CMD 68 before the copy; the Sub-CPU sets it again at CMD 60. */
#ifndef CDL_SPLASH
#define CDL_SPLASH CDL_TARGET_OPENLARA
#endif
#ifndef CDL_D32XR_PAGE
#define CDL_D32XR_PAGE 0
#endif

#define MARS_SYS_INTMSK  (*(volatile uint16_t *)0x20004000)
#define MARS_SYS_COMM0   (*(volatile uint16_t *)0x20004020)

/* ===========================================================================
 * D32XR CD32X - MILESTONE 1: THE SH2 LOADER  (sh2_main.c, master + slave SH2)
 *
 * Booted by our proven CD32X start-up (frame buffer, "_CD_").  It turns the RAM cart into
 * D32XR's cartridge ROM and then does what the 32X boot ROM does for a real cartridge:
 *   1. start-up handshake with the Sub-CPU (COMM10 0x0AAA / 0x0BBB), as in Kobo;
 *   2. CMD 38 (file 20 = D32XR.32X) + CMD 46 per 32 KB chunk -> RAM cart at offset 0 (the
 *      SH2 sees it at 0x02000000 = where D32XR expects its ROM).  Every chunk is verified by
 *      the Sub-CPU; a loading bar shows the progress;
 *   3. reads the 32X header from the cart (0x3D4: source, destination, size, entries, VBRs);
 *   4. copies a small assembly routine to the top of SDRAM (TRAMP) and parks the slave there;
 *   5. CMD 60: the Sub-CPU makes the 68000 jump to D32XR's Genesis code (0x880800);
 *   6. jumps into the routine: it copies D32XR's SDRAM part over THIS program (that is why it
 *      runs from the top of SDRAM), writes "M_OK" / "S_OK" (D32XR's 68K start-up waits for
 *      them), and starts both SH2s at D32XR's entries with their VBR and stack.
 * Status codes (COMM12, shown by the Sub-CPU as STATE:xxxx in the green text):
 *   4D01 opening the file   4D06 quick check (is it already in the cart?)   4D07 yes - copy
 *   skipped   4C00..4C3F chunk n loaded (progress)   4D02 loaded + verified   4D03 header OK   4D04 slave parked
 *   4D05 68K started -> jump.   Errors: 4DE1 file not found, 4DE2 bad chunk(s), 4DE3 not a
 *   32X ROM / bad header, 4DE4 slave did not park.
 * =========================================================================== */

#if CDL_TARGET_OPENLARA
__attribute__((used)) const char sh2_build_marker[] = "SH2-OPENLARA-CD-OL1-LOADER";
#else
__attribute__((used)) const char sh2_build_marker[] = "SH2-D32XR-CD-M1-LOADER";
#endif

void pri_vbi_handler(void) {}
#define SC_CMD_CLR       (*(volatile uint16_t *)0x2000401A)
void pri_cmd_handler(void) { SC_CMD_CLR = 0; }
void sec_cmd_handler(void) { SC_CMD_CLR = 0; }
void sec_dma1_handler(void) {}
volatile unsigned mars_pwdt_ovf_count = 0;
volatile unsigned mars_swdt_ovf_count = 0;
uint32_t _text_end;
uint32_t _data_size;
uint32_t _bss_start;
uint32_t _bss_end;
int main(void);
void _main(void) { main(); }

/* no C library (-nostdlib): our own, volatile so GCC cannot turn them into calls to themselves */
void *memset(void *d, int c, size_t n) {
    volatile uint8_t *p = (volatile uint8_t *)d;
    while (n--) *p++ = (uint8_t)c;
    return d;
}
void *memcpy(void *d, const void *s, size_t n) {
    volatile uint8_t *p = (volatile uint8_t *)d;
    const volatile uint8_t *q = (const volatile uint8_t *)s;
    while (n--) *p++ = *q++;
    return d;
}
void *memmove(void *d, const void *s, size_t n) { return memcpy(d, s, n); }

/* ---- registers ---- */
#define SC_COMM2         (*(volatile uint16_t *)0x20004022)
#define SC_COMM8_32      (*(volatile uint32_t *)0x20004028)
#define SC_COMM10        (*(volatile uint16_t *)0x2000402A)
#define SC_COMM12        (*(volatile uint16_t *)0x2000402C)   /* 16-bit: COMM14 = Sub heartbeat */
#define SC_SYS_ADAPTER_B (*(volatile uint8_t  *)0x20004000)
#define SC_VDP_DISPMODE  (*(volatile uint16_t *)0x20004100)
#define SC_VDP_FBCTL     (*(volatile uint16_t *)0x2000410A)
#define SC_CRAM          ((volatile uint16_t *)0x20004200)
#define SC_FRAMEBUFFER   ((volatile uint16_t *)0x24000000)

#define CMD_OPEN_FILE      38
#define CMD_CHUNK_TO_CART  46
#define CMD_CHUNK_COMPARE  47                /* M1c: compare a chunk, no write */
#define CMD_START_D32XR    60
#define FILE_D32XR         20
#define CHUNK_BYTES        32768
#define ROM_MAX            0x400000          /* the whole 4 MB cart */
#define CART               ((volatile uint8_t *)0x22000000)   /* cart, cache-through */

/* The hand-over routine and its parameter block live at the top of SDRAM, cache-through
   (0x26...), above D32XR's 28 KB start image and below the stacks. */
#define TRAMP_ADDR   0x2603C000u
#define INFO         ((volatile uint32_t *)0x2603DF00u)
/* INFO[0] go (slave)  [1] master entry  [2] master VBR  [3] slave entry  [4] slave VBR
   [5] park request (master -> slave)  [6] parked (slave -> master) */

static void show_status(uint16_t code) { SC_COMM12 = code; }

static void comm_pause(void) {           /* HW6 rule: never hammer a COMM register */
    volatile int k;
    for (k = 0; k < 64; k++) { }
}
static void wait_cmd(uint16_t cmd) {
    uint32_t n;
    MARS_SYS_COMM0 = cmd;
    for (n = 0; n < 2000000UL && MARS_SYS_COMM0 != 0; n++) comm_pause();
}
/* CD32X (console, 27 Oct 2026): BOUNDED.  These two were the only waits in the whole copy that could
   not end - the loading screen's, one of them twice a chunk - and on the EverDrive the load stopped in
   them with the picture frozen and no code on screen, while the same disc built with the picture off
   (LOADER_DIAG=1) loaded through and started the game.  A frame buffer that does not come back is a
   reason to go on drawing nothing, not a reason to stop loading: the copy itself asks nothing of the
   32X VDP.  The bounds are a few frames' worth of spins, far longer than a swap ever needs. */
#define FB_SPINS 2000000UL
static void take_fb(void) {
    uint32_t n;
    SC_SYS_ADAPTER_B = 0x80;
    for (n = 0; n < FB_SPINS && (MARS_SYS_INTMSK & 0x8000) == 0; n++) { }
}
static void flip_wait(void) {
    uint16_t cur = SC_VDP_FBCTL & 1;
    uint32_t n;
    SC_VDP_FBCTL = cur ^ 1;
    for (n = 0; n < FB_SPINS && (SC_VDP_FBCTL & 1) == cur; n++) { }
}

/* CDL_LOADER_CHECK (build.sh LOADER_CHECK=1, off by default): a stop is readable on the loading screen -
   the STATE code (4DEx) drawn in big white digits on a black box over the picture, in both frame buffers
   (this disc's Sub-CPU program prints no green text: KOBO_DIAG_TEXT 0), instead of a bar that just
   stops - and the ROM is checked once more right before the game starts (4DE6: it changed after its own
   check, during the preload or the record) */
#ifndef CDL_LOADER_CHECK
#define CDL_LOADER_CHECK 0
#endif
#if CDL_LOADER_CHECK && CDL_SPLASH
static int splash_on;                    /* (defined with the loading screen below) */
static const uint16_t hex35[16] = {      /* 3 x 5 digits 0-F, row by row, the top row in bits 14-12 */
    0x7B6F, 0x2C97, 0x73E7, 0x73CF, 0x5BC9, 0x79CF, 0x79EF, 0x7249,
    0x7BEF, 0x7BCF, 0x7BED, 0x6BAE, 0x7927, 0x6B6E, 0x79E7, 0x79E4 };
#define CODE_X0 122                      /* the box: 76 x 28 pixels, above the bar */
#define CODE_Y0 170
static void code_draw(uint16_t code) {
    volatile uint16_t *fb = SC_FRAMEBUFFER + 0x100;          /* the pixels, after the line table */
    int d, r, c, x, y;
    for (y = CODE_Y0; y < CODE_Y0 + 28; y++)
        for (x = CODE_X0; x < CODE_X0 + 76; x += 2) fb[y * 160 + (x >> 1)] = 0xFCFC;   /* colour 252 */
    for (d = 0; d < 4; d++) {                /* constant shifts only: no C library (__ashrsi3) */
        uint16_t g = hex35[(code >> 12) & 15], m = 0x4000;
        code = (uint16_t)(code << 4);
        for (r = 0; r < 5; r++)
            for (c = 0; c < 3; c++, m >>= 1)
                if (g & m)
                    for (y = 0; y < 4; y++)
                        for (x = 0; x < 4; x += 2)
                            fb[(CODE_Y0 + 4 + r * 4 + y) * 160 + ((CODE_X0 + 8 + d * 16 + c * 4 + x) >> 1)] = 0xFDFD;   /* 253 */
    }
}
#endif
static void halt(uint16_t code) {
    show_status(code);                   /* stays on screen as STATE:4DEx */
#if CDL_LOADER_CHECK && CDL_SPLASH
    if (splash_on) {
        int i;
        SC_CRAM[252] = 0x0000;           /* black */
        SC_CRAM[253] = 0x7FFF;           /* white */
        for (i = 0; i < 2; i++) { code_draw(code); flip_wait(); }
    }
#endif
    while (1) { }
}

/* ---- the hand-over routine (position-independent SH2 code, copied to TRAMP_ADDR) ----
   tramp_master(r4 = source in the cart, r5 = destination in SDRAM (cache-through),
                r6 = number of longs, r7 = INFO)
   tramp_slave(r4 = INFO): waits for INFO[0] == 1, then starts the slave the same way. */
extern char tramp_start[], tramp_master[], tramp_slave[], tramp_end[];
extern char tramp_mok[], tramp_sok[];
__asm__(
"        .text\n"
"        .align  2\n"
"        .global _tramp_start, _tramp_master, _tramp_slave, _tramp_end\n"
"        .global _tramp_mok, _tramp_sok\n"
"_tramp_start:\n"
"_tramp_master:\n"
"        mov.l   @r4+,r0\n"              /* copy D32XR's SDRAM image */
"        mov.l   r0,@r5\n"
"        dt      r6\n"
"        bf/s    _tramp_master\n"
"        add     #4,r5\n"
"        mov.l   tr_ccr,r1\n"            /* purge + enable the cache */
"        mov     #0x11,r0\n"
"        mov.b   r0,@r1\n"
"        mov.l   tr_comm0,r1\n"          /* what the 32X boot ROM leaves for the 68000 */
"        mov.l   tr_mok,r0\n"
"        mov.l   r0,@r1\n"               /* COMM0/2 = \"M_OK\" */
"        mov.l   tr_sok,r0\n"
"        mov.l   r0,@(4,r1)\n"           /* COMM4/6 = \"S_OK\" */
"        mov     #1,r0\n"
"        mov.l   r0,@r7\n"               /* release the slave */
"        mov.l   @(8,r7),r1\n"           /* master VBR */
"        ldc     r1,vbr\n"
"        mov.l   @(4,r1),r15\n"          /* stack = vector 1 of D32XR's table */
"        mov.l   @(4,r7),r0\n"           /* master entry */
"        jmp     @r0\n"
"        nop\n"
"_tramp_slave:\n"
"1:      mov.l   @r4,r0\n"
"        cmp/eq  #1,r0\n"
"        bf      1b\n"
"        mov.l   tr_ccr,r1\n"
"        mov     #0x11,r0\n"
"        mov.b   r0,@r1\n"
"        mov.l   @(16,r4),r1\n"          /* slave VBR */
"        ldc     r1,vbr\n"
"        mov.l   @(4,r1),r15\n"
"        mov.l   @(12,r4),r0\n"          /* slave entry */
"        jmp     @r0\n"
"        nop\n"
"        .align  2\n"
"tr_ccr:   .long   0xFFFFFE92\n"
"tr_comm0: .long   0x20004020\n"
"tr_mok:\n"
"_tramp_mok: .ascii  \"M_OK\"\n"
"tr_sok:\n"
"_tramp_sok: .ascii  \"S_OK\"\n"
"_tramp_end:\n"
);
typedef void (*tramp_m_fn)(uint32_t src, uint32_t dst, uint32_t nlongs, volatile uint32_t *info);
typedef void (*tramp_s_fn)(volatile uint32_t *info);

/* the slave: park until the master asks, then wait inside the routine at the top of SDRAM
   (this program's own code is overwritten by D32XR's start image) */
void secondary(void) {
    __asm__ __volatile__("ldc %0,sr" : : "r"(0xF0) : "memory");    /* interrupts off */
    while (INFO[5] != 0x5A5A5A5Au) { comm_pause(); }
    INFO[6] = 0x5A5A5A5Au;                                        /* parked */
    ((tramp_s_fn)(TRAMP_ADDR + (uint32_t)(tramp_slave - tramp_start)))(INFO);
    while (1) { }
}

static uint32_t rd32(uint32_t off) {     /* big-endian long from the cart */
    return ((uint32_t)CART[off] << 24) | ((uint32_t)CART[off + 1] << 16) |
           ((uint32_t)CART[off + 2] << 8) | CART[off + 3];
}

#if CDL_SPLASH
/* ---- OL-5: boot splash - the same picture + red bar as OpenLara's loading screen ----------
   IMAGE.RAW (tools/make_boot_image.py): 224 lines x 320 pixels (bytes, as the frame buffer
   holds them from byte 0x200 on) followed by the 256-entry palette.  CMD 38 file 0 opens it,
   CMD 51 copies it chunk by chunk into the frame buffer (the 68000 writes it: FM = 0).  It is
   loaded into BOTH buffers; the bar then grows in both after every ROM chunk.  No division:
   this program has no C library. */
#define CMD_CHUNK_TO_FB  51
#define SPL_FILE         0
#define SPL_W            320
#define SPL_LINES        224
#define SPL_PAL_OFS      (0x200 + SPL_W * SPL_LINES)
/* OJ-J4B: the bar sits low on the picture, between the Jazz Jackrabbit logo and the
   (C) 1994 EPIC MEGAGAMES line, clear of the turtle on the right (Splash.png measured) */
#if CDL_TARGET_OPENLARA
#define BAR_X0           56
#define BAR_X1           236
#define BAR_Y0           186
#define BAR_Y1           198
#else
/* D32XR: on the fire along the bottom of the loading screen (tools/make_splash.py) */
#define BAR_X0           60
#define BAR_X1           260
#define BAR_Y0           203
#define BAR_Y1           213
#endif
static int splash_on = 0;
static uint32_t splash_len = 0;     /* D32XR: IMAGE.RAW's length (the text strip after the palette) */

static void give_fb(void) {
    SC_SYS_ADAPTER_B = 0x00;
    while ((MARS_SYS_INTMSK & 0x8000) != 0) { }
}
static void splash_lines(void) {
    volatile uint16_t *fb = SC_FRAMEBUFFER;
    int i;
    for (i = 0; i < 256; i++)
        fb[i] = (uint16_t)(0x100 + (i < SPL_LINES ? i : SPL_LINES - 1) * (SPL_W / 2));
}
#if CDL_D32XR_PAGE
/* D32XR: only the gold part of the bar is drawn, over the picture - no white frame, no brown
   empty part: nothing shows until the copy starts (FIRST TIME), then the gold bar grows */
static int bar_on(int x, int y, int fill) {
    return y >= BAR_Y0 + 2 && y < BAR_Y1 - 2 && x >= BAR_X0 + 2 && x < BAR_X1 - 2 && x - (BAR_X0 + 2) < fill;
}
static void splash_bar(uint32_t done, uint32_t total) {
    volatile uint16_t *fb = SC_FRAMEBUFFER + 0x100;
    uint32_t acc = (uint32_t)((BAR_X1 - 2) - (BAR_X0 + 2)) * done;
    int fill = 0, x, y;
    while (total && acc >= total) { acc -= total; fill++; }       /* = inner * done / total */
    if (!fill) return;
    for (y = BAR_Y0 + 2; y < BAR_Y1 - 2; y++)
        for (x = (BAR_X0 + 2) & ~1; x < BAR_X0 + 2 + fill + 1 && x < BAR_X1; x += 2) {
            volatile uint16_t *p = &fb[y * (SPL_W / 2) + (x >> 1)];
            uint16_t v = *p;
            if (bar_on(x, y, fill)) v = (uint16_t)((v & 0x00FF) | (254 << 8));
            if (bar_on(x + 1, y, fill)) v = (uint16_t)((v & 0xFF00) | 254);
            *p = v;
        }
}
#else
static uint8_t bar_c(int x, int y, int fill) {
    if (y < BAR_Y0 + 2 || y >= BAR_Y1 - 2 || x < BAR_X0 + 2 || x >= BAR_X1 - 2) return 255;
    return (x - (BAR_X0 + 2) < fill) ? 254 : 253;
}
static void splash_bar(uint32_t done, uint32_t total) {
    volatile uint16_t *fb = SC_FRAMEBUFFER + 0x100;
    uint32_t acc = (uint32_t)((BAR_X1 - 2) - (BAR_X0 + 2)) * done;
    int fill = 0, x, y;
    while (total && acc >= total) { acc -= total; fill++; }       /* = inner * done / total */
    for (y = BAR_Y0; y < BAR_Y1; y++)
        for (x = BAR_X0; x < BAR_X1; x += 2)
            fb[y * (SPL_W / 2) + (x >> 1)] = (uint16_t)((bar_c(x, y, fill) << 8) | bar_c(x + 1, y, fill));
}
#endif
static void splash_show(void) {
    uint32_t len, c, chunks;
    int pass, i;
    SC_COMM2 = SPL_FILE;
    wait_cmd(CMD_OPEN_FILE);
    len = SC_COMM8_32;
    if ((int32_t)len < SPL_PAL_OFS - 0x200 + 512) return;     /* no IMAGE.RAW: stay black */
    splash_len = len;
    chunks = (len + CHUNK_BYTES - 1) >> 15;
    for (pass = 0; pass < 2; pass++) {
        give_fb();
        for (c = 0; c < chunks; c++) { SC_COMM2 = (uint16_t)c; wait_cmd(CMD_CHUNK_TO_FB); }
        take_fb();
        splash_lines();
        if (pass == 0) {
            const volatile uint16_t *pal =
                (const volatile uint16_t *)((volatile uint8_t *)SC_FRAMEBUFFER + SPL_PAL_OFS);
            for (i = 0; i < 256; i++) SC_CRAM[i] = pal[i];
        }
        splash_bar(0, 1);                /* OJ-J4B: the empty bar (OL-7 had removed it) */
        flip_wait();
        if (pass == 0) SC_VDP_DISPMODE = OJ_DIAG_TEXT ? 0x0081 : 0x0001;                /* 256 colours: picture shows;
                                                                   OJ-J4B: + 0x80 = the green/white
                                                                   diagnostic text in front (Kobo K18) */
    }
    splash_on = 1;
}
/* D32XR: the text line under the bar ("FIRST TIME: COPYING DOOM INTO THE RAM CART"): IMAGE.RAW
   carries it after the palette (tools/make_splash.py), so it is already in both frame buffers;
   copied to lines 214-222 of each, 16-bit accesses. Shown when the cart does not hold the game. */
#define SPL_STRIP_OFS    (SPL_PAL_OFS + 512)
#define SPL_STRIP_LINES  9
#define SPL_STRIP_Y      214
static void splash_text(int strip) {
    int i, k;
    uint32_t ofs = SPL_STRIP_OFS + (uint32_t)strip * SPL_W * SPL_STRIP_LINES;
    if (!splash_on || splash_len < ofs - 0x200 + SPL_W * SPL_STRIP_LINES) return;
    for (i = 0; i < 2; i++) {
        volatile uint16_t *src = (volatile uint16_t *)((volatile uint8_t *)SC_FRAMEBUFFER + ofs);
        volatile uint16_t *dst = (volatile uint16_t *)((volatile uint8_t *)SC_FRAMEBUFFER + 0x200 + SPL_STRIP_Y * SPL_W);
        for (k = 0; k < SPL_W * SPL_STRIP_LINES / 2; k++) dst[k] = src[k];
        flip_wait();
    }
}
static void splash_progress(uint32_t done, uint32_t total) {
    int i;
    if (!splash_on) return;
    for (i = 0; i < 2; i++) { splash_bar(done, total); flip_wait(); }
}
#elif CDL_D32XR_PAGE
/* LOADER_DIAG=1 (CDL_SPLASH 0): no loading screen - the D32XR copy still calls these two, so they are
   empty here (the build stopped at the link without them: undefined splash_text / splash_progress) */
static void splash_progress(uint32_t done, uint32_t total) { (void)done; (void)total; }
static void splash_text(int strip) { (void)strip; }
#endif

#if CDL_D32XR_PAGE
/* ===========================================================================================
 * D32XR CD32X: the 16 MB RAM cart (README.md, "The cart").
 *   page 0 + page CDL_D32XR_PAGE : the game's ROM (windows 0 and 1)
 *   page 1                       : the shared save area and the other titles' data - not touched
 *                                  (only the scratch piece 15 for the board probe and the record)
 *   pages 2-6                    : the preload (tools/make_preload.py -> preload.h): the WADs, read
 *                                  by the game from here instead of the CD
 * Every boot: the board probe, then the checksums of the ROM and of every preload file in the
 * cart; what does not match is copied from the CD with "FIRST TIME: COPYING DOOM INTO THE RAM
 * CART" under the bar; then the record "D32XR PRELOAD OK" (save piece 15 of page 1) tells the
 * game to read the preload from the cart. Status codes (COMM12): 4D10 probe, 4D11-13 the board
 * (4/8/16 MB), 4D14 checking, 4D15 copying, 4D16 record written, 4DE5 4 MB cart (stop).
 * =========================================================================================== */
#include "preload.h"
#define CART_W1 ((volatile uint32_t *)0x22200000)    /* window 1, cache-through */
#define PIECE15 0x1FF000                              /* save piece 15 in a page (window 1 offset) */

static void cart_page(int page) { SC_COMM2 = (uint16_t)page; wait_cmd(68); }

/* save piece 15 of the page in window 1: the first words from w[], the rest of the Sub-CPU's
   4 KB buffer as it is (CMD 58 per word, CMD 61) */
static void piece15_write(const uint16_t *w, int nw) {
    int k;
    for (k = 0; k < nw; k++) {
        SC_COMM2 = (uint16_t)k;
        *(volatile uint16_t *)0x20004028 = w[k];         /* COMM8 (high word) */
        wait_cmd(58);
    }
    SC_COMM2 = 15;
    wait_cmd(61);
}

/* 4, 8 or 16 (MB): markers in piece 15 of pages 1, 2 and 6, then read back. No page register:
   all three land in page 1. 8 MB: page 6 is page 2. */
static int cart_probe(void) {
    static const int pages[3] = { 1, 2, 6 };
    uint16_t w[4];
    int i;
    for (i = 0; i < 3; i++) {
        w[0] = 0x4433; w[1] = 0x3258; w[2] = (uint16_t)(0x5000 | pages[i]); w[3] = (uint16_t)~w[2];
        cart_page(pages[i]);
        piece15_write(w, 4);
    }
    cart_page(1);
    if (((volatile uint16_t *)CART_W1)[(PIECE15 >> 1) + 2] == 0x5006) return 4;
    cart_page(2);
    return ((volatile uint16_t *)CART_W1)[(PIECE15 >> 1) + 2] == 0x5002 ? 16 : 8;
}

/* the build's checksum (tools/make_preload.py) over len bytes from p (cart, cache-through) */
static uint32_t sum_add(uint32_t s, const volatile uint32_t *p, uint32_t len) {
    uint32_t n = len >> 2, k;
    for (k = 0; k < n; k++) s = ((s << 1) | (s >> 31)) + p[k];
    if (len & 3) {
        const volatile uint8_t *b = (const volatile uint8_t *)(p + n);
        for (k = 0; k < (len & 3); k++) s += b[k];
    }
    return s;
}
static uint32_t rom_sum(void) {
    uint32_t s;
    cart_page(CDL_D32XR_PAGE);
#if PL_ROM_LENGTH <= 0x200000
    /* a game image of 2 MB or less (fit_4mb.py cuts it to its used length): window 0 only - the
       second part's length would wrap around to about 4 GB */
    (void)s;
    return sum_add(0, (const volatile uint32_t *)0x22000000, PL_ROM_LENGTH);
#else
    s = sum_add(0, (const volatile uint32_t *)0x22000000, 0x200000);
    return sum_add(s, CART_W1, PL_ROM_LENGTH - 0x200000);
#endif
}
static uint32_t file_sum(int f) {
    uint32_t s = 0, done = 0, len = pl_files[f].length, lin = pl_files[f].linear;
    while (done < len) {
        uint32_t page = PL_FIRST_PAGE, off = lin + done, n;
        while (off >= PL_PAGE_USE) { off -= PL_PAGE_USE; page++; }
        n = PL_PAGE_USE - off;
        if (n > len - done) n = len - done;
        cart_page((int)page);
        s = sum_add(s, (const volatile uint32_t *)((volatile uint8_t *)CART_W1 + off), n);
        done += n;
    }
    return s;
}

/* one preload file from the CD into its place: chunk by chunk, the page changes between chunks */
static int file_copy(int f, uint32_t *done, uint32_t total) {
    uint32_t len = pl_files[f].length, lin = pl_files[f].linear, nch = (len + PL_CHUNK - 1) / PL_CHUNK, c;
    int bad = 0;
    for (c = 0; c < nch; c++) {
        uint32_t page = PL_FIRST_PAGE, off = lin + c * PL_CHUNK;
        while (off >= PL_PAGE_USE) { off -= PL_PAGE_USE; page++; }
        if (c == 0 || off == 0) {
            cart_page((int)page);
            SC_COMM8_32 = (0x200000u + off - c * PL_CHUNK) & 0x3FFFFCu;   /* where chunk 0 would go */
            SC_COMM2 = (uint16_t)(0x8000 | pl_files[f].file);
            wait_cmd(CMD_OPEN_FILE);
            if (SC_COMM8_32 != len) return 1;                            /* not on the disc */
        }
        SC_COMM2 = (uint16_t)c;
        SC_COMM12 = 0;
        wait_cmd(CMD_CHUNK_TO_CART);
        if (SC_COMM12 != 0) bad++;
        show_status((uint16_t)(0x4C00 | (c & 0xFF)));
        splash_progress(++*done, total);
    }
    return bad;
}
#endif

int main(void) {
    uint32_t len, nchunks, c, n;
    int bad = 0;
    INFO[5] = 0; INFO[6] = 0;

    /* ---- start-up: identical to the working Kobo/V80 engine ---- */
    MARS_SYS_COMM0 = 0;
    SC_COMM10 = 0x0006;
    MARS_SYS_INTMSK |= 0x0002;
    SC_COMM10 = 0x0007;
    __asm__ __volatile__("ldc %0,sr" : : "r"(0) : "memory");
    SC_COMM10 = 0x0AAA;
    while (SC_COMM10 != 0x0BBB) { }
    take_fb();
    /* NOTHING is drawn on the 32X layer: its display stays BLANK (mode 0), so the Genesis
       layer - Chilly's white boot messages and our green diagnostics - is never covered.
       (The first version drew a loading bar in 256-colour mode; in Fusion that picture hid
       all the boot text.)  Progress = the status code, shown by the Sub-CPU as STATE:. */
    SC_VDP_DISPMODE = 0x0000;
    /* Genesis text layer ON (as Kobo's set_text): CMD 52 with COMM2 = 1 makes the Sub-CPU set
       VDP register 1 = 0x8174 (display on).  Without it the status codes were not visible
       (Fusion test: black screen with only the loading bar). */
    SC_COMM2 = OJ_DIAG_TEXT;             /* OJ-J4B: Genesis text per the switch above (OL-3 had 0) */
    wait_cmd(52);
    show_status(0x4D01);
#if CDL_SPLASH
    splash_show();                       /* OL-5 */
#endif
#if CDL_D32XR_PAGE
    /* D32XR: window 1 shows the game's own page, so the copy (CMD 46) and the check (CMD 47)
       of the ROM's second 2 MB go there, and page 1 (the shared save area, other titles'
       data) is left alone. A 4 MB cart has no page register: the write does nothing. */
    SC_COMM2 = CDL_D32XR_PAGE;
    wait_cmd(68);
#endif

#if CDL_D32XR_PAGE
    {
        /* ---- 1. D32XR: the board, the ROM and the preload (see above) ---- */
        uint32_t total = 0, done = 0;
        uint8_t need[PL_COUNT + 1];
        int mb, f, all_ok = 1, rom_bad;
        uint16_t pad;
        show_status(0x4D10);
        mb = cart_probe();
        show_status((uint16_t)(mb == 4 ? 0x4D11 : mb == 8 ? 0x4D12 : 0x4D13));
        /* the 4 MB board: the shared save area (0x3F0000-0x3FFFFF) is in the game's 4 MB - only a
           game that ends before it runs there (the SIGIL disc, tools/fit_4mb.py) */
        if (mb == 4 && PL_ROM_LENGTH > 0x3F0000) { splash_text(1); halt(0x4DE5); }   /* "NEEDS THE 8 MB OR 16 MB RAM CART" */
        SC_COMM2 = FILE_D32XR;
        wait_cmd(CMD_OPEN_FILE);
        len = SC_COMM8_32;
        if ((int32_t)len <= 0) halt(0x4DE1);
        if (len != PL_ROM_LENGTH) halt(0x4DE3);
        nchunks = (len + CHUNK_BYTES - 1) >> 15;
        wait_cmd(48);                                         /* pad: A + B + C = copy everything */
        pad = (uint16_t)(SC_COMM8_32 >> 16);
        show_status(0x4D14);
        rom_bad = (pad & 0x0070) == 0x0070 || rom_sum() != PL_ROM_SUM;
        if (rom_bad) total += nchunks;
        for (f = 0; f < PL_COUNT; f++) {
            need[f] = mb == 16 && ((pad & 0x0070) == 0x0070 || file_sum(f) != pl_files[f].sum);
            if (need[f]) total += (pl_files[f].length + PL_CHUNK - 1) / PL_CHUNK;
        }
        if (total) {
            splash_text(0);                                   /* "FIRST TIME: COPYING DOOM INTO THE RAM CART" */
            show_status(0x4D15);
        }
        if (rom_bad) {
            cart_page(CDL_D32XR_PAGE);
            SC_COMM2 = FILE_D32XR;
            wait_cmd(CMD_OPEN_FILE);
            SC_COMM8_32 = len;
            for (c = 0; c < nchunks; c++) {
                SC_COMM2 = (uint16_t)c;
                SC_COMM12 = 0;
                wait_cmd(CMD_CHUNK_TO_CART);
                if (SC_COMM12 != 0) bad++;
                show_status((uint16_t)(0x4C00 | (c & 0xFF)));
                splash_progress(++done, total);
            }
            if (bad || rom_sum() != PL_ROM_SUM) halt(0x4DE2);
        }
        for (f = 0; f < PL_COUNT; f++) {
            if (need[f] && (file_copy(f, &done, total) || file_sum(f) != pl_files[f].sum)) all_ok = 0;
        }
        /* the record the game reads (save piece 15 of page 1): the preload is in the cart */
        {
            static const char rec[16] = "D32XR PRELOAD OK";
            uint16_t w[8];
            int k;
            for (k = 0; k < 8; k++)
                w[k] = (mb == 16 && all_ok && PL_COUNT) ? (uint16_t)((rec[2 * k] << 8) | rec[2 * k + 1]) : 0;
            cart_page(1);
            piece15_write(w, 8);
        }
        cart_page(CDL_D32XR_PAGE);
        show_status(0x4D16);
#if CDL_LOADER_CHECK
        if (rom_sum() != PL_ROM_SUM) halt(0x4DE6);           /* LOADER_CHECK: the ROM is still the ROM */
#endif
        goto loaded;
    }
#endif
    /* ---- 1. the ROM image into the cart ---- */
    SC_COMM2 = FILE_D32XR;
    wait_cmd(CMD_OPEN_FILE);
    len = SC_COMM8_32;
    if ((int32_t)len <= 0) halt(0x4DE1);
    if (len > ROM_MAX) len = ROM_MAX;
    SC_COMM8_32 = len;
    nchunks = (len + CHUNK_BYTES - 1) >> 15;

    /* QUICK CHECK (dev idea): is this file already in the cart from an earlier boot?  Compare
       the first, middle and last chunks (CD vs cart, nothing written).  All equal -> skip the
       copy (boot in seconds).  Any difference -> copy everything as before.  (A "force copy"
       option can come later.) */
    {
        uint32_t probe[3];
        int same = 1, i;
        probe[0] = 0; probe[1] = nchunks >> 1; probe[2] = nchunks - 1;
        show_status(0x4D06);                                         /* checking the cart */
        for (i = 0; i < 3 && same; i++) {
            SC_COMM2 = (uint16_t)probe[i];
            SC_COMM12 = 0;
            wait_cmd(CMD_CHUNK_COMPARE);
            if (SC_COMM12 != 0) same = 0;
        }
        /* OJ-J13C: quick check ON (OpenLara had it off) - the engine already in the cart from an
           earlier boot is not copied again. Holding A+B+C at power-on copies it anyway: CMD 48
           (pad -> COMM8, main.c K32), bits A 0x40 B 0x10 C 0x20. */
        if (same) {
            uint16_t pad;
            wait_cmd(48);
            pad = (uint16_t)(SC_COMM8_32 >> 16);
            if ((pad & 0x0070) != 0x0070) { show_status(0x4D07); goto loaded; }   /* already there */
        }
    }

    for (c = 0; c < nchunks; c++) {
        SC_COMM2 = (uint16_t)c;
        SC_COMM12 = 0;                   /* the Sub-CPU replies 0 = chunk verified */
        wait_cmd(CMD_CHUNK_TO_CART);
        if (SC_COMM12 != 0) bad++;
        /* progress in the green text: STATE:4C00 .. 4C3F (chunk number; 64 chunks = 2 MB) */
        show_status((uint16_t)(0x4C00 | (c & 0xFF)));
#if CDL_TARGET_OPENLARA
        splash_progress(c + 1, 2 * nchunks);  /* OJ-J4B: the bar grows with every chunk (OL-7 had it off);
                                                 OJ-J4D: to the half - the engine's data pack fills the rest */
#elif CDL_SPLASH
        splash_progress(c + 1, nchunks);      /* D32XR: the whole bar is the ROM */
#endif
    }
    if (bad) halt(0x4DE2);
loaded:
    show_status(0x4D02);

    /* ---- 2. the cartridge's 32X header (what the 32X boot ROM reads) ---- */
    if (CART[0x100] != 'S' || CART[0x101] != 'E' || CART[0x102] != 'G' || CART[0x103] != 'A') halt(0x4DE3);
    {
        uint32_t src = rd32(0x3D4), dst = rd32(0x3D8), size = rd32(0x3DC);
        uint32_t ment = rd32(0x3E0), sent = rd32(0x3E4), mvbr = rd32(0x3E8), svbr = rd32(0x3EC);
        if (size == 0 || size > 0x30000 || dst + size > 0x38000 ||
            (ment >> 24) != 0x06 || (sent >> 24) != 0x06) halt(0x4DE3);
        INFO[0] = 0; INFO[1] = ment; INFO[2] = mvbr; INFO[3] = sent; INFO[4] = svbr;
        show_status(0x4D03);

        /* ---- 3. the hand-over routine to the top of SDRAM ---- */
        {
            volatile uint8_t *t = (volatile uint8_t *)TRAMP_ADDR;
            const char *p = tramp_start;
            while (p < tramp_end) *t++ = (uint8_t)*p++;
        }
#if CDL_TARGET_OPENLARA
        *(volatile uint32_t *)(TRAMP_ADDR + (uint32_t)(tramp_mok - tramp_start)) = 0;
        *(volatile uint32_t *)(TRAMP_ADDR + (uint32_t)(tramp_sok - tramp_start)) = 0;
#endif
        /* ---- 4. park the slave there ---- */
        INFO[5] = 0x5A5A5A5Au;
        for (n = 0; n < 3000000UL && INFO[6] != 0x5A5A5A5Au; n++) comm_pause();
        if (INFO[6] != 0x5A5A5A5Au) halt(0x4DE4);
        show_status(0x4D04);

        /* ---- 5. the 68000 starts D32XR's Genesis code ---- */
        show_status(0x4D05);
#if !CDL_TARGET_OPENLARA
        wait_cmd(CMD_START_D32XR);
#endif

        /* ---- 6. copy D32XR's start image over this program and start both SH2s ---- */
        __asm__ __volatile__("ldc %0,sr" : : "r"(0xF0) : "memory");   /* interrupts off */
        ((tramp_m_fn)(TRAMP_ADDR + (uint32_t)(tramp_master - tramp_start)))(
            0x22000000u + src, 0x26000000u + dst, (size + 3) >> 2, INFO);
    }
    while (1) { }
    return 0;
}
