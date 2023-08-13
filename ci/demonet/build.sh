#!/bin/bash
#
# Script to install bmv2, stratum_bmv2, and mininet on an Ubuntu 2022.04 Docker
# Image.
#
# Usage:   ./build.sh
#
# === NOTES ===
#
# 1. I tried to install grpc by letting it use BoringSSL, which is the default.
#    The first hurdle is that the openssl.pc is missing which confuses pkg-config.
#    After adding an openssl.pc file, the linker still reports duplicate symbols.
#    For now, I am continuing to use the openssl package.
#
# 2. I am letting grpc install the protobuf libraries and protoc for us.
#
# 3. When installing bmv2, I had to call ./autogen.sh twice as it errors out 
#    the first time. Also, something is leaving an extra ltmain.sh in the $HOME
#    directory.


set -eu

#################
# G L O B A L S #
#################

WORK_DIR="$HOME"

APT_TOOLS=(autoconf automake build-essential ca-certificates cmake git 
    libtool pkg-config python3 python3-venv)

APT_LIBS=(libgmp-dev libpcap-dev libboost-filesystem-dev
    libboost-program-options-dev libboost-thread-dev libssl-dev)

GRPC_VERSION="1.43.2"
GRPC_CMAKE_FLAGS=(-DgRPC_INSTALL=ON -DgRPC_BUILD_TESTS=OFF -DgRPC_SSL_PROVIDER=package)

GRPC_GIT="https://github.com/grpc/grpc.git"
PI_GIT="https://github.com/p4lang/PI"
BMV2_GIT="https://github.com/p4lang/behavioral-model.git"
MININET_GIT="https://github.com/mininet/mininet.git"

BMV2_BIN=(bin/simple_switch_grpc)
BMV2_LIB=(
    lib/libbm{pi,_grpc_dataplane}.so.0.0.0
    lib/libpi{,grpcserver,feproto,protogrpc,protobuf,p4info,fecpp,convertproto}.so.0.0.0
)

MININET_VERSION="2.3.1b4"
MININET_VENV="/mininet"

export DEBIAN_FRONTEND=noninteractive


######################
#  F U N C T I O N S #
######################

# Install APT preqrequisites.
install_apt_prerequisites() {
    log "Install APT prerequisites."
    apt-get -qq update
    apt-get --yes --no-install-recommends install "${APT_TOOLS[@]}" "${APT_LIBS[@]}"
}

# Build and install C++ version of grpc library ($GRPC_VERSION).
install_grpc() {
    cd "$WORK_DIR"
    if [ -d "grpc" ]; then
        return 0
    fi

    log "Installing grpc."
    git clone --recurse-submodules --branch "v${GRPC_VERSION}" --depth 1 --shallow-submodules "${GRPC_GIT}"
    mkdir "grpc/cmake_build"
    cd "grpc/cmake_build"
    cmake "${GRPC_CMAKE_FLAGS[@]}" ..
    make
    make install
    make clean

    # Check that grpc++ has all its dependencies.
    pkg-config --print-errors "grpc++"

    # Remove extra libz.so files; this forces static linking.
    rm /usr/local/lib/libz.so{,.1,.1.2.11}
}

# Build and install PI library from HEAD.
install_pi() {
    cd "$WORK_DIR"
    if [ -d "PI" ]; then
        return 0
    fi

    log "Installing PI."
    git clone --recurse-submodules --depth 1 --shallow-submodules "${PI_GIT}"
    cd "PI"
    ./autogen.sh
    ./configure --with-proto
    make
    make install
    make clean
}

# Build and install simple_switch_grpc from HEAD.
install_bmv2() {
    cd "$WORK_DIR"
    if [ -d "behavioral-model" ]; then
        return 0
    fi

    log "Installing BMV2."
    git clone --depth 1 "${BMV2_GIT}"
    cd "behavioral-model"
    ./autogen.sh || ./autogen.sh  # Run twice if it fails the first time.
    ./configure --with-pi --without-thrift --without-nanomsg
    make
    make install-strip
    make clean
}

# Copy the bmv2 files to /output/{bin,lib} directories.
copy_bmv2_files() {
    local output="$1"
    mkdir -p "$output/bin" "$output/lib"

    cd /usr/local
    cp "${BMV2_BIN[@]}" "$output/bin"
    cp "${BMV2_LIB[@]}" "$output/lib"
}

# Copy stratum-bmv2 files to /output/stratum/{bin,lib} directories.
copy_stratum_files() {
    local output="$1"
    cd "$WORK_DIR/stratum"
    
    dpkg-deb --extract stratum_bmv2_deb.deb .
    mkdir -p "$output/stratum"
    mv usr/bin "$output/stratum/bin"
    mv usr/lib "$output/stratum/lib"
    mv etc/stratum "$output/stratum/etc"
    mv usr/share/doc "$output/stratum/doc"
    mv libboost_* "$output/stratum/lib"
    cat > "$output/bin/stratum_bmv2" <<'EOF' 
#!/bin/sh
LD_LIBRARY_PATH=/usr/local/stratum/lib exec /usr/local/stratum/bin/stratum_bmv2 "$@"
EOF
    chmod ugo+x "$output/bin/stratum_bmv2"
}

# Install Mininet to /output/mininet.
install_mininet() {
    cd "$WORK_DIR"
    if [ -d mininet ]; then 
        return 0
    fi

    log "Installing Mininet."
    git clone --branch "${MININET_VERSION}" --depth 1 "${MININET_GIT}"
    cd "mininet"

    python3 -m venv "$MININET_VENV"
    VIRTUAL_ENV="$MININET_VENV" "$MININET_VENV/bin/pip" install .
    PREFIX="$MININET_VENV" PYTHON=python3 make install-mnexec

    mkdir "$MININET_VENV/custom"
    cp "$WORK_DIR/p4switch.py" "$MININET_VENV/custom"

    # Remove pip and activate scripts from venv. 
    rm -rf $MININET_VENV/lib/python3.??/site-packages/pip*
    rm -f $MININET_VENV/bin/pip*
    rm -f $MININET_VENV/bin/[Aa]ctivate*
}

# Log a message.
log() {
    echo "#### $1"
}


###########
# M A I N #
###########

log "Welcome."

install_apt_prerequisites

install_grpc
install_pi
install_bmv2
install_mininet

copy_bmv2_files /output
copy_stratum_files /output

log "Done."
exit 0
