#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$0")

podman create --privileged --rm -it \
    --name mininet \
    --publish 50001-50004:50001-50004 \
    --sysctl net.ipv6.conf.default.disable_ipv6=1 \
    --entrypoint python3 \
    docker.io/opennetworking/mn-stratum \
    /root/demonet/topo-v6.py

podman pod create --replace \
    --publish 3000:3000 \
    --publish 9090:9090 \
    --name demo_pod

podman create --rm \
    --pod demo_pod \
    --name grafana \
    docker.io/grafana/grafana

podman create --rm \
    --pod demo_pod \
    --name prometheus \
    docker.io/prom/prometheus

podman cp "$SCRIPT_DIR/." mininet:/root/demonet
podman cp "$SCRIPT_DIR/prometheus.yml" prometheus:/etc/prometheus/prometheus.yml

podman pod start demo_pod
podman start -ai mininet
podman pod stop demo_pod
