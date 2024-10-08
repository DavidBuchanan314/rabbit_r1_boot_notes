# Carroot (RabbitOS Jailbreak) Instructions

These instructions are for the "carroot" WebSerial Jailbreak script, which is live [here](https://retr0.id/stuff/r1_jailbreak/).

Technical writeup [here](https://www.da.vidbuchanan.co.uk/blog/r1-jailbreak.html).

The jailbreak itself is "tethered", meaning it does not persist between reboots. Everything stays in-memory, which makes it harder to brick your device etc. That said, this is a highly experimental tool, use at your own risk, bla bla bla.

If you perform the [Post-Install](#Post-Install) steps, you can enable ADB, giving you a more ergonomic (but non-root) shell and the ability to install APKs, etc.

### Credits

This project glues together code and ideas from:

- [bkerler/mtkclient](https://github.com/bkerler/mtkclient)
- [ng-dst/flashable-android-rootkit](https://github.com/ng-dst/flashable-android-rootkit)
- [LuigiVampa92/unlocked-bootloader-backdoor-demo](https://github.com/LuigiVampa92/unlocked-bootloader-backdoor-demo)
- [topjohnwu/Magisk](https://github.com/topjohnwu/Magisk)
- [ookiineko/magiskboot_build](https://github.com/ookiineko/magiskboot_build)

## Prerequisites

You need a browser that supports WebSerial, which at the moment is most things Chromium-based (and sadly, not Firefox).

Your R1 should be running stock RabbitOS. Currently only tested on the latest version (v0.8.107) (Edit: also tested on v0.8.112).

### Linux Prerequisites

Copy [this file](https://github.com/bkerler/mtkclient/blob/main/mtkclient/Setup/Linux/50-android.rules) into the `/etc/udev/rules.d/` directory, and then run `sudo udevadm control --reload-rules && sudo udevadm trigger`

If you followed an earlier (pre-release) version of these instructions, you'll need to delete `/etc/udev/rules.d/10-rabbitr1.rules` and re-run `sudo udevadm control --reload-rules && sudo udevadm trigger`

### Windows Prerequisites

Install [these drivers](https://downloads2.myteracube.com/Tools/Drivers/MediaTek_Preloader_USB_VCOM_Drivers_Setup_Signed.zip) ([source](https://community.myteracube.com/t/teracube-2e-instructions-to-install-factory-software-and-to-reset/4026) - note to Rabbit Inc., you should be making similar provisions for your users.)

(If you previously installed these or similar drivers following the [r1 escape](https://github.com/RabbitHoleEscapeR1/r1_escape) instructions, and it worked, you're already good to go)

Note, the installer will tell you to reboot at the end, but this seems to be unnecessary.

### macOS Prerequisites

No special instructions. It Just Works™

## Doing the thing

1. Plug your R1 into your PC using a USB cable.
2. Power off your R1.
3. Click the "connect" button on the webpage.
4. After several seconds, your R1 should turn itself back on (the screen stays off, though). You'll then see it on the connection menu.
5. Select the device ("MT65xx Preloader") as fast as possible (You have about 3 seconds).

If it works, you should see log messages all the way up to `[+] It worked???!?`, and the device will
start booting normally.

During boot, you should see a "BOOTING CARROOT" message appear in a very tiny font
at the bottom of the screen, along with some ASCII art.

If something goes wrong and you want to try from scratch, reboot the device, refresh the webpage, and start agin.

## Post-Install

Connect to the TCP shell with `rlwrap nc rabbit_ip_here 1337`. You won't get a prompt or anything, but if you type in a command and press enter, you should see the results.

### Enabling ADB

The following commands will enable ADB (and developer mode settings) in a way that persists between reboots (and in theory, even between OTA updates).

```sh
pm uninstall --user 0 tech.rabbit.judy
kill $(pgrep judy)
settings put global development_settings_enabled 1
settings put global adb_enabled 1
```

"Judy" is a Rabbit service that tries to force-disable ADB, so of course we remove it first. Thank you to marceld505 for figuring these steps out.

Once you have ADB installed, you can easily install additional APKs, etc.

**NOTE:** Disabling Judy and enabling development settings will persist between reboots, but adb itself will not persist.

### Persisting ADB

But wait, there's more!

These commands will allow adb to persist beyond reboots (although the shell it gives you will be unprivileged)

```sh
setprop persist.sys.usb.config ""
setprop persist.sys.test_harness true
```

I have a feeling this will stop working in future RabbitOS updates, but it works for now.

### Upgrading to Telnet

Execute the `scripts/drop_busybox.sh` script from this repo, with your R1's IP address as argument. It'll connect to the existing TCP shell and upload a busybox binary, then start busybox's telnetd on port 31337.

You should then be able to get a more ergonomic root shell via `telnet rabbit_ip_here 31337`

### Misecellaneous Useful Commands

Open settings:

```sh
am start -a android.settings.SETTINGS
```

## Known Issues

When left alone for a while, the device sometimes randomly reboots into Fastboot mode. I'm not sure why!

This is annoying but harmless, you can just reboot the device and everything should be back to normal.

My current hunch is that RTC flag registers aren't getting set properly for whatever reason.
