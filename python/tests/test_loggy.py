import pytest
import os
from pathlib import Path
from click.testing import CliRunner
from loggy import elk_api
from loggy import main as loggy


cert_path = './tls/certs/ca/ca.crt'
# Absolute path to the resources folder
abs_path = Path(os.path.dirname(os.path.realpath(__file__)))
resources_path = abs_path / 'resources'


@pytest.fixture(scope="session")
def cli_runner():
    """Fixture that returns a helper function to run the cli."""
    runner = CliRunner()

    def cli_main(*cli_args, **cli_kwargs):
        """Run cli main with the given args."""
        return runner.invoke(loggy.cli, cli_args, **cli_kwargs)

    return cli_main


@pytest.fixture
def tmp_output_dir(tmp_path):
    tmp_test_dir = tmp_path / "deployments"
    tmp_test_dir.mkdir()
    return tmp_test_dir


@pytest.fixture
def config_yml():
    return Path(resources_path / 'template.yml')


def test_sanity():
    assert True


def test_loggy_sanity(capfd):
    excepted = "Hello from loggy!"
    runner = CliRunner()
    result = runner.invoke(loggy.cli, ['loggy'])
    assert result.exit_code == 0
    assert result.output == f"{excepted}\n"


def test_load_stack(config_yml, tmp_output_dir):
    config_yml = Path(config_yml)
    stack = loggy.LoggyStack(config_yml=config_yml, output_dir=tmp_output_dir)
    assert isinstance(stack, loggy.LoggyStack)
    assert stack.name == 'loggy_test'
    assert stack.kibana_port == 5601
    assert stack.elastic_url == 'https://localhost:9200'


def test_make_stack(config_yml, tmp_output_dir):
    assert os.path.isfile(config_yml)
    stack = loggy.LoggyStack(config_yml=config_yml, output_dir=tmp_output_dir)
    assert stack.make_stack()
    assert os.path.isdir(tmp_output_dir / 'loggy_test')
    # Test that the folder already exists and the exception is raised
    with pytest.raises(Exception):
        stack.make_stack()
    print("Stack created: ", stack.output_dir)
    # Test that the folder already exists and the force flag is True
    # assert stack.make_stack(force=True)


# Certificate functions
def test_make_ca_cert(config_yml, tmp_output_dir):
    stack = loggy.LoggyStack(config_yml=config_yml, output_dir=tmp_output_dir)
    stack.make_stack()
    cert_dir = tmp_output_dir / stack.name / 'tls' / 'certs' / 'ca'
    assert os.path.isfile(cert_dir / 'ca.crt')


# Fingerprint functions
def test_get_fingerprint(config_yml, tmp_output_dir):
    test_crt = resources_path / 'test_fingerprint' / 'ca.crt'
    expected_fingerprint = '9689574282f8d1088947747cd4000c3e55bf091a54cd76c8892567b46bffeb34'
    fp = elk_api.get_ca_fingerprint(test_crt)
    assert fp == expected_fingerprint


def test_update_fingerprint(config_yml, tmp_output_dir):
    stack = loggy.LoggyStack(config_yml=config_yml, output_dir=tmp_output_dir)
    stack.make_stack()
    stack._update_fingerprint()


def test_copy_stack_files(tmp_output_dir):
    assert loggy._copy_stack_files(output_dir=tmp_output_dir)
    print(os.listdir(tmp_output_dir))
    assert os.path.isfile(tmp_output_dir / 'agent' / 'Dockerfile')
    # assert os.path.isfile(tmp_output_dir / 'docker-compose.yml')
    # assert os.path.isfile(tmp_output_dir / '.env')


# def test_cli_make_stack(cli_runner, config_yml, tmp_output_dir):
#     # First call should create the folder
#     conf = str(config_yml)
#     temp = str(tmp_output_dir)
#     result = cli_runner(conf, '--out', temp)
#     assert result.exit_code == 0
#     print('result.output')
#     print(result.output)
#     print(f"Created deployent: {temp}")


# def test_ping_elasticsearch():
#     config_yml = '/workspaces/docker-elk/loggy_deployment/config/conf_template.yml'
#     output_dir = '/workspaces/docker-elk/loggy_deployment/deployments/loggy_dev'
#     output_dir = Path(output_dir)
#     stack = loggy.LoggyStack(config_yml=config_yml, output_dir=output_dir)
#     # Check if the elasticsearch is up
#     # Find string in the output
#     stack.ping_elastic()
