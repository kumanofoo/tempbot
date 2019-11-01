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
$ sudo cp anyping.py dnsping.py httping.py tempbotd.py weather.py /opt/tempbotd
$ sudo cp anyping-sample.conf /usr/local/etc/anyping.conf
$ sudo cp tempbot /etc/default
$ sudo vi /etc/default/tempbot
$ sudo cp tempbotd.service /etc/systemd/system
$ sudo systemctl enable tempbotd
$ sudo systemctl start tempbotd
$ sudo systemctl status tempbotd
```

