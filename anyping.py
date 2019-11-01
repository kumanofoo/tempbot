#! /usr/bin/env python

import os
import json
import time

import dnsping as dp
import httping as hp

import logging
log = logging.getLogger(__name__)


class AnypingError(Exception):
    pass


class Servers():
    """
    ping some servers
    """
    def __init__(self):
        self.ANYPING_CONFIG = os.environ.get("ANYPING_CONFIG")
        if not self.ANYPING_CONFIG:
            raise AnypingError("no 'ANYPING_CONFIG' in environment variables")

        try:
            f = open(self.ANYPING_CONFIG)
        except IOError:
            raise AnypingError(
                "cannot open configuration file '{0}'".format(
                    self.ANYPING_CONFIG))

        try:
            configuration = json.load(f)
        except Exception:
            raise AnypingError("cannot parse configuration")

        if 'ping_servers' in configuration:
            self.servers = configuration['ping_servers']
        else:
            raise AnypingError("no 'ping_servers' in configuration file")

        if 'ping_interval' in configuration:
            self.interval = int(configuration['ping_interval'])
        else:
            self.interval = 60
        log.info('ping interval: {0:d} sec'.format(self.interval))

        if 'alert_delay' in configuration:
            self.alert_delay = int(configuration['alert_delay'])
        else:
            self.alert_delay = 1
        log.info('alert delay: {0:d} turn'.format(self.alert_delay))

        for server in self.servers.keys():
            prop = self.servers[server]
            if prop['type'] == 'DNS':
                prop['server'] = dp.Server(server, prop['hostname'])
            elif prop['type'] == 'Web':
                prop['server'] = hp.Server(server)
            else:
                raise AnypingError("'type of '{0}' is unknown: {1}".format(
                    server, prop['type']))

            alive, prop['message'] = prop['server'].is_alive()
            if alive:
                prop['alive'] = self.alert_delay
            else:
                prop['alive'] = 0

    def ping(self):
        log.debug("ping()")
        messages = ''
        for server in self.servers.keys():
            alive, message = self.servers[server]['server'].is_alive()
            log.debug(
                    "%s(%s:%d): %s" %
                    (server, alive, self.servers[server]['alive'], message)
                )
            server_type = self.servers[server]['type']
            if alive:
                if self.servers[server]['alive'] <= 0:
                    messages += "{0} is up\n".format(server)
                self.servers[server]['alive'] = self.alert_delay
            else:
                if self.servers[server]['alive'] >= 0:
                    self.servers[server]['alive'] -= 1

                if self.servers[server]['alive'] == 0:
                    messages += "{0} ({1}) is down: {2}\n".format(
                        server, server_type, message)

            self.servers[server]['message'] = message

        log.debug("messages: %s" % (messages))
        return messages

    def get_status_of_servers(self):
        log.debug("get_status_of_servers()")
        messages = ''
        for server in self.servers.keys():
            alive, message = self.servers[server]['server'].is_alive()
            log.debug("%s(%s): %s" % (server, alive, message))
            server_type = self.servers[server]['type']
            if alive:
                messages += "{0} ({1}) is up\n".format(server, server_type)
            else:
                messages += "{0} ({1}) is down: {2}\n".format(
                    server, server_type, message)

            self.servers[server]['message'] = message

        return messages


def main():
    servers = Servers()
    while True:
        time.sleep(servers.interval)
        messages = servers.get_status_of_servers()
        print("ping resonse: '{0}'".format(messages))

        messages = servers.ping()
        if messages:
            print(messages)


if __name__ == '__main__':
    main()
