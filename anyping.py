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

        for server in self.servers.keys():
            prop = self.servers[server]
            if prop['type'] == 'DNS':
                prop['server'] = dp.Server(server, prop['hostname'])
            elif prop['type'] == 'Web':
                prop['server'] = hp.Server(server)
            else:
                raise AnypingError("'type of '{0}' is unknown: {1}".format(
                    server, prop['type']))

            prop['alive'], prop['message'] = prop['server'].is_alive()

    def ping(self):
        messages = ''
        for server in self.servers.keys():
            alive, message = self.servers[server]['server'].is_alive()
            server_type = self.servers[server]['type']
            if alive:
                if not self.servers[server]['alive']:
                    messages += "{0} is up\n".format(server)
            else:
                if self.servers[server]['alive']:
                    messages += "{0} ({1}) is down: {2}\n".format(
                        server, server_type, message)

            self.servers[server]['alive'] = alive
            self.servers[server]['message'] = message

        return messages

    def get_status_of_servers(self):
        messages = ''
        for server in self.servers.keys():
            alive, message = self.servers[server]['server'].is_alive()
            server_type = self.servers[server]['type']
            if alive:
                messages += "{0} ({1}) is up\n".format(server, server_type)
            else:
                messages += "{0} ({1}) is down: {2}\n".format(
                    server, server_type, message)

            self.servers[server]['alive'] = alive
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
