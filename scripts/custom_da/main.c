/*
This code gets loaded as a DA image at address 0x4020_0000

We continue execution of the normal Preloader boot process, but hook it right
before it jumps to LK. We use this opportunity to patch LK before it executes.


notes on trying to patch boot image:

avb_slot_verify.c: load_full_partition

avb_hal_read_from_partition
TODO: check if "preloading" is supported (it isn't)

we can hook avb_hal_read_from_partition in the avbops table (hopefully we can patchfind it, too)


#define DRAM_PHY_ADDR   0x40000000

#define RIL_SIZE 0

#define CFG_RAMDISK_LOAD_ADDR           (DRAM_PHY_ADDR + 0x4000000)
#define CFG_BOOTIMG_LOAD_ADDR           (DRAM_PHY_ADDR + 0x8000)
#define CFG_BOOTARGS_ADDR               (DRAM_PHY_ADDR + 0x100)


having trouble with hooking, fortunately we get exception info - data aborts
at our hook entrypoint. I guess there's memory protection going on?

I think LK occupies 0x48000000 - 0x48400000

[3121] mblock_create mblock start: 0xb7330000 size: 0x8c00000 name: avb

[8733] mblock_create mblock start: 0x47880000 size: 0x80000 name: dtb_kernel_addr_mb
[8734] mblock_create mblock start: 0x40080000 size: 0x7800000 name: kernel_addr_mb
[8735] mblock_create mblock start: 0x51b00000 size: 0x4000000 name: ramdisk_addr_mb
[8736] mblock_create mblock start: 0x48000000 size: 0x400000 name: lk_addr_mb
[8737] mblock_create mblock start: 0x48b00000 size: 0x8000000 name: scratch_addr_mb
[8738] mblock_create mblock start: 0xb3330000 size: 0x4000000 name: vendorboot_work_buf
[8740] mblock_create mblock start: 0x7dfe0000 size: 0x1000000 name: logo_db_addr_pa
[8741] mblock_create mblock start: 0x7deb0000 size: 0x12c000 name: display-others_logo_fb-addr
[8742] mblock_create mblock start: 0x47dd0000 size: 0x200000 name: pl-bootarg

I guess we can dump stuff at 0x40080000 and memcpy to where it's needed later

ok, we need to write some code to receive data from USB into memory

*/

#include <stdint.h>
#include <stddef.h>

#define TAG "[BOOTKIT] "

/* Preloader offsets */
int (*const printf)(const char *fmt, ...) = (void*)(0x2267fc+1);
//void (*const putchar)(int) = (void*)(0x2296b4+1);
void (*const bldr_jump64)(unsigned int, unsigned int, unsigned int) = (void*)(0x21ce18+1);
unsigned int *const trambopoline = (void*)0x21d230; // where bldr_jump64 would normally get called from

struct comport_ops {
    int (*send)(void *buf, uint32_t len);
    int (*recv)(void *buf, uint32_t len, uint32_t timeout);
};

struct bldr_comport {
    uint32_t type;
    uint32_t timeout;
    struct comport_ops *ops;
};

struct bldr_comport **comport = (void*)0x10963c; // also preloader offset

#include "lk_hook_xxd.h"
#ifndef LK_HOOK_BASE
// make intellisense shut up (it's defined in the makefile)
#define LK_HOOK_BASE 0
#endif

void (*const lk_hook_main)(void) = (void*)LK_HOOK_BASE;

extern void continue_preloader_main(void);

static int usbdl_get_dword(uint32_t *dword)
{
	uint32_t result = 0;
	int ret = (*comport)->ops->recv(&result, sizeof(result), 0);
	if (ret == 0) {
		*dword = __builtin_bswap32(result);
	}
	return ret;
}

static int usbdl_put_dword(uint32_t dword)
{
	uint32_t swapped = __builtin_bswap32(dword);
	return (*comport)->ops->send(&swapped, 4);
}


void *memcpy(void *dest, void *src, size_t n)
{
	unsigned char *d=dest, *s=src;
	for (size_t i=0; i<n; i++) {
		d[i] = s[i];
	}
	return dest;
}

void hook_bldr_jump64(unsigned int addr, unsigned int arg1, unsigned int arg2)
{
	printf(TAG "Hooked bldr_jump64(addr=0x%x, arg1=0x%x, arg2=0x%x);\n", addr, arg1, arg2);

	printf(TAG "Relocating lk_hook...\n");
	memcpy((void*)LK_HOOK_BASE, lk_hook_bin, lk_hook_bin_len);
	printf(TAG "Calling lk_hook main...\n");
	lk_hook_main(); // TODO: barrier / cache flush???

	printf(TAG "Calling bldr_jump64 for real...\n");
	bldr_jump64(addr, arg1, arg2);
	// unreachable...
}

void main(void)
{
	printf(TAG "Hello from custom DA image!\n");

	// TODO: read in some data over usb
	uint32_t hello;
	usbdl_get_dword(&hello);
	usbdl_put_dword(hello);

	printf(TAG "Received hello value 0x%x from USB\n", hello);
	if (hello != 0xdeadbeef) {
		printf(TAG "Unexpected hello value!\n");
		while(1);// panic! TODO: something else?
	}

	uint32_t boot_image_len;
	usbdl_get_dword(&boot_image_len);
	usbdl_put_dword(boot_image_len);

	printf(TAG "About to read 0x%x bytes of boot image over USB...\n", boot_image_len);

	if (boot_image_len) {
		int res = (*comport)->ops->recv((void*)0xbdf30000, boot_image_len, 0);
		//int res = (*comport)->ops->recv((void*)0x48B00000, boot_image_len, 0);
		printf(TAG "res: %d\n", res);

		// TODO: respond with checksum
		usbdl_get_dword(&hello);
		usbdl_put_dword(hello);

		printf(TAG "Received hello value 0x%x from USB\n", hello);
	}

	printf(TAG "Installing bldr_jump64 hook...\n");

	trambopoline[0] = 0x47184b00; // ldr r3, [pc, #0];  bx r3
	trambopoline[1] = (unsigned int)hook_bldr_jump64;

	printf(TAG "Continuing Preloader main()\n");
	continue_preloader_main();
	// unreachable...
}
