#!/bin/bash
#
# Script to make client/server TLS certificates.
# 
# Usage:  ./make_certs.sh <id>

set -eu

ID="${1-}"

PASSWORD=password
PREFIX="/C=US/ST=AZ/L=Phoenix/O=Test/OU=Test"
KEY_SIZE=4096
CERT_DAYS=3650

CA_KEY="ca$ID.key"
CA_CRT="ca$ID.crt"

SERVER_KEY="server$ID.key"
SERVER_CRT="server$ID.crt"
SERVER_CSR="_server.csr"

CLIENT_KEY="client$ID.key"
CLIENT_CRT="client$ID.crt"
CLIENT_CSR="_client.csr"

# Generate CA
openssl genrsa -passout pass:$PASSWORD -des3 -out $CA_KEY $KEY_SIZE
openssl req -passin pass:$PASSWORD -new -x509 -days $CERT_DAYS -key $CA_KEY -out $CA_CRT \
  -subj "$PREFIX/CN=root"

# Generate server certificate and key
openssl genrsa -passout pass:$PASSWORD -des3 -out $SERVER_KEY $KEY_SIZE
openssl req -passin pass:$PASSWORD -new -key $SERVER_KEY -out $SERVER_CSR \
  -subj "$PREFIX/CN=localhost"
openssl x509 -req -passin pass:$PASSWORD \
  -extfile <(printf "subjectAltName=DNS:localhost,IP:127.0.0.1") \
  -days $CERT_DAYS -in $SERVER_CSR -CA $CA_CRT -CAkey $CA_KEY -set_serial 01 -out $SERVER_CRT

# Generate client certificate and key
openssl genrsa -passout pass:$PASSWORD -des3 -out $CLIENT_KEY $KEY_SIZE
openssl req -passin pass:$PASSWORD -new -key $CLIENT_KEY -out $CLIENT_CSR -subj "$PREFIX/CN=client"
openssl x509 -passin pass:$PASSWORD -req -days $CERT_DAYS -in $CLIENT_CSR -CA $CA_CRT -CAkey $CA_KEY -set_serial 01 -out $CLIENT_CRT

# Remove passphrase from both keys.
openssl rsa -passin pass:$PASSWORD -in $SERVER_KEY -out $SERVER_KEY
openssl rsa -passin pass:$PASSWORD -in $CLIENT_KEY -out $CLIENT_KEY

# Remove unneeded files.
rm "$CA_KEY" "$SERVER_CSR" "$CLIENT_CSR"

echo "Done."
