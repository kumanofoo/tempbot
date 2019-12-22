#!/usr/bin/env python3

import os
import json
import requests
from datetime import datetime
from threading import Thread
import time
import logging
log = logging.getLogger(__name__)


class GetIPError(Exception):
    pass


class GetIP:
    def __init__(self):
        log.debug("__init__()")
        self.interval = None
        self.thread_finish = False
        self.thread = None

        self.GETIP_CONFIG = os.environ.get("GETIP_CONFIG")
        if not self.GETIP_CONFIG:
            raise GetIPError("no 'GETIP_CONFIG' in environment variables")

        try:
            f = open(self.GETIP_CONFIG)
        except IOError:
            raise GetIPError(
                "cannot open configuration file '{0}'".format(
                    self.GETIP_CONFIG))

        try:
            conf = json.load(f)
        except Exception as e:
            log.warning(e)
            raise GetIPError("cannot parse configuration")

        self.configuration = conf.get('getip', None)
        if not self.configuration:
            raise GetIPError("'getip' key not found in %s"
                             % self.GETIP_CONFIG)

        self.interval = self.configuration.get('interval', None)
        if not self.interval:
            raise GetIPError("'interval' not found")
        if type(self.interval) is not int:
            raise GetIPError("'interval' is not 'int'")
        log.debug('interval: %d sec' % self.interval)

        self.urls = self.configuration.get('urls', None)
        if not self.urls:
            raise GetIPError("'urls' not found")
        if type(self.urls) is not list:
            raise GetIPError("'urls' is not 'list'")
        log.debug('urls: %s' % self.urls)

        self.current_url = 0
        self.url = self.urls[self.current_url]
        self.current_ip = self.get()
        self.previous_ip = self.current_ip

    def __del__(self):
        self.finish_polling()

    def is_new(self):
        if self.current_ip != self.previous_ip:
            self.previous_ip = self.current_ip
            return True
        else:
            return False

    def get(self):
        log.debug("get()")
        ip = None
        for i in range(len(self.urls)):
            self.current_url = (self.current_url + 1) % len(self.urls)
            try:
                url = self.urls[self.current_url]
                res = requests.get(url)
            except Exception as e:
                log.warning(e)
            else:
                if res.status_code == 200:
                    ip = res.text
                    self.current_ip = ip
                    break
                else:
                    log.warning('%s return %d' % (url, res.status_code))

        log.debug("exit get(): %s" % ip)
        return ip

    def run(self):
        log.debug("run()")
        while not self.thread_finish:
            t1 = datetime.today()
            self.get()
            t2 = datetime.today()
            while (t2 - t1).total_seconds() < self.interval:
                if self.thread_finish:
                    break
                time.sleep(1.0)
                t2 = datetime.today()

        log.debug("exit run()")

    def start_polling(self):
        log.debug("start_polling()")

        if self.thread:
            log.warning("thread is already running")
            return False
        self.thread = Thread(target=self.run)
        self.thread_finish = False
        self.thread.start()
        log.debug("exit start_polling()")
        return True

    def finish_polling(self):
        log.debug("finish_polling()")
        if self.thread:
            self.thread_finish = True
            log.debug("waiting for thread")
            self.thread.join()
            log.debug("thread is done")
            self.thread = None
        else:
            log.debug("no running thread")
        log.debug("exit finish_polling()")


if __name__ == '__main__':
    log_level = logging.DEBUG
    formatter = '%(asctime)s %(name)s[%(lineno)s] %(levelname)s: %(message)s'
    logging.basicConfig(level=log_level, format=formatter)

    ip = GetIP()
    ip.start_polling()
    for i in range(5):
        print(ip.is_new(), ip.current_ip)
        time.sleep(10)
    ip.finish_polling()
