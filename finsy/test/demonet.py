"""Implements a DemoNet class for running Mininet tests in a container."""

import argparse
import asyncio
import json
import os
import re
import shutil
import socket
import tempfile
from dataclasses import KW_ONLY, asdict, dataclass, field
from ipaddress import IPv4Network, IPv6Network
from pathlib import Path
from types import TracebackType
from typing import Any, Generator, Sequence

from shellous import Command, Runner, sh
from shellous.harvest import harvest_results
from typing_extensions import Self

from finsy import MACAddress

try:
    import pygraphviz as pgv  # type: ignore
except ImportError:
    pgv = None

# pyright: reportUnknownMemberType=false

IPV4_BASE = IPv4Network("10.0.0.0/8")
IPV6_BASE = IPv6Network("fc00::/64")


class DemoItem:
    "Marker superclass for all Demo configuration directives."


@dataclass
class CopyFile:
    source: Path
    dest: str


@dataclass
class Image(DemoItem):
    name: str
    _: KW_ONLY
    kind: str = field(default="image", init=False)
    files: Sequence[CopyFile] = field(default_factory=list)


@dataclass
class Switch(DemoItem):
    name: str
    _: KW_ONLY
    kind: str = field(default="switch", init=False)
    params: dict[str, Any] = field(default_factory=dict)
    commands: list[str] = field(default_factory=list)


@dataclass
class Host(DemoItem):
    name: str
    switch: str = ""
    _: KW_ONLY
    kind: str = field(default="host", init=False)
    ifname: str = "eth0"
    mac: str = "auto"
    ipv4: str = "auto"
    ipv4_gw: str = ""
    ipv6: str = ""
    ipv6_gw: str = ""
    ipv6_linklocal: bool = False
    static_arp: dict[str, str] = field(default_factory=dict)
    disable_offload: Sequence[str] = ("tx", "rx", "sg")
    commands: list[str] = field(default_factory=list)

    # These fields are "assigned" when configuration is initially processed.
    assigned_switch_port: int = field(default=0, init=False)
    assigned_mac: str = field(default="", init=False)
    assigned_ipv4: str = field(default="", init=False)
    assigned_ipv6: str = field(default="", init=False)

    def init(self, host_id: int) -> None:
        "Derive MAC and IP addresses when necessary."
        if self.mac == "auto":
            self.assigned_mac = str(MACAddress(host_id))
        else:
            self.assigned_mac = self.mac

        if self.ipv4 == "auto":
            self.assigned_ipv4 = f"{IPV4_BASE[host_id]}/{IPV4_BASE.prefixlen}"
        else:
            self.assigned_ipv4 = self.ipv4

        if self.ipv6 == "auto":
            self.assigned_ipv6 = f"{IPV6_BASE[host_id]}/{IPV6_BASE.prefixlen}"
        else:
            self.assigned_ipv6 = self.ipv6


@dataclass
class Link(DemoItem):
    start: str
    end: str
    _: KW_ONLY
    kind: str = field(default="link", init=False)
    style: str = ""
    commands: list[str] = field(default_factory=list)
    assigned_start_port: int = field(default=0, init=False)
    assigned_end_port: int = field(default=0, init=False)


@dataclass
class Pod(DemoItem):
    name: str
    _: KW_ONLY
    kind: str = field(default="pod", init=False)
    images: Sequence[Image] = field(default_factory=list)
    publish: Sequence[int] = field(default_factory=list)


@dataclass
class Bridge(DemoItem):
    name: str
    _: KW_ONLY
    kind: str = field(default="bridge", init=False)
    mac: str = ""
    ipv4: str = ""
    commands: list[str] = field(default_factory=list)


