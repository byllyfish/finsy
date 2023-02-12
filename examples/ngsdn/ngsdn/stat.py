import asyncio
import random

from prometheus_client import Counter

import finsy as fy

_DIRECT_COUNTERS: dict[str, Counter] = {}
_PORT_COUNTERS: dict[str, Counter] = {}
_SWITCH_EVENT = Counter("switch_events", "", ["switch", "event"])


def _switch_event(switch: str, event: str):
    def _count(_: fy.Switch):
        _SWITCH_EVENT.labels(switch, event).inc()

    return _count


class StatManager:
    switch: fy.Switch

    def __init__(self, switch: fy.Switch):
        self.switch = switch

        for event in [fy.SwitchEvent.CHANNEL_UP, fy.SwitchEvent.CHANNEL_DOWN]:
            switch.ee.add_listener(event, _switch_event(switch.name, event.name))

    async def run(self):
        self.switch.create_task(self._poll_direct_counters())
        self.switch.create_task(self._poll_port_counters())

    async def _poll_direct_counters(self):
        await asyncio.sleep(random.uniform(0.1, 10.0))

        # Stratum Note (2022-08-25):
        #   "Reading all direct counters for ALL tables is not supported yet"
        #
        # As a work-around, get list of all direct counters from schema.

        direct_counters = [
            fy.P4DirectCounterEntry(direct_counter.alias).encode(self.switch.p4info)
            for direct_counter in self.switch.p4info.direct_counters
        ]

        while True:
            async for entry in self.switch.read(direct_counters):
                match entry:
                    case fy.P4DirectCounterEntry():
                        self._handle_direct_counter(entry)
                    case _:
                        pass
            await asyncio.sleep(10.0)

    def _handle_direct_counter(self, entry: fy.P4DirectCounterEntry):
        data = entry.data
        assert data is not None

        direct_counter = self.switch.p4info.direct_counters[entry.counter_id]
        match direct_counter.unit:
            case fy.P4CounterUnit.PACKETS:
                self._update_direct_counter(entry, "pkts", data.packet_count)
            case fy.P4CounterUnit.BYTES:
                self._update_direct_counter(entry, "bytes", data.byte_count)
            case fy.P4CounterUnit.BOTH:
                self._update_direct_counter(entry, "pkts", data.packet_count)
                self._update_direct_counter(entry, "bytes", data.byte_count)
            case _:
                pass

    def _update_direct_counter(
        self,
        entry: fy.P4DirectCounterEntry,
        units: str,
        value: int,
    ):
        assert entry.table_entry is not None

        labels = entry.table_entry.match_dict(self.switch.p4info, wildcard="*")
        labels["switch"] = self.switch.name

        counter = self._get_direct_counter(entry, units)
        counter.labels(**labels)._value.set(value)  # type: ignore

    def _get_direct_counter(
        self,
        entry: fy.P4DirectCounterEntry,
        units: str,
    ):
        name = _counter_name(entry.counter_id, units)
        counter = _DIRECT_COUNTERS.get(name)

        if not counter:
            counter_help = f"{name} help"
            labels = self._table_labels(entry.table_id)
            counter = Counter(name, counter_help, labels)
            _DIRECT_COUNTERS[name] = counter

        return counter

    def _table_labels(self, table_id: str) -> list[str]:
        table = self.switch.p4info.tables[table_id]
        labels = [field.alias for field in table.match_fields]
        labels.append("switch")
        return labels

    async def _poll_port_counters(self):
        await asyncio.sleep(random.uniform(0.1, 10.0))

        gnmi_client = self.switch.gnmi_client
        assert gnmi_client is not None

        sub = gnmi_client.subscribe()
        sub.sample(*self._port_paths(), sample_interval=10000)

        while True:
            updates = [update async for update in sub.synchronize()]
            for update in updates:
                self._update_port_counter(update)

    def _port_paths(self):
        return [fy.GNMIPath("/interfaces/interface[name=*]/state/counters")]

    def _update_port_counter(self, update: fy.GNMIUpdate):
        labels = {
            "switch": self.switch.name,
            "port": update.path["name"],
        }
        counter = self._get_port_counter(update.path.last.replace("-", "_"))
        counter.labels(**labels)._value.set(update.value)  # type: ignore

    def _get_port_counter(self, name: str):
        counter = _PORT_COUNTERS.get(name)

        if not counter:
            counter = Counter(name, "", ["switch", "port"])
            _PORT_COUNTERS[name] = counter

        return counter


def _counter_name(name: str, units: str):
    if name.endswith("_counter"):
        name = name[:-8]
    return f"{name}_{units}"
