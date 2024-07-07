# Rabbit R1 Boot Notes
REing/documenting the boot process of the Rabbit R1 (MediaTek mt6765, k65v1_64_bsp, Android 13)

# Glossary

- `brom`: bootrom
- `BSP`: Board Support Package
- `EL0`, `EL1`, `EL2`, `EL3`: [ARM Exeption Levels](https://developer.arm.com/documentation/102412/0103/Privilege-and-Exception-levels/Exception-levels)
- `GZ`: [GenieZone](https://patchwork.kernel.org/project/linux-mediatek/patch/20230919111210.19615-2-yi-de.wu@mediatek.com/), EL2 Hypervisor (not to be confused with gzip!)
- `LK`: [Little Kernel](https://github.com/littlekernel/lk)
- `MT`, `MTK`: MediaTek
