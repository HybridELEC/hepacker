# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import sys
import tarfile
import hashlib
import pathlib
import shutil
import subprocess
import argparse
from dataclasses import dataclass

@dataclass
class UpgradeTarInfo:
    kernel: tarfile.TarInfo
    kernel_md5: tarfile.TarInfo
    system: tarfile.TarInfo
    system_md5: tarfile.TarInfo
    dtb: tarfile.TarInfo
    cfgload: tarfile.TarInfo
    config: tarfile.TarInfo

@dataclass
class UpgradeTarData:
    kernel: bytes
    system: bytes
    dtb: bytes
    cfgload: bytes
    config: bytes

def verify_md5(data: bytes, md5sum_expected: bytes):
    md5sum_calculated = hashlib.md5(data).digest()
    if md5sum_calculated != md5sum_expected:
        raise Exception(f"MD5 sum is not right, calculated {md5sum_calculated} != expected {md5sum_expected}")

@dataclass
class Building:
    building: pathlib.Path

    def everything(self) -> pathlib.Path:
        return self.building.joinpath("everything")

    def keep(self, parts: list):
        print(f"Keeping only the following parts in base Android image: {parts}")
        for path in self.everything().glob('*'):
            if path.name in parts:
                print(f"+ {path}")
                continue
            print(f"- {path}")
            path.unlink()

    def check_encrypt(self):
        if self.everything().joinpath("meson1_ENC.dtb").exists():
            raise ValueError("Image contains encrypted DTB partition meson1_ENC.dtb, it's impossible to modify partition layout")

def upper_megabyte(size: int) -> int:
    return (size + 0xfffff) // 0x100000 * 0x100000

def allocate_file(path: pathlib.Path, size: int):
    path.unlink(True)
    with path.open('wb') as f:
        f.truncate(size)

