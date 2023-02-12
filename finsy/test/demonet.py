"""Implements a DemoNet class for running Mininet tests in a container."""

import asyncio
import json
import os
import tempfile
from dataclasses import KW_ONLY, asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

import shellous
from shellous import Command, sh
from shellous.harvest import harvest_results


class DemoItem:
    pass


@dataclass
class Image(DemoItem):
    image: str
    _: KW_ONLY
    kind: str = field(default="image", init=False)


@dataclass
class Switch(DemoItem):
    name: str
    _: KW_ONLY
    kind: str = field(default="switch", init=False)
    opts: dict[str, Any] = field(default_factory=dict)


@dataclass
class Host(DemoItem):
    name: str
    switch: str = ""
    _: KW_ONLY
    kind: str = field(default="host", init=False)
    ifname: str = "eth0"
    mac: str = ""
    ipv4: str = ""
    ipv4_gw: str = ""
    ipv6: str = ""
    ipv6_gw: str = ""
    static_arp: dict[str, str] = field(default_factory=dict)
    disable_offload: Sequence[str] = ("tx", "rx", "sg")
    disable_ipv6: bool = True


@dataclass
class Link(DemoItem):
    start: str
    end: str
    _: KW_ONLY
    kind: str = field(default="link", init=False)


class Prompt:
    "Utility class to help with an interactive prompt."

    def __init__(self, runner, prompt: str):
        self.runner = runner
        self.prompt_bytes = prompt.encode("utf-8")

    async def send(
        self,
        input_text: str = "",
        *,
        timeout: float | None = None,
    ) -> str:
        "Write some input text to stdin, then await the response."
        assert self.runner.returncode is None

        stdin = self.runner.stdin
        stdout = self.runner.stdout

        if input_text:
            stdin.write(input_text.encode("utf-8") + b"\n")

        # Drain our write to stdin, and wait for prompt from stdout.
        cancelled, (buf, _) = await harvest_results(
            stdout.readuntil(self.prompt_bytes),
            stdin.drain(),
            timeout=timeout,
        )
        if cancelled:
            raise asyncio.CancelledError()

        if isinstance(buf, asyncio.IncompleteReadError):
            buf = buf.partial

        # Clean up the output to remove the prompt, then return as string.
        buf = buf.replace(b"\r\n", b"\n")
        if buf.endswith(self.prompt_bytes):
            promptlen = len(self.prompt_bytes)
            buf = buf[0:-promptlen].rstrip(b"\n")

        return buf.decode("utf-8")


class DemoNet:
    """Demo network that controls Mininet running in a container.

    ```
        config = [
            Image("docker.io/opennetworking/p4mn"),
            Switch("s1"),
            Host("h1", "s1"),
            Host("h2", "s1"),
        ]

        async with DemoNet(config) as net:
            await net.pingall()
    ```
    """

    _config: Sequence[DemoItem]
    _runner: shellous.Runner | None
    _prompt: Prompt | None

    def __init__(self, config: Sequence[DemoItem]):
        self._config = config
        self._runner = None
        self._prompt = None

    async def __aenter__(self):
        try:
            await self._setup()
            self._runner = podman_start("mininet").run()
            await self._runner.__aenter__()
            self._prompt = Prompt(self._runner, "mininet> ")

            welcome = await self._prompt.send()
            if welcome.startswith("Error:"):
                raise RuntimeError(welcome)
            print(welcome)

        except Exception:
            await self._cleanup()
            raise

        return self

    async def __aexit__(self, *exc):
        print(await self._prompt.send("exit"))
        try:
            await self._runner.__aexit__(*exc)
            self._prompt = None
            self._runner = None
        finally:
            await self._teardown()

    async def pingall(self):
        return await self._prompt.send("pingall")

    async def ifconfig(self, host):
        return await self._prompt.send(f"{host} ifconfig")

    async def _setup(self):
        await podman_create("mininet", "docker.io/opennetworking/p4mn")
        await podman_copy(DEMONET_TOPO, "mininet", "/root/demonet_topo.py")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tfile:
            json.dump(self._config, tfile, default=asdict)

        try:
            await podman_copy(tfile.name, "mininet", "/root/demonet_topo.json")
        finally:
            os.unlink(tfile.name)

    async def _teardown(self):
        pass

    async def _cleanup(self):
        await podman_rm("mininet")


DEMONET_TOPO = Path(__file__).parent / "demonet_topo.py"


def podman_create(container: str, image_slug: str) -> Command:
    return sh(
        "podman",
        "create",
        "--privileged",
        "--rm",
        "-it",
        "--name",
        container,
        "--publish",
        "50001-50003:50001-50003",
        "--sysctl",
        "net.ipv6.conf.default.disable_ipv6=1",
        image_slug,
        "--custom",
        "/root/demonet_topo.py",
        "--topo",
        "demonet",
        # "-v",
        # "debug",
    )


def podman_copy(src_path: Path, container: str, dest_path: Path) -> Command:
    return sh(
        "podman",
        "cp",
        src_path,
        f"{container}:{dest_path}",
    )


def podman_start(container: str) -> Command:
    return sh("podman", "start", "-ai", container).set(pty=True)


def podman_rm(container: str) -> Command:
    return sh("podman", "rm", container).set(exit_codes={0, 1})


async def main():
    topo = [
        Image("xyz"),  # FIXME: Image not supported yet.
        Switch("s1"),
        Host("h1", "s1", ipv4="192.168.0.1/24"),
        Host("h2", "s1"),
    ]

    async with DemoNet(topo) as net:
        print(await net.ifconfig("h1"))
        print(await net.ifconfig("h2"))
        # print(await net.pingall())


if __name__ == "__main__":
    asyncio.run(main())
