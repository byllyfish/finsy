# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

from . import p4runtime_pb2 as p4_dot_v1_dot_p4runtime__pb2

GRPC_GENERATED_VERSION = '1.72.1'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in p4/v1/p4runtime_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class P4RuntimeStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Write = channel.unary_unary(
                '/p4.v1.P4Runtime/Write',
                request_serializer=p4_dot_v1_dot_p4runtime__pb2.WriteRequest.SerializeToString,
                response_deserializer=p4_dot_v1_dot_p4runtime__pb2.WriteResponse.FromString,
                _registered_method=True)
        self.Read = channel.unary_stream(
                '/p4.v1.P4Runtime/Read',
                request_serializer=p4_dot_v1_dot_p4runtime__pb2.ReadRequest.SerializeToString,
                response_deserializer=p4_dot_v1_dot_p4runtime__pb2.ReadResponse.FromString,
                _registered_method=True)
        self.SetForwardingPipelineConfig = channel.unary_unary(
                '/p4.v1.P4Runtime/SetForwardingPipelineConfig',
                request_serializer=p4_dot_v1_dot_p4runtime__pb2.SetForwardingPipelineConfigRequest.SerializeToString,
                response_deserializer=p4_dot_v1_dot_p4runtime__pb2.SetForwardingPipelineConfigResponse.FromString,
                _registered_method=True)
        self.GetForwardingPipelineConfig = channel.unary_unary(
                '/p4.v1.P4Runtime/GetForwardingPipelineConfig',
                request_serializer=p4_dot_v1_dot_p4runtime__pb2.GetForwardingPipelineConfigRequest.SerializeToString,
                response_deserializer=p4_dot_v1_dot_p4runtime__pb2.GetForwardingPipelineConfigResponse.FromString,
                _registered_method=True)
        self.StreamChannel = channel.stream_stream(
                '/p4.v1.P4Runtime/StreamChannel',
                request_serializer=p4_dot_v1_dot_p4runtime__pb2.StreamMessageRequest.SerializeToString,
                response_deserializer=p4_dot_v1_dot_p4runtime__pb2.StreamMessageResponse.FromString,
                _registered_method=True)
        self.Capabilities = channel.unary_unary(
                '/p4.v1.P4Runtime/Capabilities',
                request_serializer=p4_dot_v1_dot_p4runtime__pb2.CapabilitiesRequest.SerializeToString,
                response_deserializer=p4_dot_v1_dot_p4runtime__pb2.CapabilitiesResponse.FromString,
                _registered_method=True)


class P4RuntimeServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Write(self, request, context):
        """Update one or more P4 entities on the target.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Read(self, request, context):
        """Read one or more P4 entities from the target.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SetForwardingPipelineConfig(self, request, context):
        """Sets the P4 forwarding-pipeline config.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetForwardingPipelineConfig(self, request, context):
        """Gets the current P4 forwarding-pipeline config.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def StreamChannel(self, request_iterator, context):
        """Represents the bidirectional stream between the controller and the
        switch (initiated by the controller), and is managed for the following
        purposes:
        - connection initiation through client arbitration
        - indicating switch session liveness: the session is live when switch
        sends a positive client arbitration update to the controller, and is
        considered dead when either the stream breaks or the switch sends a
        negative update for client arbitration
        - the controller sending/receiving packets to/from the switch
        - streaming of notifications from the switch
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Capabilities(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_P4RuntimeServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Write': grpc.unary_unary_rpc_method_handler(
                    servicer.Write,
                    request_deserializer=p4_dot_v1_dot_p4runtime__pb2.WriteRequest.FromString,
                    response_serializer=p4_dot_v1_dot_p4runtime__pb2.WriteResponse.SerializeToString,
            ),
            'Read': grpc.unary_stream_rpc_method_handler(
                    servicer.Read,
                    request_deserializer=p4_dot_v1_dot_p4runtime__pb2.ReadRequest.FromString,
                    response_serializer=p4_dot_v1_dot_p4runtime__pb2.ReadResponse.SerializeToString,
            ),
            'SetForwardingPipelineConfig': grpc.unary_unary_rpc_method_handler(
                    servicer.SetForwardingPipelineConfig,
                    request_deserializer=p4_dot_v1_dot_p4runtime__pb2.SetForwardingPipelineConfigRequest.FromString,
                    response_serializer=p4_dot_v1_dot_p4runtime__pb2.SetForwardingPipelineConfigResponse.SerializeToString,
            ),
            'GetForwardingPipelineConfig': grpc.unary_unary_rpc_method_handler(
                    servicer.GetForwardingPipelineConfig,
                    request_deserializer=p4_dot_v1_dot_p4runtime__pb2.GetForwardingPipelineConfigRequest.FromString,
                    response_serializer=p4_dot_v1_dot_p4runtime__pb2.GetForwardingPipelineConfigResponse.SerializeToString,
            ),
            'StreamChannel': grpc.stream_stream_rpc_method_handler(
                    servicer.StreamChannel,
                    request_deserializer=p4_dot_v1_dot_p4runtime__pb2.StreamMessageRequest.FromString,
                    response_serializer=p4_dot_v1_dot_p4runtime__pb2.StreamMessageResponse.SerializeToString,
            ),
            'Capabilities': grpc.unary_unary_rpc_method_handler(
                    servicer.Capabilities,
                    request_deserializer=p4_dot_v1_dot_p4runtime__pb2.CapabilitiesRequest.FromString,
                    response_serializer=p4_dot_v1_dot_p4runtime__pb2.CapabilitiesResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'p4.v1.P4Runtime', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('p4.v1.P4Runtime', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class P4Runtime(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Write(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/p4.v1.P4Runtime/Write',
            p4_dot_v1_dot_p4runtime__pb2.WriteRequest.SerializeToString,
            p4_dot_v1_dot_p4runtime__pb2.WriteResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def Read(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_stream(
            request,
            target,
            '/p4.v1.P4Runtime/Read',
            p4_dot_v1_dot_p4runtime__pb2.ReadRequest.SerializeToString,
            p4_dot_v1_dot_p4runtime__pb2.ReadResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def SetForwardingPipelineConfig(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/p4.v1.P4Runtime/SetForwardingPipelineConfig',
            p4_dot_v1_dot_p4runtime__pb2.SetForwardingPipelineConfigRequest.SerializeToString,
            p4_dot_v1_dot_p4runtime__pb2.SetForwardingPipelineConfigResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def GetForwardingPipelineConfig(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/p4.v1.P4Runtime/GetForwardingPipelineConfig',
            p4_dot_v1_dot_p4runtime__pb2.GetForwardingPipelineConfigRequest.SerializeToString,
            p4_dot_v1_dot_p4runtime__pb2.GetForwardingPipelineConfigResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def StreamChannel(request_iterator,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.stream_stream(
            request_iterator,
            target,
            '/p4.v1.P4Runtime/StreamChannel',
            p4_dot_v1_dot_p4runtime__pb2.StreamMessageRequest.SerializeToString,
            p4_dot_v1_dot_p4runtime__pb2.StreamMessageResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def Capabilities(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/p4.v1.P4Runtime/Capabilities',
            p4_dot_v1_dot_p4runtime__pb2.CapabilitiesRequest.SerializeToString,
            p4_dot_v1_dot_p4runtime__pb2.CapabilitiesResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
