#!/bin/bash

set -e

case "$1" in 
    stratum)
        MININET_IMAGE="docker.io/opennetworking/mn-stratum"
        ;;
    *)
        MININET_IMAGE="docker.io/opennetworking/p4mn"
        ;;
esac

podman run --privileged --rm -it \
    --name mininet \
    --publish 50001-50003:50001-50003 \
    --sysctl net.ipv6.conf.default.disable_ipv6=1 \
    "$MININET_IMAGE" --topo=linear,3 --mac
