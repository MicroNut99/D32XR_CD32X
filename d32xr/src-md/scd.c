
#include <stdint.h>
#include <string.h>
#include <stdio.h>

/* CD32X: the disc booted (Mega CD mode 2), so the Mega CD sits at 0x000000 (BIOS ROM 0x000000,
   Program RAM window 0x020000, Word RAM 0x200000) instead of 0x400000 / 0x420000 / 0x600000
   as when a cartridge booted (mode 1). */
/* CD32X_MODE1 (build.sh EDCD=1): the disc is started from a cartridge (the EverDrive PRO), so the console
   stays in mode 1 and the Mega CD is where it is without a CD boot - the same addresses as a plain 32X
   cartridge build, not mode 2's. */
#if defined(CD32X) && !defined(CD32X_MODE1)
#define MCD_BASE 0x000000
#else
#define MCD_BASE 0x400000
#endif
#define MCD_WORDRAM ((char *)(MCD_BASE + 0x200000))

extern uint32_t vblank_vector;
extern uint16_t gen_lvl2;

extern uint32_t Sub_Start;
extern uint32_t Sub_End;

extern void Kos_Decomp(uint8_t *src, uint8_t *dst);

extern void write_byte(unsigned int dst, unsigned char val);
extern void write_word(unsigned int dst, unsigned short val);
extern void write_long(unsigned int dst, unsigned int val);
extern unsigned char read_byte(unsigned int src);
extern unsigned short read_word(unsigned int src);
extern unsigned int read_long(unsigned int src);

void scd_delay(void) __attribute__((section(".data"), aligned(16)));
char wait_cmd_ack(void) __attribute__((section(".data"), aligned(16)));
void wait_do_cmd(char cmd) __attribute__((section(".data"), aligned(16)));

extern void scd_init_pcm(void);
extern void bump_fm(void);
extern int mystrlen(const char* string);

void scd_delay(void)
{
    int cnt = 50;
    do {
        asm __volatile("nop");
    } while (--cnt);
}

char wait_cmd_ack(void)
{
    char ack = 0;

    do {
        scd_delay();
        bump_fm();
        ack = read_byte(0xA1200F); // wait for acknowledge byte in sub comm port
    } while (!ack);

    return ack;
}

void wait_do_cmd(char cmd)
{
    while (read_byte(0xA1200F)) {
        scd_delay(); // wait until Sub-CPU is ready to receive command
        bump_fm();
    }
    write_byte(0xA1200E, cmd); // set main comm port to command
}

int64_t scd_open_file(const char *name)
{
    int i;
    char *scdfn = MCD_WORDRAM; /* word ram on MD side (in 1M mode) */
    union {
        int32_t lo[2];
        int64_t value;
    } handle;

    for (i = 0; name[i]; i++)
        *scdfn++ = name[i];
    *scdfn = 0;

    write_long(0xA12010, 0x0C0000); /* word ram on CD side (in 1M mode) */
    wait_do_cmd('F');
    wait_cmd_ack();
    handle.lo[0] = read_long(0xA12020);
    handle.lo[1] = read_long(0xA12024);
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result

    return handle.value;
}

int64_t scd_read_directory(char *buf)
{
    int i, numwords;
    char *scdWordRam = MCD_WORDRAM; /* word ram on MD side (in 1M mode) */
    union {
        int32_t ln[2]; /* length, num entries */
        int64_t value;
    } res;

    memcpy(scdWordRam, buf, mystrlen(buf)+1);

    write_long(0xA12010, 0x0C0000); /* word ram on CD side (in 1M mode) */
    wait_do_cmd('M'); // ReadDir command
    wait_cmd_ack();
    res.ln[0] = read_long(0xA12020);
    res.ln[1] = read_long(0xA12024);
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result

    if (res.value < 0)
        return res.value;

    // use word copy so that zero-byte writes aren't ignored for the fb
#if 1
    numwords = (res.ln[0] + 1)/2;
    for (i = 0; i < numwords; i++) {
        ((volatile int16_t *)buf)[i] = ((volatile int16_t *)scdWordRam)[i];
    }
#else
    memcpy(buf, scdWordRam, res.ln[0]);
#endif

    return res.value;
}

void scd_read_sectors(void *ptr, int lba, int len, void (*wait)(void))
{
    char ack = 0;
    if (!wait)
        wait = scd_delay;

    write_long(0xA12010, (uintptr_t)ptr);
    write_long(0xA12014, lba);
    write_long(0xA12018, len);
    wait_do_cmd('H');
    do {
        // do some useful work while waiting
        wait();
        ack = read_byte(0xA1200F); // wait for acknowledge byte in sub comm port
    } while (!ack);
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result
}

void scd_switch_to_bank(int bank)
{
    write_byte(0xA12010, bank);
    wait_do_cmd('J');
    wait_cmd_ack();
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result
}

