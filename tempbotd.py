#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Full Stack Python
How to Build Your First Slack Bot With Python
https://www.fullstackpython.com/blog/build-first-slack-bot-python.html
"""
import os
import re
import time
import datetime
import websocket
import slackclient
from slackclient import SlackClient
import requests
import logging
import anyping as ap
from weather import Weather
from eventlogger import EventLogger
from book import BookStatus
from getip import GetIP

import matplotlib
matplotlib.use("Agg") # noqa
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# global logging settings
log_level = logging.WARNING     # default debug level
formatter = '%(name)s: %(message)s'

TEMPBOT_DEBUG = os.environ.get("TEMPBOT_DEBUG")
if TEMPBOT_DEBUG == 'info':
    log_level = logging.INFO
elif TEMPBOT_DEBUG == 'debug':
    log_level = logging.DEBUG
    formatter = '%(asctime)s %(name)s[%(lineno)s] %(levelname)s: %(message)s'
else:
    pass    # default debug level

logging.basicConfig(level=log_level, format=formatter)

# logger setting
log = logging.getLogger('tempbotd')

# tempbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")
if not BOT_ID:
    log.critical('no environment variable BOT_ID')
    exit(1)

CHANNEL_ID = os.environ.get("CHANNEL_ID")
if not CHANNEL_ID:
    log.critical('no environment variable CHANNEL_ID')
    exit(1)

SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
if not SLACK_BOT_TOKEN:
    log.critical('no environment variable SLACK_BOT_TOKEN')
    exit(1)

T_SENSOR_PATH = os.environ.get("T_SENSOR_PATH")
if not T_SENSOR_PATH:
    log.warning('no environment variable T_SENSOR_PATH')


# constants
AT_BOT = "<@" + BOT_ID + ">"
COMMAND_TIME = "time"
COMMAND_DATE = "date"
COMMAND_PLOT = "plot"
COMMAND_PING = "ping"
COMMAND_WEATHER = "weather"
COMMAND_TRAFFIC = "traffic"
COMMAND_LOG = "log"
COMMAND_BOOK = "book"
COMMAND_IP = "ip"

# default parameters
READ_WEBSOCKET_DELAY = 2    # 2 second delay between reading from firehose
ROOM_HOT_ALERT_THRESHOLD = 35.0     # [degrees celsius]
OUTSIDE_HOT_ALERT_THRESHOLD = 30.0  # [degrees celsius]
PIPE_ALERT_THRESHOLD = -5.0         # [degrees celsius]

if os.environ.get("ROOM_HOT_ALERT_THRESHOLD"):
    try:
        ROOM_HOT_ALERT_THRESHOLD = float(
            os.environ.get("ROOM_HOT_ALERT_THRESHOLD"))
    except Exception as e:
        log.warning(str(e))
log.debug("ROOM_HOT_ALERT_THRESHOLD: %.1f" % ROOM_HOT_ALERT_THRESHOLD)

if os.environ.get("OUTSIDE_HOT_ALERT_THRESHOLD"):
    try:
        OUTSIDE_HOT_ALERT_THRESHOLD = float(
            os.environ.get("OUTSIDE_HOT_ALERT_THRESHOLD"))
    except Exception as e:
        log.warning(str(e))
log.debug("OUTSIDE_HOT_ALERT_THRESHOLD: %.1f" % OUTSIDE_HOT_ALERT_THRESHOLD)

if os.environ.get("PIPE_ALERT_THRESHOLD"):
    try:
        PIPE_ALERT_THRESHOLD = float(os.environ.get("PIPE_ALERT_THRESHOLD"))
    except Exception as e:
        log.warning(str(e))
log.debug("PIPE_ALERT_THRESHOLD: %.1f" % PIPE_ALERT_THRESHOLD)


# command list
COMMAND_CHAT = {
    "hey": "Siri!",
    "ok": "Google!",
    "hello": "World!",
    "do": "Sure...write some more code then i can do that!",
    "help": "book date ip log ping plot time traffic weather",
    "?": "book date ip log ping plot time traffic weather",
}


# instantiate Slack & Twilio clients
slack_client = SlackClient(SLACK_BOT_TOKEN)


def get_temperature():
    temp = None

    if not T_SENSOR_PATH:
        log.warning("get_temperature(): no temperature sensor")
        return temp

    try:
        with open(T_SENSOR_PATH) as f:
            data = f.read()
            temp = int(data[data.index('t=')+2:])/1000.0
    except Exception as e:
        log.warning("get_temperature(): %s" % e)

    return temp


def upload_file(file_path, title='temperature', channel=CHANNEL_ID):
    with open(file_path, 'rb') as f:
        param = {'token': os.environ.get('SLACK_BOT_TOKEN'),
                 'channels': channel, 'title': title}
        r = requests.post("https://slack.com/api/files.upload",
                          params=param, files={'file': f})
        log.debug(r)


def plot_temperature(time, data, channel=CHANNEL_ID):
    retval = False

    if len(data) < 2:
        log.info('skip temperature plot because there are too few data(%d)' %
                 (len(data)))
        return retval

    temp_png = '/tmp/temp.png'
    fig = plt.figure(figsize=(15, 4))
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(time, data, c='#0000ff', alpha=0.7)
    ax.set_title('temerature')
    ax.set_xlim(time[0], time[-1])
    ax.set_ylim(0, 50)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.grid()

    ax.tick_params(left=False, bottom=False)
    ax.spines['top'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.savefig(temp_png, transparent=False, bbox_inches='tight')
    plt.close(fig)
    if os.path.isfile(temp_png):
        upload_file(temp_png, channel=channel)
        retval = True

    return retval


def handle_command(command, channel):
    """
        Receives commands directed at the bot and determins if they
        are valid commands. if so, then acts on the commands. if not,
        returns back what it needs for clarification.
    """
    tmpr = get_temperature()
    if tmpr:
        response = '%.1f °C' % (tmpr)
    else:
        response = 'no sensor'

    if command in COMMAND_CHAT:
        response = COMMAND_CHAT[command]

    if command.startswith(COMMAND_TIME):
        d = datetime.datetime.today()
        response = d.strftime("%H:%M:%S")
    if command.startswith(COMMAND_DATE):
        d = datetime.datetime.today()
        response = d.strftime("%Y-%m-%d")
    if command.startswith(COMMAND_PLOT):
        time, data = temperature.get_temp_time()
        if len(time) > 0:
            if plot_temperature(time, data, channel):
                response = 'plotted!'
            else:
                response = 'plot is not available'
        else:
            response = 'no data'
    if command.startswith(COMMAND_PING):
        if pingservers:
            response = pingservers.get_status_of_servers()
        else:
            response = 'ping is not available'
    if command.startswith(COMMAND_WEATHER):
        if forecast:
            response = forecast.fetch_temperature()
        else:
            response = 'weather information is not available'
    if command.startswith(COMMAND_TRAFFIC):
        traffic_files = pingservers.save_icmp_results()
        if traffic_files:
            for file in traffic_files:
                upload_file(file[0], title='ICMP Echo Reply Message',
                            channel=channel)
            response = 'plotted %d graphs' % len(traffic_files)
        else:
            response = 'traffic is not available'
    if command.startswith(COMMAND_LOG):
        log_file = elog.save(filename="/tmp/elog.png")
        if log_file:
            upload_file(log_file, title='Event Log', channel=channel)
            response = 'event log plotted!'
        else:
            response = 'no event log'
    if command.startswith(COMMAND_BOOK):
        if book:
            cmd = command.strip()
            cmd = re.split('[ 　]', cmd, 1)
            if len(cmd) != 2:
                response = 'book <title>'
            else:
                log.debug("command: %s, arg: %s", cmd[0], cmd[1])
                if not book.searching and not book.book_status:
                    book.search(cmd[1])
                    response = '"%s"...' % cmd[1]
                else:
                    response = 'sorry, busy with searching the other book'
        else:
            response = 'book is not available'
    if command.startswith(COMMAND_IP):
        response = ipaddress.current_ip

    slack_client.api_call("chat.postMessage", channel=channel,
                          text=response, as_user=True)


def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an envents firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                # return text after the @ mention, whitespace removed
                return output['text'].split(AT_BOT)[1].strip().lower(), \
                        output['channel']

    return None, None


class TemperatureError(Exception):
    pass


class Temperature:
    def __init__(self):
        self.delay = 15
        self.is_hot = False
        self.tempdata = []
        self.timedata = []
        self.pre_temp = get_temperature()
        self.temp_sum = 0
        self.temp_n = 0

        if not self.pre_temp:
            raise TemperatureError("temperature is not avaiable")

    def check_difference(self, cur_temp):
        self.delay = self.delay - 1
        if self.delay == 0:
            self.delay = 15
            diff = self.pre_temp - cur_temp
            self.pre_temp = cur_temp
            if diff*diff > 4:
                response = str(cur_temp) + '°C'
                slack_client.api_call("chat.postMessage",
                                      channel=CHANNEL_ID,
                                      text=response,
                                      as_user=True)

    def check_overheating(self, cur_temp):
        if cur_temp > ROOM_HOT_ALERT_THRESHOLD:
            if not self.is_hot:
                log.info("Overheating!!!")
                warning = "_Overheating!!! (" + str(cur_temp) + "°C)_"
                slack_client.api_call("chat.postMessage",
                                      channel=CHANNEL_ID,
                                      text=warning,
                                      as_user=True)
                self.is_hot = True
        else:
            if self.is_hot and cur_temp < ROOM_HOT_ALERT_THRESHOLD:
                log.info("It's cool!")
                warning = "It's cool! (" + str(cur_temp) + "°C)"
                slack_client.api_call("chat.postMessage",
                                      channel=CHANNEL_ID,
                                      text=warning,
                                      as_user=True)
                self.is_hot = False

    def check_temperature(self):
        temp = get_temperature()
        self.check_difference(temp)
        self.check_overheating(temp)

        self.temp_sum += temp
        self.temp_n += 1
        if self.temp_n == 30:
            if len(self.tempdata) > 60*24:
                self.tempdata.pop(0)
            self.tempdata.append(self.temp_sum/self.temp_n)
            if len(self.timedata) > 60*24:
                self.timedata.pop(0)
            self.timedata.append(datetime.datetime.today())

            self.temp_sum = 0
            self.temp_n = 0

    def get_temp_time(self):
        return self.timedata, self.tempdata


class OutsideTemperature():
    def __init__(self, interval=4):
        self.wt = Weather()
        self.datetime_format = 'at %I:%M %p on %A'
        self.degree = '°C'
        self.interval = datetime.timedelta(hours=interval)
        self.fetch_time = datetime.datetime.now() - self.interval

    def fetch_temperature(self):
        self.wt.fetch()
        low, low_t = self.wt.lowest()
        high, high_t = self.wt.highest()
        low_t_str = low_t.strftime(self.datetime_format)
        high_t_str = high_t.strftime(self.datetime_format)

        mes = "A low of %.1f%s %s\n" % (low, self.degree, low_t_str)
        mes += "A high of %.1f%s %s" % (high, self.degree, high_t_str)

        return mes

    def check_temperature(self, min=-5.0, max=30.0):
        now = datetime.datetime.now()
        if now < (self.fetch_time + self.interval):
            return ""

        log.debug("min=%d, max=%d" % (max, min))
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


if __name__ == "__main__":
    try:
        temperature = Temperature()
    except TemperatureError as e:
        log.warning("Temperature: %s" % e)
        log.info("Disable temperature")
        temperature = None

    elog = EventLogger(buffer_size=128)

    try:
        pingservers = ap.Servers()
    except Exception as e:
        log.warning("Anyping: %s" % e)
        log.info("Disable any pings")
        pingservers = None

    try:
        forecast = OutsideTemperature()
    except Exception as e:
        log.warning("Weather forecast: %s" % e)
        log.info("Disable outside temperature message")
        forecast = None

    try:
        book = BookStatus()
    except Exception as e:
        log.warning("Book search: %s" % e)
        log.info("Disable book search")
        book = None

    try:
        ipaddress = GetIP()
        ipaddress.start_polling()
    except Exception as e:
        log.warning("Get IP address : %s" % e)
        log.info("Disable IP address")
        ipaddress = None

    if pingservers:
        PING_INTERVAL_TIMER = int(pingservers.interval/READ_WEBSOCKET_DELAY)
    else:
        PING_INTERVAL_TIMER = -1

    if slack_client.rtm_connect(with_team_state=False, auto_reconnect=True):
        log.info("Temperature Bot connected and running!")

        ping_timer = 1
        while True:
            try:
                command, channel = parse_slack_output(slack_client.rtm_read())
                log.debug("got command(%s): %s" % (channel, command))
                if command and channel:
                    elog.log('command')
                    handle_command(command, channel)

                if temperature:
                    temperature.check_temperature()

                time.sleep(READ_WEBSOCKET_DELAY)
            except (websocket.WebSocketConnectionClosedException,
                    slackclient.server.SlackConnectionError) as e:
                log.warning(e)
                log.warning('Caught websocket disconnect, reconnecting...')
                elog.log('disconnected')
                time.sleep(READ_WEBSOCKET_DELAY)
                while not slack_client.rtm_connect(with_team_state=False,
                                                   auto_reconnect=True):
                    log.warning('Caught websocket disconnect, reconnecting...')
                    time.sleep(READ_WEBSOCKET_DELAY)
                elog.log('connected')
            except Exception as e:
                import traceback
                traceback.print_exc()
                log.warning(e)
                time.sleep(READ_WEBSOCKET_DELAY)

            if pingservers:
                ping_timer -= 1
                log.debug("do anyping: %d" % ping_timer)
                if ping_timer <= 0:
                    ping_timer = PING_INTERVAL_TIMER
                    message = pingservers.ping()
                    if message:
                        elog.log('ping')
                        slack_client.api_call("chat.postMessage",
                                              channel=CHANNEL_ID,
                                              text=message,
                                              as_user=True)

            if forecast:
                log.debug("do forecast")
                message = forecast.check_temperature(
                    min=PIPE_ALERT_THRESHOLD,
                    max=OUTSIDE_HOT_ALERT_THRESHOLD)
                if message:
                    elog.log('forecast')
                    slack_client.api_call("chat.postMessage",
                                          channel=CHANNEL_ID,
                                          text=message,
                                          as_user=True)

            if book:
                log.debug("do book")
                message = book.result_by_string()
                if message:
                    elog.log('book')
                    slack_client.api_call("chat.postMessage",
                                          channel=CHANNEL_ID,
                                          text=message,
                                          as_user=True)

            if ipaddress:
                log.debug("do get ipaddress")
                res = ipaddress.is_new()
                if res:
                    elog.log('ip')
                    message = 'New IP address: %s' % ipaddress.current_ip
                    slack_client.api_call("chat.postMessage",
                                          channel=CHANNEL_ID,
                                          text=message,
                                          as_user=True)
    else:
        log.critical("Connection failed. Invalid Slack token or bot ID?")

    if ipaddress:
        ipaddress.finish_polling()
