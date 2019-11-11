# tempbot

## Requirements
### python
- slackclient
- dnspython
- websocket-client
- matplotlib

## Installation
```ShellSession
$ git clone https://github.com/kumanofoo/tempbot.git
$ cd tempbot
$ sudo mkdir /opt/tempbotd
$ sudo cp anyping.py dnsping.py httping.py icmping.py tempbotd.py weather.py /opt/tempbotd
$ sudo cp anyping-sample.conf /opt/tempbotd/anyping.conf
$ sudo cp tempbot /etc/default
$ sudo vi /etc/default/tempbot
$ sudo cp tempbotd.service /etc/systemd/system
$ sudo systemctl enable tempbotd
$ sudo systemctl start tempbotd
$ sudo systemctl status tempbotd
```

## Test
```ShellSession
$ env $(grep -v "^#" ./tempbot) python3 -m pytest test
```

## Docker
### Build image
```Shellsession
$ cd test
$ docker image build -t tempbot .
```

### Run
```Shellsession
$ cd test
$ docker run --env-file=../tempbot -it tempbot /bin/bash
```