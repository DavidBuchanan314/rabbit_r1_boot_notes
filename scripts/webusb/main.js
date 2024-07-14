/*
/etc/udev/rules.d/10-rabbitr1.rules

ATTR{idProduct}=="2000", ATTR{idVendor}=="0e8d", RUN="/bin/sh -c 'echo %k:1.0 > /sys/bus/usb/drivers/cdc_acm/unbind'"

sudo udevadm control --reload-rules && sudo udevadm trigger
*/

let logdiv = document.getElementById("logpre");

function print(msg)
{
	console.log(msg);
	logdiv.innerText += msg + "\n";
}

// https://stackoverflow.com/a/78461863
const areUnit8ArraysEqual = (a, b) => {
	if (a.length !== b.length) {
	  return false;
	}
	for (let i = 0; i < a.length; i++) {
	  if (a[i] !== b[i]) {
		return false;
	  }
	}
	return true;
}

function concatUintArrays(a, b) {
	var res = new Uint8Array(a.length + b.length);
	res.set(a);
	res.set(b, a.length);
	return res;
}

async function readNbytes(reader, buffer_in, n) {
	let buffer = buffer_in;
	while (buffer.length < n) {
		let res = await reader.read();
		buffer = concatUintArrays(buffer, res.value);
	}
	return [buffer.slice(0, n), buffer.slice(n, buffer.length)];
}


function be32enc(val)
{
	return new Uint8Array([(val>>24)&0xff, (val>>16)&0xff, (val>>8)&0xff, val&0xff])
}

async function usb_echo(reader, writer, buffer_in, data)
{
	await writer.write(data);
	let [res, buffer] = await readNbytes(reader, buffer_in, data.length);
	if (!areUnit8ArraysEqual(res, data)) {
		print("[-] FATAL: Echo failed :(");
		console.log(res, data);
		assert(0);
	}
	return buffer;
}

function sleep(ms) {
	return new Promise(resolve => setTimeout(resolve, ms));
}

