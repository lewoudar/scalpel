from typing import Union

import attr
import httpx
import parsel
import pytest

from scalpel.core.response import BaseStaticResponse, BaseSeleniumResponse
from tests.helpers import assert_dicts


@pytest.fixture(scope='module')
def dummy_data():
    return b'<html><body><p>Hello World!</p></body></html>'


@pytest.fixture(scope='module')
def httpx_response(dummy_data):
    request = httpx.Request('GET', 'http://foobar.com')
    return httpx.Response(200, request=request, content=dummy_data)


class TestBaseStaticResponse:
    """Tests class BaseStaticResponse"""

    def test_should_validate_properties_when_passing_url_and_text(self, dummy_data):
        response = BaseStaticResponse(url='http://foo.com', text=dummy_data.decode())

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
        response = BaseStaticResponse(httpx_response=httpx_response)

        assert url == response.url
        assert_dicts(headers, response.headers)
        assert_dicts({'name': 'John'}, response.cookies)
        assert content == response.content
        assert content.decode() == response.text

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
        ('#hello', 'http://foobar.com'),
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


class TestBaseSeleniumResponse:
    """Tests class BaseSeleniumResponse"""

    # initialization

    # noinspection PyTypeChecker
    def test_should_raise_error_when_driver_does_not_have_the_correct_type(self):
        with pytest.raises(TypeError):
            BaseSeleniumResponse(driver='foo', handle='4', file_url=None)

    # noinspection PyTypeChecker
    @pytest.mark.parametrize('handle', [4, 4.0])
    def test_should_raise_error_when_handle_does_not_have_the_correct_type(self, chrome_driver, handle):
        with pytest.raises(TypeError):
            BaseSeleniumResponse(driver=chrome_driver, handle=handle, file_url=None)

    def test_should_not_raise_error_when_parameters_are_correct(self, chrome_driver):
        try:
            BaseSeleniumResponse(driver=chrome_driver, handle='4', file_url=None)
        except TypeError:
            pytest.fail('unexpected error when initializing BaseSeleniumResponse')

    # _get_absolute_url

    @pytest.mark.parametrize(('given_url', 'absolute_url'), [
        ('hello', 'http://foobar.com/hello'),
        ('/hello', 'http://foobar.com/hello'),
        ('#hello', 'http://foobar.com'),
        ('https://example.com', 'https://example.com')
    ])
    def test_should_return_absolute_url_when_base_url_is_an_http_one(
            self, mocker, chrome_driver, given_url, absolute_url
    ):
        mocker.patch('selenium.webdriver.remote.webdriver.WebDriver.current_url', 'http://foobar.com')
        response = BaseSeleniumResponse(driver=chrome_driver, handle='4', file_url=None)

        assert absolute_url == response._get_absolute_url(given_url)

    @pytest.mark.parametrize(('given_url', 'absolute_url'), [
        ('page.html', 'file:/C/foo/page.html'),
        ('/page.html', 'file:/page.html'),
        ('#page', 'file:/C/foo/bar.html'),
        ('http://foo.com', 'http://foo.com'),
        ('file:///C:/path/to/file', 'file:///C:/path/to/file')
    ])
    def test_should_return_absolute_url_when_base_url_is_a_file_one(self, chrome_driver, given_url, absolute_url):
        response = BaseSeleniumResponse(driver=chrome_driver, handle='4', file_url='file:/C/foo/bar.html')

        assert absolute_url == response._get_absolute_url(given_url)
