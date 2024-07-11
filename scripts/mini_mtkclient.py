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

		

		if self.brom:
			preloader = bytearray(open("../dumped_bins/preloader_k65v1_64_bsp.bin", "rb").read()[0xf0:])

			do_patch(
				preloader,
				bytes.fromhex("28 b9  c5 48  01 f0 c3 fd"),
				bytes.fromhex("05 e0  c5 48  01 f0 c3 fd"),
				"preloader: don't disable logging"
			)
			# load preloader into SRAM
			self.cmd_send_da(0x20_1000, len(preloader), 0x100, preloader)

			print("Jumping to preloader.")
			self.cmd_jump_da(0x20_1000)

		else:
			# load LK into DRAM
			da = open("./custom_da/main.bin", "rb").read()
			self.cmd_send_da(0x4020_0000, len(da), 0, da)
			self.cmd_jump_da(0x4020_0000)

			time.sleep(0.1)

			print("Trying to talk to DA...")


			# start talking to our custom DA
			self.echo(0xdeadbeef)
			print("It worked!!!")

			bootimg = open("../../my_dumps/boot_a3_uart.bin", "rb").read()
			img_len = int.from_bytes(bootimg[-0x30:-0x2c]) # parse AVB footer https://github.com/ARM-software/u-boot/blob/master/lib/libavb/avb_footer.h
			bootimg = bootimg[:img_len] # we don't care about the padding/footer (waste of time sending it over USB)
			
			#bootimg = b"TEST"

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

			#print("Listening for log messages from DA:")
			#try:
			#	while log_len := int.from_bytes(self.read(4, timeout=10000)):
			#		print("[DA]", self.read(log_len).decode())
			#		time.sleep(0.1)
			#except usb.core.USBTimeoutError:
			#	print("Timed out")
			#else:
			#	print("DA hung up on us. That's probably good!")


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
	
	def read(self, length, timeout=500) -> bytes:
		res = b""
		while len(res) < length:
			res += self.ep_in.read(length - len(res), timeout=timeout)
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

	def boot_to(self, addr: int, da: bytes):
		self.xsend(0x010008) # BOOT_TO
		assert(self.xstatus() == 0)
		self.xsend(addr.to_bytes(8, "little") + len(da).to_bytes(8, "little"))
		self.xsend(da)
		time.sleep(0.5)
		
		assert(self.xstatus() == 0)
		print("boot_to success.")




if __name__ == "__main__":
	#R1Exploit(brom=True)
	#print("hello")
	#time.sleep(0.5)
	R1Exploit(brom=False)
