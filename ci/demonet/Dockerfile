# Dockerfile that produces an ubuntu-based image with BMV2 and Mininet.

FROM docker.io/opennetworking/mn-stratum:latest@sha256:b588956bafc3a4829b36e0c96ff0d580662a00862dde3a1ef73ad1179cba1a62 AS stratum

FROM ubuntu:22.04@sha256:aa772c98400ef833586d1d517d3e8de670f7e712bf581ce6053165081773259d AS builder
WORKDIR /root
COPY build.sh p4switch.py ./
COPY --from=stratum /stratum_bmv2_deb.deb \
  /usr/lib/x86_64-linux-gnu/libboost_filesystem.so.1.67.0 \
  /usr/lib/x86_64-linux-gnu/libboost_thread.so.1.67.0 \
  /usr/lib/x86_64-linux-gnu/libboost_system.so.1.67.0 \
  /usr/lib/x86_64-linux-gnu/libboost_program_options.so.1.67.0 \
  /usr/lib/x86_64-linux-gnu/libboost_atomic.so.1.67.0 \
  ./stratum/
RUN ./build.sh

FROM ubuntu:22.04@sha256:aa772c98400ef833586d1d517d3e8de670f7e712bf581ce6053165081773259d
ARG BMV2_DEPS="libpcap0.8 libboost-filesystem1.74.0 libboost-program-options1.74.0 libboost-thread1.74.0"
ARG MININET_DEPS="python3 net-tools iproute2 iputils-ping socat psmisc procps ethtool iperf tcpdump telnet"
ARG OTHER_DEPS="python3-venv gpg"
ARG STRATUM_DEPS="libjudydebian1"
COPY --from=builder /output /usr/local/
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get -qq update \
    && apt-get -y --no-install-recommends install $BMV2_DEPS $MININET_DEPS $OTHER_DEPS $STRATUM_DEPS \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig \
    && ln -s /usr/local/stratum/etc /etc/stratum

LABEL org.opencontainers.image.description="This image runs Mininet with a P4Runtime switch (bmv2 or stratum_bmv2)."
EXPOSE 50001-50999
ENTRYPOINT ["mn", "--custom", "/usr/local/mininet/custom/p4switch.py", "--switch", "bmv2", "--controller", "none"]
