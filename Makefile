.DEFAULT_GOAL:=help
SHELL:=/bin/bash
# Python
VENV :=./python/VENV
TMP_PATH := $(CWD)/.tmp
PYTHON := $(VENV)/bin/python
FLAKE8 := $(VENV)/bin/flake8
PYTEST := $(VENV)/bin/pytest
LOGGY := $(PYTHON) -m python.loggy		# Loggy CLI module
LOGGY_DEV_DIR := ./loggy_deployment/deployments/loggy_dev/	# Dir where the dev files are stored
LOGGY_DEV_COMPOSE := -f ./loggy_deployment/deployments/loggy_dev/docker-compose.yml
LOGGY_DEV_CONFIG := ./loggy_deployment/config/conf_template.yml

# Environment variables
# This ist default value when running in docker desktop
TEST_ENV?="docker_desktop"
# Use this value when running on a linux host or an Github Action Runner
# make test TEST_ENV="docker_native"

# Docker Services
LOGGY_SERVICES   := elasticsearch kibana fleet-server
LOGGY_SETUP := setup
LOGGY_CERTS := tls
LOGGY_MONITORING := portainer
LOGGY_ALL_SERVICES := ${LOGGY_SERVICES} ${LOGGY_SETUP} ${LOGGY_CERTS} ${LOGGY_MONITORING}

compose_v2_not_supported = $(shell command docker compose 2> /dev/null)
ifeq (,$(compose_v2_not_supported))
  DOCKER_COMPOSE_COMMAND = docker-compose
else
  DOCKER_COMPOSE_COMMAND = docker compose
endif

# --------------------------

##@ Python
.PHONY: pyinit
pyinit:		## ✅Initialize Python Virtual Environment
		python3 -m venv $(VENV)
		$(PYTHON) -m pip install --upgrade pip
		$(PYTHON) -m pip install -r ./python/requirements.txt

.PHONY: pylint
pylint:		## ✅Run pylint
		$(FLAKE8) ./python --config ./python/.flake8

.PHONY: pytest
pytest:		## ✅Run pytest
		$(PYTEST) ./python --cov

.PHONY: type_check
type_check:		## ✅Run mypy for type checking
		$(PYTHON) -m mypy ./python/loggy

.PHONY: python_ci
python_ci:		## ✅Run all of the above
	echo "Running tests under env: ${TEST_ENV}" 
	@make pyinit
	@make pylint
	@make type_check
	@make pytest

##@ Loggy

.PHONY: loggy
loggy:			## 🧾Show Loggy help
	$(LOGGY) --help

.PHONY: loggy-make
loggy-make:			## Create and start a Dev Loggy Stack
	$(LOGGY) $(LOGGY_DEV_CONFIG) --force
	$(DOCKER_COMPOSE_COMMAND) $(LOGGY_DEV_COMPOSE) up -d portainer
	$(DOCKER_COMPOSE_COMMAND) $(LOGGY_DEV_COMPOSE) up tls
	./loggy_deployment/deployments/loggy_dev/setup/update_fingerprint.sh
	$(DOCKER_COMPOSE_COMMAND) $(LOGGY_DEV_COMPOSE) up -d

.PHONY: loggy-stop
loggy-stop:			## Stop only the Loggy Stack
	$(DOCKER_COMPOSE_COMMAND) ${LOGGY_DEV_COMPOSE} stop ${LOGGY_SERVICES}

.PHONY: loggy-rm
loggy-rm:				## Remove ELK and all its extra components containers.
	$(DOCKER_COMPOSE_COMMAND) $(LOGGY_DEV_COMPOSE)  --profile setup rm -f ${LOGGY_SERVICES}

# Docker shortcuts when ELK is running
.PHONY: loggy-ps
loggy-ps:				## Show all running containers.
	$(DOCKER_COMPOSE_COMMAND) ${LOGGY_DEV_COMPOSE} ps

.PHONY: loggy-down
loggy-down:			## TODO Down ELK and all its extra components.
	$(DOCKER_COMPOSE_COMMAND) ${LOGGY_DEV_COMPOSE} down

loggy-restart:		## Restart ELK and all its extra components.
	$(DOCKER_COMPOSE_COMMAND) ${LOGGY_DEV_COMPOSE} restart ${LOGGY_SERVICES}

.PHONY: loggy-logs
loggy-logs:			## Tail all logs with -n 1000.
	$(DOCKER_COMPOSE_COMMAND) $(LOGGY_DEV_COMPOSE) logs --follow --tail=1000 ${LOGGY_SERVICES}

.PHONY: loggy-images
loggy-images:			## Show all Images of ELK and all its extra components.
	$(DOCKER_COMPOSE_COMMAND) $(COMPOSE_ALL_FILES) images ${ELK_ALL_SERVICES}

.PHONY: loggy-prune
loggy-prune:			## Remove ELK Containers and Delete ELK-related Volume Data (the elastic_elasticsearch-data volume)
	@make loggy_stop && make loggy_rm
	@docker volume prune -f --filter label=com.docker.compose.project=docker-elk
	@make rm-certs
	@rm -rf $(VENV)
	@rm -rf $(TMP_PATH) __pycache__ .pytest_cache
	@find . -name '*.pyc' -delete
	@find . -name '__pycache__' -delete
	git checkout kibana/config/kibana.yml


##@ 🚫TODO

.PHONY: certs
certs:		## ✅Generate Elasticsearch SSL Certs.
	$(DOCKER_COMPOSE_COMMAND) up tls

.PHONY: setup
setup:		## 🚫TODO Generate Elasticsearch SSL Certs and Keystore.
	@make certs
	@make keystore

.PHONY: build
build:		## 🚫TODO Build ELK and all its extra components.
	$(DOCKER_COMPOSE_COMMAND) ${COMPOSE_ALL_FILES} build ${ELK_ALL_SERVICES}


.PHONY: keystore
keystore:		## 🚫TODO Setup Elasticsearch Keystore, by initializing passwords, and add credentials defined in `keystore.sh`.
	$(DOCKER_COMPOSE_COMMAND) -f docker-compose.setup.yml run --rm keystore

##@ Testing
.PHONY: test
test:			## Run all tests.
	echo "Running tests under env: ${TEST_ENV}" 
	.github/workflows/scripts/run-tests-loggy.sh ${TEST_ENV}

help:       	## Show this help.
	@echo "Create and manage a Loggy Stack"
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
