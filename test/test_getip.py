#!/usr/bin/env python3

import pytest
import os
import time
import getip


@pytest.mark.parametrize(('config', 'expected'), [
    ("", "no 'GETIP_CONFIG' in environment variables"),
    ("test/getip-test-cannot-open.conf", "cannot open configuration file"),
    ("test/getip-test-nokey.conf", "'getip' key not found in"),
    ("test/getip-test-cannot-parse.conf", "cannot parse configuration"),
    ("test/getip-test-no-interval.conf", "'interval' not found"),
    ("test/getip-test-interval-not-int.conf", "'interval' is not 'int'"),
    ("test/getip-test-no-urls.conf", "'urls' not found"),
    ("test/getip-test-urls-not-list.conf", "'urls' is not 'list'")
])
def test_getip_init_raise_config(config, expected):
    os.environ['GETIP_CONFIG'] = config
    with pytest.raises(getip.GetIPError) as e:
        getip.GetIP()
    assert str(e.value).startswith(expected)


def test_getip_get(mocker):
    os.environ['GETIP_CONFIG'] = 'test/getip-test.conf'

    responseMock = mocker.Mock()
    responseMock.status_code = 200
    responseMock.text = '127.0.0.1'
    mocker.patch('requests.get').return_value = responseMock

    actual = getip.GetIP().get()
    assert actual == '127.0.0.1'


def test_getip_get_error(mocker):
    os.environ['GETIP_CONFIG'] = 'test/getip-test.conf'

    responseMock = mocker.Mock()
    responseMock.status_code = 404
    responseMock.text = '127.0.0.1'
    mocker.patch('requests.get').return_value = responseMock

    actual = getip.GetIP().get()
    assert actual is None


def test_getip_polling(mocker):
    os.environ['GETIP_CONFIG'] = 'test/getip-test.conf'

    responseMock = mocker.Mock()
    responseMock.status_code = 200
    responseMock.text = '127.0.0.1'
    mocker.patch('requests.get').return_value = responseMock

    gi = getip.GetIP()
    assert gi.thread is None
    assert gi.thread_finish is False

    actual = gi.start_polling()
    assert actual is True
    assert gi.thread is not None
    assert gi.thread_finish is False

    # thread is already running
    actual = gi.start_polling()
    assert actual is False

    # check new IP address immediately after starting thread
    time.sleep(5)
    assert gi.is_new() is False
    assert gi.current_ip == '127.0.0.1'

    # change IP address
    responseMock.text = '192.168.0.1'
    time.sleep(5)
    assert gi.is_new() is True
    assert gi.current_ip == '192.168.0.1'

    # check new IP address again
    time.sleep(5)
    assert gi.is_new() is False
    assert gi.current_ip == '192.168.0.1'

    # change IP address again
    responseMock.text = '127.0.0.1'
    time.sleep(5)
    assert gi.is_new() is True
    assert gi.current_ip == '127.0.0.1'

    # check new IP address again
    time.sleep(5)
    assert gi.is_new() is False
    assert gi.current_ip == '127.0.0.1'

    # server error
    responseMock.status_code = 404
    responseMock.text = '192.168.0.1'
    time.sleep(5)
    assert gi.is_new() is False
    assert gi.current_ip == '127.0.0.1'

    # finish
    gi.finish_polling()
    assert gi.thread is None
    assert gi.thread_finish is True


def test_getip_polling_with_server_error(mocker):
    os.environ['GETIP_CONFIG'] = 'test/getip-test.conf'

    responseMock = mocker.Mock()
    responseMock.status_code = 404
    responseMock.text = '127.0.0.1'
    mocker.patch('requests.get').return_value = responseMock

    gi = getip.GetIP()
    assert gi.thread is None
    assert gi.thread_finish is False

    actual = gi.start_polling()
    assert actual is True
    assert gi.thread is not None
    assert gi.thread_finish is False

    # check new IP address immediately after starting thread
    time.sleep(5)
    assert gi.is_new() is False
    assert gi.current_ip is None

    # finish
    gi.finish_polling()
    assert gi.thread is None
    assert gi.thread_finish is True


if __name__ == '__main__':
    pytest.main(['-v', __file__])
