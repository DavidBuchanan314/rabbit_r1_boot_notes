#include <stdint.h>
#include <stddef.h>

// preloader offsets
int (*const pl_printf)(const char *fmt, ...) = (void*)(0x2267fc+1);
// TODO: custom uart?

#define TAG "[BOOTKIT][LK_HOOK] "

/* LK offsets */ // TODO: patchfinding!!!
int (*const lk_printf)(const char *fmt, ...) = (void*)(0x48029c0c+1);
char *welcome_to_lk = (char*)0x48077cA4;
char *orange_state = (char*)0x480858E8;
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

	if (memcmp(partition, "boot_", 5) == 0) {
		lk_printf(TAG "Substituting boot image!!!\n");

		/*lk_printf(TAG "Mapping the buffer we loaded earlier...\n");
		// TODO

		lk_printf(TAG "Doing the memcpy...\n");
		memcpy(buffer, (void*)0x40280000, num_bytes); // ah fuck, this doesn't work because that memory isn't mapped yet. duhdoi. can we map it ourselves???

		lk_printf(TAG "Unmapping the buffer again...\n");
		// TODO*/

		// orrrr we can just pre-load it at the right offset, then loading is a nop
		*out_num_read = num_bytes;

		return 0; // AVB_IO_RESULT_OK
	}

	return avb_hal_read_from_partition(ops, partition, offset_lo, offset_hi, num_bytes, buffer, out_num_read);
}

void main(void)
{
	pl_printf(TAG "Installing lk patches\n");

	strcpy(welcome_to_lk, "HACKED LK\n\n");
	strcpy(orange_state, "HACKED STATE\n\n");

	avb_hal_read_from_partition = *avb_hal_read_from_partition_ptr;
	pl_printf(TAG "Original avb_hal_read_from_partition @ 0x%x\n", avb_hal_read_from_partition);
	*avb_hal_read_from_partition_ptr = hook_avb_hal_read_from_partition;
}
