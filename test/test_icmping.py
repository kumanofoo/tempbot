#!/usr/bin/env python3

import time
import os
import pytest
import icmping


def test_icmping_save():
    ping1 = icmping.Server(host='www.example.com', sample_count=3, interval=5)
    ping2 = icmping.Server(host='1.1.1.1', sample_count=3, interval=5)
    ping1.start()
    ping2.start()
    time.sleep(20)

    if os.path.isfile('test/test_icmping_save1.png'):
        os.remove('test/test_icmping_save1.png')
    ping1.save(filename='test/test_icmping_save1.png')

    if os.path.isfile('test/test_icmping_save2.png'):
        os.remove('test/test_icmping_save2.png')
    ping2.save(filename='test/test_icmping_save2.png')

    if os.path.isfile('test/test_icmping_save_all.png'):
        os.remove('test/test_icmping_save_all.png')
    icmping.save_results([ping1, ping2],
                         filename='test/test_icmping_save_all.png')

    ping1.finish()
    ping2.finish()

    assert os.path.isfile('test/test_icmping_save1.png') is True
    assert os.path.isfile('test/test_icmping_save2.png') is True
    assert os.path.isfile('test/test_icmping_save_all.png') is True


def test_icmping_exception():
    with pytest.raises(icmping.PingError):
        icmping.Server(host='wwww.example.com')


if __name__ == '__main__':
    pytest.main(['-v', __file__])
