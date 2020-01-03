#!/usr/bin/env python3

import os
import datetime as dt
from datetime import datetime
import json
import time
from threading import Thread
import queue
from .weather import Weather, WeatherError

import matplotlib
matplotlib.use("Agg") # noqa
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import logging
log = logging.getLogger(__name__)


def get_value(json, key, valuetype):
    ret = None

    value = json.get(key)
    if not value:
        raise TemperatureError("'%s' not found" % key)
    try:
        ret = valuetype(value)
    except ValueError as e:
        log.warning(e)
        raise TemperatureError("'%s' is not '%s'" % (key, valuetype.__name__))

    return ret


class TemperatureError(Exception):
    pass


class Temperature:
    def __init__(self, q):
        self.thread = None
        self.thread_finish = False
        self.messages = q

        self.TEMPERATURE_CONFIG = os.environ.get("TEMPERATURE_CONFIG")
        if not self.TEMPERATURE_CONFIG:
            raise TemperatureError(
                            'no environment variable TEMPERATURE_CONFIG')

        try:
            f = open(self.TEMPERATURE_CONFIG)
        except (IOError, FileNotFoundError):
            raise TemperatureError(
                "cannot open configuration file '{0}'".format(
                    self.TEMPERATURE_CONFIG))

        try:
            conf = json.load(f)
        except ValueError as e:
            log.warning(e)
            raise TemperatureError("cannot parse configuration")

        self.configuration = conf.get('temperature')
        if not self.configuration:
            raise TemperatureError("'temperature' key not found in %s"
                                   % self.TEMPERATURE_CONFIG)

        self.sensor_path = self.configuration.get('sensor_path')
        if not self.sensor_path:
            raise TemperatureError("'sensor_path' not found")
        self.pre_temp = self.get_temperature()
        if not self.pre_temp:
            raise TemperatureError("temperature is not avaiable")
        log.debug('sensor_path: %s ' % self.sensor_path)

        key = 'room_hot_alert_threshold'
        self.room_hot_alert_threshold = get_value(self.configuration,
                                                  key, float)
        log.debug('%s: %f degrees Celsius' %
                  (key, self.room_hot_alert_threshold))

        key = 'sampling_interval'
        self.sampling_interval = get_value(self.configuration, key, int)
        log.debug('%s: %d sec' % (key, self.sampling_interval))

        key = 'plot_interval'
        self.plot_interval = get_value(self.configuration, key, int)
        log.debug('%s: %d sec' % (key, self.plot_interval))

        key = 'plot_buffer_size'
        self.plot_buffer_size = get_value(self.configuration, key, int)
        log.debug('%s: %d' % (key, self.sampling_interval))

        # self.sampleratio
        self.is_hot = False
        self.tempdata = []
        self.timedata = []
        self.temp_sum = 0
        self.temp_n = 0
        self.plot_interval_t1 = None

    def get_temperature(self):
        temp = None

        if not self.sensor_path:
            log.warning("get_temperature(): no temperature sensor")
            return temp

        try:
            with open(self.sensor_path) as f:
                data = f.read()
                temp = int(data[data.index('t=')+2:])/1000.0
        except Exception as e:
            log.warning("get_temperature(): %s" % e)

        return temp

    def check_difference(self, cur_temp):
        log.debug("check_difference(%s) pre_temp:%s" %
                  (cur_temp, self.pre_temp))

        diff = cur_temp - self.pre_temp
        log.debug("diff: %s" % diff)
        self.pre_temp = cur_temp
        m = None
        if diff > 2:
            m = str(cur_temp) + '°C'+' :icecream:'
        elif diff < -2:
            m = str(cur_temp) + '°C'+' :oden:'

        if m:
            try:
                self.messages.put_nowait(m)
            except queue.Full as e:
                log.warning("check_differnece(): %s" % e)

        log.debug("exit check_difference()")

    def check_overheating(self, cur_temp):
        m = None
        if cur_temp > self.room_hot_alert_threshold:
            if not self.is_hot:
                log.info("Overheating!!!")
                m = "_Overheating!!! (" + str(cur_temp) + "°C)_"
                self.is_hot = True
        else:
            if self.is_hot and cur_temp < self.room_hot_alert_threshold:
                log.info("It's cool!")
                m = "It's cool! (" + str(cur_temp) + "°C)"
                self.is_hot = False

        if m:
            try:
                self.messages.put_nowait(m)
            except queue.Full as e:
                log.warning("check_differnece(): %s" % e)

    def check_temperature(self):
        log.debug("check_temperature()")
        temp = self.get_temperature()
        log.debug(temp)
        if temp is None:
            return

        self.check_difference(temp)
        self.check_overheating(temp)

        self.temp_sum += temp
        self.temp_n += 1

        t2 = datetime.today()
        if (t2 - self.plot_interval_t1).total_seconds() >= self.plot_interval:
            self.plot_interval_t1 = t2
            if len(self.tempdata) >= self.plot_buffer_size:
                self.tempdata.pop(0)
            self.tempdata.append(self.temp_sum/self.temp_n)
            if len(self.timedata) >= self.plot_buffer_size:
                self.timedata.pop(0)
            self.timedata.append(datetime.today())

            self.temp_sum = 0
            self.temp_n = 0
        log.debug("exit check_temperature()")

    def get_temp_time(self):
        return self.timedata, self.tempdata

    def run(self):
        log.debug("run()")
        self.plot_interval_t1 = datetime.today()
        while not self.thread_finish:
            t1 = datetime.today()
            self.check_temperature()
            t2 = datetime.today()
            while (t2 - t1).total_seconds() < self.sampling_interval:
                if self.thread_finish:
                    break
                time.sleep(0.1)
                t2 = datetime.today()

        log.debug("exit run()")

    def start_polling(self):
        log.debug("start_polling()")
        if self.thread:
            log.warning("thread is already running")
            return

        self.thread = Thread(target=self.run)
        self.thread_finish = False
        self.thread.start()
        log.debug("exit start_polling()")

    def finish_polling(self):
        log.debug("finish_polling()")
        if self.thread:
            self.thread_finish = True
            log.debug("waiting for thread")
            self.thread.join()
            log.debug("thread is done")
            self.thread = None
        else:
            log.debug("no running thread")
        log.debug("exit finish_polling()")


