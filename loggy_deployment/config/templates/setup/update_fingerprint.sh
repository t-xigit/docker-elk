#! /bin/bash

# This script is used to update the CA fingerprint in the Kibana configuration file.
# It is required for the fleet server to be able to communicate with the ES instance.
echo ':: Updating CA Fingerprint for Fleet Server::'

echo '::Get CA fingerprint for Fleet output'
declare ca_fingerprint
ca_fingerprint="$(openssl x509 -fingerprint -sha256 -noout -in tls/certs/ca/ca.crt \
    | cut -d '=' -f2 \
    | tr -d ':' \
    | tr '[:upper:]' '[:lower:]'
)"
echo ' Write fingerprint to kibana.yml'
sed -i "s/#\(ca_trusted_fingerprint:\).*/\1 ${ca_fingerprint}/g" kibana/config/kibana.yml
git diff kibana/config/kibana.yml

