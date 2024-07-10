from dataclasses import dataclass

@dataclass
class Pattern:
	pattern: bytes
	caremap: bytes
	alignment: int  # stride to search with
	offset: int     # offset relative to start of pattern data

def find_pattern(data: bytes, pattern: Pattern):
	results = []
	for i in range(0, len(data) - len(pattern.pattern), pattern.alignment):
		for j, (pat, care) in enumerate(zip(pattern.pattern, pattern.caremap)):
			if data[i+j] & care != pat:
				break
		else:
			results.append(i)
	if not results:
		raise Exception("Pattern not found")
	if len(results) > 1:
		raise Exception(f"Too many results ({results})")
	return results[0] + pattern.offset

read_partition_pattern = Pattern(
	pattern=bytes.fromhex(
		"""
		00000000
		00000000
		00000000
		00000048
		00000000
		00000048
		00000048
		00000048
		00000048
		00000048
		00000048
		00000048
		00000048
		00000048
		"""
	),
	caremap = bytes.fromhex(
		"""
		ffffffff
		ffffffff
		ffffffff
		000000ff
		ffffffff
		000000ff
		000000ff
		000000ff
		000000ff
		000000ff
		000000ff
		000000ff
		000000ff
		000000ff
		"""
	),
	alignment=4,
	offset=0x4800_0000 + 0xc
)

printf_pattern = Pattern(
	pattern=bytes.fromhex("0fb4 0000 f0b5 9bb0"),
	caremap=bytes.fromhex("ffff 0000 ffff ffff"),
	alignment=2, # thumb instructions
	offset=0x4800_0000
)

handle_vboot_state_pattern = Pattern(
	pattern=bytes.fromhex("30b5 83b0 02ab 0022"),
	caremap=bytes.fromhex("ffff ffff ffff ffff"),
	alignment=2, # thumb instructions
	offset=0x4800_0000
)

lcd_printf_pattern = Pattern(
	pattern=bytes.fromhex("0fb4 30b5 c9b0"),
	caremap=bytes.fromhex("ffff ffff ffff"),
	alignment=2, # thumb instructions
	offset=0x4800_0000
)

memcpy_pattern = Pattern(
	pattern=bytes.fromhex("000052e3 00005111 1eff2f01 31402de9"),
	caremap=bytes.fromhex("ffffffff ffffffff ffffffff ffffffff"),
	alignment=4, # non-thumb
	offset=0x4800_0000
)

#path = "../../r1_backup/r1 backup/lk_a.bin"
path = "lk_b.bin"
data = open(path, "rb").read()[0x200:]

avb_hal_read_from_partition_ptr = find_pattern(data, read_partition_pattern)
print(f"avb_hal_read_from_partition_ptr = {hex(avb_hal_read_from_partition_ptr)}")

printf = find_pattern(data, printf_pattern)
print(f"printf = {hex(printf)}")

handle_vboot_state = find_pattern(data, handle_vboot_state_pattern)
print(f"handle_vboot_state = {hex(handle_vboot_state)}")

lcd_printf = find_pattern(data, lcd_printf_pattern)
print(f"lcd_printf = {hex(lcd_printf)}")

memcpy = find_pattern(data, memcpy_pattern)
print(f"memcpy = {hex(memcpy)}")
