# 🐟 Tutorial 0: Installation and Setup

🚧 This tutorial is [under development](## "Technical content okay; grammar not read good ;)").

This tutorial shows how to create a **Finsy** project from scratch.

Before we begin, you must install the following software:


## ◉ Requirements

- Python 3.10 or later  ([python.org](https://www.python.org/))
- Poetry  ([python-poetry.org](https://python-poetry.org/))
- Visual Studio Code ([code.visualstudio.com](https://code.visualstudio.com/))

I recommend using the latest release of Python 3 when using asyncio. Finsy requires Python 3.10 or later.
On Mac OS, I use pyenv (installed via homebrew) to manage my python versions.

Poetry is a useful tool for managing Python projects.

Visual Studio Code (VSCode) is an IDE/Editor that supports Python.


## ◉ Check Requirements

Open a Terminal and verify that the software development tools are installed.

<details>
<summary><blockquote>
python3 --version<br>
poetry --version<br>
code --version
</blockquote></summary>

```console
$ python3 --version
Python 3.10.5
$ poetry --version
Poetry version 1.1.14
$ code --version
1.69.2
3b889b090b5ad5793f524b5d1d39fda662b96a2a
x64
$ _
```

</details>
<br>

Click the disclosure triangle widget to see what the CLI output looks like on my machine.
Your output may differ slightly.

## ◉ Create the Python Project

Navigate to the directory where you want to place your new project. Use the `poetry new`
command to create a new project directory. Poetry will fill in the boilerplate for you.

<details>
<summary><blockquote>
poetry new finsy_demo
</blockquote></summary>

```console
$ poetry new finsy_demo
Created package finsy_demo in finsy_demo
$ _
```

</details>
<br>

Change into your new project directory and list its contents. In this tutorial, we will not 
use the `finsy_demo` and `test` sub-directories. We will create Python files in the same directory
as `pyproject.toml`.

<details>
<summary><blockquote>
cd finsy_demo<br>
ls -F
</blockquote></summary>

```console
$ cd finsy_demo
$ ls -F
README.rst      finsy_demo/     pyproject.toml  tests/
$ _
```

</details>
<br>

Create a new virtual environment named `.venv` using Python 3.10. Activate the virtual environment
using the `source` command.

<details>
<summary><blockquote>
python3 -m venv .venv<br>
source .venv/bin/activate<br>
</blockquote></summary>

```console
$ python3 -m venv .venv
$ source .venv/bin/activate
(.venv) $ _
```

</details>
<br>

I like to keep the Python virtual environment in a `.venv` directory local to the
project directory. Always make sure you activate the python environment before you do anything.

We need to update the version of pytest inserted by poetry in pyproject.toml. We also need
to add `pytest-asyncio`.

```console
(.venv) $ poetry add --dev pytest@latest pytest-asyncio
```

Now, add `finsy` as a dependency to your project.

<details>
<summary><blockquote>
poetry add finsy
</blockquote></summary>

```console
(.venv) $ poetry add finsy
Using version ^0.1.0 for finsy

Updating dependencies
Resolving dependencies... (1.7s)

Writing lock file

Package operations: 17 installs, 0 updates, 0 removals

  • Installing pyparsing (3.0.9)
  • Installing six (1.16.0)
  • Installing typing-extensions (4.3.0)
  • Installing attrs (21.4.0)
  • Installing grpcio (1.47.0)
  • Installing macaddress (1.2.0)
  • Installing more-itertools (8.13.0)
  • Installing packaging (21.3)
  • Installing parsy (1.4.0)
  • Installing pluggy (0.13.1)
  • Installing protobuf (4.21.2)
  • Installing py (1.11.0)
  • Installing pyee (9.0.4)
  • Installing pylev (1.4.0)
  • Installing wcwidth (0.2.5)
  • Installing finsy (0.1.0)
  • Installing pytest (5.4.3)
(.venv) $ _
```

</details>
<br>

Start Visual Studio Code and open a window to your project directory:

<details>
<summary><blockquote>
code .
</blockquote></summary>

```console
(.venv) $ code .
(.venv) $ _
```

</details>
<br>

Visual Studio Code should open in a new window with the contents of the `finsy_demo` directory
on the left.

The VSCode Python extension uses [pyright](https://github.com/microsoft/pyright) to analyze Python source
code and provide type checking. Tell pyright/pylance where to find the `finsy/proto` directory. To do this, 
add the following text to your `pyproject.toml` file.

```toml
[tool.pyright]

[[executionEnvironments]]
root = ".venv/lib/python3.10/site-packages/finsy"
extraPaths = [".venv/lib/python3.10/site-packages/finsy/proto"]
```

With this snippet, VSCode will be able to analyze the syntax of the protobuf "_pb2" files
included with Finsy.

We're done setting up the project. In the next section, we'll write a quick demo program.


## ◉ Your First Finsy Program

Use VSCode to create a new file named "demo0.py". Add the following text and save your changes.

```python
import asyncio
from finsy import Switch

ADDRESS = "127.0.0.1:50001"

async def main():
    async with Switch("sw", ADDRESS) as sw:
        print(sw.p4info)

asyncio.run(main())
```

In your terminal, run this program:

<details>
<summary><blockquote>
python demo0.py
</blockquote></summary>

```console
(.venv) $ python demo0.py
(.venv) $ _
```

</details>
<br>

You can edit the `ADDRESS` variable to specify a different P4Runtime GRPC service. GRPC represents
endpoints using a string of the form "HOST:PORT".

### Local Testing

If you don't have an existing P4Runtime target, you can start a test P4Runtime server. 
Open a second terminal and start the test P4Runtime server:

<details>
<summary><blockquote>
python -m finsy.test.p4runtime_server --port=50001
</blockquote></summary>

```console
(.venv) $ python -m finsy.test.p4runtime_server --port=50001
(.venv) $ _
```

</details>
<br>

Now, re-run `python demo0.py` from the first Terminal.


## 🎉 Next Steps

All done with this tutorial.

The next tutorial will show you how to test Finsy against bmv2 and stratum docker images.

[➡️ Go to Tutorial 1.](tutorial_1.md)