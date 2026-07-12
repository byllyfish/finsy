# Dockerfile that produces an ubuntu-based image with BMV2 and Mininet.

FROM docker.io/opennetworking/mn-stratum:latest@sha256:352323780adf642664895689b7d2350f2e0be24780420c84bb5aa437d7ac9315 AS stratum

FROM ubuntu:26.04@sha256:b7f48194d4d8b763a478a621cdc81c27be222ba2206ca3ca6bc42b49685f3d9e AS builder
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

FROM ubuntu:26.04@sha256:b7f48194d4d8b763a478a621cdc81c27be222ba2206ca3ca6bc42b49685f3d9e
ARG BMV2_DEPS="libpcap0.8 libboost-program-options1.83.0 libjsoncpp25 libprotobuf32t64 libgrpc++1.51t64"
ARG MININET_DEPS="python3 python3-venv net-tools iproute2 iputils-ping socat psmisc procps ethtool iperf tcpdump telnet"
ARG STRATUM_DEPS="libjudydebian1"
ARG CODECOV_DEPS="curl git gpg"
COPY --from=builder /output /usr/local/
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get -qq update \
    && apt-get -y --no-install-recommends install $BMV2_DEPS $MININET_DEPS $STRATUM_DEPS $CODECOV_DEPS \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig \
    && ln -s /usr/local/stratum/etc /etc/stratum

LABEL org.opencontainers.image.description="This image runs Mininet with a P4Runtime switch (bmv2 or stratum_bmv2)."
EXPOSE 50001-50999
ENTRYPOINT ["mn", "--custom", "/usr/local/mininet/custom/p4switch.py", "--switch", "bmv2", "--controller", "none"]
