#!/bin/bash
#
# This script downloads and compiles the latest P4Runtime/GNMI protobuf files.
# It also compiles type stubs using mypy-protobuf.
#
# To re-compile the local proto files, run "./ci/protoc.sh" (with no arguments).
#
# To download the latest proto files and compile them, run "./ci/protoc.sh update".
#
# Requirements:
#    pip install github-clone
#    pip install grpcio-tools

set -eu

P4RUNTIME_FILES_URL="https://github.com/p4lang/p4runtime/tree/main/proto/p4"
GOOGLE_RPC_FILES_URL="https://github.com/googleapis/api-common-protos/tree/main/google/rpc"
GNMI_URL="https://raw.githubusercontent.com/openconfig/gnmi/master/proto/gnmi/gnmi.proto"
GNMI_EXT_URL="https://raw.githubusercontent.com/openconfig/gnmi/master/proto/gnmi_ext/gnmi_ext.proto"

if ! [ -d "finsy/proto" ]; then
    echo "Wrong working directory."
    exit 1
fi

CURRENT_DIR="$(pwd)"
DEST_DIR="$CURRENT_DIR/finsy/proto"

download_proto_files() {
    # Create a temporary directory and cd into it.
    tmp_dir=$(mktemp -d -t download_proto_files-XXXXXX)
    cd "$tmp_dir"

    # Clone P4Runtime protobuf files.
    ghclone "$P4RUNTIME_FILES_URL"

    # Make a "google" directory and clone RPC protobuf files inside.
    mkdir "google" && pushd "google"
    ghclone "$GOOGLE_RPC_FILES_URL"
    popd

    # Make a "gnmi1" directory and download "gnmi.proto" and "gnmi_ext.proto" inside.
    # We also have to fix up an `import` statement in "gnmi.proto".
    mkdir "gnmi1" && pushd "gnmi1"
    curl "$GNMI_URL" | sed 's+github.com/openconfig/gnmi/proto/gnmi_ext/+gnmi1/+' > "gnmi.proto"
    curl "$GNMI_EXT_URL" > "gnmi_ext.proto"
    popd

    # Move .proto files to their destination.
    find . -type f -name '*.proto' | while read -r f; do mv "$f" "$DEST_DIR/$f"; done

    # Reset current directory.
    cd "$CURRENT_DIR"
}

if [ "${1-}" = "update" ]; then
    download_proto_files
fi

files="finsy/proto"
protoc=".venv/bin/python3 -m grpc_tools.protoc"
protoc_args="-I$files --python_out=$files --mypy_out=$files"
grpc_args="-I$files --grpc_python_out=$files --mypy_grpc_out=$files"

# Produce "*_pb2.py" files.

# shellcheck disable=SC2086
find "$files" -name "*.proto" -print0 | xargs -0 $protoc $protoc_args  

# Produce "*_pb2_grpc.py" files.

# shellcheck disable=SC2086
$protoc $grpc_args "finsy/proto/p4/v1/p4runtime.proto"
# shellcheck disable=SC2086
$protoc $grpc_args "finsy/proto/gnmi1/gnmi.proto"

exit 0
