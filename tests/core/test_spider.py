import re

import pytest
from attr.exceptions import NotCallableError
from rfc3986 import uri_reference
from rfc3986.exceptions import InvalidComponentsError

from scalpel.core.config import Configuration
from scalpel.core.spider import Spider


@pytest.fixture(scope='module')
def default_spider_arguments():
    return {'urls': ['http://foo.com'], 'parse': lambda x: x}


# noinspection PyTypeChecker
class TestUrlsValidator:
    """spider urls attribute test"""

    def dummy_parse(self, *args):
        pass

    @pytest.mark.parametrize('urls', ['http://focbar.com', {'url': 'http://foobar.com'}])
    def test_should_raise_error_when_urls_is_not_a_collection(self, urls):
        with pytest.raises(TypeError) as exc_info:
            Spider(urls, self.dummy_parse)

        assert f'urls is not a typing.Set, list or tuple instance: {urls}' == str(exc_info.value)

    @pytest.mark.parametrize('urls', [
        ['http://foo.com', b'http://bar.com'],
        ('http://foo.com', 4),
        {'http://foo.com', 4.5}
    ])
    def test_should_raise_error_when_list_is_composed_of_non_string_elements(self, urls):
        with pytest.raises(TypeError) as exc_info:
            Spider(urls, self.dummy_parse)

        assert f'not all items in urls are a string: {urls}' == str(exc_info.value)

    def test_should_raise_error_when_item_in_the_list_does_not_have_a_valid_scheme(self):
        with pytest.raises(ValueError) as exc_info:
            Spider(['http://foobar.com', 'ftp://user:pass@foo.com'], self.dummy_parse)

        assert "ftp://user:pass@foo.com does not have a scheme in ['https', 'http', 'file']" == str(exc_info.value)

    def test_should_raise_error_when_item_in_the_list_has_an_invalid_component_part(self, mocker):
        # todo: like I said in the source code, I don't know how to reproduce this error, so for now
        #   I will just mock the validate method
        url = 'http://fobor#ge.com'
        uri = uri_reference('http://fobor#ge.com')
        exception = InvalidComponentsError(uri, 'path')
        mocker.patch('rfc3986.validators.Validator.validate', side_effect=exception)

        with pytest.raises(ValueError) as exc_info:
            Spider([url], self.dummy_parse)

        assert f'{url} is not a valid url' == str(exc_info.value)

    def test_should_raise_error_when_url_in_the_list_does_not_provide_a_host_part(self):
        with pytest.raises(ValueError) as exc_info:
            Spider(('http://foo.com', 'https://?foo=bar'), self.dummy_parse)

        assert 'url https://?foo=bar must provide a host part' == str(exc_info.value)

    def test_should_raise_error_when_file_url_in_the_list_does_not_provide_a_path_part(self):
        with pytest.raises(ValueError) as exc_info:
            Spider({'http://foo.com', 'file:///my/unknown/file', 'file://'}, self.dummy_parse)

        assert 'url file:// must provide a path to a local file' == str(exc_info.value)

    @pytest.mark.parametrize('urls', [
        ['http://foo.com', 'https://foobar.com'],
        ('http://bar.com', 'file:///'),
        {'http://foo.com', 'file:///path/to/unknown/file'}
    ])
    def test_should_not_raise_error_when_giving_correct_list_of_urls(self, urls):
        try:
            Spider(urls, self.dummy_parse)
        except (TypeError, ValueError) as e:
            pytest.fail(f'Unexpected error when instantiating spider: {e}')

    def test_should_not_raise_error_when_passing_internationalized_urls(self):
        urls = ['http://中国.com.museum', 'http://Königsgäßchen.de']
        try:
            Spider(urls, self.dummy_parse)
        except Exception as e:
            pytest.fail(f'Unexpected error when instantiating spider: {e}')


class TestParseAttribute:
    """Tests spider parse attribute"""
    urls = ['http://foo.com']

    # noinspection PyTypeChecker
    @pytest.mark.parametrize('parse', [{'foo': 'bar'}, 4])
    def test_should_raise_error_when_parse_is_not_a_callable(self, parse):
        with pytest.raises(NotCallableError):
            Spider(urls=self.urls, parse=parse)

    def test_should_not_raise_error_when_giving_correct_parse_argument(self):
        try:
            Spider(urls=self.urls, parse=lambda x: x)
        except NotCallableError as e:
            pytest.fail(f'Unexpected error when instantiating parser: {e}')


class TestNameAttribute:
    """Tests spider name attribute and property"""

    # noinspection PyTypeChecker
    @pytest.mark.parametrize('name', [4, b'foo'])
    def test_should_raise_error_when_name_is_not_a_string(self, name, default_spider_arguments):
        with pytest.raises(TypeError):
            Spider(name=name, **default_spider_arguments)

    def test_should_validate_default_name_value(self, default_spider_arguments):
        spider = Spider(**default_spider_arguments)

        assert re.match(r'^spider-\d{4}(-\d{2}){2}@\d{2}(:\d{2}){2}\.\d{6}$', spider._name)

    def test_name_property_returns_the_same_value_as_the_name_attribute(self, default_spider_arguments):
        name = 'my-spider'
        spider = Spider(**default_spider_arguments, name=name)

        assert name == spider.name


class TestConfigAttribute:
    """Tests spider config attribute and property"""

    # noinspection PyTypeChecker
    @pytest.mark.parametrize('config', [{'foo': 'bar'}, ['foo', 'bar']])
    def test_should_raise_error_when_config_does_not_have_the_correct_type(self, config, default_spider_arguments):
        with pytest.raises(TypeError):
            Spider(**default_spider_arguments, config=config)

    def test_should_not_raise_error_when_giving_correct_config_argument(self, default_spider_arguments):
        config = Configuration(fetch_timeout=0)
        try:
            Spider(**default_spider_arguments, config=config)
        except TypeError as e:
            pytest.fail(f'unexpected error when instantiating spider: {e}')

    def test_config_property_returns_the_same_value_as_the_config_attribute(self, default_spider_arguments):
        config = Configuration(fetch_timeout=0)
        spider = Spider(**default_spider_arguments, config=config)

        assert config == spider.config


class TestFetchedUrlsAttribute:
    """Tests spider _fetched_urls attributes"""

    def test_should_return_empty_set_when_getting_fetched_urls_attribute(self, default_spider_arguments):
        spider = Spider(**default_spider_arguments)
        assert set() == spider._fetched_urls