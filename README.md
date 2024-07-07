# Rabbit R1 Boot Notes
REing/documenting the boot process of the Rabbit R1 (MediaTek mt6765, k65v1_64_bsp, Android 13 AOSP).

A lot of the information here will be generic to other Android and/or MediaTek devices, but my intention is only to document the specifics of the R1 device.

This is a living document.

# Glossary

There are soooo many acronyms and abbreviations, so here's a big list for reference:

- `brom`: bootrom
- `BSP`: Board Support Package
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

Boot starts in `brom`, which is baked into the CPU silicon. The CPU starts in a 32-bit mode (TODO: what's the precise mode?).

The next stage is the Preloader, which is stored in the `boot0` partition of eMMC (not to be confused with the `boot` GPT partition).

Preloader is loaded into memory at offset `0x200f10`, with entrypoint at `0x201000`. The CPU is still in a 32-bit mode here.

The Preloader is responsible for showing the initial boot logo, charging animations, etc. (logo image data is stored in the `logo` GPT partition)

# References

- https://juejin.cn/post/6844904089663307790 - Mediatek boot process overview (in Chinese)
- https://research.nccgroup.com/2020/10/15/theres-a-hole-in-your-soc-glitching-the-mediatek-bootrom/
- https://commoncriteriaportal.org/files/epfiles/NSCIB-CC-0486650-ST-v1.91.pdf
