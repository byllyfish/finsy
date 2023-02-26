# l2_switch Demo

The l2_switch demo implements a controller for a simple Layer2 switch.
This example uses the P4 program from ["p4runtime-go-client"](https://github.com/antoninbas/p4runtime-go-client), and implements a controller
similar to that project's demo program.

The P4Info for l2_switch looks like this:

```
<Unnamed> (version=, arch=v1model)
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
📋 smac[4096]
   srcAddr:48 
   learn_mac() NoAction() 
   ⏱ notify_control, 🔒learn_mac()
📋 dmac[4096]
   dstAddr:48 
   fwd(eg_port:9) broadcast(mgrp:16) drop() 
📈 igPortsCounts[512]: packets
📈 egPortsCounts[512]: packets
📇 digest_t
   srcAddr:48 ingressPort:9
```

This P4Info file has two tables: `smac` and `dmac`.

Table `smac` supports an idle timeout (⏱) and its default action is constant (learn_mac).

This program has two indirect packet counters, `igPortsCounts` and `egPortsCounts`. This program
also receives updates from the switch in a form of a digest `digest_t`with two fields: `srcAddr` and `ingressPort`.

## Running the Demo

To run the demo network, type `./net/run.py`.

To run the Finsy example program, type `python demo.py`.

Note: The demo network uses `simple_switch_grpc` because I haven't been able to make digests work using `stratum_bmv2`.