class Prompt:
    "Utility class to help with an interactive prompt."

    runner: Runner
    prompt_bytes: bytes

    def __init__(self, runner: Runner, prompt: str):
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
        assert self.runner.stdin is not None
        assert self.runner.stdout is not None
        assert self.runner.stderr is None

        stdin = self.runner.stdin
        stdout = self.runner.stdout

        if input_text:
            stdin.write(input_text.encode("utf-8") + b"\n")

        # Drain our write to stdin, and wait for prompt from stdout.
        cancelled, (buf, _) = await harvest_results(
            _read_until(stdout, self.prompt_bytes),
            stdin.drain(),
            timeout=timeout,
        )
        if cancelled:
            raise asyncio.CancelledError()

        # Clean up the output to remove the prompt, then return as string.
        assert isinstance(buf, bytes)
        buf = buf.replace(b"\r\n", b"\n")
        if buf.endswith(self.prompt_bytes):
            promptlen = len(self.prompt_bytes)
            buf = buf[0:-promptlen].rstrip(b"\n")

        return buf.decode("utf-8")


async def _read_until(stream: asyncio.StreamReader, sep: bytes) -> bytes:
    "Read all data until separator."
    # Most reads can complete without buffering.
    try:
        return await stream.readuntil(sep)
    except asyncio.IncompleteReadError as ex:
        return ex.partial
    except asyncio.LimitOverrunError as ex:
        # Okay, we have to buffer.
        buf = bytearray(await stream.read(ex.consumed))

    while True:
        try:
            buf.extend(await stream.readuntil(sep))
        except asyncio.IncompleteReadError as ex:
            buf.extend(ex.partial)
        except asyncio.LimitOverrunError as ex:
            buf.extend(await stream.read(ex.consumed))
            continue
        break

    return bytes(buf)


PID_MATCH = re.compile(r"<\w+ (\w+):.* pid=(\d+)>", re.MULTILINE)


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
    _runner: Runner | None
    _prompt: Prompt | None
    _pids: dict[str, int]

    def __init__(
        self,
        config: Sequence[DemoItem],
    ):
        _configure(config)
        self._config = config
        self._runner = None
        self._prompt = None
        self._pids = {}

    async def __aenter__(self) -> Self:
        try:
            cmd = await self._setup()
            self._runner = Runner(cmd.stdout(sh.CAPTURE))
            await self._runner.__aenter__()
            self._prompt = Prompt(self._runner, "mininet> ")

            await self._read_welcome()
            await self._read_pids()

        except Exception:
            await self._cleanup()
            raise

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        assert self._runner is not None
        await self._read_exit()

        try:
            await self._runner.__aexit__(exc_type, exc_value, exc_tb)
            self._prompt = None
            self._runner = None
        finally:
            await self._teardown()

    def __await__(self) -> Generator[None, None, None]:
        return self._interact().__await__()

    async def _read_welcome(self):
        "Collect welcome message from Mininet."
        assert self._prompt is not None
        welcome = await self._prompt.send()
        if welcome.startswith("Error:"):
            raise RuntimeError(welcome)
        print(welcome)

    async def _read_pids(self):
        "Retrieve the PID's so we can do our own `mnexec`."
        dump = await self.send("dump")
        for mo in PID_MATCH.finditer(dump):
            name, pid = mo.groups()
            self._pids[name] = int(pid)
        print(self._pids)

    async def _read_exit(self):
        "Exit and collect exit message from Mininet."
        assert self._prompt is not None
        print(await self._prompt.send("exit"))

    async def _interact(self):
        try:
            cmd = await self._setup()
            await cmd.stdin(sh.INHERIT).stdout(sh.INHERIT).stderr(sh.INHERIT)
            await self._teardown()
        except Exception:
            await self._cleanup()
            raise

    def mnexec(self, host: str, *args: str) -> Command[str]:
        pid = self._pids[host]
        return podman_exec("mininet", "mnexec", "-a", str(pid), *args)

    async def send(self, cmdline: str, *, expect: str = "") -> str:
        assert self._prompt is not None
        result = await self._prompt.send(cmdline)
        print(result)
        if expect:
            assert expect in result
        return result

    async def pingall(self) -> str:
        return await self.send("pingall")

    async def ifconfig(self, host: str) -> str:
        return await self.send(f"{host} ifconfig")

    async def _setup(self):
        image = self._image()
        switch_count = self._switch_count()

        await check_versions()
        await podman_create("mininet", image.name, switch_count)
        await podman_copy(DEMONET_TOPO, "mininet", "/root/demonet_topo.py")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tfile:
            json.dump(self._config, tfile, default=_json_default)

        try:
            temp = Path(tfile.name)
            await podman_copy(temp, "mininet", "/root/demonet_topo.json")
        finally:
            temp.unlink()

        return podman_start("mininet")

    async def _teardown(self):
        pass

    async def _cleanup(self):
        await podman_rm("mininet")

    def _image(self) -> Image:
        "Return the configured image, or the default image if none found."
        images = [item for item in self._config if isinstance(item, Image)]
        if len(images) > 1:
            raise ValueError("There should only be one Image config.")
        if not images:
            return Image("docker.io/opennetworking/p4mn")
        return images[0]

    def _switch_count(self) -> int:
        "Return the number of switches in the config."
        return sum(1 for item in self._config if isinstance(item, Switch))


