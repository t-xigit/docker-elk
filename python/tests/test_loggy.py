import pytest
import elk_api


cert_path = './tls/certs/ca/ca.crt'


def test_sanity():
    assert True


@pytest.mark.parametrize("test_input,expected", [(cert_path, True)])
def test_check_certificate(test_input, expected):
    """Tests the check_elasticsearch_status function"""
    assert elk_api.check_certificate(test_input) is expected
