#!/usr/bin/python

from pathlib import Path
import subprocess
import logging
import sys

EFI_DIR = Path("/boot")

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s]: %(message)s")
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)
LOGGER.addHandler(stream_handler)

VMLINUZ_STR = "vmlinuz"
INIRAMFS_STR = "initramfs"

kernels = [child for child in EFI_DIR.iterdir() if VMLINUZ_STR in child.name]
# initramfses = [
#     child for child in EFI_DIR.iterdir() if INIRAMFS_STR in child.name
# ]


def run_cmd(args):
    logging.info(" ".join(args))
    result = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8"
    )

    if result.returncode != 0:
        logging.error(result.stderr.strip())
        sys.exit(1)

    return result.stdout.strip()


def clean_efiboot():
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
                "--disk", "/dev/nvme0n1",
                "--part", "1",
                "--create",
                "--label", f"Gentoo {version}",
                "--loader", f"/{kernel.name}",
                "--unicode",
                f"root=LABEL=rootfs rootfstype=btrfs rw initrd=\{initramfs.name}",
            ]
        )
        # fmt: on


if __name__ == "__main__":
    main()
