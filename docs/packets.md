# PacketOut and PacketIn

This document describes how to use the P4PacketOut and P4PacketIn 
classes to construct and read P4Runtime stream messages. (§ 16.1)

Classes used:

- P4PacketOut
- P4PacketIn

All examples are interactive using the Python REPL.

Here's the initial setup.

```pycon
>>> from finsy import P4PacketOut, P4PacketIn, P4Schema
>>> from pathlib import Path
>>> p4info = P4Schema(Path('examples/ngsdn/ngsdn/p4/main.p4info.txt'))

```

To review the schema from the ngsdn example, type `print(p4info)`.

# P4PacketOut

The P4PacketOut class stores a human-readable version of a P4Runtime PacketOut. 

The constructor has a required initial parameter: the packet payload in bytes. The 
remaining parameters describe the packet's metadata values. The names of the
metadata values are described in the P4Info's `ControllerPacketMetadata`
"packet_out".

```python
P4PacketOut(
    __payload: bytes, 
    /, 
    **metadata: Any
)
```

For more on the P4PacketOut, type `help(P4PacketOut)`.

## Sending Packets

To send a packet, you are going to construct a P4PacketOut message and pass it
to the `Switch.write()` method.

```pycon
>>> entry = P4PacketOut(b"abc", magic_val=1234, egress_port=1)
>>> entry.encode_update(p4info)
packet {
  payload: "abc"
  metadata {
    metadata_id: 1
    value: "\004\322"
  }
  metadata {
    metadata_id: 2
    value: "\001"
  }
}

```

The parameter names (magic_val and egress_port) are defined in `controller_packet_metadata["packet_out"]`:

```pycon
>>> p4info.controller_packet_metadata["packet_out"]
P4ControllerPacketMetadata(alias='packet_out', annotations=[P4Annotation(name='controller_header', body='"packet_out"')], brief='', description='', id=78842819, metadata=[P4CPMetadata(annotations=[], bitwidth=15, id=1, name='magic_val', type_spec=None), P4CPMetadata(annotations=[], bitwidth=9, id=2, name='egress_port', type_spec=None)], name='packet_out')

```

If you omit a parameter name, finsy will raise a `ValueError` exception when
encoding the P4PacketOut.

```pycon
>>> entry = P4PacketOut(b"abc", egress_port=1)
>>> entry.encode_update(p4info)
Traceback (most recent call last):
  ...
ValueError: 'packet_out': missing parameter 'magic_val'

```

# P4PacketIn

The P4PacketIn class stores a human-readable version of a P4Runtime PacketIn. 

The constructor has a required initial parameter: the packet payload in bytes. The 
remaining parameters describe the packet's metadata values. The names of the
metadata values are described in the P4Info's `ControllerPacketMetadata`
"packet_in".

```python
P4PacketIn(
    __payload: bytes, 
    /, 
    **metadata: Any
)
```

For more on the P4PacketIn, type `help(P4PacketIn)`.

## Receiving Packets

To receive packets, use the async iterator returned by `Switch.read_packets()`.
In this example, `pkt` is a `P4PacketIn` object.

```python
# Read packets filtering only for ARP (eth_type == 0x0806).
async for pkt in switch.read_packets(eth_types={0x0806}):
    # You can access the packet payload `pkt.payload` or any metadata value,
    # e.g. `pkt['ingress_port']`
    print(pkt.payload)
    print(pkt['ingress_port'])
```

The parameter names (ingress_port and _pad_) are defined in `controller_packet_metadata["packet_in"]`:

```pycon
>>> p4info.controller_packet_metadata["packet_in"]
P4ControllerPacketMetadata(alias='packet_in', annotations=[P4Annotation(name='controller_header', body='"packet_in"')], brief='', description='', id=69098127, metadata=[P4CPMetadata(annotations=[], bitwidth=9, id=1, name='ingress_port', type_spec=None), P4CPMetadata(annotations=[], bitwidth=7, id=2, name='_pad', type_spec=None)], name='packet_in')

```