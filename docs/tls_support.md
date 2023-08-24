# mTLS Support

Finsy supports Mutual Transport Layer Security (mTLS). For clients to connect
to servers, you must create certificates and keys that all work together. At
a minimum, you need five files:

- `ca.crt` -- used by both client and server to authenticate each other.
- `client.crt` -- uniquely identifies the client.
- `client.key` -- private key associated with `client.cert`. Keep secret!
- `server.crt` -- uniquely identifies the server, with SAN "reachable" from client.
- `server.key` -- private key associated with `server.crt`. Keep secret!

The `server.crt` certificate must have a `Subject Alternative Name` (SAN) that
matches the IP addresses used to connect (e.g. 127.0.0.1). Alternatively, the
client can use the `target_name_override` option to force a match to the SAN.

Note: The script `finsy/tests/test_certs/make_certs.sh` produces certificate
pairs for testing.

## GRPCCredentialsTLS

In the `SwitchOptions` object, set the `channel_credentials` property to a
value of `GRPCCredentialsTLS`.

Your `GRPCCredentialsTLS` object must specify the `cacert`, `cert` and `private_key`
values. These may be stored in files or as `bytes`.

```
import finsy as fy
from pathlib import Path

creds = fy.GRPCCredentialsTLS(
    cacert=Path("ca.crt"),
    cert=Path("client.crt"),
    private_key=Path("client.key"),
)

options = fy.SwitchOptions(channel_credentials=creds, ...)
```

The P4Runtime server running in each switch must be configured using
a corresponding `server` certificate. Its `cacert` should specify a 
certificate, such as `ca.crt`, that can authenticate the client certificate.

The client's `GRPCCredentialsTLS` object may specify a value for `target_name_override`.
This value will be used instead of the GRPC target host name when validating
the server certificate.

```
creds = fy.GRPCCredentialsTLS(
    cacert=Path("ca.crt"),
    cert=Path("client.crt"),
    private_key=Path("client.key"),
)   target_name_override="localhost",
```

## Error Reporting

Finsy uses `grpc-core` to implement all GRPC operations, including TLS support.

When using `async with` on a Switch object, Finsy will raise an immediate
exception when a connection cannot be established. This exception may
include details about the underlying TLS issue, or it may just indicate that
the peer socket closed.

When running a Switch under a Controller, Finsy uses `wait_for_ready` to 
establish connections. This setting tells `grpc-core` to continuously re-connect
after a failed connection attempt. In this situation, Finsy will NOT raise an
exception even when there is a TLS issue. However, `grpc-core` will log any
errors to standard error. It is a good idea to alway capture standard error
when running a Finsy Controller.

To troubleshoot TLS issues, increase the GRPC logging verbosity. Run your 
Finsy program with these environment variables: 

```
GRPC_TRACE=transport_security
GRPC_VERBOSITY=debug
```

## Certificate Management

To manage expiring certificates when using a `Controller`, you might add multiple
instances of the same switch under different names, perhaps with a YYMMDD
convention for the certificate expiration date:

```
sw1/230501
sw1/231101
```

Only the Switch with the valid certificate will successfully connect. If both
certificates are valid, one of the Switches will be primary and the other will
have a backup role.
