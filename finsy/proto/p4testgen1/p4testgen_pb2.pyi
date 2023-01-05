"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
P4Testgen Protobuf template."""
import builtins
import collections.abc
import google.protobuf.descriptor
import google.protobuf.internal.containers
import google.protobuf.message
import p4.v1.p4runtime_pb2
import sys

if sys.version_info >= (3, 8):
    import typing as typing_extensions
else:
    import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

@typing_extensions.final
class InputPacketAtPort(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    PACKET_FIELD_NUMBER: builtins.int
    PORT_FIELD_NUMBER: builtins.int
    packet: builtins.bytes
    """The raw bytes of the test packet."""
    port: builtins.bytes
    """The raw bytes of the port associated with the packet."""
    def __init__(
        self,
        *,
        packet: builtins.bytes = ...,
        port: builtins.bytes = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["packet", b"packet", "port", b"port"]) -> None: ...

global___InputPacketAtPort = InputPacketAtPort

@typing_extensions.final
class OutputPacketAtPort(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    PACKET_FIELD_NUMBER: builtins.int
    PORT_FIELD_NUMBER: builtins.int
    PACKET_MASK_FIELD_NUMBER: builtins.int
    packet: builtins.bytes
    """The raw bytes of the test packet."""
    port: builtins.bytes
    """The raw bytes of the port associated with the packet."""
    packet_mask: builtins.bytes
    """The don't care mask of the packet."""
    def __init__(
        self,
        *,
        packet: builtins.bytes = ...,
        port: builtins.bytes = ...,
        packet_mask: builtins.bytes = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["packet", b"packet", "packet_mask", b"packet_mask", "port", b"port"]) -> None: ...

global___OutputPacketAtPort = OutputPacketAtPort

@typing_extensions.final
class TestCase(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    INPUT_PACKET_FIELD_NUMBER: builtins.int
    EXPECTED_OUTPUT_PACKET_FIELD_NUMBER: builtins.int
    ENTITIES_FIELD_NUMBER: builtins.int
    TRACES_FIELD_NUMBER: builtins.int
    METADATA_FIELD_NUMBER: builtins.int
    @property
    def input_packet(self) -> global___InputPacketAtPort:
        """The input packet."""
    @property
    def expected_output_packet(self) -> google.protobuf.internal.containers.RepeatedCompositeFieldContainer[global___OutputPacketAtPort]:
        """The corresponding expected output packet."""
    @property
    def entities(self) -> google.protobuf.internal.containers.RepeatedCompositeFieldContainer[p4.v1.p4runtime_pb2.Entity]:
        """The entities (e.g., table entries) to install on the switch before
        injecting the `input_packet`.
        """
    @property
    def traces(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]:
        """The trace associated with this particular test."""
    @property
    def metadata(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]:
        """Additional metadata and information."""
    def __init__(
        self,
        *,
        input_packet: global___InputPacketAtPort | None = ...,
        expected_output_packet: collections.abc.Iterable[global___OutputPacketAtPort] | None = ...,
        entities: collections.abc.Iterable[p4.v1.p4runtime_pb2.Entity] | None = ...,
        traces: collections.abc.Iterable[builtins.str] | None = ...,
        metadata: collections.abc.Iterable[builtins.str] | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["input_packet", b"input_packet"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["entities", b"entities", "expected_output_packet", b"expected_output_packet", "input_packet", b"input_packet", "metadata", b"metadata", "traces", b"traces"]) -> None: ...

global___TestCase = TestCase