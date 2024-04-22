#!/bin/bash

set -e

CURRENT_DIR="$(pwd)"
P4C_TOOL="$CURRENT_DIR/examples/tools/p4c.py"

p4c() {
    pushd "$1" || exit 1
    $P4C_TOOL "$2" $3
    popd || exit 1
}


p4c examples/basic/p4 basic.p4
p4c examples/flowcache/p4 flowcache.p4
p4c examples/hello/p4 hello.p4
p4c examples/int/p4/int_v1.0 int.p4 '-DBMV2=1'
p4c examples/l2_switch/p4 l2_switch.p4
p4c examples/ngsdn/ngsdn/p4 main.p4
p4c examples/simple/p4 simple_router.p4
p4c examples/tunnel/p4 advanced_tunnel.p4

exit 0
