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

    assert len(path1) == 4


def test_path_repr():
    assert repr(gNMIPath()) == "gNMIPath('/')"
    assert repr(gNMIPath("interfaces/interface")) == "gNMIPath('interfaces/interface')"
    assert repr(gNMIPath("/interfaces/")) == "gNMIPath('interfaces')"

    assert (
        repr(gNMIPath("/a/b", origin="c", target="d"))
        == "gNMIPath('a/b', origin='c', target='d')"
    )


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
    assert path1["name"] == "eth0"

    path2 = path1.set("interface", name="eth1")
    assert path2["interface", "name"] == "eth1"
    assert path2 != path1
    assert path2["name"] == "eth1"


def test_path_keys2():
    path1 = gNMIPath("a/b[name=x][alias=z]/c[name=y]")

    path2 = path1.set(name="eth0")
    assert path2 == gNMIPath("a/b[name=eth0][alias=z]/c[name=eth0]")

    with pytest.raises(ValueError, match="no keys found in path"):
        path1.set(x="d")

    with pytest.raises(ValueError, match="empty keys"):
        path1.set()


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
    path3 = gNMIPath("a")

    assert path1 == path3
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
    assert path1["a"] == "A"
    assert path1["b"] == "B"

    with pytest.raises(KeyError, match="a"):
        path1[0, "a"]

    with pytest.raises(KeyError, match="b"):
        path1["interfaces", "b"]

    with pytest.raises(KeyError, match="x"):
        path1["x", "a"]

    with pytest.raises(KeyError, match="x"):
        path1["x"]

    with pytest.raises(IndexError):
        path1[3]

    with pytest.raises(TypeError, match="invalid key type"):
        path1["interface", 3]  # type: ignore


def test_path_slice():
    "Test __getitem__ with slice."

    path1 = gNMIPath("interfaces/interface[a=A][b=B]/state")

    path2 = path1[:]
    assert path1 is not path2
    assert path1 == path2

    assert path1[0:1] == gNMIPath("interfaces")
    assert path1[0:2] == gNMIPath("interfaces/interface[a=A][b=B]")
    assert path1[1:2] == gNMIPath("interface[a=A][b=B]")
    assert path1[1:] == gNMIPath("interface[a=A][b=B]/state")
    assert path1[:1] == gNMIPath("interfaces")
    assert path1[::2] == gNMIPath("interfaces/state")
    assert path1[:-1] == gNMIPath("interfaces/interface[a=A][b=B]")


def test_hash():
    "Test hash operation on gNMIPath."

    path1 = gNMIPath("a")
    path2 = gNMIPath("a", origin="b")
    path3 = gNMIPath("a")

    assert hash(path1) == hash(path3)
    assert hash(path1) == hash(path2)  # N.B. origin not included in hash

    path4 = gNMIPath("a/b[name=s]")
    path5 = gNMIPath("a/b")

    assert hash(path4) != hash(path5)
    assert path4 != path5


def test_truediv():
    "Test path append operator (/)."

    path1 = gNMIPath("a")
    path2 = gNMIPath("b[x=1]")
    path3 = path1 / path2
    assert path3 == gNMIPath("a/b[x=1]")

    path4 = path3 / "r/s/t"
    assert str(path4) == "a/b[x=1]/r/s/t"


def test_rtruediv():
    "Test path prepend operator (/)."

    path1 = gNMIPath("b[x=1]")
    path2 = "a" / path1
    assert path2 == gNMIPath("a/b[x=1]")

    path3 = "r/s/t" / path2
    assert str(path3) == "r/s/t/a/b[x=1]"


def test_contains():
    "Test path `in` operator."

    path1 = gNMIPath("a/b/c")
    assert "b" in path1
    assert "z" not in path1
