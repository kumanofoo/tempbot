#!/usr/bin/env python3

import pytest
import httping


@pytest.mark.parametrize("url, expected", [
    ('https://httpstat.us/200', (True, 200)),
    ('https://httpstat.us/403', (False, 403)),
    ('https://www.httpstat.us/', (False, 500)),
])
def test_httping_is_alive(url, expected):
    assert expected == httping.Server(url).is_alive()


if __name__ == '__main__':
    pytest.main(['-v', __file__])
