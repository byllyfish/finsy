#!/bin/bash
#
# Update requirements.txt files to synchronize with "poetry.lock".

set -eu

if [ ! -f "./ci/requirements.txt" ]; then
    echo "Wrong directory."
    exit 1
fi

HEADER="# $(poetry --version) export at $(date)"

echo "$HEADER" > ./ci/requirements.txt
poetry export >> ./ci/requirements.txt

echo "$HEADER" > ./ci/requirements-dev.txt
poetry export --with dev >> ./ci/requirements-dev.txt

echo "$HEADER" > ./ci/requirements-extra.txt
poetry export --only extra >> ./ci/requirements-extra.txt

exit 0
