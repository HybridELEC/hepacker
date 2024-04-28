import os
import sys
import tarfile
import hashlib
import pathlib
import shutil
import subprocess
from dataclasses import dataclass

@dataclass
class Args:
    base_image: str
    ce_tar: str
    ce_dtb: str
    ce_storage_size: str
    ee_tar: str
    ee_dtb: str
    ee_storage_size: str
    output_image: str

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

    def build_system(self, building: Building) -> int:
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
                cfgload_segments.append(f'setenv rootopt "BOOT_IMAGE=kernel.img boot=/dev/{self.name}_system disk=/dev/{self.name}_storage'.encode('utf-8'))
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
        size = len(cfgload) + 0x48 + len(config) + len(self.data.kernel) + len(self.data.system) + len(self.data.dtb)
        size_partition_least = upper_megabyte(size)
        system_partition = everything.joinpath(f"{system_stem}.PARTITION")
        # Brute force to find minimum size
        for oversize in range(2, 10):
            size_partition = size_partition_least + oversize * 0x100000
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

    def build(self, building: Building, storage_size: int) -> (int, int):
        return (
            self.build_system(building),
            self.build_storage(building, storage_size)
        )

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

    def update(self, ce_system_size: int, ee_system_size: int, ce_storage_size: int, ee_storage_size: int):
        partitions = [
            AmpartPartition("ce_system", ce_system_size, 2),
            AmpartPartition("ee_system", ee_system_size, 2)
        ]
        partitions.extend(self.partitions[:-1])
        partitions.append(AmpartPartition("ce_storage", ce_storage_size, 4))
        partitions.append(AmpartPartition("ee_storage", ee_storage_size, 4))
        partitions.append(self.partitions[-1])
        self.partitions = partitions

def size_from_human_readable(size: str) -> int:
    suffix_map = {
        'B': 1,
        'K': 0x400,
        'M': 0x100000,
        'G': 0x40000000
    }
    return int(size[:-1]) * suffix_map[size[-1]]


def main():
    argv = sys.argv
    args = Args(argv[1], argv[2], argv[3], argv[4], argv[5], argv[6], argv[7], argv[8])
    building = Building(pathlib.Path("building"))
    shutil.rmtree(building.building, True)
    everything = building.everything()
    subprocess.run(("ampack", "unpack", args.base_image, everything), check = True)
    ce_tar = UpgradeTar("ce", args.ce_tar, args.ce_dtb)
    ce_system_size, ce_storage_size = ce_tar.build(building, size_from_human_readable(args.ce_storage_size))
    ee_tar = UpgradeTar("ee", args.ee_tar, args.ee_dtb)
    ee_system_size, ee_storage_size = ee_tar.build(building, size_from_human_readable(args.ee_storage_size))
    # everything = pathlib.Path("building/everything")
    dtb = everything.joinpath("meson1.dtb")
    r = subprocess.run(("ampart", "--mode", "dsnapshot", dtb), check = True, stdout = subprocess.PIPE)
    table = AmpartTable.from_line(r.stdout.decode("utf-8").split("\n")[0])
    table.update(ce_system_size, ee_system_size, ce_storage_size, ee_storage_size)
    subprocess.run(("ampart", "--mode", "dclone", dtb, *(f"{partition.name}::{partition.size}:{partition.masks}" for partition in table.partitions)))
    dtb_dup = everything.joinpath("_aml_dtb.PARTITION")
    if dtb_dup.exists():
        shutil.copyfile(dtb, dtb_dup)
    subprocess.run(("ampack", "pack", everything, args.output_image), check = True)

if __name__ == '__main__':
    main()