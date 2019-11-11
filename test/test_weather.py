#!/usr/bin/env python3

import pytest
import os
import weather
import datetime

my_place = os.environ.get('MY_PLACE')
dark_sky_key = os.environ.get('DARK_SKY_KEY')


def test_weather_init_raise_my_place():
    os.environ['MY_PLACE'] = ''
    os.environ['DARK_SKY_KEY'] = dark_sky_key
    with pytest.raises(weather.WeatherError):
        weather.Weather()


def test_weather_init_raise_dark_sky_key():
    os.environ['MY_PLACE'] = my_place
    os.environ['DARK_SKY_KEY'] = ''
    with pytest.raises(weather.WeatherError):
        weather.Weather()


def test_weather_lowest():
    os.environ['MY_PLACE'] = my_place
    os.environ['DARK_SKY_KEY'] = dark_sky_key

    w = weather.Weather()
    low, lowTime = w.lowest()
    assert type(low) == float
    assert type(lowTime) == datetime.datetime


def test_weather_highest():
    os.environ['MY_PLACE'] = my_place
    os.environ['DARK_SKY_KEY'] = dark_sky_key

    w = weather.Weather()
    high, highTime = w.highest()
    assert type(high) == float
    assert type(highTime) == datetime.datetime


if __name__ == '__main__':
    pytest.main(['-v', __file__])
