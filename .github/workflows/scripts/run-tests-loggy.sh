#!/usr/bin/env bash

set -eu
set -o pipefail


source "$(dirname ${BASH_SOURCE[0]})/lib/testing.sh"

TEST_ENV=$1
echo "TEST_ENV: $TEST_ENV"

cid_es="$(container_id elasticsearch)"
cid_kb="$(container_id kibana)"
cid_fl="$(container_id fleet-server)"

if [ "$TEST_ENV" = "docker_desktop" ]; then
    echo "Running tests on Docker Desktop"

    ip_es="localhost"
    ip_ls="localhost"
    ip_kb="localhost"
    ip_fl="localhost"

    service_url_es="https://localhost:9200/"
    service_url_fleet="https://localhost"
    
elif [ "$TEST_ENV" = "docker_native" ]; then
    echo "Running tests on native Docker"

    ip_es="$(service_ip elasticsearch)"
    ip_kb="$(service_ip kibana)"
    ip_fl="$(service_ip fleet-server)"

    service_url_es="https://elasticsearch:9200/"
    service_url_fleet="https://fleet-server"
else
    echo "Unknown test environment: $TEST_ENV"
    exit 1
fi

es_ca_cert="$(realpath $(dirname ${BASH_SOURCE[0]})/../../../tls/certs/ca/ca.crt)"

log 'Waiting for readiness of Elasticsearch'
poll_ready "$cid_es" $service_url_es --resolve "elasticsearch:9200:${ip_es}" --cacert "$es_ca_cert" -u 'elastic:changeme'

log 'Waiting for readiness of Kibana'
poll_ready "$cid_kb" "http://${ip_kb}:5601/api/status" -u 'kibana_system:changeme'


log 'Check Container Status for Fleet Server'
docker container inspect $cid_fl
log 'Check Container Status for Fleet Server'
docker container inspect $cid_fl --format '{{ .State.Status}}'

log 'Waiting for readiness of Fleet Server'
poll_ready "$cid_fl" "https://localhost:8220/api/status" --cacert "$es_ca_cert"
# poll_ready "$cid_fl" 'https://fleet-server:8220/api/status' --resolve "fleet-server:8220:${ip_fl}" --cacert "$es_ca_cert"
# poll_ready "$cid_fl" "${service_url_fleet}:8220/api/status" --resolve "fleet-server:8220:${ip_fl}" --cacert "$es_ca_cert"
