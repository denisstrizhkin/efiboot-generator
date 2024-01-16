from pathlib import Path
from typing import List
import logging
import subprocess
import sys


def run_cmd(args: List[str]) -> str:
    logging.info(" ".join(args))
    result = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8"
    )

    if result.returncode != 0:
        logging.error(result.stderr.strip())
        sys.exit(1)

    return result.stdout.strip()


def delete_entry(id: int) -> None:
    run_cmd(["efibootmgr", "--delete-bootnum", "--bootnum", str(id)])


def add_entry(
    efi_device: str,
    efi_part_num: int,
    prefix: str,
    version: str,
    cmd_line: str,
    kernel: Path,
    initramfs: Path,
) -> None:
    # fmt: off
    run_cmd(
        [
            "efibootmgr",
            "--create",
            "--disk", efi_device,
            "--part", str(efi_part_num),
            "--label", f"{prefix} {version}",
            "--loader", f"/{kernel.name}",
            "--unicode", f"{cmd_line} initrd=\\{initramfs.name}",
        ]
    )
    # fmt: on


def find_entries(prefix: str) -> List[int]:
    lines = run_cmd(["efibootmgr"]).splitlines()
    entries = [line for line in lines if prefix in line]
    for entry in entries:
        logging.info(f"found entry: {entry}")

    ids = [int(entry.split("*", 1)[0][-4:]) for entry in entries]
    return ids
