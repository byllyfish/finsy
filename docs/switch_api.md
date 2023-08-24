# Switch Read/Write API

The `Switch` class provides the API for interacting with P4Runtime switches. You will control 
a Switch object with a "ready handler" function. The `ready handler` is an
async function that is called when the switch is ready to accept commands.

Your `ready handler` will typically write some control entities to the switch, then
listen for incoming events and react to them with more writes. You may occasionally read entities
from the switch.

When your `ready handler` is invoked, there is already a P4Runtime channel established, with client
arbitration completed, and pipeline configured as specified in `SwitchOptions`.

Here is an example skeleton program. The `ready handler` is named `ready()`.

```python
async def ready(switch: Switch):
    # Check if switch is the primary. If not, we may want to proceed
    # in a read-only mode. In this example, ignore switch if it's a backup.
    if not switch.is_primary:
        return

    # If we're reconnecting to a switch, it will already have runtime state.
    # In this example, we just delete all entities and start over.
    await switch.delete_all()

    # Provision the pipeline with one or more `write` transactions. Each
    # `write` is a single WriteRequest which may contain multiple updates.
    await switch.write(
        # [Next section will cover what goes here.]
    )

    # Listen for events and respond to them. This "infinite" loop will
    # continue until the Switch disconnects, changes primary/backup status,
    # or the controller is stopped.
    async for packet in switch.read_packets():
        await handle_packet(switch, packet)
```

The Switch class provides a `switch.create_task` method to start a managed task.
Tasks allow you to perform concurrent operations on the same switch. We could have
written the last stanza above that reads packets in an infinite loop as a separate
task. It's okay for the ready handler function to return early; any tasks it
created will still run.

## Writes

Use the `write()` method to write one or more P4Runtime updates and packets.

A P4Runtime update supports one of three operations: INSERT, MODIFY or DELETE.
Some entities support all three operations. Other entities only support MODIFY.

| Entity | Operations Permitted 
| ------ | -------------------
| `P4TableEntry` |  INSERT, MODIFY, DELETE
| `P4ActionProfileMember` |  INSERT, MODIFY, DELETE
| `P4ActionProfileGroup` |  INSERT, MODIFY, DELETE
| `P4MulticastGroupEntry` |  INSERT, MODIFY, DELETE
| `P4CloneSessionEntry` |  INSERT, MODIFY, DELETE
| `P4DigestEntry` |  INSERT, MODIFY, DELETE
| `P4RegisterEntry` | MODIFY
| `P4CounterEntry` | MODIFY
| `P4DirectCounterEntry` | MODIFY
| `P4MeterEntry` | MODIFY
| `P4DirectMeterEntry` | MODIFY
| `P4ValueSetEntry` | MODIFY

The `write()` method takes an optional keyword argument `atomicity` to specify the atomicity option.

### Insert/Modify/Delete Updates

To specify the operation, use a unary `+` (insert), `~` (modify), or `-` (delete). If you
do not specify the operation, `write` will raise a `ValueError` exception.

Here is an example showing how to insert and delete two different entities in the same WriteRequest.

```python
await switch.write([
    +P4TableEntry(          # unary + means insert
        "ipv4", 
        match=P4TableMatch(dest="192.168.1.0/24"),
        action=P4TableAction("forward", port=1),
    ),
    -P4TableEntry(          # unary - means delete
        "ipv4", 
        match=P4TableMatch(dest="192.168.2.0/24"),
        action=P4TableAction("forward", port=2),
    ),
])
```

You should not insert, modify or delete the same entry in the same WriteRequest.

If you are performing the **same** operation on all entities, you can use the Switch 
`insert`, `delete`, or `modify` methods.

```python
await switch.insert([
    P4MulticastGroupEntry(1, replicas=[1, 2, 3]),
    P4MulticastGroupEntry(2, replicas=[4, 5, 6]),
])
```

### Modify-Only Updates

For entities that only support the modify operation, you do not need to specify the operation. (You can
optionally use `~`.)

```python
await switch.write([
    P4RegisterEntry("reg1", index=0, data=0),
    P4RegisterEntry("reg1", index=1, data=1),
    P4RegisterEntry("reg1", index=2, data=2),
])
```

You can also use the `modify` method:

```python
await switch.modify([
    P4RegisterEntry("reg1", index=0, data=0),
    P4RegisterEntry("reg1", index=1, data=1),
    P4RegisterEntry("reg1", index=2, data=2),
])
```

If you pass a modify-only entity to the `insert` or `delete` methods, the P4Runtime server will
return an error.

### Sending Packets

Use the `write` method to send a packet.

```
await switch.write([P4PacketOut(b"payload", port=3)])
```

You can include other entities in the same call. Any non-update objects (e.g. P4PacketOut, 
P4DigestListAck) will be sent **before** the WriteRequest.

### Listening for Packets

To receive packets, use the async iterator `Switch.read_packets()`.
In this example, `pkt` is a `P4PacketIn` object.

`read_packets` can filter for a specific `eth_type`.

```python
# Read packets filtering only for ARP (eth_type == 0x0806).
async for pkt in switch.read_packets(eth_types={0x0806}):
    # You can access the packet payload `pkt.payload` or any metadata value,
    # e.g. `pkt['ingress_port']`
    print(pkt.payload)
    print(pkt['ingress_port'])
```

### Listening for Digests

To receive digests, use the async iterator `Switch.read_digests`. You must specify 
the name of the digest from your P4 program.

```python
async for digest in switch.read_digests("digest_t"):
    # You can access the digest metadata e.g. `digest['ingress_port']`
    # Your code may need to update table entries based on the digest data.
    # To ack the digest, write `digest.ack()`.
    await switch.write([entry, ...])
    await switch.write([digest.ack()])
```

To acknowledge the digest entry, you can write `digest.ack()`.

### Other Events

A P4 switch may report other events using the `EventEmitter` API. See
the `SwitchEvent` class for the event types. Each switch has a `switch.ee`
attribute that lets your code register for event callbacks.
