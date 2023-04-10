import finsy as fy

from . import netcfg
from .link import LinkEvent, LinkReady


class RouteManager:
    switch: fy.Switch

    def __init__(self, switch: fy.Switch):
        self.switch = switch

    async def run(self):
        self.switch.ee.add_listener(LinkEvent.LINK_READY, self._link_ready)

        await self.switch.write(
            [
                self._station_entry(),
                self._srv6_sid_entry(),
                self._routes(),
                self._link_stations(),
                self._ndp_replies(),
            ]
        )

    def _station_entry(self):
        return +fy.P4TableEntry(
            "my_station_table",
            match=fy.P4TableMatch(dst_addr=netcfg.get_station_mac(self.switch)),
            action=fy.P4TableAction("NoAction"),
        )

    def _srv6_sid_entry(self):
        sid = netcfg.get_sid(self.switch)
        return +fy.P4TableEntry(
            "srv6_my_sid",
            match=fy.P4TableMatch(dst_addr=sid),
            action=fy.P4TableAction("srv6_end"),
        )

    def _ndp_replies(self):
        station_mac = netcfg.get_station_mac(self.switch)
        return [
            +fy.P4TableEntry(
                "ndp_reply_table",
                match=fy.P4TableMatch(target_ipv6_addr=ipaddr),
                action=fy.P4TableAction("ndp_ns_to_na", target_mac=station_mac),
            )
            for ipaddr in netcfg.get_addresses(self.switch)
        ]

    def _routes(self):
        if netcfg.is_spine(self.switch):
            return self._spine_routes()
        else:
            return [self._leaf_routes(), self._internal_routes()]

    def _spine_routes(self):
        return [
            +fy.P4TableEntry(
                "routing_v6_table",
                match=fy.P4TableMatch(dst_addr=net),
                action=fy.P4TableAction(
                    "set_next_hop", dmac=netcfg.get_station_mac(leaf)
                ),
            )
            for leaf in netcfg.leaf_switches()
            for net in netcfg.get_networks(leaf, include_sid=True)
        ]

    def _leaf_routes(self):
        other_networks = {
            net
            for leaf in netcfg.leaf_switches()
            if leaf is not self.switch
            for net in netcfg.get_networks(leaf)
        }

        spine_actions = [
            1 * fy.P4TableAction("set_next_hop", dmac=netcfg.get_station_mac(spine))
            for spine in netcfg.spine_switches()
        ]

        return [
            +fy.P4TableEntry(
                "routing_v6_table",
                match=fy.P4TableMatch(dst_addr=net),
                action=fy.P4IndirectAction(spine_actions),
            )
            for net in other_networks
        ]

    def _internal_routes(self):
        "Add SRv6 internal routes."
        return [
            +fy.P4TableEntry(
                "routing_v6_table",
                match=fy.P4TableMatch(dst_addr=netcfg.get_sid(spine)),
                action=fy.P4TableAction(
                    "set_next_hop", dmac=netcfg.get_station_mac(spine)
                ),
            )
            for spine in netcfg.spine_switches()
        ]

    def _link_stations(self):
        controller = fy.Controller.current()
        links = [
            (event.local_port, controller[event.remote_switch])
            for event in self.switch.manager["link"].links.values()
        ]

        return [
            +fy.P4TableEntry(
                "l2_exact_table",
                match=fy.P4TableMatch(dst_addr=netcfg.get_station_mac(sw)),
                action=fy.P4TableAction("set_egress_port", port_num=port),
            )
            for port, sw in links
        ]

    async def _link_ready(self, switch: fy.Switch, event: LinkReady):
        "Handle the LINK_READY event."
        assert switch is self.switch

        controller = fy.Controller.current()
        sw = controller[event.remote_switch]

        await self.switch.write(
            [
                +fy.P4TableEntry(
                    "l2_exact_table",
                    match=fy.P4TableMatch(dst_addr=netcfg.get_station_mac(sw)),
                    action=fy.P4TableAction(
                        "set_egress_port", port_num=event.local_port
                    ),
                )
            ]
        )
