import os

import finsy as fy

from . import netcfg
from .link import LinkEvent, LinkReady


class RouteManagerOneShot:
    switch: fy.Switch

    def __init__(self, switch: fy.Switch):
        self.switch = switch

    async def run(self):
        self.switch.ee.add_listener(LinkEvent.LINK_READY, self._link_ready)

        await self._init_profiles()

        await self.switch.write(
            [
                self._station_entry(),
                self._srv6_sid_entry(),
                self._routes(),
                self._link_stations(),
                self._ndp_replies(),
            ]
        )

    async def _init_profiles(self):
        "Allow subclass to add ActionProfileGroups and ActionProfileMembers."
        # Base class uses one-shot selector programming. Nothing to do here.

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


class RouteManagerActionProfile(RouteManagerOneShot):
    "Version of RouteManager that uses ActionProfiles instead of one shots."

    LEAF_GROUP_ID = 1
    members: dict[fy.MACAddress, int]

    def __init__(self, switch: fy.Switch):
        super().__init__(switch)
        self.members = {}

    async def _init_profiles(self):
        "Write members and groups before we add table entries."
        if netcfg.is_spine(self.switch):
            await self._init_spine_profiles()
        else:
            await self._init_leaf_profiles()

    async def _init_spine_profiles(self):
        "Write profile members for spine switches."
        macs = (netcfg.get_station_mac(leaf) for leaf in netcfg.leaf_switches())
        members = dict((mac, i + 1) for (i, mac) in enumerate(macs))

        await self.switch.write(
            +fy.P4ActionProfileMember(
                "ecmp_selector",
                member_id=i,
                action=fy.P4TableAction("set_next_hop", dmac=mac),
            )
            for (mac, i) in members.items()
        )

        self.members = members

    async def _init_leaf_profiles(self):
        "Write profile members for leaf switches."
        macs = (netcfg.get_station_mac(spine) for spine in netcfg.spine_switches())
        members = dict((mac, i + 1) for (i, mac) in enumerate(macs))

        await self.switch.write(
            +fy.P4ActionProfileMember(
                "ecmp_selector",
                member_id=i,
                action=fy.P4TableAction("set_next_hop", dmac=mac),
            )
            for (mac, i) in members.items()
        )

        # Add the group in a separate Write message.
        await self.switch.write(
            [
                +fy.P4ActionProfileGroup(
                    "ecmp_selector",
                    group_id=self.LEAF_GROUP_ID,
                    members=[
                        fy.P4Member(member_id=i, weight=1) for i in members.values()
                    ],
                )
            ]
        )

        self.members = members

    def _spine_routes(self):
        return [
            +fy.P4TableEntry(
                "routing_v6_table",
                match=fy.P4TableMatch(dst_addr=net),
                action=fy.P4IndirectAction(
                    member_id=self.members[netcfg.get_station_mac(leaf)]
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

        return [
            +fy.P4TableEntry(
                "routing_v6_table",
                match=fy.P4TableMatch(dst_addr=net),
                action=fy.P4IndirectAction(group_id=self.LEAF_GROUP_ID),
            )
            for net in other_networks
        ]

    def _internal_routes(self):
        "Add SRv6 internal routes."
        return [
            +fy.P4TableEntry(
                "routing_v6_table",
                match=fy.P4TableMatch(dst_addr=netcfg.get_sid(spine)),
                action=fy.P4IndirectAction(
                    member_id=self.members[netcfg.get_station_mac(spine)]
                ),
            )
            for spine in netcfg.spine_switches()
        ]


if os.environ.get("NGSDN_USE_ACTIONPROFILE"):
    RouteManager = RouteManagerActionProfile
else:
    RouteManager = RouteManagerOneShot
