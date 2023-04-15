#!/bin/bash

set -ex

# Install poetry.
python3 .devcontainer/install-poetry.py

# Install all dependencies.
poetry install

echo "Done."
