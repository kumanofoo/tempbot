#!/usr/bin/env python3

import time
import re
import os
from threading import Thread
import json
import random
import queue
import bs4
import requests

import logging
log = logging.getLogger(__name__)

ZEN = "".join(chr(0xff01 + i) for i in range(94))
HAN = "".join(chr(0x21 + i) for i in range(94))
ZEN2HAN = str.maketrans(ZEN, HAN)


class BookStatusError(Exception):
    pass


class BookStatus:
    """
    check book's status in libraries
    """
    def __init__(self, q):
        self.thread = None
        self.abort = False
        self.searching = False
        self.messages = q

        self.CALIL_APPKEY = os.environ.get("CALIL_APPKEY")
        if not self.CALIL_APPKEY:
            raise BookStatusError("no 'CALIL_APPKEY' in environment variables")

        self.BOOK_CONFIG = os.environ.get("BOOK_CONFIG")
        if not self.BOOK_CONFIG:
            raise BookStatusError("no 'BOOK_CONFIG' in environment variables")

        try:
            f = open(self.BOOK_CONFIG)
        except IOError:
            raise BookStatusError(
                "cannot open configuration file '{0}'".format(
                    self.BOOK_CONFIG))

        try:
            conf = json.load(f)
        except Exception as e:
            log.warning(e)
            raise BookStatusError("cannot parse configuration")

        self.configuration = conf.get('book', None)
        if not self.configuration:
            raise BookStatusError("'book' key not found in %s"
                                  % self.BOOK_CONFIG)

        self.libraries = self.configuration.keys()
        if len(self.libraries) == 0:
            raise BookStatusError("library not found in %s"
                                  % self.BOOK_CONFIG)
        log.debug('libraries: %s' % self.libraries)

    def __del__(self):
        if self.thread:
            self.abort = True
            self.thread.join()
            self.searching = False
            self.thread = None

    def get_isbn_c(self, book, max_count=5):
        log.debug('get_isbn_c(%s, %d)' % (book, max_count))
        url = 'https://api.calil.jp/openurl'
        params = {
            'title': book
        }
        isbns = {}
        book_link = []
        try:
            res = requests.get(url, params=params)
        except Exception as e:
            log.warning(e)
            return None
        else:
            if res.status_code != 200:
                log.warning('%s return %d' % (url, res.status_code))
                return None

        soup = bs4.BeautifulSoup(res.text, features='html.parser')
        title = soup.find_all('div', class_='title')
        book_han = book.translate(ZEN2HAN).lower().split()
        for t in title:
            log.debug("%s (%s)" % (t.a.string.strip(), t.a['id']))
            if not t.a:
                continue
            if t.a['id'] == 'link':
                continue
            t_han = t.a.string.strip().translate(ZEN2HAN).lower().split()
            t_han.append('')  # sentinel
            match = True
            if not re.match(r'^\d{10}$', book.translate(ZEN2HAN)):  # not ISBN
                for b in book_han:
                    if t_han.pop(0) != b:
                        match = False
                        break
            if match:
                book_link.append((t.a.string.strip(),
                                 'https://calil.jp' + t.a.get('href')))

        for title, link in book_link[:max_count]:
            if self.abort:
                log.warning('abort get_isbn_d()')
                return None
            try:
                res = requests.get(link)
            except Exception as e:
                log.warning(e)
                return None
            else:
                if res.status_code != 200:
                    log.warning('%s return %d' % (link, res.status_code))
                    return None

            soup = bs4.BeautifulSoup(res.text, features='html.parser')
            description = soup.find_all('div', itemprop='description')
            for d in description:
                for line in d.text.split('\n'):
                    pattern = r'ISBN-10\D+(\d{9}[0-9Xx])\D*'
                    result = re.match(pattern, line)
                    if result:
                        isbns[result.group(1)] = title

        log.debug('get_isbn_c(): %s' % isbns)
        return isbns

    def get_isbn_h(self, book, max_count=5):
        log.debug('get_isbn_h(%s, %d)' % (book, max_count))
        url = 'https://honto.jp/netstore/search.html'
        params = {
            'k': book,
            'srchf': '1',
            'tbty': 1
        }
        isbns = {}
        book_link = []
        try:
            res = requests.get(url, params=params)
        except Exception as e:
            log.warning(e)
            return None
        else:
            if res.status_code != 200:
                log.warning('%s return %d' % (url, res.status_code))
                return None

        soup = bs4.BeautifulSoup(res.text, features='html.parser')
        title = soup.find_all('a', class_='dyTitle')
        book_han = book.translate(ZEN2HAN).lower().split()
        for t in title:
            log.debug("%s" % t)
            t_han = t.string.translate(ZEN2HAN).lower().split()
            t_han.append('')  # sentinel
            match = True
            if not re.match(r'^\d{10}$', book.translate(ZEN2HAN)):  # not ISBN
                for b in book_han:
                    if t_han.pop(0) != b:
                        match = False
                        break
            if match:
                book_link.append((t.string.translate(ZEN2HAN), t.get('href')))

        for title, link in book_link[:max_count]:
            if self.abort:
                log.warning('abort get_isbn_h()')
                return None
            try:
                res = requests.get(link)
            except Exception as e:
                log.warning(e)
                return None
            else:
                if res.status_code != 200:
                    log.warning('%s return %d' % (link, res.status_code))
                    return None

            soup = bs4.BeautifulSoup(res.text, features='html.parser')
            lis = soup.find_all('li', text=re.compile('ISBN'))
            for li in lis:
                isbn_string = li.string.split(r'：')
                if len(isbn_string) == 2:
                    isbn = isbn_string[1].split('-')
                    if len(isbn) == 5:
                        isbn.pop(0)
                    isbns[''.join(isbn)] = title

        log.debug('get_isbn_h(): %s' % isbns)
        return isbns

    def get_book_status(self, isbns, systemids, timeout=60):
        log.debug('get_book_status(%s, %s, %s)' %
                  (isbns, systemids, timeout))

        polling_interval = 2  # [sec]
        url = 'https://api.calil.jp/check'
        params = {
            'appkey': self.CALIL_APPKEY,
            'callback': 'no'
        }
        params['isbn'] = ','.join(isbns.keys())
        params['systemid'] = ','.join(systemids)

        try:
            res = requests.get(url, params=params)
        except Exception as e:
            log.warning(e)
            return []

        if res.status_code != 200:
            log.warning('%s return %d' % (url, res.status_code))
            return []

        json_data = res.json()
        timer = timeout/polling_interval
        while json_data['continue'] == 1:
            if self.abort:
                log.warning('abort get_book_status()')
                return []

            if timer <= 0:
                log.warning('calil.jp query time-out')
                return []
            timer -= 1
            time.sleep(polling_interval)
            try:
                params = {
                    'appkey': self.CALIL_APPKEY,
                    'session': json_data['session'],
                    'callback': 'no'
                }
                res = requests.get(url, params=params)
            except Exception as e:
                log.warning(e)
                return []
            else:
                if res.status_code != 200:
                    log.warning('%s return %d' % (url, res.status_code))
                    return []
                else:
                    json_data = res.json()

        log.debug('get_book_status(): %s' % json_data)
        return json_data

    def run_search(self, book, result_format, param):
        log.debug('run_search(%s)' % book)
        result = {'book': book, 'data': {}}

        isbns = self.get_isbn_h(book)
        if not isbns:
            isbns = self.get_isbn_c(book)
        if not isbns:
            if result_format == 'json':
                param.args['json'] = result
            else:
                param.message = self.result_by_string(result)
            try:
                self.messages.put_nowait(param)
                log.debug('add queue: %s' % param.message)
            except queue.Full as e:
                log.warning("run_search(): %s" % e)

            self.searching = False
            return

        if self.abort:
            log.warning('abort run_search()')
            self.searching = False
            return

        book_status = self.get_book_status(isbns, self.libraries)
        if not book_status:
            if result_format == 'json':
                param.args['json'] = result
            else:
                param.message = 'Search error :construction:'
            try:
                self.messages.put_nowait(param)
                log.debug('add queue: %s' % param.message)
            except queue.Full as e:
                log.warning("run_search(): %s" % e)

            self.searching = False
            return

        for isbn in book_status['books']:
            title = isbns[isbn]
            result['data'][title] = {}
            for systemid in book_status['books'][isbn]:
                result['data'][title][systemid] = {}
                library = result['data'][title][systemid]
                status = book_status['books'][isbn][systemid]
                library['name'] = self.configuration[systemid]
                if status['status'] == 'OK' or status['status'] == 'Cache':
                    library['url'] = status['reserveurl']
                    library['status'] = status['libkey']
                else:
                    library['url'] = 'https://httpbin.org/status/418'
                    library['status'] = {' -_-': 'Error'}

        log.debug('run_search(): %s' % result)
        if result_format == 'json':
            param.args['json'] = result
        else:
            param.message = self.result_by_string(result)
        try:
            self.messages.put_nowait(param)
            log.debug('add queue: %s' % param.message)
        except queue.Full as e:
            log.warning("run_search(): %s" % e)

        self.searching = False
        return

    def search(self, book, param=None, result_format='string'):
        if self.searching:
            log.warning('already searching')
            return False
        self.thread = Thread(target=self.run_search,
                             args=(book, result_format, param))
        self.searching = True
        self.thread.start()

        return True

    def run(self, param):
        log.debug('command(): %s, %s' % (param.command, param.channel))
        cmd = param.command.strip()
        cmd = re.split('[ 　]', cmd, 1)
        if len(cmd) == 2:
            res = self.search(cmd[1], param=param)
            if res:
                param.message = '"%s"...' % cmd[1]
            else:
                param.message = 'sorry, busy with searching the other book'
        else:
            param.message = 'book <title>'

        log.debug('exit command(): %s' % param.message)
        return param

    def result_by_string(self, result):
        if not result:
            return None

        if not result['data']:
            emoji = [
                ':collision:',
                ':moyai:',
                ':socks:',
                ':ramen:',
                ':jack_o_lantern:'
            ]
            return emoji[random.randrange(0, len(emoji))]

        string = '[%s]\n' % result['book']
        for title in result['data']:
            string += '\n%s\n' % title
            for systemid in result['data'][title]:
                library = result['data'][title][systemid]
                if library['status']:
                    for place in library['status']:
                        string += '- %s(%s): <%s|%s>\n' % (
                            library['name'], place,
                            library['url'], library['status'][place])
                else:
                    string += '- %s: 蔵書なし\n' % (library['name'])

        return string