def _json_default(obj: object):
    try:
        if isinstance(obj, Path):
            return str(obj)
        return asdict(obj)  # pyright: ignore[reportGeneralTypeIssues]
    except TypeError as ex:
        raise ValueError(
            f"DemoNet can't serialize {type(obj).__name__!r}: {obj!r}"
        ) from ex


# Allow an environment variable to override podman command.
_podman = os.environ.get("FINSY_PODMAN", "podman")
DEMONET_TOPO = Path(__file__).parent / "demonet_topo.py"
PUBLISH_BASE = 50000


async def check_versions():
    "Check the versions of podman/docker installed."
    global _podman

    cmd = _podman
    if shutil.which(cmd):
        _podman = cmd
    elif shutil.which("docker"):
        _podman = "docker"
    else:
        raise RuntimeError("Cannot find podman or docker!")


def podman_create(
    container: str,
    image_slug: str,
    switch_count: int,
) -> Command[str]:
    assert switch_count > 0

    if switch_count == 1:
        publish = f"{PUBLISH_BASE + 1}"
    else:
        publish = f"{PUBLISH_BASE + 1}-{PUBLISH_BASE+switch_count}"

    debug = []
    if os.environ.get("DEMONET_DEBUG"):
        debug = ["-v", "debug"]

    return sh(
        _podman,
        "create",
        "--privileged",
        "--rm",
        "-it",
        "--name",
        container,
        "--publish",
        f"{publish}:{publish}",
        "--sysctl",
        "net.ipv6.conf.default.disable_ipv6=1",
        image_slug,
        "--custom",
        "/root/demonet_topo.py",
        "--topo",
        "demonet",
        *debug,
    ).stderr(sh.INHERIT)


def podman_copy(src_path: Path, container: str, dest_path: str) -> Command[str]:
    return sh(
        _podman,
        "cp",
        src_path,
        f"{container}:{dest_path}",
    )


def podman_start(container: str) -> Command[str]:
    return sh(_podman, "start", "-ai", container).set(pty=True)


def podman_rm(container: str) -> Command[str]:
    return sh(_podman, "rm", container).set(exit_codes={0, 1})


def podman_exec(container: str, *args: str) -> Command[str]:
    return sh(_podman, "exec", "-it", container, *args)