class OutsideTemperature():
    def __init__(self, interval=4):
        self.TEMPERATURE_CONFIG = os.environ.get("TEMPERATURE_CONFIG")
        if not self.TEMPERATURE_CONFIG:
            raise TemperatureError(
                            'no environment variable TEMPERATURE_CONFIG')

        try:
            f = open(self.TEMPERATURE_CONFIG)
        except (IOError, FileNotFoundError):
            raise TemperatureError(
                "cannot open configuration file '{0}'".format(
                    self.TEMPERATURE_CONFIG))

        try:
            conf = json.load(f)
        except ValueError as e:
            log.warning(e)
            raise TemperatureError("cannot parse configuration")

        self.configuration = conf.get('temperature')
        if not self.configuration:
            raise TemperatureError("'temperature' key not found in %s"
                                   % self.TEMPERATURE_CONFIG)

        key = 'outside_hot_alert_threshold'
        self.outside_hot_alert_threshold = get_value(self.configuration,
                                                     key, float)
        log.debug('%s: %f degrees Celsius' %
                  (key, self.outside_hot_alert_threshold))

        key = 'pipe_alert_threshold'
        self.pipe_alert_threshold = get_value(self.configuration, key, float)
        log.debug('%s: %f degrees Celsius' %
                  (key, self.pipe_alert_threshold))

        try:
            self.wt = Weather()
        except WeatherError as e:
            raise TemperatureError(e)

        self.datetime_format = 'at %I:%M %p on %A'
        self.degree = '°C'
        self.interval = dt.timedelta(hours=interval)
        self.fetch_time = datetime.now() - self.interval

    def fetch_temperature(self):
        self.wt.fetch()
        low, low_t = self.wt.lowest()
        high, high_t = self.wt.highest()
        low_t_str = low_t.strftime(self.datetime_format)
        high_t_str = high_t.strftime(self.datetime_format)

        mes = "A low of %.1f%s %s\n" % (low, self.degree, low_t_str)
        mes += "A high of %.1f%s %s" % (high, self.degree, high_t_str)

        return mes

    def check_temperature(self):
        min = self.pipe_alert_threshold
        max = self.outside_hot_alert_threshold

        now = datetime.now()
        if now < (self.fetch_time + self.interval):
            return ""

        log.debug("min=%d, max=%d" % (min, max))
        self.fetch_time = now
        self.wt.fetch()
        low, low_t = self.wt.lowest()
        high, high_t = self.wt.highest()
        low_t_str = low_t.strftime(self.datetime_format)
        high_t_str = high_t.strftime(self.datetime_format)
        log.debug("log=%d, low_t=%s" % (low, low_t_str))
        log.debug("high=%d, high_t=%s" % (high, high_t_str))
        mes = ""
        if low_t > now and low <= min:
            if mes != "":
                mes += "\n"
            mes += "keep your pipes!!\n"
            mes += "A low of %.1f%s %s" % (low, self.degree, low_t_str)
        if high_t > now and high < 0:
            if mes != "":
                mes += "\n"
            mes += "It will be too cold!!\n"
            mes += "A high of %.1f%s %s" % (high, self.degree, high_t_str)
        if high_t > now and high > max:
            if mes != "":
                mes += "\n"
            mes += "It will be too hot!!\n"
            mes += "A high of %.1f%s %s" % (high, self.degree, high_t_str)
        if low_t > now and low > max:
            if mes != "":
                mes += "\n"
            mes += "You become butter...\n"
            mes += "A low of %.1f%s %s" % (low, self.degree, low_t_str)

        log.debug("message: %s" % (mes))
        return mes


