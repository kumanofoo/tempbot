#!/usr/bin/env python3

import time
from datetime import datetime
import subprocess
from threading import Thread

import matplotlib
matplotlib.use("Agg") # noqa
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import logging
log = logging.getLogger(__name__)


class PingError(Exception):
    pass


class Server:
    """
    icmp ping
    """

    def __init__(self, host="www.example.com",
                 sample_count=20, interval=120, rotate=48):
        log.debug("__init__(host=%s, sample_count=%d, interval=%d, rotate=%d)"
                  % (host, sample_count, interval, rotate))
        self.host = host
        self.count = sample_count
        self.interval = interval
        self.results = {}
        self.results['datetime'] = []
        self.results['min'] = []
        self.results['avg'] = []
        self.results['max'] = []
        self.thread = None
        # self.results['stddev'] = []
        self.thread_finish = False
        self.rotate = rotate*60*60/interval
        log.debug("self.rotate=%d" % self.rotate)

        # because of checking error, do ping once
        self.onetime_ping()
        log.debug("exit __init__()")

    def __del__(self):
        self.finish()

    def onetime_ping(self):
        log.debug("onetime_ping()")
        ping = subprocess.Popen(["ping", "-c", "3", self.host],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        response, error = ping.communicate()
        if ping.returncode >= 2:
            raise PingError("cannot ping to host '{0}'".format(self.host))
        log.debug("exit onetime_ping()")

    def ping(self):
        log.debug("ping()")
        error_count = 0
        error_datetime = None
        while not self.thread_finish:
            t1 = datetime.today()
            log.debug("ping -c %d %s" % (self.count, self.host))
            ping = subprocess.Popen(["ping", "-c", str(self.count), self.host],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            response, error = ping.communicate()
            log.debug("ping.returncode(%s)=%d" % (self.host, ping.returncode))
            if ping.returncode == 0:
                stat = response.decode('utf-8').split("\n")[-2].split("/")
                self.results['min'].append(float(stat[-4].split(" ")[-1]))
                self.results['avg'].append(float(stat[-3]))
                self.results['max'].append(float(stat[-2]))
                # self.results['stddev'].append(float(stat[-1].split(" ")[0]))
                self.results['datetime'].append(datetime.today())
                error_count = 0
                error_datetime = None
            elif ping.returncode == 1:
                self.results['min'].append(None)
                self.results['avg'].append(None)
                self.results['max'].append(None)
                # self.results['stddev'].append(None)
                self.results['datetime'].append(datetime.today())
            else:
                self.results['min'].append(None)
                self.results['avg'].append(None)
                self.results['max'].append(None)
                # self.results['stddev'].append(None)
                self.results['datetime'].append(datetime.today())
                if error_count == 0:
                    today = datetime.today()
                    error_datetime = today.strftime('%Y/%m/%d %H:%M:%S')
                    log.warning("cannot ping to host '%s'" % (self.host))
                    log.warning(error.decode('utf-8'))
                elif error_count % 10 == 0:
                    log.warning("cannot ping to host '%s' from %s" %
                                (self.host, error_datetime))
                    log.warning(error.decode('utf-8'))
                error_count += 1

            if len(self.results['datetime']) > self.rotate:
                self.results['min'].pop(0)
                self.results['avg'].pop(0)
                self.results['max'].pop(0)
                # self.results['stddev'].pop(0)
                self.results['datetime'].pop(0)

            t2 = datetime.today()
            while (t2 - t1).total_seconds() < self.interval:
                if self.thread_finish:
                    break
                time.sleep(1.0)
                t2 = datetime.today()
        log.debug("exit ping()")

    def start(self):
        log.debug("start(%s)" % self.host)
        if self.thread:
            log.warning("thread is already running")
            return

        self.thread = Thread(target=self.ping)
        self.thread_finish = False
        self.thread.start()
        log.debug("exit start()")

    def finish(self):
        log.debug("finish(%s)" % self.host)
        if self.thread:
            self.thread_finish = True
            self.thread.join()
            self.thread = None
        else:
            log.debug("no running thread")
        log.debug("exit finish()")

    def save(self, filename="ping.png", linecolor='#0000ff'):
        log.debug("save(filename=%s, linecolor=%s)" % (filename, linecolor))
        results_len = len([x for x in self.results['avg'] if x is not None])
        if results_len < 2:
            log.info('skip traffic plot because %s has too few data(%d)' %
                     (self.host, results_len))
            return None

        fig = plt.figure(figsize=(15, 4))
        ax = fig.add_subplot(1, 1, 1)

        ax.set_xlim(self.results['datetime'][0], self.results['datetime'][-1])
        m = max(i for i in self.results['max'] if i is not None)
        if float(m) < 10.0:
            m = 10.0
        ax.set_ylim(0.0, int(m/100.0+0.9)*100.0)
        ax.plot(self.results['datetime'], self.results['avg'],
                c=linecolor, alpha=1.0)
        ax.plot(self.results['datetime'], self.results['min'],
                c=linecolor, alpha=0.4, linestyle='dotted')
        ax.plot(self.results['datetime'], self.results['max'],
                c=linecolor, alpha=0.4, linestyle='dotted')
        ax.set_title("ping to %s" % (self.host))
        ax.set_ylabel("ms")
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.grid()

        ax.tick_params(left=False, bottom=False)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)

        plt.savefig(filename, transparent=False, bbox_inches='tight')
        plt.close(fig)
        log.debug("exit save()")
        return filename


def save_results(servers, filename="ping.png", title="ping"):
    log.debug("save_results(servers=%s, filename=%s, title=%s)" %
              (servers, filename, title))
    color_map = ['#00a0e9', '#e4007f', '#009944', '#f39800', '#0068b7']
    current_color = 0
    is_canvas_clean = True
    outfile = None

    fig = plt.figure(figsize=(15, 4))
    ax = fig.add_subplot(1, 1, 1)

    start_date = None
    end_date = None
    for server in servers:
        results_len = len([x for x in server.results['avg'] if x is not None])
        if results_len < 2:
            log.info('skip traffic plot because %s has too few data(%d)' %
                     (server.host, results_len))
            continue
        if not start_date:
            start_date = server.results['datetime'][0]
        else:
            if start_date > server.results['datetime'][0]:
                start_date = server.results['datetime'][0]

        if not end_date:
            end_date = server.results['datetime'][-1]
        else:
            if end_date < server.results['datetime'][-1]:
                end_date = server.results['datetime'][-1]

    if start_date != end_date:
        ax.set_xlim(start_date, end_date)
    ax.set_ylim(0, 1000)

    for server in servers:
        if len([x for x in server.results['avg'] if x is not None]) < 2:
            continue

        c = color_map[current_color]
        ax.plot(server.results['datetime'], server.results['avg'],
                c=c, alpha=1.0)
        ax.plot(server.results['datetime'], server.results['min'],
                c=c, alpha=0.4, linestyle='dotted')
        ax.plot(server.results['datetime'], server.results['max'],
                c=c, alpha=0.4, linestyle='dotted')

        text_ypos = server.results['avg'][-1]
        if text_ypos is None:
            text_ypos = 990.0
        ax.text(end_date, text_ypos, ' ' + server.host, color=c, va='center')

        is_canvas_clean = False

        current_color += 1
        if current_color >= len(color_map):
            current_color = 0

    if not is_canvas_clean:

        ax.set_title(title)
        ax.set_ylabel("ms")
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.grid()

        ax.tick_params(left=False, bottom=False)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)

        plt.savefig(filename, transparent=False, bbox_inches='tight')
        outfile = filename

    plt.close(fig)
    log.debug("exit save_results()")
    return outfile


if __name__ == '__main__':
    """
    for debug
    """
    log_level = logging.DEBUG
    formatter = '%(asctime)s %(name)s[%(lineno)s] %(levelname)s: %(message)s'
    logging.basicConfig(level=log_level, format=formatter)

    hosts = [
        'www.example.com',
        'www.google.com',
    ]
    ping = []
    for host in hosts:
        print(host, flush=True)
        try:
            # interval [sec], routate [hour]
            p = Server(host=host, sample_count=10, interval=30, rotate=1)
        except Exception as e:
            print(e)
            exit(0)
        else:
            ping.append(p)

    for p in ping:
        p.start()

    for i in range(5):
        time.sleep(60)
        n = 0
        for p in ping:
            p.save(filename="ping%d.png" % n)
            n += 1
        save_results(ping, filename="ping_all.png")
        print("\r%s" % i, end="")

    for p in ping:
        p.finish()

    print('ping done')
