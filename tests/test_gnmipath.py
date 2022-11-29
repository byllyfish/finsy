import pytest

from finsy import pbuf
from finsy.gnmipath import GNMIPath


def test_path_basics():
    path1 = GNMIPath("interfaces/interface[a=A][b=B]/state/counters")

    assert pbuf.to_dict(path1.path) == {
        "elem": [
            {"name": "interfaces"},
            {"name": "interface", "key": {"a": "A", "b": "B"}},
            {"name": "state"},
            {"name": "counters"},
        ]
    }

    path2 = GNMIPath(path1.path)
    assert path2.path is path1.path

    path3 = path2.copy()
    assert path3 == path2
    assert path3.path is not path2.path

    assert len(path1) == 4


def test_path_copy():
    "Test GNMIPath copy constructor."
    path1 = GNMIPath("a/b[x=1]/c")
    path2 = GNMIPath(path1)
    path3 = path1.copy()

    assert path1 == path2
    assert path1 == path3

    assert path1 is not path2
    assert path1 is not path3
    assert path1.path is not path2.path
    assert path1.path is not path3.path

    path4 = GNMIPath(path1, origin="origin", target="target")
    assert path4 != path1
    assert path4.path.elem == path1.path.elem
    assert path4.origin == "origin" and path1.origin == ""
    assert path4.target == "target" and path1.target == ""

    path5 = path4.copy()
    path5 is not path4
    assert path5.path == path4.path
    assert path5.path is not path4.path


def test_path_repr():
    assert repr(GNMIPath()) == "GNMIPath('/')"
    assert repr(GNMIPath("interfaces/interface")) == "GNMIPath('interfaces/interface')"
    assert repr(GNMIPath("/interfaces/")) == "GNMIPath('interfaces')"

    assert (
        repr(GNMIPath("/a/b", origin="c", target="d"))
        == "GNMIPath('a/b', origin='c', target='d')"
    )


def test_path_str():
    assert str(GNMIPath()) == "/"
    assert str(GNMIPath("interfaces/interface")) == "interfaces/interface"
    assert str(GNMIPath("/interfaces/")) == "interfaces"


def test_path_properties():
    path1 = GNMIPath("interfaces/interface/state/oper-status")

    assert path1.last == "oper-status"
    assert path1.first == "interfaces"


def test_path_keys():
    path1 = GNMIPath("interfaces/interface[name=eth0]/state/oper-status")

    assert path1[2] == "state"
    assert path1["interface", "name"] == "eth0"
    assert path1[1, "name"] == "eth0"
    assert path1["name"] == "eth0"

    path2 = path1.set("interface", name="eth1")
    assert path2["interface", "name"] == "eth1"
    assert path2 != path1
    assert path2["name"] == "eth1"

    path3 = path1.set(1, name="eth2")
    assert path3["interface", "name"] == "eth2"
    assert path3["name"] == "eth2"
    assert str(path3) == "interfaces/interface[name=eth2]/state/oper-status"


def test_path_keys2():
    path1 = GNMIPath("a/b[name=x][alias=z]/c[name=y]")

    path2 = path1.set(name="eth0")
    assert path2 == GNMIPath("a/b[name=eth0][alias=z]/c[name=eth0]")

    with pytest.raises(ValueError, match="no keys found in path"):
        path1.set(x="d")

    with pytest.raises(ValueError, match="empty keys"):
        path1.set()


def test_path_origin():
    path1 = GNMIPath("interfaces", origin="abc", target="def")

    assert path1.origin == "abc"
    assert path1.target == "def"

    assert pbuf.to_dict(path1.path) == {
        "elem": [{"name": "interfaces"}],
        "origin": "abc",
        "target": "def",
    }


def test_path_equals():
    path1 = GNMIPath("a")
    path2 = GNMIPath("a", origin="b")
    path3 = GNMIPath("a")

    assert path1 == path3
    assert path1 != path2
    assert path1.path != path2.path
    assert not path1 == 3


def test_path_getitem():
    path1 = GNMIPath("interfaces/interface[a=A][b=B]/state")

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

    with pytest.raises(KeyError, match="c"):
        path1["interface", "c"]

    with pytest.raises(IndexError):
        path1[3]

    with pytest.raises(TypeError, match="invalid key type"):
        path1["interface", 3]  # type: ignore


def test_path_slice():
    "Test __getitem__ with slice."

    path1 = GNMIPath("interfaces/interface[a=A][b=B]/state")

    path2 = path1[:]
    assert path1 is not path2
    assert path1 == path2

    assert path1[0:1] == GNMIPath("interfaces")
    assert path1[0:2] == GNMIPath("interfaces/interface[a=A][b=B]")
    assert path1[1:2] == GNMIPath("interface[a=A][b=B]")
    assert path1[1:] == GNMIPath("interface[a=A][b=B]/state")
    assert path1[:1] == GNMIPath("interfaces")
    assert path1[::2] == GNMIPath("interfaces/state")
    assert path1[:-1] == GNMIPath("interfaces/interface[a=A][b=B]")


def test_hash():
    "Test hash operation on GNMIPath."

    path1 = GNMIPath("a")
    path2 = GNMIPath("a", origin="b")
    path3 = GNMIPath("a")

    assert hash(path1) == hash(path3)
    assert hash(path1) == hash(path2)  # N.B. origin not included in hash

    path4 = GNMIPath("a/b[name=s]")
    path5 = GNMIPath("a/b")

    assert hash(path4) != hash(path5)
    assert path4 != path5


def test_truediv():
    "Test path append operator (/)."

    path1 = GNMIPath("a")
    path2 = GNMIPath("b[x=1]")
    path3 = path1 / path2
    assert path3 == GNMIPath("a/b[x=1]")

    path4 = path3 / "r/s/t"
    assert str(path4) == "a/b[x=1]/r/s/t"


def test_rtruediv():
    "Test path prepend operator (/)."

    path1 = GNMIPath("b[x=1]")
    path2 = "a" / path1
    assert path2 == GNMIPath("a/b[x=1]")

    path3 = "r/s/t" / path2
    assert str(path3) == "r/s/t/a/b[x=1]"


def test_contains():
    "Test path `in` operator."

    path1 = GNMIPath("a/b/c")
    assert "b" in path1
    assert "z" not in path1


def test_truediv_origin():
    "Test path append operator (/) with origin."

    path1 = GNMIPath("a", origin="ao", target="at")
    path2 = GNMIPath("b", origin="bo", target="bt")

    path3 = path1 / path2
    assert path3 == GNMIPath("a/b", origin="ao", target="at")
    assert path3 is not path1

    path4 = GNMIPath("c") / path1
    assert path4 == GNMIPath("c/a")
