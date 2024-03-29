# gNMI Demo

The gnmi demo programs demonstrate how to use Finsy's `GNMIClient` and `GNMIPath` classes.

The demo network looks like this picture. To start Mininet, type `./net/run.py`.

![Network Map](net/map.png)

## demo1.py

The demo1 program prints out a list of interface names and their operational status.

```
$ python demo1.py
Interface 's1-eth1' is UP
```

## demo2.py

The demo2 program subscribes to changes in the operational status of each interface.

```
$ python demo2.py 
initial: s1-eth1 is UP
update:  s1-eth1 is DOWN
update:  s1-eth1 is UP
```

You can change the operational status of a switch interface by setting the host `h1`
interface down and up.

```
mininet> h1 ifconfig eth0 down
mininet> h1 ifconfig eth0 up
```

Note that h1's `eth0` is connected to `s1-eth1` in the demo topology.

## demo3.py

The demo3 program also subscribes to changes in the operational status of each interface. 
This time, it also uses a gNMI set operation to toggle the switch interface up and down.

```
$ python demo3.py 
initial: s1-eth1 is UP
update:  s1-eth1 is DOWN
update:  s1-eth1 is UP
update:  s1-eth1 is DOWN
update:  s1-eth1 is UP
```
