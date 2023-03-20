#!/usr/bin/python3
import os.path
import subprocess
from pathlib import Path
import yaml
import shutil
from typing import Tuple, List
import jinja2
import click
from . import elk_api
from .utils import make_sure_path_exists,\
                   rmtree,\
                   make_executable,\
                   assert_is_file

# Absolute path to the main repo folder
abs_path = Path(__file__).resolve().parents[2]
# abs_path = Path(__file__).parent.absolute()
DEFAULT_DEPLOYMENT_FOLDER = Path(abs_path / 'loggy_deployment/deployments')
TEMPLATE_DIR = Path(abs_path / 'loggy_deployment/config/templates/')


# Class for the Stack
class LoggyStack:
    def __init__(self, config_yml: Path, output_dir: Path):
        self.config_yml: Path = config_yml
        assert_is_file(self.config_yml)
        self.name: str
        self.output_dir: Path = output_dir
        self.elastic_version: str
        self.kibana_server_name: str
        self.kibana_port: int = 0
        self.kibana_url: str = 'http://localhost:5601'
        self.elastic_url: str
        self.elastic_ca: Path
        self.ca_fingerprint: str
        self._load_stack()

    def _load_stack(self) -> bool:
        """Loads the stack parameters from a YAML file"""
        # Load the config file
        result = yaml.safe_load(open(self.config_yml))
        # Create a LoggyStack object
        self.name = result['stack']['name']
        # Load Kibana parameters
        self.kibana_port = result['stack']['kibana']['port']
        assert self.kibana_port > 0, "Kibana port must be greater than 0"
        self.kibana_server_name = result['stack']['kibana']['server_name']

        # Load Elasticsearch parameters
        self.elastic_url = 'https://localhost:9200'
        assert self.elastic_url is not None, "Elasticsearch host must be defined"

        # Load Elasticsearch version
        self.elastic_version = result['stack']['version']
        # Load the Elasticsearch CA
        self.elastic_ca = self.output_dir / self.name / 'tls' / 'certs' / 'ca' / 'ca.crt'
        return True

    # ELK Stack test functions
    def ping_elastic(self):
        """Pings Elasticsearch"""
        reply = elk_api.ping_elasticsearch(self.elastic_url, self.elastic_ca)
        assert reply['tagline'] == 'You Know, for Search', "Elasticsearch is not running"

    # Agent management functions
    def _create_agent_policy(self):
        """Returns the agent policy"""
        agent_name = 'CI/CD Agent Policy'
        description = 'Agent Policy for the CI/CD Agent'
        policy = elk_api.create_agent_policy(agent_name, description, self.elastic_url)
        return policy

    def add_agent(self) -> bool:
        """Adds an agent to the stack"""
        # Create the agent compose file
        agent_comp_file = Path(self.output_dir / self.name / 'agent' / 'agent-compose.yml')
        elk_api.add_agent(agent_comp_file)
        return True

    def _update_fingerprint(self):
        ca_fingerprint = elk_api.get_ca_fingerprint(self.elastic_ca)
        print(f"Fingerprint: {ca_fingerprint}")
        self.ca_fingerprint = ca_fingerprint
        # Update the fingerprint in the Kibana config file
        kibana_env = Path(self.output_dir / self.name)
        assert kibana_env.exists(), f"Kibana environment {kibana_env} does not exist"
        kibana_config_file = Path(self.output_dir / self.name / 'kibana' / 'config' / 'kibana.yml')
        environment = jinja2.Environment(loader=jinja2.FileSystemLoader(kibana_env))
        # For this one we use the rendered file
        template = environment.get_template('kibana/config/kibana.yml')
        kibana_config = template.render(CA_TRUSTED_FINGERPRINT=self.ca_fingerprint)

        with open(kibana_config_file, mode='w', encoding="utf-8") as f:
            f.write(kibana_config)
        # Make sure the fingerprint is updated into the kibana.yml file
        # Find string in file
        with open(kibana_config_file, 'r') as f:
            if self.ca_fingerprint not in f.read():
                print(f"Fingerprint not updated in {kibana_config_file}")
                raise Exception("Fingerprint not updated in kibana.yml file")

    def _make_stack_files(self, deploy_folder: Path) -> bool:
        """Render deployment files for Loggy Stack"""
        assert os.path.isdir(deploy_folder), f"Output directory {deploy_folder} does not exist"
        kibana_env = Path(TEMPLATE_DIR)
        assert kibana_env.exists(), f"Kibana environment {kibana_env} does not exist"

        # Jinja2 rendering needs to be done in a separate function
        environment = jinja2.Environment(loader=jinja2.FileSystemLoader(kibana_env))
        template = environment.get_template('kibana/config/kibana.yml.j2')
        kibana_config = template.render(KibanaServerName=self.kibana_server_name,
                                        CA_TRUSTED_FINGERPRINT='{{CA_TRUSTED_FINGERPRINT}}')

        kibana_config_file = Path(deploy_folder / 'kibana' / 'config' / 'kibana.yml')
        # Render the .env file
        env_template = environment.get_template('/.env.j2')
        env_config = env_template.render(elastic_version=self.elastic_version)
        enf_file = Path(deploy_folder / '.env')
        with open(enf_file, mode='w', encoding="utf-8") as f:
            f.write(env_config)
        with open(kibana_config_file, mode='w', encoding="utf-8") as f:
            f.write(kibana_config)
        # Copy compose file
        compose_file = Path(TEMPLATE_DIR / 'docker-compose.yml')
        copy_file(compose_file, deploy_folder / 'docker-compose.yml')

        executable_files = []
        executable_files.append(Path(TEMPLATE_DIR / 'tls/entrypoint.sh'))
        executable_files.append(Path(TEMPLATE_DIR / 'setup/entrypoint.sh'))
        executable_files.append(Path(TEMPLATE_DIR / 'setup/update_fingerprint.sh'))
        for file in executable_files:
            make_executable(file)
        return True

    def _make_certificates(self) -> bool:
        ''' This will be replaced with a call to the certificate module '''
        compose_file = Path(self.output_dir / self.name / 'docker-compose.yml')
        subprocess.run(['docker', 'compose', '-f', compose_file, 'up', 'tls'])
        assert_is_file(self.elastic_ca)
        return True

    def make_stack(self, force: bool = False) -> bool:
        """Creates a stack from a YAML file"""
        make_sure_path_exists(self.output_dir)
        # Create the deployment folder
        print(f"Creating stack {self.name}")
        deploy_folder = Path(self.output_dir) / self.name
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
        self._make_stack_files(deploy_folder)
        self._make_certificates()
        self._update_fingerprint()
        return True


