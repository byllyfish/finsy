import pytest
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


def test_path_str():
    assert str(gNMIPath()) == "/"
    assert str(gNMIPath("interfaces/interface")) == "interfaces/interface"
    assert str(gNMIPath("/interfaces/")) == "interfaces"


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


def test_path_origin():
    path1 = gNMIPath("interfaces", origin="abc", target="def")

    assert path1.origin == "abc"
    assert path1.target == "def"

    assert pbuf.to_dict(path1.path) == {
        "elem": [{"name": "interfaces"}],
        "origin": "abc",
        "target": "def",
    }


def test_path_equals():
    path1 = gNMIPath("a")
    path2 = gNMIPath("a", origin="b")

    assert path1 != path2
    assert path1.path != path2.path
    assert not path1 == 3


def test_path_getitem():
    path1 = gNMIPath("interfaces/interface[a=A][b=B]/state")

    assert path1[0] == "interfaces"
    assert path1[1] == "interface"
    assert path1[2] == "state"

    assert path1[1, "a"] == "A"
    assert path1[1, "b"] == "B"
    assert path1["interface", "a"] == "A"
    assert path1["interface", "b"] == "B"

    assert path1[0, "a"] == ""
    assert path1["interfaces", "b"] == ""

    with pytest.raises(TypeError, match="invalid key type"):
        path1["interface"]  # type: ignore

    with pytest.raises(KeyError, match="x"):
        path1["x", "a"]

    with pytest.raises(IndexError):
        path1[3]

    with pytest.raises(TypeError, match="invalid key type"):
        path1["interface", 3]  # type: ignore
