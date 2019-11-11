#!/usr/bin/env python3

import pytest
import dnsping


@pytest.mark.parametrize("nameserver, hostname, expected", [
    ('8.8.8.8', 'www.example.com', (True, '93.184.216.34')),
    ('8.8.8.8', 'www.example.co.jp', (False, 'Hostname does not exist')),
    ('93.184.216.34', 'www.example.com', (False, 'Request Timeout')),
])
def test_dnsping_is_alive(nameserver, hostname, expected):
    assert expected == dnsping.Server(nameserver=nameserver,
                                      hostname=hostname).is_alive()


if __name__ == '__main__':
    pytest.main(['-v', __file__])
