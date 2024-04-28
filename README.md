# HybridELEC packer
A tool to create HybridELEC Android + CE + EE 3in1 burning image.

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
```

## Usage
```
python packer.py [base image] [ce tar] [ce dtb] [ce storage size] [ee tar] [ee dtb] [ee storage size] [output image]
```
- `[base image]`: The path to the base Android Amlogic Bunring Image
  - It must be the original Android image, without CE/EE embedded.
  - It must not be compressed
  - E.g. `~/Downloads/ah218.VONTAR_X4_1000M_11.2023.01.05.02.55.img`
- `[ce tar]`: The path to CoreELEC upgrade tar
  - E.g. `~/Downloads/CoreELEC-Amlogic-ne.aarch64-21.0-Omega.tar`
- `[ce dtb]`: The name of CoreELEC DTB
  - It shall not contain the `.dtb` suffix
  - E.g. `sc2_s905x4_4g_1gbit`
- `[ce storage size]`: The size of CoreELEC storage partition
  - It shall be a valid argument for both `mkfs.ext4 -s` and `ampart --mode dclone`
  - E.g. `1G`
- `[ee tar]`: The path to EmuELEC upgrade tar
  - E.g. `~/Downloads/EmuELEC-Amlogic-ng.aarch64-4.7.tar`
- `[ee dtb]`: The name of EmuELEC DTB
  - It shall not contain the `.dtb` suffix
  - E.g. `sc2_s905x4_4g_1gbit`
- `[ce storage size]`: The size of EmuELEC storage partition
  - It shall be a valid argument for both `mkfs.ext4 -s` and `ampart --mode dclone`
  - E.g. `4G`
- `[output image]`: The path to the output Android Amlogic Burning Image
  - E.g. `HybridELEC_sc2_s905x4_ah212_HK1_Rbox-X4_1000M_Android-11.0-2022.03.05.13.49_CoreELEC-20.0-ne_EmuELEC-v4.6-ng.img`