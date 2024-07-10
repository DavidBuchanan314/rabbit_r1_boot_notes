.section .init

.globl _start
.extern main

_start:
	b main
