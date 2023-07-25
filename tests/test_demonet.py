import json

import finsy.test.demonet as dn


def test_config():
    "Test the DemoNet Config object."
    config = dn.Config(
        [
            dn.Switch("s1"),
            dn.Host("h1", "s1"),
        ]
    )

    assert json.loads(config.to_json(indent=2)) == [
        {"commands": [], "kind": "switch", "name": "s1", "params": {}},
        {
            "assigned_ipv4": "10.0.0.1/8",
            "assigned_ipv6": "",
            "assigned_mac": "00:00:00:00:00:01",
            "assigned_switch_port": 1,
            "commands": [],
            "disable_offload": ["tx", "rx", "sg"],
            "ifname": "eth0",
            "ipv4": "auto",
            "ipv4_gw": "",
            "ipv6": "",
            "ipv6_gw": "",
            "ipv6_linklocal": False,
            "kind": "host",
            "mac": "auto",
            "name": "h1",
            "static_arp": {},
            "switch": "s1",
        },
    ]
