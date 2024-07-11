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

function dataViewsAreEqual(a, b) {
	if (a.byteLength !== b.byteLength) return false;
	for (let i=0; i < a.byteLength; i++) {
	  if (a.getUint8(i) !== b.getUint8(i)) return false;
	}
	return true;
}

function be32enc(val)
{
	return new Uint8Array([(val>>24)&0xff, (val>>16)&0xff, (val>>8)&0xff, val&0xff])
}

async function usb_echo(dev, data)
{
	let res = await dev.transferOut(1, data);
	//console.log(res);
	let res2 = await dev.transferIn(1, data.byteLength);
	if (!dataViewsAreEqual(res2.data, new DataView(data.buffer))) {
		print("[-] FATAL: Echo failed :(");
		console.log(data, res2);
		assert(0);
	}
}

function sleep(ms) {
	return new Promise(resolve => setTimeout(resolve, ms));
}

async function go()
{
	try {
	print("[*] Connecting...");
	let device = await navigator.usb.requestDevice({ filters: [{
		vendorId: 0x0e8d,
		productId: 0x2000
	}] });
	print("[+] Device connected.");

	await device.open();

	if (device.configuration === null) {
		print("[*] Selecting configuration...");
		await device.selectConfiguration(0);
	}

	print("[*] Claiming interface...");
	await device.claimInterface(1);

	console.log(device);

	print("[*] Handshaking...");
	let handshake_data = new Uint8Array([0xa0, 0x0a, 0x50, 0x05]);
	let i = 0;
	let num_tries = 0;
	let res = null;
	while (i < 4) {
		//console.log("send", handshake_data[i])
		res = await device.transferOut(1, handshake_data.slice(i, i+1));
		if (res.status == "ok" && res.bytesWritten == 1) {
			//console.log("sent");
			res = await device.transferIn(1, 0x100);
			//console.log(res, res.data.getInt8(res.data.byteLength-1));
			//console.log(res.data.getUint8(res.data.byteLength-1) ^ handshake_data[i]);
			if (res.status == "ok" && ((res.data.getUint8(res.data.byteLength-1) ^ handshake_data[i]) == 0xff)) {
				i++;
			} else {
				i = 0;
			}
		}
		num_tries++;
		if (num_tries > 100) {
			print("[-] Handshake failed :(");
			return;
		}
	}
	print("[+] Handshook!");

	await usb_echo(device, new Uint8Array([0xfd])); // GET_HW_CODE
	res = await device.transferIn(1, 2);
	console.log(res);
	hwcode = res.data.getUint8(0) << 8 | res.data.getUint8(1);
	print(`[+] hw code: 0x${hwcode.toString(16)}`);
	res = await device.transferIn(1, 2);
	console.log(res);

	print("[*] Disabling WDT...");
	await usb_echo(device, new Uint8Array([0xd4])); // WRITE32
	await usb_echo(device, be32enc(0x1000_7000));
	await usb_echo(device, be32enc(1));
	res = await device.transferIn(1, 2);
	if (res.data.getUint16(0) > 3) {
		print(`[-] FATAL: Bad status ${res.data.getUint16(0)}`);
		return;
	}
	await usb_echo(device, new Uint8Array([0x22, 0x00, 0x00, 0x64]));
	res = await device.transferIn(1, 2);
	if (res.data.getUint8(0) != 0) {
		print(`[-] FATAL: Bad status ${res.data.getUint16(0)}`);
		return;
	}
	print("[+] WDT disabled!");

	print("[*] Fetching DA...");
	let da = await fetch("./da.bin").then(r => r.arrayBuffer());
	print("[*] Sending DA...");
	let dalen = da.byteLength;
	await usb_echo(device, new Uint8Array([0xd7])); // SEND_DA
	await usb_echo(device, be32enc(0x4020_0000)); // address
	await usb_echo(device, be32enc(dalen)); // length
	await usb_echo(device, be32enc(0)); // sig length
	res = await device.transferIn(1, 2);
	if (res.data.getUint8(0) != 0) {
		print(`[-] FATAL: Bad status ${res.data.getUint16(0)}`);
		return;
	}
	let bytestowrite = dalen;
	let pos = 0;
	while (bytestowrite > 0) {
		_sz = Math.min(bytestowrite, 64);
		await device.transferOut(1, da.slice(pos, pos + _sz));
		bytestowrite -= _sz;
		pos += _sz;
	}

	await sleep(35);

	let csum = await device.transferIn(1, 2);
	console.log(csum);
	res = await device.transferIn(1, 2);
	if (res.data.getUint8(0) != 0) {
		print(`[-] FATAL: Bad status ${res.data.getUint16(0)}`);
		return;
	}
	print("[+] Sent DA.");


	print("[*] Jumping to DA...");
	await usb_echo(device, new Uint8Array([0xd5])); // JUMP_DA
	await usb_echo(device, be32enc(0x4020_0000)); // address
	res = await device.transferIn(1, 2);
	if (res.data.getUint16(0) != 0) {
		print(`[-] FATAL: Bad status ${res.data.getUint16(0)}`);
		return;
	}
	print("[+] Jumped!");

	await sleep(100);

	print("[*] Saying hi to DA...");
	await usb_echo(device, be32enc(0xdeadbeef));
	print("[*] Loading boot.img... (TODO: loading bar for this lol (it's 22MB))")
	let bootimg = await fetch("./boot.bin").then(r => r.arrayBuffer());
	print("[*] Sending boot.img...");
	let bootlen = bootimg.byteLength;
	await usb_echo(device, be32enc(bootlen));

	let progbar = document.createElement("span");
	logdiv.appendChild(progbar);
	let proglen = 50;

	bytestowrite = bootlen;
	pos = 0;
	while (bytestowrite > 0) {
		_sz = Math.min(bytestowrite, 0x2000);
		await device.transferOut(1, bootimg.slice(pos, pos + _sz));
		bytestowrite -= _sz;
		pos += _sz;
		let progsteps = Math.floor(proglen * (pos / bootlen));
		progbar.innerText = "[" + "#".repeat(progsteps) + "-".repeat(proglen-progsteps) + "] " + Math.floor(100 * (pos / bootlen)) + "%\n"
	}

	await sleep(500);
	await usb_echo(device, be32enc(0xdeadbeef));
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
