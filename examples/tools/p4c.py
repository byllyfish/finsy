#!/usr/bin/env python3
"""Tool to compile P4 programs inside a remote container.

Differs from `p4c-lite.sh` in that it works with remote containers where
volume mounting is not available.

Reference: https://github.com/antoninbas/p4c-lite-docker
"""

import argparse
import asyncio
import contextlib
import os.path
import re
import sys
from pathlib import Path

from shellous import ResultError, sh

_MISSING_SENTINEL = {"*MISSING*"}

_INCLUDE_REGEX = re.compile(
    # match `#include "file" | <file> | FILE`
    r'^\s*#\s*include\s+("[^"\n]+"|<[^>\n]+>|[A-Za-z_][A-Za-z0-9_]*)',
    re.MULTILINE,
)

_DEST_ROOT = Path("/root")
_DEFAULT_IMAGE = "docker.io/antoninbas/p4c-lite"


def _scan_file(source_file: Path) -> set[str]:
    """Scan one source file and produce a set of all #include files.

    Each include file string still retains its start and end delimiters,
    either <>, "", or nothing (MACRO).

    Note: If a file is conditionally included, or the #include line is commented
    out, the file will *still* be in the list.
    """
    if not source_file.exists():
        return _MISSING_SENTINEL

    source = source_file.read_text()
    return set(_INCLUDE_REGEX.findall(source))


def _fix_includes(includes: set[str], parent: str) -> set[str]:
    if not parent:
        return includes
    quote = '"'
    return {f'"{parent}/{name.strip(quote)}"' for name in includes}


def _scan_all_files(source_file: Path) -> dict[str, set[str]]:
    """Scan all source files and produce a dictionary showing dependencies.

    The scan starts with the given `source_file` and recursively hunts down
    all dependencies.

    If a file cannot be found, it will be assigned the _MISSING_SENTINEL value.
    """
    result: dict[str, set[str]] = {}

    dir = source_file.parent
    names = {f'"{source_file.name}"'}
    while names:
        latest = set[str]()
        for name in names:
            if name[0] == '"' and name not in result:
                source = name.strip('"')
                includes = _scan_file(dir / source)
                includes = _fix_includes(includes, os.path.dirname(source))
                result[name] = includes
                latest |= includes
        names = latest

    return result


async def _copy_in(
    src_files: list[Path],
    src_root: Path,
    dest_container: str,
    dest_root: Path,
):
    """Copy specified files to a destination container."""
    assert all(f.is_absolute() for f in src_files)
    assert src_root.is_absolute()

    dest_files = [f.relative_to(src_root) for f in src_files]
    tar = sh("tar", "Ccf", src_root, "-", dest_files).stderr(sh.INHERIT)
    cp = sh("podman", "cp", "-", f"{dest_container}:{dest_root}")

    await (tar | cp)


async def _p4c(container: str, dest_program: Path, dest_out: Path, args: list[str]):
    "Run p4c compiler in a container."
    base_name = dest_program.stem
    await sh(
        "podman",
        "exec",
        container,
        "p4c",
        "--output",
        dest_out,
        "--p4runtime-files",
        dest_out / f"{base_name}.p4info.txtpb",
        args,
        dest_program,
    ).stdout(sh.INHERIT).stderr(sh.INHERIT)


async def _copy_out(dest_container: str, dest_out: Path):
    "Copy output files."
    await sh("podman", "cp", f"{dest_container}:{dest_out}/.", ".")


async def _compile(p4program: Path, container: str, args: list[str]):
    "Compile a p4 program in a container."
    p4program = p4program.resolve()
    work_dir = p4program.parent
    assert p4program.is_file()

    deps = _scan_all_files(p4program)
    print(deps)

    source_files = [
        work_dir / dep.strip('"')
        for dep, val in deps.items()
        if val is not _MISSING_SENTINEL
    ]

    if len(source_files) > 1:
        source_root = Path(os.path.commonpath(source_files))
    else:
        source_root = source_files[0].parent

    dest_program = _DEST_ROOT / p4program.relative_to(source_root)
    dest_out = _DEST_ROOT / "_out_"

    await _copy_in(source_files, source_root, container, _DEST_ROOT)
    await _p4c(container, dest_program, dest_out, args)
    await _copy_out(container, dest_out)


@contextlib.asynccontextmanager
async def running_container(image: str):
    "Async context manager that runs a container."
    podman = sh(
        "podman",
        "run",
        "-i",
        "--rm",
        "--entrypoint",
        "sh",
        image,
        "-c",
        "echo $HOSTNAME; cat",  # `cat` will run util we close stdin.
    )

    async with podman.stdin(sh.CAPTURE).stdout(sh.CAPTURE) as run:
        assert run.stdin is not None
        assert run.stdout is not None

        data = await run.stdout.readline()
        container = data.decode().strip()
        try:
            yield container
        finally:
            run.stdin.close()


def _parse_args():
    "Parse command line arguments."
    parser = argparse.ArgumentParser(
        description="Compile a P4 program.",
        usage="p4c.py [--x-help] [--x-image X_IMAGE] source_file [OPTS...]",
        add_help=False,
    )
    parser.add_argument(
        "--x-help", action="help", help="show this help message and exit"
    )
    parser.add_argument(
        "--x-image", type=str, default=_DEFAULT_IMAGE, help="docker image to use"
    )
    parser.add_argument("source_file", type=Path, help="P4 source file")
    # All other arguments are passed through to `p4c`...
    return parser.parse_known_args()


def _check_file_exists(path: Path):
    "Check that file exists."
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}")
    if not path.is_file():
        raise FileExistsError(f"Not a file: {path}")


async def main():
    "Main function."
    args, extra_args = _parse_args()
    _check_file_exists(args.source_file)

    try:
        # Compile `source_file` inside `container`.
        async with running_container(args.x_image) as container:
            await _compile(args.source_file, container, extra_args)

    except ResultError as err:
        print(err.result.error, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