class UpgradeTar:
    def __init__(self, name: str, path: str, dtb: str):
        tar = tarfile.TarFile(path, 'r', format = tarfile.GNU_FORMAT)
        prefix = tar.members[0].name
        target = f"{prefix}/target"
        bootloader = f"{prefix}/3rdparty/bootloader"
        self.info = UpgradeTarInfo(
            tar.getmember(f"{target}/KERNEL"),
            tar.getmember(f"{target}/KERNEL.md5"),
            tar.getmember(f"{target}/SYSTEM"),
            tar.getmember(f"{target}/SYSTEM.md5"),
            tar.getmember(f"{bootloader}/device_trees/{dtb}.dtb"),
            tar.getmember(f"{bootloader}/Generic_cfgload"),
            tar.getmember(f"{bootloader}/config.ini")
        )
        kernel = tar.extractfile(self.info.kernel).read()
        kernel_md5 = bytes.fromhex(tar.extractfile(self.info.kernel_md5).read()[0:32].decode('utf-8'))
        verify_md5(kernel, kernel_md5)
        system = tar.extractfile(self.info.system).read()
        system_md5 = bytes.fromhex(tar.extractfile(self.info.system_md5).read()[0:32].decode('utf-8'))
        verify_md5(system, system_md5)
        self.data = UpgradeTarData(
            kernel,
            system,
            tar.extractfile(self.info.dtb).read(),
            tar.extractfile(self.info.cfgload).read(),
            tar.extractfile(self.info.config).read()
        )
        self.tar = tar
        self.name = name
        self.dtb = dtb

    def build_system(self, building: Building, system_dynamic: bool, system_size: int) -> int:
        everything = building.everything()
        system_stem = f"{self.name}_system"
        system_content = building.building.joinpath(system_stem)
        system_content.mkdir()
        # cfgload
        cfgload = self.data.cfgload[72:]
        cfgload_segments = []
        for segment in cfgload.split(b'\x0a'):
            if segment.startswith(b'echo "Using device ${device}, number ${devnr}, partition ${partnr}, '):
                cfgload_segments.append(b''.join((
                    b'echo "Using device ${device}, number ${devnr}, partition ${partnr}, HybridELEC (',
                    self.name.upper().encode('utf-8'),
                    b') on eMMC"')))
            elif segment.startswith(b'setenv rootopt "BOOT_IMAGE=kernel.img boot=LABEL='):
                cfgload_segments.append(f'setenv rootopt "BOOT_IMAGE=kernel.img boot=/dev/{self.name}_system disk=/dev/{self.name}_storage"'.encode('utf-8'))
            elif segment.startswith(b'if test "${ce_on_emmc}" = "yes"; then setenv rootopt "BOOT_IMAGE=kernel.img boot=LABEL=CE_FLASH disk=FOLDER=/dev/CE_STORAGE"; fi'):
                pass
            elif segment.startswith(b'fatload ${device} ${devnr}:${partnr} ${dtb_mem_addr} dtb.img'):
                cfgload_segments.append(b'fatload ${device} ${devnr}:${partnr} ${dtb_mem_addr} "device_trees/${device_tree}.dtb"')
            else:
                cfgload_segments.append(segment)
        cfgload = b'\x0a'.join(cfgload_segments)
        cfgload_raw = system_content.joinpath('cfgload.raw')
        with cfgload_raw.open('wb') as f:
            f.write(cfgload)
        cfgload_uscript = system_content.joinpath('cfgload')
        subprocess.run(('mkimage', '-A', 'arm64', '-O', 'linux', '-T', 'script', '-C', 'none', '-d', cfgload_raw, cfgload_uscript))
        cfgload_raw.unlink()
        # config.ini
        config_segments = self.data.config.split(b'\x0a\x0a')
        config_segments.insert(1, 
            '#------------------------------------------------------------------------------------------------------\n'
            '#\n'
            '# HybridELEC specific logic: DTB selection\n'
            '#\n'
            '# should be the name (without .dtb extension) of a file under device_trees\n'
            '#\n'
            f'device_tree={self.dtb}\n'
            '#\n'
            '#------------------------------------------------------------------------------------------------------'.encode('utf-8')
        )
        config = b'\x0a\x0a'.join(config_segments)
        config_ini = system_content.joinpath('config.ini')
        with config_ini.open('wb') as f:
            f.write(config)
        # kernel.img
        kernel_img = system_content.joinpath("kernel.img")
        with kernel_img.open("wb") as f:
            f.write(self.data.kernel)
        # SYSTEM
        system_img = system_content.joinpath("SYSTEM")
        with system_img.open("wb") as f:
            f.write(self.data.system)
        # device_trees/{dtb}.dtb
        device_trees = system_content.joinpath("device_trees")
        device_trees.mkdir()
        with device_trees.joinpath(f"{self.dtb}.dtb").open('wb') as f:
            f.write(self.data.dtb)
        # the whole system partition
        if system_dynamic:
            size = len(cfgload) + 0x48 + len(config) + len(self.data.kernel) + len(self.data.system) + len(self.data.dtb)
            size_partition_least = upper_megabyte(size) + 2 * 0x100000 + system_size
        else:
            size_partition_least = system_size
        system_partition = everything.joinpath(f"{system_stem}.PARTITION")
        # Brute force to find minimum size
        for oversize in range(0, 10):
            size_partition = size_partition_least + oversize * 0x100000
            print(f"Trying system partition size: {size_partition // 0x100000}M")
            allocate_file(system_partition, size_partition)
            subprocess.run(("mkfs.vfat", "-F", "32", "-n", f"HYBRID_{self.name[0].upper()}SYS", system_partition))
            r = subprocess.run(("mcopy", "-svi", system_partition, cfgload_uscript, config_ini, kernel_img, system_img, device_trees, "::"))
            if r.returncode == 0:
                return size_partition
        raise Exception("Cannot create a FAT32 filesystem large enough to hold all files")

    def build_storage(self, building: Building, storage_size: int) -> int:
        storage_size = upper_megabyte(storage_size)
        everything = building.everything()
        storage_stem = f"{self.name}_storage"
        storage_raw = everything.joinpath(f"{storage_stem}.RAW")
        allocate_file(storage_raw, storage_size)
        subprocess.run(("mkfs.ext4", "-m", "0", "-L", f"Hybrid_{self.name.upper()}storage", storage_raw), check = True)
        subprocess.run(("img2simg", storage_raw, everything.joinpath(f"{storage_stem}.PARTITION")), check = True)
        storage_raw.unlink()
        return storage_size

    def build(self, building: Building, system_dynamic: bool, system_size: int, storage_size: int) -> (int, int):
        return (
            self.build_system(building, system_dynamic, system_size),
            self.build_storage(building, storage_size)
        )


