#!/usr/bin/env python3

import requests
import time


class Server:
    down = 1
    up = 2

    def __init__(self, url):
        self.url = url
        self.timeout = 3
        self.server_status = self.down
        if self.get_status() == 200:
            self.server_status = self.up

    def is_alive(self):
        response = self.get_status()
        if response == 200:
            alive = True
        else:
            alive = False

        return alive, response

    def get_status(self):
        status_code = -1
        try:
            response = requests.get(self.url, timeout=self.timeout)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout):
            status_code = 500
        else:
            status_code = response.status_code

        return status_code


if __name__ == "__main__":
    urls = [
        'http://www.google.com/',
        'https://www.google.co.jp/',
    ]
    servers = []
    for server in urls:
        servers.append(Server(server))
    while (True):
        for server in servers:
            print(server.url, server.is_alive())
        time.sleep(60)
