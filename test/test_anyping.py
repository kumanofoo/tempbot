#!/usr/bin/env python3

import time
import os
import pytest
import anyping


def test_anyping_init_raise_no_config():
    os.environ['ANYPING_CONFIG'] = ''
    with pytest.raises(anyping.AnypingError):
        anyping.Servers()


def test_anyping_init_raise_config_syntax_error():
    os.environ['ANYPING_CONFIG'] = 'test/anyping-test-config-error.conf'
    with pytest.raises(anyping.AnypingError):
        anyping.Servers()


def test_anyping_get_status_of_servers():
    os.environ['ANYPING_CONFIG'] = 'test/anyping-test.conf'
    responses = ['8.8.8.8 (DNS) is up',
                 '1.1.1.1 (DNS) is down: Hostname does not exist',
                 'https://httpstat.us/200 (Web) is up',
                 'https://httpstat.us/403 (Web) is down: 403',
                 'http://www.example.co.jp/ (Web) is down: 500']

    messages = anyping.Servers().get_status_of_servers().split('\n')
    for response in responses:
        assert response in messages


def test_anyping_ping():
    os.environ['ANYPING_CONFIG'] = 'test/anyping-test.conf'
    test_servers = {'8.8.8.8': 0,
                    '1.1.1.1': 0,
                    'https://httpstat.us/200': 0,
                    'https://httpstat.us/403': 1,
                    'http://www.example.co.jp/': 0}
    responses = ['8.8.8.8 is up',
                 'https://httpstat.us/200 is up',
                 'https://httpstat.us/403 (Web) is down: 403']

    ap = anyping.Servers()
    for server in ap.servers:
        ap.servers[server]['alive'] = test_servers[server]

    messages = ap.ping().split('\n')[:-1]
    ap = None

    for message in messages:
        assert message in responses


def test_anyping_icmp_raise():
    os.environ['ANYPING_CONFIG'] = 'test/anyping-test-icmp-error.conf'
    with pytest.raises(anyping.AnypingError):
        anyping.Servers()


def test_anyping_save_icmp_results():
    os.environ['ANYPING_CONFIG'] = 'test/anyping-test.conf'
    responses = {'all': 'test/test_icmp_all.png',
                 'www.example.com': 'test/test_icmp_0.png',
                 'www.iana.org': 'test/test_icmp_1.png'}

    ap = anyping.Servers()
    time.sleep(30)
    files = ap.save_icmp_results()
    ap = None

    for file in files:
        assert file[0] == responses[file[1]]


def test_anyping_save_icmp_fail():
    os.environ['ANYPING_CONFIG'] = 'test/anyping-test.conf'

    ap = anyping.Servers()
    time.sleep(5)
    files = ap.save_icmp_results()
    ap = None

    assert len(files) == 0


if __name__ == '__main__':
    pytest.main(['-v', __file__])
