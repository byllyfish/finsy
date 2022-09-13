#!/bin/bash

set -e

podman run --privileged --rm -it \
    --name mininet \
    --publish 50001-50004:50001-50004 \
    opennetworking/mn-stratum --topo=linear,3