def size_from_human_readable(size: str) -> int:
    suffix_map = {
        'B': 1,
        'K': 0x400,
        'M': 0x100000,
        'G': 0x40000000
    }
    return int(size[:-1]) * suffix_map[size[-1]]

@dataclass
class SubsystemOptions:
    tar: str
    dtb: str
    system_dynamic: bool
    system_size: int
    storage: int

    @classmethod
    def from_args(cls, tar: str, dtb: str, system: str, storage: str):
        if tar is None:
            return None
        elif dtb is None:
            raise ValueError("DTB must be set when tar is set")
        elif storage is None:
            raise ValueError("storaget size must be set when tar is set")
        else:
            if system is None:
                system_dynamic = True
                system_size = 0
            elif system[0] == '+':
                print(system)
                system_dynamic = True
                system_size = size_from_human_readable(system[1:])
            else:
                system_dynamic = False
                system_size = size_from_human_readable(system)
            return cls(tar, dtb, system_dynamic, system_size, size_from_human_readable(storage))

    def build_tar(self, tar: UpgradeTar, building: Building):
        self.system, self.storage = tar.build(building, self.system_dynamic, self.system_size, self.storage)

    def build(self, name: str, building: Building):
        self.build_tar(UpgradeTar(name, self.tar, self.dtb), building)

@dataclass
class AmpartPartition:
    name: str
    size: int
    masks: int

    @classmethod
    def from_parg(cls, parg: str):
        parg_parts = parg.split(":")
        if len(parg_parts) != 4:
            raise ValueError("Splitted parg length is not 4")
        return cls(parg_parts[0], int(parg_parts[2]), int(parg_parts[3]))

@dataclass
class AmpartTable:
    partitions: list[AmpartPartition]
    count: int

    @classmethod
    def from_line(cls, line: str):
        line_parts = line.split(" ")
        if len(line_parts) <= 0:
            raise ValueError("Parts of snapshot not greater than 0, impossible")
        partitions = [AmpartPartition.from_parg(line_part) for line_part in line_parts]
        return cls(partitions, len(partitions))

    def update(self, ce_options: SubsystemOptions, ee_options: SubsystemOptions):
        partitions = []
        if ce_options is not None:
            partitions.append(AmpartPartition("ce_system", ce_options.system, 2))
        if ee_options is not None:
            partitions.append(AmpartPartition("ee_system", ee_options.system, 2))
        partitions.extend(self.partitions[:-1])
        if ce_options is not None:
            partitions.append(AmpartPartition("ce_storage", ce_options.storage, 4))
        if ee_options is not None:
            partitions.append(AmpartPartition("ee_storage", ee_options.storage, 4))
        partitions.append(self.partitions[-1])
        if len(partitions) > 28: # Too many, remove _b partitions
            partitions = [partition for partition in partitions if not partition.name.endswith("_b")]
            if len(partitions) > 28:
                raise Exception("Too many partitions")
        self.partitions = partitions

def hack_recovery(building: Building):
    recovery_partition = building.everything().joinpath("recovery.PARTITION")
    if not recovery_partition.exists():
        return
    with recovery_partition.open('rb') as f:
        magic = f.read(8)
        if magic != b'ANDROID!':
            return
        f.seek(0x40)
        cmdline = f.read(0x200)
    cmdline = cmdline.strip()
    cmdline_parts = []
    for part in cmdline.split(b' '):
        if len(part) == 0:
            continue
        elif part.startswith(b'root=/dev/mmcblk0p'):
            part_id = int(part[18:])
            part = f"root=/dev/mmcblk0p{part_id + 2}".encode('utf-8')
        cmdline_parts.append(part)
    cmdline = b' '.join(cmdline_parts)
    cmdline += b'\0' * (0x200 - len(cmdline))
    with recovery_partition.open('rb+') as f:
        f.seek(0x40)
        len_written = f.write(cmdline)
    if len_written != 0x200:
        raise Exception("Written bytes length is not 0x200")

