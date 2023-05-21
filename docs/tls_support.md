# mTLS Support

Finsy supports Transport Layer Security (TLS) with client certificates. You must
create server/client certificates and keys that all work together. 

- `ca.crt` -- used by both client and server to authenticate each other.
- `client.crt` -- uniquely identifies the client.
- `client.key` -- private key associated with `client.cert`. Keep secret!
- `server.crt` -- uniquely identifies the server, with SAN "reachable" from client.
- `server.key` -- private key associated with `server.crt`. Keep secret!

The `server.crt` certificate must have a SAN that matches the IP addresses
used to connect (e.g. 127.0.0.1).

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

The P4Runtime server running in each switch will need to be configured using
the corresponding `server` certificate. Its `cacert` should specify the a 
certificate, such as `ca.crt`, that can authenticate the client certificate.
