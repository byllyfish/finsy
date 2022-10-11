"""Package that provides accessors for protobuf files.

For example, to access `p4.v1.p4runtime_pb2.CapabilitiesRequest`:

    from finsy.proto import p4r
    msg = p4r.CapabilitiesRequest(...)

Here is the full table:

    p4.v1.p4runtime_pb2       => `from finsy.proto import p4r`
    p4.v1.p4runtime_pb2_grpc  => `from finsy.proto import p4r_gprc`
    p4.v1.p4data_pb2          => `from finsy.proto import p4d`
    p4.config.v1.p4info_pb2   => `from finsy.proto import p4i`
    p4.config.v1.p4types_pb2  => `from finsy.proto import p4t`
    google.rpc.code_pb2       => `from finsy.proto import rpc_code`
    google.rpc.status_pb2     => `from finsy.proto import rpc_status`
    gnmi1.gnmi_pb2            => `from finsy.proto import gnmi`
    gnmi1.gnmi_pb2_grpc       => `from finsy.proto import gnmi_grpc`
    gnmi1.gnmi_ext_pb2        => `from finsy.proto import gnmi_ext`

"""

__all__ = (
    "gnmi",
    "gnmi_ext",
    "gnmi_grpc",
    "p4i",
    "p4t",
    "p4d",
    "p4r",
    "p4r_grpc",
    "rpc_code",
    "rpc_status",
    "U128",
)

import os
import sys

# Generated protobuf files reference their dependencies using absolute imports.
# To work around this, modify the import path to substitute our embedded
# modules for global "p4" and "google.rpc" modules. After we've imported the
# protobuf modules, we switch `sys.path` back.

if "p4.v1.p4runtime_pb2" in sys.modules:
    raise RuntimeError("p4runtime_pb2 already imported?")  # pragma: no cover

sys.path.insert(0, os.path.dirname(__file__))

from gnmi1 import gnmi_ext_pb2 as gnmi_ext
from gnmi1 import gnmi_pb2 as gnmi
from gnmi1 import gnmi_pb2_grpc as gnmi_grpc
from google.rpc import code_pb2 as rpc_code
from google.rpc import status_pb2 as rpc_status
from p4.config.v1 import p4info_pb2 as p4i
from p4.config.v1 import p4types_pb2 as p4t
from p4.v1 import p4data_pb2 as p4d
from p4.v1 import p4runtime_pb2 as p4r
from p4.v1 import p4runtime_pb2_grpc as p4r_grpc

del sys.path[0]


class U128:
    "Utility class for p4r.Uint128."

    @staticmethod
    def encode(value: int) -> p4r.Uint128:
        "Create a Uint128 object from an integer."

        if not isinstance(value, int) or value < 0:
            raise ValueError(f"invalid argument: {value!r}")
        return p4r.Uint128(high=value >> 64, low=value & 0xFFFFFFFFFFFFFFFF)

    @staticmethod
    def decode(value: p4r.Uint128) -> int:
        "Convert a Uint128 object to an integer."

        return (value.high << 64) | value.low
