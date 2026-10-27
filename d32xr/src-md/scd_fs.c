
#include <stdint.h>
#include <string.h>
#include <stdio.h>

/* CD32X_MODE1 (build.sh EDCD=1): the disc is started from a cartridge (the EverDrive PRO), so the console
   stays in mode 1 and the Mega CD is where it is without a CD boot - the same addresses as a plain 32X
   cartridge build, not mode 2's. */
#if defined(CD32X) && !defined(CD32X_MODE1)
#define MD_WORDRAM          (void*)0x200000 /* word RAM on the MD in mega CD mode 2 (the disc booted) */
#else
#define MD_WORDRAM          (void*)0x600000 /* word RAM address on the MD in 1M mode */
#endif
#define MCD_WORDRAM         (void*)((uintptr_t)0x0C0000) /* word RAM address on the SCD in 1M mode */

#define BLOCK_SIZE 2048
#define CHUNK_SHIFT 3
#define CHUNK_BLOCKS (1<<CHUNK_SHIFT) 
#define CHUNK_SIZE (CHUNK_BLOCKS*BLOCK_SIZE)

#define DISC_BUFFER_WORDRAM_OFS (0x20000 - CHUNK_SIZE)
#define MCD_DISC_BUFFER (void*)(MCD_WORDRAM + DISC_BUFFER_WORDRAM_OFS)
#define MD_DISC_BUFFER (void*)(MD_WORDRAM + DISC_BUFFER_WORDRAM_OFS)

extern int64_t scd_open_file(const char *name);
extern void scd_read_sectors(void *ptr, int lba, int len, void (*wait)(void));
extern void bump_fm(void);

typedef struct CDFileHandle {
    int32_t  offset; // start block of file
    int32_t  length; // length of file
    int32_t  blk; // current block in buffer
    int32_t  pos; // current position in file
#ifdef CD32X
    int32_t  cart; // CD32X: the file's place in the RAM cart's preload, or -1 (read from the CD)
#endif
} CDFileHandle_t;

CDFileHandle_t gfh;

#ifdef CD32X
/*
 * CD32X: the preload. The 16 MB RAM cart keeps the WADs of cd32x_preload.h (made by the build,
 * tools/make_preload.py) in its pages 2-6; the CD loader copies them there once and checks them
 * at every boot (checksums), then writes a record into save piece 15 of page 1. When the record
 * is there, a file of the table is read from the cart instead of the CD: same bytes, no seeking.
 * Linear place L -> page 2 + L / 0x1F8000, offset L % 0x1F8000 (63 chunks of 32 KB a page).
 */
typedef struct { const char *name; int32_t length; int32_t linear; } cd32x_preload_t;
#include "cd32x_preload.h"

#define CD32X_PAGE_USE   0x1F8000
#define CD32X_FIRST_PAGE 2
#define CD32X_RECORD     "D32XR PRELOAD OK"     /* 16 bytes, piece 15 of page 1 (cart 0x3FF000) */

extern void cd32x_cart_copy(void *dst, int page, int offset, int len);   /* crt0.s */

static int8_t cd32x_cart_ok = -1;       /* -1: not checked yet, 0: read the CD, 1: the cart */
static int32_t cd32x_lba[CD32X_PRELOAD_COUNT + 1];

static int cd32x_preload_ok(void)
{
    if (cd32x_cart_ok < 0) {
        char rec[16];
        int i;
        cd32x_cart_copy(rec, 1, 0x1FF000, 16);
        cd32x_cart_ok = CD32X_PRELOAD_COUNT > 0;
        for (i = 0; i < 16; i++)
            if (rec[i] != CD32X_RECORD[i])
                cd32x_cart_ok = 0;
    }
    return cd32x_cart_ok;
}

static int cd32x_same_name(const char *a, const char *b)
{
    const char *p;
    for (p = a; *p; p++)
        if (*p == '/' || *p == '\\')
            a = p + 1;
    for (; *a && *b; a++, b++) {
        char x = *a >= 'a' && *a <= 'z' ? *a - 32 : *a;
        if (x != *b)
            return 0;
        }
    return *a == *b || (*a == ';' && !*b);
}

