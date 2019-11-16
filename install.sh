#!/bin/bash

install -o root -g root -m 770 -D -d /opt/tempbotd
install -o root -g root -m 640 anyping.py dnsping.py httping.py /opt/tempbotd
install -o root -g root -m 640 icmping.py weather.py eventlogger.py /opt/tempbotd
install -o root -g root -m 750 tempbotd.py /opt/tempbotd

if [ -f /opt/tempbotd/anyping-sample.conf ]; then
    echo skip install /opt/tempbotd/anyping-sample.conf
else
    install -o root -g root -m 640 anyping-sample.conf /opt/tempbotd
fi

if [ -f /etc/default/tempbot ]; then
    echo skip install /etc/default/tempbot
else
    install -o root -g root -m 600 tempbot /etc/default
fi

if [ -f /etc/systemd/system/tempbotd.service ]; then
    echo skip install /etc/systemd/system/tempbotd.service
else
    install -o root -g root -m 640 tempbotd.service /etc/systemd/system
fi


cat << EOS

Install tempbotd as systemd service
$ sudo systemctl daemon-reload

Start tempbotd service
$ sodo systemctl start tempbotd

Check tempbotd service
$ systemctl status tempbotd

Enable to start tempbotd service on system boot 
$ sudo systemctl enable tempbotd

EOS
