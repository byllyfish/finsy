#!/bin/bash

set -e

podman pod create --replace \
    --publish 50001-50004:50001-50004 \
    --publish 8181:8181 \
    --publish 8101:8101 \
    --name onos_pod

podman create --privileged --rm -it \
    --pod onos_pod \
    --name mininet \
    --entrypoint python3 \
    opennetworking/mn-stratum \
    /root/demonet/topo-v6.py

podman create --rm \
    --pod onos_pod \
    --name onos \
    --env ONOS_APPS=gui2,drivers.bmv2,lldpprovider,hostprovider \
    onosproject/onos:2.2.2

podman cp demonet mininet:/root/demonet

podman start onos
echo "Wait 60 seconds to onos to get ready..."
sleep 60

# Install app and netcfg.
echo "Delete app."
curl --fail -sSL --user onos:rocks --noproxy localhost \
    -X DELETE \
    'http://localhost:8181/onos/v1/applications/org.onosproject.ngsdn-tutorial' || echo "delete failed? continue..."

echo "Install app."
curl --fail -sSL --user onos:rocks --noproxy localhost \
    -X POST -H 'Content-Type:application/octet-stream' \
	'http://localhost:8181/onos/v1/applications?activate=true' \
	--data-binary @./demonet/onos/ngsdn-tutorial-1.0-SNAPSHOT.oar

echo "Install config."
curl --fail -sSL --user onos:rocks --noproxy localhost \
     -X POST -H 'Content-Type:application/json' \
	'http://localhost:8181/onos/v1/network/configuration' \
    -d@./demonet/netcfg.json

podman start -ai mininet
podman pod stop onos_pod
