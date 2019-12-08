#!/usr/bin/env python3

import time
import os
import pytest
import book
import re

book_config = os.environ['BOOK_CONFIG']
calil_appkey = os.environ['CALIL_APPKEY']


def test_book_init_raise_no_appkey():
    os.environ['BOOK_CONFIG'] = book_config
    os.environ['CALIL_APPKEY'] = ''
    with pytest.raises(book.BookStatusError):
        book.BookStatus()


def test_book_init_raise_no_config():
    os.environ['BOOK_CONFIG'] = ''
    os.environ['CALIL_APPKEY'] = calil_appkey
    with pytest.raises(book.BookStatusError):
        book.BookStatus()


def test_anyping_init_raise_config_syntax_error():
    os.environ['BOOK_CONFIG'] = 'test/book-test-config-error.conf'
    os.environ['CALIL_APPKEY'] = calil_appkey
    with pytest.raises(book.BookStatusError):
        book.BookStatus()


@pytest.mark.parametrize("bk, expected", [
    ('Twiter', r':.+:'),
    ('イマココ',
     '.イマココ.\n\nイマココ 渡り鳥からグーグル・アースまで、空間認知の科学\n'
     '- 東京都立図書館.中央.+\n- 国立国会図書館: 蔵書なし\n')
])
def test_book_search(bk, expected):
    os.environ['BOOK_CONFIG'] = 'test/book-test.conf'
    os.environ['CALIL_APPKEY'] = calil_appkey

    bs = book.BookStatus()
    result = bs.search(bk)
    assert result is True
    result = bs.search(bk)
    assert result is False

    while bs.searching:
        time.sleep(2)

    status = bs.result_by_string()
    assert re.match(expected, status)


if __name__ == '__main__':
    pytest.main(['-v', __file__])
