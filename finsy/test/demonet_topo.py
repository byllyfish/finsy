"""Custom Mininet file that loads topology from `demonet_topo.json` file.

For compatibility, this file MUST support BOTH Python 2.7 and Python 3+.
"""

import json
import os.path

from mininet.node import Host
from mininet.topo import Topo

# Name of file to load topology from. The file should be located in the same
# directory as this python file.
DEMONET_JSON = "demonet_topo.json"


class DemoHost(Host):
    "Demo host."

    def __init__(self, name, **kwds):
        super(DemoHost, self).__init__(name, **kwds)

        # Do not generate an IPv6 link-local address when interface goes UP.
        # (This does not affect interface 'lo', which already exists.)
        self.cmd("sysctl -w net.ipv6.conf.default.addr_gen_mode=1")

    def config(self, config=None, **_params):
        """Load the host config.

        This subclass does NOT invoke the superclass method. Instead, we
        configure everything here and then bring the default interface UP.
        """

        # Bring the default interface down.
        intf = self.defaultIntf()
        intf.ifconfig("down")

        # Rename the default interface.
        old_ifname = intf.name
        ifname = config["ifname"]
        intf.name = ifname
        self.nameToIntf[ifname] = self.nameToIntf.pop(old_ifname)
        self.cmd("ip link set %s name %s" % (old_ifname, ifname))

        # Disable offload features.
        for feature in config["disable_offload"]:
            self.cmd("ethtool --offload %s %s off" % (ifname, feature))

        # Set the MAC address.
        mac = config["mac"]
        if mac == "auto":
            mac = _params.get("mac")
        if mac:
            intf.mac = mac
            intf.ifconfig("hw", "ether", mac)

        # Reset the addr_gen_mode if we actually want IPv6 link local address.
        if config["ipv6_linklocal"]:
            self.cmd("sysctl -w net.ipv6.conf.%s.addr_gen_mode=0" % ifname)

        # Bring the default interface back up.
        intf.ifconfig("up")

        # Bring the loopback interface up.
        self.cmd("ifconfig lo up")

        # Configure IPv4.
        ipv4 = config["ipv4"]
        if ipv4 == "auto":
            ipv4 = _params.get("ip")
        if ipv4:
            intf.setIP(ipv4)

        ipv4_gw = config["ipv4_gw"]
        if ipv4_gw:
            self.setDefaultRoute("dev %s via %s" % (ifname, ipv4_gw))

        static_arp = config["static_arp"]
        if static_arp:
            for ip, mac in static_arp.items():
                self.setARP(ip, mac)

        # Configure IPv6.
        ipv6 = config["ipv6"]
        if ipv6:
            self.cmd("ip -6 addr add %s dev %s" % (ipv6, ifname))

        ipv6_gw = config["ipv6_gw"]
        if ipv6_gw:
            self.cmd("ip -6 route add default via %s" % ipv6_gw)

        if ipv6 and not ipv4:
            # Make IPv6 address the default IP address so ping will work.
            def updateIP():
                return ipv6.split("/")[0]

            intf.updateIP = updateIP


class DemoTopo(Topo):
    "Demo topology."

    def __init__(self, *args, **kwargs):
        "Load topology from `DEMONET_JSON` file."
        super(DemoTopo, self).__init__(*args, **kwargs)

        json_file = os.path.join(os.path.dirname(__name__), DEMONET_JSON)
        with open(json_file) as fp:
            json_config = json.load(fp)

        for config in json_config:
            kind = config["kind"]
            if kind == "switch":
                self.addSwitch(config["name"], **config["params"])
            elif kind == "host":
                self.addHost(config["name"], cls=DemoHost, config=config)
                if config["switch"]:
                    self.addLink(config["switch"], config["name"])
            elif kind == "link":
                self.addLink(config["start"], config["end"])
            elif kind == "image":
                pass  # ignore image specification
            else:
                print("!!! DemoTopo is ignoring %r directive." % kind)


topos = {"demonet": DemoTopo}
