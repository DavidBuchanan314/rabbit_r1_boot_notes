all: main.bin

# custom linker scripts are for noobz

main.bin: main.elf
	~/.cargo/bin/elfloader --binary main.elf main.bin

main.elf: main.c entry.s
	arm-none-eabi-gcc entry.s main.c -o main.elf -nostdlib -ffreestanding -static -Wall -Wextra -Wl,--section-start=.init=0x40200000