void scd_play_spcm_track(const char *name, int repeat)
{
    char *scdWordRam = MCD_WORDRAM; /* word ram on MD side (in 1M mode) */

    memcpy(scdWordRam, name, mystrlen(name)+1);
    write_long(0xA12010, 0x0C0000); /* word ram on CD side (in 1M mode) */
    write_long(0xA12014, repeat);
    wait_do_cmd('Q'); // PlaySPCMTrack command
    wait_cmd_ack();
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result
}

void scd_stop_spcm_track(void)
{
    wait_do_cmd('R'); // StopSPCMTrack command
    wait_cmd_ack();
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result
}

void scd_resume_spcm_track(void)
{
    wait_do_cmd('X'); // ResumeSPCMTrack command
    wait_cmd_ack();
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result
}

int scd_get_spcm_playback_status(void)
{
    return read_byte(0xA1202E);
}

void scd_set_volume(int volume)
{
    write_word(0xA12010, volume);
    wait_do_cmd('V'); // SetVolume command
    wait_cmd_ack();
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result
}

int64_t scd_get_disc_info(void)
{
    union {
        int16_t lo[4];
        int64_t value;
    } res;

    wait_do_cmd('D'); // GetDiscInfo command
    wait_cmd_ack();
    res.lo[0] = read_word(0xA12020); // status
    res.lo[1] = read_word(0xA12022); // first and last song
    res.lo[2] = read_word(0xA12024); // drive version, flag
    res.lo[3] = 0;
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result

    return res.value;
}

int64_t scd_get_track_info(int track)
{
    union {
        int32_t lo[2];
        int64_t value;
    } res;

    write_word(0xA12010, track);
    wait_do_cmd('T'); // GetTrackInfo command
    wait_cmd_ack();
    res.lo[0] = read_long(0xA12020); // MMSSFFTN
    res.lo[1] = read_byte(0xA12024) & 0xff; // track type
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result

    return res.value;
}

void scd_play_cdda_track(int track, int repeat)
{
    write_word(0xA12010, track);
    write_byte(0xA12012, repeat);
    wait_do_cmd('P'); // PlayTrack command
    wait_cmd_ack();
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result
}

void scd_stop_cdda_playback(void)
{
    wait_do_cmd('S'); // StopPlaying command
    wait_cmd_ack();
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result
}

void scd_toggle_cdda_pause(void)
{
    wait_do_cmd('Z'); // PauseResume command
    wait_cmd_ack();
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result
}

void scd_open_tray(void)
{
    wait_do_cmd('Y'); // OpenTray command
    wait_cmd_ack();
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result
}

int scd_stream_cd(int lba, int len)
{
    int wram_ofs;
    write_long(0xA12010, lba);
    write_long(0xA12014, len);
    wait_do_cmd('['); // StreamCD command
    wait_cmd_ack();
    wram_ofs = read_long(0xA12020);
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result
    return wram_ofs;
}

void scd_stream_cmd(char cmd)
{
    wait_do_cmd(cmd);
    wait_cmd_ack();
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result
}

uint16_t InitCD(void)
{
    char *bios;

    /*
     * Check for CD BIOS
     * When a cart is inserted in the MD, the CD hardware is mapped to
     * 0x400000 instead of 0x000000. So the BIOS ROM is at 0x400000, the
     * Program RAM bank is at 0x420000, and the Word RAM is at 0x600000.
     */
    bios = (char *)(MCD_BASE + 0x15800);
    if (memcmp(bios + 0x6D, "SEGA", 4))
    {
        bios = (char *)(MCD_BASE + 0x16000);
        if (memcmp(bios + 0x6D, "SEGA", 4))
        {
            // check for WonderMega/X'Eye
            if (memcmp(bios + 0x6D, "WONDER", 6))
            {
                bios = (char *)(MCD_BASE + 0x1AD00); // might also be 0x40D500
                // check for LaserActive
                if (memcmp(bios + 0x6D, "SEGA", 4))
                    return 0; // no CD
            }
        }
    }

    /*
     * Reset the Gate Array - this specific sequence of writes is recognized by
     * the gate array as a reset sequence, clearing the entire internal state -
     * this is needed for the LaserActive
     */
    write_word(0xA12002, 0xFF00);
    write_byte(0xA12001, 0x03);
    write_byte(0xA12001, 0x02);
    write_byte(0xA12001, 0x00);

    /*
     * Reset the Sub-CPU, request the bus
     */
    write_byte(0xA12001, 0x02);
    while (!(read_byte(0xA12001) & 2)) write_byte(0xA12001, 0x02); // wait on bus acknowledge

    /*
     * Decompress Sub-CPU BIOS to Program RAM at 0x00000
     */
    write_word(0xA12002, 0x0002); // no write-protection, bank 0, 2M mode, Word RAM assigned to Sub-CPU
    memset((char *)(MCD_BASE + 0x20000), 0, 0x20000); // clear program ram first bank - needed for the LaserActive
    Kos_Decomp((uint8_t *)bios, (uint8_t *)(MCD_BASE + 0x20000));

    /*
     * Copy Sub-CPU program to Program RAM at 0x06000
     */
    memcpy((char *)(MCD_BASE + 0x26000), (char *)&Sub_Start, (int)&Sub_End - (int)&Sub_Start);

    write_byte(0xA1200E, 0x00); // clear main comm port
    write_byte(0xA12002, 0x2A); // write-protect up to 0x05400
    write_byte(0xA12001, 0x01); // clear bus request, deassert reset - allow CD Sub-CPU to run
    while (!(read_byte(0xA12001) & 1)) write_byte(0xA12001, 0x01); // wait on Sub-CPU running

    /*
     * Set the vertical blank handler to generate Sub-CPU level 2 ints.
     * The Sub-CPU BIOS needs these in order to run.
     */
    gen_lvl2 = 1; // generate Level 2 IRQ to Sub-CPU

    /*
     * Wait for Sub-CPU program to set sub comm port indicating it is running -
     * note that unless there's something wrong with the hardware, a timeout isn't
     * needed... just loop until the Sub-CPU program responds, but 2000000 is about
     * ten times what the LaserActive needs, and the LA is the slowest unit to
     * initialize
     */
    while (read_byte(0xA1200F) != 'I')
    {
        static int timeout = 0;
        timeout++;
        if (timeout > 2000000)
        {
            gen_lvl2 = 0;
            return 0; // no CD
        }
    }

    /*
     * Wait for Sub-CPU to indicate it is ready to receive commands
     */
    while (read_byte(0xA1200F) != 0x00) ;

    scd_init_pcm();

    return 0x1; // CD ready to go!
}

