from pathlib import Path

import pytest

# All tests run in the "module" event loop.
pytestmark = pytest.mark.asyncio(loop_scope="module")

COPY_FILE_DIR = Path(__file__).parents[1] / "copy_file"

DEMONET = COPY_FILE_DIR / "net/run.py"


async def test_file_exists(demonet):
    "Test the script copied to the mininet image."
    if demonet.inside_running_image:
        pytest.skip("No files copied when image is already running.")

    await demonet.send('sh stat -c "%a" /tmp/myscript.py', expect="755")
    await demonet.send("sh /tmp/myscript.py", expect="It works!")
