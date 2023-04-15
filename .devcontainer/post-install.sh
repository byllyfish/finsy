#!/bin/bash

set -ex

WORKSPACE_DIR="$(pwd)"

# Install poetry.
pip3 install --user poetry

# Prepare poetry to work inside a container.
poetry config cache-dir "${WORKSPACE_DIR}/.cache"
poetry config virtualenvs.in-project true

# Install all dependencies.
poetry install

echo "Done."
