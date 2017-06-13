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
from slackclient import SlackClient

# tempbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")
if not BOT_ID:
    sys.stderr.write('no environment variable BOT_ID\n')
    exit()

CHANNEL_ID = os.environ.get("CHANNEL_ID")
if not CHANNEL_ID:
    sys.stderr.write('no environment variable CHANNEL_ID\n')
    exit()
    
T_SENSOR_PATH = os.environ.get("T_SENSOR_PATH")


# constants
AT_BOT = "<@" + BOT_ID + ">"
EXAMPLE_COMMAND = "do"
COMMAND_HEY = "hey"
COMMAND_OK = "ok"
COMMAND_HELLO = "hello"
COMMAND_TIME = "time"
COMMAND_DATE = "date"
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


def handle_command(command, channel):
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
        self.pre_temp = get_temperature()

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
                warning = "_Overheating!!! (" + str(cur_temp) + "°C_)"
                slack_client.api_call("chat.postMessage",
                                      channel=CHANNEL_ID,
                                      text=warning,
                                      as_user=True)
                self.is_hot = True
        else:
            if self.is_hot:
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



if __name__ == "__main__":
    temperature = Temperature()

    READ_WEBSOCKET_DELAY = 2 # 2 second delay between reading from firehose
    if slack_client.rtm_connect():
        print("Temperature Bot connected and running!")
        tmpr = get_temperature()
        if tmpr == -100:
            print("without temperature sensor...")

        while True:
            try:
                command, channel = parse_slack_output(slack_client.rtm_read())
                if command and channel:
                    handle_command(command, channel)

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
    else:
        sys.stderr.write("Connection failed. Invalid Slack token or bot ID?")