#ifdef CD32X_BRAMSAVE
/* CD32X BRAMSAVE (build.sh BRAMSAVE=1; crt0.s read_sram has the whole story): the save as a file in the Sega
   CD's backup RAM, through the Sub-CPU (cd/crt.s commands '\\' and ']', cd/s_main.c) and Word RAM */
#define SRAM_BYTES 2048
uint8_t sram_shadow[SRAM_BYTES];
uint8_t sram_loaded, sram_dirty, sram_mode;   /* sram_mode 1: the cart's piece 11 is the save (no backup RAM / no room) */
extern void sram_from_cart(uint8_t *dst);
extern void sram_to_cart(const uint8_t *src);

/* the file into dst: 1 read, 0 no such file, -1 no backup RAM */
static int scd_bram_load(uint8_t *dst)
{
    int i, r;
    char *scdWordRam = MCD_WORDRAM; /* word ram on MD side (in 1M mode) */
    write_long(0xA12010, 0x0C0000); /* word ram on CD side (in 1M mode) */
    wait_do_cmd('\\');
    wait_cmd_ack();
    r = (int16_t)read_word(0xA12020);
    write_byte(0xA1200E, 0x00); // acknowledge receipt of command result
    if (r == 1)
        for (i = 0; i < SRAM_BYTES; i++) dst[i] = scdWordRam[i];
    return r;
}

/* src as the file: 1 written, 0 not (no room), -1 no backup RAM */
static int scd_bram_save(const uint8_t *src)
{
    int i, r;
    char *scdWordRam = MCD_WORDRAM;
    for (i = 0; i < SRAM_BYTES; i++) scdWordRam[i] = src[i];
    write_long(0xA12010, 0x0C0000);
    wait_do_cmd(']');
    wait_cmd_ack();
    r = (int16_t)read_word(0xA12020);
    write_byte(0xA1200E, 0x00);
    return r;
}

void sram_commit(void)
{
    if (!sram_loaded || !sram_dirty || sram_mode)
        return;
    if (scd_bram_save(sram_shadow) == 1) {
        sram_dirty = 0;
        return;
    }
    /* no backup RAM, or no room in it: the cart keeps the save, as before */
    sram_mode = 1;
    sram_to_cart(sram_shadow);
    sram_dirty = 0;
}

void sram_load(void)
{
    int i, r;
    sram_loaded = 1;
    r = scd_bram_load(sram_shadow);
    if (r == 1)
        return;
    sram_from_cart(sram_shadow);                 /* the save as it was: piece 11 of the cart */
    if (r < 0) {                                 /* no backup RAM: the cart stays the save */
        sram_mode = 1;
        return;
    }
    /* no file yet: the save moves over once when piece 11 holds DOOM's options (marssave.c: the last
       slot, 9 x 200; magic1 0xDE at +7, magic2 0xAD at +10), else it starts empty */
    if (sram_shadow[1807] == 0xDE && sram_shadow[1810] == 0xAD) {
        sram_dirty = 1;
        sram_commit();
        return;
    }
    for (i = 0; i < SRAM_BYTES; i++) sram_shadow[i] = 0;
}
#endif
