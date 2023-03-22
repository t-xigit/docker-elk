.DEFAULT_GOAL:=help
SHELL:=/bin/bash
# Python
VENV :=./python/VENV
PYTHON := $(VENV)/bin/python
FLAKE8 := $(VENV)/bin/flake8
PYTEST := $(VENV)/bin/pytest
LOGGY := $(PYTHON) -m python.loggy		# Loggy CLI module
LOGGY_DEV_DIR := ./loggy_deployment/deployments/	# Dir where the dev files are stored
LOGGY_DEV_COMPOSE := -f ./loggy_deployment/deployments/loggy_dev/docker-compose.yml
LOGGY_DEV_ENV_FILE := ./loggy_deployment/deployments/loggy_dev/.env
LOGGY_DEV_AGENT_COMPOSE := -f ./loggy_deployment/deployments/loggy_dev/agent/agent-compose.yml
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

help:       	## Show this help.
	@echo "Create and manage a Loggy Stack"
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Python
.PHONY: pyinit
pyinit:		## ✅Initialize Python Virtual Environment
		python3 -m venv $(VENV)
		$(PYTHON) -m pip install --upgrade pip
		$(PYTHON) -m pip install -r ./python/requirements.txt

.PHONY: pyclean
pyclean:		## ✅Clean Python VENV and Build Files
		@echo "Removing Python Virtual Environment"
		@rm -rf $(VENV)
		@echo "Removing Python Build Files"
		@find . -name '*.pyc' -delete
		@find . -name '__pycache__' -delete

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
	$(LOGGY) make $(LOGGY_DEV_CONFIG) --out $(LOGGY_DEV_DIR) --force
	$(DOCKER_COMPOSE_COMMAND) $(LOGGY_DEV_COMPOSE) up -d portainer
	$(DOCKER_COMPOSE_COMMAND) $(LOGGY_DEV_COMPOSE) up -d

.PHONY: loggy-add_agent
loggy-add_agent:			## Add an agent to the Loggy Stack for testing
	$(LOGGY) add-agent $(LOGGY_DEV_CONFIG)
	$(DOCKER_COMPOSE_COMMAND) --env-file $(LOGGY_DEV_ENV_FILE) $(LOGGY_DEV_AGENT_COMPOSE) up -d

.PHONY: loggy-stop
loggy-stop:			## Stop only the Loggy Stack
	$(DOCKER_COMPOSE_COMMAND) ${LOGGY_DEV_COMPOSE} stop ${LOGGY_SERVICES}

.PHONY: loggy-start
loggy-start:			## TODO Down ELK and all its extra components.
	$(DOCKER_COMPOSE_COMMAND) ${LOGGY_DEV_COMPOSE} start ${LOGGY_SERVICES}

.PHONY: loggy-rm
loggy-rm:				## Remove ELK and all its extra components containers.
	$(DOCKER_COMPOSE_COMMAND) $(LOGGY_DEV_COMPOSE)  --profile setup rm -f ${LOGGY_SERVICES}

# Docker shortcuts when ELK is running
.PHONY: loggy-ps
loggy-ps:				## Show all running containers.
	$(DOCKER_COMPOSE_COMMAND) ${LOGGY_DEV_COMPOSE} ps

.PHONY: loggy-down
loggy-down:			## TODO Down ELK and all its extra components.
	$(DOCKER_COMPOSE_COMMAND) ${LOGGY_DEV_COMPOSE} down -v

loggy-restart:		## Restart ELK and all its extra components.
	$(DOCKER_COMPOSE_COMMAND) ${LOGGY_DEV_COMPOSE} restart ${LOGGY_SERVICES}

.PHONY: loggy-logs
loggy-logs:			## Tail all logs with -n 1000.
	$(DOCKER_COMPOSE_COMMAND) $(LOGGY_DEV_COMPOSE) logs --follow --tail=1000 ${LOGGY_SERVICES}

.PHONY: loggy-images
loggy-images:			## Show all Images of ELK and all its extra components.
	$(DOCKER_COMPOSE_COMMAND) $(LOGGY_DEV_COMPOSE) images ${LOGGY_ALL_SERVICES}

.PHONY: loggy-prune
loggy-prune:			## Remove everything from the Loggy Stack
	@make pyclean
	$(DOCKER_COMPOSE_COMMAND) $(LOGGY_DEV_COMPOSE) --profile setup --profile development down -v

.PHONY: loggy-test
loggy-test:			## Run all tests.
	echo "Running tests under env: ${TEST_ENV}" 
	.github/workflows/scripts/run-tests-loggy-dev.sh ${TEST_ENV}
