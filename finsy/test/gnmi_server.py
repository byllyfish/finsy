"gNMI server for testing with hard-wired responses."

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

import asyncio
import contextlib
from typing import AsyncIterator

import grpc  # pyright: ignore[reportMissingTypeStubs]

from finsy import pbuf
from finsy.proto import gnmi, gnmi_grpc

# pyright: reportIncompatibleMethodOverride=false
# pylint: disable=invalid-overridden-method,line-too-long


class GNMIServer(gnmi_grpc.gNMIServicer):
    "Test gNMI server."

    _listen_addr: str
    _server: grpc.aio.Server | None

    def __init__(self, listen_addr: str):
        "Initialize gNMI server."
        self._listen_addr = listen_addr
        self._server = None

    @contextlib.asynccontextmanager
    async def run(self):
        "Run server inside an async context manager."
        self._server = self._create_server()
        try:
            await self._server.start()
            yield self

        finally:
            await self._server.stop(0)
            self._server = None

    def _create_server(self) -> grpc.aio.Server:
        "Create AIO server."
        server = grpc.aio.server()
        gnmi_grpc.add_gNMIServicer_to_server(self, server)
        server.add_insecure_port(self._listen_addr)
        return server

    async def Get(
        self,
        request: gnmi.GetRequest,
        context: grpc.aio.ServicerContext[gnmi.GetRequest, gnmi.GetResponse],
    ) -> gnmi.GetResponse:
        "Handle gNMI GetRequest."
        if len(request.path) == 1:
            if not request.path[0].elem and request.type == gnmi.GetRequest.CONFIG:
                return pbuf.from_text(_GNMI_CONFIG_STRATUM, gnmi.GetResponse)

        return pbuf.from_text(_GNMI_INTERFACE_STUFF, gnmi.GetResponse)

    async def Set(
        self,
        request: gnmi.SetRequest,
        context: grpc.aio.ServicerContext[gnmi.SetRequest, gnmi.SetResponse],
    ) -> gnmi.SetResponse:
        "Handle the set request."
        # TODO: Does not actually do anything.
        results = (
            [
                gnmi.UpdateResult(
                    path=update.path, op=gnmi.UpdateResult.Operation.UPDATE
                )
                for update in request.update
            ]
            + [
                gnmi.UpdateResult(
                    path=update.path, op=gnmi.UpdateResult.Operation.REPLACE
                )
                for update in request.replace
            ]
            + [
                gnmi.UpdateResult(path=path, op=gnmi.UpdateResult.Operation.DELETE)
                for path in request.delete
            ]
        )

        return gnmi.SetResponse(response=results)

    async def Capabilities(
        self,
        request: gnmi.CapabilityRequest,
        context: grpc.aio.ServicerContext[
            gnmi.CapabilityRequest, gnmi.CapabilityResponse
        ],
    ) -> gnmi.CapabilityResponse:
        "Handle the capability request."
        return pbuf.from_text(_GNMI_CAPABILITIES, gnmi.CapabilityResponse)

    async def Subscribe(
        self,
        request_iterator: AsyncIterator[gnmi.SubscribeRequest],
        _context: grpc.aio.ServicerContext[
            gnmi.SubscribeRequest, gnmi.SubscribeResponse
        ],
    ) -> AsyncIterator[gnmi.SubscribeResponse]:
        "Handle the subscribe request."
        async for msg in request_iterator:
            match msg.WhichOneof("request"):
                case "subscribe":
                    mode = msg.subscribe.subscription[0].mode
                    if mode == gnmi.SubscriptionMode.SAMPLE:
                        for reply in _GNMI_SUBSCRIBE_RESPONSES_SAMPLE:
                            await asyncio.sleep(0.1)
                            yield pbuf.from_text(reply, gnmi.SubscribeResponse)
                    else:
                        for reply in _GNMI_SUBSCRIBE_RESPONSES_INITIAL:
                            yield pbuf.from_text(reply, gnmi.SubscribeResponse)
                        yield gnmi.SubscribeResponse(sync_response=True)
                        if msg.subscribe.mode != gnmi.SubscriptionList.ONCE:
                            await asyncio.sleep(0.2)
                            for reply in _GNMI_SUBSCRIBE_RESPONSES_UPDATES:
                                yield pbuf.from_text(reply, gnmi.SubscribeResponse)
                    await asyncio.sleep(5.0)
                case "poll":  # not supported
                    raise RuntimeError("not supported")
                case _:
                    pass


# Copy and pasted from Stratum responses (minor editing).

