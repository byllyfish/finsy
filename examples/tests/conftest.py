import asyncio
import sys

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


@pytest.fixture(scope="module")
async def demonet2(request):
    async with dn.DemoNet(request.module.DEMONET) as net:
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
