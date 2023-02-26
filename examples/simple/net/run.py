from finsy.test import demonet as dn

DEMONET = [
    dn.Image("docker.io/opennetworking/p4mn"),
    dn.Switch("s1"),
    dn.Host(
        "h1",
        "s1",
        mac="00:00:00:00:00:01",
        ipv4="10.0.1.10/24",
        ipv4_gw="10.0.1.1",
        static_arp={"10.0.1.1": "00:00:00:aa:bb:cc"},
    ),
    dn.Host(
        "h2",
        "s1",
        mac="00:00:00:00:00:02",
        ipv4="10.0.2.10/24",
        ipv4_gw="10.0.2.1",
        static_arp={"10.0.2.1": "00:00:00:aa:bb:cc"},
    ),
]

if __name__ == "__main__":
    dn.run(DEMONET)
