#!/usr/bin/env python3

import time
import os
import subprocess
import queue
import datetime as dt
from datetime import datetime
import pytest
import tempbotlib.temperature as tmp
@pytest.fixture
def make_sensor():
    w1_slave = """
bd 01 4b 46 7f ff 03 10 ff : crc=ff YES
bd 01 4b 46 7f ff 03 10 ff t=%05d
"""
    w1_slave_path = '/tmp/w1_slave_test'
    with open(w1_slave_path, 'w') as f:
        f.write(w1_slave % (25*1000))


@pytest.mark.parametrize(('config', 'expected'), [
    ('', 'no environment variable TEMPERATURE_CONFIG'),
    ('tests/temperature-test-xxx.conf', "cannot open configuration file "),
    ('tests/temperature-test-no-temperature.conf',
     "'temperature' key not found in")
])
def test_temperature_init_raise(make_sensor, config, expected):
    os.environ['TEMPERATURE_CONFIG'] = config
    with pytest.raises(tmp.TemperatureError) as e:
        tmp.Temperature(queue.Queue())
    assert str(e.value).startswith(expected)


@pytest.mark.parametrize(('key', 'expected'), [
    ('temperature', "cannot parse configuration"),
    ('sensor_path', ''),
    ('room_hot_alert_threshold', ''),
    ('sampling_interval', ''),
    ('plot_interval', ''),
    ('plot_buffer_size', ''),
])
def test_temperature_init_raise_no_key(make_sensor, key, expected):
    conf = "/tmp/test.conf"
    cmd = "grep -v %s tests/temperature-test.conf > %s" % (key, conf)
    subprocess.run(cmd, shell=True,
                   stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE)
    os.environ['TEMPERATURE_CONFIG'] = conf

    with pytest.raises(tmp.TemperatureError) as e:
        tmp.Temperature(queue.Queue())
    if expected:
        assert str(e.value).startswith(expected)
    else:
        mes = "'%s' not found" % key
        assert str(e.value).startswith(mes)


def test_temperature_check_temperature():
    os.environ['TEMPERATURE_CONFIG'] = "tests/temperature-test.conf"
    w1_slave = """
bd 01 4b 46 7f ff 03 10 ff : crc=ff YES
bd 01 4b 46 7f ff 03 10 ff t=%05d
"""
    w1_slave_path = '/tmp/w1_slave_test'
    temp = [20, 21, 23, 26, 30, 31, 32, 33, 34, 35, 36, 35, 34, 32, 29, 28]
    expected = ["26.0°C :icecream:",
                "30.0°C :icecream:",
                "_Overheating!!! (36.0°C)_",
                "It's cool! (34.0°C)",
                "29.0°C :oden:"]
    with open(w1_slave_path, 'w') as f:
        f.write(w1_slave % (temp[0]*1000))

    q = queue.Queue()
    sensor = tmp.Temperature(q)
    sensor.start_polling()

    for t in temp:
        with open(w1_slave_path, 'w') as f:
            f.write(w1_slave % (t*1000))
        time.sleep(2.0)

    sensor.finish_polling()

    while not q.empty():
        assert q.get() == expected.pop(0)

    pngfile = '/tmp/test-temp.png'
    timedata, tempdata = sensor.get_temp_time()
    if os.path.isfile(pngfile):
        os.remove(pngfile)
        assert not os.path.isfile(pngfile)
    tmp.plot_temperature(timedata, tempdata, pngfile=pngfile)
    assert os.path.isfile(pngfile)


@pytest.mark.parametrize(('config', 'expected'), [
    ('', 'no environment variable TEMPERATURE_CONFIG'),
    ('tests/temperature-test-xxx.conf', "cannot open configuration file "),
    ('tests/temperature-test-no-temperature.conf',
     "'temperature' key not found in")
])
def test_outsidetemperature_init_raise(config, expected):
    os.environ['TEMPERATURE_CONFIG'] = config
    with pytest.raises(tmp.TemperatureError) as e:
        tmp.OutsideTemperature()
    assert str(e.value).startswith(expected)


@pytest.mark.parametrize(('key', 'expected'), [
    ('temperature', "cannot parse configuration"),
    ('outside_hot_alert_threshold', ''),
    ('pipe_alert_threshold', ''),
])
def test_outsidetemperature_init_raise_no_key(key, expected):
    conf = "/tmp/test.conf"
    cmd = "grep -v %s tests/temperature-test.conf > %s" % (key, conf)
    subprocess.run(cmd, shell=True,
                   stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE)
    os.environ['TEMPERATURE_CONFIG'] = conf

    with pytest.raises(tmp.TemperatureError) as e:
        tmp.OutsideTemperature()
    if expected:
        assert str(e.value).startswith(expected)
    else:
        mes = "'%s' not found" % key
        assert str(e.value).startswith(mes)


@pytest.mark.parametrize(('lowest', 'highest', 'days', 'expected'), [
    (20, 30, 0, '===='),
    (20, 35, 0, '===='),
    (-0.5, 30, 0, '===='),
    (-10, 30, 0, '===='),
    (20, 30, 1, '===='),
    (20, 35, 1, '====It will be too hot!!'),
    (31, 20, 1, '====You become butter...'),
    (-4, -0.5, 1, '====It will be too cold!!'),
    (-10, 30, 1, '====keep your pipes!!'),
])
def test_outsidetemperature(mocker, lowest, highest, days, expected):
    os.environ['TEMPERATURE_CONFIG'] = 'tests/temperature-test.conf'

    mocker.patch('tempbotlib.temperature.Weather.__init__', return_value=None)
    mocker.patch('tempbotlib.temperature.Weather.fetch')

    date = datetime.today() + dt.timedelta(days=days)
    mocker.patch('tempbotlib.temperature.Weather.lowest',
                 return_value=(lowest, date))
    mocker.patch('tempbotlib.temperature.Weather.highest',
                 return_value=(highest, date))

    outside = tmp.OutsideTemperature()
    mes = '===='
    mes += outside.check_temperature()
    assert mes.startswith(expected)

    mes = outside.fetch_temperature()
    assert mes.startswith('A low of')


if __name__ == '__main__':
    pytest.main(['-v', __file__])
