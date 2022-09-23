# 🐟 Tutorial 2: Using gNMI

🚧 This tutorial is under development.

In this tutorial, we will demonstrate how to use the `Finsy` gNMI client.
gNMI is a protocol for reading and writing a key/value store that describes a 
device's configuration and runtime state.

Each gNMI key is a path, e.g. `interfaces/interface/state/oper-status`. A path
may specify a specific instance with embedded key-value pairs. For
example, the path `interfaces/interface[name=en0]/state/oper-status` specifies
the operational status of interface "en0" -- whether the interface is up or not.

The gNMI client API consists of two classes `gNMIClient` and `gNMIPath`. A `gNMIClient` 
object manages the client TCP connection to the target device. A `gNMIPath` creates and 
manipulates gNMI path objects.

First, we'll discuss the use of gNMI paths.

## ◉ gNMIPath

Use the `gNMIPath` class to create and manipulate gNMI paths.

A gNMI path is a sequence of names separated by '/'. Each name may
optionally have one or more key-value pairs. Each key-value pair is enclosed in square brackets, 
e.g. \[key=value\]. The specification for the string format is 
[here](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-path-strings.md).

Start the Python3 asyncio REPL by typing `python -m asyncio`.

```pycon
>>> from finsy import gNMIPath
>>> p = gNMIPath("a/b[x=1]/c")
>>> p
gNMIPath('a/b[x=1]/c')
>>> len(p)
3
```

Use the `path` property to access the underlying `gnmi.Path` protobuf object. 

```pycon
>>> p.path
elem {
  name: "a"
}
elem {
  name: "b"
  key {
    key: "x"
    value: "1"
  }
}
elem {
  name: "c"
}
```

You can retrieve element names from the gNMIPath object using [] and an integer subscript.

```pycon
>>> p[0]
'a'
>>> p[1]
'b'
```

Note that the `p[1]` did not include the `x` key. You can access an element's key using 
two subscripts. The first subscript identifies the element and the second identifies the key.

```pycon
>>> p["b", "x"]
'1'
>>> p[1, "x"]
'1'
```

In most cases, a key's name will be unique to a specific element of the path. As a shorthand, 
you can retrieve the key's value using a single string subscript.

```pycon
>>> p["x"]
'1'
```

You can retrieve a portion of a path using [] and a slice subscript.

```pycon
>>> p[0:2]
gNMIPath('a/b[x=1]')
>>> p[1:2]
gNMIPath('b[x=1]')
```

### Setting Keys

gNMIPath objects are intended to be immutable. You can set an element key using the `set()` method. 
Remember that this method constructs and returns a new object. You must store the result in a 
new variable; the original object is unchanged.

```pycon
>>> q = p.set("c", x=1, y=2)
>>> q
gNMIPath('a/b[x=1]/c[x=1][y=2]')
```

The `set()` method replaces the entire key. To delete all keys from element "b", call `set` with
no keyword arguments.

```pycon
>>> q.set("c")
gNMIPath('a/b[x=1]/c')
```

If the gNMIPath has an existing key, you do not need to specify the element name.

```pycon
>>> p.set(x=99)
gNMIPath('a/b[x=99]/c')
```

### Editing Paths

You can concatenate paths using the `/` operator.

```pycon
>>> gNMIPath("interfaces") / "interface[name=eth0]" / "state/oper-status"
gNMIPath('interfaces/interface[name=eth0]/state/oper-status')
```

Avoid using accessors on the underlying `gnmi.Path` object. It's easy to inadvertently
add a key. Here is one way that could happen:

```
>>> p.path.elem[2].key["d"]    # adds empty "d" key!
''
>>> p
gNMIPath('a/b[x=1]/c[d=]')
```

## ◉ gNMIClient

The gNMIClient class provides an API to retrieve values from the key/value store that describes a 
device's configuration and runtime state. The client can also set certain values controlling
the device's configuration state.

Finally, a gNMIClient can sample or observe how values change over time using the `subscribe` API.

### gNMI Get

Run the asyncio REPL, `python -m asyncio`. Unlike the normal Python REPL we used above,
the asyncio REPL allows you to make async calls.

