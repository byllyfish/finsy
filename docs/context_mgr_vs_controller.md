# Context Manager API vs. Controller API

Finsy provides two API's for *running* a Switch. You can run the switch in its 
own context using `async with`, or you can run the switch in a `Controller`.

If you have an async `ready_handler` function and one switch, these approaches
are similar. This section highlights the operational differences to help you
decide which approach to use.

### Running in a context manager

Running a Switch as a context manager gives you a **one-off** API.

```python
async with fy.Switch("sw1", "127.0.0.1:50001") as sw1:
    await ready_handler(sw1)
```

When you run a Switch in a context manager, the context is entered after
the GRPC connection is established and the forwarding pipeline is 
optionally configured. If the connection attempt fails, Finsy will raise a 
`P4ClientError` exception; there are **no** retries.

When you leave the Switch context, the GRPC connection is closed immediately,
and the script proceeds on the next line.

Note: You can control multiple switches with the context manager API. The 
switches connections are established **serially**; first sw1, then sw2.

```python
async with (
    fy.Switch("sw1", "127.0.0.1:50001") as sw1,
    fy.Switch("sw2", "127.0.0.1:50002") as sw2,
):
    # Do something with sw1, sw2.
```

### Running in a controller

Running a Switch in a Controller gives you a persistent control 
connection that continuously attempts to recover a lost connection.
When you run multiple switches in a Controller, each switch is managed
independently and **concurrently**.

```python
opts = fy.SwitchOptions(ready_handler=ready_handler)
switches = [fy.Switch("sw1", "127.0.0.1:50001", opts)]
controller = fy.Controller(switches)
await controller.run()
```

The controller runs until it is cancelled, or the process is terminated.

The `ready_handler` is entered after the GRPC connection is established and the
forwarding P4 program is optionally configured. If the connection attempt fails,
a new connection will be periodically re-attempted, but no error is raised. Once
connected, if the connection drops or there is a change in
primary/backup status, the ready handler task will be cancelled, and restarted.

If you want to run multiple switches concurrently, or you want to add/remove
switches at runtime, you'll want to use the Controller API.
