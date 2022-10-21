# Hello Demo

The "hello" example consists of three demo programs that use the same P4 program.

## demo0.py

This demo program reads an existing P4Info file and prints out a description of its 
contents.

```
$ python demo0.py p4src/hello.p4info.txt
```

You should see output like:

```
hello.p4 (version=1, arch=v1model)
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
📋 ipv4[1024]
   ipv4_dst:32 
   forward(port:9) flood() MyIngress.drop() 
📬 packet_in
   ingress_port:9 _pad:7 
📬 packet_out
   egress_port:9 _pad:7
```

The first line is the name of the P4 program along with its version and architecture.

Next, there is a description of the `ipv4` table (📋). It has a maximum size of 1024 entries.
The first two lines are match fields and actions respectively. The `ipv4` table has one 
match field `ipv4_dst` which is 32 bits wide.

Match fields and action parameters show the `name` and `bitwidth`.
The delimiter between the field `name` and its `bitwidth` indicates the type of field:

- `:` EXACT
- `/` LPM
- `/&` TERNARY
- `?` OPTIONAL
- `..` RANGE

If the `ipv4_dst` field was LPM, it would be displayed as `ipv4_dst/32` instead of 
`ipv4_dst:32`.

The two mailbox icons (📬) describe the packet metadata for `packet_in` and `packet_out` 
messages.

## demo1.py

The `demo1.py` program implements a simple P4Runtime controller that does flooding. Incoming 
packets are copied and delivered to all other ports using a `P4MulticastGroupEntry`. In addition, 
copies of all packets are sent to the controller as `P4PacketIn` messages.

To run this demo, first start the controller:

```
$ python demo1.py
```

In another terminal, start the demo network:

```
$ ./demonet/run.sh
```

After a couple of seconds, the controller should connect to the switches running in Mininet. You
should see log messages like this for each switch.

```
1663717188.187 INFO finsy [sw1] Channel up (is_primary=True, election_id=10, primary_id=10, p4r=1.4.0-rc.5): (1)s1-eth1 (2)s1-eth2
1663717188.201 INFO finsy [sw1] Pipeline installed: pipeline='hello.p4' version='1' arch='v1model'
1663717188.201 INFO finsy [sw1] Channel ready (is_primary=True): pipeline='hello.p4' version='1' arch='v1model'
```

In the demo network (Mininet) shell, run the `pingall` command.

```
mininet> pingall
```

You should see all IPv4 packets copied to the controller as `P4PacketIn` messages.

To stop the demo program, type CONTROL-C.

If you re-run `demo1.py` without stopping Mininet, you should notice that there is no
"Pipeline installed" log message. The demo program detects that the "hello.p4" pipeline is already 
installed.

If you run two instances of `demo1.py`, the second instance will log `is_primary=False`
because there is already a primary controller. The `demo1` program is not designed to run as a backup 
controller, so it will repeatedly fail/retry with a `PERMISSION_DENIED` error. (There is support for 
running as a backup in `demo2`.)

To shutdown Mininet, type `exit`.

## demo2.py

The `demo2.py` program adds to the previous demo by learning which IPv4 addresses are on which ports. 
It does this by listening to ARP packets. Unmatched packets are dropped. In this example, only ARP
packets are sent to the controller.

To run this demo, first start the controller:

```
$ python demo2.py
```

In another terminal, start the demo network (if it is not already running):

```
$ ./demonet/run.sh
```

In the demo network (Mininet) shell, run the `ping` command.

```
mininet> h1 ping h3
```

There may be some packet loss, until the hosts learn each other's addresses with ARP. You 
can also try the backwards direction:

```
mininet> h3 ping h1
```

The demo2 program can recognize when it is run as a backup controller. If you run two instances
of demo2, you can see that the second instance runs as a backup. If you stop the primary controller, 
the backup controller will automatically take over. 

However, demo2 is a simple implementation that resets everything to the empty state (using delete_all)
when it becomes a primary controller. A real controller would reconcile with the running state to
minimize the disruption to the network.

## demo3.py (Advanced)

The `demo3.py` program tests support for "roles". Roles are a feature of P4Runtime that let you
have multiple primary controllers for a switch. The default role ("") gives full pipeline
read-write access. One can also define a role configuration that specifies how multiple primaries
coordinate access to resources and divide their labor. 

`demo3.py` adds a second primary connection to `s1` that uses the "backup" role. The "backup" 
role has read-only access, but still receives `PacketIn` messages. The role 
configuration `P4RoleConfig` is specific to Stratum only. 
