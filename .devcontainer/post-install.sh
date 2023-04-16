#!/bin/bash

set -ex

echo "Install poetry."
python3 .devcontainer/install-poetry.py

echo "Install project dependencies."
poetry config virtualenvs.in-project true
poetry install

echo "Done."
