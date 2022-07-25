"Implements the gNMIPath class."

# Copyright (c) 2022 Bill Fisher
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

from typing_extensions import Self

from finsy import gnmistring
from finsy.proto import gnmi


class gNMIPath:
    """Concrete class for working with `gnmi.Path` objects.

    A `gNMIPath` should be treated as an immutable object. You can access
    the wrapped `gnmi.Path` protobuf class using the `.path` property.
    `gNMIPath` objects are hashable, but you must be careful that you do not
    mutate them via the underlying `gnmi.Path`.

    You can construct a gNMIPath from a string:
    ```
    path = gNMIPath("interfaces/interface[name=eth1]/state")
    ```

    You can construct a gNMIPath object from a `gnmi.Path` directly.
    ```
    path = gNMIPath(update.path)
    ```

    You can create paths by using an existing path as a template, without
    modifying the original path. Use the `key` method:
    ```
    operStatus = gNMIPath("interfaces/interface/state/oper-status")
    path = operStatus.key("interface", name="eth1")
    ```

    Use [] to access the name/key of path elements:
    ```
    path[1] == "interface"
    path["interface", "name"] == "eth1"
    path["interface"] == { "name": "eth1" }
    ```
    """

    path: gnmi.Path
    "The underlying `gnmi.Path` protobuf representation."

    def __init__(
        self,
        path: gnmi.Path | str = "",
        *,
        origin: str = "",
        target: str = "",
    ):
        "Construct a `gNMIPath` from a string or `gnmi.Path`."
        if isinstance(path, str):
            path = gnmistring.parse(path)

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

    def key(self, elem: str | int, **kwds: str) -> Self:
        "Construct a new gNMIPath with keys set for the given elem."
        if isinstance(elem, str):
            elem = _find_index(elem, self.path)

        # Convert kwds values to string, if necessary.
        new_kwds = {key: str(val) for key, val in kwds.items()}
        result = self.copy()
        result.path.elem[elem].key.update(new_kwds)
        return result

    def copy(self) -> Self:
        "Return a copy of the path."
        new_path = gnmi.Path()
        new_path.CopyFrom(self.path)
        return gNMIPath(new_path)

    def __getitem__(
        self,
        key: int | str | tuple[int | str, str] | slice,
    ) -> str | dict[str, str] | Self:
        "Return the specified element or key value."
        match key:
            case int(idx):
                return self.path.elem[idx].name
            case str(name):
                return dict(self.path.elem[_find_index(name, self.path)].key)
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
            case other:
                if isinstance(other, slice):
                    return self._slice(other.start, other.stop, other.step)
                raise TypeError(f"invalid key type: {other!r}")

    def __eq__(self, rhs: Self) -> bool:
        "Return True if path's are equal."
        if not isinstance(rhs, gNMIPath):
            return False
        return self.path == rhs.path  # pyright: ignore[reportUnknownVariableType]

    def __hash__(self) -> int:
        "Return hash of path."
        return hash(tuple(_to_tuple(elem) for elem in self.path.elem))

    def __repr__(self) -> str:
        "Return string representation of path."
        return f"gNMIPath({gnmistring.to_str(self.path)!r})"

    def __str__(self) -> str:
        "Return path as string."
        return gnmistring.to_str(self.path)

    def __len__(self) -> int:
        "Return the length of the path."
        return len(self.path.elem)

    def __truediv__(self, rhs: Self | str) -> Self:
        "Append values to end of path."
        if not isinstance(rhs, gNMIPath):
            rhs = gNMIPath(rhs)

        result = gnmi.Path(elem=itertools.chain(self.path.elem, rhs.path.elem))
        return gNMIPath(result)

    def __rtruediv__(self, lhs: str) -> Self:
        "Prepend values to the beginning of the path."
        path = gNMIPath(lhs)

        result = gnmi.Path(elem=itertools.chain(path.path.elem, self.path.elem))
        return gNMIPath(result)

    def _slice(self, start: int | None, stop: int | None, step: int | None) -> Self:
        "Return specified slice of gNMIPath."

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

        return gNMIPath(path)


def _find_index(value: str, path: gnmi.Path) -> int:
    "Return index in path of specified element `value`."
    for i, elem in enumerate(path.elem):
        if elem.name == value:
            return i
    raise KeyError(value)


def _to_tuple(elem: gnmi.PathElem) -> tuple[str, ...]:
    "Return a tuple of name and key'd values."
    return (elem.name,) + tuple(sorted(elem.key.values()))
