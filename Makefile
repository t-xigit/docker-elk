.DEFAULT_GOAL:=help
SHELL:=/bin/bash
# Python
VENV :=./python/VENV
PYTHON := $(VENV)/bin/python
FLAKE8 := $(VENV)/bin/flake8
PYTEST := $(VENV)/bin/pytest
# Docker
COMPOSE_ALL_FILES := \
		-f ./docker-compose.yml\
		-f ./extensions/heartbeat/heartbeat-compose.yml\
		-f ./extensions/fleet/fleet-compose.yml\
		-f ./extensions/fleet/agent-apmserver-compose.yml\
		-f ./extensions/enterprise-search/enterprise-search-compose.yml\
		-f ./extensions/logspout/logspout-compose.yml\
		-f ./extensions/curator/curator-compose.yml\
		-f ./extensions/filebeat/filebeat-compose.yml\
		-f ./extensions/metricbeat/metricbeat-compose.yml

# Environment variables
# This ist default value when running in docker desktop
TEST_ENV?="docker_desktop"
# Use this value when running on a linux host or an Github Action Runner
# make test TEST_ENV="docker_native"

COMPOSE_FLEET := -f ./docker-compose.yml -f ./extensions/fleet/fleet-compose.yml
ELK_SERVICES   := elasticsearch logstash kibana apm-server fleet-server
ELK_LOG_COLLECTION := filebeat
ELK_MONITORING := elasticsearch-exporter logstash-exporter filebeat-cluster-logs
ELK_TOOLS  := rubban
ELK_SETUP := setup
ELK_CERTS := tls
ELK_NODES := elasticsearch-1 elasticsearch-2
ELK_MAIN_SERVICES := ${ELK_SERVICES} ${ELK_CERTS}
# TODO ELK_MAIN_SERVICES := ${ELK_SERVICES} ${ELK_MONITORING} ${ELK_TOOLS}
# TODO ELK_ALL_SERVICES := ${ELK_MAIN_SERVICES} ${ELK_NODES} ${ELK_LOG_COLLECTION}
ELK_ALL_SERVICES := ${ELK_MAIN_SERVICES} ${ELK_SETUP}
LOGGY_SERVICES := setup elasticsearch kibana fleet-server

compose_v2_not_supported = $(shell command docker compose 2> /dev/null)
ifeq (,$(compose_v2_not_supported))
  DOCKER_COMPOSE_COMMAND = docker-compose
else
  DOCKER_COMPOSE_COMMAND = docker compose
endif

# --------------------------
.PHONY: setup keystore certs all elk monitoring tools build down stop restart rm logs loggy ps

.PHONY: pyinit
pyinit:		## Initialize Python Virtual Environment
		python3 -m venv $(VENV)
		$(PYTHON) -m pip install --upgrade pip
		$(PYTHON) -m pip install -r ./python/requirements.txt

.PHONY: pylint
pylint:		## Run pylint
		$(FLAKE8) ./python --config ./python/.flake8

.PHONY: pytest
pytest:		## Run pylint
		$(PYTEST) ./python

keystore:		## TODO Setup Elasticsearch Keystore, by initializing passwords, and add credentials defined in `keystore.sh`.
	$(DOCKER_COMPOSE_COMMAND) -f docker-compose.setup.yml run --rm keystore

certs:		## Generate Elasticsearch SSL Certs.
	$(DOCKER_COMPOSE_COMMAND) up tls

rm-certs:		## Remove Elasticsearch SSL Certs.
	@sudo find tls/certs/ -mindepth 1 -not -name ".*" -delete

setup:		## TODO Generate Elasticsearch SSL Certs and Keystore.
	@make certs
	@make keystore

all:		## TODO Start Elk and all its component (ELK, Monitoring, and Tools).

# $(DOCKER_COMPOSE_COMMAND) ${COMPOSE_ALL_FILES} up -d --build ${ELK_MAIN_SERVICES}

elk:		    ## TODO Start ELK.
	$(DOCKER_COMPOSE_COMMAND) up -d --build

up:
	@make elk
	@echo "Visit Kibana: https://localhost:5601"

monitoring:		## TODO Start ELK Monitoring.
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_MONITORING} up -d --build ${ELK_MONITORING}

collect-docker-logs:		## TODO Start Filebeat that collects all Host Docker Logs and ship it to ELK
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_LOGGING} up -d --build ${ELK_LOG_COLLECTION}

tools:		## TODO Start ELK Tools (ElastAlert, Curator).
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_TOOLS} up -d --build ${ELK_TOOLS}

nodes:		## TODO Start Two Extra Elasticsearch Nodes
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_NODES} up -d --build ${ELK_NODES}

build:			## TODO Build ELK and all its extra components.
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_ALL_FILES} build ${ELK_ALL_SERVICES}

loggy:			## Start Loggy Service
	@make certs
	@./setup/update_fingerprint.sh
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_FLEET} up -d

# Docker shortcuts when ELK is running
ps:				## Show all running containers.
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_ALL_FILES} ps

down:			## TODO Down ELK and all its extra components.
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_ALL_FILES} down

stop:			## **WIP** Stop ELK and all its extra components.
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_ALL_FILES} stop ${ELK_ALL_SERVICES}
	
restart:		## Restart ELK and all its extra components.
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_ALL_FILES} restart ${ELK_ALL_SERVICES}

rm:				## Remove ELK and all its extra components containers.
	$(DOCKER_COMPOSE_COMMAND) $(COMPOSE_ALL_FILES)  --profile setup rm -f ${ELK_ALL_SERVICES}

logs:			## Tail all logs with -n 1000.
	$(DOCKER_COMPOSE_COMMAND) $(COMPOSE_ALL_FILES) logs --follow --tail=1000 ${ELK_ALL_SERVICES}

images:			## Show all Images of ELK and all its extra components.
	$(DOCKER_COMPOSE_COMMAND) $(COMPOSE_ALL_FILES) images ${ELK_ALL_SERVICES}

prune:			## Remove ELK Containers and Delete ELK-related Volume Data (the elastic_elasticsearch-data volume)
	@make stop && make rm
	@docker volume prune -f --filter label=com.docker.compose.project=docker-elk
	@make rm-certs
	git checkout kibana/config/kibana.yml

# Testing

test:			## Run all tests.
	echo "Running tests under env: ${TEST_ENV}" 
	.github/workflows/scripts/run-tests-loggy.sh ${TEST_ENV}

help:       	## Show this help.
	@echo "Make Application Docker Images and Containers using Docker-Compose files in 'docker' Dir."
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m (default: help)\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
