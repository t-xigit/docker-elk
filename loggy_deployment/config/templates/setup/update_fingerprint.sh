#! /bin/bash

# This script is used to update the CA fingerprint in the Kibana configuration file.
# It is required for the fleet server to be able to communicate with the ES instance.
echo ':: Updating CA Fingerprint for Fleet Server::'

# Get the path to this script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
CA_PATH="${SCRIPT_DIR}/../tls/certs/ca/ca.crt"
KIBANA_YML="${SCRIPT_DIR}/../kibana/config/kibana.yml"

echo '::Get CA fingerprint for Fleet output'
#ca_fingerprint=$(openssl x509 -fingerprint -sha256 -noout -in loggy_deployment/deployments/loggy_dev/tls/certs/ca/ca.crt | cut -d "=" -f2 | tr -d ":" | tr "[:upper:]" "[:lower:]")
#ca_fingerprint="$(openssl x509 -fingerprint -sha256 -noout -in ${CA_PATH}) | cut -d "=" -f2 | tr -d ":" | tr "[:upper:]" "[:lower:]")"
declare ca_fingerprint
ca_fingerprint="$(openssl x509 -fingerprint -sha256 -noout -in ${CA_PATH} \
                | cut -d '=' -f2 \
                | tr -d ':' \
                | tr '[:upper:]' '[:lower:]'
)"

echo "CA fingerprint: ${ca_fingerprint}"
echo ' Write fingerprint to kibana.yml'
sed -i "s/#\(ca_trusted_fingerprint:\).*/\1 ${ca_fingerprint}/g" ${KIBANA_YML}
git diff ${KIBANA_YML}