```pycon
>>> from finsy import gNMIClient, gNMIPath
>>> client = gNMIClient("127.0.0.1:50001")
>>> interface_id = gNMIPath("interfaces/interface[name=*]/state/id")
```

`interface_id` is the gNMI path for the port number of an interface. The `*` in `[name=*]` key
specifies we want to match any interface name.

```pycon
>>> async with client:
...   result = await client.get(interface_id)
... 
>>> len(result)
2
>>> for i in result: print(i)
...
gNMIUpdate(timestamp=1659325786657061923, path=gNMIPath('interfaces/interface[name=s1-eth1]/state/id'), typed_value=`uint_val: 1`)
gNMIUpdate(timestamp=1659325786657089008, path=gNMIPath('interfaces/interface[name=s1-eth2]/state/id'), typed_value=`uint_val: 2`)
```

The output shows two values because our `s1` switch has two interfaces. From the "name" key, we see that
the interface names are "s1-eth1" and "s1-eth2". Their interface id values are `1` and `2` respectively.

The value of `typed_value` is in backticks, because value is a `gnmi.TypedValue`. This is a protobuf 
derived class, not a Finsy class.

In the output above, the value of `id` is of type uint_val.
To access this in your Python program, you will type `update.typed_value.uint_val`. As you will see below, you 
can also access the value as just `update.value`.

For reference, here is the definition of `gnmi.TypedValue` from gnmi.proto:

```protobuf
message TypedValue {
  // One of the fields within the val oneof is populated with the value
  // of the update. The type of the value being included in the Update
  // determines which field should be populated. In the case that the
  // encoding is a particular form of the base protobuf type, a specific
  // field is used to store the value (e.g., json_val).
  oneof value {
    string string_val = 1;            // String value.
    int64 int_val = 2;                // Integer value.
    uint64 uint_val = 3;              // Unsigned integer value.
    bool bool_val = 4;                // Bool value.
    bytes bytes_val = 5;              // Arbitrary byte sequence value.
    float float_val = 6 [deprecated=true]; // Deprecated - use double_val.
    double double_val = 14;           // Floating point value.
    Decimal64 decimal_val = 7 [deprecated=true]; // Deprecated - use double_val.
    ScalarArray leaflist_val = 8;     // Mixed type scalar array value.
    google.protobuf.Any any_val = 9;  // protobuf.Any encoded bytes.
    bytes json_val = 10;              // JSON-encoded text.
    bytes json_ietf_val = 11;         // JSON-encoded text per RFC7951.
    string ascii_val = 12;            // Arbitrary ASCII text.
    // Protobuf binary encoded bytes. The message type is not included.
    // See the specification at
    // github.com/openconfig/reference/blob/master/rpc/gnmi/protobuf-vals.md
    // for a complete specification. [Experimental]
    bytes proto_bytes = 13;
  }
}
```

Let's examine the first result.

```pycon
>>> update1 = result[0]
>>> update1
gNMIUpdate(timestamp=1659128669262256490, path=gNMIPath('interfaces/interface[name=s1-eth1]/state/id'), typed_value=`uint_val: 1`)
```

We are interested in the name of the interface and the value of 'id'. Note that we can obtain the value
using the convenient `.value` property. If necessary, you can determine the underlying protobuf type 
using the `WhichOneof()` method on `.typed_value`.

```pycon
>>> update1.path["name"]
's1-eth1'
>>> update1.value
1
>>> update1.typed_value.WhichOneof("value")
'uint_val'
>>> update1.typed_value.uint_val
1
```

Let's collect the interface names and values into a Python dictionary.

```pycon
>>> ports = { update.path["name"]: update.value for update in result }
>>> ports
{'s1-eth1': 1, 's1-eth2': 2}
```

Now, let's display the value of `interfaces/interface/state/oper-status` for the interfaces.

```pycon
>>> oper_status = gNMIPath("interfaces/interface[name=*]/state/oper-status")
>>> paths = [oper_status.set(name=name) for name in ports]
>>> async with client:
...   result = await client.get(*paths)]
>>> for update in result:
...   print(update.path["name"], update.value)
... 
s1-eth1 UP
s1-eth2 UP
```

