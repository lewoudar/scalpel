import inspect

import attr
import httpx
import pytest

from scalpel.core.abc import Response, AbstractStaticResponse
from tests.helpers import assert_dicts


@pytest.fixture(scope='module')
def dummy_data():
    return b'<html><body><p>Hello World!</p></body></html>'


@pytest.fixture(scope='module')
def httpx_response(dummy_data):
    request = httpx.Request('GET', 'http://foobar.com')
    return httpx.Response(200, request=request, content=dummy_data)


class TestResponse:
    """Tests abstract class Response"""

    class DummyResponse(Response):

        def follow(self, url: str) -> None:
            pass

    def test_should_validate_class_is_abstract(self):
        assert inspect.isabstract(Response)

    def test_should_validate_abstract_method(self):
        assert {'follow'} == Response.__abstractmethods__
        assert inspect.isfunction(Response.follow)

    def test_should_validate_properties(self):
        url = 'http://foobar.com'
        request = httpx.Request('GET', url)
        headers = {'foo': 'bar', 'set-cookie': 'name=John'}
        content = b'hello world'
        httpx_response = httpx.Response(200, request=request, headers=headers, content=content)
        response = self.DummyResponse(httpx_response)

        assert url == response.url
        assert_dicts(headers, response.headers)
        assert {'name': 'John'} == response.cookies
        assert content == response.content
        assert content.decode() == response.text

    def test_should_validate_attributes(self):
        fields = {attribute.name: attribute.type for attribute in attr.fields(Response)}
        assert {'_httpx_response': httpx.Response} == fields


class TestAbstractStaticResponse:
    """Tests abstract class AbstractStaticResponse"""

    class DummyStaticResponse(AbstractStaticResponse):

        def follow(self, url: str) -> None:
            pass

    def test_should_validate_class_is_abstract(self):
        assert inspect.isabstract(AbstractStaticResponse)

    def test_should_validate_attributes(self):
        fields = {attribute.name: attribute.type for attribute in attr.fields(Response)}
        assert {'_httpx_response': httpx.Response} == fields

    def test_should_validate_that_selector_attribute_is_correctly_instantiated(self, dummy_data, httpx_response):
        response = self.DummyStaticResponse(httpx_response)
        assert response._selector.get() == dummy_data.decode()

    def test_should_return_correct_data_when_calling_css_method(self, httpx_response):
        response = self.DummyStaticResponse(httpx_response)
        assert '<p>Hello World!</p>' == response.css('p').get()

    def test_should_return_correct_data_when_calling_xpath_method(self, httpx_response):
        response = self.DummyStaticResponse(httpx_response)
        assert '<p>Hello World!</p>' == response.xpath('//p').get()
