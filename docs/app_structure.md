# Structure of Finsy Apps

This document describes a common pattern or skeleton for making a Finsy **App**.
An **App** is an object that controls a set of Switches. Each Switch will
usually run the same P4 program, and the App's `on_ready` handler will control each
Switch individually.

The **App** object provides a common area where your switches can store their runtime
state.

Finsy does not include any scaffolding for an **App** -- there isn't anything
to subclass. What follows is just a suggestion on how to structure
this common object.

You can easily extend this pattern to multiple apps. This can be useful if you
have two or more sets of switches that behave differently. For example, you might
have `leaf` switches and `spine` switches that operate independently of each other.
Each set of switches can be managed by a different app, all within the same 
`fy.Controller`.

## The App Pattern

Here is the basic App pattern. The `MyApp` class will implement the main logic
for the switches we want to control.

```python
from pathlib import Path
import finsy as fy


class MyApp:
    "MyApp controls Switches that run the `myapp.p4` program."

    _P4INFO = Path("myapp.p4info.pbtxt")
    _P4BIN = Path("myapp.json")
    _OPTIONS = fy.SwitchOptions(p4info=_P4INFO, p4blob=_P4BIN)

    def __init__(self):
        "Set up app's data structures here (if needed)."

    def on_ready(self, sw: fy.Switch):
        "Called when Switch establishes P4Runtime connection."
        print(f"{sw.name}: on_ready")

    def on_port_up(self, sw: fy.Switch, port: fy.SwitchPort):
        "Called when a switch port goes up (according to GNMI)."
        print(f"{sw.name}: on_port_up {port.name}")

    def on_port_down(self, sw: fy.Switch, port: fy.SwitchPort):
        "Called when a switch port goes down (according to GNMI)."
        print(f"{sw.name}: on_port_down {port.name}")

    def new_switch(self, name: str, address: str, config: Any) -> fy.Switch:
        "Return a new Switch for `MyApp`."
        sw = fy.Switch(name, address, self._OPTIONS, stash={"config": config})
        sw.ee.add_listener(fy.SwitchEvent.CHANNEL_READY, self.on_ready)
        sw.ee.add_listener(fy.SwitchEvent.PORT_UP, self.on_port_up)
        sw.ee.add_listener(fy.SwitchEvent.PORT_DOWN, self.on_port_down)
        # Set up other Switch events as needed...
        return sw
```

When we create the SwitchOptions object `_OPTIONS`, we do *not* set the `ready_handler` field.
Instead, we are going to listen for the CHANNEL_READY event on the `ee` event
emitter. The SwitchOptions `ready_handler` is just a convenient way to register a 
function to be called when the channel is ready. In this code, we use the
`CHANNEL_READY` event instead.

To set up the event emitter, our app will use a factory function `new_switch`
to create our `fy.Switch` objects. Inside the `new_switch` function, you can
see that we customize the switch to point to the app's callbacks.

The `_options` attribute is private to our App class, so only `new_switch` can
create our Switch instances.

Finsy classes such as `Switch` are not designed to be subclassed. Instead, use
the `ee` and `stash` properties to customize their behavior.

The `ee` event emitter implements the `Observer` design pattern. The Observer
pattern allows the Switch class to notify outside code of events through a
standard interface.

We will use our `MyApp` class when we load our switches.

```python
APP = MyApp()


def _load_switches() -> list[fy.Switch]:
    "Load list of switches from a JSON file."
    switches_json: dict[str, dict[str, Any]] = json.load("switches.json")

    result: list[fy.Switch] = []
    for name, value in switches_json.items():
        result.append(APP.new_switch(name, value["address"], value["config"]))
    return result


async def main():
    controller = fy.Controller(_load_switches())
    await controller.run()


if __name__ == "__main__":
    fy.run(main())
```

If you have multiple app's or more complicated configuration needs, you can 
lift this functionality into an `AppManager` class that wraps the `fy.Controller`
and manages the the top-level App objects.

The `AppManager` class could also add and remove switches at runtime.

```python
class AppManager:
    app: MyApp
    controller: fy.Controller

    def __init__(self):
        self.app = MyApp()
        self.controller = fy.Controller(self._load_switches())

    async def run(self):
        "Run the controller."
        await self.controller.run()

    def _load_switches(self):
        "Load list of switches from a JSON file."
        switches_json: dict[str, dict[str, Any]] = json.load("switches.json")

        result: list[fy.Switch] = []
        for name, value in switches_json.items():
            switch = self.app.new_switch(name, value["address"], value["config"])
            result.append(switch)
        return result


async def main():
    manager = AppManager()
    await manager.run()


if __name__ == "__main__":
    fy.run(main())
```
