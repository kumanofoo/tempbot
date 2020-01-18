#!/usr/bin/env python3

"""
Full Stack Python
How to Build Your First Slack Bot With Python
https://www.fullstackpython.com/blog/build-first-slack-bot-python.html
"""
import os
import time
import datetime
import queue
import websocket
import slackclient
from slackclient import SlackClient
import requests
import logging
import tempbotlib as tbd

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

BOOK_CHANNEL = os.environ.get('BOOK_CHANNEL')
if not BOOK_CHANNEL:
    log.info('no environment variable BOOK_CHANNEL')
if BOOK_CHANNEL == CHANNEL_ID:
    log.critical('CHANNEL_ID and BOOK_CHANNEL have the same ID')
    exit(1)

# constants
AT_BOT = "<@" + BOT_ID + ">"

# default parameters
READ_WEBSOCKET_DELAY = 2    # 2 second delay between reading from firehose

# instantiate Slack & Twilio clients
slack_client = SlackClient(SLACK_BOT_TOKEN)

messages = queue.Queue()

try:
    temperature = tbd.temperature.Temperature(messages)
    temperature.start_polling()
except tbd.temperature.TemperatureError as e:
    log.warning("Temperature: %s" % e)
    log.info("Disable temperature")
    temperature = None

elog = tbd.eventlogger.EventLogger(buffer_size=128)

try:
    pingservers = tbd.anyping.Servers()
except tbd.anyping.AnypingError as e:
    log.warning("Anyping: %s" % e)
    log.info("Disable any pings")
    pingservers = None

try:
    forecast = tbd.temperature.OutsideTemperature()
except tbd.temperature.TemperatureError as e:
    log.warning("Weather forecast: %s" % e)
    log.info("Disable outside temperature message")
    forecast = None

try:
    book = tbd.book.BookStatus(messages)
except tbd.book.BookStatusError as e:
    log.warning("Book search: %s" % e)
    log.info("Disable book search")
    book = None

try:
    ipaddress = tbd.getip.GetIP(messages)
    ipaddress.start_polling()
except tbd.getip.GetIPError as e:
    log.warning("Get IP address : %s" % e)
    log.info("Disable IP address")
    ipaddress = None


def upload_file(file_path, title='temperature', channel=CHANNEL_ID):
    with open(file_path, 'rb') as f:
        param = {'token': os.environ.get('SLACK_BOT_TOKEN'),
                 'channels': channel, 'title': title}
        r = requests.post("https://slack.com/api/files.upload",
                          params=param, files={'file': f})
        log.debug(r)


def parse_slack_output(slack_rtm_output):
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                # return text after the @ mention, whitespace removed
                return output['text'].split(AT_BOT)[1].strip().lower(), \
                        output['channel']

    return None, None


class CommandHandler:
    def __init__(self):
        self.chat = {
            "hey": "Siri!",
            "ok": "Google!",
            "hello": "World!",
            "do": "Sure...write some more code then i can do that!",
            "help": "book date ip log ping plot time traffic weather",
            "?": "book date ip log ping plot time traffic weather",
        }
        self.command = {
            "book": book.run,
            "date": self.date,
            "ip": self.ip,
            "log": self.log,
            "ping": self.ping,
            "plot": self.plot,
            "time": self.time,
            "traffic": self.traffic,
            "weather": self.weather,
        }

    def run(self, command, channel):
        response = 'no sensor'
        if temperature:
            tmpr = temperature.get_temperature()
            if tmpr:
                response = '%.1f °C' % (tmpr)

        if command in self.chat:
            response = self.chat[command]

        if channel == BOOK_CHANNEL:
            command = 'book ' + command

        for key in self.command:
            if not command.startswith(key):
                continue
            if self.command[key]:
                param = tbd.command.Command(command=command, channel=channel)
                log.debug('param.files(%x): %s' % (id(param), param.files))
                result = self.command[key](param)
                log.debug('result.files: %s' % result.files)
                for file in result.files:
                    log.debug('result file: %s', file)
                    upload_file(file[0], title=file[1], channel=channel)
                response = result.message
            else:
                response = "'%s' command is not available" % key

        slack_client.api_call("chat.postMessage", channel=channel,
                              text=response, as_user=True)

    def time(self, param):
        param.message = datetime.datetime.today().strftime("%H:%M:%S")
        return param

    def date(self, param):
        param.message = datetime.datetime.today().strftime("%Y-%m-%d")
        return param

    def traffic(self, param):
        if not pingservers:
            param.message = 'traffic is not available'
            return param

        traffic_files = pingservers.save_icmp_results()
        if traffic_files:
            log.debug('traffic_files: %s', traffic_files)
            param.files = traffic_files
            param.message = 'plotted %d graphs' % len(traffic_files)
        else:
            param.message = 'traffic is not available'
        return param

    def ping(self, param):
        if pingservers:
            param.message = pingservers.get_status_of_servers()
        else:
            param.message = 'ping is not available'
        return param

    def log(self, param):
        log_file = elog.save(filename="/tmp/elog.png")
        if log_file:
            param.files = [(log_file, 'Event Log')]
            param.message = 'event log plotted!'
        else:
            param.message = 'no event log'
        return param

    def ip(self, param):
        if ipaddress:
            ipaddr = ipaddress.get()
            if ipaddr:
                param.message = ipaddr
            else:
                param.message = 'cannot get IP address'
        else:
            param.message = 'ip is not available'
        return param

    def weather(self, param):
        if forecast:
            param.message = forecast.fetch_temperature()
        else:
            param.message = 'weather information is not available'
        return param

    def plot(self, param):
        if temperature:
            time, data = temperature.get_temp_time()
            if len(time) > 2:
                pngfile = tbd.temperature.plot_temperature(
                    time, data, pngfile='/tmp/temp.png')
                if pngfile:
                    param.files = [(pngfile, 'Temperature')]
                    param.message = 'plotted!'
                else:
                    param.message = 'plot is not available'
            else:
                param.message = 'no data'
        else:
            param.message = 'temperature is not available'
        return param


if __name__ == "__main__":
    ch = CommandHandler()

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
                    ch.run(command, channel)

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

            while not messages.empty():
                mes = messages.get()
                if mes.channel:
                    channel = mes.channel
                else:
                    channel = CHANNEL_ID
                log.debug('messages.get(): "%s"(channel=%s)' %
                          (mes.message, mes.channel))
                slack_client.api_call("chat.postMessage",
                                      channel=channel,
                                      text=mes.message,
                                      as_user=True)

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
                message = forecast.check_temperature()
                if message:
                    elog.log('forecast')
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
    if temperature:
        temperature.finish_polling()
