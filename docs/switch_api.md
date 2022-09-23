# Switch Read/Write API

The `Switch` class provides the API for interacting with P4Runtime switches. You will control 
a Switch object with a `ready handler` function. The `ready handler` is an
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

The Switch class provides a `create_task` method to start a managed task. Tasks allow you to perform
concurrent opertions on the same switch. See the `Switch Tasks` design doc for more information.

We will start by covering the `Switch.write` API.

## Writes

Use the `write()` method to write one or more P4Runtime updates and packets.

A P4Runtime `Update` supports one of three operations: INSERT, MODIFY or DELETE.
Some entities support all three operations. Other entities only support MODIFY.

| Entity | Operations Permitted 
| ------ | -------------------
| P4TableEntry |  INSERT, MODIFY, DELETE
| P4ActionProfileMember |  INSERT, MODIFY, DELETE
| P4ActionProfileGroup |  INSERT, MODIFY, DELETE
| P4MulticastGroupEntry |  INSERT, MODIFY, DELETE
| P4CloneSessionEntry |  INSERT, MODIFY, DELETE
| P4DigestEntry |  INSERT, MODIFY, DELETE
| P4RegisterEntry | MODIFY
| P4CounterEntry | MODIFY
| P4DirectCounterEntry | MODIFY
| P4MeterEntry | MODIFY
| P4DirectMeterEntry | MODIFY
| P4ValueSetEntry | MODIFY

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

You can include other entities in the same call. Any non-update objects (e.g. P4PacketIn, 
P4DigestListAck) will be sent **before** the WriteRequest.

## Listen for Events

TODO

## Read Entities

TODO

## Other Events

TODO

## Errors

TODO