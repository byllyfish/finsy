# 🐟 Tutorial 0: Installation and Setup

🚧 This tutorial is under development.

This tutorial shows how to create a **Finsy** project from scratch.

Before we begin, you must install the following software:

## ◉ Requirements

- Python 3.10 or later  ([python.org](https://www.python.org/))

- Poetry  ([python-poetry.org](https://python-poetry.org/))

- Visual Studio Code ([code.visualstudio.com](https://code.visualstudio.com/))

I recommend using the latest release of Python 3 when using asyncio. Finsy requires Python 3.10 or later.

Poetry is a useful tool for managing Python projects.

Visual Studio Code (VSCode) is an IDE that supports Python.


## ◉ Create the Python Project

Open a Terminal and navigate to the directory where you want to place your new project. Use the `poetry new`
command to create a new project directory and fill it with boilerplate.

```console
$ poetry new finsy_demo
Created package finsy_demo in finsy_demo
```

Change into your new project directory and list the contents:

```console
$ cd finsy_demo
$ ls -F
README.rst      finsy_demo/     pyproject.toml  tests/
```

Check the current python interpreter version. Then, create a new virtual environment named `.venv` using
Python 3.10:

```console
$ python3 --version
Python 3.10.5
$ python3 -m venv .venv
```

Activate the virtual environment, then upgrade pip and setuptools. This is the last time
we will use pip. After this, we will only use poetry to install dependencies.

```console
$ source .venv/bin/activate
(.venv) $ pip list
Package    Version
---------- -------
pip        22.0.4
setuptools 58.1.0
WARNING: You are using pip version 22.0.4; however, version 22.1.2 is available.
You should consider upgrading via the '/Users/bfish/code/finsy_demo/.venv/bin/python3 -m pip install --upgrade pip' command.
(.venv) $ pip install -U pip setuptools
...
```

Note: I like to keep the Python virtual environment in a `.venv` directory local to the
project directory. Always make sure you activate the python environment before doing anything.

Add `finsy` as a dependency to your project. This will install finsy inside your virtual 
environment.

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
```

Start Visual Studio Code and open a window to your project directory:

```console
(.venv) $ code .
```

Tell pyright/pylance where to find the `finsy/proto` directory. To do this, add the following
text to your `pyproject.toml` file.

```toml
[tool.pyright]

[[executionEnvironments]]
root = ".venv/lib/python3.10/site-packages/finsy"
extraPaths = [".venv/lib/python3.10/site-packages/finsy/proto"]
```

With this snippet, VSCode will be able to analyze the syntax of the protobuf "_pb2" files
included with Finsy.

We're done setting up the project. In the next section, we'll write a quick demo program.

## ◉ Your First Demo Program

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

```console
(.venv) $ python demo0.py
```

You can edit the `ADDRESS` variable to specify a different P4Runtime GRPC service. GRPC uses 
a string of the form "HOST:PORT".

### Local Testing

If you don't have an existing P4Runtime target, you can start a test P4Runtime server. 
Open a second terminal and start the test P4Runtime server:

```console
(.venv) $ python -m finsy.test.p4runtime_server --port=50001
```

Now, re-run `python demo0.py`.