def plot_temperature(time, data, pngfile='/tmp/temp.png'):
    retval = False

    if len(data) < 2:
        log.info('skip temperature plot because there are too few data(%d)' %
                 (len(data)))
        return retval

    fig = plt.figure(figsize=(15, 4))
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(time, data, c='#0000ff', alpha=0.7)
    ax.set_title('temerature')
    ax.set_xlim(time[0], time[-1])
    ax.set_ylim(0, 50)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M'))
    ax.grid()

    ax.tick_params(left=False, bottom=False)
    ax.spines['top'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.savefig(pngfile, transparent=False, bbox_inches='tight')
    plt.close(fig)

    if os.path.isfile(pngfile):
        retval = pngfile

    return retval


if __name__ == '__main__':
    """
    for debug
    """
    log_level = logging.DEBUG
    formatter = '%(asctime)s %(name)s[%(lineno)s] %(levelname)s: %(message)s'
    logging.basicConfig(level=log_level, format=formatter)

    os.environ['TEMPERATURE_CONFIG'] = 'tests/temperature-test.conf'

    # pusedo sensor /tmp/w1_slave
    w1_slave_path = '/tmp/w1_slave_tests'
    w1_slave = """
bd 01 4b 46 7f ff 03 10 ff : crc=ff YES
bd 01 4b 46 7f ff 03 10 ff t=%05d
"""
    # pusedo temperature
    temp = [20, 21, 23, 26, 30, 31, 32, 33, 34, 35, 36, 35, 34, 32, 29, 28]

    # initialize /tmp/w1_slave
    with open(w1_slave_path, 'w') as f:
        f.write(w1_slave % (temp[0]*1000))

    # initialize Temperature and run
    q = queue.Queue()
    tmp = Temperature(q)
    tmp.start_polling()

    # change temperature
    for t in temp:
        with open(w1_slave_path, 'w') as f:
            f.write(w1_slave % (t*1000))
        time.sleep(2.0)

    # output graph
    tp, tm = tmp.get_temp_time()
    plot_temperature(tp, tm, pngfile='temp_test.png')

    # print output
    while not q.empty():
        print(q.get())

    # stop Temperature
    tmp.finish_polling()

    # initialize OutsideTemperature
    outside = OutsideTemperature()
    mes = outside.fetch_temperature()
    print(mes)
