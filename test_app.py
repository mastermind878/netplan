import logging
import pytest
from fastapi.testclient import TestClient
from app_final import create_app


@pytest.fixture
def client(monkeypatch):
    for key in ('APP_NAME', 'LOG_LEVEL', 'MAX_SUBNETS'):
        monkeypatch.delenv(key, raising=False)
    with TestClient(create_app()) as c:
        yield c


def test_health(client):
    assert client.get('/health').json() == {'status': 'ok', 'service': 'NetPlan'}


def test_version(client):
    assert client.get('/version').json() == {'version': '1.0.0'}


def test_docs_and_schema(client):
    assert client.get('/docs').status_code == 200
    assert len(client.get('/openapi.json').json()['paths']) == 7


def test_network_normalization(client):
    r = client.get('/networks/info', params={'cidr': '192.168.1.42/24'})
    assert r.status_code == 200
    assert r.json() == {'network': '192.168.1.0/24', 'netmask': '255.255.255.0',
                        'broadcast': '192.168.1.255', 'total_addresses': 256,
                        'usable_hosts': 254, 'first_host': '192.168.1.1', 'last_host': '192.168.1.254'}


@pytest.mark.parametrize('cidr,count,first,last', [
    ('10.0.0.0/31', 2, '10.0.0.0', '10.0.0.1'),
    ('10.0.0.7/32', 1, '10.0.0.7', '10.0.0.7'),
    ('0.0.0.0/0', 4294967294, '0.0.0.1', '255.255.255.254')])
def test_boundary_networks(client, cidr, count, first, last):
    data = client.get('/networks/info', params={'cidr': cidr}).json()
    assert (data['usable_hosts'], data['first_host'], data['last_host']) == (count, first, last)


@pytest.mark.parametrize('cidr', ['garbage', '192.168.1.1', '10.0.0.0/33', '2001:db8::/64', '999.1.1.1/24'])
def test_invalid_network(client, cidr):
    assert client.get('/networks/info', params={'cidr': cidr}).status_code == 422


@pytest.mark.parametrize('ip,belongs,usable', [
    ('192.168.1.42', True, True), ('192.168.1.0', True, False),
    ('192.168.1.255', True, False), ('192.168.2.1', False, False)])
def test_membership(client, ip, belongs, usable):
    data = client.get('/networks/contains', params={'cidr': '192.168.1.0/24', 'ip': ip}).json()
    assert data['belongs'] is belongs
    assert data['usable_as_host'] is usable


@pytest.mark.parametrize('cidr,ip', [('10.0.0.0/31','10.0.0.0'), ('10.0.0.7/32','10.0.0.7')])
def test_small_network_host(client, cidr, ip):
    assert client.get('/networks/contains', params={'cidr':cidr, 'ip':ip}).json()['usable_as_host']


def test_invalid_ip(client):
    assert client.get('/networks/contains', params={'cidr':'10.0.0.0/24', 'ip':'oops'}).status_code == 422


def test_split(client):
    r = client.get('/networks/split', params={'cidr':'192.168.1.0/24','new_prefix':26})
    assert r.status_code == 200
    assert r.json()['count'] == 4
    assert [n['network'] for n in r.json()['subnets']] == [
        '192.168.1.0/26','192.168.1.64/26','192.168.1.128/26','192.168.1.192/26']
    assert all(n['usable_hosts'] == 62 for n in r.json()['subnets'])


@pytest.mark.parametrize('prefix', [23, 24, 33, -1, 'abc'])
def test_invalid_split(client, prefix):
    assert client.get('/networks/split', params={'cidr':'10.0.0.0/24','new_prefix':prefix}).status_code == 422


def test_large_split_rejected(client):
    assert client.get('/networks/split', params={'cidr':'0.0.0.0/0','new_prefix':32}).status_code == 422


@pytest.mark.parametrize('right,overlaps,child', [('10.0.0.0/25', True, True), ('10.0.1.0/24', False, False), ('10.0.0.0/24', True, True)])
def test_compare(client, right, overlaps, child):
    data = client.get('/networks/compare', params={'left':'10.0.0.0/24','right':right}).json()
    assert data['overlaps'] is overlaps
    assert data['right_subnet_of_left'] is child


def test_required_parameter(client):
    assert client.get('/networks/info').status_code == 422


def test_environment(monkeypatch):
    monkeypatch.setenv('APP_NAME','DemoLab')
    monkeypatch.setenv('MAX_SUBNETS','2')
    with TestClient(create_app()) as c:
        assert c.get('/health').json()['service'] == 'DemoLab'
        assert c.get('/networks/split',params={'cidr':'10.0.0.0/24','new_prefix':25}).status_code == 200
        assert c.get('/networks/split',params={'cidr':'10.0.0.0/24','new_prefix':26}).status_code == 422


@pytest.mark.parametrize('key,value', [('MAX_SUBNETS','0'), ('MAX_SUBNETS','4097'), ('MAX_SUBNETS','abc'), ('LOG_LEVEL','BAD')])
def test_invalid_environment(monkeypatch, key, value):
    monkeypatch.setenv(key,value)
    with pytest.raises(ValueError, match=key):
        create_app()


def test_lifecycle_and_request_logs(caplog):
    with caplog.at_level(logging.INFO, logger='netplan'):
        with TestClient(create_app()) as c:
            c.get('/networks/info',params={'cidr':'10.123.45.0/24'})
    assert 'service_started' in caplog.text
    assert 'path=/networks/info status=200' in caplog.text
    assert 'service_stopped' in caplog.text
    assert '10.123.45.0' not in '\n'.join(r.message for r in caplog.records if r.name == 'netplan')
