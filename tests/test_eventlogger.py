#!/usr/bin/env python3

import pytest
import time
import tempbotlib.eventlogger as eventlogger
import random
import os


def test_eventlogger_buffer_size():
    elog = eventlogger.EventLogger(buffer_size=10)

    elog.log('test')
    assert len(elog.eventlog['test']) == 1

    for i in range(8):
        elog.log('test')
    assert len(elog.eventlog['test']) == 9

    elog.log('test')
    assert len(elog.eventlog['test']) == 10

    elog.log('test')
    assert len(elog.eventlog['test']) == 10

    for i in range(100):
        elog.log('test')
    assert len(elog.eventlog['test']) == 10

    # other category
    elog.log('test2')
    assert len(elog.eventlog['test2']) == 1

    for i in range(8):
        elog.log('test2')
    assert len(elog.eventlog['test2']) == 9

    elog.log('test2')
    assert len(elog.eventlog['test2']) == 10

    elog.log('test2')
    assert len(elog.eventlog['test2']) == 10

    for i in range(100):
        elog.log('test2')
    assert len(elog.eventlog['test2']) == 10

    assert len(elog.eventlog['test']) == 10


def test_eventlogger_not_save():
    fruits = ["apple", "banana", "cherry",
              "durian", "elderberry", "fig", "grape"]

    elog = eventlogger.EventLogger()

    filename = 'event_log.png'
    if os.path.isfile(filename):
        os.remove(filename)
    ret = elog.save()
    assert ret is None
    assert os.path.isfile(filename) is False

    for i in range(15):
        time.sleep(2)
        for cat in fruits:
            if random.random() < 0.3:
                elog.log(cat)

    filename = 'tests/test_eventlogger_zucchini.png'
    if os.path.isfile(filename):
        os.remove(filename)
    ret = elog.save(filename=filename,
                    category='zucchini',
                    title='event(zucchini)')
    assert ret is None
    assert os.path.isfile(filename) is False


def test_eventlogger_save():
    fruits = ["apple", "banana", "cherry",
              "durian", "elderberry", "fig", "grape"]

    elog = eventlogger.EventLogger()
    for i in range(15):
        time.sleep(2)
        for cat in fruits:
            if random.random() < 0.3:
                elog.log(cat)
    for i in range(15):
        time.sleep(2)
        if random.random() < 0.3:
            elog.log('zucchini')

    filename = 'event_log.png'
    if os.path.isfile(filename):
        os.remove(filename)
    ret = elog.save()
    assert ret == filename
    assert os.path.isfile(filename) is True

    filename = 'tests/test_eventlogger_apple.png'
    if os.path.isfile(filename):
        os.remove(filename)
    ret = elog.save(filename=filename, category='apple', title='event(apple)')
    assert ret == filename
    assert os.path.isfile(filename) is True


if __name__ == '__main__':
    pytest.main(['-v', __file__])
