#!/usr/bin/python

from pathlib import Path
from typing import List
import subprocess
import logging
import re
import sys

EFI_DIR = Path("/boot")

IS_CMDLINE_AUTO = True
CMDLINE = "root=LABEL=rootfs rootfstype=btrfs rootflags=subvol=gentoo-root rw"

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s]: %(message)s")
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)
LOGGER.addHandler(stream_handler)

VMLINUZ_STR = "vmlinuz"
INIRAMFS_STR = "initramfs"


def run_cmd(args):
    logging.info(" ".join(args))
    result = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8"
    )

    if result.returncode != 0:
        logging.error(result.stderr.strip())
        sys.exit(1)

    return result.stdout.strip()


def read_file(file_path: Path) -> List[str]:
    with open(file_path, mode="r", encoding="utf-8") as f:
        return f.readlines()


def get_cmdline() -> str:
    cmd_line = read_file(Path("/proc/cmdline"))[0].strip()
    cmd_line = re.sub(r"initrd=\\[^\s]+", "", cmd_line).strip()
    logging.info(f"cmd_line: {cmd_line}")
    return cmd_line


def get_efi_dir_device(efi_dir_path: Path) -> str:
    mounts = read_file(Path("/proc/mounts"))
    efi_mount = [mount for mount in mounts if f" {efi_dir_path} " in mount][
        0
    ].strip()

    efi_part = efi_mount.split(" ", 1)[0]
    efi_part_num = re.findall(r"[0-9]+$", efi_part)[0]

    efi_device = efi_part.removesuffix(efi_part_num)
    if "nvme" in efi_device:
        efi_device = efi_device[:-1]

    return efi_device, efi_part_num


def clean_efiboot() -> None:
    lines = run_cmd(["efibootmgr"]).splitlines()
    entries = [line for line in lines if "Gentoo" in line]
    ids = [int(entry.split("*", 1)[0][-4:]) for entry in entries]

    [
        run_cmd(
            ["sudo", "efibootmgr", "--delete-bootnum", "--bootnum", str(id)]
        )
        for id in ids
    ]


def main():
    clean_efiboot()

    kernels = [
        child for child in EFI_DIR.iterdir() if VMLINUZ_STR in child.name
    ]
    # initramfses = [
    #     child for child in EFI_DIR.iterdir() if INIRAMFS_STR in child.name
    # ]

    if IS_CMDLINE_AUTO:
        cmd_line = get_cmdline()
    else:
        cmd_line = CMDLINE

    efi_device, efi_part_num = get_efi_dir_device(EFI_DIR)

    for kernel in kernels:
        logging.info(f"found kernel: {kernel}")

        version = kernel.name.split("-", 1)[1]
        initramfs = kernel.parent / f"{INIRAMFS_STR}-{version}.img"

        if not initramfs.exists():
            logging.error(f"file does not exist: {initramfs}")
            continue
        elif not initramfs.is_file():
            logging.error(f"is not a file: {initramfs}")
            continue

        logging.info(f"initramfs: {initramfs}")

        # fmt: off
        run_cmd(
            [
                "sudo", "efibootmgr",
                "--create",
                "--disk", efi_device,
                "--part", efi_part_num,
                "--label", f"Gentoo {version}",
                "--loader", f"/{kernel.name}",
                "--unicode", f"{cmd_line} initrd=\\{initramfs.name}",
            ]
        )
        # fmt: on


if __name__ == "__main__":
    main()
