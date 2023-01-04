#!/usr/bin/env bash

set -eu
set -o pipefail


source "$(dirname ${BASH_SOURCE[0]})/lib/testing.sh"


cid_es="$(container_id elasticsearch)"
cid_ls="$(container_id logstash)"
cid_kb="$(container_id kibana)"

ip_es="$(service_ip elasticsearch)"
ip_ls="$(service_ip logstash)"
ip_kb="$(service_ip kibana)"

es_ca_cert="$(realpath $(dirname ${BASH_SOURCE[0]})/../../../tls/certs/ca/ca.crt)"

log 'Waiting for readiness of Elasticsearch'
poll_ready "$cid_es" 'https://elasticsearch:9200/' --resolve "elasticsearch:9200:${ip_es}" --cacert "$es_ca_cert" -u 'elastic:changeme'

log 'Waiting for readiness of Kibana'
poll_ready "$cid_kb" "http://${ip_kb}:5601/api/status" -u 'kibana_system:changeme'
