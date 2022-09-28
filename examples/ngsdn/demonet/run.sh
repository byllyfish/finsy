#!/bin/bash

set -e

podman --noout create --privileged --rm -it \
    --name mininet \
    --publish 50001-50004:50001-50004 \
    --entrypoint python3 \
    opennetworking/mn-stratum \
    /root/demonet/topo-v6.py

podman --noout pod create --replace \
    --publish 3000:3000 \
    --publish 9090:9090 \
    demo_pod

podman --noout create --rm \
    --pod demo_pod \
    --name grafana \
    grafana/grafana

podman --noout create --rm \
    --pod demo_pod \
    --name prometheus \
    prom/prometheus

podman cp demonet mininet:/root/demonet
podman cp demonet/prometheus.yml prometheus:/etc/prometheus/prometheus.yml

podman --noout pod start demo_pod
podman start -ai mininet
podman --noout pod stop demo_pod
