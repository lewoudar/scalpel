import logging
from typing import Dict, Optional

import attr
import httpx
import parsel
from rfc3986 import uri_reference

logger = logging.getLogger('scalpel')


@attr.s(kw_only=True)
class Response:
    _url: str = attr.ib(default='', validator=attr.validators.optional(attr.validators.instance_of(str)))
    _text: str = attr.ib(default='', validator=attr.validators.instance_of(str))
    _httpx_response: Optional[httpx.Response] = attr.ib(
        default=None, validator=attr.validators.optional(attr.validators.instance_of(httpx.Response))
    )

    @property
    def url(self) -> str:
        if self._url:
            _url = self._url
        else:
            _url = f'{self._httpx_response.url}'
        logger.debug('returning response url: %s', _url)
        return _url

    @property
    def headers(self) -> Dict[str, str]:
        if self._url:
            _headers = {}
        else:
            _headers = dict(self._httpx_response.headers)
        logger.debug('returning response headers:\n %s', _headers)
        return _headers

    @property
    def text(self) -> str:
        if self._text:
            _text = self._text
        else:
            _text = self._httpx_response.text
        logger.debug('returning response text content:\n %s', _text)
        return _text

    @property
    def content(self) -> bytes:
        if self._text:
            _content = self._text.encode(errors='replace')
        else:
            _content = self._httpx_response.content
        logger.debug('returning response byte content:\n %s', _content)
        return _content

    @property
    def cookies(self) -> Dict[str, str]:
        if self._url:
            _cookies = {}
        else:
            _cookies = dict(self._httpx_response.cookies)
        logger.debug('returning response cookies: %s', _cookies)
        return _cookies


@attr.s
class BaseStaticResponse(Response):
    _selector: parsel.Selector = attr.ib(init=False)

    @_selector.default
    def _get_selector(self) -> parsel.Selector:
        logger.debug('creating parsel selector with text:\n %s', self.text)
        return parsel.Selector(self.text)

    def css(self, query: str) -> parsel.SelectorList:
        logger.debug('selecting content using css selector: %s', query)
        return self._selector.css(query)

    def xpath(self, query: str) -> parsel.SelectorList:
        logger.debug('selecting content using xpath selector: %s', query)
        return self._selector.xpath(query)

    def _get_absolute_url(self, url: str) -> str:
        """
        This method will help to get absolute url from local or http urls.
        """
        if self._url:
            absolute_uri = uri_reference(self._url)
            given_uri = uri_reference(url)
            if given_uri.is_absolute():
                _url = url
            else:
                uri = given_uri.resolve_with(absolute_uri)
                uri = uri.copy_with(fragment=None)
                _url = uri.unsplit()
        else:
            _url = f'{self._httpx_response.url.join(url)}'
        logger.debug('returning new joined url: %s', _url)
        return _url
