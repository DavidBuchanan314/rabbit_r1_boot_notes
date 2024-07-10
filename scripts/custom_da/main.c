/*
This code gets loaded as a DA image at address 0x4020_0000

We continue execution of the normal Preloader boot process, but hook it right
before it jumps to LK. We use this opportunity to patch LK before it executes.

*/

#define TAG "[BOOTKIT] "

/* Preloader offsets */
int (*const printf)(const char *fmt, ...) = (void*)(0x2267fc+1);
//void (*const putchar)(int) = (void*)(0x2296b4+1);
void (*const bldr_jump64)(unsigned int, unsigned int, unsigned int) = (void*)(0x21ce18+1);
unsigned int *const trambopoline = (void*)0x21d230; // where bldr_jump64 would normally get called from

/* LK offsets */ // TODO: patchfinding!!!
char *welcome_to_lk = (char*)0x48077cA4;
char *orange_state = (char*)0x480858E8;

extern void continue_preloader_main(void);

char *strcpy(char *restrict dst, const char *restrict src)
{
	char *tmp = dst;
	while((*dst++ = *src++));
	return tmp;
}

void hook_bldr_jump64(unsigned int addr, unsigned int arg1, unsigned int arg2)
{
	printf(TAG "Hooked bldr_jump64(addr=0x%x, arg1=0x%x, arg2=0x%x);\n", addr, arg1, arg2);

	unsigned int *ptr = (void*)0x48000000;
	for (int i=0; i<8; i++) {
		printf("%x -> %x\n", &ptr[i], ptr[i]);
	}

	// make our presence known
	strcpy(welcome_to_lk, "HACKED LK\n\n");
	strcpy(orange_state, "HACKED STATE\n\n");

	printf(TAG "Calling bldr_jump64 for real...");
	bldr_jump64(addr, arg1, arg2);
	// unreachable...
}

void main(void)
{
	printf(TAG "Hello from custom DA image!\n");
	printf(TAG "Installing bldr_jump64 hook...\n");

	trambopoline[0] = 0x47184b00; // ldr r3, [pc, #0];  bx r3
	trambopoline[1] = (unsigned int)hook_bldr_jump64;

	printf(TAG "Continuing Preloader main()\n");
	continue_preloader_main();
	// unreachable...
}
