#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$0")

podman --noout create --privileged --rm -it \
    --name mininet \
    --publish 50001:50001 \
    --entrypoint python3 \
    opennetworking/mn-stratum \
    /root/demonet/simple_topo.py

podman cp "$SCRIPT_DIR/." mininet:/root/demonet

podman start -ai mininet
