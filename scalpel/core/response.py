import logging
from typing import Dict, Optional

import attr
import httpx
import parsel
from rfc3986 import uri_reference
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger('scalpel')


@attr.s(kw_only=True)
class BaseStaticResponse:
    _url: str = attr.ib(default='', validator=attr.validators.optional(attr.validators.instance_of(str)))
    _text: str = attr.ib(default='', validator=attr.validators.instance_of(str))
    _httpx_response: Optional[httpx.Response] = attr.ib(
        default=None, validator=attr.validators.optional(attr.validators.instance_of(httpx.Response))
    )
    _selector: parsel.Selector = attr.ib(init=False)

    @property
    def url(self) -> str:
        """The url associated to the response object."""
        if self._url:
            _url = self._url
        else:
            _url = f'{self._httpx_response.url}'
        logger.debug('returning response url: %s', _url)
        return _url

    @property
    def headers(self) -> Dict[str, str]:
        """A `dict` of http headers in case of an HTTP url. Empty `dict` otherwise."""
        if self._url:
            _headers = {}
        else:
            _headers = dict(self._httpx_response.headers)
        logger.debug('returning response headers:\n %s', _headers)
        return _headers

    @property
    def text(self) -> str:
        """The string content associated to the url."""
        if self._text:
            _text = self._text
        else:
            _text = self._httpx_response.text
        logger.debug('returning response text content:\n %s', _text)
        return _text

    @property
    def content(self) -> bytes:
        """The bytes content associated to the url."""
        if self._text:
            _content = self._text.encode(errors='replace')
        else:
            _content = self._httpx_response.content
        logger.debug('returning response byte content:\n %s', _content)
        return _content

    @property
    def cookies(self) -> Dict[str, str]:
        """A `dict` of cookies associated to the response in case of an HTTP url. Empty `dict` otherwise."""
        if self._url:
            _cookies = {}
        else:
            _cookies = dict(self._httpx_response.cookies)
        logger.debug('returning response cookies: %s', _cookies)
        return _cookies

    @_selector.default
    def _get_selector(self) -> parsel.Selector:
        logger.debug('creating parsel selector with text:\n %s', self.text)
        return parsel.Selector(self.text)

    def css(self, query: str) -> parsel.SelectorList:
        """
        Applies CSS rules to select DOM elements.

        **Parameters:**

        * **query:** The CSS rule used to select DOM elements.

        **Returns:** `parsel.SelectorList`
        """
        logger.debug('selecting content using css selector: %s', query)
        return self._selector.css(query)

    def xpath(self, query: str) -> parsel.SelectorList:
        """
        Applies XPath rules to select DOM elements.

        **Parameters:**

        * **query:** The XPath rule used to select DOM elements.

        **Returns:** `parsel.SelectorList`
        """
        logger.debug('selecting content using xpath selector: %s', query)
        return self._selector.xpath(query)

    def _get_absolute_url(self, url: str) -> str:
        """
        This method returns absolute url from local or http urls.
        """
        current_uri = uri_reference(self._url) if self._url else uri_reference(str(self._httpx_response.url))
        given_uri = uri_reference(url)
        if given_uri.is_absolute():
            _url = url
        else:
            uri = given_uri.resolve_with(current_uri)
            uri = uri.copy_with(fragment=None)
            _url = uri.unsplit()
        logger.debug('returning computed absolute url: %s', _url)
        return _url


@attr.s(kw_only=True)
class BaseSeleniumResponse:
    driver: WebDriver = attr.ib(validator=attr.validators.instance_of(WebDriver))
    handle: str = attr.ib(validator=attr.validators.instance_of(str))

    def _get_absolute_url(self, url: str) -> str:
        """
        This method returns absolute url from local or http urls.
        """
        uri = uri_reference(url)
        if uri.is_absolute():
            _url = url
        else:
            # this is probably useless because I checked with firefox and chrome and both
            # computes absolute urls when they encounter a relative one, but to remove any doubt, let's do this
            current_uri = uri_reference(self.driver.current_url)
            uri = uri.resolve_with(current_uri)
            uri = uri.copy_with(fragment=None)
            _url = uri.unsplit()
        logger.debug('returning computed absolute url: %s', _url)
        return _url
