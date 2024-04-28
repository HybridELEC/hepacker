import os
import sys
import tarfile
import hashlib
from dataclasses import dataclass

# setenv rootopt "BOOT_IMAGE=kernel.img boot=/dev/ce_system disk=/dev/ce_storage"

# #------------------------------------------------------------------------------------------------------
# #
# # HybridELEC specific logic: DTB selection
# #
# # should be the name (without .dtb extension) of a file under device_trees
# #
# device_tree=sc2_s905x4_4g_1gbit
# #
# #------------------------------------------------------------------------------------------------------

# We don't want the first 0x48 bytes

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

    @classmethod 
    def from_args(cls):
        argv = sys.argv
        return cls(argv[1], argv[2], argv[3], argv[4], argv[5], argv[6], argv[7], argv[8])

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

class UpgradeTar:
    def __init__(self, path: str, dtb: str):
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

if __name__ == '__main__':
    args = Args.from_args()
    ce_tar = UpgradeTar(args.ce_tar, args.ce_dtb)
    ee_tar = UpgradeTar(args.ee_tar, args.ee_dtb)
    print(args)
    print(ce_tar)
    print(ee_tar)