#!/bin/bash

set -e

case "$1" in 
    stratum)
        MININET_IMAGE="opennetworking/mn-stratum"
        ;;
    *)
        MININET_IMAGE="opennetworking/p4mn"
        ;;
esac

podman run --privileged --rm -it \
    --name mininet \
    --publish 50001-50003:50001-50003 \
    "$MININET_IMAGE" --topo=linear,3 --mac
