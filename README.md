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
python hepacker.py [-h] --android ANDROID [--ce-tar CE_TAR] [--ce-dtb CE_DTB] [--ce-system CE_SYSTEM] [--ce-storage CE_STORAGE] [--ee-tar EE_TAR] [--ee-dtb EE_DTB] [--ee-system EE_SYSTEM] [--ee-storage EE_STORAGE] [--keep KEEP [KEEP ...]]
                [--building BUILDING] --output OUTPUT

options:
  -h, --help            show this help message and exit
  --android ANDROID     path to base Android image, it must not contain embedded CE nor EE
  --ce-tar CE_TAR       path to CoreELEC upgrade tar, setting this enables embedding CE, requiring --ce-dtb and --ce-storage
  --ce-dtb CE_DTB       name of CoreELEC DTB, without .dtb suffix, e.g. sc2_s905x4_4g_1gbit; needed alongside --ce-tar
  --ce-system CE_SYSTEM
                        size of CoreELEC system partition, e.g. 200M, or with + for free space needed to calculate the size dynamically, e.g. +100M, by default it is +0M; dynamic or not, hepacker would always try from set/estimated size +0M
                        to +10M before it gives up for the size, so an e.g. 256M size could result in 266M
  --ce-storage CE_STORAGE
                        size of CoreELEC storage partition, e.g. 1G; needed alongside --ce-tar
  --ee-tar EE_TAR       path to EmuELEC upgrade tar, setting this enables embedding EE, requiring --ee-dtb and --ee-storage
  --ee-dtb EE_DTB       name of EmuELEC DTB, without .dtb suffix, e.g. sc2_s905x4_4g_1gbit; needed alongside --ee-tar
  --ee-system EE_SYSTEM
                        size of EmuELEC system partition, e.g. 2G, or with + for free space needed to calculate the size dynamically, e.g. +100M, by default it is +0M; dynamic or not, hepacker would always try from set/estimated size +0M to
                        +10M before it gives up for the size, so an e.g. 2G size could result in 2058M
  --ee-storage EE_STORAGE
                        size of EmuELEC storage partition, e.g. 1G; needed alongside --ee-tar
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

The image needs to be burnt to eMMC via Amlogic USB Burning Tool, on a Windows host. Check how to flash Android image for your box and everything goes similarly.

## Alternative usage

It's also possible to use the building artifacts (partitions) on a running box. This won't be a step-by-step guide as every box works differently, I would only cover main ideas.

- Make sure you have a working stock Android image.
- Make an image containing your expected CE and EE layout (e.g. if you want CoreELEC + EmuELEC, then make an Android + CoreELEC + EmuELEC one), make sure you have `building/everything/ce_system.PARTITION` and `building/everything/ee_system.PARTITION`
- Boot to an official external CoreELEC or EmuELEC
- Build, or download an already built staticly linked ARM binary for https://github.com/7Ji/ampart
- Transfer ampart to your external system
- Run ampart webreport mode and keep the link, so you can latter restore the snapshots
- Also run ampart dsnapshot mode and esnapshot mode and keep the human-readable snaphsots
- If you do not want to keep Android:
  - Use `dedit` mode with `--migrate all` to drop Android partitions one by one until the box does not boot, for every boot keep a `dsnapshot`.
  - Use `dclone` mode with `--migrate all` to restore the box to the last working `dsnapshot` after you re-flashing the Android and keep on trying.
  - Every box is different so be patient. 
  - Alternatively, you could try to `dclone` a `data::-1:4` snapshot, which means to only keep a data partition that takes all space, however newer boxes require more partitions to boot and this would mostly break the box.
  - You should now have the minimum number of partitions, take a dsnapshot.
  - For a few boxes that would not break without a sane DTB partitions info, you can use `e-` modes, including `ecreate`, for maximum space utilization.
- If you want to keep Android:
  - Back up your Android data partition
- Adapt your dsnapshot: add `[prefix]_system::[size of your ce_system.PARTITION]:2`, e.g. `ce_system::234M:2`,  as needed, before the first partitions (so they would be first, and second if you have two), then add `[prefix]_storage::[size you want for storage]:4`as needed, at the end
  - If you don't want Android, the last storage should have a size of `-1` to take all space, the 2nd last should have an exact size, and both as the last 2.
  - If you keep Android, your storage partitions should be 2nd last and 3rd last, and the Android data partition should keep its size `-1`
- Apply your new dnspashot with `dclone` mode with `--migrate all`
- Reboot the box to ensure it still boots to your external system, and to let the kernel recognize new partitions.
- Restore your Android data partition if needed.
- Use `dd` to clone your `[prefix]_system.PARTITION` into corresponding `/dev/[prefix]_system`
- Run `mkfs.ext4 -m 0` on your `/dev/[prefix]_storage`
- The box should now be able to boot to the first eMMC `_system` partition, to boot to the second you would need https://github.com/HybridELEC/hybrid_android_helper

## License
**HEpacker**, a tool to create HybridELEC Android + CE + EE 3in1 burning image

Copyright (C) 2024-present Guoxin "7Ji" Pu

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.