# Finsy Examples

Here are some example programs that demonstrate how to use Finsy.

In each example directory, you'll find two support directories: `p4src` and `demonet`.

- `p4src` contains the source code for a P4 program, along with the compiled code for
bmv2. Each Finsy controller will load this program into the switch for its forwarding
pipeline. 
- `demonet` contains a shell script and resources for setting up a demonstration 
Mininet network. To run the demo network, type `./demonet/run.sh`. The demonet script uses 
`podman` to run the demonstration network in containers.

### Requirements

- Python 3.10 virtual environment with `finsy` installed.
- [podman](https://podman.io/) and a unix shell for `run.sh`.

## gnmi

The [gnmi](./gnmi/README.md) directory contains programs that demonstrate Finsy's standalone gNMI API.

## hello

The [hello](./hello/README.md) directory contains several introductory demo programs. These examples use 
a minimal `hello.p4` program to demonstrate Finsy with a single table.

## l2_switch

The [l2_switch](./l2_switch/README.md) directory implements a controller for the P4 program from the
l2_switch example from ["p4runtime-go-client"](https://github.com/antoninbas/p4runtime-go-client).

## ngsdn

The [ngsdn](./ngsdn/README.md) directory implements a controller similar to the ONOS example in ["Next-Gen SDN Tutorial (Advanced)"](https://github.com/opennetworkinglab/ngsdn-tutorial).

In this example, the `p4src` directory is embedded in the `ngsdn` Python package. This example also uses
the third-party `prometheus-client` to export statistics to the Prometheus/Grafana.

## simple

The [simple](./simple/README.md) directory contains a P4Runtime script for the `simple_router` example from ["P4App"](https://github.com/p4lang/p4app/tree/master/examples/simple_router.p4app)

## References

Most of the Finsy example programs use P4 programs from other open source projects. These
projects are listed here:

- ["p4runtime-go-client"](https://github.com/antoninbas/p4runtime-go-client), Apache 2.0 license. Copied ["l2_switch.p4" (Oct-2020/9212bb6)](https://github.com/antoninbas/p4runtime-go-client/commits/main/cmd/l2_switch/l2_switch.p4).
- ["Next-Gen SDN Tutorial (Advanced)"](https://github.com/opennetworkinglab/ngsdn-tutorial), Apache-2.0 license. Copied ["main.p4" (Nov-2019/bf2289e)](https://github.com/opennetworkinglab/ngsdn-tutorial/commits/advanced/solution/p4src/main.p4).
