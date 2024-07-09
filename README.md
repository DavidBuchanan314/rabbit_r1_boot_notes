# Rabbit R1 Boot Notes
REing/documenting the boot process of the Rabbit R1 (MediaTek mt6765, k65v1_64_bsp, Android 13 AOSP).

A lot of the information here will be generic to other Android and/or MediaTek devices, but my intention is only to document the specifics of the R1 device.

This is a living document.

# Glossary

There are soooo many acronyms and abbreviations, so here's a big list for reference:

- `ATF`, `TF-A`: [ARM Trusted Firmware](https://community.arm.com/oss-platforms/w/docs/483/trusted-firmware-a)
- `brom`: bootrom
- `BSP`: Board Support Package
- `DA`: Download Agent
- `EL0`, `EL1`, `EL2`, `EL3`: [ARM Exeption Levels](https://developer.arm.com/documentation/102412/0103/Privilege-and-Exception-levels/Exception-levels)
- `GPT`: [GUID Partition Table](https://en.wikipedia.org/wiki/GUID_Partition_Table)
- `GZ`: [GenieZone](https://patchwork.kernel.org/project/linux-mediatek/patch/20230919111210.19615-2-yi-de.wu@mediatek.com/), EL2 Hypervisor (not to be confused with gzip!)
- `IPI`: InterProcessor Interrupt
- `LK`: [Little Kernel](https://github.com/littlekernel/lk)
- `magiskboot`: A component of [Magisk](https://github.com/topjohnwu/Magisk) for repacking android boot images (kernel, ramdisk). Also repackaged as a standalone tool [here](https://github.com/ookiineko/magiskboot_build).
- `MT`, `MTK`: MediaTek
- `mtkclient`: https://github.com/bkerler/mtkclient - "MTK reverse engineering and flash tool"
- `Picachu`: "PI CAlibration and CHaracterization Utility" - "voltage calibration during booting" (What is PI? Power Input?)
- `REE`: Rich Execution Environment
- `SSPM`: "System Security Processor Manager", "Secure System Power Manager" (???)
- `TEE`: Trusted Execution Environment

# Boot Stages Overview

Boot starts in `brom`, which is baked into the CPU silicon. The CPU starts in AArch32 mode.

The next stage is the Preloader, which is stored in the `boot0` partition of eMMC (not to be confused with the `boot` GPT partition).

Preloader is loaded into memory at offset `0x200f10`, with entrypoint at `0x201000`. The CPU is still in AArch32 mode here.

The Preloader's stack spans from `0x200000` to `0x200c00`.

The Preloader is responsible for showing the initial boot logo, charging animations, etc. (logo image data is stored in the `logo` GPT partition).

The Preloader loads cached DRAM calibration data from the `boot_para` GPT partition.

The Preloader loads the `lk`, `tee` (ATF), and `gz` GPT partitions into memory, and verifies their signatures.

(TODO: move some of this "overview" stuff into the subsections below)

## BROM

The CPU starts in AArch32 mode.

As far as I can tell, the ROM itself is mapped at address 0.

Among the first things it does is:

- The stack is set up to grow downwards from `0x0010_2738`
- Copy data from `0x0001_0618` to `0x0010_2740`-`0x0010_2891` (presumably `.data`)
- Zero the range `0x0010_2894`-`0x0010_2d00` (presumably `.bss`)

## Preloader

The Preloader also starts in AArch32 mode.

The Preloader is responsible for (in no particular order):

- Initialising DRAM
- Showing the boot logo (and associated animations, e.g. charging)
- Loading and jumping to the next stage (I haven't figured out the specifics of this yet, I think it also switches to AArch64)
- Optionally booting into "Fastboot" mode.
- Optionally booting a "DA" image, loaded over USB.

# Physical Memory Map

```
start       - end (inclusive)

0x0000_0000 - 0x????_????: BROM

0x0010_0000 - 0x0011_2000: SRAM
0x0020_0000 - 0x0030_0000: SRAM (1MB)

0x1000_7000 - 0x????_????: WDT

0x1100_2000 - 0x1100_2020: UART
0x1100_3000 - 0x1100_3020: UART

0x4000_0000 - 0x1_4000_0000: DRAM (4GB)
```

# References

- https://juejin.cn/post/6844904089663307790 - Mediatek boot process overview (in Chinese)
- https://research.nccgroup.com/2020/10/15/theres-a-hole-in-your-soc-glitching-the-mediatek-bootrom/
- https://commoncriteriaportal.org/files/epfiles/NSCIB-CC-0486650-ST-v1.91.pdf
- https://gist.github.com/lopestom/ce250f5de64a2764ee85092a2c01939e - android partition name info
- https://github.com/u-boot/u-boot/blob/master/doc/README.mediatek - u-boot mediatek docs
- https://github.com/bkerler/mtkclient/blob/a789e6ccb5601e931a4f4a1f2c3f36fe59c29a81/mtkclient/config/brom_config.py#L974-L1001 - mtkclient chipconfig (useful memory addresses)
