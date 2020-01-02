#! /usr/bin/env python3

import os
import json
import time

from . import dnsping as dp
from . import httping as hp
from . import icmping as ip

import logging
log = logging.getLogger(__name__)


class AnypingError(Exception):
    pass


class Servers():
    """
    ping some servers
    """
    def __init__(self):
        self.icmp_servers = []

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
            conf = json.load(f)
        except Exception:
            raise AnypingError("cannot parse configuration")

        self.configuration = conf.get('anyping', None)
        if not self.configuration:
            raise AnypingError("'anyping' key not found in %s"
                               % self.ANYPING_CONFIG)

        self.servers = self.configuration.get('ping_servers', None)
        if not self.servers:
            raise AnypingError("no 'ping_servers' in configuration file")

        self.interval = self.configuration.get('ping_interval', None)
        if not self.interval:
            raise AnypingError("'interval' not found")
        if type(self.interval) is not int:
            raise AnypingError("'interval' is not 'int'")
        log.debug('interval: %d sec' % self.interval)

        self.alert_delay = self.configuration.get('alert_delay', None)
        if not self.alert_delay:
            raise AnypingError("'alert_delay' not found")
        if type(self.alert_delay) is not int:
            raise AnypingError("'alert_delay' is not 'int'")
        log.debug('alert_delay: %d times' % self.interval)

        for server in self.servers.keys():
            log.debug("server=%s" % server)
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

        icmp_sample_size = self.configuration.get('icmp_sample_size')
        if not icmp_sample_size:
            raise AnypingError("'icmp_sample_size' not found")
        log.debug('icmp_sample_size: %d ' % icmp_sample_size)

        icmp_interval = self.configuration.get('icmp_interval')  # [sec]
        if not icmp_interval:
            raise AnypingError("'icmp_interval' not found")
        log.debug('icmp_interval: %d ' % icmp_interval)

        icmp_rotate = self.configuration.get('icmp_rotate')  # [h]
        if not icmp_rotate:
            raise AnypingError("'icmp_rotate' not found")
        log.debug('icmp_rotate: %d ' % icmp_rotate)

        icmp_hosts = self.configuration.get('icmp_hosts', None)
        log.debug('icmp_hosts: %s ' % icmp_hosts)

        self.icmp_file_prefix = self.configuration.get('icmp_file_prefix',
                                                       None)
        log.debug('icmp_file_prefix: %s ' % self.icmp_file_prefix)

        for host in icmp_hosts:
            log.debug("icmp host=%s" % host)
            try:
                ips = ip.Server(host=host, sample_count=icmp_sample_size,
                                interval=icmp_interval,
                                rotate=icmp_rotate)
            except Exception as e:
                raise AnypingError(e)
            else:
                self.icmp_servers.append(ips)

        for icmp_server in self.icmp_servers:
            icmp_server.start()

    def __del__(self):
        if self.icmp_servers:
            for server in self.icmp_servers:
                server.finish()

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

        log.debug("exit get_status_of_servers()")
        return messages

    def save_icmp_results(self):
        log.debug("save_icmp_results()")
        outfiles = []
        if self.icmp_servers:
            if self.icmp_file_prefix:
                filename = "%s_all.png" % (self.icmp_file_prefix)
                if ip.save_results(self.icmp_servers, filename=filename):
                    outfiles.append((filename, "all"))
                n = 0
                for server in self.icmp_servers:
                    filename = "%s_%d.png" % (self.icmp_file_prefix, n)
                    if server.save(filename=filename):
                        outfiles.append((filename, server.host))
                    n += 1
            else:
                log.warning("no icmp_file_prefix")
        else:
            log.warning("no icmp hosts")

        log.debug("exit save_icmp_results()")
        return outfiles


def main():
    servers = Servers()
    for i in range(3):
        time.sleep(servers.interval)
        messages = servers.get_status_of_servers()
        print("ping resonse: '{0}'".format(messages))

        messages = servers.ping()
        if messages:
            print(messages)

        out = servers.save_icmp_results()
        print("save as:", out)


if __name__ == '__main__':
    """
    for debug
    """
    log_level = logging.DEBUG
    formatter = '%(asctime)s %(name)s[%(lineno)s] %(levelname)s: %(message)s'
    logging.basicConfig(level=log_level, format=formatter)

    main()
