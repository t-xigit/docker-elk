#!/usr/bin/python3
import os.path
from dataclasses import dataclass


@dataclass
class LoggyStack:
    deployment_name: str
    # kibana_url: str
    # elastic_url: str
    # elastic_ca: str


def loggy() -> str:
    mystring = "Hello from loggy!"
    print(mystring)
    return mystring


def load_stack(config_yml: str) -> LoggyStack:
    assert os.path.isfile(config_yml), f"Config file {config_yml} does not exist"
    stack = LoggyStack(deployment_name="loggy_test")
    return stack
