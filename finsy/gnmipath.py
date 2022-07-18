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

from typing_extensions import Self

from finsy import gnmistring
from finsy.proto import gnmi


class gNMIPath:
    """Concrete class for working with `gnmi.Path` objects.

    A `gNMIPath` should be treated as an immutable object. You can access
    the wrapped `gnmi.Path` protobuf class using the `.path` property.

    You can construct a gNMIPath object from a `gnmi.Path` directly.
    ```
    path = gNMIPath(update.path)
    ```

    You can construct a gNMIPath from a string:
    ```
    path = gNMIPath("interfaces/interface[name=eth1]/state")
    ```

    You can create paths by using an existing path as a template, without
    modifying the original path:
    ```
    operStatus = gNMIPath("interfaces/interface/state/oper-status")
    path = operStatus.key("interface", name="eth1")
    ```

    Use [] to access the name/key of path elements:
    ```
    path[1] == "interface"
    path["interface", "name"] == "eth1"
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

        result = self.copy()
        result.path.elem[elem].key.update(kwds)
        return result

    def copy(self) -> Self:
        "Return a copy of the path."
        new_path = gnmi.Path()
        new_path.CopyFrom(self.path)
        return gNMIPath(new_path)

    def __getitem__(self, key: int | tuple[int | str, str]) -> str:
        "Return the specified element or key value."
        match key:
            case int(idx):
                return self.path.elem[idx].name
            case (int(idx), str(k)):
                return self.path.elem[idx].key[k]
            case (str(name), str(k)):
                return self.path.elem[_find_index(name, self.path)].key[k]
            case _:
                raise TypeError(f"invalid key type: {key!r}")

    def __eq__(self, rhs: Self) -> bool:
        "Return True if path's are equal."
        if not isinstance(rhs, gNMIPath):
            return False
        return self.path == rhs.path  # pyright: ignore[reportUnknownVariableType]

    def __repr__(self) -> str:
        "Return string representation of path."
        return gnmistring.to_str(self.path)


def _find_index(value: str, path: gnmi.Path) -> int:
    "Return index in path of specified element `value`."
    for i, elem in enumerate(path.elem):
        if elem.name == value:
            return i
    raise KeyError(value)
