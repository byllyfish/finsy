#!/bin/bash

set -e

podman run --privileged --rm -it \
    --name mininet \
    --publish 50001-50003:50001-50003 \
    docker.io/opennetworking/mn-stratum --topo=linear,3