async function go()
{
	try {
	print("[*] Connecting...");
	let port = await navigator.serial.requestPort({ filters: [{
		usbVendorId: 0x0e8d,
		usbProductId: 0x2000
	}] });
	print("[+] Device connected.");

	await port.open({ baudRate: 115200 }); // not the real baud (arbitrary value)

	print("[+] Port opened.");

	const reader = port.readable.getReader();
	const writer = port.writable.getWriter();

	console.log(port);

	print("[*] Handshaking...");
	let handshake_data = new Uint8Array([0xa0, 0x0a, 0x50, 0x05]);
	let i = 0;
	let num_tries = 0;
	let res = null;
	while (i < 4) {
		await writer.write(handshake_data.slice(i, i+1));
		
		console.log("sent", handshake_data.slice(i, i+1));
		res = await reader.read();
		console.log(res);

		if ((res.value[res.value.length-1] ^ handshake_data[i]) == 0xff) {
			i++;
		} else {
			i = 0;
		}

		num_tries++;
		if (num_tries > 100) {
			print("[-] Handshake failed :(");
			return;
		}
	}
	print("[+] Handshook!");

	let buffer = new Uint8Array([]);

	buffer = await usb_echo(reader, writer, buffer, new Uint8Array([0xfd])); // GET_HW_CODE
	[res, buffer] = await readNbytes(reader, buffer, 2);
	console.log(res);
	hwcode = res[0] << 8 | res[1];
	print(`[+] hw code: 0x${hwcode.toString(16)}`);
	[res, buffer] = await readNbytes(reader, buffer, 2);
	console.log(res);

	print("[*] Disabling WDT...");
	buffer = await usb_echo(reader, writer, buffer, new Uint8Array([0xd4])); // WRITE32
	buffer = await usb_echo(reader, writer, buffer, be32enc(0x1000_7000));
	buffer = await usb_echo(reader, writer, buffer, be32enc(1));
	[res, buffer] = await readNbytes(reader, buffer, 2);
	if (new Uint16Array(res.buffer)[0] > 3) {
		print(`[-] FATAL: Bad status ${res.data.getUint16(0)}`);
		return;
	}
	buffer = await usb_echo(reader, writer, buffer, new Uint8Array([0x22, 0x00, 0x00, 0x64]));
	[res, buffer] = await readNbytes(reader, buffer, 2);
	if (res[0] != 0) {
		print(`[-] FATAL: Bad status ${res.data.getUint16(0)}`);
		return;
	}
	print("[+] WDT disabled!");

	print("[*] Fetching DA...");
	let da = await fetch("./da.bin").then(r => r.arrayBuffer());
	print("[*] Sending DA...");
	let dalen = da.byteLength;
	buffer = await usb_echo(reader, writer, buffer, new Uint8Array([0xd7])); // SEND_DA
	buffer = await usb_echo(reader, writer, buffer, be32enc(0x4020_0000)); // address
	buffer = await usb_echo(reader, writer, buffer, be32enc(dalen)); // length
	buffer = await usb_echo(reader, writer, buffer, be32enc(0)); // sig length
	[res, buffer] = await readNbytes(reader, buffer, 2);
	if (res[0] != 0) {
		print(`[-] FATAL: Bad status ${res.data.getUint16(0)}`);
		return;
	}
	let bytestowrite = dalen;
	let pos = 0;
	while (bytestowrite > 0) {
		_sz = Math.min(bytestowrite, 64);
		await writer.write(da.slice(pos, pos + _sz));
		bytestowrite -= _sz;
		pos += _sz;
	}

	await sleep(35);

	[res, buffer] = await readNbytes(reader, buffer, 2);
	console.log("csum", res);
	[res, buffer] = await readNbytes(reader, buffer, 2);
	if (res[0] != 0) {
		print(`[-] FATAL: Bad status ${res.data.getUint16(0)}`);
		return;
	}
	print("[+] Sent DA.");


	print("[*] Jumping to DA...");
	buffer = await usb_echo(reader, writer, buffer, new Uint8Array([0xd5])); // JUMP_DA
	buffer = await usb_echo(reader, writer, buffer, be32enc(0x4020_0000)); // address
	[res, buffer] = await readNbytes(reader, buffer, 2);
	if (new Uint16Array(res.buffer)[0] != 0) {
		print(`[-] FATAL: Bad status ${res.data.getUint16(0)}`);
		return;
	}
	print("[+] Jumped!");

	await sleep(100);

	print("[*] Saying hi to DA...");
	buffer = await usb_echo(reader, writer, buffer, be32enc(0xdeadbeef));
	print("[*] Loading boot.img... (TODO: loading bar for this lol (it's 22MB))")
	let bootimg = await fetch("./boot.bin").then(r => r.arrayBuffer());
	print("[*] Sending boot.img...");
	let bootlen = bootimg.byteLength;
	buffer = await usb_echo(reader, writer, buffer, be32enc(bootlen));

	let progbar = document.createElement("span");
	logdiv.appendChild(progbar);
	let proglen = 50;

	bytestowrite = bootlen;
	pos = 0;
	while (bytestowrite > 0) {
		_sz = Math.min(bytestowrite, 0x2000);
		await writer.write(bootimg.slice(pos, pos + _sz));
		bytestowrite -= _sz;
		pos += _sz;
		let progsteps = Math.floor(proglen * (pos / bootlen));
		progbar.innerText = "[" + "#".repeat(progsteps) + "-".repeat(proglen-progsteps) + "] " + Math.floor(100 * (pos / bootlen)) + "%\n"
	}

	await sleep(500);
	buffer = await usb_echo(reader, writer, buffer, be32enc(0xdeadbeef));
	print("[+] It worked???!?");

	} catch (error) {
		console.log(error);
		print("[-] FATAL: JavaScript exception :(");
		print("");
		print(error.stack.toString());
	}
}

print("");
print("This webpage uses WebUSB to jailbreak a connected Rabbit R1 device.");
print("On success, it'll spawn a root shell on TCP port 1337 (not even telnet, super bare-bones).");
print("If you don't know what that is or why you'd want it, this isn't for you.");
print("DISCLAIMER: Consider this a developer preview, may brick your device, etc. etc.");
print("");
print("Credits to bkerler/mtkclient, ng-dst/flashable-android-rootkit, LuigiVampa92/unlocked-bootloader-backdoor-demo. Writeup coming soon-ish!");
print("");
print("1. Plug your R1 into your PC using a USB cable.");
print("2. Power off your R1.");
print("3. Click the \"connect\" button on this page.");
print("4. Power on your R1. As it turns on, you should see it on the connection menu.");
print("5. Select the device (\"MT65xx Preloader\") as fast as possible (You have about 3 seconds).");
print("");
