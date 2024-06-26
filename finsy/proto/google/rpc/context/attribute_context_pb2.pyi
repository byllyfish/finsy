"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
Copyright 2020 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import builtins
import collections.abc
import google.protobuf.descriptor
import google.protobuf.internal.containers
import google.protobuf.message
import google.protobuf.struct_pb2
import google.protobuf.timestamp_pb2
import typing

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

@typing.final
class AttributeContext(google.protobuf.message.Message):
    """This message defines the standard attribute vocabulary for Google APIs.

    An attribute is a piece of metadata that describes an activity on a network
    service. For example, the size of an HTTP request, or the status code of
    an HTTP response.

    Each attribute has a type and a name, which is logically defined as
    a proto message field in `AttributeContext`. The field type becomes the
    attribute type, and the field path becomes the attribute name. For example,
    the attribute `source.ip` maps to field `AttributeContext.source.ip`.

    This message definition is guaranteed not to have any wire breaking change.
    So you can use it directly for passing attributes across different systems.

    NOTE: Different system may generate different subset of attributes. Please
    verify the system specification before relying on an attribute generated
    a system.
    """

    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    @typing.final
    class Peer(google.protobuf.message.Message):
        """This message defines attributes for a node that handles a network request.
        The node can be either a service or an application that sends, forwards,
        or receives the request. Service peers should fill in
        `principal` and `labels` as appropriate.
        """

        DESCRIPTOR: google.protobuf.descriptor.Descriptor

        @typing.final
        class LabelsEntry(google.protobuf.message.Message):
            DESCRIPTOR: google.protobuf.descriptor.Descriptor

            KEY_FIELD_NUMBER: builtins.int
            VALUE_FIELD_NUMBER: builtins.int
            key: builtins.str
            value: builtins.str
            def __init__(
                self,
                *,
                key: builtins.str = ...,
                value: builtins.str = ...,
            ) -> None: ...
            def ClearField(self, field_name: typing.Literal["key", b"key", "value", b"value"]) -> None: ...

        IP_FIELD_NUMBER: builtins.int
        PORT_FIELD_NUMBER: builtins.int
        LABELS_FIELD_NUMBER: builtins.int
        PRINCIPAL_FIELD_NUMBER: builtins.int
        REGION_CODE_FIELD_NUMBER: builtins.int
        ip: builtins.str
        """The IP address of the peer."""
        port: builtins.int
        """The network port of the peer."""
        principal: builtins.str
        """The identity of this peer. Similar to `Request.auth.principal`, but
        relative to the peer instead of the request. For example, the
        idenity associated with a load balancer that forwared the request.
        """
        region_code: builtins.str
        """The CLDR country/region code associated with the above IP address.
        If the IP address is private, the `region_code` should reflect the
        physical location where this peer is running.
        """
        @property
        def labels(self) -> google.protobuf.internal.containers.ScalarMap[builtins.str, builtins.str]:
            """The labels associated with the peer."""

        def __init__(
            self,
            *,
            ip: builtins.str = ...,
            port: builtins.int = ...,
            labels: collections.abc.Mapping[builtins.str, builtins.str] | None = ...,
            principal: builtins.str = ...,
            region_code: builtins.str = ...,
        ) -> None: ...
        def ClearField(self, field_name: typing.Literal["ip", b"ip", "labels", b"labels", "port", b"port", "principal", b"principal", "region_code", b"region_code"]) -> None: ...

    @typing.final
    class Api(google.protobuf.message.Message):
        """This message defines attributes associated with API operations, such as
        a network API request. The terminology is based on the conventions used
        by Google APIs, Istio, and OpenAPI.
        """

        DESCRIPTOR: google.protobuf.descriptor.Descriptor

        SERVICE_FIELD_NUMBER: builtins.int
        OPERATION_FIELD_NUMBER: builtins.int
        PROTOCOL_FIELD_NUMBER: builtins.int
        VERSION_FIELD_NUMBER: builtins.int
        service: builtins.str
        """The API service name. It is a logical identifier for a networked API,
        such as "pubsub.googleapis.com". The naming syntax depends on the
        API management system being used for handling the request.
        """
        operation: builtins.str
        """The API operation name. For gRPC requests, it is the fully qualified API
        method name, such as "google.pubsub.v1.Publisher.Publish". For OpenAPI
        requests, it is the `operationId`, such as "getPet".
        """
        protocol: builtins.str
        """The API protocol used for sending the request, such as "http", "https",
        "grpc", or "internal".
        """
        version: builtins.str
        """The API version associated with the API operation above, such as "v1" or
        "v1alpha1".
        """
        def __init__(
            self,
            *,
            service: builtins.str = ...,
            operation: builtins.str = ...,
            protocol: builtins.str = ...,
            version: builtins.str = ...,
        ) -> None: ...
        def ClearField(self, field_name: typing.Literal["operation", b"operation", "protocol", b"protocol", "service", b"service", "version", b"version"]) -> None: ...

    @typing.final
    class Auth(google.protobuf.message.Message):
        """This message defines request authentication attributes. Terminology is
        based on the JSON Web Token (JWT) standard, but the terms also
        correlate to concepts in other standards.
        """

        DESCRIPTOR: google.protobuf.descriptor.Descriptor

        PRINCIPAL_FIELD_NUMBER: builtins.int
        AUDIENCES_FIELD_NUMBER: builtins.int
        PRESENTER_FIELD_NUMBER: builtins.int
        CLAIMS_FIELD_NUMBER: builtins.int
        ACCESS_LEVELS_FIELD_NUMBER: builtins.int
        principal: builtins.str
        """The authenticated principal. Reflects the issuer (`iss`) and subject
        (`sub`) claims within a JWT. The issuer and subject should be `/`
        delimited, with `/` percent-encoded within the subject fragment. For
        Google accounts, the principal format is:
        "https://accounts.google.com/{id}"
        """
        presenter: builtins.str
        """The authorized presenter of the credential. Reflects the optional
        Authorized Presenter (`azp`) claim within a JWT or the
        OAuth client id. For example, a Google Cloud Platform client id looks
        as follows: "123456789012.apps.googleusercontent.com".
        """
        @property
        def audiences(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]:
            """The intended audience(s) for this authentication information. Reflects
            the audience (`aud`) claim within a JWT. The audience
            value(s) depends on the `issuer`, but typically include one or more of
            the following pieces of information:

            *  The services intended to receive the credential such as
               ["pubsub.googleapis.com", "storage.googleapis.com"]
            *  A set of service-based scopes. For example,
               ["https://www.googleapis.com/auth/cloud-platform"]
            *  The client id of an app, such as the Firebase project id for JWTs
               from Firebase Auth.

            Consult the documentation for the credential issuer to determine the
            information provided.
            """

        @property
        def claims(self) -> google.protobuf.struct_pb2.Struct:
            """Structured claims presented with the credential. JWTs include
            `{key: value}` pairs for standard and private claims. The following
            is a subset of the standard required and optional claims that would
            typically be presented for a Google-based JWT:

               {'iss': 'accounts.google.com',
                'sub': '113289723416554971153',
                'aud': ['123456789012', 'pubsub.googleapis.com'],
                'azp': '123456789012.apps.googleusercontent.com',
                'email': 'jsmith@example.com',
                'iat': 1353601026,
                'exp': 1353604926}

            SAML assertions are similarly specified, but with an identity provider
            dependent structure.
            """

        @property
        def access_levels(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]:
            """A list of access level resource names that allow resources to be
            accessed by authenticated requester. It is part of Secure GCP processing
            for the incoming request. An access level string has the format:
            "//{api_service_name}/accessPolicies/{policy_id}/accessLevels/{short_name}"

            Example:
            "//accesscontextmanager.googleapis.com/accessPolicies/MY_POLICY_ID/accessLevels/MY_LEVEL"
            """

        def __init__(
            self,
            *,
            principal: builtins.str = ...,
            audiences: collections.abc.Iterable[builtins.str] | None = ...,
            presenter: builtins.str = ...,
            claims: google.protobuf.struct_pb2.Struct | None = ...,
            access_levels: collections.abc.Iterable[builtins.str] | None = ...,
        ) -> None: ...
        def HasField(self, field_name: typing.Literal["claims", b"claims"]) -> builtins.bool: ...
        def ClearField(self, field_name: typing.Literal["access_levels", b"access_levels", "audiences", b"audiences", "claims", b"claims", "presenter", b"presenter", "principal", b"principal"]) -> None: ...

    @typing.final
    class Request(google.protobuf.message.Message):
        """This message defines attributes for an HTTP request. If the actual
        request is not an HTTP request, the runtime system should try to map
        the actual request to an equivalent HTTP request.
        """

        DESCRIPTOR: google.protobuf.descriptor.Descriptor

        @typing.final
        class HeadersEntry(google.protobuf.message.Message):
            DESCRIPTOR: google.protobuf.descriptor.Descriptor

            KEY_FIELD_NUMBER: builtins.int
            VALUE_FIELD_NUMBER: builtins.int
            key: builtins.str
            value: builtins.str
            def __init__(
                self,
                *,
                key: builtins.str = ...,
                value: builtins.str = ...,
            ) -> None: ...
            def ClearField(self, field_name: typing.Literal["key", b"key", "value", b"value"]) -> None: ...

        ID_FIELD_NUMBER: builtins.int
        METHOD_FIELD_NUMBER: builtins.int
        HEADERS_FIELD_NUMBER: builtins.int
        PATH_FIELD_NUMBER: builtins.int
        HOST_FIELD_NUMBER: builtins.int
        SCHEME_FIELD_NUMBER: builtins.int
        QUERY_FIELD_NUMBER: builtins.int
        TIME_FIELD_NUMBER: builtins.int
        SIZE_FIELD_NUMBER: builtins.int
        PROTOCOL_FIELD_NUMBER: builtins.int
        REASON_FIELD_NUMBER: builtins.int
        AUTH_FIELD_NUMBER: builtins.int
        id: builtins.str
        """The unique ID for a request, which can be propagated to downstream
        systems. The ID should have low probability of collision
        within a single day for a specific service.
        """
        method: builtins.str
        """The HTTP request method, such as `GET`, `POST`."""
        path: builtins.str
        """The HTTP URL path."""
        host: builtins.str
        """The HTTP request `Host` header value."""
        scheme: builtins.str
        """The HTTP URL scheme, such as `http` and `https`."""
        query: builtins.str
        """The HTTP URL query in the format of `name1=value1&name2=value2`, as it
        appears in the first line of the HTTP request. No decoding is performed.
        """
        size: builtins.int
        """The HTTP request size in bytes. If unknown, it must be -1."""
        protocol: builtins.str
        """The network protocol used with the request, such as "http/1.1",
        "spdy/3", "h2", "h2c", "webrtc", "tcp", "udp", "quic". See
        https://www.iana.org/assignments/tls-extensiontype-values/tls-extensiontype-values.xhtml#alpn-protocol-ids
        for details.
        """
        reason: builtins.str
        """A special parameter for request reason. It is used by security systems
        to associate auditing information with a request.
        """
        @property
        def headers(self) -> google.protobuf.internal.containers.ScalarMap[builtins.str, builtins.str]:
            """The HTTP request headers. If multiple headers share the same key, they
            must be merged according to the HTTP spec. All header keys must be
            lowercased, because HTTP header keys are case-insensitive.
            """

        @property
        def time(self) -> google.protobuf.timestamp_pb2.Timestamp:
            """The timestamp when the `destination` service receives the first byte of
            the request.
            """

        @property
        def auth(self) -> global___AttributeContext.Auth:
            """The request authentication. May be absent for unauthenticated requests.
            Derived from the HTTP request `Authorization` header or equivalent.
            """

        def __init__(
            self,
            *,
            id: builtins.str = ...,
            method: builtins.str = ...,
            headers: collections.abc.Mapping[builtins.str, builtins.str] | None = ...,
            path: builtins.str = ...,
            host: builtins.str = ...,
            scheme: builtins.str = ...,
            query: builtins.str = ...,
            time: google.protobuf.timestamp_pb2.Timestamp | None = ...,
            size: builtins.int = ...,
            protocol: builtins.str = ...,
            reason: builtins.str = ...,
            auth: global___AttributeContext.Auth | None = ...,
        ) -> None: ...
        def HasField(self, field_name: typing.Literal["auth", b"auth", "time", b"time"]) -> builtins.bool: ...
        def ClearField(self, field_name: typing.Literal["auth", b"auth", "headers", b"headers", "host", b"host", "id", b"id", "method", b"method", "path", b"path", "protocol", b"protocol", "query", b"query", "reason", b"reason", "scheme", b"scheme", "size", b"size", "time", b"time"]) -> None: ...

    @typing.final
    class Response(google.protobuf.message.Message):
        """This message defines attributes for a typical network response. It
        generally models semantics of an HTTP response.
        """

        DESCRIPTOR: google.protobuf.descriptor.Descriptor

        @typing.final
        class HeadersEntry(google.protobuf.message.Message):
            DESCRIPTOR: google.protobuf.descriptor.Descriptor

            KEY_FIELD_NUMBER: builtins.int
            VALUE_FIELD_NUMBER: builtins.int
            key: builtins.str
            value: builtins.str
            def __init__(
                self,
                *,
                key: builtins.str = ...,
                value: builtins.str = ...,
            ) -> None: ...
            def ClearField(self, field_name: typing.Literal["key", b"key", "value", b"value"]) -> None: ...

        CODE_FIELD_NUMBER: builtins.int
        SIZE_FIELD_NUMBER: builtins.int
        HEADERS_FIELD_NUMBER: builtins.int
        TIME_FIELD_NUMBER: builtins.int
        code: builtins.int
        """The HTTP response status code, such as `200` and `404`."""
        size: builtins.int
        """The HTTP response size in bytes. If unknown, it must be -1."""
        @property
        def headers(self) -> google.protobuf.internal.containers.ScalarMap[builtins.str, builtins.str]:
            """The HTTP response headers. If multiple headers share the same key, they
            must be merged according to HTTP spec. All header keys must be
            lowercased, because HTTP header keys are case-insensitive.
            """

        @property
        def time(self) -> google.protobuf.timestamp_pb2.Timestamp:
            """The timestamp when the `destination` service generates the first byte of
            the response.
            """

        def __init__(
            self,
            *,
            code: builtins.int = ...,
            size: builtins.int = ...,
            headers: collections.abc.Mapping[builtins.str, builtins.str] | None = ...,
            time: google.protobuf.timestamp_pb2.Timestamp | None = ...,
        ) -> None: ...
        def HasField(self, field_name: typing.Literal["time", b"time"]) -> builtins.bool: ...
        def ClearField(self, field_name: typing.Literal["code", b"code", "headers", b"headers", "size", b"size", "time", b"time"]) -> None: ...

    @typing.final
    class Resource(google.protobuf.message.Message):
        """This message defines core attributes for a resource. A resource is an
        addressable (named) entity provided by the destination service. For
        example, a file stored on a network storage service.
        """

        DESCRIPTOR: google.protobuf.descriptor.Descriptor

        @typing.final
        class LabelsEntry(google.protobuf.message.Message):
            DESCRIPTOR: google.protobuf.descriptor.Descriptor

            KEY_FIELD_NUMBER: builtins.int
            VALUE_FIELD_NUMBER: builtins.int
            key: builtins.str
            value: builtins.str
            def __init__(
                self,
                *,
                key: builtins.str = ...,
                value: builtins.str = ...,
            ) -> None: ...
            def ClearField(self, field_name: typing.Literal["key", b"key", "value", b"value"]) -> None: ...

        SERVICE_FIELD_NUMBER: builtins.int
        NAME_FIELD_NUMBER: builtins.int
        TYPE_FIELD_NUMBER: builtins.int
        LABELS_FIELD_NUMBER: builtins.int
        service: builtins.str
        """The name of the service that this resource belongs to, such as
        `pubsub.googleapis.com`. The service may be different from the DNS
        hostname that actually serves the request.
        """
        name: builtins.str
        """The stable identifier (name) of a resource on the `service`. A resource
        can be logically identified as "//{resource.service}/{resource.name}".
        The differences between a resource name and a URI are:

        *   Resource name is a logical identifier, independent of network
            protocol and API version. For example,
            `//pubsub.googleapis.com/projects/123/topics/news-feed`.
        *   URI often includes protocol and version information, so it can
            be used directly by applications. For example,
            `https://pubsub.googleapis.com/v1/projects/123/topics/news-feed`.

        See https://cloud.google.com/apis/design/resource_names for details.
        """
        type: builtins.str
        """The type of the resource. The syntax is platform-specific because
        different platforms define their resources differently.

        For Google APIs, the type format must be "{service}/{kind}".
        """
        @property
        def labels(self) -> google.protobuf.internal.containers.ScalarMap[builtins.str, builtins.str]:
            """The labels or tags on the resource, such as AWS resource tags and
            Kubernetes resource labels.
            """

        def __init__(
            self,
            *,
            service: builtins.str = ...,
            name: builtins.str = ...,
            type: builtins.str = ...,
            labels: collections.abc.Mapping[builtins.str, builtins.str] | None = ...,
        ) -> None: ...
        def ClearField(self, field_name: typing.Literal["labels", b"labels", "name", b"name", "service", b"service", "type", b"type"]) -> None: ...

    ORIGIN_FIELD_NUMBER: builtins.int
    SOURCE_FIELD_NUMBER: builtins.int
    DESTINATION_FIELD_NUMBER: builtins.int
    REQUEST_FIELD_NUMBER: builtins.int
    RESPONSE_FIELD_NUMBER: builtins.int
    RESOURCE_FIELD_NUMBER: builtins.int
    API_FIELD_NUMBER: builtins.int
    @property
    def origin(self) -> global___AttributeContext.Peer:
        """The origin of a network activity. In a multi hop network activity,
        the origin represents the sender of the first hop. For the first hop,
        the `source` and the `origin` must have the same content.
        """

    @property
    def source(self) -> global___AttributeContext.Peer:
        """The source of a network activity, such as starting a TCP connection.
        In a multi hop network activity, the source represents the sender of the
        last hop.
        """

    @property
    def destination(self) -> global___AttributeContext.Peer:
        """The destination of a network activity, such as accepting a TCP connection.
        In a multi hop network activity, the destination represents the receiver of
        the last hop.
        """

    @property
    def request(self) -> global___AttributeContext.Request:
        """Represents a network request, such as an HTTP request."""

    @property
    def response(self) -> global___AttributeContext.Response:
        """Represents a network response, such as an HTTP response."""

    @property
    def resource(self) -> global___AttributeContext.Resource:
        """Represents a target resource that is involved with a network activity.
        If multiple resources are involved with an activity, this must be the
        primary one.
        """

    @property
    def api(self) -> global___AttributeContext.Api:
        """Represents an API operation that is involved to a network activity."""

    def __init__(
        self,
        *,
        origin: global___AttributeContext.Peer | None = ...,
        source: global___AttributeContext.Peer | None = ...,
        destination: global___AttributeContext.Peer | None = ...,
        request: global___AttributeContext.Request | None = ...,
        response: global___AttributeContext.Response | None = ...,
        resource: global___AttributeContext.Resource | None = ...,
        api: global___AttributeContext.Api | None = ...,
    ) -> None: ...
    def HasField(self, field_name: typing.Literal["api", b"api", "destination", b"destination", "origin", b"origin", "request", b"request", "resource", b"resource", "response", b"response", "source", b"source"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing.Literal["api", b"api", "destination", b"destination", "origin", b"origin", "request", b"request", "resource", b"resource", "response", b"response", "source", b"source"]) -> None: ...

global___AttributeContext = AttributeContext
