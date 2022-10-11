"Utility functions for protobuf messages."

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

import logging
import re
import textwrap
from typing import Any, TypeVar

import grpc  # pyright: ignore [reportMissingTypeStubs]
from google.protobuf import json_format, text_format
from google.protobuf.any_pb2 import Any as _Any  # pylint: disable=E0611
from google.protobuf.message import Message as _Message

import finsy as _fy
from finsy.gnmiclient import gNMIPath
from finsy.log import MSG_LOG
from finsy.proto import gnmi, p4r

PBAny = _Any
PBMessage = _Message

_MT = TypeVar("_MT", bound=PBMessage)


def from_any(any_obj: PBAny, msg_class: type[_MT]) -> _MT:
    "Unpack a protobuf `any_pb2.Any` message, or raise an exception."

    obj = msg_class()
    if not any_obj.Unpack(obj):  # pyright: ignore[reportUnknownMemberType]
        raise ValueError(f"Not a {msg_class.__name__}: {any_obj!r}")
    return obj


def from_text(data: str, msg_class: type[_MT]) -> _MT:
    "Read protobuf message from given text/json string."
    assert isinstance(data, str)

    msg = msg_class()
    if data[0] == "{":
        json_format.Parse(data, msg)
    else:
        text_format.Parse(data, msg)

    return msg


def from_dict(value: dict[str, Any], msg_class: type[_MT]) -> _MT:
    "Convert Python dict to protobuf message."
    return json_format.ParseDict(value, msg_class())


def to_text(
    msg: PBMessage,
    *,
    as_one_line: bool = True,
    custom_format: bool = False,
) -> str:
    "Convert protobuf message to text format."
    assert isinstance(msg, PBMessage)
    formatter = _message_formatter if custom_format else None
    result = text_format.MessageToString(
        msg,
        as_one_line=as_one_line,
        message_formatter=formatter,
    )
    return result


def to_json(msg: PBMessage) -> str:
    "Convert protobuf message to JSON format."
    assert isinstance(msg, PBMessage), f"not a Message: {msg!r}"
    return json_format.MessageToJson(msg, preserving_proto_field_name=True)


def to_dict(msg: PBMessage) -> dict[str, Any]:
    "Convert protobuf message to Python dict."
    assert isinstance(msg, PBMessage), f"not a Message: {msg!r}"
    return json_format.MessageToDict(msg, preserving_proto_field_name=True)


def _message_formatter(msg: PBMessage, _indent: int, as_one_line: bool):
    if isinstance(msg, p4r.ForwardingPipelineConfig):
        return f"📦p4cookie=0x{msg.cookie.cookie:x}"
    if isinstance(msg, gnmi.Path):
        return f"📂{gNMIPath(msg)}"
    if isinstance(msg, gnmi.Update):
        value = repr(msg.val).strip()
        dups = "" if not msg.duplicates else f" ({msg.duplicates} dups)"
        return f"📂{gNMIPath(msg.path)} = {value}{dups}"
    if isinstance(msg, (p4r.PacketIn, p4r.PacketOut)):
        metadata = " ".join(
            f"meta[{md.metadata_id}]={md.value.hex()}" for md in msg.metadata
        )
        return f"📬{msg.payload.hex()} {metadata}"
    if not as_one_line and isinstance(msg, gnmi.GetResponse):
        return "\n".join(
            f"📩{to_text(notif, custom_format=True)}" for notif in msg.notification
        )
    if isinstance(msg, gnmi.SubscribeResponse):
        if msg.WhichOneof("response") == "update":
            return f"📩{to_text(msg.update, custom_format=True)}"
    return None


def log_msg(
    channel: grpc.aio.Channel | None,
    msg: PBMessage,
    schema: "_fy.P4Schema | None",
    *,
    level: int = logging.DEBUG,
):
    """Log a sent/received client message.

    Format:
        <state><mesg-type> (<size> bytes): <msg-contents>

    <state> is empty if the client state is READY. Otherwise, it's the
    channel connectivity state.
    """
    if not MSG_LOG.isEnabledFor(level):
        return  # pragma: no cover

    # Include the channel's state if it's not READY.
    assert channel is not None
    state = channel.get_state()
    state_name = ""
    if state != grpc.ChannelConnectivity.READY:
        state_name = f"{state.name} "  # trailing space necessary

    if isinstance(msg, (p4r.ReadResponse, p4r.WriteRequest)):
        text = to_text(msg, as_one_line=False, custom_format=True)
        if schema is not None:
            text = _log_annotate(text, schema)
    elif isinstance(msg, gnmi.GetResponse):
        text = to_text(msg, as_one_line=False, custom_format=True)
    else:
        text = to_text(msg, custom_format=True)

    # If text contains multiple lines, insert the multiline indicator and
    # indent the text.
    if "\n" in text:
        text = "⤵️\n" + textwrap.indent(text.rstrip(), "  ")

    size = msg.ByteSize()

    MSG_LOG.log(
        level,
        "%s%s (%d bytes): %s",
        state_name,
        type(msg).__name__,
        size,
        text,
    )


_ANNOTATE_REGEX = re.compile(r'([a-z]+_id|value|mask): (\d+|"[^"]+")\n', re.MULTILINE)


def _log_annotate(text: str, schema: "_fy.P4Schema") -> str:
    "Annotate table_id, action_id, etc. in log messages."

    action_id = 0
    table_id = 0

    def _replace(m: re.Match[str]) -> str:
        nonlocal action_id, table_id

        key, value = m.groups()
        name = None

        try:
            match key:
                case "table_id":
                    table_id = int(value)
                    name = schema.tables[table_id].name
                case "action_id":
                    action_id = int(value)
                    name = schema.actions[action_id].name
                case "digest_id":
                    name = schema.digests[int(value)].name
                case "field_id":
                    name = schema.tables[table_id].match_fields[int(value)].name
                case "param_id":
                    name = schema.actions[action_id].params[int(value)].name
                case "value" | "mask":
                    name = _decode_escaped_value(value.encode("ascii"))
                # TODO: Annotate more identifier types.
                case _:
                    pass

        except (LookupError, ValueError):
            # If there is a failure, don't replace anything.
            pass

        if name:
            return f"{key}: {value}  # {name}\n"

        return m[0]

    return _ANNOTATE_REGEX.sub(_replace, text)


def _decode_escaped_value(value: bytes) -> str:
    "Decode an octal-escaped string enclosed in double-quotes."
    if not (value[0] == value[-1] == ord('"')):
        raise ValueError("unexpected value?")
    return value[1:-1].decode("unicode-escape").encode("latin1").hex()
