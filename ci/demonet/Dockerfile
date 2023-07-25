# Dockerfile that produces an ubuntu-based image with BMV2 and Mininet.

FROM ubuntu:22.04 AS builder
WORKDIR /root
COPY build.sh p4switch.py ./
RUN ./build.sh

FROM ubuntu:22.04
ARG BMV2_DEPS="libpcap0.8 libboost-filesystem1.74.0 libboost-program-options1.74.0 libboost-thread1.74.0"
ARG MININET_DEPS="python3 net-tools iproute2 iputils-ping socat psmisc procps ethtool iperf tcpdump telnet"
ARG OTHER_DEPS="python3-venv"
COPY --from=builder /output /usr/local/
COPY --from=builder /mininet /mininet
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get -qq update \
    && apt-get -y --no-install-recommends install $BMV2_DEPS $MININET_DEPS $OTHER_DEPS \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig

LABEL org.opencontainers.image.description="This image runs Mininet with a BMV2 switch."
ENV PATH=/mininet/bin:$PATH
EXPOSE 50001-50999
ENTRYPOINT ["mn", "--custom", "/mininet/custom/p4switch.py", "--switch", "bmv2", "--controller", "none"]
