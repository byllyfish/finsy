from pathlib import Path

import finsy as fy

_THIS_DIR = Path(__file__).parent

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
