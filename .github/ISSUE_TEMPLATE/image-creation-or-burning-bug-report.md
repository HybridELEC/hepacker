---
name: Image creation or burning bug report
about: Create a report to help us improve
title: ''
labels: ''
assignees: ''

---

**The build environment**
- Distro: [e.g. Arch Linux]
- Architecture: [e.g. x86_64]
- ampart version: [result of `ampart --version`, e.g. `ampart-ng (Amlogic eMMC partition tool) by 7Ji, version 1.4-c998dd0-20240606`]
- ampack version: [result of `ampack --version`, e.g. `ampack 0.1.0`]
- Python version: [result of `python --version`, e.g. `Python 3.12.5`]

**The target platform**
- Family: [e.g. SC2]
- SoC: [e.g. S905X4]
- Board/Box:  [e.g. HK1 RBox X4]

**The Android image**
- URL to download it: [e.g. https://drive.google.com/......]
- Android version: [e.g. 11]
- Release name containing image version: [e.g.  ah218.VONTAR_X4_1000M_11.2023.01.05.02.55]

**The CoreELEC subsystem options**
- URL to upgrade tarball: [e.g. https://github.com/CoreELEC/CoreELEC/releases/download/21.1-Omega/CoreELEC-Amlogic-ne.aarch64-21.1-Omega.tar]
- Version: [e.g. 21.1-Omega]
- Target: [e.g. Amlogic-ne]
- DTB: [e.g. sc2-s905x4-4g-1gbit]
- Storage size: [e.g. 1G]

**The CoreELEC subsystem options**
- URL to upgrade tarball: [e.g. https://github.com/EmuELEC/EmuELEC/releases/download/v4.7/EmuELEC-Amlogic-ng.aarch64-4.7.tar
- Version: [e.g. v4.7]
- Target: [e.g. Amlogic-ng]
- DTB: [e.g. sc2-s905x4-4g-1gbit]
- Storage size: [e.g. 4G]

**The hepacker command**
- Full command: [e.g. python ~/Development/embedded/image/hepacker/hepacker.py --android ~/Downloads/aml_upgrade_package_senk.img --ce-tar ~/Downloads/CoreELEC-Amlogic-ng.arm-21.0-Omega.tar --ce-dtb g12a_s905x2_4g --ce-storage 1G --ee-tar ~/Downloads/EmuELEC-Amlogic-ng.aarch64-4.7.tar --ee-dtb g12a_s905x2_4g --ee-storage 4G --output a95x_f2_hybrid.img]
- Log of the command: [save it in a text file and compress as gz, don't paste a wall of text here]

**The burning environment**
- The OS [e.g. Windows 11]
- The Burning Tool version [e.g. v2.2.4]

**The image status (write X in brackets if it matches)**
- The original Android image burns without issue []
- The new image builds successfully []
- The new image could be identified by Amlogic USB Burning Tool []
- The new image can be burnt at least partially by Amlogic USB Burning Tool, i.e. the progress goes over 10% []
- The new image can be burnt successfully by Amlogic USB Burning Tool []

**Additional context**
Add any other context about the problem here.
