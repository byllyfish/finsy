#!/bin/bash
#
# Update requirements.txt files to synchronize with "uv.lock".

set -eu

if [ ! -f "./ci/requirements.txt" ]; then
    echo "Wrong directory."
    exit 1
fi

uv export --quiet --frozen --no-annotate --format requirements-txt --no-emit-local --no-dev --output-file ./ci/requirements.txt
uv export --quiet --frozen --no-annotate --format requirements-txt --no-emit-local --output-file ./ci/requirements-dev.txt
uv export --quiet --frozen --no-annotate --format requirements-txt --only-group demonet --output-file ./ci/requirements-demonet.txt

exit 0