"""
{
  "book": <book>,
  "data": {
    <title>: {
      <systemid>: {
        "name": <library name>,
        "url": <url>,
        "status": {<place>:<status>, <place>:<status>, ...}
      },
      <systemid>: {
        "name": <library name>,
        "url": <url>,
        "status": {<place>:<status>, <place>:<status>, ...}
      },
      ...
    },
    <title>: {
      <systemid>: {
        "name": <library name>,
        "url": <url>,
        "status": {<place>:<status>, <place>:<status>}
      },
      ...
    },
    ...
  }
}

"""


if __name__ == '__main__':
    """
    for debug
    """
    from .command import Command
    log_level = logging.DEBUG
    formatter = '%(asctime)s %(name)s[%(lineno)s] %(levelname)s: %(message)s'
    logging.basicConfig(level=log_level, format=formatter)

    """
    michi: hankaku zenkaku
    星界の報告: not owned
    Twiter: ISBN not found
    ナポレオン: many title
    リーダブルコード: one title
    インターネットを256倍使うための本: a few title
    誰が音楽をタダにした？: with a special character
    """
    books = ['michi', '星界の報告', 'Twiter']
    # books = ['ナポレオン', 'リーダブルコード', 'インターネットを256倍使うための本', '誰が音楽をタダにした？']

    q = queue.Queue()
    bs = BookStatus(q)
    for book in books:
        param = Command(channel='123456789')
        param.command = 'book ' + book
        res = bs.run(param)
        print(res.message)

        while bs.searching:
            print('wait for results...')
            """
            if not bs.search('ドラえもん'):
                print("can't search %s" % 'ドラえもん')
            """
            time.sleep(2)
            # bs.abort = True

        while not q.empty():
            status = q.get()
            if status:
                print('----- status.message ----')
                print(status.message)
                print('----- status.channel ----')
                print(status.channel)
                print('----- status.files ----')
                print(status.files)
            else:
                print('"%s" is not found' % book)