static void cd32x_cart_read(void *dst, int32_t linear, int32_t len)
{
    uint8_t *d = dst;
    while (len > 0) {
        int32_t page = CD32X_FIRST_PAGE, off = linear, n;
        while (off >= CD32X_PAGE_USE) {
            off -= CD32X_PAGE_USE;
            page++;
        }
        n = CD32X_PAGE_USE - off;
        if (n > len)
            n = len;
        cd32x_cart_copy(d, page, off, n);
        d += n;
        linear += n;
        len -= n;
    }
}
#endif

static uint8_t cd_Eof(CDFileHandle_t *handle)
{
    if (!handle)
        return 1;

    if (handle->pos >= handle->length)
        return 1;

    return 0;
}

static int32_t cd_Read(CDFileHandle_t *handle, void *ptr, int32_t size)
{
    int32_t pos, blk, len, read = 0;
    uint8_t *dst = ptr;

    if (!handle)
        return -1;

#ifdef CD32X
    if (handle->cart >= 0) {
        /* CD32X: the file is in the cart */
        len = handle->length - handle->pos;
        if (len > size)
            len = size;
        if (len <= 0)
            return 0;
        cd32x_cart_read(dst, cd32x_preload[handle->cart].linear + handle->pos, len);
        handle->pos += len;
        return len;
    }
#endif

    while (size > 0 && !cd_Eof(handle))
    {
        pos = handle->pos;
        len = CHUNK_SIZE - (pos & (CHUNK_SIZE-1));
        if (len > size)
            len = size;
        if (len > (handle->length - pos))
            len = (handle->length - pos);

        blk = pos / CHUNK_SIZE;
        if (blk != handle->blk)
        {
            // keep the FM music going by calling bump_fm
            scd_read_sectors((void *)MCD_DISC_BUFFER, blk*CHUNK_BLOCKS + handle->offset, CHUNK_BLOCKS, bump_fm);
            handle->blk = blk;
        }

        memcpy(dst, (char *)MD_DISC_BUFFER + (pos & (CHUNK_SIZE-1)), len);

        handle->pos += len;
        dst += len;
        read += len;
        size -= len;
    }

    return read;
}

static int32_t cd_Seek(CDFileHandle_t *handle, int32_t offset, int32_t whence)
{
    int32_t pos;

    if (!handle)
        return -1;

    pos = handle->pos;
    switch(whence)
    {
        case SEEK_CUR:
            pos += offset;
            break;
        case SEEK_SET:
            pos = offset;
            break;
        case SEEK_END:
            pos = handle->length - offset - 1;
            break;
    }
    if (pos < 0)
        handle->pos = 0;
    else if (pos > handle->length)
        handle->pos = handle->length;
    else
        handle->pos = pos;

    return handle->pos;
}

int64_t scd_open_gfile_by_name(char *name)
{
    int64_t lo;
    CDFileHandle_t *handle = &gfh;
    int length, offset;

    lo = scd_open_file(name);
    if (lo < 0)
        return lo;
    length = lo >> 32;
    offset = lo & 0x7fffffff;

    handle->offset = offset;
    handle->length = length;
    handle->blk = -1; // nothing read yet
    handle->pos = 0;
#ifdef CD32X
    handle->cart = -1;
    if (cd32x_preload_ok()) {
        int i;
        for (i = 0; i < CD32X_PRELOAD_COUNT; i++)
            if (cd32x_preload[i].length == length && cd32x_same_name(name, cd32x_preload[i].name)) {
                handle->cart = i;
                cd32x_lba[i] = offset;      /* the same file opened again by length + offset */
                break;
            }
    }
#endif
    return lo;
}

void scd_open_gfile_by_length_offset(int length, int offset)
{
    CDFileHandle_t *handle = &gfh;
    handle->offset = offset;
    handle->length = length;
    handle->blk = -1; // nothing read yet
    handle->pos = 0;
#ifdef CD32X
    handle->cart = -1;
    {
        int i;
        for (i = 0; i < CD32X_PRELOAD_COUNT; i++)
            if (cd32x_lba[i] == offset && cd32x_preload[i].length == length && offset > 0) {
                handle->cart = i;
                break;
            }
    }
#endif
}

int scd_read_gfile(void *ptr, int length)
{
    return cd_Read(&gfh, ptr, length);
}

int scd_seek_gfile(int offset, int whence)
{
    return cd_Seek(&gfh, offset, whence);
}

int scd_tell_gfile(void) {
    return gfh.offset;
}

int scd_gfile_length(void) {
    return gfh.length;
}
