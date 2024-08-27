----
SPDX-License-Identifier: AGPL-3.0-or-later
----
# HybridELEC packer
A tool to create HybridELEC Android + CE + EE 3in1 burning image, Android + CE 2in1 burning image, and Android + EE 2in1 burning image.

You're free to redistribute the generated image, but be sure not to violate the EULA of your Android image provider. Be extra careful if you build from a third party Android ROM, as most ROM makers are not happy for re-modification of their ROMs.

## Dependencies
The platform on which this tool is developed and tested is Arch Linux.

This tool expects the following tool & binaries to exist in `PATH` and being the latest version. 

- `ampart`: from https://github.com/7Ji/ampart , for modifying the partition table in DTB
- `ampack`: from https://github.com/7Ji/ampack , for unpacking and repacking burning image
- `mkimage`: provided by `uboot-tools`, for creating uboot script
- `mkfs.vfat`: provided by `dosfstools`, for creating fat32 filesystems for `ce_system` and `ee_system`
- `mcopy`: provided by `mtools`, for pre-populating fat32 filesystems
- `mkfs.ext4`: provided by `e2fsprogs`, for creating ext4 filesystems for `ce_storage` and `ee_storage`
- `img2simg`: provides by `android-tools`, for converting raw partition files to sparse partition files

On Arch Linux, install the above dependencies with the following command:
```
sudo pacman -Syu uboot-tools dosfstools mtools e2fsprogs android-tools
yay -S ampart-git ampack-git
```

## Usage
```
python hepacker.py [-h] --android ANDROID [--ce-tar CE_TAR] [--ce-dtb CE_DTB] [--ce-storage CE_STORAGE] [--ee-tar EE_TAR] [--ee-dtb EE_DTB] [--ee-storage EE_STORAGE] [--keep KEEP [KEEP ...]] [--building BUILDING] --output OUTPUT

options:
  -h, --help            show this help message and exit
  --android ANDROID     path to base Android image, it must not contain embedded CE nor EE
  --ce-tar CE_TAR       path to CoreELEC upgrade tar, setting this enables embedding CE, requiring --ce-dtb and --ce-storage
  --ce-dtb CE_DTB       name of CoreELEC DTB, without .dtb suffix, e.g. sc2_s905x4_4g_1gbit
  --ce-storage CE_STORAGE
                        size of CoreELEC storage partition, e.g. 1G
  --ee-tar EE_TAR       path to EmuELEC upgrade tar, setting this enables embedding EE, requiring --ee-dtb and --ee-storage
  --ee-dtb EE_DTB       name of EmuELEC DTB, without .dtb suffix, e.g. sc2_s905x4_4g_1gbit
  --ee-storage EE_STORAGE
                        size of EmuELEC storage partition, e.g. 1G
  --keep KEEP [KEEP ...]
                        partition file(s) you would want to keep, multiple args can be followed, by keeping only the bare minimum you essentially keep the Android pre-booting environment but remove the Android system and the disk space
                        occupied by them, so the installation would be CE/EE only, in that case an external CoreELEC/EmuELEC boot is needed before the eMMC CE/EE is bootable, the parts set is box-specific and newer boxes need more parts to
                        boot, you are recommended to go from a full list (with a manual ampack unpack and set all unpacked parts) and drop one by one to find the minimum list, e.g. UBOOT.USB UBOOT.ENC
  --building BUILDING   path to building folder, would be removed if it already exists, default: building
  --output OUTPUT       path to output image

Note: --android is always needed (Android); with --ce-tar = embedding CoreELEC (+CoreELEC); with --ee-tar = embedding EmuELEC (+EmuELEC); with box-specific --keep = dropping Android system (-Android)
```

Examples:

- Build Android + CoreELEC + EmuELEC 3-in-1 image
  ````
  python hepacker.py --android ~/Downloads/aml_upgrade_package_senk.img --ce-tar ~/Downloads/CoreELEC-Amlogic-ng.arm-21.0-Omega.tar --ce-dtb g12a_s905x2_4g --ce-storage 1G --ee-tar ~/Downloads/EmuELEC-Amlogic-ng.aarch64-4.7.tar --ee-dtb g12a_s905x2_4g --ee-storage 4G --output a95x_f2_hybrid_ACE.img
  ````

- Build Android + CoreELEC 2-in-1 image
  ````
  python hepacker.py --android ~/Downloads/aml_upgrade_package_senk.img --ce-tar ~/Downloads/CoreELEC-Amlogic-ng.arm-21.0-Omega.tar --ce-dtb g12a_s905x2_4g --ce-storage 1G --output a95x_f2_hybrid_AC.img
  ````

- Build Android + EmuELEC 2-in-1 image
  ````
  python hepacker.py --android ~/Downloads/aml_upgrade_package_senk.img --ee-tar ~/Downloads/EmuELEC-Amlogic-ng.aarch64-4.7.tar --ee-dtb g12a_s905x2_4g --ee-storage 4G --output a95x_f2_hybrid_AE.img
  ````
