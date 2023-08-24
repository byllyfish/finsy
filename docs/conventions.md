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

Finsy depends on protobuf-defined classes for gNMI and P4Runtime. The protobuf classes are compiled and 
included as part of the Finsy framework. Finsy also includes `.pyi` files containing type hints for the 
protobuf classes. The type hints are available to the IDE for auto-completion support in the editor.

Always use the qualified syntax, e.g. `prefix.ClassName` instead of just `ClassName`.  In a few cases, 
Finsy defines wrapper classes with the same name as the protobuf class. By including the prefix, we
can distinguish them.

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
library.
