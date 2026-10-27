ifdef GENDEV
ROOTDIR = $(GENDEV)
else
ROOTDIR = /opt/toolchains/sega
endif

LDSCRIPTSDIR = $(ROOTDIR)/ldscripts

LIBPATH = -L$(ROOTDIR)/m68k-elf/lib -L$(ROOTDIR)/m68k-elf/lib/gcc/m68k-elf/12.1.0 -L$(ROOTDIR)/m68k-elf/m68k-elf/lib
INCPATH = -I$. -I$(ROOTDIR)/m68k-elf/include -I$(ROOTDIR)/m68k-elf/m68k-elf/include -I../liblzss

HWCCFLAGS = -m68000 -Wall -O1 -c -fomit-frame-pointer -fno-lto
CCFLAGS = -m68000 -Wall -Os -c -fomit-frame-pointer -flto -DUSE_SCD_IN_RAM
ASFLAGS = -m68000 --register-prefix-optional
ifdef ENABLE_SSF_MAPPER
HWCCFLAGS += -DENABLE_SSF_MAPPER
CCFLAGS += -DENABLE_SSF_MAPPER
ASFLAGS += --defsym ENABLE_SSF_MAPPER=1
endif
# CD32X=1: Mega CD mode 2 (the disc booted, the game runs from the RAM cart)
ifdef CD32X
HWCCFLAGS += -DCD32X
CCFLAGS += -DCD32X
ASFLAGS += --defsym CD32X=1
endif
# CD32X_ED=1: the Mega EverDrive PRO as the cart (crt0.s: its window registers, the write bit);
# CD32X_PAGE=<n>: the game's page in window 1 (7; 1 on the EverDrive)
ifdef CD32X_ED
ASFLAGS += --defsym CD32X_ED=1
endif
ifdef CD32X_PAGE
ASFLAGS += --defsym CD32X_PAGE=$(CD32X_PAGE)
endif
# CD32X_MODE1=1 (build.sh EDCD=1): the disc is started from the EverDrive PRO, so the console stays in
# cartridge mode ("mode 1") and the map is the mirror of a CD boot's - the Mega CD at 0x400000 (Word RAM
# 0x600000) and the cart at 0x000000.  The game's own 68000 code addresses both directly (scd*.c, vgm.c,
# crt0.s), so that disc needs its own ROM.  Without it the file list comes back empty on the EverDrive.
ifdef CD32X_MODE1
HWCCFLAGS += -DCD32X_MODE1
CCFLAGS += -DCD32X_MODE1
ASFLAGS += --defsym CD32X_MODE1=1
endif
LINKFLAGS = -T $(LDSCRIPTSDIR)/mars-md.ld -Wl,-Map=output.map -nostdlib -Os -flto

PREFIX = $(ROOTDIR)/m68k-elf/bin/m68k-elf-
CC = $(PREFIX)gcc
AS = $(PREFIX)as
LD = $(PREFIX)ld
OBJC = $(PREFIX)objcopy

ASMZ80 = $(ROOTDIR)/bin/zasm
FLAGSZ80 = -bv2 -uwy

DD = dd
RM = rm -f

TARGET = m68k
LIBS = $(LIBPATH) -lc -lgcc -lnosys
OBJS = crt0.o everdrive.o main.o kos.o cd.o lzss.o megasd.o vgm.o zfiles.o scd.o scd_pcm.o scd_fs.o scd_roq.o
# CD32X: no MegaSD / EverDrive code (never probed on the RAM cart, see main.c): the space the
# title fire needs to fit the 4 MB cart (crt0.s keeps three stubs for the CD music calls)
ifdef CD32X
OBJS := $(filter-out megasd.o everdrive.o,$(OBJS))
endif

all: $(TARGET).bin

$(TARGET).bin: $(TARGET).elf
	$(OBJC) -O binary $< $(TARGET).bin

$(TARGET).elf: $(OBJS)
	$(CC) $(LINKFLAGS) $(OBJS) $(LIBS) -o $(TARGET).elf

zfiles.o: z80_vgm.o80

%.o80: %.s80
	$(ASMZ80) $(FLAGSZ80) -o $@ $<

main.o: main.c
	$(CC) $(HWCCFLAGS) $(INCPATH) $< -o $@

megasd.o: megasd.c
	$(CC) $(HWCCFLAGS) $(INCPATH) $< -o $@

everdrive.o: everdrive.c
	$(CC) $(HWCCFLAGS) $(INCPATH) $< -o $@

cd.bin:
	make -C cd

cd.o: cd.s cd.bin

%.o: %.c
	$(CC) $(CCFLAGS) $(INCPATH) $< -o $@

%.o: ../liblzss/%.c
	$(CC) $(CCFLAGS) $(INCPATH) $< -o $@

%.o: %.s
	$(AS) $(ASFLAGS) $(INCPATH) $< -o $@

clean:
	make clean -C cd
	$(RM) *.o *.o80 *.bin *.elf output.map