def _create_graph(config: Sequence[DemoItem]):
    "Create a pygraphviz Graph of the network."
    assert pgv is not None, "pygraphviz is not installed."

    graph_style = dict(
        bgcolor="lightblue",
        margin="0",
        pad="0.25",
    )
    switch_style = dict(
        shape="box",
        fillcolor="green:white",
        style="filled",
        gradientangle=90,
        width="0.1",
        height="0.1",
        margin="0.08,0.02",
    )
    host_style = dict(
        shape="box",
        width="0.01",
        height="0.01",
        margin="0.04,0.02",
        fillcolor="yellow:white",
        style="filled",
        gradientangle=90,
        fontsize="10",
    )
    bridge_style = dict(
        shape="box",
        width="0.01",
        height="0.01",
        margin="0.04,0.02",
        fillcolor="white",
        style="filled",
        fontsize="10",
    )
    link_style = dict(
        penwidth="2.0",
        fontcolor="darkgreen",
        fontsize="10",
    )

    graph = pgv.AGraph(**graph_style)

    for item in config:
        match item:
            case Switch():
                graph.add_node(item.name, **switch_style)
            case Host():
                sublabels = [item.name, item.assigned_ipv4, item.assigned_ipv6]
                host_label = "\n".join(x for x in sublabels if x)
                graph.add_node(
                    item.name,
                    label=host_label,
                    **host_style,
                )
                if item.switch:
                    graph.add_edge(
                        item.name,
                        item.switch,
                        headlabel=f"{item.assigned_switch_port}",
                        **link_style,
                    )
            case Bridge():
                sublabels = [item.name, item.ipv4]
                bridge_label = "\n".join(x for x in sublabels if x)
                graph.add_node(
                    item.name,
                    label=bridge_label,
                    **bridge_style,
                )
            case Link():
                labels = {}
                if item.assigned_end_port:
                    labels["headlabel"] = str(item.assigned_end_port)
                if item.assigned_start_port:
                    labels["taillabel"] = str(item.assigned_start_port)
                addl_style = {}
                if item.style:
                    addl_style.update(style=item.style)
                graph.add_edge(
                    item.start,
                    item.end,
                    **labels,
                    **link_style,
                    **addl_style,
                )
            case _:
                pass

    return graph


def draw(config: Sequence[DemoItem], filename: str) -> None:
    "Draw the config as a graph."
    if pgv is None:
        raise RuntimeError("ERROR: pygraphviz is not installed.")
    _configure(config)
    graph = _create_graph(config)
    graph.layout()
    graph.draw(filename)


def run(config: Sequence[DemoItem]) -> None:
    "Create demo network and run it interactively."

    async def _main():
        await DemoNet(config)

    asyncio.run(_main())


def _configure(config: Sequence[DemoItem]):
    """Scan the configuration and fill in necessary details.

    This method modifies unset fields in the configuration. It is safe to do
    this more than once; this is an idempotent operation.
    """
    switch_db = SwitchPortDB()
    host_id = 1

    for item in config:
        match item:
            case Switch():
                switch_db.add_switch(item.name)
            case Host():
                item.init(host_id)
                host_id += 1
                if item.switch:
                    item.assigned_switch_port = switch_db.next_port(item.switch)
            case Link():
                if item.start in switch_db:
                    item.assigned_start_port = switch_db.next_port(item.start)
                if item.end in switch_db:
                    item.assigned_end_port = switch_db.next_port(item.end)
            case _:
                pass

        if isinstance(item, (Switch, Host, Link, Bridge)):
            # Replace "$DEMONET_IP" in "commands".
            item.commands = [s.replace("$DEMONET_IP", _LOCAL_IP) for s in item.commands]


class SwitchPortDB:
    "Helper class to help track the next available switch port number."

    _next_port: dict[str, int]

    def __init__(self):
        self._next_port = {}

    def add_switch(self, name: str) -> None:
        if name in self._next_port:
            raise ValueError(f"duplicate switch named {name!r}")
        self._next_port[name] = 1

    def next_port(self, name: str) -> int:
        result = self._next_port[name]
        self._next_port[name] = result + 1
        return result

    def __contains__(self, name: str) -> bool:
        return name in self._next_port


def _parse_args():
    "Create argument parser and parse arguments."
    parser = argparse.ArgumentParser("demonet")
    parser.add_argument("--draw", help="Draw network map into file.")
    return parser.parse_args()


def main(config: Sequence[DemoItem]) -> None:
    "Main entry point for demonet."
    args = _parse_args()
    if args.draw:
        draw(config, args.draw)
    else:
        run(config)


def _get_local_ipv4_address():
    "Retrieve the local (routable) IPv4 address."
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(0)
        sock.connect(("10.254.254.254", 1))
        result = sock.getsockname()[0]
    finally:
        sock.close()
    return result


_LOCAL_IP = _get_local_ipv4_address()
