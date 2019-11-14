# tempbot
[![reelase](https://img.shields.io/github/v/release/kumanofoo/tempbot)](https://github.com/kumanofoo/tempbot)

## Requirements
### python
- slackclient
- websocket-client
- dnspython
- matplotlib
- pytest

### temperature sensor
- DS18B20


### slack
- Hubot API token
- Channel ID
- Bot ID

### Dark Sky
- Secret Key


## Installation
```ShellSession
$ git clone https://github.com/kumanofoo/tempbot.git
$ cd tempbot
$ sudo ./install.sh
$ sudo vi /etc/default/tempbot
$ sudo vi /opt/tempbotd/anyping.conf
$ sudo systemctl enable tempbotd
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

## Docker
### Requirements
- docker
- test/test.env

Copy tempbot to test/test.env
```Shellsession
$ cp tempbot test/test.env
```
Edit test/test.env
```Shell
# your Hubot API Token
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxx-YYYYYYYYYYYYYYYYYYYYYYYY

# watching channel 
CHANNEL_ID=XXXXXXXXX

# your Hubot ID
BOT_ID=YYYYYYYYY


# dummy temprature sensor
T_SENSOR_PATH=test/w1_slave

ANYPING_CONFIG=/opt/tempbotd/anyping.conf


# your Dark Sky Key
DARK_SKY_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# weather forecast place latitude:longitude
MY_PLACE=35.3625:138.7306
```

### Run tempbotd.py
```Shellsession
$ bash test/run.sh
```

### Test
```Shellsession
$ bash test/run.sh test
```