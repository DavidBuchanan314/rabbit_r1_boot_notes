# https://github.com/u-boot/u-boot/blob/master/tools/mtk_image.h

import struct
from enum import Enum

class GFH_TYPE(Enum):
	FILE_INFO = 0
	BL_INFO = 1
	BROM_CFG = 7
	BL_SEC_KEY = 3
	ANTI_CLONE = 2
	BROM_SEC_CFG = 8

class GFH_FLASH_TYPE(Enum):
	GEN = 5
	NAND = 2

class GFH_SIG_TYPE(Enum):
	NONE = 0
	SHA256 = 1
	MAYBE_RSA_OAEP_SHA256 = 5

def parse_gfh(stream):
	magic, size, type_ = struct.unpack("<4sHH", stream.read(8))
	assert(magic == b"MMM\x01")
	body = stream.read(size - 8)
	return GFH_TYPE(type_), body

# http://gitlab.rosoperator.com/SPRD-stuff/bsp_bootloader_chipram/-/blob/3114181e8418a7e68d44f5b73f40146a20324330/include/security/sansa/bootimagesverifier_def.h
# https://github.com/ARM-software/arm-trusted-firmware/blob/4b9be5abfa8b1a7c7e00776da01768d3358e648a/drivers/renesas/common/auth/auth_mod.c#L22
# https://github.com/josefeliuf/vendor/blob/474f53c591ec2bbcf2e53ad105031ab4c5458a8c/sprd/proprietories-source/packimage_scripts/signimage/sansa/python/bin/sbu_scripts/flags_global_defines.py

# DX = Discretix
# Trivia: Discretix changed their name to Sansa Security in 2014, and in 2015 got bought by ARM
DX_CERT_MAGIC_NUMBER = 0xE291F358
class DX_CERT_TYPE(Enum):
	UNKNOWN = 0
	KEY = 1
	CONTENT = 2

def parse_dx_cert(stream):
	magic = int.from_bytes(stream.read(4), "little")
	assert(magic == DX_CERT_MAGIC_NUMBER)
	cert_version = int.from_bytes(stream.read(4), "little")
	cert_size = int.from_bytes(stream.read(4), "little")
	cert_flags = int.from_bytes(stream.read(4), "little")
	print(hex(cert_version), hex(cert_size))

	# bit 8 = RSA_ALGORITHM_RSAPSS_2048_SHA256_BIT_POS
	# bit 16 = CODE_ENCRYPTION_SUPPORT_BIT_POS
	#for i in range(17):
	#	print(f"flag {i} = {(cert_flags>>i)&1}")
	print("cert_flags", hex(cert_flags))
	
	cert_type = DX_CERT_TYPE(cert_flags >> 17)
	print("cert_type", repr(cert_type))

	cert_body = stream.read(cert_size - 16)
	print(hex(len(cert_body)), cert_body)

	# TODO...
	if cert_type == DX_CERT_TYPE.KEY:
		# rsa public parameters, sw version, pubkey hash, rsa signature
		#print(len(cert_body))
		pass

preloader = open("../dumped_bins/preloader_k65v1_64_bsp.bin", "rb")

file_info_type, file_info = parse_gfh(preloader)
assert(file_info_type == GFH_TYPE.FILE_INFO)

name, unused, file_type, flash_type, sig_type, load_addr, \
	total_size, max_size, hdr_size, sig_size, jump_offset, processed = struct.unpack("<12sIHBBIIIIIII", file_info)

flash_type = GFH_FLASH_TYPE(flash_type)
sig_type = GFH_SIG_TYPE(sig_type)

print("file_type", hex(file_type))
print("flash_type", repr(flash_type))
print("sig_type", repr(sig_type))
print("load_addr", hex(load_addr))
print("total_size", hex(total_size))
print("max_size", hex(max_size))
print("hdr_size", hex(hdr_size))
print("sig_size", hex(sig_size))
print("jump_offset", hex(jump_offset))
print("processed", hex(processed))


while preloader.tell() < hdr_size - 8:
	print(parse_gfh(preloader))

# seek to signature data
preloader.seek(total_size - sig_size)



num_certs = int.from_bytes(preloader.read(4), "little")
print("num_certs", num_certs)
for i in range(num_certs):
	parse_dx_cert(preloader)

assert(preloader.tell() == total_size)
