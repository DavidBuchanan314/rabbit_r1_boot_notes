from dataclasses import dataclass
import os

@dataclass
class Pattern:
	name: str
	pattern: bytes
	caremap: bytes
	alignment: int  # stride to search with
	offset: int     # offset relative to start of pattern data

def find_pattern(data: bytes, pattern: Pattern, baseaddr: int):
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
	return baseaddr + results[0] + pattern.offset

LK_BASE = 0x4800_0000

PATTERNS = [
	Pattern(
		name="avb_hal_read_from_partition_ptr", # part of the avbops function pointer table
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
		offset=0xc
	),
	Pattern(
		name="printf",
		pattern=bytes.fromhex("0fb4 0000 f0b5 9bb0"),
		caremap=bytes.fromhex("ffff 0000 ffff ffff"),
		alignment=2, # thumb instructions
		offset=0
	),
	Pattern(
		name="handle_vboot_state",
		pattern=bytes.fromhex("30b5 83b0 02ab 0022"),
		caremap=bytes.fromhex("ffff ffff ffff ffff"),
		alignment=2, # thumb instructions
		offset=0
	),
	Pattern(
		name="lcd_printf",
		pattern=bytes.fromhex("0fb4 30b5 c9b0"),
		caremap=bytes.fromhex("ffff ffff ffff"),
		alignment=2, # thumb instructions
		offset=0
	),
	Pattern(
		name="memcpy",
		pattern=bytes.fromhex("000052e3 00005111 1eff2f01 31402de9"),
		caremap=bytes.fromhex("ffffffff ffffffff ffffffff ffffffff"),
		alignment=4, # non-thumb
		offset=0
	)
]

#path = "../../r1_backup/r1 backup/lk_a.bin"

def test_patterns():
	LK_DIR = "../dumped_bins/lk_versions"

	for lk_name in sorted(os.listdir(LK_DIR), key=lambda x: x.split("-")[-1]):
		print()
		print(f"===== SCANNING {lk_name} =====")
		with open(f"{LK_DIR}/{lk_name}", "rb") as lk_file:
			lk_file.seek(0x200)
			data = lk_file.read()
		for pattern in PATTERNS:
			addr = find_pattern(data, pattern, LK_BASE)
			print(f"{pattern.name:<32} = {hex(addr)}")

print("""
struct pattern {
	const char *name;
	const unsigned char *pattern;
	const unsigned char *caremap;
	const size_t pattern_len;
	const size_t alignment;
	const size_t offset;
};

struct pattern PATTERNS[] = {""")

for pattern in PATTERNS:
	print("	{")
	print(f'		.name = "{pattern.name}",')
	print(f'		.pattern = {{{",".join(f"0x{x:02x}" for x in pattern.pattern)}}},')
	print(f'		.caremap = {{{",".join(f"0x{x:02x}" for x in pattern.caremap)}}},')
	print(f'		.pattern_len = {len(pattern.pattern)},')
	print(f'		.alignment = {pattern.alignment},')
	print(f'		.offset = {pattern.offset},')
	print("	},")

print("};")
