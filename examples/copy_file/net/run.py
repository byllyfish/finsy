#!/usr/bin/env python3

from pathlib import Path

from finsy.test import demonet as dn

MY_DIR = Path(__file__).parent
TMP_DIR = Path("/tmp")

DEMONET = [
    dn.Image(
        files=[
            dn.CopyFile(
                MY_DIR / "myscript.py",
                TMP_DIR / "myscript.py",
            )
        ],
    ),
    dn.Switch("s1"),
    dn.Host("h1", "s1"),
    dn.Host("h2", "s1"),
]

if __name__ == "__main__":
    dn.main(DEMONET)
