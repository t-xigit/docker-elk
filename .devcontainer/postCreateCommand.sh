#!/bin/bash

# Check ansible is installed
cd ..
make pyinit
cd .devcontainer
ansible --version
ansible-playbook playbook.yml