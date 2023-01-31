#!/usr/bin/python3
import os.path
from pathlib import Path
import yaml
import shutil
from typing import Union
from dataclasses import dataclass
import jinja2
import click

default_deployment_folder = Path('loggy_deployment/deployments')


@dataclass
class LoggyStack:
    deployment_name: str
    kibana_server_name: str = ''
    kibana_port: int = 0
    kibana_url: str = 'http://localhost:5601'
    elastic_url: Union[str, None] = None
    # elastic_ca: str


def loggy() -> str:
    mystring = "Hello from loggy!"
    print(mystring)
    return mystring


def _make_sure_path_exists(path: "os.PathLike[str]") -> None:
    """Ensure that a directory exists.
    :param path: A directory tree path for creation.
    """
    print('Making sure path exists (creates tree if not exist): %s', path)
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise OSError(f'Unable to create directory at {path}') from error


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
    stack.kibana_server_name = result['stack']['kibana']['server_name']

    # Load Elasticsearch parameters
    stack.elastic_url = result['stack']['elasticsearch']['host']
    assert stack.elastic_url is not None, "Elasticsearch host must be defined"
    return stack


def _copy_stack_files(output_dir: Path) -> bool:
    """Copy deployment files for Loggy Stack"""
    assert output_dir.exists(), f"Output directory {output_dir} does not exist"
    template_dir = Path('loggy_deployment/config/templates/')
    assert template_dir.exists(), f"Template directory {template_dir} does not exist"
    services = ['agent', 'kibana', 'fleet', 'elasticsearch', 'tls']
    for service in services:
        service_dir = template_dir / service
        dir_to_create = Path(output_dir / service)
        # Create the service directory
        _make_sure_path_exists(dir_to_create)
        # Copy all files in the service directory
        tree = list(os.walk(service_dir))
        files = tree[0][2]
        subdirs = tree[0][1]
        for subdir in subdirs:
            # Create the subdirectory
            _make_sure_path_exists(dir_to_create / subdir)
            # Copy all files in the subdirectory
            files_in_subdir = list(os.walk(service_dir / subdir))[0][2]
            for file in files_in_subdir:
                # Copy the files
                shutil.copy(service_dir / subdir / file, output_dir / service / subdir / file)
                # Apply file permissions to output file
                shutil.copymode(service_dir / subdir / file, output_dir / service / subdir / file)
                assert os.path.isfile(output_dir / service / subdir / file), f"{file} file not copied"

        for file in files:
            # Copy the files
            shutil.copy(service_dir / file, output_dir / service / file)
            # Apply file permissions to output file
            shutil.copymode(service_dir / file, output_dir / service / file)
            assert os.path.isfile(output_dir / service / file), f"{file} file not copied"

    # Copy the docker-compose file
    shutil.copyfile(template_dir / 'docker-compose.yml', output_dir / 'docker-compose.yml')
    # Apply file permissions to output file
    assert os.path.isfile(output_dir / 'docker-compose.yml'), "docker-compose.yml file not copied"
    # Copy the .env file
    shutil.copyfile(template_dir / '.env', output_dir / '.env')
    assert os.path.isfile(output_dir / '.env'), ".env file not copied"
    return True


def _make_stack_files(stack: LoggyStack, output_dir: Path) -> bool:
    """Render deployment files for Loggy Stack"""
    assert os.path.isdir(output_dir), f"Output directory {output_dir} does not exist"
    kibana_env = Path("loggy_deployment/config/templates/")
    assert kibana_env.exists(), f"Kibana environment {kibana_env} does not exist"

    # Jina2 rendering needs to be done in a separate function
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(kibana_env))
    template = environment.get_template('kibana/config/kibana.yml.j2')
    kibana_config = template.render(KibanaServerName=stack.kibana_server_name)

    kibana_config_file = output_dir / 'kibana.yml'
    with open(kibana_config_file, mode='w', encoding="utf-8") as f:
        f.write(kibana_config)
    return True


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
        shutil.rmtree(deploy_folder)
    elif force is False and deploy_folder.exists():
        raise Exception(f"Deployment folder {deploy_folder} already exists")
    # Create the folder
    deploy_folder.mkdir(parents=True)
    assert deploy_folder.exists(), f"Deployment folder {deploy_folder} could not be created"
    assert _copy_stack_files(deploy_folder), "Could not copy config files"
    assert _make_stack_files(stack, deploy_folder), "Could not create config files"
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
