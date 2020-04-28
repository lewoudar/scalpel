from typing import Dict

import attr
import httpx
import parsel


@attr.s
class Response:
    _httpx_response: httpx.Response = attr.ib()

    @property
    def url(self) -> str:
        return f'{self._httpx_response.url}'

    @property
    def headers(self) -> Dict[str, str]:
        return dict(self._httpx_response.headers)

    @property
    def text(self) -> str:
        return self._httpx_response.text

    @property
    def content(self) -> bytes:
        return self._httpx_response.content

    @property
    def cookies(self) -> Dict[str, str]:
        return dict(self._httpx_response.cookies)


@attr.s
class BaseStaticResponse(Response):
    _selector: parsel.Selector = attr.ib(init=False)

    @_selector.default
    def get_selector(self) -> parsel.Selector:
        return parsel.Selector(self._httpx_response.text)

    def css(self, query: str) -> parsel.SelectorList:
        return self._selector.css(query)

    def xpath(self, query: str) -> parsel.SelectorList:
        return self._selector.xpath(query)
