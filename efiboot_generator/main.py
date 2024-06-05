#!/usr/bin/python

from argparse import ArgumentParser
from pathlib import Path
from typing import List, Tuple
import logging
import re
from efiboot_generator import add_entry, delete_entry, find_entries

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s]: %(message)s")
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)
LOGGER.addHandler(stream_handler)

VMLINUZ_STR = "vmlinuz"
INIRAMFS_STR = "initramfs"


def read_file(file_path: Path) -> List[str]:
    with open(file_path, mode="r", encoding="utf-8") as f:
        return f.readlines()


def get_cmdline() -> str:
    cmd_line = read_file(Path("/proc/cmdline"))[0].strip()
    cmd_line = re.sub(r"initrd=\\[^\s]+", "", cmd_line).strip()
    logging.info(f"cmd_line: {cmd_line}")
    return cmd_line


def get_efi_dir_device(efi_dir_path: Path) -> Tuple[str, int]:
    mounts = read_file(Path("/proc/mounts"))
    dev_mounts = [mount for mount in mounts if re.match(r"^/dev/", mount)]
    efi_mount = [mount for mount in dev_mounts if f" {efi_dir_path} " in mount][
        0
    ].strip()
    print(efi_mount)

    efi_part = efi_mount.split(" ", 1)[0]
    efi_part_num = re.findall(r"[0-9]+$", efi_part)[0]

    efi_device = efi_part.removesuffix(efi_part_num)
    if "nvme" in efi_device:
        efi_device = efi_device[:-1]

    return efi_device, int(efi_part_num)


def main():
    argparser = ArgumentParser(
        prog="efiboot-generator",
        description="Automate EFI entries generation with efibootmgr",
    )

    argparser.add_argument(
        "--efi-dir",
        action="store",
        required=False,
        default="/boot",
        type=str,
        help="Efi partiton mount point",
    )

    argparser.add_argument(
        "--entry-prefix",
        action="store",
        required=False,
        default="Gentoo Efistub",
        type=str,
        help="Efi entry prefix",
    )

    argparser.add_argument(
        "--entry-cmdline",
        action="store",
        required=False,
        type=str,
        help="Efi entry cmdline",
    )

    args = argparser.parse_args()

    entry_prefix = args.entry_prefix
    efi_dir = Path(args.efi_dir)

    if args.entry_cmdline:
        entry_cmdline = args.entry_cmdline
    else:
        entry_cmdline = get_cmdline()

    old_entries = find_entries(entry_prefix)

    kernels = [
        child for child in efi_dir.iterdir() if VMLINUZ_STR in child.name
    ]
    # initramfses = [
    #     child for child in EFI_DIR.iterdir() if INIRAMFS_STR in child.name
    # ]

    efi_device, efi_part_num = get_efi_dir_device(efi_dir)
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
        add_entry(
            efi_device,
            efi_part_num,
            entry_prefix,
            version,
            entry_cmdline,
            kernel,
            initramfs,
        )

    for entry in old_entries:
        delete_entry(entry)


if __name__ == "__main__":
    main()
