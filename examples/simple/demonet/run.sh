#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$0")

podman --noout create --privileged --rm -it \
    --name mininet \
    --publish 50001:50001 \
    opennetworking/p4mn \
    --custom /root/demonet/simple_topo.py --topo simple

podman cp "$SCRIPT_DIR/." mininet:/root/demonet

podman start -ai mininet
