#!/bin/bash

set -e

podman run --privileged --rm -it \
    --name mininet \
    --publish 50001:50001 \
    opennetworking/mn-stratum --topo=single,1