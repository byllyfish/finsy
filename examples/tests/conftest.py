import asyncio
import importlib
import sys
from pathlib import Path

import pytest
from shellous import sh
from shellous.harvest import harvest_results

from finsy.test import demonet as dn


@pytest.fixture(scope="module")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def demonet(request):
    script = request.module.DEMONET

    async with sh(script).set(pty=True).run() as net:
        prompt = Prompt(net, "mininet> ")

        welcome = await prompt.send()
        if welcome.startswith("Error:"):
            raise RuntimeError(welcome)

        yield prompt
        await prompt.send("exit")


def _import_module(path: Path):
    # Reference: https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    assert path.suffix == ".py"
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    # sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
async def demonet2(request):
    if isinstance(request.module.DEMONET, Path):
        # Load module at path and obtain its DEMONET value.
        module = _import_module(request.module.DEMONET)
        config = module.DEMONET
    else:
        config = request.module.DEMONET

    async with dn.DemoNet(config) as net:
        yield net


@pytest.fixture
def python():
    return sh(sys.executable).stdin(sh.CAPTURE).stderr(sh.INHERIT).env(PYTHONPATH="..")


class Prompt:
    "Utility class to help with an interactive prompt."

    def __init__(self, runner, prompt: str):
        self.runner = runner
        self.prompt_bytes = prompt.encode("utf-8")

    async def send(
        self,
        input_text: str = "",
        *,
        expect: str = "",
        timeout: float | None = None,
    ) -> str:
        "Write some input text to stdin, then await the response."
        assert self.runner.returncode is None

        stdin = self.runner.stdin
        stdout = self.runner.stdout

        if input_text:
            stdin.write(input_text.encode("utf-8") + b"\n")

        # Drain our write to stdin, and wait for prompt from stdout.
        cancelled, (buf, _) = await harvest_results(
            stdout.readuntil(self.prompt_bytes),
            stdin.drain(),
            timeout=timeout,
        )
        if cancelled:
            raise asyncio.CancelledError()

        if isinstance(buf, asyncio.IncompleteReadError):
            buf = buf.partial

        # Clean up the output to remove the prompt, then return as string.
        buf = buf.replace(b"\r\n", b"\n")
        if buf.endswith(self.prompt_bytes):
            promptlen = len(self.prompt_bytes)
            buf = buf[0:-promptlen].rstrip(b"\n")

        result = buf.decode("utf-8")
        print(result)
        if expect:
            assert expect in result

        return result
