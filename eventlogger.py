#!/usr/bin/env python3

from datetime import datetime
import matplotlib
matplotlib.use("Agg") # noqa
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import logging
log = logging.getLogger(__name__)


class EventLoggerError(Exception):
    pass


class EventLogger:
    """
    log event and plot
    """

    def __init__(self, buffer_size=32):
        log.debug("__init__(buffer_size=%d)" % (buffer_size))

        self.eventlog = {}
        self.buffer_size = buffer_size

        log.debug("exit __init__()")

    def log(self, category):
        log.debug("log(category=%s)" % (category))

        if category not in self.eventlog:
            self.eventlog[category] = []
        self.eventlog[category].append(datetime.today())
        if len(self.eventlog[category]) > self.buffer_size:
            self.eventlog[category].pop(0)

        log.debug("exit log()")

    def save(self, filename="event_log.png", category=None, title="event"):
        log.debug("save(filename=%s, category=%s)" % (filename, category))

        if not self.eventlog:
            log.warning("event log is empty")
            log.debug("exit save()")
            return None

        color_map = ['#00a0e9', '#e4007f', '#009944', '#f39800', '#0068b7']

        categories = self.eventlog.keys()
        if category:
            if category not in self.eventlog:
                log.warning("category '%s' not found" % category)
                log.debug("exit save()")
                return None
            else:
                categories = [category]

        fig = plt.figure(figsize=(15, 4))
        ax = fig.add_subplot(1, 1, 1)

        start_date = None
        end_date = None
        cat_n = 0
        yticks = [""]
        for cat in categories:
            if not start_date:
                start_date = self.eventlog[cat][0]
                end_date = self.eventlog[cat][-1]
            if start_date > self.eventlog[cat][0]:
                start_date = self.eventlog[cat][0]
            if end_date < self.eventlog[cat][-1]:
                end_date = self.eventlog[cat][-1]

            n = len(self.eventlog[cat])
            color_n = cat_n % len(color_map)
            ax.scatter(self.eventlog[cat], [cat_n+1]*n, c=color_map[color_n])
            yticks.append(cat)
            cat_n += 1

        if start_date != end_date:
            ax.set_xlim(start_date, end_date)
        ax.set_yticks(range(cat_n+2))
        ax.set_yticklabels(yticks)
        ax.set_ylim(0, cat_n+1)

        ax.set_title(title)
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


if __name__ == '__main__':
    import time
    import random

    """
    for debug
    """
    log_level = logging.DEBUG
    formatter = '%(asctime)s %(name)s[%(lineno)s] %(levelname)s: %(message)s'
    logging.basicConfig(level=log_level, format=formatter)

    fruits = ["apple", "banana", "cherry", "durian",
              "elderberry", "fig", "grape"]
    elog = EventLogger(buffer_size=32)

    count = 30
    for i in range(count):
        print('%d/%d' % (i, count))
        r = random.uniform(0.0, 3.0)
        time.sleep(r)
        for e in fruits:
            if random.random() < 0.3:
                elog.log(e)

    elog.save()
