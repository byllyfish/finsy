# Packet Replication: MulticastGroupEntry and CloneSessionEntry

This document describes how to use the P4MulticastGroupEntry and P4CloneSessionEntry 
classes to construct P4Runtime messages. (§ 9.5)

The P4Runtime protocol refers to MulticastGroupEntry and CloneSessionEntry as
subtypes of `PacketReplicationEngineEntry`. Finsy does not have a class that
corresponds to `PacketReplicationEngineEntry`.

Classes used:

- P4MulticastGroupEntry
- P4CloneSessionEntry

All examples are interactive using the Python REPL.

Here's the initial setup.

```pycon
>>> from finsy import P4MulticastGroupEntry, P4CloneSessionEntry, P4Schema
>>> from pathlib import Path
>>> p4info = P4Schema(Path('examples/ngsdn/ngsdn/p4/main.p4info.txtpb'))

```

MulticastGroupEntry and CloneSessionEntry are not objects named in a P4Info
file. However, the `encode()` protocol still requires a P4Schema object. The
P4Schema is currently unused, but it may be used in the future to support
runtime translation of strings to port numbers.

## Replicas

When a packet is replicated to a port, the port may include an instance number.
This allows a packet to be copied more than once to the same egress port.
Port replicas are represented in Finsy by a 2-tuple `(port: int, instance: int)`.
If you specify a replica as just the port number, the instance number will 
default to 0.  (FIXME: Should this be 1?)

# P4MulticastGroupEntry (§ 9.5.1)

The P4MulticastGroupEntry class stores a human-readable version of the
P4Runtime MulticastGroupEntry, which is used to replicate a packet to different
(or the same) egress ports.


```python
P4MulticastGroupEntry(
    multicast_group_id: int = 0, 
    *, 
    replicas: Sequence[tuple[int, int] | int] = ()
)
```

## Reading Entries

### All multicast group entries.

```pycon
>>> entry = P4MulticastGroupEntry()
>>> entry.encode(p4info)
packet_replication_engine_entry {
  multicast_group_entry {
  }
}

```

### MulticastGroupEntry with multicast_group_id=1.

```pycon
>>> entry = P4MulticastGroupEntry(1)
>>> entry.encode(p4info)
packet_replication_engine_entry {
  multicast_group_entry {
    multicast_group_id: 1
  }
}

```

## Writing Entries

### Insert multicast group entry to replicate a packet to egress ports 1, 2, 3 and 4.

```pycon
>>> entry = +P4MulticastGroupEntry(1, replicas=[1, 2, 3, 4])
>>> entry.encode_update(p4info)
type: INSERT
entity {
  packet_replication_engine_entry {
    multicast_group_entry {
      multicast_group_id: 1
      replicas {
        egress_port: 1
      }
      replicas {
        egress_port: 2
      }
      replicas {
        egress_port: 3
      }
      replicas {
        egress_port: 4
      }
    }
  }
}

```

### Delete multicast group entry with id=5.

```pycon
>>> entry = -P4MulticastGroupEntry(5)
>>> entry.encode_update(p4info)
type: DELETE
entity {
  packet_replication_engine_entry {
    multicast_group_entry {
      multicast_group_id: 5
    }
  }
}

```

### Modify multicast group entry 1 to replicate packet 3 times to egress port 2.

```pycon
>>> entry = ~P4MulticastGroupEntry(1, replicas=[(2, 1), (2, 2), (2, 3)])
>>> entry.encode_update(p4info)
type: MODIFY
entity {
  packet_replication_engine_entry {
    multicast_group_entry {
      multicast_group_id: 1
      replicas {
        egress_port: 2
        instance: 1
      }
      replicas {
        egress_port: 2
        instance: 2
      }
      replicas {
        egress_port: 2
        instance: 3
      }
    }
  }
}

```

# P4CloneSessionEntry

The P4CloneSessionEntry class stores a human-readable version of the 
P4Runtime CloneSessionEntry, which is used to make clones of packets in the
ingress and egress pipelines.

```python
P4CloneSessionEntry(
    session_id: int = 0, 
    *, 
    class_of_service: int = 0, 
    packet_length_bytes: int = 0, 
    replicas: Sequence[tuple[int, int] | int] = ()
)
```

## Reading Entries

### All clone session entries.

```pycon
>>> entry = P4CloneSessionEntry()
>>> entry.encode(p4info)
packet_replication_engine_entry {
  clone_session_entry {
  }
}

```

### CloneSessionEntry with session_id=1.

```pycon
>>> entry = P4CloneSessionEntry(1)
>>> entry.encode(p4info)
packet_replication_engine_entry {
  clone_session_entry {
    session_id: 1
  }
}

```

## Writing Entries

### Insert clone session entry to replicate a packet to ports 1, 2, and 3.

```pycon
>>> entry = +P4CloneSessionEntry(
...   1, 
...   class_of_service=2, 
...   packet_length_bytes=64,
...   replicas=[1, 2, 3]
... )
>>> entry.encode_update(p4info)
type: INSERT
entity {
  packet_replication_engine_entry {
    clone_session_entry {
      session_id: 1
      replicas {
        egress_port: 1
      }
      replicas {
        egress_port: 2
      }
      replicas {
        egress_port: 3
      }
      class_of_service: 2
      packet_length_bytes: 64
    }
  }
}

```

### Delete clone session entry with id=6.

```pycon
>>> entry = -P4CloneSessionEntry(6)
>>> entry.encode_update(p4info)
type: DELETE
entity {
  packet_replication_engine_entry {
    clone_session_entry {
      session_id: 6
    }
  }
}

```

### Modify clone session entry 2 to replicate packet twice to egress port 3.

```pycon
>>> entry = ~P4CloneSessionEntry(2, packet_length_bytes=96, replicas=[(3, 1), (3, 2)])
>>> entry.encode_update(p4info)
type: MODIFY
entity {
  packet_replication_engine_entry {
    clone_session_entry {
      session_id: 2
      replicas {
        egress_port: 3
        instance: 1
      }
      replicas {
        egress_port: 3
        instance: 2
      }
      packet_length_bytes: 96
    }
  }
}

```