def main():
    argv = sys.argv
    parser = argparse.ArgumentParser(prog='hepacker', epilog='''
        Note: --android is always needed (Android); with --ce-tar = embedding CoreELEC (+CoreELEC); with --ee-tar = embedding EmuELEC (+EmuELEC); with box-specific --keep = dropping Android system (-Android)
    ''')
    parser.add_argument('--android', help='path to base Android image, it must not contain embedded CE nor EE', required=True)
    parser.add_argument('--ce-tar', help='path to CoreELEC upgrade tar, setting this enables embedding CE, requiring --ce-dtb and --ce-storage')
    parser.add_argument('--ce-dtb', help='name of CoreELEC DTB, without .dtb suffix, e.g. sc2_s905x4_4g_1gbit; needed alongside --ce-tar')
    parser.add_argument('--ce-system', help='size of CoreELEC system partition, e.g. 200M, or with + for free space needed to calculate the size dynamically, e.g. +100M, by default it is +0M; dynamic or not, hepacker would always try from set/estimated size +0M to +10M before it gives up for the size, so an e.g. 256M size could result in 266M')
    parser.add_argument('--ce-storage', help='size of CoreELEC storage partition, e.g. 1G; needed alongside --ce-tar')
    parser.add_argument('--ee-tar', help='path to EmuELEC upgrade tar, setting this enables embedding EE, requiring --ee-dtb and --ee-storage')
    parser.add_argument('--ee-dtb', help='name of EmuELEC DTB, without .dtb suffix, e.g. sc2_s905x4_4g_1gbit; needed alongside --ee-tar')
    parser.add_argument('--ee-system', help='size of EmuELEC system partition, e.g. 2G, or with + for free space needed to calculate the size dynamically, e.g. +100M, by default it is +0M; dynamic or not, hepacker would always try from set/estimated size +0M to +10M before it gives up for the size, so an e.g. 2G size could result in 2058M')
    parser.add_argument('--ee-storage', help='size of EmuELEC storage partition, e.g. 1G; needed alongside --ee-tar')
    parser.add_argument('--keep', nargs='+', help='partition file(s) you would want to keep, multiple args can be followed, by keeping only the bare minimum you essentially keep the Android pre-booting environment but remove the Android system and the disk space occupied by them, so the installation would be CE/EE only, in that case an external CoreELEC/EmuELEC boot is needed before the eMMC CE/EE is bootable, the parts set is box-specific and newer boxes need more parts to boot, you are recommended to go from a full list (with a manual ampack unpack and set all unpacked parts) and drop one by one to find the minimum list, e.g. UBOOT.USB UBOOT.ENC')
    parser.add_argument('--building', help='path to building folder, would be removed if it already exists, default: building', default='building')
    parser.add_argument('--output', help='path to output image', required=True)
    args = parser.parse_args()
    ce_options = SubsystemOptions.from_args(args.ce_tar, args.ce_dtb, args.ce_system, args.ce_storage)
    ee_options = SubsystemOptions.from_args(args.ee_tar, args.ee_dtb, args.ee_system, args.ee_storage)
    if ce_options is None and ee_options is None:
        raise ValueError("Neither CoreELEC or EmuELEC to be embedded, check your options")
    building = Building(pathlib.Path(args.building))
    shutil.rmtree(building.building, True)
    everything = building.everything()
    subprocess.run(("ampack", "unpack", args.android, everything), check = True)
    building.check_encrypt()
    if args.keep is not None:
        building.keep(args.keep)
    if ce_options is not None:
        ce_options.build("ce", building)
    if ee_options is not None:
        ee_options.build("ee", building)
    hack_recovery(building)
    dtb = everything.joinpath("meson1.dtb")
    r = subprocess.run(("ampart", "--mode", "dsnapshot", dtb), check = True, stdout = subprocess.PIPE)
    table = AmpartTable.from_line(r.stdout.decode("utf-8").split("\n")[0])
    table.update(ce_options, ee_options)
    subprocess.run(("ampart", "--mode", "dclone", dtb, *(f"{partition.name}::{partition.size}:{partition.masks}" for partition in table.partitions)))
    dtb_dup = everything.joinpath("_aml_dtb.PARTITION")
    if dtb_dup.exists():
        shutil.copyfile(dtb, dtb_dup)
    if everything.joinpath("super.PARTITION").exists() and any(True for _ in everything.glob("*_a.PARTITION")):
        pack_args = ("ampack", "pack", "--out-align", "8", everything, args.output)
    else:
        pack_args = ("ampack", "pack", everything, args.output)
    subprocess.run(pack_args, check = True)

if __name__ == '__main__':
    main()