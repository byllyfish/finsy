from finsy.test import demonet as dn

DEMONET = [
    dn.Switch("s1"),
    dn.Switch("s2"),
    dn.Switch("s3"),
    dn.Switch("s4"),
    dn.Host(
        "h1",
        ipv4="10.0.1.1/24",
        mac="08:00:00:00:01:11",
        ipv4_gw="10.0.1.10",
        static_arp={"10.0.1.10": "08:00:00:00:01:00"},
    ),
    dn.Host(
        "h2",
        ipv4="10.0.2.2/24",
        mac="08:00:00:00:02:22",
        ipv4_gw="10.0.2.20",
        static_arp={"10.0.2.20": "08:00:00:00:02:00"},
    ),
    dn.Host(
        "h3",
        ipv4="10.0.3.3/24",
        mac="08:00:00:00:03:33",
        ipv4_gw="10.0.3.30",
        static_arp={"10.0.3.30": "08:00:00:00:03:00"},
    ),
    dn.Host(
        "h4",
        ipv4="10.0.4.4/24",
        mac="08:00:00:00:04:44",
        ipv4_gw="10.0.4.40",
        static_arp={"10.0.4.40": "08:00:00:00:04:00"},
    ),
    dn.Link("s1", "h1"),
    dn.Link("s1", "h2"),
    dn.Link("s1", "s3"),
    dn.Link("s1", "s4"),
    dn.Link("s2", "h3"),
    dn.Link("s2", "h4"),
    dn.Link("s2", "s4"),
    dn.Link("s2", "s3"),
]

if __name__ == "__main__":
    dn.main(DEMONET)
