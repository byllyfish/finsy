# Conventions

This document describes the code conventions used in the Finsy project.

## Use pathlib for file system paths.

Whenever a file system path is passed to an API, this project uses the builtin `Path` class. Finsy does
not support passing a file path as a string.

```python
from pathlib import Path

P4INFO = Path("example.p4info.txt")
```

## Protobuf Classes

Finsy depends on protobuf-defined classes for P4Runtime and gNMI. The protobuf classes are compiled and 
included as part of the Finsy framework. Finsy relies on the HEAD versions of the protobuf definitions;
these are more current than the published, release versions.

Finsy includes `.pyi` files containing type hints for the protobuf classes. The type hints are
available to the IDE for auto-completion support in the editor.

When referring to protobuf classes, always use the qualified syntax, e.g. `prefix.ClassName` instead
of just `ClassName`. For example, refer to the P4Runtime protobuf class `TableEntry` as `p4r.TableEntry`
in source files.

### gNMI

To use a particular definition, import its prefix name from `finsy.proto`. For example, to use a gNMI
protobuf class:

```python
from finsy.proto import gnmi

value = gnmi.TypedValue(bool_val=False)
```

### P4Runtime

P4Runtime splits its protobuf definitions into four files. To access a P4Runtime protobuf class, use
the appropriate import from this table:

| File | Import |
| ---- | ------ |
| p4.v1.p4runtime_pb2       | `from finsy.proto import p4r` |
| p4.v1.p4data_pb2          | `from finsy.proto import p4d` |
| p4.config.v1.p4info_pb2   | `from finsy.proto import p4i` |
| p4.config.v1.p4types_pb2  | `from finsy.proto import p4t` |

Here is an example:

```python
from finsy.proto import p4r, p4i

ack = p4r.DigestListAck(digest_id=1, list_id=2)
info = p4i.PkgInfo(name="abc")
```

Note: Finsy actually stores its P4Runtime protobuf files as `finsy.proto.p4.v1.p4runtime_pb2`.
If your code accesses `p4.v1.p4runtime_pb2`, you will access the system-provided P4Runtime
library, if it is installed.

## Logging

Finsy uses the `logging` module in the Python standard library. Finsy's log
format includes the name of the current Switch in square brackets.

Here is a Finsy log message for the switch named `sw1`.

```
1715971407.458 INFO finsy [sw1] Channel ready (is_primary=True, role_name=''): pipeline='hello.p4' version='1' arch='v1model'
```

For INFO messages, only the name of the Switch is included in the square brackets.
For all other log levels, Finsy includes the name of the switch *and* the running
task separated by `|`.

Here is a WARNING message from Finsy. The current switch is `sw1` and the name
of the running task is `Switch._run&`.

```
1715971394.055 WARNING finsy [sw1|Switch._run&] gNMI is not implemented
```

Log messages emanating from Finsy itself will come from one of two
loggers: `finsy` and `finsy.msg`.

### The `finsy` Logger

This is the main logger for Finsy. It logs various messages at the DEBUG, INFO, 
WARNING, ERROR and CRITICAL levels.

### The `finsy.msg` Logger

The `finsy.msg` logger logs the actual contents of Protobuf messages sent and
received by Finsy's P4Runtime and GNMI clients. For certain large messages, 
like GetForwardingPipelineRequest and SetForwardingPipelineRequest, the message
is formatted to only include the cookie/hash value rather than the
full contents. In addition, GNMI paths are shortened to a human-readable format.

The `finsy.msg` logger normally only logs message at the DEBUG level. There is
one case where it logs a P4Runtime `StreamMessageResponse` at the ERROR level
when the response contains an actual error.

If you start a Finsy app with the `FINSY_DEBUG` environment variable set to 1
or `true`, Finsy will enable the `finsy.msg` logger by setting its log level
to DEBUG. You may still need to customize the log level of your root logger
to see these log messages.

## Using `fy.LoggerAdapter`

Use the `fy.LoggerAdapter` to wrap your own Python loggers if you want to
include the name of the `[switch|task]` in your log messages.


