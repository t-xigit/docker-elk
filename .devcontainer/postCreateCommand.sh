#!/bin/bash

# Check ansible is installed
make pyinit
ansible --version
ansible-playbook ./.devcontainer/playbook.yml