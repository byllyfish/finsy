#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$0")

podman  create --privileged --rm -it \
    --name mininet \
    --publish 50001-50003:50001-50003 \
    --sysctl net.ipv6.conf.default.disable_ipv6=1 \
    docker.io/opennetworking/p4mn \
    --custom /root/demonet/tunnel_topo.py --topo tunnel

podman cp "$SCRIPT_DIR/." mininet:/root/demonet

podman start -ai mininet
