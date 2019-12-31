#!/usr/bin/env python3

import pytest
import tempbotlib.dnsping as dnsping
import mocks


@pytest.mark.parametrize(('nameserver', 'hostname', 'expected'), [
    ('8.8.8.8', 'www.example.com', (True, '93.184.216.34')),
    ('8.8.8.8', 'www.example.co.jp', (False, 'Hostname does not exist')),
    ('93.184.216.34', 'www.google.com', (False, 'Request Timeout')),
])
def test_dnsping_is_alive(mocker, nameserver, hostname, expected):
    mocker.patch('tempbotlib.dnsping.dns.resolver.Resolver.query',
                 side_effect=mocks.query_mock)
    assert expected == dnsping.Server(nameserver=nameserver,
                                      hostname=hostname).is_alive()


if __name__ == '__main__':
    pytest.main(['-v', __file__])
