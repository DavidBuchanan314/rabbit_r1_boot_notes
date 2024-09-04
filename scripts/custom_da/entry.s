.section .init

.globl _start
.globl continue_preloader_main
.extern main
.extern printf

_start:
	// no need to init a stack, we can reuse the existing sp
	b main

ret0:
	mov r0, #0
	bx lr

// restores the necessary local variables to continue execution of preloader main()
continue_preloader_main:
	ldr r11, =ret0
	ldr r10, =0x1097cc
	ldr r9, =printf
	ldr r9, [r9]
	ldr pc, =(0x21d0f4+1)
