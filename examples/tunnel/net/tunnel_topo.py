from mininet.node import Host
from mininet.topo import Topo


class TunnelHost(Host):
    "Tunnel host with default gateway / arp support."

    def config(self, ip_gw=None, arp=None, **params):
        super(TunnelHost, self).config(**params)

        self.defaultIntf().rename("eth0")
        for feature in ["rx", "tx", "sg"]:
            self.cmd("ethtool --offload eth0 %s off" % feature)

        if ip_gw:
            self.setDefaultRoute("dev eth0 via %s" % ip_gw)

        if arp:
            for ip, mac in arp.items():
                self.setARP(ip, mac)


class TunnelTopo(Topo):
    "3 host triangle topology."

    def __init__(self, *args, **kwargs):
        super(TunnelTopo, self).__init__(*args, **kwargs)

        s1 = self.addSwitch("s1")
        s2 = self.addSwitch("s2")
        s3 = self.addSwitch("s3")

        self.addLink(s1, s2)
        self.addLink(s1, s3)
        self.addLink(s2, s3)

        h1 = self.addHost(
            "h1",
            cls=TunnelHost,
            mac="08:00:00:00:01:11",
            ip="10.0.1.1/24",
            ip_gw="10.0.1.10",
            arp={"10.0.1.10": "08:00:00:00:01:00"},
        )
        h2 = self.addHost(
            "h2",
            cls=TunnelHost,
            mac="08:00:00:00:02:22",
            ip="10.0.2.2/24",
            ip_gw="10.0.2.20",
            arp={"10.0.2.20": "08:00:00:00:02:00"},
        )
        h3 = self.addHost(
            "h3",
            cls=TunnelHost,
            mac="08:00:00:00:03:33",
            ip="10.0.3.3/24",
            ip_gw="10.0.3.30",
            arp={"10.0.3.30": "08:00:00:00:03:00"},
        )

        self.addLink(h1, s1)
        self.addLink(h2, s2)
        self.addLink(h3, s3)


topos = {"tunnel": TunnelTopo}
