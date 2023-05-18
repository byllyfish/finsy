from pathlib import Path

import finsy as fy

_THIS_DIR = Path(__file__).parent


# Valid certificates (expire in 2033).

SERVER1_CREDS = fy.GRPCCredentialsTLS(
    cacert=_THIS_DIR / "mtls1/ca.crt",
    cert=_THIS_DIR / "mtls1/server.crt",
    private_key=_THIS_DIR / "mtls1/server.key",
)

CLIENT1_CREDS = fy.GRPCCredentialsTLS(
    cacert=_THIS_DIR / "mtls1/ca.crt",
    cert=_THIS_DIR / "mtls1/client.crt",
    private_key=_THIS_DIR / "mtls1/client.key",
)

SERVER2_CREDS = fy.GRPCCredentialsTLS(
    cacert=_THIS_DIR / "mtls2/ca.crt",
    cert=_THIS_DIR / "mtls2/server.crt",
    private_key=_THIS_DIR / "mtls2/server.key",
)

CLIENT2_CREDS = fy.GRPCCredentialsTLS(
    cacert=_THIS_DIR / "mtls2/ca.crt",
    cert=_THIS_DIR / "mtls2/client.crt",
    private_key=_THIS_DIR / "mtls2/client.key",
)

# Expired certificates.

SERVER3_CREDS_XCLIENT = fy.GRPCCredentialsTLS(
    cacert=_THIS_DIR / "mtls3_expired_client/ca.crt",
    cert=_THIS_DIR / "mtls3_expired_client/server.crt",
    private_key=_THIS_DIR / "mtls3_expired_client/server.key",
)

CLIENT3_CREDS_XCLIENT = fy.GRPCCredentialsTLS(
    cacert=_THIS_DIR / "mtls3_expired_client/ca.crt",
    cert=_THIS_DIR / "mtls3_expired_client/client.crt",
    private_key=_THIS_DIR / "mtls3_expired_client/client.key",
)

SERVER4_CREDS_XSERVER = fy.GRPCCredentialsTLS(
    cacert=_THIS_DIR / "mtls4_expired_server/ca.crt",
    cert=_THIS_DIR / "mtls4_expired_server/server.crt",
    private_key=_THIS_DIR / "mtls4_expired_server/server.key",
)

CLIENT4_CREDS_XSERVER = fy.GRPCCredentialsTLS(
    cacert=_THIS_DIR / "mtls4_expired_server/ca.crt",
    cert=_THIS_DIR / "mtls4_expired_server/client.crt",
    private_key=_THIS_DIR / "mtls4_expired_server/client.key",
)
