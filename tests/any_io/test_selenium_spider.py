from datetime import datetime

import httpx
import pytest
import respx

# noinspection PyProtectedMember
from anyio._core._synchronization import Lock
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from scalpel.any_io.files import read_mp
from scalpel.any_io.queue import Queue
from scalpel.any_io.response import SeleniumResponse
from scalpel.any_io.robots import RobotsAnalyzer
from scalpel.any_io.selenium_spider import SeleniumSpider, StaticSpider
from scalpel.core.config import Browser, Configuration
from scalpel.core.message_pack import datetime_decoder

pytestmark = pytest.mark.anyio


class TestSeleniumSpider:
    """Tests class SeleniumSpider"""

    def test_selenium_spider_class_is_a_subclass_of_static_spider(self):
        assert issubclass(SeleniumSpider, StaticSpider)

    async def test_selenium_attributes_are_correctly_instantiated(self):
        config = Configuration(selenium_driver_log_file=None)
        spider = SeleniumSpider(urls=['http://foo.com'], parse=lambda x, y: None, config=config)

        assert isinstance(spider._driver, WebDriver)
        assert isinstance(spider._start_time, float)
        assert isinstance(spider._http_client, httpx.AsyncClient)
        assert isinstance(spider._robots_analyser, RobotsAnalyzer)
        assert config == spider._config
        assert isinstance(spider._lock, Lock)
        assert isinstance(spider._queue, Queue)

        # cleanup
        await spider._cleanup()

    # _get_selenium_response test

    @pytest.mark.parametrize(('browser', 'handle'), [(Browser.FIREFOX, '4'), (Browser.CHROME, '4')])
    async def test_should_return_selenium_response_when_giving_correct_input(self, browser, handle):
        config = Configuration(selenium_driver_log_file=None, selenium_browser=browser)
        spider = SeleniumSpider(urls=['http://foo.com'], parse=lambda x, y: None, config=config)
        response = spider._get_selenium_response(handle)

        assert isinstance(response, SeleniumResponse)
        assert response.driver is spider._driver
        assert response.handle == handle
        assert response._reachable_urls == spider.reachable_urls
        assert response._followed_urls == spider.followed_urls
        assert response._queue == spider._queue

        # cleanup
        await spider._cleanup()

    # _handle_url test

    @pytest.mark.parametrize(
        ('reachable_urls', 'unreachable_urls', 'robots_excluded_urls'),
        [(set(), set(), {'http://foo.com'}), (set(), {'http://foo.com'}, set()), ({'http://foo.com'}, set(), set())],
    )
    async def test_should_do_nothing_if_url_is_already_present_in_one_url_set(
        self, mocker, reachable_urls, unreachable_urls, robots_excluded_urls
    ):
        url = 'http://foo.com'
        logger_mock = mocker.patch('logging.Logger.debug')

        config = Configuration(selenium_driver_log_file=None)
        spider = SeleniumSpider(urls=['http://foo.com'], parse=lambda x, y: None, config=config)
        spider.reachable_urls = reachable_urls
        spider.unreachable_urls = unreachable_urls
        spider.robots_excluded_urls = robots_excluded_urls
        await spider._handle_url(url)

        logger_mock.assert_any_call('url %s has already been processed', url)

    async def test_should_read_file_content_when_giving_a_file_url(self, tmp_path):
        parse_args = []
        hello_file = tmp_path / 'hello.txt'
        hello_file.write_text('Hello world!')
        file_url = hello_file.resolve().as_uri()

        async def parse(sel_spider, response):
            parse_args.extend([sel_spider, response])

        spider = SeleniumSpider(urls=[file_url], parse=parse, config=Configuration(selenium_driver_log_file=None))
        await spider._handle_url(file_url)

        assert parse_args[0] is spider
        sel_response = parse_args[1]
        assert isinstance(sel_response, SeleniumResponse)
        assert '<body><pre>Hello world!</pre></body>' in sel_response.driver.page_source
        assert {file_url} == spider.reachable_urls
        assert 1 == spider.request_counter
        assert set() == spider.unreachable_urls
        assert spider._total_fetch_time > 0

        # cleanup
        await spider._cleanup()

    async def test_should_not_call_parse_method_when_file_cannot_be_opened(self, mocker, tmp_path):
        logger_mock = mocker.patch('logging.Logger.exception')
        hello_file = tmp_path / 'hello.txt'
        file_url = hello_file.resolve().as_uri()
        parse_args = []

        async def parse(sel_spider, response):
            parse_args.extend([sel_spider, response])

        spider = SeleniumSpider(urls=[file_url], parse=parse, config=Configuration(selenium_driver_log_file=None))
        await spider._handle_url(file_url)

        assert [] == parse_args
        logger_mock.assert_any_call(f'unable to open file {file_url}')
        assert {file_url} == spider.unreachable_urls
        assert set() == spider.reachable_urls
        assert 0 == spider.request_counter == spider._total_fetch_time

        # cleanup
        await spider._cleanup()

    @respx.mock
    async def test_should_not_called_parse_method_if_url_is_not_accessible(self, mocker):
        parse_args = []
        url = 'http://foo.com'

        async def parse(sel_spider, response):
            parse_args.extend([sel_spider, response])

        respx.get(f'{url}/robots.txt') % 404
        mocker.patch('selenium.webdriver.remote.webdriver.WebDriver.get', side_effect=WebDriverException)
        config = Configuration(follow_robots_txt=True, selenium_driver_log_file=None)
        spider = SeleniumSpider(urls=[url], parse=parse, config=config)
        await spider._handle_url(url)

        assert [] == parse_args
        assert {url} == spider.unreachable_urls
        assert set() == spider.reachable_urls
        assert 0 == spider.request_counter == spider._total_fetch_time

        # cleanup
        await spider._cleanup()

    # for an unknown reason asyncio timer on Windows does not work correctly which makes
    # static_spider._total_fetch_time to be equal to 0.0 and therefore the test fails
    # this si why the test is only run on trio backend
    @pytest.mark.parametrize('anyio_backend', ['trio'])
    async def test_should_fetch_content_when_giving_http_url(self, mocker, anyio_backend):
        parse_args = []
        url = 'http://foo.com'

        async def parse(sel_spider, response):
            parse_args.extend([sel_spider, response])

        mocker.patch('selenium.webdriver.remote.webdriver.WebDriver.get')
        mocker.patch('selenium.webdriver.remote.webdriver.WebDriver.current_window_handle', 'handle')
        config = Configuration(follow_robots_txt=True, selenium_driver_log_file=None)
        spider = SeleniumSpider(urls=[url], parse=parse, config=config)
        await spider._handle_url(url)

        assert parse_args[0] is spider
        selenium_response = parse_args[1]
        assert isinstance(selenium_response, SeleniumResponse)
        assert selenium_response.driver is spider._driver
        assert 'handle' == selenium_response.handle
        assert {url} == spider.reachable_urls
        assert 1 == spider.request_counter
        assert set() == spider.unreachable_urls
        assert spider._total_fetch_time > 0

        # cleanup
        await spider._cleanup()

    async def test_should_raise_error_if_parse_function_raises_error_and_ignore_errors_is_false(self, mocker):
        async def parse(*_):
            raise ValueError('simple error')

        url = 'http://foo.com'
        mocker.patch('selenium.webdriver.remote.webdriver.WebDriver.get')
        config = Configuration(selenium_driver_log_file=None)
        spider = SeleniumSpider(urls=[url], parse=parse, config=config, ignore_errors=False)

        with pytest.raises(ValueError) as exc_info:
            await spider._handle_url(url)

        assert 'simple error' == str(exc_info.value)

        # cleanup
        await spider._cleanup()

    async def test_should_not_raise_error_if_parse_function_raises_error_and_ignore_errors_is_true(self, mocker):
        async def parse(*_):
            raise ValueError('simple error')

        url = 'http://foo.com'
        mocker.patch('selenium.webdriver.remote.webdriver.WebDriver.get')
        config = Configuration(selenium_driver_log_file=None)
        spider = SeleniumSpider(urls=[url], parse=parse, config=config, ignore_errors=True)

        try:
            await spider._handle_url(url)
        except ValueError:
            pytest.fail('unexpected ValueError raised when ignore_errors is set to true')

        # cleanup
        await spider._cleanup()


