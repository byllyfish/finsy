from mininet.node import Host
from mininet.topo import Topo


class SimpleHost(Host):
    "Simple host with default gateway / arp support."

    def config(self, ip_gw=None, arp=None, **params):
        super(SimpleHost, self).config(**params)

        self.defaultIntf().rename("eth0")
        for feature in ["rx", "tx", "sg"]:
            self.cmd("ethtool --offload eth0 %s off" % feature)

        if ip_gw:
            self.setDefaultRoute("dev eth0 via %s" % ip_gw)

        if arp:
            for ip, mac in arp.items():
                self.setARP(ip, mac)


class SimpleTopo(Topo):
    "Simple 2 host topology."

    def __init__(self, *args, **kwargs):
        super(SimpleTopo, self).__init__(*args, **kwargs)

        s1 = self.addSwitch("s1")
        h1 = self.addHost(
            "h1",
            cls=SimpleHost,
            mac="00:00:00:00:00:01",
            ip="10.0.1.10/24",
            ip_gw="10.0.1.1",
            arp={"10.0.1.1": "00:00:00:aa:bb:cc"},
        )
        h2 = self.addHost(
            "h2",
            cls=SimpleHost,
            mac="00:00:00:00:00:02",
            ip="10.0.2.10/24",
            ip_gw="10.0.2.1",
            arp={"10.0.2.1": "00:00:00:aa:bb:cc"},
        )
        self.addLink(h1, s1)
        self.addLink(h2, s1)


topos = {"simple": SimpleTopo}
