#!/bin/bash
#
# Script to make client/server TLS certificates for testing.
# 
# Usage:  ./make_certs.sh <id>

# shellcheck disable=SC2086

set -eu

ID="${1-}"  # ID is optional

PREFIX="/C=US/ST=AZ/L=Phoenix/O=Finsy/OU=Test"
KEY_SIZE=4096
SER_NUM=01

CA_CERT_DAYS=3650
CA_KEY="ca$ID.key"
CA_CRT="ca$ID.crt"

SERVER_CERT_DAYS=3650
SERVER_KEY="server$ID.key"
SERVER_CRT="server$ID.crt"
SERVER_CSR="_server$ID.csr"

CLIENT_CERT_DAYS=3650
CLIENT_KEY="client$ID.key"
CLIENT_CRT="client$ID.crt"
CLIENT_CSR="_client$ID.csr"

echo
echo "*** Generate CA ***"
openssl genrsa -out $CA_KEY $KEY_SIZE
openssl req -new -x509 -days $CA_CERT_DAYS -key $CA_KEY -out $CA_CRT -subj "$PREFIX/CN=root"

echo
echo "*** Generate server certificate and key ***"
openssl genrsa -out $SERVER_KEY $KEY_SIZE
openssl req -new -key $SERVER_KEY -out $SERVER_CSR -subj "$PREFIX/CN=localhost"
openssl x509 -req \
  -extfile <(printf "subjectAltName=DNS:localhost,IP:127.0.0.1") \
  -days $SERVER_CERT_DAYS -in $SERVER_CSR -CA $CA_CRT -CAkey $CA_KEY -set_serial $SER_NUM -out $SERVER_CRT

echo
echo "*** Generate client certificate and key ***"
openssl genrsa -out $CLIENT_KEY $KEY_SIZE
openssl req -new -key $CLIENT_KEY -out $CLIENT_CSR -subj "$PREFIX/CN=client"
openssl x509 -req -days $CLIENT_CERT_DAYS -in $CLIENT_CSR -CA $CA_CRT -CAkey $CA_KEY -set_serial $SER_NUM -out $CLIENT_CRT

# Remove unneeded files.
rm "$CA_KEY" "$SERVER_CSR" "$CLIENT_CSR"

echo
echo "*** Done ***"

exit 0
