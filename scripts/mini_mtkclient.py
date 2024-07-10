"""
mktclient (https://github.com/bkerler/mtkclient) is an awesome tool, with many
features, and as a result it has a fair bit of complexity.

In order to understand it better, I'm writing this standalone script specifically
for the mk6765/Rabbit R1.

Once I've understood everything, I'll have a think about porting it to WebUSB!
"""

import usb
import time
from typing import List
from tqdm import tqdm

def do_patch(image: bytearray, find, replace, name):
	assert(len(find) == len(replace))
	print(image.count(find))
	assert(image.count(find) == 1)
	print("Patching:", name)
	offset = image.index(find)
	replacement = replace
	image[offset:offset+len(replacement)] = replacement

class R1Exploit():
	PRELOADER_VID = 0x0e8d
	PRELOADER_PID = 0x2000

	XMAGIC = b"\xef\xee\xee\xfe"

	def __init__(self, brom=False):
		self.brom = brom
		if brom:
			self.PRELOADER_PID = 0x0003
		self.connect()
		self.handshake()

		hwcode = self.cmd_get_hw_code()
		print("hwcode:", hex(hwcode))

		assert(hwcode == 0x7660000)

		print("Disabling wdt...")
		self.cmd_write32(0x1000_7000, [0x2200_0064])

		preloader = bytearray(open("../dumped_bins/preloader_k65v1_64_bsp.bin", "rb").read()[0xf0:])
		lk = bytearray(open("../dumped_bins/lk.bin", "rb").read()[0x200:0xB7440] + preloader[-0x100:])

		do_patch(
			preloader,
			bytes.fromhex("28 b9  c5 48  01 f0 c3 fd"),
			bytes.fromhex("05 e0  c5 48  01 f0 c3 fd"),
			"preloader: don't disable logging"
		)

		# patch 2: don't bother loading lk from emmc
		#do_patch(
		#	preloader,
		#	bytes.fromhex("ff f7 97 fc   08 b1   06 46"),
		#	bytes.fromhex("4f f0 00 00   08 b1   06 46"),
		#	"preloader: don't load lk from emmc"
		#)

		# patch 3: make a noticeable change to lk
		do_patch(
			lk,
			b"welcome to lk",
			b"welcome patch",
			"lk: welcome message"
		)

		if self.brom:
			# load preloader into SRAM
			self.cmd_send_da(0x20_1000, len(preloader), 0x100, preloader)

			print("Jumping to preloader.")
			self.cmd_jump_da(0x20_1000)

		else:
			# load LK into DRAM
			lk = open("./custom_da/main.bin", "rb").read() + bytes(0x100)
			self.cmd_send_da(0x4020_0000, len(lk), 0x100, lk)
			self.cmd_jump_da(0x4020_0000)

			time.sleep(0.1)

			print("Trying to talk to DA...")


			# start talking to our custom DA
			self.echo(0xdeadbeef)
			print("It worked!!!")

			bootimg = open("../../my_dumps/boot_a3_uart.bin", "rb").read()
			self.echo(len(bootimg))

			print(f"Sending {len(bootimg)} bytes of bootimg...")

			with tqdm(total=len(bootimg), unit="B", unit_scale=True, unit_divisor=1024) as pbar:
				bytestowrite = len(bootimg)
				pos = 0
				while bytestowrite > 0:
					_sz = min(bytestowrite, 0x2000)
					self.write(bootimg[pos:pos + _sz])
					bytestowrite -= _sz
					pos += _sz
					pbar.update(_sz)

			time.sleep(0.5)

			self.echo(0xdeadbeef)
			print("It worked!!!")

			"""
			Problem: My device has CFG_DA_RAM_ADDR = 0x40200000
			which means it only accepts images there.

			Also, maximum DA length is 0x400000 (4MB)

			oh wait this is Preloader we can just patch it lmao

			GZ is 2680304 bytes (~2.7MB)
			LK is 750656 bytes (~0.7MB)
			TEE is a mere 0x22686 bytes (~0.14MB)

			so, we build a custom DA image that memcpy's the images into place
			if we can do this all without patching Preloader then we don't
			need to get people into BROM mode, and everything works with webusb.

			If we're going the custom DA route, maybe I could write one that loads
			everything from disk and patchfinds - I think mktclient has homebrew DA bins.
			"""

		#self.cmd_jump_da(0x21d0ee+1)

		return
		print("Sending da1...")
		self.cmd_send_da(0x20_0000, 0x3_9f98, 0x100, open("da1.bin", "rb").read())

		print("Sent da1, jumping...")
		self.cmd_jump_da(0x20_0000)

		sync = self.read(1)
		assert(sync == b"\xc0")

		self.xsend(b"SYNC")

		self.xsend(0x010100) # SETUP_ENVIRONMENT
		self.xsend(b"\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
		assert(self.xstatus() == 0)

		self.xsend(0x010101) # SETUP_HW_INIT_PARAMS
		self.xsend(b"\x00\x00\x00\x00")
		assert(self.xstatus() == 0)
		
		assert(self.xstatus().to_bytes(4, "little") == b"SYNC")

		print("DA sync success.")

		print("Sending da2...")
		self.boot_to(0x4000_0000, open("da2.bin", "rb").read())


	def connect(self) -> None:
		"""
		Wait for a MT6765 to appear in Preloader mode, connect to the USB device,
		and find the CDC endpoints.
		"""

		print("Waiting for device...", end="")

		while True:
			self.dev = usb.core.find(idVendor=self.PRELOADER_VID, idProduct=self.PRELOADER_PID)
			print(".", end="", flush=True)
			if type(self.dev) is usb.core.Device:
				break
			time.sleep(0.1) # seems like there's about a 4 second window

		#print(self.dev)
		print()
		print("Found:", self.dev.product)

		# seems unnecessary on my machine
		#dev.set_configuration()

		dev_config = self.dev.get_active_configuration()
		if self.brom:
			interface = dev_config[(1,0)] # brom
		else:
			interface = dev_config[(0,0)] # preloader

		# match the first OUT endpoint
		self.ep_out = usb.util.find_descriptor(
			interface,
			custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
		)
		assert(type(self.ep_out) is usb.core.Endpoint)

		# match the first IN endpoint
		self.ep_in = usb.util.find_descriptor(
			interface,
			custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
		)
		assert(type(self.ep_in) is usb.core.Endpoint)

		if self.dev.is_kernel_driver_active(0):
			self.dev.detach_kernel_driver(0)


	def handshake(self):
		maxinsize = self.ep_in.wMaxPacketSize
		startcmd = b"\xa0\x0a\x50\x05"
		print("Trying to handshake...")
		i = 0
		num_tries = 0
		while i < len(startcmd):
			if self.ep_out.write(startcmd[i:i+1]):
				if self.ep_in.read(maxinsize)[-1] ^ startcmd[i] == 0xff:
					i += 1
				else:
					i = 0
			num_tries += 1
			if num_tries > 100:
				raise Exception("Handshake failed")
		
		print("Handshake complete!")
	
	def write(self, data): # TODO chunk large writes
		i = 0
		while i < len(data):
			res = self.ep_out.write(data[i:i+64])
			if res < 0:
				print("res", res)
			else:
				i += res
	
	def read(self, length) -> bytes:
		res = b""
		while len(res) < length:
			res += self.ep_in.read(length - len(res))
		return res

	def echo(self, data: int | bytes):
		if type(data) is int:
			data = data.to_bytes(4)
		self.write(data)
		res = self.read(len(data))
		assert(data == res)

	def cmd_get_hw_code(self) -> int:
		self.echo(b"\xfd") # GET_HW_CODE
		return int.from_bytes(self.read(4))

	def cmd_write32(self, addr: int, values: List[int]):
		self.echo(b"\xd4") # WRITE32
		self.echo(addr.to_bytes(4))
		self.echo(len(values))
		status = int.from_bytes(self.read(2))
		assert(status <= 3)
		for value in values:
			self.echo(value.to_bytes(4))
		status2 = int.from_bytes(self.read(2))
		assert(status2 <= 0xff)

	@staticmethod
	def prepare_data(data, sigdata=b"", maxsize=0):
		gen_chksum = 0
		data = (data[:maxsize] + sigdata)
		if len(data + sigdata) % 2 != 0:
			data += b"\x00"
		for x in range(0, len(data), 2):
			gen_chksum ^= int.from_bytes(data[x:x+2], "little")
		if len(data) & 1 != 0:
			gen_chksum ^= data[-1:]
		return gen_chksum, data

	def cmd_send_da(self, address, size, sig_len, dadata):
		gen_chksum, data = self.prepare_data(dadata[:-sig_len], dadata[-sig_len:], size)
		self.echo(b"\xd7") # SEND_DA
		self.echo(address)
		self.echo(len(data))
		self.echo(sig_len)
		status = int.from_bytes(self.read(2))
		assert(status <= 0xff)

		bytestowrite = len(data)
		pos = 0
		while bytestowrite > 0:
			_sz = min(bytestowrite, 64)
			self.write(data[pos:pos + _sz])
			bytestowrite -= _sz
			pos += _sz
		
		self.write(b"")
		time.sleep(0.035)

		checksum = int.from_bytes(self.read(2))
		status = int.from_bytes(self.read(2))

		#print(hex(checksum), hex(gen_chksum))
		assert(checksum == gen_chksum)
		assert(status <= 0xff)
	
	def cmd_jump_da(self, address):
		self.echo(b"\xd5") # JUMP_DA
		self.echo(address)
		status = int.from_bytes(self.read(2))
		assert(status == 0)
	
	def xsend(self, data: int | bytes):
		if type(data) is int:
			data = data.to_bytes(4, "little")

		hdr = self.XMAGIC + b"\x01\x00\x00\x00" + len(data).to_bytes(4, "little")
		self.write(hdr)
		self.write(data)

	def xstatus(self):
		hdr = self.read(12)
		assert(hdr.startswith(self.XMAGIC))
		length = int.from_bytes(hdr[-4:], "little")
		body = self.read(length)
		if length <= 4:
			return int.from_bytes(body, "little")
		else:
			return [int.from_bytes(body[i:i+4], "little") for i in range(0, length, 4)]

	def boot_to(self, addr: int, da: bytes):
		self.xsend(0x010008) # BOOT_TO
		assert(self.xstatus() == 0)
		self.xsend(addr.to_bytes(8, "little") + len(da).to_bytes(8, "little"))
		self.xsend(da)
		time.sleep(0.5)
		
		assert(self.xstatus() == 0)
		print("boot_to success.")




if __name__ == "__main__":
	R1Exploit(brom=True)
	print("hello")
	time.sleep(0.5)
	R1Exploit(brom=False)
