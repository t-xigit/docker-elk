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


def make_file_executable(file: Path) -> bool:
    """Make a file executable"""
    assert os.path.isfile(file), f"File {file} does not exist"
    os.chmod(file, 0o755)
    return True


def copy_file(source: Path, destination: Path) -> bool:
    """Copy a file from source to destination"""
    assert os.path.isfile(source), f"Source file {source} does not exist"
    # assert os.path.isdir(destination), f"Destination directory {destination} does not exist"
    shutil.copy(source, destination)
    shutil.copymode(source, destination)
    assert os.path.isfile(destination), f"File {source} not copied"
    return True


def get_tree(path: Path) -> Union[list, list]:
    """Returns a list of relative files and directories in a given path"""
    rfiles = []
    rdirs = []
    # base = Path(os.path.basename(os.path.normpath(path)))
    base = Path(path)
    root_dir = Path(os.path.basename(os.path.normpath(base)))
    for root, dirs, files in os.walk(path):
        # relative_path = Path(os.path.basename(os.path.normpath(root)))
        relative_path = Path(root)
        relative_path = root_dir / relative_path.relative_to(base)
        for d in dirs:
            _d = Path(relative_path / d)
            rdirs.append(_d)
        for f in files:
            _f = Path(relative_path / f)
            rfiles.append(_f)
    return rfiles, rdirs


def _copy_stack_files(output_dir: Path) -> bool:
    """Copy deployment files for Loggy Stack"""
    assert output_dir.exists(), f"Output directory {output_dir} does not exist"
    template_dir = Path('loggy_deployment/config/templates/')
    assert template_dir.exists(), f"Template directory {template_dir} does not exist"
    services = ['agent', 'kibana', 'elasticsearch', 'tls', 'fleet']
    for service in services:
        # Creating a list of files and directories to create
        service_dir = template_dir / service
        # Add the service directory to the list of directories to create
        # Copy all files in the service directory
        files, dirs = get_tree(service_dir)
        _make_sure_path_exists(output_dir / service)

        for d in dirs:
            dir_to_create = Path(output_dir / d)
            _make_sure_path_exists(dir_to_create)
        for file in files:
            # Copy the files
            template_file = template_dir / file
            output_file = output_dir / file
            copy_file(template_file, output_file)
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
    # Copy compose file
    compose_file = Path("loggy_deployment/config/templates/docker-compose.yml")
    copy_file(compose_file, output_dir / 'docker-compose.yml')
    env_file = Path("loggy_deployment/config/templates/.env")
    copy_file(env_file, output_dir / '.env')

    executable_files = []
    executable_files.append(Path("loggy_deployment/config/templates/tls/entrypoint.sh"))
    for file in executable_files:
        make_file_executable(file)
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
