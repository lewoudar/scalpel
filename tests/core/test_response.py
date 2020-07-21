from typing import Union

import attr
import httpx
import parsel
import pytest

from scalpel.core.response import Response, BaseStaticResponse
from tests.helpers import assert_dicts


@pytest.fixture(scope='module')
def dummy_data():
    return b'<html><body><p>Hello World!</p></body></html>'


@pytest.fixture(scope='module')
def httpx_response(dummy_data):
    request = httpx.Request('GET', 'http://foobar.com')
    return httpx.Response(200, request=request, content=dummy_data)


class TestResponse:
    """Tests Response class"""

    def test_should_validate_properties_when_passing_url_and_text(self, dummy_data):
        response = Response(url='http://foo.com', text=dummy_data.decode())

        assert 'http://foo.com' == response.url
        assert_dicts({}, response.headers)
        assert_dicts({}, response.cookies)
        assert dummy_data.decode() == response.text
        assert dummy_data == response.content

    def test_should_validate_properties_when_passing_httpx_response(self):
        url = 'http://foobar.com'
        request = httpx.Request('GET', url)
        headers = {'foo': 'bar', 'set-cookie': 'name=John'}
        content = b'hello world'
        httpx_response = httpx.Response(200, request=request, headers=headers, content=content)
        response = Response(httpx_response=httpx_response)

        assert url == response.url
        assert_dicts(headers, response.headers)
        assert_dicts({'name': 'John'}, response.cookies)
        assert content == response.content
        assert content.decode() == response.text

    def test_should_validate_attributes(self):
        fields = {attribute.name: attribute.type for attribute in attr.fields(Response)}
        attributes = {
            '_httpx_response': Union[httpx._models.Response, type(None)],
            '_url': str,
            '_text': str
        }
        assert_dicts(fields, attributes)


class TestBaseStaticResponse:
    """Tests class BaseStaticResponse"""

    def test_should_validate_attributes(self):
        fields = {attribute.name: attribute.type for attribute in attr.fields(BaseStaticResponse)}
        attributes = {
            '_httpx_response': Union[httpx._models.Response, type(None)],
            '_url': str,
            '_text': str,
            '_selector': parsel.Selector
        }
        assert_dicts(fields, attributes)

    def test_should_validate_that_selector_attribute_is_correctly_instantiated(self, dummy_data, httpx_response):
        response = BaseStaticResponse(httpx_response=httpx_response)
        assert response._selector.get() == dummy_data.decode()

    def test_should_return_correct_data_when_calling_css_method(self, httpx_response):
        response = BaseStaticResponse(httpx_response=httpx_response)
        assert '<p>Hello World!</p>' == response.css('p').get()

    def test_should_return_correct_data_when_calling_xpath_method(self, httpx_response):
        response = BaseStaticResponse(httpx_response=httpx_response)
        assert '<p>Hello World!</p>' == response.xpath('//p').get()

    # tests method _get_absolute_url

    @pytest.mark.parametrize(('given_url', 'absolute_url'), [
        ('hello', 'http://foobar.com/hello'),
        ('/hello', 'http://foobar.com/hello'),
        ('#hello', 'http://foobar.com#hello'),
        ('http://example.com', 'http://example.com')
    ])
    def test_should_return_absolute_url_given_httpx_response(self, httpx_response, given_url, absolute_url):
        response = BaseStaticResponse(httpx_response=httpx_response)
        assert absolute_url == response._get_absolute_url(given_url)

    @pytest.mark.parametrize(('given_url', 'absolute_url'), [
        ('page.html', 'file:/C/foo/page.html'),
        ('/page.html', 'file:/page.html'),
        ('#page', 'file:/C/foo/bar.html'),
        ('http://foo.com', 'http://foo.com'),
        ('file:///C:/path/to/file', 'file:///C:/path/to/file')
    ])
    def test_should_return_absolute_url_given_url_and_text(self, dummy_data, given_url, absolute_url):
        response = BaseStaticResponse(url='file:/C/foo/bar.html', text=dummy_data.decode())
        assert absolute_url == response._get_absolute_url(given_url)
