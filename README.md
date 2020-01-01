# tempbot
[![reelase](https://img.shields.io/github/v/release/kumanofoo/tempbot)](https://github.com/kumanofoo/tempbot/releases)
[![CircleCI](https://circleci.com/gh/kumanofoo/tempbot.svg?style=shield)](https://circleci.com/gh/kumanofoo/tempbot)

## Requirements
### python
- slackclient(=1.3.2)
- websocket-client
- dnspython
- matplotlib
- Beautiful Soup 4

### test
- pytest
- pytest-mock
- pytest-cov

### temperature sensor
- DS18B20


### slack
- Hubot API token
- Channel ID
- Bot ID

### Dark Sky
- Secret Key

### calil
- Appkey

## Installation
```ShellSession
$ git clone https://github.com/kumanofoo/tempbot.git
$ cd tempbot
$ sudo bash ./install.sh install
$ sudo vi /etc/default/tempbot
$ sudo cp /opt/tempbotd/tempbot-sample.conf /opt/tempbotd/tempbot.conf
$ sudo vi /opt/tempbotd/tempbot.conf
$ sudo systemctl enable tempbotd    # automatically start on boot
```

If you want to uninstall tempbot, run install.sh with 'uninstall'.
```ShellSession
$ sudo bash ./install.sh uninstall
```

## Run tempbotd
```ShellSession
$ sudo systemctl start tempbotd
$ sudo systemctl status tempbotd
```

## Stop tempbotd
```ShellSession
$ sudo systemctl stop tempbotd
$ sudo systemctl status tempbotd
```

## Test on Docker
### Requirements
- docker
- tests/test.env

Copy tempbot to tests/test.env
```Shellsession
$ cp tempbot tests/test.env
```
Edit tests/test.env
```Shell
# your Hubot API Token
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxx-YYYYYYYYYYYYYYYYYYYYYYYY

# watching channel 
CHANNEL_ID=XXXXXXXXX

# your Hubot ID
BOT_ID=YYYYYYYYY

# dummy temprature sensor
T_SENSOR_PATH=tests/w1_slave

# configuration files
ANYPING_CONFIG=/opt/tempbotd/tempbot.conf
BOOK_CONFIG=/opt/tempbotd/tempbot.conf
GETIP_CONFIG=/opt/tempbotd/tempbot.conf
TEMPBOT_CONFIG=/opt/tempbotd/tempbot.conf

# weather forecast place latitude:longitude
MY_PLACE=35.3625:138.7306

# your calil appkey
CALIL_APPKEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

TZ=Asia/Tokyo
PYTHONDONTWRITEBYTECODE=1
TEMPBOT_DEBUG=debug
```

### Run tempbotd.py
```Shellsession
$ bash ./install.sh run
```

### Test
```Shellsession
$ bash ./install.sh test
```
