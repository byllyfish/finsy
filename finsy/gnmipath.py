"Implements the GNMIPath class."

# Copyright (c) 2022-2023 Bill Fisher
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools
from typing import Any, overload

from typing_extensions import Self

from finsy import gnmistring
from finsy.proto import gnmi


class GNMIPath:
    """Concrete class for working with `gnmi.Path` objects.

    A `GNMIPath` should be treated as an immutable object. You can access
    the wrapped `gnmi.Path` protobuf class using the `.path` property.
    `GNMIPath` objects are hashable, but you must be careful that you do not
    mutate them via the underlying `gnmi.Path`.

    You can construct a GNMIPath from a string:
    ```
    path = GNMIPath("interfaces/interface[name=eth1]/state")
    ```

    You can construct a GNMIPath object from a `gnmi.Path` directly.
    ```
    path = GNMIPath(update.path)
    ```

    You can create paths by using an existing path as a template, without
    modifying the original path. Use the `set` method:
    ```
    operStatus = GNMIPath("interfaces/interface/state/oper-status")
    path = operStatus.set("interface", name="eth1")
    ```

    Use [] to access the name/key of path elements:
    ```
    path[1] == "interface"
    path["interface", "name"] == "eth1"
    path["name"] == "eth1"
    ```
    """

    path: gnmi.Path
    "The underlying `gnmi.Path` protobuf representation."

    def __init__(
        self,
        path: gnmi.Path | str | Self = "",
        *,
        origin: str = "",
        target: str = "",
    ):
        "Construct a `GNMIPath` from a string or `gnmi.Path`."
        if isinstance(path, str):
            path = gnmistring.parse(path)
        elif isinstance(path, GNMIPath):
            path = _copy_path(path.path)

        assert isinstance(path, gnmi.Path)

        if origin:
            path.origin = origin

        if target:
            path.target = target

        self.path = path

    @property
    def first(self) -> str:
        "Return the first element of the path."
        return self.path.elem[0].name

    @property
    def last(self) -> str:
        "Return the last element of the path."
        return self.path.elem[-1].name

    @property
    def origin(self) -> str:
        "Return the path's origin."
        return self.path.origin

    @property
    def target(self) -> str:
        "Return the path's target."
        return self.path.target

    def set(self, __elem: str | int | None = None, **kwds: Any) -> Self:
        "Construct a new GNMIPath with keys set for the given elem."
        if __elem is None:
            return self._rekey(kwds)

        if isinstance(__elem, str):
            elem = _find_index(__elem, self.path)
        else:
            elem = __elem

        result = self.copy()
        keys = result.path.elem[elem].key
        keys.clear()
        keys.update({key: str(val) for key, val in kwds.items()})
        return result

    def copy(self) -> Self:
        "Return a copy of the path."
        return GNMIPath(_copy_path(self.path))

    @overload
    def __getitem__(self, key: int | str | tuple[int | str, str]) -> str:
        ...  # pragma: no cover

    @overload
    def __getitem__(self, key: slice) -> Self:
        ...  # pragma: no cover

    def __getitem__(
        self,
        key: int | str | tuple[int | str, str] | slice,
    ) -> str | Self:
        "Return the specified element or key value."
        match key:
            case int(idx):
                return self.path.elem[idx].name
            case str(name):
                return _retrieve_key(name, self.path)
            case (int(idx), str(k)):
                result = self.path.elem[idx].key.get(k)
                if result is None:
                    raise KeyError(k)
                return result
            case (str(name), str(k)):
                result = self.path.elem[_find_index(name, self.path)].key.get(k)
                if result is None:
                    raise KeyError(k)
                return result
            case slice() as s:
                return self._slice(s.start, s.stop, s.step)
            case other:  # pyright: ignore[reportUnnecessaryComparison]
                raise TypeError(f"invalid key type: {other!r}")

    def __eq__(self, rhs: Self) -> bool:
        "Return True if path's are equal."
        if not isinstance(rhs, GNMIPath):
            return False
        return self.path == rhs.path  # pyright: ignore[reportUnknownVariableType]

    def __hash__(self) -> int:
        "Return hash of path."
        return hash(tuple(_to_tuple(elem) for elem in self.path.elem))

    def __contains__(self, name: str) -> bool:
        "Return True if element name is in path."
        for elem in self.path.elem:
            if elem.name == name:
                return True
        return False

    def __repr__(self) -> str:
        "Return string representation of path."
        path = gnmistring.to_str(self.path)
        if self.target or self.origin:
            return f"GNMIPath({path!r}, origin={self.origin!r}, target={self.target!r})"
        return f"GNMIPath({path!r})"

    def __str__(self) -> str:
        "Return path as string."
        return gnmistring.to_str(self.path)

    def __len__(self) -> int:
        "Return the length of the path."
        return len(self.path.elem)

    def __truediv__(self, rhs: Self | str) -> Self:
        "Append values to end of path."
        if not isinstance(rhs, GNMIPath):
            rhs = GNMIPath(rhs)

        result = gnmi.Path(
            elem=itertools.chain(self.path.elem, rhs.path.elem),
            origin=self.origin,
            target=self.target,
        )
        return GNMIPath(result)

    def __rtruediv__(self, lhs: str) -> Self:
        "Prepend values to the beginning of the path."
        path = GNMIPath(lhs)

        result = gnmi.Path(elem=itertools.chain(path.path.elem, self.path.elem))
        return GNMIPath(result)

    def _slice(self, start: int | None, stop: int | None, step: int | None) -> Self:
        "Return specified slice of GNMIPath."
        if start is None:
            start = 0

        if stop is None:
            stop = len(self)
        elif stop < 0:
            stop = len(self) + stop

        if step is None:
            step = 1

        path = gnmi.Path()
        for i in range(start, stop, step):
            elem = self.path.elem[i]
            path.elem.append(gnmi.PathElem(name=elem.name, key=elem.key))

        return GNMIPath(path)

    def _rekey(self, keys: dict[str, Any]) -> Self:
        """Construct a new path with specified keys replaced."""
        if not keys:
            raise ValueError("empty keys")

        result = self.copy()

        found = False
        for elem in result.path.elem:
            for key, value in keys.items():
                if key in elem.key:
                    elem.key[key] = str(value)
                    found = True

        if not found:
            raise ValueError(f"no keys found in path: {keys!r}")

        return result


def _find_index(name: str, path: gnmi.Path) -> int:
    "Return index in path of specified element `name`."
    for i, elem in enumerate(path.elem):
        if elem.name == name:
            return i
    raise KeyError(name)


def _retrieve_key(key: str, path: gnmi.Path) -> str:
    "Retrieve keyed value from first element that has that key."
    for elem in path.elem:
        val = elem.key.get(key)
        if val is not None:
            return val
    raise KeyError(key)


def _to_tuple(elem: gnmi.PathElem) -> tuple[str, ...]:
    "Return a tuple of element name and values (does not include key names)."
    return (elem.name, *sorted(elem.key.values()))


def _copy_path(path: gnmi.Path) -> gnmi.Path:
    "Return a copy of given path."
    new_path = gnmi.Path()
    new_path.CopyFrom(path)
    return new_path
