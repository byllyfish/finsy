from pathlib import Path

from finsy.test import demonet as dn

SWITCH_PARAMS = {"cpuport": 255}

PROM_YML = Path(__file__).parent / "prometheus.yml"


DEMONET = [
    # Use stratum.
    dn.Image("docker.io/opennetworking/mn-stratum"),
    # 2x2 fabric topology.
    dn.Switch("leaf1", params=SWITCH_PARAMS),
    dn.Switch("leaf2", params=SWITCH_PARAMS),
    dn.Switch("spine1", params=SWITCH_PARAMS),
    dn.Switch("spine2", params=SWITCH_PARAMS),
    dn.Link("spine1", "leaf1"),
    dn.Link("spine1", "leaf2"),
    dn.Link("spine2", "leaf1"),
    dn.Link("spine2", "leaf2"),
    # IPv6 hosts attached to leaf 1.
    dn.Host(
        "h1a",
        "leaf1",
        mac="00:00:00:00:00:1A",
        ipv4="",
        ipv6="2001:1:1::a/64",
        ipv6_gw="2001:1:1::ff",
    ),
    dn.Host(
        "h1b",
        "leaf1",
        mac="00:00:00:00:00:1B",
        ipv4="",
        ipv6="2001:1:1::b/64",
        ipv6_gw="2001:1:1::ff",
    ),
    dn.Host(
        "h1c",
        "leaf1",
        mac="00:00:00:00:00:1C",
        ipv4="",
        ipv6="2001:1:1::c/64",
        ipv6_gw="2001:1:1::ff",
    ),
    dn.Host(
        "h2",
        "leaf1",
        mac="00:00:00:00:00:20",
        ipv4="",
        ipv6="2001:1:2::1/64",
        ipv6_gw="2001:1:2::ff",
    ),
    # IPv6 hosts attached to leaf 2.
    dn.Host(
        "h3",
        "leaf2",
        mac="00:00:00:00:00:30",
        ipv4="",
        ipv6="2001:2:3::1/64",
        ipv6_gw="2001:2:3::ff",
    ),
    dn.Host(
        "h4",
        "leaf2",
        mac="00:00:00:00:00:40",
        ipv4="",
        ipv6="2001:2:4::1/64",
        ipv6_gw="2001:2:4::ff",
    ),
    # Add pod with prometheus and grafana containers.
    dn.Pod(
        "demo_pod",
        images=[
            # Prometheus container (port 9090)
            dn.Image(
                "docker.io/prom/prometheus",
                files=[
                    dn.CopyFile(PROM_YML, "/etc/prometheus/prometheus.yml"),
                ],
            ),
            # Grafana container (port 3000)
            dn.Image("docker.io/grafana/grafana"),
        ],
        publish=[3000, 9090],
    ),
]


if __name__ == "__main__":
    dn.run(DEMONET)
