import logging
from typing import Dict

import attr
import httpx
import parsel

logger = logging.getLogger('scalpel')


@attr.s
class Response:
    _httpx_response: httpx.Response = attr.ib()

    @property
    def url(self) -> str:
        _url = f'{self._httpx_response.url}'
        logger.debug('returning response url: %s', _url)
        return _url

    @property
    def headers(self) -> Dict[str, str]:
        _headers = dict(self._httpx_response.headers)
        logger.debug('returning response headers:\n %s', _headers)
        return _headers

    @property
    def text(self) -> str:
        _text = self._httpx_response.text
        logger.debug('returning response text content:\n %s', _text)
        return _text

    @property
    def content(self) -> bytes:
        _content = self._httpx_response.content
        logger.debug('returning response byte content:\n %s', _content)
        return _content

    @property
    def cookies(self) -> Dict[str, str]:
        _cookies = dict(self._httpx_response.cookies)
        logger.debug('returning response cookies: %s', _cookies)
        return _cookies


@attr.s
class BaseStaticResponse(Response):
    _selector: parsel.Selector = attr.ib(init=False)

    @_selector.default
    def get_selector(self) -> parsel.Selector:
        return parsel.Selector(self._httpx_response.text)

    def css(self, query: str) -> parsel.SelectorList:
        logger.debug('selecting content using css selector: %s', query)
        return self._selector.css(query)

    def xpath(self, query: str) -> parsel.SelectorList:
        logger.debug('selecting content using xpath selector: %s', query)
        return self._selector.xpath(query)
