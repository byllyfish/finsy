import asyncio

from int_report import Header, parse_msg


async def _handle_tcp(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    print(f"open connection from {addr!r}")

    try:
        buf = b""
        while True:
            data = await reader.read(1024)
            if not data:
                break

            print(f"read {data.hex()}")
            buf += data
            msg, leftover = parse_msg(data)
            if msg:
                _handle_msg(msg)
                buf = leftover

    finally:
        writer.close()
        await writer.wait_closed()
        print(f"closed connection from {addr!r}")


def _handle_msg(msg: Header):
    print(msg)


async def int_listen(port: int):
    "Listen for INT messages."
    server = await asyncio.start_server(_handle_tcp, port=port)

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"int_listen serving on {addrs}")

    async with server:
        await server.serve_forever()
