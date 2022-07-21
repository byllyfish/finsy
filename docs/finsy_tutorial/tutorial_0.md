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

Visual Studio Code (VSCode) is an IDE that includes support for Python.


## ◉ Create the Python Project

Open a Terminal and navigate to the directory where you want to place your new project. Use the `poetry new`
command to create a new project directory and fill it with boilerplate.

```
poetry new finsy_demo
```

Change into your new project directory and list the contents:

```
cd finsy_demo
ls
```

Check the current python interpreter version.  Then, create a new virtual environment named `.venv` using
Python 3.10:

```
python3 --version
python3 -m venv .venv
```

Activate the virtual environment, then upgrade pip and setuptools. This is the last time
we will use pip. After this, we will only use poetry to install dependencies.

```
source .venv/bin/activate
pip list
pip install -U pip setuptools
```

Note: I like to keep the Python virtual environment in a `.venv` directory local to the
project directory. Always make sure you activate the python environment before doing anything.

Add `finsy` as a dependency to your project. This will install finsy inside your virtual 
environment.

```
poetry add finsy
```

Start Visual Studio Code and open a window to your project directory:

```
code .
```

Tell pyright/pylance where to find the `finsy/proto` directory. To do this, add the following
text to your `pyproject.toml` file.

```
[tool.pyright]

[[executionEnvironments]]
root = ".venv/lib/python3.10/site-packages/finsy"
extraPaths = [".venv/lib/python3.10/site-packages/finsy/proto",]
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

```
python demo0.py
```

You can edit the `ADDRESS` variable to specify a different P4Runtime GRPC service. GRPC uses 
a string of the form "HOST:PORT".

### Local Testing

If you don't have an existing P4Runtime target, you can start a test P4Runtime server. Open a
second terminal and start the test P4Runtime server:

```
python -m finsy.test.p4runtime_server --port=50001
```