_GNMI_CONFIG_STRATUM = r"""
notification {
  update {
    path {
    }
    val {
      any_val {
        type_url: "type.googleapis.com/openconfig.Device"
        value: "\252\221\231\304\001\025\n\002s1\022\017\242\313\237\312\004\t\250\314\333\264\010\261\366\216\006\252\221\231\304\001 \n\005:lc-1\022\027\202\377\211H\t\322\315\356\351\007\003\n\0011\212\212\344\255\007\003\n\0011\252\221\231\304\001R\n\007s1-eth1\022G\202\377\211H\t\322\315\356\351\007\003\n\0011\322\374\322\233\001\010\372\375\371\331\n\002\010\001\312\212\243\352\005\010\312\223\360\266\005\002\010\001\362\262\360\266\010\t\n\007s1-eth1\312\261\312\343\017\010\262\250\370\240\002\002\010\001\252\221\231\304\001R\n\007s1-eth2\022G\202\377\211H\t\322\315\356\351\007\003\n\0011\322\374\322\233\001\010\372\375\371\331\n\002\010\001\312\212\243\352\005\010\312\223\360\266\005\002\010\001\362\262\360\266\010\t\n\007s1-eth2\312\261\312\343\017\010\262\250\370\240\002\002\010\002\322\277\322\313\0148\n\007s1-eth1\022-\352\366\377\215\001\002\010\001\262\241\245\260\001\002\010\001\242\207\355\257\002\017\330\220\301\217\010\304\371\266i\322\354\274\350\n\000\352\340\372\222\003\002\010\001\322\277\322\313\0148\n\007s1-eth2\022-\352\366\377\215\001\002\010\001\262\241\245\260\001\002\010\001\242\207\355\257\002\017\330\220\301\217\010\304\371\266i\322\354\274\350\n\000\352\340\372\222\003\002\010\002"
      }
    }
  }
}
"""

_GNMI_CAPABILITIES = r"""
supported_models { name: "openconfig-interfaces-stratum" organization: "Open Networking Foundation" version: "0.1.0" }
supported_encodings: PROTO
gNMI_version: "0.7.0"
"""


_GNMI_INTERFACE_STUFF = r"""
notification {
  timestamp: 1656719438871244764
  update {
    path {
      elem {
        name: "interfaces"
      }
      elem {
        name: "interface"
        key {
          key: "name"
          value: "s1-eth1"
        }
      }
      elem {
        name: "state"
      }
      elem {
        name: "ifindex"
      }
    }
    val {
      uint_val: 1
    }
  }
}
notification {
  timestamp: 1656719438871263864
  update {
    path {
      elem {
        name: "interfaces"
      }
      elem {
        name: "interface"
        key {
          key: "name"
          value: "s1-eth2"
        }
      }
      elem {
        name: "state"
      }
      elem {
        name: "ifindex"
      }
    }
    val {
      uint_val: 2
    }
  }
}
"""


_GNMI_SUBSCRIBE_RESPONSES_INITIAL = [
    r"""
    update { timestamp: 1656723692816736079 update { path { elem { name: "interfaces" } elem { name: "interface" key { key: "name" value: "s1-eth1" } } elem { name: "state" } elem { name: "oper-status" } } val { string_val: "UP" } } }
    """,
    r"""
    update { timestamp: 1656723692817152380 update { path { elem { name: "interfaces" } elem { name: "interface" key { key: "name" value: "s1-eth2" } } elem { name: "state" } elem { name: "oper-status" } } val { string_val: "UP" } } }
    """,
]


_GNMI_SUBSCRIBE_RESPONSES_UPDATES = [
    r"""
    update { timestamp: 1656723692816736079 update { path { elem { name: "interfaces" } elem { name: "interface" key { key: "name" value: "s1-eth1" } } elem { name: "state" } elem { name: "oper-status" } } val { string_val: "DOWN" } } }
    """,
    r"""
    update { timestamp: 1656723692816736079 update { path { elem { name: "interfaces" } elem { name: "interface" key { key: "name" value: "s1-eth1" } } elem { name: "state" } elem { name: "oper-status" } } val { string_val: "UP" } } }
    """,
]


_GNMI_SUBSCRIBE_RESPONSES_SAMPLE = [
    r"""
    update { timestamp: 1656728002678626415 update { path { elem { name: "interfaces" } elem { name: "interface" key { key: "name" value: "s1-eth1" } } elem { name: "state" } elem { name: "counters" } elem { name: "in-octets" } } val { uint_val: 1196 } } }
    """,
    r"""
    update { timestamp: 1656728002680768004 update { path { elem { name: "interfaces" } elem { name: "interface" key { key: "name" value: "s1-eth2" } } elem { name: "state" } elem { name: "counters" } elem { name: "in-octets" } } val { uint_val: 1196 } } }
    """,
    r"""
    update { timestamp: 1656728002779297318 update { path { elem { name: "interfaces" } elem { name: "interface" key { key: "name" value: "s1-eth1" } } elem { name: "state" } elem { name: "counters" } elem { name: "in-octets" } } val { uint_val: 1196 } } }
    """,
    r"""
    update { timestamp: 1656728002782083970 update { path { elem { name: "interfaces" } elem { name: "interface" key { key: "name" value: "s1-eth2" } } elem { name: "state" } elem { name: "counters" } elem { name: "in-octets" } } val { uint_val: 1196 } } }
    """,
    r"""
    update { timestamp: 1656728002879090194 update { path { elem { name: "interfaces" } elem { name: "interface" key { key: "name" value: "s1-eth1" } } elem { name: "state" } elem { name: "counters" } elem { name: "in-octets" } } val { uint_val: 1196 } } }
    """,
]
