from finsy import pbuf
from finsy.gnmipath import gNMIPath


def test_path_basics():
    path1 = gNMIPath("interfaces/interface[a=A][b=B]/state/counters")

    assert pbuf.to_dict(path1.path) == {
        "elem": [
            {"name": "interfaces"},
            {"name": "interface", "key": {"a": "A", "b": "B"}},
            {"name": "state"},
            {"name": "counters"},
        ]
    }

    path2 = gNMIPath(path1.path)
    assert path2.path is path1.path

    path3 = path2.copy()
    assert path3 == path2
    assert path3.path is not path2.path


def test_path_repr():
    assert repr(gNMIPath()) == "/"
    assert repr(gNMIPath("interfaces/interface")) == "interfaces/interface"
    assert repr(gNMIPath("/interfaces/")) == "interfaces"


def test_path_properties():
    path1 = gNMIPath("interfaces/interface/state/oper-status")

    assert path1.last == "oper-status"
    assert path1.first == "interfaces"


def test_path_keys():
    path1 = gNMIPath("interfaces/interface[name=eth0]/state/oper-status")

    assert path1[2] == "state"
    assert path1["interface", "name"] == "eth0"
    assert path1[1, "name"] == "eth0"

    path2 = path1.key("interface", name="eth1")
    assert path2["interface", "name"] == "eth1"
    assert path2 != path1
