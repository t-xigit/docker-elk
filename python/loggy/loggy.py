#!/usr/bin/python3
import os.path
from pathlib import Path
import yaml
from typing import Union
from dataclasses import dataclass
import click

default_deployment_folder = Path('loggy_deployment/deployments')


@dataclass
class LoggyStack:
    deployment_name: str
    kibana_port: int = 0
    kibana_url: str = 'http://localhost:5601'
    elastic_url: Union[str, None] = None
    # elastic_ca: str


def loggy() -> str:
    mystring = "Hello from loggy!"
    print(mystring)
    return mystring


def _load_stack(config_yml: Path) -> LoggyStack:
    """Loads the stack parameters from a YAML file"""
    assert os.path.isfile(config_yml), f"Config file {config_yml} does not exist"
    # Load the config file
    result = yaml.safe_load(open(config_yml))
    # Create a LoggyStack object
    stack = LoggyStack(deployment_name=result['stack']['name'])
    # Load Kibana parameters
    stack.kibana_port = result['stack']['kibana']['port']
    assert stack.kibana_port > 0, "Kibana port must be greater than 0"

    # Load Elasticsearch parameters
    stack.elastic_url = result['stack']['elasticsearch']['host']
    assert stack.elastic_url is not None, "Elasticsearch host must be defined"
    return stack


def _make_stack(config_yml: Path,
                output_dir: Path = default_deployment_folder,
                force: bool = False) -> bool:
    """Creates a stack from a YAML file"""
    assert os.path.isfile(config_yml), f"Config file {config_yml} does not exist"
    assert os.path.isdir(output_dir), f"Output directory {output_dir} does not exist"
    stack = _load_stack(config_yml)

    # Create the deployment folder
    print(f"Creating stack {stack.deployment_name}")
    deploy_folder = Path(output_dir) / stack.deployment_name
    # If force is true delete the folder and create it again
    # If force is false and the folder exists raise an exception
    # If force is false and the folder does not exist create it
    if force is True and deploy_folder.exists():
        deploy_folder.rmdir()
    elif force is False and deploy_folder.exists():
        raise Exception(f"Deployment folder {deploy_folder} already exists")
    # Create the folder
    deploy_folder.mkdir(parents=True)
    return True


@click.command()
@click.argument('conf')
@click.option('--out', help='Path to the output folder.')
@click.option('--force', is_flag=True, default=False, help='Overwrite the output folder if it exists.')
def make(conf, out, force):
    """Create a new deployment from a YAML file"""
    click.echo(f"Creating deployment for: {conf}!")
    if out is not None:
        click.echo(f"Output folder: {default_deployment_folder}!")
        _out = Path(out)
        _make_stack(config_yml=conf, output_dir=_out, force=force)
    else:
        _make_stack(config_yml=conf, force=force)


if __name__ == '__main__':
    make()
