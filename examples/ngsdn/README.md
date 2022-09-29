# ngsdn Demo

This demo provides an alternate P4Runtime implementation for the [ngsdn-tutorial](https://github.com/opennetworkinglab/ngsdn-tutorial).

The P4Info file looks like this:

```
<Unnamed> (version=, arch=v1model)
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
📋 l2_exact_table[1024]
   dst_addr:48 
   set_egress_port(port_num:9) ↓drop()
   📈counter-both, 🔒drop()
📋 l2_ternary_table[1024]
   dst_addr/&48 
   set_multicast_group(gid:16) ↓drop()
   📈counter-both, 🔒drop()
📋 ndp_reply_table[1024]
   target_ipv6_addr:128 
   ndp_ns_to_na(target_mac:48) ↓NoAction()
   📈counter-both
📋 my_station_table[1024]
   dst_addr:48 
   NoAction()
   📈counter-both
📋 routing_v6_table[1024] -> 📦 ecmp_selector[1024]
   dst_addr/128 
   set_next_hop(dmac:48) ↓NoAction()
   📈counter-both
📋 srv6_my_sid[1024]
   dst_addr/128 
   srv6_end() ↓NoAction()
   📈counter-both
📋 srv6_transit[1024]
   dst_addr/128 
   srv6_t_insert_2(s1:128, s2:128) srv6_t_insert_3(s1:128, s2:128, s3:128) ↓NoAction()
   📈counter-both
📋 acl_table[1024]
   ingress_port/&9 dst_addr/&48 src_addr/&48 ether_type/&16 ip_proto/&8 icmp_type/&8 l4_src_port/&16 l4_dst_port/&16 
   send_to_cpu() clone_to_cpu() drop() ↓NoAction()
   📈counter-both
📦 ecmp_selector[1024]
   type=selector max_group_size=0 tables=routing_v6_table
📬 packet_in
   ingress_port:9 _pad:7 
📬 packet_out
   egress_port:9 _pad:7
```

## Running the Demo

You will need to install additional packages into your Python virtual environment from `requirements.txt`. 
Inside your `venv`, type `pip install -r requirements.txt`.

To run the demo network, type `./demonet/run.sh`.

To run the Finsy example program, type `python -m ngsdn`.
