#!/bin/bash

install -o root -g root -m 770 -D -d /opt/tempbotd
install -o root -g root -m 640 anyping.py dnsping.py httping.py icmping.py weather.py /opt/tempbotd
install -o root -g root -m 750 tempbotd.py /opt/tempbotd

if [ ! -f /opt/tempbotd/anyping.conf ]; then
    install -o root -g root -m 640 anyping-sample.conf /opt/tempbotd/anyping.conf
fi

if [ ! -f /etc/default/tempbot ]; then
    install -o root -g root -m 600 tempbot /etc/default
fi

if [ ! -f /etc/systemd/system/tempbotd.service ]; then
    install -o root -g root -m 640 tempbotd.service /etc/systemd/system
fi

type systemctl &> /dev/null
if [ $? = 0 ]; then
    systemctl enable tempbotd
fi