### gNMI Subscribe

In this section, we show how to use gNMI subscribe. Before we begin, let's open the gNMI
client and leave it open:

```pycon
>>> await client.open()
```

In previous examples, we used `async with`, which opened and closed the client for us. To
use the subscribe API, we'll want the client to remain open.

First, we create a `gNMISubscription` object tied to a client. Then, we call methods on
the subscription object to register for the events we are interested in.

Here we create oper_status paths for each interface name in `ports`.

```pycon
>>> sub = client.subscribe()
>>> port_status = [oper_status.set(name=name) for name in ports]
>>> sub.on_change(*port_status)
```

A gNMI subscription does not send the actual `SubscribeRequest` until we
call `synchronize`. The `synchronize()` method returns the initial state
of the values we are subscribing to.

```pycon
>>> async for update in sub.synchronize():
...   print(update)
...
gNMIUpdate(timestamp=1659380663818110532, path=gNMIPath('interfaces/interface[name=s1-eth1]/state/oper-status'), typed_value=`string_val: "UP"`)
gNMIUpdate(timestamp=1659380663818678235, path=gNMIPath('interfaces/interface[name=s1-eth2]/state/oper-status'), typed_value=`string_val: "UP"`)
```

We are not allowed to make changes to the subscription after calling `synchronize`.
To receive further changes to the subscription, we call the `updates` method.
Here we will create an asyncio task to do that.

```pycon
>>> async def listen():
...   async for update in sub.updates():
...     print("\n  ***", update)
... 
>>> listen_task = asyncio.create_task(listen())
```

If we check the topology in Mininet, we can see that interface `s1-eth1` on switch `s1` is
connected to interface `s2-eth3` on switch `s2`. Let's disable interface `s2-eth3` and see
how this changes that status of `s1-eth1`.

```shell
mininet> net
h1 h1-eth0:s2-eth1
h2 h2-eth0:s2-eth2
h3 h3-eth0:s3-eth1
h4 h4-eth0:s3-eth2
s1 lo:  s1-eth1:s2-eth3 s1-eth2:s3-eth3
s2 lo:  s2-eth1:h1-eth0 s2-eth2:h2-eth0 s2-eth3:s1-eth1
s3 lo:  s3-eth1:h3-eth0 s3-eth2:h4-eth0 s3-eth3:s1-eth2
mininet> sh ifconfig s2-eth3 down
```

We should see some new output in the asyncio REPL from our "listen_task". The status of the 
interface is now down.

```pycon
>>> 
  *** gNMIUpdate(timestamp=1659376837812996081, path=gNMIPath('interfaces/interface[name=s1-eth1]/state/oper-status'), typed_value=`string_val: "DOWN"`)
```

Use Mininet to re-enable the interface. You should see another gNMIUpdate message for interface
"s1-eth1".

```shell
mininet> sh ifconfig s2-eth3 up
```

Let's leave our `listen_task` running. In the next section, we will disable the interface using gNMI set.

### gNMI Set

We use a gNMI Set operation to create, modify or delete a value. Let's use gNMI set to re-enable the 
interface we just disabled.

We'll need to use the `TypedValue` class directly. Let's import the "gnmi" protobuf definitions.
We also create a path to the "enabled" variable we'll need to set.

```pycon
>>> from finsy.proto import gnmi
>>> enabled = gNMIPath("interfaces/interface[name=s2-eth3]/config/enabled")
```

Before starting, let's double-check the status of interface "s2-eth3". This 
interface is on switch "s2", so we temporarily create another client:

```pycon
>>> async with gNMIClient("127.0.0.1:50002") as s2:
...   result = await s2.get(oper_status.set(name="s2-eth3"))
...
>>> result
[gNMIUpdate(timestamp=1659379912824896183, path=gNMIPath('interfaces/interface[name=s2-eth3]/state/oper-status'), typed_value=`string_val: "DOWN"`)]
```

Now, let's re-enable the interface:

```pycon
>>> async with gNMIClient("127.0.0.1:50002") as s2:
...   result = await s2.set(update={enabled: gnmi.TypedValue(bool_val=True)})
...
(something is not working right?)
```
