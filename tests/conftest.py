import datetime
from pathlib import Path
from typing import Any, List

import msgpack
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions


@pytest.fixture(scope='session')
def robots_content():
    return """
    User-agent: Googlebot
    Disallow: /videos/
    Disallow: /photos/

    User-agent: *
    Disallow: /admin/
    Allow: /admin/admin-ajax.php
    """


@pytest.fixture(scope='session')
def encode_datetime():
    """Factory fixture providing a msgpack encoder for datetime objects."""

    def _encode_datetime(obj):
        if isinstance(obj, datetime.datetime):
            return {'__datetime__': True, 'as_str': obj.strftime("%Y%m%dT%H:%M:%S.%f")}
        return obj

    return _encode_datetime


@pytest.fixture(scope='session')
def decode_datetime():
    """Factory fixture providing a msgpack decoder for datetime objects."""

    def _decode_datetime(obj):
        if '__datetime__' in obj:
            obj = datetime.datetime.strptime(obj["as_str"], "%Y%m%dT%H:%M:%S.%f")
        return obj

    return _decode_datetime


@pytest.fixture(scope='session')
def create_msgpack_file(encode_datetime):
    """Factory fixture to create msgpack files."""

    # noinspection PyTypeChecker
    def _create_msgpack_file(path: Path, data: List[Any]):
        packer = msgpack.Packer(autoreset=False, default=encode_datetime)
        for item in data:
            packer.pack(item)
        with open(path, 'wb') as f:
            f.write(packer.getbuffer())

        packer.reset()

    return _create_msgpack_file


@pytest.fixture(scope='session')
def page_1_file_url():
    """Returns file url of website/page1.html"""
    p = Path(__file__).parent / 'website' / 'page1.html'
    return p.as_uri()


@pytest.fixture(scope='session')
def page_content():
    """Returns function factory to get page content of each html page in website folder"""

    def _page_content(page: str):
        p = Path(__file__).parent / 'website' / page
        return p.read_text()

    return _page_content


@pytest.fixture()
def chrome_driver():
    """Returns an instance of a selenium chrome driver"""
    options = ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    try:
        yield driver
    finally:
        driver.quit()
