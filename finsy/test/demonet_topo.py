"""Custom Mininet file that loads topology from `demonet_config.json` file.

For compatibility, this file MUST support BOTH Python 2.7 and Python 3+.
"""

# pylint: disable=import-error,super-with-arguments,consider-using-f-string
# pylint: disable=invalid-name,unspecified-encoding

import json
import os.path

from __main__ import SWITCHES  # pylint: disable=no-name-in-module
from mininet.node import Host
from mininet.nodelib import LinuxBridge
from mininet.topo import Topo
from mininet.util import quietRun

# Location of file to load topology from.
DEMONET_CONFIG = os.environ.get("DEMONET_CONFIG", "/tmp/demonet_config.json")


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
        mac = config["assigned_mac"]
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
        ipv4 = config["assigned_ipv4"]
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
        ipv6 = config["assigned_ipv6"]
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


class DemoBridge(LinuxBridge):
    "Demo bridge."

    def __init__(self, name, config, **kwargs):
        super(DemoBridge, self).__init__(name, **kwargs)
        self.config = config

    def start(self, _controllers):
        "Start Linux bridge."
        super(DemoBridge, self).start(_controllers)

        mac = self.config["mac"]
        if mac:
            self.cmd("ifconfig %s hw ether %s" % (self.name, mac))

        ipv4 = self.config["ipv4"]
        if ipv4:
            self.cmd("ifconfig %s %s up" % (self.name, ipv4))

        for command in self.config["commands"]:
            self.cmd(command)


class DemoTopo(Topo):
    "Demo topology."

    def __init__(self, *args, **kwargs):
        "Load topology from `demonet_config.json` file."
        super(DemoTopo, self).__init__(*args, **kwargs)

        with open(DEMONET_CONFIG) as text:
            json_config = json.load(text)

        need_bridge_utils = False

        for config in json_config:
            kind = config["kind"]
            if kind == "switch":
                model = config.get("model")
                cls = SWITCHES[model] if model else None
                self.addSwitch(config["name"], cls=cls, config=config)
            elif kind == "host":
                self.addHost(config["name"], cls=DemoHost, config=config)
                if config["switch"]:
                    self.addLink(config["switch"], config["name"])
            elif kind == "link":
                self.addLink(config["start"], config["end"])
            elif kind == "image":
                pass  # ignore image specification
            elif kind == "bridge":
                need_bridge_utils = True
                self.addSwitch(config["name"], cls=DemoBridge, config=config)
            else:
                print("!!! DemoTopo is ignoring %r directive." % kind)

        # Install bridge-utils if necessary.
        if need_bridge_utils:
            quietRun("apt-get -y -qq update", echo=True)
            quietRun("apt-get -y -qq install bridge-utils", echo=True)

        # Disable IPv6.
        quietRun("sysctl -w net.ipv6.conf.default.disable_ipv6=1")


topos = {"demonet": DemoTopo}
