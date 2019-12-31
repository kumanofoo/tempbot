#!/usr/bin/env python3

"""
Full Stack Python
How to Build Your First Slack Bot With Python
https://www.fullstackpython.com/blog/build-first-slack-bot-python.html
"""
import os
import re
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


def upload_file(file_path, title='temperature', channel=CHANNEL_ID):
    with open(file_path, 'rb') as f:
        param = {'token': os.environ.get('SLACK_BOT_TOKEN'),
                 'channels': channel, 'title': title}
        r = requests.post("https://slack.com/api/files.upload",
                          params=param, files={'file': f})
        log.debug(r)


def handle_command(command, channel):
    """
        Receives commands directed at the bot and determins if they
        are valid commands. if so, then acts on the commands. if not,
        returns back what it needs for clarification.
    """
    if temperature:
        tmpr = temperature.get_temperature()
        if tmpr:
            response = '%.1f °C' % (tmpr)
        else:
            response = 'no sensor'
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
        if temperature:
            time, data = temperature.get_temp_time()
            if len(time) > 2:
                pngfile = tbd.temperature.plot_temperature(
                    time, data, pngfile='/tmp/temp.png')
                if pngfile:
                    upload_file(pngfile, title='Temperature')
                    response = 'plotted!'
                else:
                    response = 'plot is not available'
            else:
                response = 'no data'
        else:
            response = 'temperature is not available'
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
                if not book.searching:
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


if __name__ == "__main__":
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
        ipaddress = tbd.getip.GetIP()
        ipaddress.start_polling()
    except tbd.getip.GetIPError as e:
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
                slack_client.api_call("chat.postMessage",
                                      channel=CHANNEL_ID,
                                      text=messages.get(),
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
