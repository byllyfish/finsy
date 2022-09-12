/******************************** hello.p4 **********************************/
/*
    "Hello, world" example.

    1. ARP requests and replies are flooded to all ports. To copy to the 
    controller, include port 255 in the multicast group (ID=1).

    2. IPv4 Packets are forwarded, flooded, or dropped based on their
    destination IPv4 address. The default action is to drop.

    3. All other packets are dropped.

*/

#include <core.p4>
#include <v1model.p4>

const bit<9>  CONTROLLER_PORT = 255;

const bit<16> ETH_ARP = 0x0806;
const bit<16> ETH_IPV4 = 0x0800;

const bit<16> MULTICAST_GROUP = 1;

@controller_header("packet_in")
header PacketIn_t {
    bit<9> ingress_port;
    bit<7> _pad;
}

@controller_header("packet_out")
header PacketOut_t {
    bit<9> egress_port;
    bit<7> _pad;
}

header PartEth_t {
    bit<96> _unused;
    bit<16> eth_type;
}

header PartIPv4_t {
    bit<128> _unused;
    bit<32> ipv4_dst;
}

struct Metadata_t {
    // empty
}

struct Headers_t {
    PartEth_t eth;
    PartIPv4_t ipv4;
    PacketIn_t packet_in;
    PacketOut_t packet_out;
}


/*******************
 * M y P a r s e r *
 *******************/

parser MyParser(
    packet_in packet, 
    out Headers_t hdr, 
    inout Metadata_t meta, 
    inout standard_metadata_t std_meta) {

    state start {
        transition select(std_meta.ingress_port) {
            CONTROLLER_PORT: parse_packet_out;
            default: parse_eth;
        }
    }

    state parse_packet_out {
        packet.extract(hdr.packet_out);
        transition parse_eth;
    }

    state parse_eth {
        packet.extract(hdr.eth);
        transition select(hdr.eth.eth_type) {
            ETH_IPV4: parse_ipv4;
        }
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition accept;
    }
}


/*********************
 * M y I n g r e s s *
 *********************/

control MyIngress(
    inout Headers_t hdr,
    inout Metadata_t meta,
    inout standard_metadata_t std_meta) {

    action drop() {
        mark_to_drop(std_meta);
    }

    action flood() {
        std_meta.mcast_grp = MULTICAST_GROUP;
    }

    action forward(bit<9> port) {
        std_meta.egress_spec = port;
    }

    table ipv4 {
        key = {
            hdr.ipv4.ipv4_dst: exact @finsy_addr;
        }
        actions = {
            forward;
            flood;
            drop;
        }
        size = 1024;
        default_action = drop;
    }

    apply {
        if (std_meta.ingress_port == CONTROLLER_PORT) {
            forward(hdr.packet_out.egress_port);
            hdr.packet_out.setInvalid();
        } else if (hdr.eth.eth_type == ETH_ARP) {
            flood();
        } else if (hdr.ipv4.isValid()) {
            ipv4.apply();
        } else {
            drop();
        }
    }
}


/*******************
 * M y E g r e s s *
 *******************/

control MyEgress(
    inout Headers_t hdr,
    inout Metadata_t meta,
    inout standard_metadata_t std_meta) {

    action drop() {
        mark_to_drop(std_meta);
    }

    action send_to_controller() {
        hdr.packet_in.setValid();
        hdr.packet_in.ingress_port = std_meta.ingress_port;
    }

    apply {
        if (std_meta.egress_port == CONTROLLER_PORT) {
            send_to_controller();
        } else if (std_meta.egress_port == std_meta.ingress_port) {
            drop();
        }
    }
}


/***********************
 * M y D e p a r s e r *
 ***********************/

control MyDeparser(
    packet_out packet, 
    in Headers_t hdr) {

    apply {
        packet.emit(hdr.packet_in);
        packet.emit(hdr.eth);
        packet.emit(hdr.ipv4);
    }
}


/***********
 * m a i n *
 ***********/

control MyVerifyChecksum(inout Headers_t hdr, inout Metadata_t meta) {
    apply {}
}

control MyComputeChecksum(inout Headers_t hdr, inout Metadata_t meta) {
    apply {}
}

@pkginfo(name="hello.p4", version="1")
@brief("Hello, World example for Finsy.")
V1Switch(
    MyParser(), 
    MyVerifyChecksum(), 
    MyIngress(), 
    MyEgress(), 
    MyComputeChecksum(), 
    MyDeparser()
) main;
