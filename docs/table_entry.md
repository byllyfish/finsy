# Table Entries

This document describes how to use the P4TableEntry classes to construct 
P4Runtime `TableEntry` messages. (§ 9.1)

Classes used:

- P4Schema
- P4TableEntry
- P4TableMatch (alias: Match)
- P4TableAction (alias: Action)
- P4IndirectAction (alias: IndirectAction)

All examples are interactive using the Python REPL.

Here's the initial setup:

```pycon
>>> from finsy import P4Schema, P4TableEntry, Match, Action, IndirectAction
>>> from pathlib import Path
>>> p4info = P4Schema(Path('examples/ngsdn/ngsdn/p4/main.p4info.txtpb'))

``` 

To review the schema from the ngsdn example, type `print(p4info)`.

# P4TableEntry

The P4TableEntry class stores a human-readable version of a P4Runtime TableEntry. 

The constructor has one positional parameter (table_id). The rest are keyword-only parameters.
All parameters are optional.

```python
P4TableEntry(
    table_id: str = '', 
    *, 
    match: P4TableMatch | None = None, 
    action: P4TableAction | P4IndirectAction | None = None, 
    priority: int = 0,
    meter_config: P4MeterConfig | None = None,
    counter_data: P4CounterData | None = None,
    meter_counter_data: P4MeterCounterData | None = None,
    is_default_action: bool = False,
    idle_timeout_ns: int = 0,
    time_since_last_hit: int | None = None,
    metadata: bytes = b''
)
```

For more on the P4TableEntry, type `help(P4TableEntry)`.

Finsy handles encoding and decoding of P4TableEntry automatically when you use the
`Switch.read` and `Switch.write` methods. The following examples manually encode
entries using the `P4Schema` to show the exact protobuf result.

## Reading Entries

### All entries in all tables (except for default entries).

```pycon
>>> entry = P4TableEntry()
>>> entry.encode(p4info)
table_entry {
}

```

### All entries in `l2_exact_table` (except for the default entry).

```python
>>> entry = P4TableEntry('l2_exact_table')
>>> entry.encode(p4info)
table_entry {
  table_id: 34391805
}

```

### The default entry in `l2_exact_table`.

```python
>>> entry = P4TableEntry('l2_exact_table', is_default_action=True)
>>> entry.encode(p4info)
table_entry {
  table_id: 34391805
  is_default_action: true
}

```

### The entry in `l2_exact_table` with dst_addr '00:00:00:00:00:01'.

```python
>>> entry = P4TableEntry(
...   'l2_exact_table',
...   match=Match(dst_addr='00:00:00:00:00:01'),
... )
>>> entry.encode(p4info)
table_entry {
  table_id: 34391805
  match {
    field_id: 1
    exact {
      value: "\001"
    }
  }
}

```

### All entries in `l2_ternary_table` with priority 11.

```python
>>> entry = P4TableEntry('l2_ternary_table', priority=11)
>>> entry.encode(p4info)
table_entry {
  table_id: 48908925
  priority: 11
}

```

### All entries in `l2_ternary_table` with metadata b'abc'.

```python
>>> entry = P4TableEntry('l2_ternary_table', metadata=b'abc')
>>> entry.encode(p4info)
table_entry {
  table_id: 48908925
  metadata: "abc"
}

```

### All entries in `acl_table` with the `drop` action.

```python
>>> entry = P4TableEntry('acl_table', action=Action('drop'))
>>> entry.encode(p4info)
table_entry {
  table_id: 33951081
  action {
    action {
      action_id: 28396054
    }
  }
}

```

### All entries from `l2_exact_table` including counter data.

```python
>>> from finsy import P4CounterData
>>> entry = P4TableEntry('l2_exact_table', counter_data=P4CounterData())
>>> entry.encode(p4info)
table_entry {
  table_id: 34391805
  counter_data {
  }
}

```

### All entries from `l2_exact_table` including the `time_since_last_hit` information.

```python
>>> entry = P4TableEntry('l2_exact_table', time_since_last_hit=0)
>>> entry.encode(p4info)
table_entry {
  table_id: 34391805
  time_since_last_hit {
  }
}

```

Note: The l2_exact_table does not actually support timeouts, so the P4Runtime server will return an
INVALID_ARGUMENT error.

## Writing Entries

When you write a table entry, you specify INSERT (+), DELETE (-) or MODIFY (~) using a
unary operator.

### Add entry to `l2_exact_table`.

```pycon
>>> entry = +P4TableEntry(
...   'l2_exact_table',
...   match=Match(dst_addr='00:00:00:00:00:01'),
...   action=Action('set_egress_port', port_num=1),
... )
>>> entry.encode_update(p4info)
type: INSERT
entity {
  table_entry {
    table_id: 34391805
    match {
      field_id: 1
      exact {
        value: "\001"
      }
    }
    action {
      action {
        action_id: 24677122
        params {
          param_id: 1
          value: "\001"
        }
      }
    }
  }
}

```

### Remove entry from `l2_exact_table`.

```pycon
>>> entry = -P4TableEntry(
...   'l2_exact_table',
...   match=Match(dst_addr='00:00:00:00:00:01'),
... )
>>> entry.encode_update(p4info)
type: DELETE
entity {
  table_entry {
    table_id: 34391805
    match {
      field_id: 1
      exact {
        value: "\001"
      }
    }
  }
}

```

