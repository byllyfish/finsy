# simple Demo

The simple directory demonstrates the `simple_router.p4` example from [P4App](https://github.com/p4lang/p4app).

The P4Info.txt for the `simple_router.p4` program looks like this:

```
<Unnamed> (version=, arch=v1model)
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
📋 ipv4_lpm[1024]
   dstAddr/32 
   ingress._drop() set_nhop(nhop_ipv4:32, port:9) NoAction()
📋 forward[512]
   nhop_ipv4:32 
   set_dmac(dmac:48) ingress._drop() NoAction()
📋 send_frame[256]
   egress_port:9 
   rewrite_mac(smac:48) egress._drop() NoAction()
```

## Running the Demo

To run the demo network, type `./net/run.sh`.

To load the P4 tables with the proper entries, run `python demo.py`. The program should
exit immediately with no output.

In the Mininet CLI, the `pingall` and `iperf` commands now work.
