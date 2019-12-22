#!/usr/bin/env python3

import time
import os
import pytest
import icmping
import mocks


def test_icmping_save(mocker):
    mocker.patch('icmping.subprocess.Popen', side_effect=mocks.popen_mock)
    png1 = 'test/test_icmping_save1.png'
    png2 = 'test/test_icmping_save2.png'
    pngall = 'test/test_icmping_save_all.png'

    ping1 = icmping.Server(host='www.example.com', sample_count=3, interval=5)
    ping2 = icmping.Server(host='1.1.1.1', sample_count=3, interval=5)
    ping1.start()
    ping2.start()
    time.sleep(20)

    if os.path.isfile(png1):
        os.remove(png1)
    outfile1 = ping1.save(filename=png1)

    if os.path.isfile(png2):
        os.remove(png2)
    outfile2 = ping2.save(filename=png2)

    if os.path.isfile(pngall):
        os.remove(pngall)
    outfile_all = icmping.save_results([ping1, ping2], filename=pngall)

    ping1.finish()
    ping2.finish()

    assert outfile1 == png1
    assert outfile2 == png2
    assert outfile_all == pngall
    assert os.path.isfile(png1) is True
    assert os.path.isfile(png2) is True
    assert os.path.isfile(pngall) is True


def test_icmping_too_few_data(mocker):
    mocker.patch('icmping.subprocess.Popen', side_effect=mocks.popen_mock)
    png1 = 'test/test_icmping_save1.png'
    png2 = 'test/test_icmping_save2.png'
    pngall = 'test/test_icmping_save_all.png'

    ping1 = icmping.Server(host='www.example.com', sample_count=3, interval=60)
    ping2 = icmping.Server(host='1.1.1.1', sample_count=3, interval=60)
    ping1.start()
    ping2.start()
    time.sleep(10)

    if os.path.isfile(png1):
        os.remove(png1)
    outfile1 = ping1.save(filename=png1)

    if os.path.isfile(png2):
        os.remove(png2)
    outfile2 = ping2.save(filename=png2)

    if os.path.isfile(pngall):
        os.remove(pngall)
    outfile_all = icmping.save_results([ping1, ping2], filename=pngall)

    ping1.finish()
    ping2.finish()

    assert outfile1 is None
    assert outfile2 is None
    assert outfile_all is None
    assert os.path.isfile(png1) is False
    assert os.path.isfile(png2) is False
    assert os.path.isfile(pngall) is False


def test_icmping_exception(mocker):
    mocker.patch('icmping.subprocess.Popen', side_effect=mocks.popen_mock)
    with pytest.raises(icmping.PingError):
        icmping.Server(host='wwww.example.com')


if __name__ == '__main__':
    pytest.main(['-v', __file__])
