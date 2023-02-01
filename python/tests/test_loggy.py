import pytest
import os
from click.testing import CliRunner
import loggy.loggy as loggy


cert_path = './tls/certs/ca/ca.crt'


@pytest.fixture
def tmp_output_dir(tmp_path):
    tmp_test_dir = tmp_path / "deployments"
    tmp_test_dir.mkdir()
    return tmp_test_dir


@pytest.fixture
def config_yml():
    return './python/tests/resources/template.yml'


def test_sanity():
    assert True


def test_loggy_sanity(capfd):
    excepted = "Hello from loggy!"
    assert loggy.loggy() == excepted
    out, err = capfd.readouterr()
    assert out == f"{excepted}\n"


def test_load_stack(config_yml):
    stack = loggy._load_stack(config_yml=config_yml)
    assert isinstance(stack, loggy.LoggyStack)
    assert stack.deployment_name == 'loggy_test'
    assert stack.kibana_port == 5601
    assert stack.elastic_url == 'localhost'


def test_copy_stack_files(tmp_output_dir):
    assert loggy._copy_stack_files(output_dir=tmp_output_dir)
    print(os.listdir(tmp_output_dir))
    assert os.path.isfile(tmp_output_dir / 'agent' / 'Dockerfile')
    # assert os.path.isfile(tmp_output_dir / 'docker-compose.yml')
    # assert os.path.isfile(tmp_output_dir / '.env')


def test_make_stack(config_yml, tmp_output_dir):
    assert os.path.isfile(config_yml)
    assert loggy._make_stack(config_yml=config_yml, output_dir=tmp_output_dir)
    assert os.path.isdir(tmp_output_dir / 'loggy_test')
    # Test that the folder already exists and the exception is raised
    with pytest.raises(Exception):
        loggy._make_stack(config_yml=config_yml, output_dir=tmp_output_dir)
    # Test that the folder already exists and the force flag is True
    assert loggy._make_stack(config_yml=config_yml, output_dir=tmp_output_dir, force=True)


def test_cli_make_stack(config_yml, tmp_output_dir):
    runner = CliRunner()
    # First call should create the folder
    result = runner.invoke(loggy.make, [config_yml, '--out', tmp_output_dir])
    assert result.exit_code == 0
    assert os.path.isdir(tmp_output_dir / 'loggy_test')
    # Second call should raise an exception
    result = runner.invoke(loggy.make, [config_yml, '--out', tmp_output_dir])
    assert result.exit_code == 1
    # Third call should delete the folder and create it again
    result = runner.invoke(loggy.make, [config_yml, '--out', tmp_output_dir, '--force'])
    assert result.exit_code == 0
    print(result.output)
