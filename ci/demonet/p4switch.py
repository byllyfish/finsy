"Custom switch classes for Mininet."

import shlex
from pathlib import Path
from typing import Any, ClassVar, Iterable

from mininet.node import Switch  # pyright: ignore[reportMissingImports]

_DEFAULT_CPU_PORT = 255
_DEFAULT_DEVICE_ID = 1
_DEFAULT_LOG_LEVEL = "warn"
_DEFAULT_TMP_DIR = Path("/tmp")


class P4RuntimeSwitch(Switch):
    """Abstract base class for a P4Runtime switch (either BMV2 or Stratum)

    Subclasses must override `switch_command` method.
    """

    grpc_port: int
    log_level: str
    cpu_port: int
    device_id: int
    temp_dir: Path
    log_file: Path
    grpc_cacert: Path | None
    grpc_cert: Path | None
    grpc_private_key: Path | None

    _start_command: str = ""
    _base_grpc_port: ClassVar[int] = 50000

    def __init__(self, name: str, config: dict[str, Any], **kwargs):
        super().__init__(name, **kwargs)
        self.grpc_port = config.get("grpc_port") or P4RuntimeSwitch._next_grpc_port()
        self.log_level = config.get("log_level") or _DEFAULT_LOG_LEVEL
        self.cpu_port = config.get("cpu_port") or _DEFAULT_CPU_PORT
        self.device_id = config.get("device_id") or _DEFAULT_DEVICE_ID
        self.grpc_cacert = config.get("grpc_cacert")
        self.grpc_cert = config.get("grpc_cert")
        self.grpc_private_key = config.get("grpc_private_key")

        self.temp_dir = _DEFAULT_TMP_DIR / name
        self.log_file = self.temp_dir / "log.txt"
        self._reset_temp_dir()

    def start(self, controllers):
        "Start the switch."
        args = list(_flatten(self.switch_command()))
        self._start_command = shlex.quote(args[0])
        cmd_line = shlex.join(args)
        log = shlex.quote(str(self.log_file))

        self.cmd(f"{cmd_line} &> {log} &")
        print(f"⚡️ {self._start_command} @ {self.grpc_port}")

    def stop(self, deleteIntfs=True):
        "Stop the switch."
        self.cmd(f"kill %{self._start_command}")
        self.cmd("wait")
        self._start_command = ""

        super().stop(deleteIntfs)

    def switch_command(self):
        """Return command line to run the switch.

        Result must be a list of strings. If this list contains any tuple or
        list objects, they will be recursively flattened, so the end result
        is a single list of strings.
        """
        raise NotImplementedError

    def _reset_temp_dir(self):
        "Remove the temporary switch directory and re-create it."
        tmp = shlex.quote(str(self.temp_dir))
        self.cmd(f"rm -rf {tmp}")
        self.temp_dir.mkdir()

    def _get_interfaces(self):
        "Return (id, name) iterator for all interfaces (excluding loopback)."
        if_index = 1
        for if_name in self.intfNames():
            if if_name == "lo":
                continue
            yield (if_index, if_name)
            if_index += 1

    @staticmethod
    def _next_grpc_port():
        "Return the next available GRPC port."
        P4RuntimeSwitch._base_grpc_port += 1
        return P4RuntimeSwitch._base_grpc_port


class StratumSwitch(P4RuntimeSwitch):
    "StratumBMV2 switch."

    def switch_command(self) -> list[Any]:
        "Return command line to run the switch."
        # Stratum requires an initial dummy pipeline file.
        initial_pipeline = Path("/etc/stratum/dummy.json")
        assert initial_pipeline.exists()

        # Stratum configures the interfaces using a config file.
        config_file = self.temp_dir / "chassis_config.txt"
        config_file.write_text(
            _stratum_chassis_config(self.name, self.device_id, self._get_interfaces())
        )

        tls_config = []
        if self.grpc_cert:
            tls_config = [
                f"-ca_cert_file={self.grpc_cacert}",
                f"-server_cert_file={self.grpc_cert}",
                f"-server_key_file={self.grpc_private_key}",
            ]

        return [
            "stratum_bmv2",
            f"-device_id={self.device_id}",
            f"-chassis_config_file={config_file}",
            f"-persistent_config_dir={self.temp_dir}",
            f"-initial_pipeline={initial_pipeline}",
            f"-cpu_port={self.cpu_port}",
            f"-external_stratum_urls=0.0.0.0:{self.grpc_port}",
            f"-bmv2_log_level={self.log_level}",
            "-read_req_log_file=",
            "-write_req_log_file=",
            *tls_config,
        ]


class BMV2Switch(P4RuntimeSwitch):
    "BMV2 switch."

    def switch_command(self) -> list[Any]:
        "Return command line to run the switch."
        tls_config = []
        if self.grpc_cert:
            tls_config = [
                "--grpc-server-ssl",
                "--grpc-server-with-client-auth",
                ("--grpc-server-cacert", self.grpc_cacert),
                ("--grpc-server-cert", self.grpc_cert),
                ("--grpc-server-key", self.grpc_private_key),
            ]

        return [
            "simple_switch_grpc",
            "--no-p4",
            "--log-console",
            "--log-level",
            self.log_level,
            "--device-id",
            self.device_id,
            [("-i", f"{id}@{name}") for id, name in self._get_interfaces()],
            "--",
            "--cpu-port",
            self.cpu_port,
            "--grpc-server-addr",
            f"0.0.0.0:{self.grpc_port}",
            *tls_config,
        ]


# Exports for bin/mn
switches = {
    "bmv2": BMV2Switch,
    "stratum": StratumSwitch,
}


def _stratum_chassis_config(name: str, node_id: int, interfaces):
    "Produce chassis config file used to configure interfaces."
    ports = "\n".join(
        f"""\
singleton_ports {{
  id: {if_index}
  name: "{if_name}"
  slot: 1
  port: {if_index}
  channel: 1
  speed_bps: 10000000000
  config_params {{
    admin_state: ADMIN_STATE_ENABLED
  }}
  node: {node_id}
}}
""".strip()
        for (if_index, if_name) in interfaces
    )
    result = f"""\
description: "{name}"
chassis {{
  platform: PLT_P4_SOFT_SWITCH
  name: "{name}"
}}
nodes {{
  id: {node_id}
  name: "{name} node {node_id}"
  slot: 1
  index: 1
}}
{ports}
"""
    return result.strip()


def _flatten(value: Iterable[Any]) -> Iterable[str]:
    """Recursively flatten a list containing tuples/lists."""
    for item in value:
        if isinstance(item, (list, tuple)):
            yield from _flatten(item)
        else:
            yield str(item)
