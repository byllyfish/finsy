# Finsy Examples

Here are some example programs that demonstrate how to use Finsy.

In each example directory, you'll find two support directories: `p4` and `net`.

- `p4` contains the source code for a P4 program, along with the compiled code for
bmv2. Each Finsy controller will load this program into the switch for its forwarding
pipeline. 
- `net` contains a Python script and resources for setting up a demonstration 
Mininet network. To run the demo network, type `./net/run.py`. The `run.py` script uses 
podman or docker to run the demonstration network in a container.

### Requirements

- Python 3.10 virtual environment with `finsy` installed.
- [podman](https://podman.io/) or [docker](https://docker.com)

## gnmi

The [gnmi](./gnmi) directory contains programs that demonstrate Finsy's standalone gNMI API.

## hello

The [hello](./hello) directory contains several introductory demo programs. These examples use 
a minimal `hello.p4` program to demonstrate Finsy with a single table.

## l2_switch

The [l2_switch](./l2_switch) directory implements a controller for the P4 program from the
l2_switch example from ["p4runtime-go-client"](https://github.com/antoninbas/p4runtime-go-client).

## ngsdn

The [ngsdn](./ngsdn) directory implements a controller similar to the ONOS example in ["Next-Gen SDN Tutorial (Advanced)"](https://github.com/opennetworkinglab/ngsdn-tutorial).

In this example, the `p4` directory is embedded in the `ngsdn` Python package. This example also uses
the third-party `prometheus-client` to export statistics to Prometheus/Grafana.

## simple

The [simple](./simple) directory contains a P4Runtime script for the `simple_router` example from ["P4App"](https://github.com/p4lang/p4app/tree/master/examples/simple_router.p4app)

## tunnel

The [tunnel](./tunnel) directory contains a P4Runtime script for the `advanced_tunnel.p4` example from the [P4Runtime exercise](https://github.com/p4lang/tutorials/tree/master/exercises/p4runtime)  in the P4 tutorial.

## INT

The [INT](./int) directory contains an In-Band Network Telemetry controller adapted from the [GEANT INT implementation](https://github.com/GEANT-DataPlaneProgramming/int-platforms).

## Integration Tests

To run the integration tests, enter the examples directory and type 
`pytest`. Each test module will create a Mininet instance, run its tests in order, 
then stop Mininet.

## References

Most of the Finsy example programs use P4 programs from other open source projects. These
projects are listed here:

- ["p4runtime-go-client"](https://github.com/antoninbas/p4runtime-go-client), Apache 2.0 license. Copied ["l2_switch.p4" (Oct-2020/9212bb6)](https://github.com/antoninbas/p4runtime-go-client/commits/main/cmd/l2_switch/l2_switch.p4).
- ["Next-Gen SDN Tutorial (Advanced)"](https://github.com/opennetworkinglab/ngsdn-tutorial), Apache-2.0 license. Copied ["main.p4" (Nov-2019/bf2289e)](https://github.com/opennetworkinglab/ngsdn-tutorial/commits/advanced/solution/p4src/main.p4).
- ["P4App"](https://github.com/p4lang/p4app), Apache 2.0 license. Copied ["simple_router.p4", "parser.p4", "header.p4"](https://github.com/p4lang/p4app/tree/master/examples/simple_router.p4app).
- ["P4Runtime Tutorial"](https://github.com/p4lang/tutorials), Apache 2.0 license.
- ["Common P4-based INT implementation for bmv2-mininet and Tofino platforms"](https://github.com/GEANT-DataPlaneProgramming/int-platforms), Apache 2.0 license.
