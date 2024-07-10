all: main.bin

CFLAGS := -nostdlib -ffreestanding -static -Wall -Wextra
DA_BASE := 0x40200000
LK_HOOK_BASE := 0x48380000

# custom linker scripts are for noobz
# https://github.com/gamozolabs/elfloader
%.bin: %.elf
	~/.cargo/bin/elfloader --binary $< $@

main.elf: main.c entry.s lk_hook_xxd.h
	arm-none-eabi-gcc $^ -o $@ $(CFLAGS) -Wl,--section-start=.init=$(DA_BASE) -DLK_HOOK_BASE=$(LK_HOOK_BASE)

lk_hook.elf: lk_hook.c lk_hook_entry.s
	arm-none-eabi-gcc $^ -o $@ $(CFLAGS) -N -Wl,--section-start=.init=$(LK_HOOK_BASE)

lk_hook_xxd.h: lk_hook.bin
	xxd -i lk_hook.bin > lk_hook_xxd.h
