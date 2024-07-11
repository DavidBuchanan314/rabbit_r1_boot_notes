#include <stdint.h>
#include <stddef.h>

/*

we need to make verified boot go away

maybe by setting avb_flag in load_vfy_boot, to something permissive

nah, lets hook the tail end of load_vfy_boot.
let verification pass with the original boot image, *then* do the memcpy

let's hook handle_vboot_state, it gets called right at the end of load_vfy_boot, and its a nop under normal boot conditions.
it's also where the "warning" messages are normally printed - lets add our own!

fuuuuck that's actually too late. boot_post_processing() is where the kernel/dtb/ramdisk get
copied into their final resting places. we could do that ourselves, but boot_post_processing
sounds like a safer place to hook.





[1878] [BOOTKIT][LK_HOOK] Hooked avb_hal_read_from_partition(partition='seccfg', offset=0x0000000000000200, num_bytes=0x200, buffer=0xb7330000);
[1881] [BOOTKIT][LK_HOOK] Hooked avb_hal_read_from_partition(partition='vbmeta_a', offset=0x0000000000000000, num_bytes=0x10000, buffer=0xb7330814);
[1886] [BOOTKIT][LK_HOOK] Hooked avb_hal_read_from_partition(partition='boot_a', offset=0xffffffffffffffc0, num_bytes=0x40, buffer=0x4816db30);
[1889] [BOOTKIT][LK_HOOK] Hooked avb_hal_read_from_partition(partition='boot_a', offset=0x00000000015cc000, num_bytes=0x680, buffer=0xb7340e44);
[1894] [BOOTKIT][LK_HOOK] Hooked avb_hal_read_from_partition(partition='boot_a', offset=0x0000000000000000, num_bytes=0x15cc000, buffer=0xb7341af0);
[2377] [BOOTKIT][LK_HOOK] Hooked avb_hal_read_from_partition(partition='vbmeta_system_a', offset=0x0000000000000000, num_bytes=0x10000, buffer=0xb890daf8);
[2382] [BOOTKIT][LK_HOOK] Hooked avb_hal_read_from_partition(partition='vbmeta_vendor_a', offset=0x0000000000000000, num_bytes=0x10000, buffer=0xb891e13c);
[2394] [BOOTKIT][LK_HOOK] Hooked memcpy!!! 0x48b00000, 0xb7341af0, 0x15cc000

*/

// preloader offsets
int (*const pl_printf)(const char *fmt, ...) = (void*)(0x2267fc+1);
// TODO: custom uart?

#define TAG "[BOOTKIT][LK_HOOK] "

/* LK offsets */ // TODO: patchfinding!!!
int (*const lk_printf)(const char *fmt, ...) = (void*)(0x48029c0c+1);
int (*const lcd_printf)(const char *fmt, ...) = (void*)(0x4802991c+1);
//char *welcome_to_lk = (char*)0x48077cA4;
//char *orange_state = (char*)0x480858E8;
void **avb_hal_read_from_partition_ptr = (void*)0x480b6a9c;
int (*avb_hal_read_from_partition)(
	void *ops,
	const char *partition,
	uint32_t offset_lo,
	int32_t offset_hi,
	size_t num_bytes,
	void *buffer,
	size_t *out_num_read
);
unsigned int *handle_vboot_state_trampoline = (void*)0x48050f80;
unsigned int *memcpy_trampoline = (void*)0x4802aa38;

char *strcpy(char *restrict dst, const char *restrict src)
{
	char *tmp = dst;
	while((*dst++ = *src++));
	return tmp;
}

// musl
int memcmp(const void *vl, const void *vr, size_t n)
{
	const unsigned char *l=vl, *r=vr;
	for (; n && *l == *r; n--, l++, r++);
	return n ? *l-*r : 0;
}

// musl
#define SS (sizeof(size_t))
#define ALIGN (sizeof(size_t)-1)
#define ONES ((size_t)-1/UCHAR_MAX)

void *memcpy(void *dest, const void *src, size_t n)
{
	unsigned char *d = dest;
	const unsigned char *s = src;

	if (((uintptr_t)d & ALIGN) != ((uintptr_t)s & ALIGN))
		goto misaligned;

	for (; ((uintptr_t)d & ALIGN) && n; n--) *d++ = *s++;
	if (n) {
		size_t *wd = (void *)d;
		const size_t *ws = (const void *)s;

		for (; n>=SS; n-=SS) *wd++ = *ws++;
		d = (void *)wd;
		s = (const void *)ws;
misaligned:
		for (; n; n--) *d++ = *s++;
	}
	return dest;
}

