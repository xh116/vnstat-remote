import asyncio
import base64
import logging
import subprocess
import sys
from hashlib import blake2s

from cryptography.fernet import Fernet

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger("VnStat Server")


async def send_vnstat(reader, writer):
    data = await reader.readline()
    data_decrypted = f.decrypt(data)
    logger.info(f"Received {data_decrypted} from {writer.get_extra_info('peername')}")
    begin = data_decrypted.decode()
    try:
        sp = subprocess.run(
            ["vnstat", "-b", begin, "--json", "d", "--limit", "31"],
            capture_output=True,
            check=True,
        )
        result = sp.stdout
    except subprocess.CalledProcessError as err:
        logger.warning(f"Subprocess: {err}")
        result = f'{"error": "{err}"}'.encode()
    result_encrypted = f.encrypt(result) + b"\n"
    logger.debug(f"Sending:\n{result}\n{result_encrypted}")
    writer.write(result_encrypted)
    await writer.drain()
    writer.close()


def init_key(password):
    key = base64.urlsafe_b64encode(
        blake2s(password.encode(), digest_size=16).hexdigest().encode()
    )
    return Fernet(key)


if __name__ == "__main__":
    password = sys.argv[1] if len(sys.argv) >= 2 else "test"
    port = int(sys.argv[2]) if len(sys.argv) >= 3 else 10000
    f = init_key(password)
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(send_vnstat, port=port, reuse_port=True, loop=loop)
    server = loop.run_until_complete(coro)
    logger.info(f"Serving on {server.sockets[0].getsockname()}")
    loop.run_forever()
