import requests
import dns.resolver
import time

def query_mock(*args, **kwargs):
    a_record = {
        'www.example.com': ['93.184.216.34'],
        'www.example.co.jp': dns.resolver.NXDOMAIN,
        'www.google.com': dns.resolver.Timeout,
        'one.one.one.one': ['1.1.1.1']
    }

    a = a_record.get(args[0])
    if type(a) == list:
        return a
    if type(a) == type:
        raise a

    return []


def requests_mock(*args, **kwargs):
    class responseMock():
        def __init__(self, status_code):
            self.status_code = status_code

    url_response = {
        'https://httpstat.us/200': 200,
        'https://httpstat.us/403': 403,
        'http://www.example.co.jp/': requests.exceptions.ConnectionError,
        'https://www.httpstat.us/': requests.exceptions.ConnectionError
    }

    status_code = url_response.get(args[0])
    if type(status_code) == int:
        return responseMock(status_code)
    if type(status_code) == type:
        raise status_code

    return responseMock(200)


def popen_mock(*args, **kwargs):
    response = {
        'www.example.com': """PING www.example.com (93.184.216.34) 56(84) bytes of data.
64 bytes from 93.184.216.34 (93.184.216.34): icmp_seq=1 ttl=128 time=156 ms
64 bytes from 93.184.216.34 (93.184.216.34): icmp_seq=2 ttl=128 time=148 ms
64 bytes from 93.184.216.34 (93.184.216.34): icmp_seq=3 ttl=128 time=146 ms

--- www.example.com ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms
rtt min/avg/max/mdev = 146.058/150.131/156.237/4.408 ms
""",
        'www.iana.org': """PING ianawww.vip.icann.org (192.0.32.8) 56(84) bytes of data.
64 bytes from www.iana.org (192.0.32.8): icmp_seq=1 ttl=128 time=147 ms
64 bytes from www.iana.org (192.0.32.8): icmp_seq=2 ttl=128 time=153 ms
64 bytes from www.iana.org (192.0.32.8): icmp_seq=3 ttl=128 time=147 ms

--- ianawww.vip.icann.org ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2001ms
rtt min/avg/max/mdev = 547.566/549.391/553.008/2.557 ms
""",
        '1.1.1.1': """PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.
64 bytes from 1.1.1.1: icmp_seq=1 ttl=128 time=23.3 ms
64 bytes from 1.1.1.1: icmp_seq=2 ttl=128 time=21.7 ms
64 bytes from 1.1.1.1: icmp_seq=3 ttl=128 time=22.1 ms

--- 1.1.1.1 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2022ms
rtt min/avg/max/mdev = 21.786/22.415/23.320/0.655 ms
"""
    }

    class MockPing:
        def __init__(self, returncode, response, error):
            self.returncode = returncode
            self.response = response
            self.error = error

        def communicate(self):
            return (self.response, self.error)

    ping_command = args[0]
    ping_count = ping_command[2]
    res = response.get(ping_command[3])
    if res:
        res = res.encode()
        status_code = 0
    else:
        res = 'ping: %s: Name or service not known' % ping_command[3]
        status_code = 2
    time.sleep(int(ping_count))
    return MockPing(status_code, res, None)

