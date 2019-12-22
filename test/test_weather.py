#!/usr/bin/env python3

import pytest
import os
import weather
import datetime


def requests_mock(*args, **kwargs):
    class MockResponse:
        def __init__(self, text, status_code):
            self.status_code = status_code
            self.text = text

    try:
        f = open('test/test_weather_response_mock.txt')
    except IOError as e:
        print(e)
        raise(e)

    return MockResponse(f.read(), 200)


def test_weather_init_raise_my_place():
    os.environ['MY_PLACE'] = ''
    os.environ['DARK_SKY_KEY'] = 'xxxx'
    with pytest.raises(weather.WeatherError):
        weather.Weather()


def test_weather_init_raise_dark_sky_key():
    os.environ['MY_PLACE'] = 'xxxx:yyyy'
    os.environ['DARK_SKY_KEY'] = ''
    with pytest.raises(weather.WeatherError):
        weather.Weather()


def test_weather_lowest(mocker):
    mocker.patch('weather.requests.get', side_effect=requests_mock)
    os.environ['MY_PLACE'] = 'xxxx:yyyy'
    os.environ['DARK_SKY_KEY'] = 'xxxx'

    w = weather.Weather()
    low, lowTime = w.lowest()
    assert type(low) == float
    assert low == 1.34
    assert type(lowTime) == datetime.datetime


def test_weather_highest(mocker):
    mocker.patch('weather.requests.get', side_effect=requests_mock)
    os.environ['MY_PLACE'] = 'xxxx:yyyy'
    os.environ['DARK_SKY_KEY'] = 'xxxx'

    w = weather.Weather()
    high, highTime = w.highest()
    assert type(high) == float
    assert high == 5.69
    assert type(highTime) == datetime.datetime


if __name__ == '__main__':
    pytest.main(['-v', __file__])
