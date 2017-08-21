#! /usr/bin/python -u
# -*- coding: utf-8 -*-

"""
Full Stack Python
How to Build Your First Slack Bot With Python
https://www.fullstackpython.com/blog/build-first-slack-bot-python.html
"""
import os
import sys
import time
import datetime
import websocket
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from slackclient import SlackClient
import requests

import anyping as ap

# tempbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")
if not BOT_ID:
    sys.stderr.write('no environment variable BOT_ID\n')
    exit(1)

CHANNEL_ID = os.environ.get("CHANNEL_ID")
if not CHANNEL_ID:
    sys.stderr.write('no environment variable CHANNEL_ID\n')
    exit(1)
    
T_SENSOR_PATH = os.environ.get("T_SENSOR_PATH")


# constants
AT_BOT = "<@" + BOT_ID + ">"
COMMAND_TIME = "time"
COMMAND_DATE = "date"
COMMAND_PLOT = "plot"
COMMAND_PING = "ping"
TEMP_TO_ALERT = 30

COMMAND_CHAT = {
    "hey":"Siri!",
    "ok":"Google!",
    "hello":"World!",
    "do":"Sure...write some more code then i can do that!",
}



# instantiate Slack & Twilio clients
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))


def get_temperature():
    temp = -100
    try:
        with open(T_SENSOR_PATH) as f:
            data = f.read()
            temp = int(data[data.index('t=')+2:])/1000
    except IOError as e:
        pass

    return temp


def upload_file(file_path):
    with open(file_path, 'rb') as f:
        param = {'token':os.environ.get('SLACK_BOT_TOKEN'),
                 'channels':CHANNEL_ID, 'title':'temperature'}
        r = requests.post("https://slack.com/api/files.upload",
                          params=param, files={'file':f})




def plot_temperature(time, data):
    fig = plt.figure(figsize=(15, 4))
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(time, data, c='#0000ff', alpha=0.7)
    ax.set_title('temerature')
    ax.set_ylim(0, 50)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.grid()
    plt.savefig('/tmp/temp.png', transparent=False, bbox_inches='tight')
    upload_file('/tmp/temp.png')


    
def handle_command(command, channel, temperature, pingservers):
    """
        Receives commands directed at the bot and determins if they
        are valid commands. if so, then acts on the commands. if not,
        returns back what it needs for clarification.
    """
    tmpr = get_temperature()
    if tmpr == -100:
        response = 'no sensor'
    else:
        response = str(tmpr) + '°C'

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
            plot_temperature(time, data)
            response = 'plotted!'
        else:
            response = 'no data'
    if command.startswith(COMMAND_PING):
        response = pingservers.get_status_of_servers()


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


class Temperature:
    def __init__(self):
        self.delay = 15
        self.is_hot = False
        self.tempdata = []
        self.timedata = []
        self.pre_temp = get_temperature()
        self.temp_sum = 0
        self.temp_n = 0

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
        if cur_temp > TEMP_TO_ALERT:
            if not self.is_hot:
                print("Overheating!!!")
                warning = "_Overheating!!! (" + str(cur_temp) + "°C)_"
                slack_client.api_call("chat.postMessage",
                                      channel=CHANNEL_ID,
                                      text=warning,
                                      as_user=True)
                self.is_hot = True
        else:
            if self.is_hot and cur_temp < TEMP_TO_ALERT:
                print("It's cool!")
                warning = "It's cool! (" + str(cur_temp) + "°C)"
                slack_client.api_call("chat.postMessage",
                                      channel=CHANNEL_ID,
                                      text=warning,
                                      as_user=True)
                self.is_hot = False


    def checkTemperature(self):
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


if __name__ == "__main__":
    temperature = Temperature()
    pingservers = ap.Servers()

    READ_WEBSOCKET_DELAY = 2 # 2 second delay between reading from firehose
    PING_INTERVAL_TIMER = int(pingservers.interval/READ_WEBSOCKET_DELAY)

    if slack_client.rtm_connect():
        print("Temperature Bot connected and running!")
        tmpr = get_temperature()
        if tmpr == -100:
            print("without temperature sensor...")

        ping_timer = PING_INTERVAL_TIMER
        while True:
            try:
                command, channel = parse_slack_output(slack_client.rtm_read())
                if command and channel:
                    handle_command(command, channel, temperature, pingservers)

                temperature.checkTemperature()
                time.sleep(READ_WEBSOCKET_DELAY)
            except websocket.WebSocketConnectionClosedException as e:
                sys.stderr.write(e)
                sys.stderr.write('Caught websocket disconnect, reconnecting...')
                time.sleep(READ_WEBSOCKET_DELAY)
                while not slack_client.rtm_connect():
                    sys.stderr.write('Caught websocket disconnect, reconnecting...')
                    time.sleep(READ_WEBSOCKET_DELAY)
                warning = "I'm back!"
                slack_client.api_call("chat.postMessage",
                                      channel=CHANNEL_ID,
                                      text=warning,
                                      as_user=True)
            except Exception, e:
                print(e)
                time.sleep(READ_WEBSOCKET_DELAY)

            ping_timer -= 1
            if ping_timer == 0:
                ping_timer = PING_INTERVAL_TIMER
                message = pingservers.ping()
                if message:
                    slack_client.api_call("chat.postMessage",
                                          channel=CHANNEL_ID,
                                          text=message,
                                          as_user=True)


    else:
        sys.stderr.write("Connection failed. Invalid Slack token or bot ID?")

