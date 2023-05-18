from pathlib import Path

import finsy as fy

_THIS_DIR = Path(__file__).parent

SERVER1_CREDS = fy.GRPCCredentialsTLS(
    cacert=_THIS_DIR / "ca1.crt",
    cert=_THIS_DIR / "server1.crt",
    private_key=_THIS_DIR / "server1.key",
)


CLIENT1_CREDS = fy.GRPCCredentialsTLS(
    cacert=_THIS_DIR / "ca1.crt",
    cert=_THIS_DIR / "client1.crt",
    private_key=_THIS_DIR / "client1.key",
)


SERVER2_CREDS = fy.GRPCCredentialsTLS(
    cacert=_THIS_DIR / "ca2.crt",
    cert=_THIS_DIR / "server2.crt",
    private_key=_THIS_DIR / "server2.key",
)


CLIENT2_CREDS = fy.GRPCCredentialsTLS(
    cacert=_THIS_DIR / "ca2.crt",
    cert=_THIS_DIR / "client2.crt",
    private_key=_THIS_DIR / "client2.key",
)
