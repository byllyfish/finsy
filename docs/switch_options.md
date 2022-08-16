# SwitchOptions

Use the `SwitchOptions` class to specify the settings for one or more switches.
Each `SwitchOptions` instance is immutable.

```
SwitchOptions(
    p4info: pathlib.Path | None = None, 
    p4blob: pathlib.Path | typing.SupportsBytes | None = None, 
    device_id: int = 1, 
    initial_election_id: int = 10, 
    channel_credentials: grpc.ChannelCredentials | None = None, 
    ready_handler: Optional[Callable[[ForwardRef('Switch')], Coroutine[Any, Any, NoneType]]] = None
)
```

You can make a new copy of `SwitchOptions` by using function call syntax with the properties
you want altered.

```python
opts = SwitchOptions(device_id=5)
new_opts = opts(device_id=6)
```

The rest of this document describes the `SwitchOptions` settings.

## p4info

`p4info` specifies a file system path to a P4Info file containing a P4Runtime schema. If `p4info` is `None`, 
the Switch class will attempt to retrieve the `p4info` schema from the Switch target via P4Runtime.

If `p4blob` is also set, the `Switch` class will set the forwarding pipeline to the program
specified by both `p4info` and `p4blob`. If `p4blob` is not set, the Switch class does not know
the authoritative pipeline for the device and will never set the forwarding pipeline.

## p4blob 

`p4blob` specifies the "P4 Device Config" -- the output of the P4 compiler for the target. If `p4blob` is
`None`, the Switch class will never alter the forwarding pipeline.

`p4blob` can be a file system path or any object that implements the `__bytes__()` dunder method. For some
targets `p4blob` is an amalgamation of several files.

## device_id

The Device ID to use in the P4Runtime protocol.

## initial_election_id

The initial value of `election_id` is used to connect to the switch. If the `initial_election_id` is already
in use, the switch may probe for an unused election_id using values < `initial_election_id`.

## channel_credentials

The GRPC `ChannelCredentials` object to use. If `channel_credentials` is `None`, GRPC will use insecure, 
plaintext connections for P4Runtime and gNMI.

`channel_credentials` may be created with `grpc.ssl_channel_credentials(...)`.

## ready_handler

`ready_handler` is an async function that takes a `switch` argument. The `ready_handler` function is 
called when the P4Runtime connection is established.

```python
async def ready(switch: Switch):
    ...
```

If the switch disconnects or changes its primary/backup status, all switch tasks are cancelled. The
`ready_handler` will be invoked again when the switch's new status is ready.