### Modify default entry for `acl_table`.

```pycon
>>> entry = ~P4TableEntry(
...   'acl_table',
...   action=Action('send_to_cpu'),
...   is_default_action=True,
... )
>>> entry.encode_update(p4info)
type: MODIFY
entity {
  table_entry {
    table_id: 33951081
    action {
      action {
        action_id: 30661427
      }
    }
    is_default_action: true
  }
}

```

### Add entry to indirect table `routing_v6_table` using a "one-shot" selector.

The action weights are specified using the multiplication operator. In the one-shot below, the
actions have weights `1` and `2`.

```pycon
>>> entry = +P4TableEntry(
...   'routing_v6_table',
...   match=Match(dst_addr='2000:1234::/64'),
...   action=IndirectAction([
...     1 * Action('set_next_hop', dmac='00:00:00:00:00:01'),
...     2 * Action('set_next_hop', dmac='00:00:00:00:00:02'),
...   ]),
... )
>>> entry.encode_update(p4info)
type: INSERT
entity {
  table_entry {
    table_id: 39493057
    match {
      field_id: 1
      lpm {
        value: " \000\0224\000\000\000\000\000\000\000\000\000\000\000\000"
        prefix_len: 64
      }
    }
    action {
      action_profile_action_set {
        action_profile_actions {
          action {
            action_id: 23394961
            params {
              param_id: 1
              value: "\001"
            }
          }
          weight: 1
        }
        action_profile_actions {
          action {
            action_id: 23394961
            params {
              param_id: 1
              value: "\002"
            }
          }
          weight: 2
        }
      }
    }
  }
}

```

### Add entry to indirect table `routing_v6_table` using a "one-shot" selector with watch ports.

The action weights are specified using a 2-tuple `(weight, port)`.

```
>>> entry = +P4TableEntry(
...   'routing_v6_table',
...   match=Match(dst_addr='2000:1234::/64'),
...   action=IndirectAction([
...     (1, 1) * Action('set_next_hop', dmac='00:00:00:00:00:01'),
...     (1, 2) * Action('set_next_hop', dmac='00:00:00:00:00:02'),
...   ]),
... )
>>> entry.encode_update(p4info)
type: INSERT
entity {
  table_entry {
    table_id: 39493057
    match {
      field_id: 1
      lpm {
        value: " \000\0224\000\000\000\000\000\000\000\000\000\000\000\000"
        prefix_len: 64
      }
    }
    action {
      action_profile_action_set {
        action_profile_actions {
          action {
            action_id: 23394961
            params {
              param_id: 1
              value: "\001"
            }
          }
          weight: 1
          watch_port: "\001"
        }
        action_profile_actions {
          action {
            action_id: 23394961
            params {
              param_id: 1
              value: "\002"
            }
          }
          weight: 1
          watch_port: "\002"
        }
      }
    }
  }
}

```

### Add entry to indirect table `routing_v6_table` using a "one-shot" selector (automatic promotion)

An Action will be automatically promoted to an IndirectAction when applied to an indirect table.

```pycon
>>> entry = +P4TableEntry(
...   'routing_v6_table',
...   match=Match(dst_addr='2000:1234::/64'),
...   action=Action('set_next_hop', dmac='00:00:00:00:00:01'),
... )
>>> entry.encode_update(p4info)
type: INSERT
entity {
  table_entry {
    table_id: 39493057
    match {
      field_id: 1
      lpm {
        value: " \000\0224\000\000\000\000\000\000\000\000\000\000\000\000"
        prefix_len: 64
      }
    }
    action {
      action_profile_action_set {
        action_profile_actions {
          action {
            action_id: 23394961
            params {
              param_id: 1
              value: "\001"
            }
          }
          weight: 1
        }
      }
    }
  }
}

```

### Add entry to indirect table `routing_v6_table` using an existing ActionProfileGroup.

```pycon
>>> entry = +P4TableEntry(
...   'routing_v6_table',
...   match=Match(dst_addr='2000:1234::/64'),
...   action=IndirectAction(group_id=1234),
... )
>>> entry.encode_update(p4info)
type: INSERT
entity {
  table_entry {
    table_id: 39493057
    match {
      field_id: 1
      lpm {
        value: " \000\0224\000\000\000\000\000\000\000\000\000\000\000\000"
        prefix_len: 64
      }
    }
    action {
      action_profile_group_id: 1234
    }
  }
}

```

### Add entry to indirect table `routing_v6_table` using an existing ActionProfileMember.

```pycon
>>> entry = +P4TableEntry(
...   'routing_v6_table',
...   match=Match(dst_addr='2000:1234::/64'),
...   action=IndirectAction(member_id=9876),
... )
>>> entry.encode_update(p4info)
type: INSERT
entity {
  table_entry {
    table_id: 39493057
    match {
      field_id: 1
      lpm {
        value: " \000\0224\000\000\000\000\000\000\000\000\000\000\000\000"
        prefix_len: 64
      }
    }
    action {
      action_profile_member_id: 9876
    }
  }
}

```
