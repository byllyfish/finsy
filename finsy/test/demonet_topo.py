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

    def config(self, config=None, **params):
        "Load host config."
        if config["mac"]:
            params["mac"] = config["mac"]

        params["ip"] = config["ipv4"]
        if not params["ip"]:
            del params["ip"]

        # Disable IPv6.
        if config["disable_ipv6"] and not config["ipv6"]:
            self.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")

        # Let superclass configure the IPv4 and MAC address.
        super(DemoHost, self).config(**params)

        # Configure the interface.
        ifname = config["ifname"]
        self.defaultIntf().rename(ifname)

        for feature in config["disable_offload"]:
            self.cmd("ethtool --offload %s %s off" % (ifname, feature))

        # Configure IPv4.
        ipv4_gw = config["ipv4_gw"]
        if ipv4_gw:
            self.setDefaultRoute("dev %s via %s" % (ifname, ipv4_gw))

        static_arp = config["static_arp"]
        if static_arp:
            for ip, mac in static_arp.items():
                self.setARP(ip, mac)


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
                self.addSwitch(config["name"])
            elif kind == "host":
                self.addHost(config["name"], cls=DemoHost, config=config)
                if config["switch"]:
                    self.addLink(config["switch"], config["name"])
            elif kind == "link":
                self.addLink(config["start"], config["end"])
            elif kind == "image":
                pass  # ignore image specification
            else:
                print("DemoTopo loader is ignoring: %r" % kind)


topos = {"demonet": DemoTopo}
