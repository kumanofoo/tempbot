#! /usr/bin/env python3

import os
import json
import time

import dnsping as dp
import httping as hp
import icmping as ip

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

        if 'icmp_sample_count' in configuration:
            icmp_sample_count = configuration['icmp_sample_count']
        else:
            icmp_sample_count = 20

        if 'icmp_interval' in configuration:
            icmp_interval = configuration['icmp_interval']
        else:
            icmp_interval = 120  # [sec]

        if 'icmp_rotate' in configuration:
            icmp_rotate = configuration['icmp_rotate']
        else:
            icmp_rotate = 48  # [h]

        if 'icmp_hosts' in configuration:
            icmp_hosts = configuration['icmp_hosts']
        else:
            icmp_hosts = None

        if 'icmp_file_prefix' in configuration:
            self.icmp_file_prefix = configuration['icmp_file_prefix']
        else:
            self.icmp_file_prefix = None

        for host in icmp_hosts:
            log.debug("icmp host=%s" % host)
            try:
                ips = ip.Server(host=host, sample_count=icmp_sample_count,
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