class TestIntegrationSeleniumSpider:
    @staticmethod
    def processor(item: dict) -> dict:
        item['date'] = datetime.now()
        return item

    @staticmethod
    async def parse(spider: SeleniumSpider, response: SeleniumResponse) -> None:
        quotes = [element.text for element in response.driver.find_elements_by_xpath('//blockquote/p')]
        authors = [element.text for element in response.driver.find_elements_by_xpath('//blockquote/footer')]

        link = None
        try:
            element = response.driver.find_element_by_xpath('//a[2][contains(@href, "page")]')
            link = element.get_attribute('href')
        except NoSuchElementException:
            pass

        for quote, author in zip(quotes, authors):
            await spider.save_item({'quote': quote, 'author': author})

        if link is not None:
            await response.follow(link)

    @pytest.mark.parametrize('browser', [Browser.FIREFOX, Browser.CHROME])
    async def test_should_save_correct_output_when_giving_file_url(self, page_1_file_url, tmp_path, browser):
        backup_path = tmp_path / 'backup.mp'
        config = Configuration(
            item_processors=[self.processor],
            backup_filename=f'{backup_path}',
            selenium_driver_log_file=None,
            selenium_browser=browser,
        )
        spider = SeleniumSpider(urls=[page_1_file_url], parse=self.parse, config=config)
        await spider.run()
        stats = spider.statistics()
        followed_urls = {page_1_file_url.replace('1', '2'), page_1_file_url.replace('1', '3')}

        assert followed_urls == stats.followed_urls
        assert {page_1_file_url} | followed_urls == stats.reachable_urls
        assert stats.total_time > 0
        assert stats.average_fetch_time == spider._total_fetch_time / stats.request_counter
        assert set() == stats.unreachable_urls
        assert set() == stats.robot_excluded_urls
        assert 3 == stats.request_counter
        assert stats.total_time > 0

        albert_count = 0
        async for item in read_mp(backup_path, decoder=datetime_decoder):
            assert isinstance(item['date'], datetime)
            if item['author'] == 'Albert Einstein':
                albert_count += 1

        assert albert_count == 3