void *memmove(void *dest, const void *src, size_t n)
{
	char *d = dest;
	const char *s = src;

	if (d==s) return d;
	if ((uintptr_t)s-(uintptr_t)d-n <= -2*n) return memcpy(d, s, n);

	if (d<s) {
		for (; n; n--) *d++ = *s++;
	} else {
		while (n) n--, d[n] = s[n];
	}

	return dest;
}

void *memcpy_hook(void *dest, const void *src, size_t n)
{
	if (dest == (void*)0x48B00000 /* && n == 0x2000000*/) {
		lk_printf(TAG "Hooked memcpy!!! 0x%x, 0x%x, 0x%x\n", dest, src, n);
		for (int i=0; i<8; i++) {
			lk_printf(TAG "src 0x%x: 0x%x\n", (uint32_t)src+i*4, *(((uint32_t*)src)+i));
		}
		for (int i=0; i<8; i++) {
			lk_printf(TAG "dst 0x%x: 0x%x\n", (uint32_t)dest+i*4, *(((uint32_t*)dest)+i));
		}
		return dest; // don't actually copy anything
	}
	return memmove(dest, src, n); // for some reason it fails when we use memcpy?
}

int handle_vboot_state(void)
{
	lk_printf(TAG "Hooked handle_vboot_state()!!!\n");
	lcd_printf("Congratulations, you are very cool!\n\n");
	//memcpy((void*)0xb734081c, (void*)0xbdf30000, 0x2000000);
	return 0;
}

// https://android.googlesource.com/platform/external/avb/+/master/libavb/avb_ops.h#112
int hook_avb_hal_read_from_partition(
	void *ops,
	const char *partition,
	uint32_t offset_lo,
	int32_t offset_hi,
	size_t num_bytes,
	void *buffer,
	size_t *out_num_read
) {
	// XXX: does this printf support %lx?
	lk_printf(TAG "Hooked avb_hal_read_from_partition(partition='%s', offset=0x%08x%08x, num_bytes=0x%x, buffer=0x%x);\n", partition, offset_hi, offset_lo, num_bytes, buffer);
	// [1797] [BOOTKIT][LK_HOOK] Hooked avb_hal_read_from_partition(partition='boot_a', offset=0 0, num_bytes=0x2000000, buffer=0xb734081c);

#if 0
	if (memcmp(partition, "boot_", 5) == 0) {
		lk_printf(TAG "Substituting boot image!!!\n");

		/*lk_printf(TAG "Mapping the buffer we loaded earlier...\n");
		// TODO

		lk_printf(TAG "Doing the memcpy...\n");
		memcpy(buffer, (void*)0x40280000, num_bytes); // ah fuck, this doesn't work because that memory isn't mapped yet. duhdoi. can we map it ourselves???

		lk_printf(TAG "Unmapping the buffer again...\n");
		// TODO*/

		// orrrr we can just pre-load it at the right offset, then loading is a nop
		memcpy(buffer, (void*)0xbdf30000, num_bytes);

		*out_num_read = num_bytes;

		return 0; // AVB_IO_RESULT_OK
	}
#endif
	if (memcmp(partition, "boot_", 5) == 0) {
		lk_printf(TAG "Copying image...\n");
		memcpy((void*)0x48B00000, (void*)0xbdf30000, 0x2000000);
	}

	return avb_hal_read_from_partition(ops, partition, offset_lo, offset_hi, num_bytes, buffer, out_num_read);
}

void main(void)
{
	pl_printf(TAG "Installing lk patches...\n");

	//strcpy(welcome_to_lk, "HACKED LK\n\n");
	//strcpy(orange_state, "HACKED STATE\n\n");

	avb_hal_read_from_partition = *avb_hal_read_from_partition_ptr;
	pl_printf(TAG "Original avb_hal_read_from_partition @ 0x%x\n", avb_hal_read_from_partition);
	*avb_hal_read_from_partition_ptr = hook_avb_hal_read_from_partition;

	handle_vboot_state_trampoline[0] = 0x47184b00; // ldr r3, [pc, #0];  bx r3
	handle_vboot_state_trampoline[1] = (unsigned int)handle_vboot_state;

	// nb: memcpy is not thumb mode
	memcpy_trampoline[0] = 0xe51ff004; // ldr   pc, [pc, #-4]
	memcpy_trampoline[1] = (unsigned int)memcpy_hook;

	pl_printf(TAG "Done installing lk patches\n");
}
