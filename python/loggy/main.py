#!/usr/bin/python3
import os.path
from pathlib import Path
import yaml
import shutil
from typing import Union, Tuple, List
import jinja2
import click
from .utils import make_sure_path_exists,\
                   rmtree,\
                   make_executable,\
                   assert_is_file

# Absolute path to the main repo folder
abs_path = Path(__file__).resolve().parents[2]
# abs_path = Path(__file__).parent.absolute()
default_deployment_folder = Path(abs_path / 'loggy_deployment/deployments')
template_dir = Path(abs_path / 'loggy_deployment/config/templates/')


# Class for the Stack
class LoggyStack:
    def __init__(self, config_yml: Path, output_dir: Path):
        self.config_yml: Path = config_yml
        assert_is_file(self.config_yml)
        self.name: str = ''
        self.output_dir: Path = output_dir
        self.elastic_version: str = ''
        self.kibana_server_name: str = ''
        self.kibana_port: int = 0
        self.kibana_url: str = 'http://localhost:5601'
        self.elastic_url: Union[str, None] = None
        self.elastic_ca: Path | None = None
        self._load_stack()

    def _load_stack(self) -> bool:
        """Loads the stack parameters from a YAML file"""
        config_yml = self.config_yml
        stack = self
        # Load the config file
        result = yaml.safe_load(open(config_yml))
        # Create a LoggyStack object
        stack.name = result['stack']['name']
        # Load Kibana parameters
        stack.kibana_port = result['stack']['kibana']['port']
        assert stack.kibana_port > 0, "Kibana port must be greater than 0"
        stack.kibana_server_name = result['stack']['kibana']['server_name']

        # Load Elasticsearch parameters
        stack.elastic_url = result['stack']['elasticsearch']['host']
        assert stack.elastic_url is not None, "Elasticsearch host must be defined"

        # Load Elasticsearch version
        stack.elastic_version = result['stack']['version']
        return True


def loggy() -> str:
    mystring = "Hello from loggy!"
    print(mystring)
    return mystring


def copy_file(source: Path, destination: Path) -> bool:
    """Copy a file from source to destination"""
    assert os.path.isfile(source), f"Source file {source} does not exist"
    # assert os.path.isdir(destination), f"Destination directory {destination} does not exist"
    shutil.copy(source, destination)
    # Copy the owner, group and permissions
    shutil.copystat(source, destination)
    shutil.copymode(source, destination)
    assert os.path.isfile(destination), f"File {source} not copied"
    return True


def get_tree(path: Path) -> Tuple[List[Path], List[Path]]:
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
    make_sure_path_exists(output_dir)
    make_sure_path_exists(template_dir)
    services = ['agent', 'kibana', 'elasticsearch', 'tls', 'fleet', 'setup']
    for service in services:
        # Creating a list of files and directories to create
        service_dir = template_dir / service
        # Add the service directory to the list of directories to create
        # Copy all files in the service directory
        files, dirs = get_tree(service_dir)
        make_sure_path_exists(output_dir / service)

        for d in dirs:
            dir_to_create = Path(output_dir / d)
            make_sure_path_exists(dir_to_create)
        for file in files:
            # Copy the files
            template_file = template_dir / file
            output_file = output_dir / file
            copy_file(template_file, output_file)
    return True


def _make_stack_files(stack: LoggyStack, output_dir: Path) -> bool:
    """Render deployment files for Loggy Stack"""
    assert os.path.isdir(output_dir), f"Output directory {output_dir} does not exist"
    kibana_env = Path(template_dir)
    assert kibana_env.exists(), f"Kibana environment {kibana_env} does not exist"

    # Jina2 rendering needs to be done in a separate function
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(kibana_env))
    template = environment.get_template('kibana/config/kibana.yml.j2')
    kibana_config = template.render(KibanaServerName=stack.kibana_server_name)

    kibana_config_file = Path(output_dir / 'kibana' / 'config' / 'kibana.yml')
    # Render the .env file
    env_template = environment.get_template('/.env.j2')
    env_config = env_template.render(elastic_version=stack.elastic_version)
    enf_file = Path(output_dir / '.env')
    with open(enf_file, mode='w', encoding="utf-8") as f:
        f.write(env_config)
    with open(kibana_config_file, mode='w', encoding="utf-8") as f:
        f.write(kibana_config)
    # Copy compose file
    compose_file = Path(template_dir / 'docker-compose.yml')
    copy_file(compose_file, output_dir / 'docker-compose.yml')

    executable_files = []
    executable_files.append(Path(template_dir / 'tls/entrypoint.sh'))
    executable_files.append(Path(template_dir / 'setup/entrypoint.sh'))
    executable_files.append(Path(template_dir / 'setup/update_fingerprint.sh'))
    for file in executable_files:
        make_executable(file)
    return True


def _make_stack(config_yml: Path,
                output_dir: Path = default_deployment_folder,
                force: bool = False) -> bool:
    """Creates a stack from a YAML file"""
    # assert os.path.isfile(config_yml), f"Config file {config_yml} does not exist"
    assert_is_file(config_yml)
    make_sure_path_exists(output_dir)
    stack = LoggyStack(config_yml, output_dir)

    # Create the deployment folder
    print(f"Creating stack {stack.name}")
    deploy_folder = Path(output_dir) / stack.name
    # Set the CA path of the stack
    stack.elastic_ca = deploy_folder / 'tls' / 'ca'
    # If force is true delete the folder and create it again
    # If force is false and the folder exists raise an exception
    # If force is false and the folder does not exist create it
    if force is True and deploy_folder.exists():
        rmtree(deploy_folder)
    elif force is False and deploy_folder.exists():
        raise Exception(f"Deployment folder {deploy_folder} already exists")
    # Create the folder
    make_sure_path_exists(deploy_folder)
    _copy_stack_files(deploy_folder)
    _make_stack_files(stack, deploy_folder)
    return True


@click.command()
@click.argument('conf')
@click.option('--out', help='Path to the output folder.')
@click.option('--force', is_flag=True, default=False, help='Overwrite the output folder if it exists.')
def main(conf, out, force):
    """Create a new deployment from a YAML file"""
    click.echo(f"Creating deployment for: {conf}!")
    if out is not None:
        click.echo(f"Output folder: {default_deployment_folder}!")
        _out = Path(out)
        _make_stack(config_yml=conf, output_dir=_out, force=force)
        return None
    else:
        _make_stack(config_yml=conf, force=force)
        return None


if __name__ == '__main__':
    main()