@click.command()
def loggy():
    mystring = "Hello from loggy!"
    click.echo(mystring)


@click.command()
@click.argument('conf')
def add_agent(conf):
    """Add an agent to the stack"""
    click.echo(f"Loading Stack: {conf}!")
    assert_is_file(conf)
    stack = LoggyStack(config_yml=conf, output_dir=DEFAULT_DEPLOYMENT_FOLDER)
    stack.add_agent()
    return True


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
    make_sure_path_exists(TEMPLATE_DIR)
    services = ['agent', 'kibana', 'elasticsearch', 'tls', 'fleet', 'setup']
    for service in services:
        # Creating a list of files and directories to create
        service_dir = TEMPLATE_DIR / service
        # Add the service directory to the list of directories to create
        # Copy all files in the service directory
        files, dirs = get_tree(service_dir)
        make_sure_path_exists(output_dir / service)

        for d in dirs:
            dir_to_create = Path(output_dir / d)
            make_sure_path_exists(dir_to_create)
        for file in files:
            # Copy the files
            template_file = TEMPLATE_DIR / file
            output_file = output_dir / file
            copy_file(template_file, output_file)
    return True


@click.command()
@click.argument('conf')
@click.option('--out', help='Path to the output folder.')
@click.option('--force', is_flag=True, default=False, help='Overwrite the output folder if it exists.')
def make(conf, out, force):
    """Create a new deployment from a YAML file"""
    click.echo(f"Creating deployment for: {conf}!")
    assert_is_file(conf)
    if out is not None:
        _out = Path(out)
        click.echo(f"Output folder: {_out}!")
    else:
        _out = Path(DEFAULT_DEPLOYMENT_FOLDER)
        click.echo(f"Output folder: {_out}!")
    stack = LoggyStack(config_yml=conf, output_dir=_out)
    stack.make_stack(force=force)
    return None


@click.group()
def cli():
    pass


cli.add_command(make)
cli.add_command(loggy)
cli.add_command(add_agent)

if __name__ == '__main__':
    cli()
