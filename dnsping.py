#!/usr/bin/env python3

import dns.flags
import dns.rdatatype
import dns.resolver
import re
import logging
log = logging.getLogger(__name__)


class Server:
    def __init__(self, nameserver='8.8.8.8', hostname='www.google.com'):
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = [nameserver]
        self.resolver.timeout = 5.0
        self.resolver.lifetime = 10.0
        self.hostname = hostname
        self.re_addr = re.compile(
            r'^(?:(?:[1-9]?\d|1\d\d|2[0-4]\d|25[0-5])\.){3}'
            r'(?:[1-9]?\d|1\d\d|2[0-4]\d|25[0-5])$')

    def is_alive(self):
        answer = self.ping()
        if self.re_addr.search(answer):
            alive = True
        else:
            alive = False
        return alive, answer

    def ping(self):
        answer = 'None'
        try:
            answers = self.resolver.query(
                self.hostname, 'A', raise_on_no_answer=False)
        except dns.resolver.NoNameservers:
            answer = "No response to dns request"
        except dns.resolver.NXDOMAIN:
            answer = "Hostname does not exist"
        except dns.resolver.Timeout:
            answer = 'Request Timeout'
        except dns.resolver.NoAnswer:
            answer = 'No answer'
        else:
            if len(answers) < 1:
                answer = 'No record'
            else:
                answer = str(answers[0])

        return answer


if __name__ == '__main__':
    dnsserver = Server(nameserver='8.8.8.8', hostname='www.google.com')
    answer = dnsserver.ping()
    print(answer)
    print(dnsserver.is_alive())
