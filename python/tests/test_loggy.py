import pytest
import os
import loggy.loggy as loggy


cert_path = './tls/certs/ca/ca.crt'


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
    assert os.path.isdir('./python/tests/resources')
    stack = loggy.load_stack(config_yml=config_yml)
    assert isinstance(stack, loggy.LoggyStack)
    assert stack.deployment_name == 'loggy_test'
    # Test that the function is raising an exception when the file does not exist
